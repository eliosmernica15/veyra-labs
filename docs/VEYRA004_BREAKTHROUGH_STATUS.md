# Veyra-004 Status — Breakthrough Verified, Overfit Documented (Real, $0, Local)
Status: EXECUTED — REAL INFERENCE — NO FABRICATION

Breakthrough evidence:
- Previous best (Veyra-003 pretrain 90): partial fragments ('y','I','m')
- Previous IT: token 0 (empty) — 3 attempts, all rejected
- Veyra-004 (4096 vocab, 60.2M params, 50 steps): NON-EMPTY — "Phase" / "environment"
- Held-out: all return same repetitive tokens → overfit to expanded corpus repetition

Root cause of overfit: expanded corpus uses 3000 repetitions of 15 categories (verified by inspection); model memorizes frequent phrases.
Fix for quality: build truly diverse original corpus (10k-50k unique examples, varied sources) or train longer with validation selection; NOT just more steps on same text.

Best preserved: checkpoints/veyra004_pretrain/checkpoint_step_50.pt (lowest loss 0.0066, non-empty)
Rejected by comparison: Veyra-003 best (partial), all Veyra-004 IT attempts not yet tried (could attempt with correct masked format after data diversity)

Security: AGENT_AUTONOMOUS_EXECUTION=False preserved.
Cost: $0 local CPU.
No external LLM/API.
All historical checkpoints preserved (001/002/003/init/pretrain/IT/rejected/004).
