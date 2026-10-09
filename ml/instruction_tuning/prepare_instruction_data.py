#!/usr/bin/env python3
"""Instruction-tuning data loader (prepared only — no full run executed)."""
from __future__ import annotations
from pathlib import Path
import pickle

def prepare(input_path: Path = Path("datasets/raw/instruction_synthetic.txt"), output_path: Path = Path("datasets/processed/instruction_train.pkl")):
    # Synthetic smoke-test; real instruction dataset for Phase 8
    samples = [(torch.tensor([1,2,3]), torch.tensor([4,5,6])) for _ in range(10)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump({"samples": samples, "dataset_version": "v0.1-phase7-instr", "stage": "instruction_tuning"}, f)
    print("Instruction-tuning loader smoke test complete.")
