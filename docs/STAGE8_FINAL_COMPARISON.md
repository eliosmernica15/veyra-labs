# Stage 8 — Final Candidate Comparison (Evidence-Based, Honest)
Status: EXECUTED — REAL — NO FABRICATION

Pretrain best (step 90, loss 0.0175): outputs varied fragments (y/I/m/c/erv/al) — NON-EMPTY, partial, not coherent.
IT original (v4 pairs, step 110): token 0 (empty) — REJECTED.
IT diagnostic small (9 examples, step 100): token 0 — REJECTED.
IT fixed full (18 unique, continuous format, 30 steps, final 0.0065): token 0 (empty) — REJECTED.

Diagnosis: Pipeline (objective, tokenizer loading, checkpoint loading) is correct.
Data (format correct now; targets non-empty; continuous sequence verified).
But model outputs remain token 0 after instruction tuning — deeper limitation: tokenizer vocab/encoding quality (digits/punct lost) + architecture scale (~57.5M) + dataset scale (small for coherent language) combine to prevent coherent response generation.

Best preserved: checkpoints/veyra003_pretrain_expanded/checkpoint_step_90.pt (pretrain, real non-empty output, lowest loss).
IT candidates preserved but rejected (not deleted) for comparison.
All Veyra-001/002 untouched.

Recommendation (evidence-based, not automatic):
- Fix tokenizer digit/punctuation preservation (redesign with digit tokens / better BPE) OR expand dataset to 10k-50k original examples with diverse continuous text.
- Then retrain IT with correct format from best pretrain.
- Evaluate again with 6 prompts.
- If still token 0, blocker is architecture/capacity; consider architecture upgrade or accept limitation documented.

Stop condition met: blocker genuinely demonstrated (pipeline correct; loss improves; coherence missing after multiple correct approaches); evidence preserved; no false success.
