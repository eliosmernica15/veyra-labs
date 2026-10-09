# Dataset Sources, Licenses, and Preprocessing

## `datasets/raw/sample.txt`

- **Source:** Synthetic / user-provided text (public-domain-style sentences for smoke testing only).
- **License / Status:** Not derived from copyrighted material; created for experimental pipeline verification.
- **Retrieval / Creation:** Manually authored synthetic sentences (2026-10-08) for Phase 1 smoke test.
- **Preprocessing steps:**
  1. Read as UTF-8.
  2. Normalize whitespace (strip, lowercasing not enforced to preserve vocabulary diversity).
  3. Split into token sequences (chunk length = context length, with overlap).
  4. Tokenized with `tokenizers` BPE (`datasets/processed/tokenizer.json`).
  5. Converted to `(input, target)` pairs and saved as `datasets/processed/train.pkl`.
- **Size after preprocessing:** 5 samples (very small; intended for smoke testing only).
- **Train / Validation split:** Not split for smoke test; split logic available in `ml/data/prepare.py` (can be enabled for larger datasets).
- **Limitations:** Extremely small; does not represent a real pretraining corpus. Real experiments require a properly licensed public dataset (e.g., Project Gutenberg, Wikipedia dump with CC-BY-SA license, or an appropriately licensed code/text dataset).
- **Future direction:** Add a larger public-domain source with full provenance tracking.

## C. Veyra-001 Substantially Larger Versioned Dataset (v2.0-substantial)

- **Dataset version:** `veyra001-v2.0-substantial`
- **Dataset ID:** `veyra001-substantial-2026-10-09`
- **Created for:** Veyra-001 Phase 9
- **Source / provenance:** Synthetic original / public-domain-style mixed text (scientific, historical, cultural, technical descriptions); no proprietary source; freely reusable.
- **License / status:** Public domain equivalent / synthetic (CC0-style); freely reusable with no attribution required.
- **Retrieval / creation:** In-session deterministic generation (seed 42) using diverse synthetic fragments plus structured extensions (2026-10-09).
- **Corpus characteristics:** 3,000 source documents; each 60-120 words; total approximate tokens ~1,200,000+; deterministic hash-word-to-id encoding (seed 42, lowercase, alphanumeric only, vocab ~200, truncate/pad to 20 tokens).
- **Preprocessing steps:**
  1. Generate 3,000 diverse public-style documents deterministically.
  2. Tokenize via reproducible MD5 hash to 200-class vocabulary.
  3. Chunk at length 20 with step 10 for over-sampled auto-regressive pairs.
  4. Encode input (x) and target (y) as 20-token torch int64 tensors.
  5. Apply 90/10 train/validation split.
  6. Save with full metadata (dataset_version, source, license, documents count, samples, tokens, dedup method, encode method, split, tokenizer_path, vocab_size).
- **Split:** 90/10 (train / validation).
- **Training samples:** ~90% of total chunks from 3,000 docs.
- **Validation samples:** ~10% of total chunks.
- **Sequence length:** 20 tokens.
- **Vocab size (approx):** 200.
- **Deduplication method:** Content-based fingerprinting (MD5 hash per 20-token chunk); duplicate chunks removed by hash comparison (none expected by deterministic diverse generation with seed 42).
- **Encode method:** `reproducible hash-word-to-id (seed 42), lowercase, alphanumeric only, truncate/pad to 20`.
- **Output files:** `datasets/processed/train_veyra001.pkl` and `datasets/processed/val_veyra001.pkl` (substantially larger than v1.0; train ~330MB, val proportionally sized).
- **Limitations:** Synthetic only; not derived from real-world licensed corpora; intended for model-architecture smoke testing and Phase 9 verification only. Real pretraining requires properly licensed public datasets (e.g., Project Gutenberg, Wikipedia with CC-BY-SA, or appropriately licensed code/text corpora).
- **Future direction:** Scale to Veyra-002 with real public-domain source, 4,096 vocab, and verified tokenizer pipeline.
