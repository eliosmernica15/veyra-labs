# Veyra Labs — Backup Manifest (before commit/push)
Project path: C:\Users\Admin\Desktop\LLM
Branch: master (before backup commit)
Baseline commit: 176e723 Phase 3: Agent framework architecture
Current state: working tree has unstaged modifications (previous Veyra-004 work); all preserved.
Configuration review: `.env` was present in historical commit `ec1eb318733b79ea5bbd114d6220be101325c070` and is ignored/absent from the current tracked tree. A value-safe comparison against `.env.example` confirmed that `VEYRA_BACKEND_URL` and `VEYRA_API_KEY` were only development placeholders; the other differences were training settings. Repository code does not consume `VEYRA_API_KEY`. No provider-issued credential was found, and no rotation is needed.
History remediation: shared history was not rewritten. The historical file remains in private repository history, but contains no live credential based on the verified comparison.
Checkpoint upload decision: NO — LFS free quota / $0 safeguard not verifiably safe; checkbox not confirmed; best checkpoint (690MB) remains local with SHA-256 verified.
Test results: existing tests in agent/tests/ preserved in commit; not modified for backup; no fabrication of success.
Included directories (intended): agent/, ml/, apps/, configs/, docs/, datasets/processed/tokenizer_*.json, .gitignore, README.md, docs/GITHUB_BACKUP_REPORT.md (will create after push verification).
Excluded (intended): .env, __pycache__/*.pyc, *.pt checkpoints, venv/, .claude/, .agent_memory/, logs/temp_*, build/, dist/.
Dataset / tokenizer versions: tokenizer_veyra004.json (4096 vocab, verified); dataset manifests (v3, v4, v5_diverse) preserved as docs/ and preparation code.
Restore: clone private repo; restore source/docs; reload checkpoints from local copy with hash verification.
