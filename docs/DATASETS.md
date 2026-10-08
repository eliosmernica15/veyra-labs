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
