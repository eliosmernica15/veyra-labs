# Stage C Corpus and Training Readiness

**Assessment date:** 2026-10-10
**Status:** Corpus preparation and training-loop regressions were verified; the bounded 10-step CPU pilot was evaluated; and hosted CPU baseline verification completed. Follow-up source-integrity checks now reject unpinned or changed source files before preprocessing. No further training is underway; see [Stage D](./STAGE_D_COMPUTE_AND_PILOT.md) for hosted results.

## Repository preservation and security

- The reviewed Stage B/C and hosted-verification changes were selectively committed and merged through PRs #1 and #2. A separate private prerelease holds verified copies of the v5 checkpoint, tokenizer, all three CPython split files, provenance, and the pinned PSF license notice; no `.env` or credentials were uploaded.
- Unrelated local modifications and untracked artifacts remain preserved and were not staged or discarded as part of the reviewed commits.
- `.env` is ignored and absent from the current tracked tree. Historical commit `ec1eb318733b79ea5bbd114d6220be101325c070` contains it, but a value-safe comparison confirmed its `VEYRA_BACKEND_URL` and `VEYRA_API_KEY` entries exactly match the development placeholders in `.env.example` (`localhost` and `local-dev-key`); the other differing entries are non-secret training settings. The application code does not consume `VEYRA_API_KEY`. No provider-issued credential was present, so no credential rotation is needed. Git history was not rewritten.
- `AGENT_AUTONOMOUS_EXECUTION` remains `False`.
- The preserved Veyra-004 v5 checkpoint is unchanged: 722,729,765 bytes; SHA-256 `7aaee496c5adff3f652a30d67b3bf12dc5438505364ea5a7582a869b43b2110b`. Its verified configuration is vocab 4,096, context 512, embedding 768, 8 layers, 12 heads, hidden size 3,072, step 100. Its tokenizer path is `datasets/processed/tokenizer_veyra004.json`; the tokenizer digest is independently recorded and checked against the data artifact, as the checkpoint itself does not carry a tokenizer SHA-256 field.

## Rights review and source decisions

### Accepted for this local corpus

**CPython official documentation, tag `v3.14.7`, commit `823f0323ee6ec1402088b73bce1a38473cac36dc`.**

