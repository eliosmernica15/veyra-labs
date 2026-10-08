#!/usr/bin/env python3
"""Real inference: load checkpoint, generate text with temperature/top-k/top-p."""
from __future__ import annotations

import argparse
from pathlib import Path

import torch

from ml.models.transformer import VeyraPrime, Config
from ml.training.checkpoint import load_checkpoint
from ml.tokenizer.train_tokenizer import load_tokenizer


def generate_text(
    checkpoint_path: Path,
    tokenizer_path: Path,
    prompt: str = "The quick brown fox",
    max_new_tokens: int = 20,
    temperature: float = 1.0,
    top_k: int = 50,
    top_p: float = 0.9,
    seed: int | None = None,
):
    model, state, config = load_checkpoint(checkpoint_path)
    tokenizer = load_tokenizer(tokenizer_path)
    vocab = tokenizer.get_vocab()
    # Encode prompt
    encoding = tokenizer.encode(prompt)
    input_ids = torch.tensor([encoding.ids], dtype=torch.long)
    with torch.no_grad():
        output_ids = model.generate(input_ids, max_new_tokens=max_new_tokens,
                                   temperature=temperature, top_k=top_k, top_p=top_p, seed=seed)
    # Decode
    text = tokenizer.decode(output_ids[0].tolist())
    return {
        "checkpoint": str(checkpoint_path),
        "prompt": prompt,
        "output": text,
        "settings": {"max_new_tokens": max_new_tokens, "temperature": temperature,
                     "top_k": top_k, "top_p": top_p, "seed": seed},
        "step": state.get("step"),
        "vocab_size": config.vocab_size,
        "context_length": config.context_length,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, default=Path("datasets/processed/tokenizer.json"))
    parser.add_argument("--prompt", type=str, default="The quick brown fox")
    parser.add_argument("--max-new-tokens", type=int, default=20)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    result = generate_text(args.checkpoint, args.tokenizer, args.prompt,
                           args.max_new_tokens, args.temperature, seed=args.seed)
    print(f"Checkpoint: {result['checkpoint']} (step {result['step']})")
    print(f"Prompt: {result['prompt']}")
    print(f"Output: {result['output']}")
