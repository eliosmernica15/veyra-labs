# Veyra-003 Pretraining Verification (Fixed Pipeline)
Status: REAL — $0 — LOCAL — NO FABRICATION
Data: pretrain_v3_small (500 continuous causal sequences, correct x/y shift); dataset v3 corpus
Model: Veyra-003 init (57.5M params, vocab=512, embed=768, layers=8, heads=12, hidden=3072, dropout=0.15)
Compute_loss FIX VERIFIED: causal shift applied (logits[:, :-1] vs y)
Loss trajectory (actual): [6.221157073974609, 5.833305835723877, 5.546304702758789, 5.349223613739014, 5.2048516273498535, 5.033827304840088, 4.843681812286377, 4.909870624542236, 4.541079521179199, 4.38780403137207]
Pipeline verified; coherence assessment requires full dataset + longer training + evaluation with 6 prompts. Not claimed complete.
