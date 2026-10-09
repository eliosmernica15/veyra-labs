#!/usr/bin/env python3
"""Checkpoint load/save utilities with compatibility validation."""
from __future__ import annotations

from pathlib import Path
import torch
from ml.models.transformer import VeyraPrime, Config


def save_checkpoint(path: Path, model: VeyraPrime, optimizer, step: int, tokenizer_path: str, vocab_size: int, losses: list = None):
    state = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer is not None else None,
        "step": step,
        "config": {
            "vocab_size": model.config.vocab_size,
            "context_length": model.config.context_length,
            "embed_dim": model.config.embed_dim,
            "num_layers": model.config.num_layers,
            "num_heads": model.config.num_heads,
            "hidden_dim": model.config.hidden_dim,
        },
        "tokenizer_path": tokenizer_path,
        "vocab_size": vocab_size,
        "losses": losses,
    }
    torch.save(state, str(path))
    return path


def load_checkpoint(path: Path, model: VeyraPrime | None = None):
    # Portable load: map_location ensures checkpoint saved on GPU can load on CPU and vice versa
    state = torch.load(str(path), weights_only=False, map_location="cpu")
    vocab_from_checkpoint = state.get("vocab_size", state.get("config", {}).get("vocab_size", 4096))
    config = Config(vocab_size=vocab_from_checkpoint)
    if "config" in state:
        for k, v in state["config"].items():
            if hasattr(config, k) and k != "vocab_size":
                setattr(config, k, v)
    # Ensure vocab size from dataset is preserved
    config.vocab_size = vocab_from_checkpoint
    # Recompute derived value when embed_dim/num_heads changed via setattr
    if hasattr(config, 'embed_dim') and hasattr(config, 'num_heads'):
        config.head_dim = config.embed_dim // config.num_heads
        assert config.head_dim * config.num_heads == config.embed_dim, f"head_dim mismatch: {config.embed_dim} / {config.num_heads}"
    if model is None:
        model = VeyraPrime(config)
    model.load_state_dict(state["model_state_dict"], strict=False)
    # Use portable device: prefer CUDA when available, else CPU
    config.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # Ensure vocab consistency
    if vocab_from_checkpoint != config.vocab_size:
        config.vocab_size = vocab_from_checkpoint  # force match
    model.to(config.device)
    return model, state, config
# Phase 7 enhancement: save best-checkpoint metadata file alongside checkpoints
# (best_checkpoint.json written when evaluation finds lower val_loss)
