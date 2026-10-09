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
    tokenizer_path: Path | None = None,
    prompt: str = "The quick brown fox",
    max_new_tokens: int = 20,
    temperature: float = 1.0,
    top_k: int = 50,
    top_p: float = 0.9,
    seed: int | None = None,
):
    model, state, config = load_checkpoint(checkpoint_path)
    checkpoint_tokenizer_path = state.get("tokenizer_path")
    if checkpoint_tokenizer_path:
        checkpoint_tokenizer_path = Path(checkpoint_tokenizer_path)
        if tokenizer_path is not None and tokenizer_path.resolve() != checkpoint_tokenizer_path.resolve():
            raise ValueError("The requested tokenizer does not match the checkpoint's recorded tokenizer")
        tokenizer_path = checkpoint_tokenizer_path
    if tokenizer_path is None:
        raise ValueError("No tokenizer path was supplied or recorded in the checkpoint")
    tokenizer = load_tokenizer(tokenizer_path)
    if tokenizer.get_vocab_size() != config.vocab_size:
        raise ValueError(
            f"Tokenizer vocabulary ({tokenizer.get_vocab_size()}) does not match "
            f"checkpoint vocabulary ({config.vocab_size})"
        )
    eos_token_id = tokenizer.token_to_id("</s>")
    pad_token_id = tokenizer.token_to_id("<pad>")
    if eos_token_id is None or pad_token_id is None:
        raise ValueError("Tokenizer must define </s> and <pad> tokens for generation")
    encoding = tokenizer.encode(prompt, add_special_tokens=False)
    if not encoding.ids:
        raise ValueError("Prompt produced no input tokens")
    input_ids = torch.tensor([encoding.ids], dtype=torch.long)
    model.eval()
    with torch.no_grad():
        output_ids = model.generate(input_ids, max_new_tokens=max_new_tokens,
                                   temperature=temperature, top_k=top_k, top_p=top_p, seed=seed,
                                   eos_token_id=eos_token_id, pad_token_id=pad_token_id)
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
    parser.add_argument("--tokenizer", type=Path, default=None)
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
