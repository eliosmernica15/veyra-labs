# Phase 8 — Reproducibility
Same dataset + same tokenizer + same config (configs/training/default.yaml) + same seed = reproducible pipeline.
Record for every run: dataset_version, tokenizer_version, model_config, hardware, seed, start/end time, steps, tokens, optimizer_steps, validation metrics, checkpoint paths, evaluation references.
Experiment tracker (ml/training/experiment_tracker.py) writes metadata.json automatically.
