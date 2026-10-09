#!/usr/bin/env python3
"""Lightweight experiment tracking (file-based, no external service)."""
from __future__ import annotations
import json, time
from pathlib import Path
from datetime import datetime

class ExperimentTracker:
    def __init__(self, experiment_root: Path = Path("experiments")):
        self.root = experiment_root
        self.root.mkdir(parents=True, exist_ok=True)

    def log_experiment(
        self,
        dataset_version: str,
        tokenizer_version: str,
        config: dict,
        hardware: dict,
        final_loss: float | None,
        best_checkpoint_path: str | None = None,
        best_val_loss: float | None = None,
        steps: int = 0,
        tokens_seen: int = 0,
        optimizer_steps: int = 0,
        wall_time_s: float = 0.0,
        evaluation_result_path: str | None = None,
    ) -> Path:
        exp_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_dir = self.root / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        metadata = {
            "experiment_id": exp_id,
            "timestamp": datetime.now().isoformat(),
            "dataset_version": dataset_version,
            "tokenizer_version": tokenizer_version,
            "model_config": config,
            "hardware": hardware,
            "training_steps": steps,
            "tokens_seen": tokens_seen,
            "optimizer_steps": optimizer_steps,
            "wall_time_s": wall_time_s,
            "final_loss": final_loss,
            "best_checkpoint_path": best_checkpoint_path,
            "best_val_loss": best_val_loss,
            "evaluation_result_path": evaluation_result_path,
            "phase": "Phase 7 — scalable pipeline (not full remote GPU execution)",
        }
        meta_path = exp_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return meta_path
