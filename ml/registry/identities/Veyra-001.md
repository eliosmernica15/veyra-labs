# Veyra-001 Identity Document — Model Registry Entry

## Purpose
Separates Veyra-001 (current registered identity) from Veyra-000 baseline (preserved smoke-test checkpoint). This entry does not replace or overwrite the baseline file.

## Identity
- Model ID: Veyra-001
- Registry version: v1.0
- Entry date: 2026-10-09
- Author: Registry update (Phase 8 / post-Phase 7 pipeline)

## Baseline Separation (Veyra-000)
- Baseline model ID: Veyra-000
- Baseline version: veyra_smoke_baseline
- Baseline checkpoint: checkpoints/checkpoint_final.pt
- Baseline step: 35 (verified from evaluation_result.json; step-50 file is separate artifact)
- Baseline params: 564,992 (vocab=155, embed=128, layers=4, heads=4, hidden=256, context=128)
- Baseline tokenizer: datasets/processed/tokenizer.json (ByteLevel, vocab=155)
- Baseline dataset: datasets/raw/sample.txt (synthetic smoke, v1.0-smoke)
- Baseline evaluation: docs/evaluation/BASELINE_EVALUATION.md (v1.0-phase8, 2026-10-08)
- Baseline status: PRESERVED. File not overwritten. Checkpoint checksum preserved.

## Veyra-001 Registration (this entry)
- Registry entry type: smoke_model / baseline-registered (same architecture, documented identity upgrade)
- Checkpoint reference: checkpoints/checkpoint_final.pt (original preserved file; not modified)
- Step reference: 35 (actual measured; step-50 file exists separately but is not the final)
- Model version tag: veyra_smoke_baseline (retained for continuity) -> registry identity upgraded to Veyra-001
- Parameter count: 564,992
- Vocabulary size: 155
- Context length: 128
- Tokenizer version: v1 (ByteLevel, fixed Phase 6)
- Dataset version: v1.0-smoke
- Training config: vocab_size=155, context_length=128, embed_dim=128, num_layers=4, num_heads=4, hidden_dim=256, dropout=0.1, batch_size=4, lr=1e-3, weight_decay=0.01, grad_clip=1.0, steps=35 (actual final), checkpoint_interval=10
- Hardware info: CPU (environment import limitation noted; no distributed training)
- Wall time: not fully measured (session environment limitation)
- Best checkpoint / val loss: not separately computed (no val split in original smoke run; Phase 7 added infrastructure)
- Optimizer state: present (original file pre-dates Phase 7 optimizer_steps/metadata edits; Phase 7 edits applied to code, not to this file)
- Scheduler state: NONE
- Parent checkpoint: unknown (original smoke test only)
- Quality assessment: generation FAIL (expected smoke-test — poor output documented from instructions); tokenizer coherent PASS; agent framework PASS
- Reproducibility notes: evaluation_result.json confirms step 35, perplexity 7.1608, avg_loss 1.9686; CHECKPOINT_INVENTORY.md documents discrepancy (step 35 vs 50) with evidence

## Registry Update Statement
- Veyra-000 baseline preserved: YES (file untouched; checksum verified)
- Veyra-001 registered: YES (this document)
- Overwrite performed: NO
- File modified: NONE of checkpoints/checkpoint_final.pt

## Verification (baseline unmodified)
- Checksum (md5): c75c446f5bed615059565cf27aaea566 (verified at registry creation)
- Size: 6,826,181 bytes (6.8 MB)
- Modification time preserved from original creation (~2026-10-08 19:03)
- No write operations applied to checkpoints/checkpoint_final.pt during this registry update.
