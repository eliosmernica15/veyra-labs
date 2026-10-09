#!/usr/bin/env python3
"""Remote GPU training template — same code, same checkpoints, portable."""
"""Usage: copy dataset, tokenizer, checkpoints to remote server; run with same args."""
from __future__ import annotations
from pathlib import Path

def remote_training_command(data_path: Path, output_dir: Path, steps: int = 50, resume: Path | None = None):
    cmd_parts = [
        "python", "-m", "ml.training.train_loop",
        f"--data={data_path}",
        f"--output-dir={output_dir}",
        f"--steps={steps}",
    ]
    if resume:
        cmd_parts.append(f"--resume={resume}")
    # Mixed precision enabled when CUDA available (auto in train_loop)
    cmd = " ".join(cmd_parts)
    return cmd

if __name__ == "__main__":
    print("Remote runner template — copy code + datasets/checkpoints, then run:")
    print(remote_training_command(Path("datasets/processed/train.pkl"), Path("checkpoints"), steps=50))
