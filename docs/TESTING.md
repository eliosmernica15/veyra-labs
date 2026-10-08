# Testing — Veyra Labs

## Unit tests
```bash
python -m pytest tests/unit/test_model.py -v
```

## Integration tests (requires backend running)
```bash
# Start backend first
python -m services.api.main
# In another terminal
python -m pytest tests/integration/test_api.py -v
```

## Manual smoke test
```bash
# 1. Dataset
python ml/tokenizer/train_tokenizer.py --raw datasets/raw/sample.txt --vocab-size 4096 --output datasets/processed/tokenizer.json

# 2. Data prep
python ml/data/prepare.py --raw datasets/raw/sample.txt --tokenizer datasets/processed/tokenizer.json --output datasets/processed/train.pkl

# 3. Train
python ml/training/train_loop.py --data datasets/processed/train.pkl --steps 50 --batch-size 4 --lr 1e-3

# 4. Load and generate
python ml/inference/generate.py --checkpoint checkpoints/checkpoint_final.pt --tokenizer datasets/processed/tokenizer.json --prompt "The quick brown fox" --max-new-tokens 20

# 5. Evaluate
python ml/evaluation/evaluate.py --checkpoint checkpoints/checkpoint_final.pt --tokenizer datasets/processed/tokenizer.json
```

All tests must pass; failures must be reported honestly.
