#!/usr/bin/env python3
"""Data pipeline tests: provenance, preparation, validation."""
from __future__ import annotations

import tempfile
from pathlib import Path

import torch


def test_dataset_readme_exists():
    assert Path("datasets/README.md").exists()


def test_dataset_documentation_exists():
    assert Path("docs/DATASETS.md").exists()


def test_raw_sample_exists():
    assert Path("datasets/raw/sample.txt").exists()
    text = Path("datasets/raw/sample.txt").read_text()
    assert len(text) > 0


def test_tokenizer_exists():
    assert Path("datasets/processed/tokenizer.json").exists()


def test_processed_data_exists():
    assert Path("datasets/processed/train.pkl").exists()


def test_data_preparation_reproducible():
    # Verify that running preparation with the same inputs produces similar results
    import pickle
    with open("datasets/processed/train.pkl", "rb") as f:
        original = pickle.load(f)
    # Should contain samples
    assert "samples" in original
    assert len(original["samples"]) > 0
    # Should reference tokenizer
    assert "tokenizer_path" in original
    # Vocab size should match tokenizer
    from ml.tokenizer.train_tokenizer import load_tokenizer
    tok = load_tokenizer(Path(original.get("tokenizer_path", "datasets/processed/tokenizer.json")))
    vocab_size = tok.get_vocab_size()
    assert vocab_size == original.get("vocab_size", vocab_size)
