#!/usr/bin/env python3
"""Train a BPE tokenizer from a small public-domain text corpus."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from tokenizers import Tokenizer, models, trainers, pre_tokenizers, processors, decoders


def train_tokenizer(raw_path: Path, vocab_size: int = 4096) -> Tokenizer:
    # Read raw text
    text = raw_path.read_text(encoding="utf-8", errors="ignore") if raw_path.is_file() else ""
    # If empty, create a minimal synthetic dataset for smoke tests
    if len(text) < 200:
        # Synthetic public-domain style text for smoke testing
        text = (
            "The quick brown fox jumps over the lazy dog. " * 30
            + "In science we investigate phenomena through observation and experiment. " * 20
            + "Machine learning models learn patterns from data using mathematical optimization. " * 15
        )
    # Write temporary training file
    train_file = Path("/tmp/veyra_tokenizer_train.txt")
    train_file.write_text(text, encoding="utf-8")

    tokenizer = Tokenizer(models.BPE())
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel()
    tokenizer.decoder = decoders.ByteLevel()
    tokenizer.post_processor = processors.ByteLevel(add_prefix_space=True)
    tokenizer.processor = processors.TemplateProcessing(
        single="$A </s>",
        pair="$A </s> $B </s>",
        special_tokens=[("</s>", 1), ("<pad>", 2), ("<unk>", 3)],
    )
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        special_tokens=["</s>", "<pad>", "<unk>"],
        min_frequency=2,
    )
    tokenizer.train([str(train_file)], trainer)
    return tokenizer


def save_tokenizer(tokenizer: Tokenizer, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(out_path))


def load_tokenizer(path: Path) -> Tokenizer:
    return Tokenizer.from_file(str(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("datasets/raw/sample.txt"))
    parser.add_argument("--vocab-size", type=int, default=4096)
    parser.add_argument("--output", type=Path, default=Path("datasets/processed/tokenizer.json"))
    args = parser.parse_args()
    tok = train_tokenizer(args.raw, args.vocab_size)
    save_tokenizer(tok, args.output)
    print(f"Tokenizer saved to {args.output} (vocab size: {tok.get_vocab_size()})")
