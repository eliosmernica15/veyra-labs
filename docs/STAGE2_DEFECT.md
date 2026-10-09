# Stage 2 — Artifact Defect Found (Real, Not Hidden)
Veyra-003 init (checkpoints/veyra003_init/init.pt): vocab=512, embed=768, layers=8, heads=12, hidden=3072, dropout=0.15, context=512 — CORRECT
Veyra-003 pretrain 10-step (checkpoints/veyra003_pretrain_small/checkpoint_final.pt): config shows vocab=512, embed=128, layers=4, heads=4, hidden=256, context=128 — WRONG
Root: train_loop creates Config from dataset vocab_size when initializing from scratch; ignores architecture from init checkpoint.
Fix: modify training to load architecture from init/model_path; save correct config. Retrain Veyra-003 correctly.
Previous Veyra-001/002 untouched; this defect only affects Veyra-003 training path.
