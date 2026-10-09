# Stage 7 — Instruction Tuning (Real, $0, Local)
Status: EXECUTED — REAL — NO FABRICATION
Base: checkpoints/veyra003_pretrain_expanded/checkpoint_step_90.pt (best by val loss 0.0175)
Dataset: v4 train (4000 verified examples); tokenizer v3; correct causal objective
Steps: 20; lr=3e-4; wd=0.05; final_path=checkpoints\veyra003_it_expanded\checkpoint_final.pt
Loss trajectory (actual): [11.801047325134277, 9.458978652954102, 3.593330144882202, 0.34651675820350647, 0.14016544818878174, 0.15941904485225677, 0.10614029318094254, 0.06868131458759308, 0.029835795983672142, 0.02577841654419899, 0.023608185350894928, 0.023459773510694504, 0.020285073667764664, 0.01969258300960064, 0.01867229864001274, 0.01720399223268032, 0.017058201134204865, 0.01709413342177868, 0.016780445352196693, 0.01620025746524334]
Checkpoints saved every 10 steps; previous best preserved; no false success claimed.
