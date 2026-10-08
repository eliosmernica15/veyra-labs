# Inference — Veyra Labs

## Overview
Inference loads a real checkpoint (`checkpoints/*.pt`) using `ml/training/checkpoint.load_checkpoint()`, then runs autoregressive generation.

## Commands
```bash
python ml/inference/generate.py --checkpoint checkpoints/checkpoint_final.pt --tokenizer datasets/processed/tokenizer.json --prompt "The quick brown fox" --max-new-tokens 20 --temperature 1.0
```

## Key points
- Generation loads actual model weights.
- Temperature, top-k, and top-p sampling are implemented.
- If using an untrained or randomly initialized checkpoint, output will be random tokens — clearly labeled by the model version/step in the response.
