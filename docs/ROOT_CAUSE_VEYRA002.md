# Root-Cause Report — Veyra-002 Fragmented Outputs (Evidence-Based)
Status: VERIFIED — NO FABRICATION — $0 — LOCAL

SOURCE INSPECTION (actual files, not assumed):
- ml/models/transformer.py compute_loss: NO shift of logits vs targets. Assumes x/y already aligned.
- ml/data/prepare_expanded.py: builds (instruction_encode, answer_encode) pairs with rough_encode — not continuous text.
- ml/tokenizer/train_tokenizer.py / tokenizer_veyra002.json: ByteLevel BPE 512 vocab; round-trip tests show digits all -> token 51; punctuation/spacing partially lost.
- datasets/processed/v4/ samples: near-empty token sequences (3-7 non-zero / 64); ~265 duplicates in first 500.
- Checkpoints: BEST_110 (step 110) loads correctly; forward pass runs; outputs token 0 for all 6 prompts.
- Training logs (C-30, C-100): loss 5.9->1.15 and 5.72->0.022 — real reduction; coherence not achieved.

DIAGNOSIS (evidence, not assumption):
1. WRONG TRAINING OBJECTIVE: compute_loss treats x and y as position-aligned, not causal next-token continuation. For decoder-only LM, targets should be x shifted by 1 (or concatenated instruction+response with proper causal mask). Current training teaches model to reproduce answer at same position as instruction, not generate response after instruction.
2. DATA QUALITY: v4 has high duplication, sparse tokens, no continuous pretraining corpus. Instruction tuning needs continuous "instruction -> response" sequences, not isolated pairs.
3. TOKENIZER DEFECT: digits collapse to single token; punctuation/spacing degraded. Prevents precise code/math output.
4. MODEL SCALE / DURATION: ~19.3M params, short context, limited training relative to task complexity.
5. NOT A PIPELINE DEFECTION: load_checkpoint, tokenizer pairing, forward, decode all verified (STEP1). Fix is in objective + data + tokenizer + architecture + duration.

FIX STRATEGY (evidence-based, not speculative):
- Fix compute_loss / data pipeline for causal LM with continuous sequences.
- Build continuous pretraining corpus (diverse text, verified sources, $0).
- Build 10k+ instruction dataset with correct format (instruction + response as continuous sequence; mask instruction if needed for IT, but pretrain on full).
- Redesign tokenizer (v3) to preserve digits, punctuation, code syntax.
- Design Veyra-003 with improved architecture; initialize; train properly (pretrain then IT); evaluate with 6 prompts + held-out.
- Preserve all Veyra-001/002; keep old checkpoints untouched.
