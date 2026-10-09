# Phase 8 — Remote GPU Training Preparation

Not executed: no server rented or provisioned.
Not executed: no paid cloud resources started.

Required environment (estimate):
- Python 3.11+
- PyTorch with CUDA support (torch>=2.0 recommended)
- tokenizers library (0.22.2+)
- numpy, pickle, pathlib
- GPU with at least 4GB VRAM for small experiments (~565k params, vocab=155, context=128)
- For substantial training (larger vocab/config): estimate 8-16GB+ depending on config; use mixed_precision and gradient accumulation to reduce memory

Launch instructions (same code):
1. Transfer datasets/processed/ (tokenizer.json, train.pkl, val.pkl, eval_fixed.pkl)
2. Transfer configs/training/default.yaml (or custom config)
3. Copy ml/ source (same pipeline)
4. Run: python -m ml.training.train_loop --data datasets/processed/train.pkl --steps 50 --batch-size 4 --accumulation-steps 1 --mixed-precision
5. Resume: python -m ml.training.train_loop --resume checkpoints/checkpoint_step_N.pt
6. Evaluate: python -m ml.evaluation.evaluate --checkpoint checkpoints/checkpoint_final.pt --data datasets/processed/eval_fixed.pkl

Storage: dataset + tokenizer ~10MB; checkpoints ~7MB each at small scale.
Experiment tracking: experiments/ directory with metadata.json per run.
No cloud credentials saved. Activation requires deliberate user action.
