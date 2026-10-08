#!/usr/bin/env python3
"""Data preparation pipeline: load raw text, split, tokenize, save batches."""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import torch

from ml.tokenizer.train_tokenizer import load_tokenizer, train_tokenizer


def prepare_dataset(raw_path: Path, tokenizer_path: Path, out_path: Path, max_samples: int = 500):
    tokenizer = load_tokenizer(tokenizer_path)
    vocab_size = tokenizer.get_vocab_size()
    text = raw_path.read_text(encoding="utf-8", errors="ignore") if raw_path.is_file() else ""
    if len(text) < 200:
        text = (
            "The quick brown fox jumps over the lazy dog. " * 30
            + "Science is the pursuit of knowledge through observation and reasoning. " * 20
        )
    # Encode full text
    encoding = tokenizer.encode(text)
    ids = encoding.ids
    # Split into chunks: input = sequence[:-1], target = sequence[1:]
    chunk_len = 128  # match context length
    samples = []
    step = chunk_len // 2  # overlap for more training samples
    for i in range(0, max(0, len(ids) - chunk_len - 1), step):
        chunk = ids[i:i + chunk_len + 1]
        if len(chunk) < chunk_len + 1:
            break
        x = torch.tensor(chunk[:-1], dtype=torch.long)
        y = torch.tensor(chunk[1:], dtype=torch.long)
        samples.append((x, y))
        if len(samples) >= max_samples:
            break
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump({"samples": samples, "tokenizer_path": str(tokenizer_path), "vocab_size": vocab_size}, f)
    print(f"Prepared {len(samples)} samples -> {out_path} (vocab_size={vocab_size})")
    return samples


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("datasets/raw/sample.txt"))
    parser.add_argument("--tokenizer", type=Path, default=Path("datasets/processed/tokenizer.json"))
    parser.add_argument("--output", type=Path, default=Path("datasets/processed/train.pkl"))
    parser.add_argument("--max-samples", type=int, default=500)
    args = parser.parse_args()
    prepare_dataset(args.raw, args.tokenizer, args.output, args.max_samples)
