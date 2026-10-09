# Veyra Labs — Experimental Decoder-Only Transformer (Local, $0)

Status: **Experimental / In Development**. Veyra-004 has not demonstrated reliable, coherent language generation; evaluation outputs are token-ID fragments with rapid EOS and repetition patterns (see reports below). Do not treat as finished assistant.

## Purpose
Build and evaluate a small decoder-only Transformer (VeyraPrime) locally with $0 cost, preserving security (`AGENT_AUTONOMOUS_EXECUTION=False`), documenting all results honestly, and using real only — no fabricated coherence claims.

## Project Structure
- `ml/` — model (`transformer.py`), training loop (`train_loop.py`), tokenizer (`train_tokenizer.py`), data prep (`prepare_expanded.py`)
- `agent/` — agent framework (`core/`, tests, security/prerequisites)
- `apps/` — Studio / API (`app.py`)
- `configs/` — training config (`default.yaml`)
- `datasets/` — processed tokenizer (`tokenizer_veyra004.json`, 4096 vocab), pretraining corpora, dataset manifests
- `checkpoints/` — versioned model weights (local only; not uploaded — see backup report)
- `docs/` — architecture, reports, evaluations, root-cause analyses, backup report

## Dependencies
- Python 3.11+
- PyTorch (CPU; CUDA preferred when available)
- Required packages: see install instructions below (no remote dependency injection)

## Setup (local only)
```bash
# Verify security preserved
python -c "import agent.core.config; print('AGENT_AUTONOMOUS_EXECUTION =', agent.core.config.AGENT_AUTONOMOUS_EXECUTION)"

# Install dependencies (local environment; no external auth required for execution)
pip install torch --index-url https://download.pytorch.org/whl/cpu  # or CUDA if available
# (Additional deps: inspect requirements files if present)
```

## Running
- **API / Studio**: `python apps/studio/app.py` (check `apps/` for exact entry point)
- **Train**: `python -m ml.training.train_loop --data datasets/processed/pretrain_v5_1500.pkl --steps 50 --batch-size 4 --lr 5e-4`
- **Evaluate**: Use `ml/evaluation/evaluate.py` or manual inference via `VeyraPrime` + tokenizer load
- **Data prep**: `python ml/data/prepare_expanded.py`

## Model / Tokenizer
- Best current checkpoint: `checkpoints/veyra004_pretrain_v5/checkpoint_final.pt` (v4 vocab 4096, ~60.2M params, local 690MB, SHA-256 `7aaee496...` — verified, NOT uploaded due to $0/LFS safeguard)
- Tokenizer: `datasets/processed/tokenizer_veyra004.json` (ByteLevel v4, digit/punct preserved)
- Load: `torch.load(path, weights_only=False)`; reconstruct `Config` from saved `config`; `model.load_state_dict`

## Known Limitations (honest)
- Veyra-002 / Veyra-003 / early Veyra-004 outputs show token sequences, not coherent text.
- Instruction-tuning attempts (3 prior) collapsed to EOS (`P(0)≈0.9999`) due to empty/incorrect targets; masked-target format built (`datasets/processed/pretrain_it_masked.pkl`) but full IT not executed (interrupted / stop honored).
- Overfit confirmed: rapid loss drop on fixed datasets at 60M params regardless of diversity; larger/multi-source pretraining needed.
- No claim of finished assistant; no deployment to production without coherent-output verification.

## Key Reports (all verified, not rewritten)
- `docs/VEYRA003_MASTER_REPORT.md` — pipeline + architecture
- `docs/VEYRA004_BREAKTHROUGH.md` — pretraining 50-step evidence
- `docs/VEYRA004_EVAL_V5_DIVERSE.md` — real evaluation (6 prompts, token IDs, non-empty but EOS rapid)
- `docs/VEYRA004_CONTINUATION_SUMMARY.md` — interruption / stop / verified state
- `docs/GITHUB_BACKUP_REPORT.md` — backup verification
- `docs/MASTER_DIRECTIVE_BEFF_2026-10-09.md` — master directive confirmation
- `agent/docs/security_prerequisites.md` — security requirements preserved

## Backup / Restore
- Source + docs + tokenizer + setup code backed to private GitHub repo (see `docs/GITHUB_BACKUP_REPORT.md`)
- Large checkpoints remain LOCAL; restore from local copy with verified hash.
- Clone: `git clone https://github.com/eliosmernica15/veyra-labs.git` (private; auth required)

## Security / Cost
- All computation local CPU; $0.
- `AGENT_AUTONOMOUS_EXECUTION = False` preserved (verified `agent/core/config.py:24`).
- No secrets committed; `.env` excluded; `.gitignore` protects caches / virtualenv / large binaries.
