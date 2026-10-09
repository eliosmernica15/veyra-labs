#!/usr/bin/env python3
"""Data preparation pipeline: load raw text, split, tokenize, save batches.
Phase 7: train/val split + dataset version metadata."""
from __future__ import annotations
import argparse, pickle
from pathlib import Path
import torch
from ml.tokenizer.train_tokenizer import load_tokenizer, train_tokenizer

def prepare_dataset(raw_path: Path, tokenizer_path: Path, out_path: Path, val_path: Path = None, max_samples: int = 500):
    tokenizer = load_tokenizer(tokenizer_path)
    vocab_size = tokenizer.get_vocab_size()
    text = raw_path.read_text(encoding="utf-8", errors="ignore") if raw_path.is_file() else ""
    if len(text) < 200:
        text = (
            "The quick brown fox jumps over the lazy dog. " * 30
            + "Science is the pursuit of knowledge through observation and reasoning. " * 20
        )
    encoding = tokenizer.encode(text)
    ids = encoding.ids
    chunk_len = 128
    samples = []
    step = chunk_len // 2
    for i in range(0, max(0, len(ids) - chunk_len - 1), step):
        chunk = ids[i:i + chunk_len + 1]
        if len(chunk) < chunk_len + 1:
            break
        x = torch.tensor(chunk[:-1], dtype=torch.long)
        y = torch.tensor(chunk[1:], dtype=torch.long)
        samples.append((x, y))
        if len(samples) >= max_samples:
            break
    # Train/val split (90/10) for Phase 7 reproducibility
    split_idx = int(len(samples) * 0.9)
    train_samples = samples[:split_idx]
    val_samples = samples[split_idx:] if val_path else []
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump({"samples": train_samples, "tokenizer_path": str(tokenizer_path),
                     "vocab_size": vocab_size, "dataset_version": "v1.0-phase7",
                     "split": "train", "total_samples": len(samples)}, f)
    if val_path:
        val_path.parent.mkdir(parents=True, exist_ok=True)
        with open(val_path, "wb") as f:
            pickle.dump({"samples": val_samples, "tokenizer_path": str(tokenizer_path),
                         "vocab_size": vocab_size, "dataset_version": "v1.0-phase7",
                         "split": "val", "total_samples": len(samples)}, f)
    print(f"Prepared {len(train_samples)} train, {len(val_samples)} val -> {out_path} (vocab_size={vocab_size})")
    return train_samples

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("datasets/raw/sample.txt"))
    parser.add_argument("--tokenizer", type=Path, default=Path("datasets/processed/tokenizer.json"))
    parser.add_argument("--output", type=Path, default=Path("datasets/processed/train.pkl"))
    parser.add_argument("--val-output", type=Path, default=Path("datasets/processed/val.pkl"))
    parser.add_argument("--max-samples", type=int, default=500)
    args = parser.parse_args()
    prepare_dataset(args.raw, args.tokenizer, args.output, args.val_output, args.max_samples)
