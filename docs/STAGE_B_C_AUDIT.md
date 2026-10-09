# Stage B/C Audit — 2026-10-10

## Verified repository and security state

- Local `master` and remote `master` both point to `b5c497fa67adf8fd9a0a5b35ffb9a8e6812d8bc7`; the remote repository is private.
- The worktree contains unrelated modified and untracked artifacts. They were not reset, cleaned, overwritten, or staged indiscriminately. Only the reviewed Stage B/C source, tests, documentation, research manifest, and `.env` index removal are in scope for the security commit.
- Correction to the previous audit: `.env` was tracked in the index and in `HEAD` at `b5c497fa67adf8fd9a0a5b35ffb9a8e6812d8bc7`, despite `.gitignore`. It also appears in historical commit `ec1eb318733b79ea5bbd114d6220be101325c070`. The remediation removes it from the latest tracked tree without deleting the local ignored file or rewriting history. Earlier copies remain in Git history.
- Secret values were not printed or included in the new changes. The local `VEYRA_BACKEND_URL` resolves to `localhost`; repository code does not consume `VEYRA_API_KEY`, and no issuing provider was identified. No credential has been rotated. Manual action: identify the issuer privately, revoke the exposed key in that issuer's management interface, issue a replacement if still needed, and update the local `.env` without sharing it in chat. If it is only a local-service key, rotate it in that service's private configuration.
- The repository is private. No history rewrite, force-push, hosted inference, cloud compute, or paid service was used.
- The local v5 checkpoint is 722,729,765 bytes, SHA-256 `7aaee496c5adff3f652a30d67b3bf12dc5438505364ea5a7582a869b43b2110b`. No checkpoint was overwritten and no candidate training run was performed. The focused tests do run five optimization steps on a tiny test-only model in a temporary directory.

## Stage B — Instruction-tuning diagnosis

- `tokenizer_veyra004.json` has 4,096 tokens and maps ID 0 to `</s>`. The v5 checkpoint at step 100 loads strictly with its saved 4,096-token, 768-dimensional, 8-layer configuration.
- Actual next-token probabilities on the six retained prompts were not EOS-dominated. For example, the top token probability was 0.996645 for token 823 on `What is 2 + 2?`, while the EOS probabilities across all six tested prompts were at most 0.000052. The predictions are still not evidence of coherent responses; they are isolated next-token measurements.
- The current `pretrain_it_masked.pkl` has 8 examples, each with input length 16 and target length 32. Every target begins with the encoded prompt; 18–26 target entries per sample are ID 0, and there are no ignored (`-1`) labels. It is neither response-only masking nor a shape accepted by `compute_loss`.
- The prior `compute_loss` chose between two implicit alignment modes based only on sequence lengths. The implementation could silently use inconsistent shift conventions. The training loop also resumed optimizer state from the base model and did not validate the tokenizer/dataset contract.
- `prepare_instruction_data.py` was only a smoke-test stub (and referenced `torch` without importing it); it did not produce the masked dataset.
- Both actual tokenizer files tested (`tokenizer_veyra004.json` and `tokenizer.json`) return the same ordinary prompt IDs with and without `add_special_tokens=False`; neither automatically appended EOS in the tested prompt. The explicit no-special-token setting is retained so generation remains safe if a tokenizer later gains a post-processor.

The updated data preparation format reads JSONL records with explicit `instruction`, `response`, `source`, `license`, and `target_provenance` fields. It groups equal prompts into a single split, shifts labels exactly once, supervises response tokens plus EOS only, and uses `-1` for prefix and pad positions. The loss now requires aligned input/target tensors and ignores only `-1`. The training entry point validates the checkpoint/dataset dimensions, starts a fresh optimizer for fine-tuning, and refuses to overwrite existing candidate files.

Generation now loads the exact tokenizer recorded by the checkpoint, switches the model to evaluation mode, passes raw prompt tokens, and ends each sequence at EOS (padding already-finished batch rows where applicable). The API and standalone inference wrapper use the same tokenizer/EOS contract.

After applying that path, the actual v5 checkpoint (step 100), seed 42, temperature 1, top-k 50, top-p 0.9, 32-token cap produced these exact continuations:

| Prompt | Continuation | EOS within 32 tokens |
|---|---|---|
| `hi how are you` | `models - \`GET /api/training/prepare-data\` — Active training setting-data\` — Not implemented in` | No |
| `What is 2 + 2?` | `- \`GET /api/system\` — Hardware / environment info - \`GET /api/models\` — Available` | No |
| `Explain what Python is in two sentences.` | `AET /api/training/prepare-data\` — Not im Active trainingcripts directly) - \`POST /api` | No |
| `Reply with exactly three bullet points about computers.` | `s - \`GET /api/training/config-data\` — Not implemented in Phase 1 (use CLI scripts directly)` | No |
| `Write a Python function that adds two numbers.` | `Amodels\` — A Hardware / environment info - \`GET /api/models\` — Available checkpoints - \`GET` | No |
| `Fix this code: def add(a, b) return a + b` | `s - \`POST /api/config\` — Active training settings - \`POST /api/training/prepare-` | No |

