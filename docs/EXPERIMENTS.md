# Phase 8 — First Substantial Training Experiment Proposal

Status: PROPOSED ONLY — not executed. Waiting for user approval and working GPU environment.

Candidate configurations (ESTIMATES — clearly marked):

Candidate A — Small progressive (development / smoke-to-real transition):
- Params: ~2-5M (vocab=4096, embed=256, layers=6, heads=8, hidden=512, context=256)
- Checkpoint: ~20-40MB
- VRAM (mixed precision, accumulation=2): ~4-8GB
- Dataset: public-domain text ~100MB-1GB (versioned, deduplicated)
- Steps: 1000-5000
- Expected time on single GPU: hours to days
- Recommended GPU: RTX 3060 / A10 / V100 (estimate — not verified)

Candidate B — Medium pretraining (first serious experiment):
- Params: ~10-30M (vocab=4096, embed=512, layers=12, heads=8, hidden=1024, context=512)
- Checkpoint: ~100-300MB
- VRAM (mixed precision, accumulation=4): ~16-32GB
- Dataset: larger public-domain corpus (versioned, deduplicated)
- Steps: 10000+
- Recommended GPU: A100 / H100 / multi-GPU

Candidate C — Large pretraining (future Phase 9):
- Params: 100M+
- Requires distributed / multi-GPU or cloud cluster
- Not proposed for immediate Phase 8 execution

All estimates marked as estimates; no exact performance predictions given.
Improvement must be shown across fixed quality gates (quality_gates.yaml) with actual outputs — not from parameter count or loss alone.
Baseline preserved: checkpoint_final.pt (step 35, ~565k) remains reference.
