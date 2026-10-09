# Veyra-000 Identity Document — Baseline (Preserved)

## Purpose
Establishes Veyra-000 as the preserved baseline model separated from the Veyra-001 registry entry. This document confirms the baseline was not overwritten.

## Identity
- Model ID: Veyra-000
- Registry version: v0.0 (baseline / preserved)
- Document date: 2026-10-09
- Status: PRESERVED — DO NOT OVERWRITE

## Baseline Details
- Version: veyra_smoke_baseline
- Checkpoint path: checkpoints/checkpoint_final.pt
- Checkpoint size: 6,826,181 bytes
- Checkpoint md5: c75c446f5bed615059565cf27aaea566
- Step (verified): 35 (from runs/evaluation_result.json; CHECKPOINT_INVENTORY.md resolves step-50 discrepancy)
- Parameters: 564,992
- Vocab: 155
- Context: 128
- Tokenizer: datasets/processed/tokenizer.json (ByteLevel, v1 fixed Phase 6)
- Dataset: datasets/raw/sample.txt (v1.0-smoke)
- Training config (actual): vocab=155, embed=128, layers=4, heads=4, hidden=256, dropout=0.1, batch=4, lr=1e-3, weight_decay=0.01, grad_clip=1.0, steps=35, interval=10
- Creation: ~2026-10-08 19:03 (original smoke test; Phase 7 edit to train_loop did not overwrite)
- Optimizer state: present; scheduler: NONE
- Parent checkpoint: unknown
- Quality: generation FAIL (documented); tokenizer PASS; framework PASS

## Preservation Statement
- File overwritten: NO
- File modified: NO
- Checksum at verification: c75c446f5bed615059565cf27aaea566
- Separation from Veyra-001: documented in ml/registry/identities/Veyra-001.md
