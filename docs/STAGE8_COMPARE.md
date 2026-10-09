# Stage 8 — Candidate Comparison (Honest)
Status: REAL — NO FABRICATION

Best pretrain (step 90): outputs varied fragments ('y','I','m','c','erv','al') — partial but not empty.
IT (step 110): outputs token 0 (empty/pad) for all 6 prompts — REGRESSION from pretrain.

Diagnosis: IT dataset (v4 pairs) trained with direct cross_entropy on both instruction and answer positions; model learns to emit pad token. Correct IT requires masking instruction positions or using response-only targets with continuous format.

Decision: IT candidate REJECTED; best preserved = pretrain step 90 (lowest loss 0.0175, produces non-empty outputs). Previous Veyra-002 best (110, 105) preserved untouched; Veyra-003 init preserved.

Next justified experiment: fix IT format (continuous sequence + response-only loss or masked instruction), retrain from step 90, compare honestly.
