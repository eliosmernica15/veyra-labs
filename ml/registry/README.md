# Model Registry — Phase 8

Types:
- smoke_model: current baseline (checkpoint_final.pt, step 35, vocab=155)
- base_pretrained: future — trained on larger dataset
- instruction_tuned: future — separate stage
- coding_specialized: future — separate stage
- experimental: future — any variant

Every checkpoint must contain:
- model_state_dict
- optimizer_state_dict (if resume needed)
- step
- optimizer_steps
- tokens_seen
- config (vocab, context, embed, layers, heads, hidden)
- tokenizer_path
- vocab_size
- dataset_version
- training_config (from default.yaml or custom)
- hardware_info
- wall_time_s
- best_checkpoint_path / best_val_loss (if evaluated)

Metadata distinguishes model types; improves reproducibility.

## Registry Entries — Updated 2026-10-09

### Veyra-000 (Baseline — Preserved)
- Model ID: Veyra-000
- Version: veyra_smoke_baseline
- Checkpoint: checkpoints/checkpoint_final.pt (6,826,181 bytes; md5 c75c446f5bed615059565cf27aaea566)
- Step: 35 (verified from evaluation_result.json; step-50 file is separate artifact)
- Params: 564,992 | Vocab: 155 | Context: 128
- Tokenizer: datasets/processed/tokenizer.json (ByteLevel v1, fixed Phase 6)
- Dataset: datasets/raw/sample.txt (v1.0-smoke)
- Status: PRESERVED. Not overwritten. Identity doc: ml/registry/identities/Veyra-000.md
- Lineage / Child entry: Veyra-001 (Phase 9 smoke verification; checkpoints/veyra001_smoke.pt step 5, 3,239,424 params, vocab 200) — registered FROM this baseline; baseline file untouched.
- Note: Phase 7 code edits (grad accumulation, tracking) applied to train_loop.py AFTER original creation; original file not overwritten.

### Veyra-001 (Phase 9 — Verification Smoke / Registered Identity — Separated from Baseline)
- Model ID: Veyra-001
- Registry version: v1.0
- Parent / Lineage: Veyra-000 (checkpoint_final.pt, step 35, 564,992 params, vocab 155) — Veyra-001 configured/trained FROM Veyra-000 baseline; NOT replacing it
- Checkpoint (verification): checkpoints/veyra001_smoke.pt (38,925,599 bytes; step 5; verified load; resume verified)
- Reference baseline (preserved, NOT overwritten): checkpoints/checkpoint_final.pt (6,826,181 bytes; md5 c75c446f5bed615059565cf27aaea566; step 35)
- Step (actual smoke): 5 (verified from smoke run; not step 35 baseline)
- Params: 3,239,424 | Vocab: 200 | Context: 128 | Embed: 256 | Layers: 4 | Heads: 4 | Hidden: 1024
- Training config (smoke verification): optimizer AdamW, lr 1e-3, batch 2, accum 1, mixed_precision false, grad_clip 1.0, weight_decay 0.01, steps=5, interval=10, vocab_size=200
- Dataset: datasets/processed/train_veyra001.pkl / val_veyra001.pkl (v1.0-substantial / v2.0-substantial synthetic; 3,000 docs source; seed 42)
- Tokenizer: datasets/processed/tokenizer_veyra001.json (v1.0 / v2.0-4096 aspirational; vocab 1392 chosen at 4096 target; 200 used for smoke init)
- Quality: generation FAIL / smoke-gibberish (documented honestly); tokenizer coherent PASS; agent framework PASS; milestone unchanged
- Status: VERIFICATION COMPLETE — substantial remote-GPU pretraining NOT executed (no CUDA; CPU-only Windows 11 Pro); baseline preserved
- Cost: $0.00
- Security preserved: AGENT_AUTONOMOUS_EXECUTION=False; workspace-only; no external compute
- Identity doc: ml/registry/identities/Veyra-001.md
- Lineage statement: Veyra-001 -> parent Veyra-000 baseline (checkpoint_final.pt); identity upgrade documented; no weight overwrite performed.
- Verification: baseline md5 preserved (c75c446f...); smoke checkpoint verified (load + resume + step 5); no write to checkpoint_final.pt.

## Preservation Rules
- Baseline checkpoint must never be overwritten by registry updates.
- New registry entries must reference preserved checkpoints by path + checksum.
- All identity docs must explicitly state overwrite status (NO) and baseline separation.
