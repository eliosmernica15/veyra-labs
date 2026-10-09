# Veyra-003 Evaluation — 10-step pretrain verification (real inference)
Status: REAL — $0 — LOCAL — NO FABRICATION
Checkpoint: checkpoints/veyra003_pretrain_small/checkpoint_final.pt (step 10, continuous causal, loss 4.39)
Tokenizer: tokenizer_veyra003.json (v3, 512 vocab; digit preservation still limited — documented)
Actual outputs: partial (next tokens vary; coherence not verified as pass — quality gate open)
Pipeline fix verified: compute_loss shift applied; data format continuous; training runs correctly.
Next: continue with larger pretrain dataset + instruction tuning + evaluation; preserve all Veyra-001/002.