These outputs are still incoherent project-document fragments, not useful responses. The exact outputs are recorded to distinguish an EOS/termination issue from the remaining data/learning failure.

## Stage C — Corpus audit and gate

The existing `datasets/pretrain_text` directory contains five corpora but no source/rights manifest. The v5 file has 1,656 unique non-empty lines and 49,544 v4-tokenizer tokens; its opening content is project API documentation, so its line uniqueness does not establish independent source diversity or language quality. The v3 expanded file has 846 duplicate-line excess among 3,033 non-empty lines; the v4 file has the same 846 repeated-line excess among 33,033 lines. The current sources therefore do not pass a provenance-verified pretraining gate.

`ml/data/prepare_licensed_corpus.py` provides a deterministic, manifest-driven local pipeline. Its build manifest requires dataset version/date and per-document HTTPS source and license evidence URLs, supported license identifier, attribution, source version, rights basis, and explicit `rights_verified: true`. Public-domain entries must also identify a jurisdiction. It normalizes line endings and Unicode; excludes missing, malformed UTF-8, replacement/NUL/control, empty, short, and duplicate documents with auditable reasons; and splits eligible content by document into disjoint train/validation/test data. It records source/normalized-content/manifest/tokenizer hashes, document and token counts, cleaning/dedup rules, license details, exclusions, and sample counts. It refuses to overwrite output directories and publishes a completed set of split files atomically.

The instruction JSONL pipeline is separate from continuous-text pretraining. It now requires per-record source URL, license URL, attribution, rights basis, source version, acquisition date, human rights review, and an explicit `human_authored` or `source_excerpt` target provenance. External-model-generated target provenance is rejected. Prompt groups stay within a single split, response tokens plus EOS are supervised, and prompt/padding targets are `-1`.

Research references and one candidate record are in `datasets/source_research_manifest.json`. The official Wikisource policy, CC BY-SA 4.0 legal terms, and Project Gutenberg access terms were reviewed. Wikisource returned page metadata for the candidate revision `16279506` (2026-09-05), with CC BY-SA 4.0 page-license metadata and an observed public-domain assertion for the 1843 work. That is not sufficient to authorize use: edition and jurisdiction-specific rights, plus ShareAlike implications, still require human review. Page-content requests returned HTTP 429; no source text was downloaded, hashed, cleaned, or put into a dataset. The research manifest explicitly marks the candidate excluded and records zero acquired documents/tokens. The pipeline can be used only after each source passes the documented human review.

No eligible training corpus has been collected, no instruction answers have been acquired, no provenance was fabricated, and no substantive pretraining or instruction-tuning was launched. The preserved five-step tiny-model smoke test is test-only and writes to a temporary directory; it is not a Veyra candidate run. Existing checkpoints and data artifacts remain untouched.

## Status and next gated run

- Source document count/token count: **0 / 0**; no train/validation/test dataset exists.
- Stage B/C regression test: `tests/unit/test_stage_b_c_data.py` passed **11 tests** in the project virtual environment. Coverage includes response-only targets plus EOS, ignored prompt/padding labels, one-time shift, loss/backpropagation, EOS stopping, checkpoint/tokenizer pairing, rights/provenance rejection, malformed/short/duplicate document exclusion, split disjointness, and reproducibility. Pylance reported no errors in the changed Python files.
- The fixed six-prompt Veyra-004 outputs above remain incoherent; the EOS/data-path changes do not establish language quality.
- Proposed next candidate configuration, **not executed**: parent `checkpoints/veyra004_pretrain_v5/checkpoint_final.pt`; paired `datasets/processed/tokenizer_veyra004.json`; CPU only; context length 128 to match the checkpoint; fresh AdamW optimizer, learning rate `1e-5`, weight decay `0.01`, gradient clipping `1.0`; batch size 1; seed 42; 100 optimizer steps; validation every 10 steps; checkpoint every 25 steps under a new, unique candidate directory. Start only after a source-verified corpus exists with nonempty, document-disjoint train/validation/test splits and recorded hashes/counts. This is a proposed small pilot, not a claim of sufficient corpus scale or an authorization to bypass the data gate.
- This configuration is not currently executable as specified: `ml/training/train_loop.py` has no validation-dataset input/evaluation path, and its `tokens_seen` counter counts padded sequence slots. Implement and test held-out validation metrics and a correctly counted token metric before considering that pilot; no such change or training run occurred in this mission.
- The master handoff file was not present at repository root; `docs/STAGE_A_VERIFICATION.md` was inspected. Its historical narrative contains claims superseded by the current Stage B/C audit.
