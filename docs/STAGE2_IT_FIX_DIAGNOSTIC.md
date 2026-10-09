# Stage 2 — Fixed IT Diagnostic (Small, Real)
Status: EXECUTED — REAL — $0
Dataset: it_corrected_400.pkl (9 unique continuous sequences; correct format)
Base: pretrain step 90 (best by val)
Loss trajectory: [10.484159469604492, 7.4223198890686035, 3.844241142272949, 3.3417699337005615, 2.4508888721466064, 1.7375428676605225, 1.3857989311218262, 0.9309536814689636, 0.6930972933769226, 0.43630480766296387]
Purpose: verify pipeline fix (continuous format + real tokenizer + nonempty targets) eliminates token-0 output.
Next: if loss improves and outputs non-empty, scale to full instruction dataset with same format.
