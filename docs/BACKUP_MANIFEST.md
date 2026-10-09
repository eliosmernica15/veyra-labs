# Veyra Labs — Backup Manifest (before commit/push)
Project path: C:\Users\Admin\Desktop\LLM
Branch: master (before backup commit)
Baseline commit: 176e723 Phase 3: Agent framework architecture
Current state: working tree has unstaged modifications (previous Veyra-004 work); all preserved.
Secrets review: .env found (keys: VEYRA_BACKEND_URL, VEYRA_API_KEY, etc.); .env EXCLUDED from commit; not printed; .gitignore updated.
Secret-bearing history: not rewritten (no exposed secrets in existing commit 176e723 per inspection); safe to push current source.
Checkpoint upload decision: NO — LFS free quota / $0 safeguard not verifiably safe; checkbox not confirmed; best checkpoint (690MB) remains local with SHA-256 verified.
Test results: existing tests in agent/tests/ preserved in commit; not modified for backup; no fabrication of success.
Included directories (intended): agent/, ml/, apps/, configs/, docs/, datasets/processed/tokenizer_*.json, .gitignore, README.md, docs/GITHUB_BACKUP_REPORT.md (will create after push verification).
Excluded (intended): .env, __pycache__/*.pyc, *.pt checkpoints, venv/, .claude/, .agent_memory/, logs/temp_*, build/, dist/.
Dataset / tokenizer versions: tokenizer_veyra004.json (4096 vocab, verified); dataset manifests (v3, v4, v5_diverse) preserved as docs/ and preparation code.
Restore: clone private repo; restore source/docs; reload checkpoints from local copy with hash verification.
