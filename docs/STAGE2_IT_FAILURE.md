# Stage 2 — Instruction-Tuning Empty Output Root Cause (Real)
Status: DIAGNOSED — EVIDENCE-BASED
Token 0 decode: '' (empty/pad/unknown)
v4 dataset: 4000 samples; ALL have <5 non-zero tokens out of 64 in answer (y)
Cause: rough_encode + short texts + vocab limitations -> sparse/empty targets
IT trained with direct cross_entropy on empty targets -> model learns to emit token 0
Fix required: build instruction dataset with continuous sequences + real tokenizer + nonempty targets + proper masking.
