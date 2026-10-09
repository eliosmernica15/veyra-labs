#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

def compare_checkpoints(checkpoint_a: Path, checkpoint_b: Path, prompts: list[str], tokenizer_path: Path = Path("datasets/processed/tokenizer.json")):
    import torch, math
    state_a = torch.load(str(checkpoint_a), weights_only=False, map_location="cpu")
    state_b = torch.load(str(checkpoint_b), weights_only=False, map_location="cpu")
    meta_a = {"check": str(checkpoint_a), "version": checkpoint_a.name, "step": state_a.get("step",0), "vocab": state_a.get("vocab_size"), "training_config": state_a.get("config",{})}
    meta_b = {"check": str(checkpoint_b), "version": checkpoint_b.name, "step": state_b.get("step",0), "vocab": state_b.get("vocab_size"), "training_config": state_b.get("config",{})}
    comparison = {
        "a": meta_a, "b": meta_b, "prompts": prompts,
        "version": "v1.0-phase8",
        "note": "No improvement claimed without measured evidence across fixed prompts.",
        "regressions": [], "improvements": [],
    }
    return comparison
