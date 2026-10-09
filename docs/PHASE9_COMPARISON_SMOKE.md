# Phase 9 Model Comparison — Verification Only (Honest)

Status: VERIFICATION ONLY (5-step CPU smoke, no remote GPU); NOT substantial pretraining.
Baseline preserved: checkpoints/checkpoint_final.pt (Veyra-000, step 35, 564,352 params, vocab 155).
Verification checkpoint: checkpoints/veyra001_smoke.pt (Veyra-001, step 5, 3,239,424 params, vocab 200).
Material size difference verified: 3.24M vs 564K (~5.7x larger).
Weight-change verified: all 45 weight keys changed during 5-step optimization.
Output shape difference expected (vocab 200 vs 155) — direct numeric comparison not applicable; qualitative comparison not performed because smoke is not a capable model.
No claim of improvement made. Full comparison requires completed remote-GPU experiment.
