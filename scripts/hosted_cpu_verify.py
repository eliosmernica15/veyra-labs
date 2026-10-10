#!/usr/bin/env python3
"""Verify the preserved Veyra checkpoint and fixed prompts on a CPU runner."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pickle
import platform
import time
from pathlib import Path
from typing import Any

import torch

from ml.inference.generate import generate_text
from ml.training.checkpoint import load_checkpoint
from ml.training.train_loop import evaluate

PROMPTS = (
    "hi how are you",
    "What is 2 + 2?",
    "Explain what Python is in two sentences.",
    "Reply with exactly three bullet points about computers.",
    "Write a Python function that adds two numbers.",
    "Fix this code: def add(a, b) return a + b",
    "Summarize what a list is in Python.",
    "What is 17 times 6?",
)
CHECKPOINT_SHA256 = "7aaee496c5adff3f652a30d67b3bf12dc5438505364ea5a7582a869b43b2110b"
TOKENIZER_SHA256 = "47ccdfb870d203c002c65c64e199aeb0ec7b36fc9a91e2826fd2c7d9f0456c4d"
VALIDATION_SHA256 = "1106bb2fd22cbfa6325fb52ea34194262d09cf306355b3338e3add88410123c3"
VALIDATION_SAMPLE_COUNT = 883
VALIDATION_SUPERVISED_TOKENS = 437_989


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def state_dict_sha256(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in model.state_dict().items():
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def run(checkpoint_path: Path, tokenizer_path: Path, validation_path: Path) -> dict[str, Any]:
    if torch.cuda.is_available():
        raise RuntimeError("This verification is intended to run on CPU only")
    torch.set_num_threads(2)

    for path, expected, label in (
        (checkpoint_path, CHECKPOINT_SHA256, "checkpoint"),
        (tokenizer_path, TOKENIZER_SHA256, "tokenizer"),
        (validation_path, VALIDATION_SHA256, "validation split"),
    ):
        actual = sha256_file(path)
        if actual != expected:
            raise ValueError(f"{label} SHA-256 mismatch: {actual}")

    with validation_path.open("rb") as source:
        validation_data = pickle.load(source)
    samples = validation_data["samples"]
    validation_sample_count = len(samples)
    supervised_tokens = sum(int((target != -1).sum().item()) for _, target in samples)
    if (
        validation_data.get("split") != "val"
        or validation_sample_count != VALIDATION_SAMPLE_COUNT
        or supervised_tokens != VALIDATION_SUPERVISED_TOKENS
    ):
        raise ValueError("Validation artifact split or supervised-target count is incorrect")

    model, state, config = load_checkpoint(checkpoint_path)
    weights_before = state_dict_sha256(model)
    validation_started = time.monotonic()
    validation_loss = evaluate(model, samples, device=torch.device("cpu"), batch_size=8)
    validation_seconds = time.monotonic() - validation_started
    weights_after = state_dict_sha256(model)
    if weights_before != weights_after:
        raise RuntimeError("Validation modified model weights")

    step = state.get("step")
    del model, state, samples, validation_data
    gc.collect()

    generations = []
    for index, prompt in enumerate(PROMPTS):
        result = generate_text(
            checkpoint_path,
            tokenizer_path,
            prompt=prompt,
            max_new_tokens=32,
            temperature=0.8,
            top_k=50,
            top_p=0.9,
            seed=4200 + index,
        )
        generations.append({"prompt": prompt, "output": result["output"], "seed": 4200 + index})

    return {
        "host": platform.platform(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cpu_threads": torch.get_num_threads(),
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "validation_sha256": VALIDATION_SHA256,
        "checkpoint_step": step,
        "model_config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "validation_samples": validation_sample_count,
        "validation_supervised_tokens": supervised_tokens,
        "validation_loss": validation_loss,
        "validation_seconds": validation_seconds,
        "validation_weight_sha256_before": weights_before,
        "validation_weight_sha256_after": weights_after,
        "generations": generations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run(args.checkpoint, args.tokenizer, args.validation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
