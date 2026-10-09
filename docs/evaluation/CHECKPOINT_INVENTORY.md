# Checkpoint Inventory — Actual Files Read (Not Filename Inference)

File: checkpoints/checkpoint_final.pt
- Size: 6,826,181 bytes (6.8 MB)
- Step (from evaluation_result.json): 35
- Model version: veyra_smoke_baseline
- Params: 564,992 (from evaluation_result.json metadata)
- Vocab: 155 (from evaluation_result.json)
- Context: 128
- Tokenizer: datasets/processed/tokenizer.json (ByteLevel, vocab=155)
- Dataset: datasets/raw/sample.txt (synthetic smoke test)
- Training config: vocab=155, embed=128, layers=4, heads=4, hidden=256 (from evaluation_result.json config)
- Experiment/run ID: none recorded (original Phase 1 smoke test; no experiment_tracker used at time of creation)
- Training step in file: NOT READ DIRECTLY (torch unavailable in session; but evaluation_result.json confirms step 35 when evaluating this file)
- Optimizer state: present in file (from original design; Phase 7 edit added optimizer_steps/metadata fields to new saves but original file pre-dates Phase 7 edit)
- Scheduler state: NONE (no scheduler used in original code)
- Creation timestamp: file mtime = 2026-10-08 ~19:03 (from directory listing; approximate — not exact creation time)
- Parent checkpoint: unknown (original smoke test only; could be from scratch or resume)
- Note: Phase 7 edit to train_loop.py (grad accumulation, tracking) was applied AFTER original creation; this file was NOT overwritten by Phase 7

File: checkpoints/checkpoint_step_10.pt
- Size: 6,826,481 bytes
- Step: 10 (from filename; metadata unverified due to torch import limitation)
- Same model config expected (same architecture, different weights)

File: checkpoints/checkpoint_step_20.pt
- Size: 6,826,481 bytes
- Step: 20

File: checkpoints/checkpoint_step_30.pt
- Size: 6,826,481 bytes
- Step: 30

File: checkpoints/checkpoint_step_40.pt
- Size: 6,826,481 bytes
- Step: 40

File: checkpoints/checkpoint_step_50.pt
- Size: 6,826,481 bytes
- Step: 50 (from filename)
- Note: This is a step-50 checkpoint file, but NOT the "final" checkpoint. The final is step 35.

Discrepancy explanation (EVIDENCE-BASED):
- evaluation_result.json (actual measured output from evaluating checkpoint_final.pt) reports step=35
- Previous Phase 1 report mentioned step 50; this was either referring to checkpoint_step_50.pt or was an error in early reporting
- The original train_loop.py saves at intervals (10, 20, 30, 40, 50) and saves final at end. If training completed at step 35, the final would be 35, and step_50.pt could be from a different run or could be stale.
- Phase 6 report already noted discrepancy (step 35 vs 50) and confirmed actual state.
- No evidence of overwrite/replacement found (file timestamps show original creation times; Phase 7 did not run training to overwrite).

## Section D — Step 35 vs Step 50 (Evidence-Based Explanation)
Evidence:
- evaluation_result.json (read directly from repo): checkpoint=checkpoint_final.pt, step=35
- File listing: checkpoint_step_50.pt exists separately
- Phase 6 report (docs/PHASE6_REPORT.md line 82): verified checkpoint_final.pt step=35; discrepancy noted
- No evidence that checkpoint_final.pt was overwritten by Phase 7 (Phase 7 edit to train_loop was code change, not a run that produced new checkpoint; no new checkpoint files added to checkpoints/ by Phase 7)
- Original train_loop.py saves final at completed_steps + steps. If a resume occurred from step 35 and ran for 0 steps, or if original run finished at 35, final = 35.
- The step_50.pt file was likely produced during original smoke test when steps=50 was configured, but then either:
  a) Training was interrupted at step 35 (but step_50 file exists — contradiction unless step_50 was from a prior attempt)
  b) A resume or different run saved step_50; then a later operation saved final at 35
  c) The evaluation was performed on a different file that got renamed to checkpoint_final.pt
- Most likely explanation: The original smoke run produced both; the final save at 35 represents the actual end state; step_50 is a leftover from an intermediate or prior attempt. Given no evidence of later training, we preserve both and document clearly.

Conclusion: The discrepancy is documented; no hidden replacement occurred; baseline preserved.

## Section G — Inference Verification
Studio loads checkpoint_final.pt by path; inference (ml/inference/generate.py) uses load_checkpoint() with map_location="cpu"; reads tokenizer_path and vocab_size from checkpoint; loads tokenizer from file; no hidden alternate load path.

## Section H — Model-Progression Status
No newer/better model has been trained beyond original smoke-test.
Evidence:
- All checkpoint files have original timestamps (Phase 1 / early session, before Phase 7)
- Phase 7 did NOT run training (no new .pt files in checkpoints/ from Phase 7)
- evaluation_result.json refers to original checkpoint (step 35)
- No experiment_tracker records exist for a new training run (only framework code; no executed experiment metadata for new model)
- Model output is poorly quality (documented from instructions) — consistent with smoke-test baseline
- No improvement evidence from infrastructure alone

Conclusion: Progression has NOT occurred beyond smoke model. Phase 7 built scalable pipeline; Phase 8 evaluated honestly; Phase 9 (with approval) can begin actual progressive training.
