# Veyra Model Registry

Veyra-000 (Baseline / Smoke)
- Checkpoint: checkpoints/checkpoint_final.pt
- Step: 35
- Params: 564,992 (verified from checkpoint load)
- Vocab: 155
- Context: 32 (approx, from original Config)
- Status: PROTECTED — not overwritten by Phase 9
- Identity: smoke-test baseline only; NOT a capable assistant
- Lineage / Child entry: Veyra-001 (Phase 9 smoke verification; checkpoints/veyra001_smoke.pt step 5, 3,239,424 params, vocab 200) — identity upgrade registered FROM this preserved baseline; no overwrite performed.
- Documented poor output: `hiiii` -> broken fragments (docs/evaluation/BASELINE_EVALUATION.md)

Veyra-001 (Phase 9 — First Substantial Experiment — Verification Only)
- Checkpoint: checkpoints/veyra001_smoke.pt (verification; 5 steps)
- Config: ml/configs/veyra001.yaml
- Dataset: datasets/processed/train_veyra001.pkl / val_veyra001.pkl (v1.0)
- Tokenizer: datasets/processed/tokenizer_veyra001.json (v1.0, vocab 200 chosen; 4096 aspirational)
- Params: 3,239,424 (verified from init + smoke load)
- Step: 5
- Status: VERIFICATION COMPLETE; substantial remote-GPU pretraining NOT executed (no GPU available)
- Baseline comparison: docs/PHASE9_COMPARISON_SMOKE.md
- Milestone: smoke / gibberish (no coherent language achieved — documented honestly)
- Cost: $0
- Lineage: Veyra-001 -> trained/configured from Veyra-000; not replacing baseline

Next proposed: Veyra-002 (after remote GPU approval, larger dataset, vocab 4096+, more steps)

Veyra-001-IT (Instruction-Tuned � Phase 10)
- Parent: Veyra-001 smoke (checkpoints/veyra001_smoke.pt, step 5, 3,239,424 params)
- Checkpoint: checkpoints/veyra001_it/instruction_final.pt (step 20, 3,239,424 params � same architecture, optimized for instruction data)
- Dataset: datasets/processed/instruction_train.pkl / instruction_val.pkl (20 original examples, v1.0)
- Training: 20 steps CPU, batch 2, lr 5e-4, mixed_precision False, accumulation 1
- Loss trajectory: 4.89 -> 2.82 -> 1.62 -> 1.23 -> 0.88 (training); val: 2.57 -> 2.48 -> 2.48
- Checkpoints: instruction_step_10.pt, instruction_step_15.pt, instruction_step_20.pt, instruction_final.pt
- Status: REAL LOCAL CPU INSTRUCTION TUNING EXECUTED. Not a smoke run. Pipeline verified. Milestone unchanged (small model, early stage).
- Cost: $0.00
- Security preserved: AGENT_AUTONOMOUS_EXECUTION=False; workspace/local only; no external model
- Identity separate from Veyra-000 (baseline) and Veyra-001 (smoke verification)

## Iteration B — 2026-10-09 (Executed honestly under directive id=bede)
- Candidate: checkpoints/veyra001_it/iteration_b_30/instruction_final.pt (step 50, Veyra-001-IT-ITER-B)
- Parent: checkpoints/veyra001_it/instruction_final.pt (step 20, Veyra-001-IT)
- Dataset: datasets/processed/instruction_train_v2.pkl (v1.1, 21 samples — 16 original corrected + 5 added)
- Training: 30 steps CPU, batch 2, lr 5e-4, resume from step 20; checkpoints every 5 steps
- Training metrics (honest from log): loss 0.5235 (step 21) -> 0.0885 (step 30) -> 0.0117 (step 48); val_loss 2.6859/2.7104/2.6825/2.8263/2.7489/2.7934 — no improvement, fluctuating around 2.7
- Technical verification: load_checkpoint fix applied (head_dim recomputation); forward verified; no crash
- Evaluation: real inference executed on 6 fixed prompts (token IDs recorded, no fabricated text); quality still insufficient
- Verdict: REJECTED — overfitting shown by training loss collapse with unchanged validation loss; not better than step 20
- Best preserved: checkpoints/veyra001_it/instruction_final.pt (step 20) — NEVER overwritten; baseline (checkpoint_final.pt) untouched
- Next justified step: expand dataset to 10k-50k original examples or increase model capacity; do not train more steps on 21 examples

## Veyra-002 — Master Directive Execution (id=bede, authorized, confirmed)
- Architecture: Config(vocab=512, embed=512, 6 layers, 8 heads, hidden=2048, context=256) — ~19.3M params
- Tokenizer: datasets/processed/tokenizer_veyra002.json (ByteLevel BPE, vocab 512, verified roundtrip)
- Pretraining: checkpoints/veyra002_pretrain/checkpoint_final.pt (step 100, 19.3M params, $0 CPU, 43s, loss 6.3->0.0007)
- Instruction tuning: checkpoints/veyra002_it/instruction_final.pt (step 120, resuming pretrain; dataset v3 400 train/100 val; loss 9.3->0.39; val best ~0.70 at step 105/110, then rise to 2.22 at 120 — overfitting after best val)
- Best deployment checkpoint: checkpoints/veyra002_it/instruction_step_105.pt OR instruction_step_110.pt (by validation, not final; documented)
- Current best model identity: Veyra-002-IT (step ~105/110, validated) — KEPT; not rejected
- Rejected candidates preserved but not best: Veyra-001-IT step 20 (preserved); Iteration B step 50 (rejected for overfitting on v1.1); Veyra-002 step 120 (overfits; use best-val instead)
- Integration verified: load_checkpoint works (head_dim 64 verified); forward passes; tokenizer matches; registry updated; CLI/studio paths maintained
- Security: AGENT_AUTONOMOUS_EXECUTION=False preserved; $0; local-only; no external LLM for inference
