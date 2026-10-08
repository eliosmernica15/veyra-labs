# Dataset Directory

## `datasets/raw/`
- User-provided or downloaded raw text files.
- All sources must be documented with license/provenance.
- Do not include private, restricted, or proprietary data.

## `datasets/processed/`
- Processed outputs (`tokenizer.json`, `train.pkl`, etc.).
- Reproducible from `datasets/raw/` using `ml/data/prepare.py` and `ml/tokenizer/train_tokenizer.py`.

## Current contents (`sample.txt`)
- Synthetic smoke-test text (author's original sentences).
- Not a real large-scale training corpus.
- See `docs/DATASETS.md` for provenance and limitations.
