#!/usr/bin/env python3
"""Cloud-readiness and portability tests: device portability, checkpoint resume, config portability."""
from __future__ import annotations

import tempfile
from pathlib import Path

import torch

from ml.training.train_loop import train
from ml.training.checkpoint import load_checkpoint


def test_portable_checkpoint_load():
    # Verify checkpoint can be loaded on CPU regardless of where saved
    checkpoint_path = Path("checkpoints/checkpoint_final.pt")
    if not checkpoint_path.exists():
        # Skip if no checkpoint exists (smoke test may not have run in isolated test)
        import pytest
        pytest.skip("No checkpoint available for portability test")
    model, state, config = load_checkpoint(checkpoint_path)
    assert state.get("step") > 0
    assert config.vocab_size > 0


def test_checkpoint_resume_on_cpu():
    # Verify resume from checkpoint works and uses CPU safely
    checkpoint_path = Path("checkpoints/checkpoint_step_30.pt")
    if not checkpoint_path.exists():
        import pytest
        pytest.skip("Checkpoint step 30 not available for resume test")
    result_path, model, losses = train(
        data_path=Path("datasets/processed/train.pkl"),
        steps=5,
        batch_size=2,
        lr=1e-3,
        resume_from=checkpoint_path,
    )
    assert result_path.exists()
    assert len(losses) == 5


def test_config_portable():
    # Verify Config can be created with different vocab sizes (simulating different dataset sizes)
    from ml.models.transformer import Config
    cfg_small = Config(vocab_size=155, embed_dim=128, num_layers=2)
    cfg_large = Config(vocab_size=4096, embed_dim=128, num_layers=2)
    assert cfg_small.vocab_size == 155
    assert cfg_large.vocab_size == 4096
    assert cfg_large.embed_dim == cfg_small.embed_dim