- The pinned upstream `Doc/license.rst` identifies the PSF License Version 2 for Python and its documentation. Its terms grant a worldwide, royalty-free license to reproduce, prepare derivative works, distribute, and otherwise use the documentation, subject to preserving the PSF license and copyright notices. Documentation examples, recipes, and code are additionally dual-licensed under Zero-Clause BSD.
- Source license: [Python documentation license](https://docs.python.org/3/license.html); pinned evidence: [CPython `Doc/license.rst`](https://github.com/python/cpython/blob/823f0323ee6ec1402088b73bce1a38473cac36dc/Doc/license.rst).
- The locally acquired archive is 34,863,910 bytes, SHA-256 `4d91279383772be3f216bd7c44fdbd45f68efe30e2ea2c16ad062348666927aa`. The pinned recursive tree SHA-256 is `6ef5e62adcb3114420680e8702b07357237b14cd7a4fa178ae6c04e420af6ab2`. All 540 selected `.rst` files were checked against Git blob hashes from that pinned tree before extraction.
- Retain the PSF attribution and notice with any redistribution. Legal review is still needed before distributing model artifacts or datasets, especially to determine how the corpus license, embedded examples, and notices apply to those artifacts. This is an initial licensed technical-document corpus, not a general-language corpus.

### Rejected or not acquired

- **WikiText-103:** rejected; no data artifact was downloaded. The dataset card describes CC BY-SA 4.0, while repository/API metadata identifies CC BY-SA 3.0 and GFDL; the card also has incomplete provenance fields. Resolve authoritative licensing and attribution obligations before reconsideration.
- **Wikisource candidate, “The Tell-Tale Heart”:** not acquired because page-content requests returned HTTP 429. The work's edition/jurisdiction status and the page's CC BY-SA obligations remain unresolved; no text entered the corpus.
- **Project Gutenberg and Standard Ebooks candidates:** not acquired. The investigated terms and jurisdiction-specific public-domain cautions were not sufficient to approve a specific collection for this pipeline.
- Older project corpora lacking a source-level rights manifest are not accepted into this Stage C dataset. No instruction-response targets were acquired or mixed with continuous text.

The machine-readable source decisions and provenance are in [the source research manifest](../datasets/source_research_manifest.json). The acquired source files and per-file records are in `datasets/raw/cpython-3.14.7-docs/`; the acquisition/verification entry point is [collect_cpython_docs.py](../ml/data/collect_cpython_docs.py).

## Corpus construction and measured quality

The reproducible preprocessing implementation is [prepare_licensed_corpus.py](../ml/data/prepare_licensed_corpus.py). Before reading a document, it verifies the file against a declared SHA-256 or pinned Git blob SHA-1; missing pins and content mismatches fail the build rather than silently substituting text. It then normalizes UTF-8/BOM, line endings, and Unicode NFC; rejects malformed, empty, control-character, and under-20-word documents; removes exact duplicates and near duplicates using a bottom-128 five-word-shingle estimate with a word-count-ratio gate; and assigns whole documents to seeded, disjoint train/validation/test splits. No source text was repeated to inflate counts.

### Follow-up: source-file integrity gate

The CPython collector now records a SHA-256 for every extracted document in addition to its upstream Git blob SHA-1. Corpus preparation checks every supplied pin against the exact source bytes before decoding, cleaning, deduplication, or tokenization. Manifests from Git sources may pin the Git blob identity; other sources must provide a lowercase SHA-256. Missing, malformed, or mismatched pins stop the build with an explicit error. The previously acquired CPython manifest remains compatible because each document already contains its pinned Git blob SHA-1; this code change does not rewrite the raw manifest or existing split files.

Regression coverage verifies both Git blob and SHA-256 pins, rejects manifests without either pin, and stops if a source document changes after the manifest is prepared. The focused Stage B/C suites pass **20 tests** (`test_stage_b_c_data.py` and `test_training_validation.py`). No new source was acquired, no corpus artifact was rebuilt, and no pretraining or instruction tuning was run in this follow-up.

The accepted local source set contains:

- **540** hash-verified source documents; **537** eligible documents.
- **3** excluded: two under-20-word documents and one containing disallowed control/NUL content.
- **0** exact duplicates removed; **0** near duplicates removed.
- **1,684,239** words; **23,978** unique words; corpus type-token ratio **0.01424**; mean per-document type-token ratio **0.31740**; mean unique-word-trigram fraction **0.85580**; Latin-letter fraction **0.9999927**.
- These statistics measure script and lexical variety, not correctness or general linguistic quality. The technical subject matter remains narrow; the corpus does not demonstrate coherent assistant behavior.

### Checkpoint-compatible split artifacts

The context-512 output matches the preserved Veyra-004 checkpoint dimensions. Tokenizer: `datasets/processed/tokenizer_veyra004.json`, vocabulary 4,096, SHA-256 `47ccdfb870d203c002c65c64e199aeb0ec7b36fc9a91e2826fd2c7d9f0456c4d`. Seed: 42.

| Split | Documents | Token count (includes per-document EOS; excludes batch padding) | Supervised targets (`y != -1`) | Samples | File SHA-256 | Canonical content SHA-256 |
|---|---:|---:|---:|---:|---|---|
| Train | 429 | 5,049,389 | 5,048,960 | 10,070 | `d2aae57b2953d0e8e10878350f496bd3dff3193d33c7b0af9ed774ad05b00a49` | `a997a011041334eca2cf2d8e3503dbdc31e383ac4e71fd794cb5572d4f66f611` |
| Validation | 54 | 438,043 | 437,989 | 883 | `1106bb2fd22cbfa6325fb52ea34194262d09cf306355b3338e3add88410123c3` | `d420401488efc0b32de9faec36bb6a9a5c147cda7c63e83464dc407fb029be50` |
| Test | 54 | 601,913 | 601,859 | 1,199 | `ca7f8c846ae34ac89541dee0761ebb11e63a6e0732ab1e428638e1f10e029891` | `3c0ddba4111a21db62ae946645fdaf13c2f9a4587dafd38d5721c9b0ee8f6d79` |

The total is **6,089,345 tokenizer tokens** and **6,088,808 supervised targets**. The split assignments are by document and do not overlap. Each `.pkl` file SHA-256 is recorded in `provenance.json` and was rechecked against the file. Tensor pickle byte hashes can differ across independent builds; the canonical content SHA-256 is calculated from stable metadata plus canonical little-endian input/target token IDs. The reproducibility test checks that this content hash, document membership, and tensor content repeat for the same input, tokenizer, seed, and settings.

The context-512 split artifacts and detailed counts are in [the processed corpus directory](../datasets/processed/cpython_docs_3_14_7_v4_ctx512_seed42/). An earlier context-128 variant is preserved separately; neither output overwrites the other.

## Training-readiness corrections

[train_loop.py](../ml/training/train_loop.py) now:

- Evaluates validation data in `eval()` and `no_grad()` mode, aggregates loss weighted by non-ignored target tokens, then restores the prior model mode. Evaluation does not update weights.
- Requires distinct train/validation data files, correct declared split identities, matching vocabulary/context/tokenizer path and tokenizer SHA-256, and disjoint normalized document hashes.
- Validates inputs and target IDs; counts only labels where `y != -1` as meaningful tokens, including across gradient-accumulation microbatches.
- Weights accumulated mean losses by supervised-token counts so padding does not distort the optimization-step mean.
- Verifies the checkpoint's tokenizer path and, when present, tokenizer digest; verifies the dataset digest against the actual tokenizer file and checks vocabulary size.
- Records train/validation artifact hashes, validation loss history, optimizer steps, and meaningful tokens in candidate checkpoints; refuses to overwrite existing step or final checkpoint files.

The model loss uses `ignore_index=-1` and mean cross-entropy over active labels. Stage B's response-only target preparation, one-time causal alignment, EOS handling, and checkpoint/tokenizer pairing regressions remain covered by the focused suite.

## Validation results

Command:

```text
.venv\Scripts\python.exe -m pytest tests\unit\test_stage_b_c_data.py tests\unit\test_training_validation.py -q
18 passed
```

The tests cover rights/license gates, source blob verification and corruption rejection, filtering, exact/near deduplication, language metrics, repeatable split membership/content, portable tokenizer paths, response-target masking, validation mode and loss weighting, no validation weight mutation, padding-excluded token counts, split/tokenizer mismatch rejection, and exclusive checkpoint output.

Intermediate test runs exposed fixture assumptions that were corrected: stricter near-duplicate filtering excluded overly similar fixture documents, and the training fixture initially named a tokenizer file that did not exist. A later byte-for-byte repeat-build assertion also failed; because tensor pickle bytes are not a stable content identity, the pipeline now records both the actual file SHA-256 and a canonical logical-content SHA-256. The final focused run passed all 18 tests.

Pylance diagnostics report no issues in the modified corpus pipeline, training loop, or new training-validation tests. The existing Stage B/C test file has four low-severity unused lambda-parameter warnings unrelated to the changed behavior.

Signature compatibility analysis also found two legacy call sites in the root and archived Kaggle experiments that pass string paths to the `Path`-typed training API. They are not used or modified here: they are cloud-oriented historical scripts, outside the local-only training path. Do not execute them for this project.

The training-loop unit test executes a single optimizer step against a tiny synthetic model in a temporary directory. After readiness validation, a bounded 10-step CPU-only Veyra pretraining pilot was also run on the accepted train split; its result and actual generation evidence are in [the Stage D compute and pilot report](./STAGE_D_COMPUTE_AND_PILOT.md). No instruction tuning was launched. The pilot's training and validation losses decreased, but its outputs remained incoherent API-document fragments. It did not pass the assistant-quality gate.

## Further laptop training is paused

The 10-step pilot took approximately 11.4 minutes on the CPU. Given the user's report that laptop compute is overwhelming the machine, no follow-on training is proposed on this laptop. The user later explicitly authorized hosted compute. A private GitHub artifact release has been created, and the manual CPU-only baseline-verification workflow completed successfully: 19 focused tests passed and the preserved model's baseline evaluation/generation was recorded without changing weights. See the Stage D report for results. This does not mean training was run remotely.

## Remaining blockers and human decisions

1. No credential remediation remains for the historical `.env`: its secret-named entry is only the documented development placeholder. Keep the real local `.env` ignored; if a real key is later configured for another service, issue and manage it there rather than committing it.
2. Obtain human/legal advice on preserving PSF notices and how training derivatives, datasets, and any future model/checkpoint distribution should be handled.
3. Obtain more independent, rights-cleared domains before treating this narrow Python-document corpus as sufficient for general language modeling. Continue to exclude unresolved sources rather than weakening the gate.
4. The reviewed code, tests, and reports have been selectively committed, pushed, and merged; unrelated worktree artifacts remain local.
5. Veyra-004 remains incoherent on fixed and unseen prompts, despite a lower held-out technical-document loss after the CPU pilot. The hosted CPU workflow is for verification, not a claim of improved language quality or authorization to repeat the rejected pilot unchanged.
