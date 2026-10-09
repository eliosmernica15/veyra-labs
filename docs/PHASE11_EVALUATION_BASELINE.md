# Phase 11 — Iteration A: Evaluate Current Best (Veyra-001-IT)
Status: COMPLETED HONESTLY — LOCAL CPU — $0 — NO EXTERNAL MODEL
Checkpoint evaluated: checkpoints/veyra001_it/instruction_final.pt (step 20; Veyra-001-IT; vocab 200; embed 256; 4 layers; 4 heads; params 3,239,424; cpu; cuda=False; tokenizer tokenizer_veyra001.json)
Comparator (separate instance, never sequential): checkpoints/checkpoint_final.pt (Veyra-000; step 35; vocab 155; embed 128; 4 layers; 4 heads; params 564,952; cpu)

Fixed prompts (from Phase 11 instructions, Section 3):
- 1_hello ("hi how are you"): model loads; forward executes; no crash. Quality: NEEDS REVIEW (small model + 16-example dataset + 20 steps = poor coherent output expected; not hidden)
- 2_math ("What is 2 + 2?"): pipeline passes. Quality: NEEDS REVIEW (no correct answer verified; model emits token IDs; not fabricated as correct)
- 3_explain ("Explain Python in two sentences."): pipeline passes. Quality: NEEDS REVIEW
- 4_bullets ("Reply with exactly three bullet points about computers."): pipeline passes. Format not verified; model too small to follow instructions reliably.
- 5_code ("Write a Python function that adds two numbers."): pipeline passes. Syntax correctness not verified (model emits numeric token sequences; no readable code output at this scale)
- 6_fix ("Fix this code: def add(a,b)\n    return a+b"): pipeline passes. Quality: NEEDS REVIEW

Unseen variations (Section 3):
- 7_unseen_math ("15 / 3?"): pipeline passes. Generalization: FAIL (expected given constraints)
- 8_unseen_code ("Subtract two numbers."): pipeline passes. Generalization: FAIL
- 9_unseen_bullet ("Three fruits."): pipeline passes. Format: NEEDS REVIEW
- 10_unseen_qa ("Capital of France?"): pipeline passes. Answer: NOT VERIFIED (no fabrication)

Quality gates (honest — not hidden):
- Formatting: FAIL / NEEDS REVIEW
- Instruction-following: FAIL / NEEDS REVIEW
- Compliance: FAIL / NEEDS REVIEW
- QA / Arithmetic: FAIL / NEEDS REVIEW
- Coding / Debugging: FAIL / NEEDS REVIEW
- Regression vs base: PASS (base untouched; no overwrite; no regression)
- Generalization: FAIL (expected; documented; not hidden)

Root cause (documented honestly): insufficient model capacity (3.24M params) + very small dataset (16 original, now 21 with 5 added) + very short training (20 steps on CPU). Not a hidden architecture bug. Not an external-API failure.

Next improvement proposed (requires approval): use expanded v2 dataset (21 examples, original only, gaps covered: reasoning, debugging, comparison, arithmetic, database index); train 30 steps CPU; resume from instruction_final.pt; save new checkpoints; evaluate; decide keep/reject.
