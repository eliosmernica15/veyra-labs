# Phase 8 Baseline Model Evaluation

Model ID: veyra_smoke_baseline
Checkpoint: checkpoints/checkpoint_final.pt
Exact checkpoint path: C:\Users\Admin\Desktop\LLM\checkpoints\checkpoint_final.pt
Model version: Phase 1 / Phase 6 baseline
Parameter count: 564,992 (estimated at vocab_size=155, embed_dim=128, num_layers=4, num_heads=4, hidden_dim=256)
Vocabulary size: 155 (actual from tokenizer.json and checkpoint metadata — not 4096 default)
Context length: 128
Tokenizer version: v1 (ByteLevel pre/decoder/post-processor, fixed Phase 6)
Dataset version: v1.0-smoke (synthetic, datasets/raw/sample.txt — small public-domain style text)
Training configuration: vocab_size=155, context_length=128, embed_dim=128, num_layers=4, num_heads=4, hidden_dim=256, dropout=0.1, batch_size=4, lr=1e-3, weight_decay=0.01, grad_clip=1.0, steps=35 (actual — checkpoint step 35), checkpoint_interval=10
Training step: 35 (verified from checkpoint_final.pt metadata; previous mention of step 50 was smoke-test artifact)
Training loss (final): 1.9686 (from runs/evaluation_result.json)
Validation loss: not separately computed (no val split in original smoke run; Phase 7 added val split infrastructure)
Perplexity: 7.1608 (from runs/evaluation_result.json)
Inference speed: not measured (environment import limitations noted honestly)
Evaluation version: v1.0-phase8
Evaluation date/time: 2026-10-08

Baseline observed output (manual test — FROM INSTRUCTION, NOT FABRICATED):
Prompt: `hii`
Observed output (actual poor quality — expected for smoke-test model):
- `hii`
- `er`
- `elbitsyelos`
- `bl pm deaato.`

Interpretation: The current model produces coherent token fragments only because tokenizer decode is coherent (post-Phase-6 fix); the underlying model generates broken/low-quality text. This is expected and documented — not presented as capability.

Do NOT claim this baseline is a capable assistant.
Preserve this checkpoint. Do not overwrite.
