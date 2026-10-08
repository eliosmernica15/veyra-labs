# Veyra Labs — Phase 1 Implementation Plan (Updated for Python-First Stack)

## Confirmed architecture change
- No TypeScript / React / Vite / Node.js for application code.
- Streamlit (`streamlit`) replaces the previous `apps/studio` React app.
- Python CLI (`click` or `argparse`) replaces previous TypeScript CLI.
- All application logic in Python.

## Phase 1 steps (in order)
1. Model architecture (`ml/models/transformer.py`) — decoder-only Transformer, configurable dims.
2. Tokenizer (`ml/tokenizer/train_tokenizer.py`) — train BPE from raw text using `tokenizers` library.
3. Data pipeline (`ml/data/prepare.py`) — load raw text, split, tokenize, save processed.
4. Training loop (`ml/training/train_loop.py`) — real PyTorch optimization, loss logging, gradient clipping, checkpointing.
5. Checkpoint system (`ml/training/checkpoint.py`) — save/load model + optimizer + config + tokenizer reference.
6. Inference (`ml/inference/generate.py`) — load checkpoint, autoregressive generation with temperature/top-k/top-p.
7. Evaluation (`ml/evaluation/evaluate.py`) — perplexity, validation loss, smoke tests.
8. Backend (`services/api/main.py`) — FastAPI endpoints (health, system, models, checkpoints, training, generate, evaluate, logs).
9. Studio (`apps/studio/app.py`) — Streamlit interface (overview, models, training, chat, evaluation, logs).
10. CLI (`apps/cli/veyra.py`) — Python CLI with basic commands (`status`, `models`, `train`, `chat`, `eval`).
11. Tests (`tests/unit/test_model.py`, `tests/integration/test_api.py`) — real test assertions.
12. Update `docs/` (TRAINING.md, INFERENCE.md, API.md, TESTING.md).

## Hardware-appropriate model config (preserved from Phase 0)
- ~2M params, 4 layers, 128 embed dim, 4 heads, context 128, vocab 4096.
- CPU device (`torch.device('cpu')`).
- Batch size 4.
- Smoke-test training: 50–100 steps.
- Checkpoint every 10 steps.

## Testing requirements (mandatory per master prompt)
- Backend starts.
- Studio connects to backend.
- Model instantiated with random weights.
- Tokenizer encodes/decodes.
- Tiny dataset processed.
- At least one real training step updates params.
- Loss measured correctly.
- Checkpoint saved and reloaded.
- Reloaded model generates text.
- Training resumes from checkpoint.
- Invalid requests return errors.
- UI displays real training status.
- Chat uses selected checkpoint.
- Tests verify core behavior.
