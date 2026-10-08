# Training — Veyra Labs

## Overview
Training is performed by `ml/training/train_loop.py` using a real PyTorch optimization loop (AdamW, gradient clipping, cross-entropy loss).

## Commands
```bash
# Train tokenizer
python ml/tokenizer/train_tokenizer.py --raw datasets/raw/sample.txt --vocab-size 4096 --output datasets/processed/tokenizer.json

# Prepare dataset
python ml/data/prepare.py --raw datasets/raw/sample.txt --tokenizer datasets/processed/tokenizer.json --output datasets/processed/train.pkl

# Train model (smoke test: 50 steps)
python ml/training/train_loop.py --data datasets/processed/train.pkl --steps 50 --batch-size 4 --lr 1e-3

# Resume from checkpoint
python ml/training/train_loop.py --data datasets/processed/train.pkl --steps 50 --resume checkpoints/checkpoint_step_10.pt
```

## Key points
- Every loss value is measured (not simulated).
- Checkpoints saved to `checkpoints/` include model weights, optimizer state, config, tokenizer reference, and completed step.
- No hidden external AI dependency. All weights initialized from scratch.
