# Stage D — Local Pilot and Free Compute Options

**Date:** 2026-10-10
**Purpose:** Record Veyra's local pilot, compare no-cost hosted options, and track the private artifact mirror plus remote CPU verification. No hosted training job has run.

## Local hardware and constraint

The configured project interpreter reports PyTorch `2.14.1+cpu`, CUDA unavailable, 8 torch CPU threads. The machine reports an AMD Ryzen 7 5700U and 14,870,306,816 bytes of physical memory. Therefore, Veyra's local pilot ran on CPU, not the laptop GPU.

The user reported that laptop compute is overwhelming the PC and requested another free online option. This concern was honored: training stopped after the bounded pilot; the interrupted follow-on process was verified absent. Do not launch additional CPU training on this laptop.

On 2026-10-10 the user explicitly requested hosted compute, superseding the earlier user-level local-only preference for the proposed next step. That request does not itself provision a runner or establish free quota. No upload or remote training was performed.

### Live provider access checks from this workspace

- After the account owner signed into GitHub in the shared browser, the billing page showed the **GitHub Free** plan at **$0/month**. The Actions product panel showed **3 minutes used / 2,000 included**, with included usage resetting in 22 days. It showed **$0 billable usage** (the displayed $0.16 consumed was offset by $0.16 of discounts).
- The personal account's Actions budget is **$0**, configured to **stop usage** at the limit. The current Actions usage is within the included allowance. GitHub's billing documentation says metered-product budgets can stop usage at the budget threshold; included usage and paid overage are distinct. This is evidence for a bounded Actions job under the included quota, not evidence for GPU access or a permanent free service.
- GitHub CLI confirmed the repository initially had **no workflows or workflow runs**. Local `HEAD` and `origin/master` were both `80d86685039001925d45ac3168a054fd6533ad34`.
- The `master` revision lacks the reviewed validation/token-count changes, tests, and corpus tooling; these are local worktree changes, not yet pushed. The checkpoint and split files are not Git-tracked.
- The account's Actions artifact/cache allowance shown is **0.5 GB**, smaller than the checkpoint. GitHub Release assets are a separate mechanism: official GitHub release documentation permits individual assets under 2 GiB with no total release-size or bandwidth cap. The repository was confirmed **private** before use.
- No Kaggle API credentials/configuration or Hugging Face access token are present in this workspace.
- Google Cloud CLI has an active configuration, but the configured project reports billing disabled and Compute API access is unavailable. No VM or cloud resource was created.
- No connected Colab runtime is present.

**Private artifact mirror created:** the prerelease [`veyra004-v5-cpython-v3.14.7-ctx512-20261010`](https://github.com/eliosmernica15/veyra-labs/releases/tag/veyra004-v5-cpython-v3.14.7-ctx512-20261010) is in the verified-private repository. GitHub's release API reports uploaded assets whose SHA-256 digests match local files: v5 checkpoint `7aaee496c5adff3f652a30d67b3bf12dc5438505364ea5a7582a869b43b2110b` (722,729,765 bytes), tokenizer `47ccdfb870d203c002c65c64e199aeb0ec7b36fc9a91e2826fd2c7d9f0456c4d`, train split `d2aae57b2953d0e8e10878350f496bd3dff3193d33c7b0af9ed774ad05b00a49`, validation split `1106bb2fd22cbfa6325fb52ea34194262d09cf306355b3338e3add88410123c3`, and test split `ca7f8c846ae34ac89541dee0761ebb11e63a6e0732ab1e428638e1f10e029891`. The release also holds `provenance.json` and the pinned CPython `Doc/license.rst` notice. No source tree, `.env`, or credentials were uploaded. This is private storage, not a public model release.

**Hosted runner prepared:** `.github/workflows/hosted-cpu-verify.yml` is manual-dispatch only, read-only on repository contents, and uses pinned GitHub Actions. It downloads only the private release into an Ubuntu CPU runner, verifies hashes, runs the focused Stage B/C tests, measures held-out validation loss without weight mutation, and records outputs for all six fixed and two unseen prompts via Veyra's real inference entry point. `scripts/hosted_cpu_verify.py` contains the measurement. The job has not run yet; these files and the fixes are not committed or present on remote `master`.

During cross-platform preparation, inspection of the actual uploaded pickle metadata exposed Windows backslashes in its relative tokenizer path (`datasets\\processed\\tokenizer_veyra004.json`). That path would not resolve on Ubuntu. `ml/path_utils.py` now resolves separator variants, corpus preparation writes portable POSIX paths, and training/inference use the resolver. The focused regression suite now passes **19 tests** locally. No training job was created or run.

**Result:** GitHub Actions is a verified included-minutes option for carefully scoped CPU jobs under the current $0 stop-usage budget. It is not GPU compute and is not free forever. A private, hash-verified copy of the required model and corpus assets now exists remotely. The remaining remote execution steps are to selectively commit/push the reviewed code, tests, workflow, and report (not the full dirty worktree), dispatch the verification job, and inspect actual remote outputs before considering any training.

## Baseline: preserved Veyra-004 v5

- Checkpoint: `checkpoints/veyra004_pretrain_v5/checkpoint_final.pt`
- Step: 100; config: vocab 4,096; context 512; embedding 768; 8 layers; 12 heads; hidden size 3,072.
- Checkpoint SHA-256: `7aaee496c5adff3f652a30d67b3bf12dc5438505364ea5a7582a869b43b2110b`.
- Tokenizer: `datasets/processed/tokenizer_veyra004.json`; SHA-256 `47ccdfb870d203c002c65c64e199aeb0ec7b36fc9a91e2826fd2c7d9f0456c4d`.
- Local inference entry point: `ml.inference.generate.generate_text`.
- Generation: 32 new tokens, temperature 0.8, top-k 50, top-p 0.9, seeds 4200–4207.
- Baseline held-out validation: loss **10.8994022470** over 883 validation samples / 437,989 supervised targets; CPU time **545.907 s**. Weights remained unchanged and the model's original train mode was restored.
- All 8 outputs below are raw decoded outputs returned by the actual Veyra model. Replacement glyphs are preserved as rendered by the tokenizer.

## Bounded candidate pilot

- Hypothesis: a short additional pretraining pass on licensed, deduplicated, document-split technical text might lower held-out technical-domain loss.
- Initialization: v5 above, loaded as `model_path` with fresh AdamW optimizer.
- Dataset: CPython docs v3.14.7, context 512, seed 42; train file SHA-256 `d2aae57b2953d0e8e10878350f496bd3dff3193d33c7b0af9ed774ad05b00a49`; validation file SHA-256 `1106bb2fd22cbfa6325fb52ea34194262d09cf306355b3338e3add88410123c3`.
- Configuration: 10 optimizer steps, batch size 8, accumulation 1, learning rate `1e-5`, weight decay `0.01`, gradient clip `1.0`, validation at step 10, fp32, seed 42.
- Actual: 10 optimizer steps, **40,629 supervised tokens**, train loss **10.6555929184 → 8.4064130783**, validation loss **8.3728643114**, elapsed **684.271 s** total.
- Candidate checkpoint: `checkpoints/candidates/veyra004_cpython_docs_cpu_pilot10_seed42/checkpoint_final.pt`; SHA-256 `39f90ec806b08598822f09ddbec324c83bb54cbb5c504072555360c4dcadf64c`; size **722,726,559 bytes**. It records the parent, tokenizer and dataset identities, step/token counters, and validation result. The v5 parent was not overwritten.
- Interpretation: held-out loss improved on this in-domain validation corpus, but the result is only a small pilot and validation is not a general assistant-quality measure. The assistant-quality candidate is **not accepted**: all fixed prompts and both unseen prompts still elicited incoherent fragments. No instruction tuning was attempted.

### Exact local generations

Each row uses the settings above and the same prompt-specific seed for baseline and pilot.

| Prompt | v5 baseline raw output | 10-step candidate raw output |
|---|---|---|
| `hi how are you` | ` hi how are you info - \`GET /api/models\` � Available checkpoints - \`GET /api/training/models\` � Available checkpoints` | ` hi how are you info - \`GET /api/models\` � Active /api/config\` � Active training settings - \`P` |
| `What is 2 + 2?` | ` What is 2 + 2? - \`GET /api/system\` � Hardware / environment info - \`GET /api/models\` � Available` | ` What is 2 + 2? - \`GET /api/system\` � Hardware / environment info - \`GET /api/models\` � Available` |
| `Explain what Python is in two sentences.` | ` Explain what Python is in two sentences. A /api/-/s - \`GET /api/training/config\` � Not immodels\` � Activevailable checkpoints - \`` | ` Explain what Python is in two sentences.:/system\` � Hardware / environment info - \`GET /api/models\` � Available checkpoints - \`GET` |
| `Reply with exactly three bullet points about computers.` | ` Reply with exactly three bullet points about computers.ware / environment info - \`GET /api/models\` � Available checkpoints - \`GET /api/checkpoints\` � Checkpoint` | ` Reply with exactly three bullet points about computers.ware / environment info - \`GET /api/models\` � Available checkpoints - \`GET /api/checkpoints\` � Checkpoint` |
| `Write a Python function that adds two numbers.` | ` Write a Python function that adds two numbers. AL (lo-data\` � Not implemented in Phase 1 (use CLI scripts directly) - \`POST /api` | ` Write a Python function that adds two numbers. L/system\` � Hardware / environment info - \`GET /api/models\` � Available checkpoints - \`GET` |
| `Fix this code: def add(a, b) return a + b` | ` Fix this code: def add(a, b) return a + bs - \`POST /api/config\` � Active training settings - \`POST /api/training/prepare-` | ` Fix this code: def add(a, b) return a + b \`POST /api/training/config\` � Active training settings - \`POST /api/training/prepare-` |
| `Summarize what a list is in Python.` *(unseen)* | ` Summarize what a list is in Python. \`GET /api/config\` � Active training settings - \`GET /api/training/pre Phase 1 - \`PO` | ` Summarize what a list is in Python. \`GET /api/config\` � Active training settings - \`GET /api/training/pre Phase 1 (use CLI s` |
| `What is 17 times 6?` *(unseen)* | ` What is 17 times 6? - \`GET /api/system\` � Hardware / environment info - \`GET /api/models\` � Available` | ` What is 17 times 6? - \`GET /api/system\` � Hardware / environment info - \`GET /api/models\` � Available` |

The arithmetic prompts do not produce answers that can pass independent arithmetic checks. The explanation and formatting requests fail relevance and form. The code outputs are not usable programs, so no generated-code execution was necessary. Outputs still echo the prompt and reproduce API-document text. The training pilot lowered loss but did not fix the observed generation failure.

## Free hosting and storage comparison

Checked against provider documentation on 2026-10-10. Offers, quotas, and retention policies can change. **No provider promises a permanent free GPU plus unlimited private storage.** The user has authorized exploring hosted execution, but that does not guarantee a free service or establish the privacy, licensing, and retention suitability of every destination; review the destination before uploading project materials.

| Provider | Verified free offering | Suitability / risk |
|---|---|---|
| **Hugging Face Hub / ZeroGPU** | Free personal accounts in good standing may host up to two ZeroGPU Spaces; current documentation lists **5 GPU minutes/day** for a free account. Free user/org accounts have **100 GB private repository storage**; public storage is best-effort. | Best clearly documented free private storage amount found, but ZeroGPU is far too limited for sustained training. Not one bundled compute-and-storage solution. [Storage limits](https://huggingface.co/docs/hub/storage-limits), [ZeroGPU quotas](https://huggingface.co/docs/hub/spaces-zerogpu). |
| **Google Colab** | Free of charge; free managed runtimes may offer GPUs. Google states resources are not guaranteed or unlimited and usage limits fluctuate. | Not dependable for scheduled training. Runtime VMs are temporary; free Drive storage is shared with Gmail and Photos (typically 15 GB for a personal account). Mounting Drive gives notebook code access to Drive contents. Google also restricts remote-control and distributed-worker activities on free managed runtimes. [Colab FAQ and resource limits](https://research.google.com/colaboratory/faq.html#resource-limits); [Google account storage details](https://support.google.com/drive/answer/6374270?hl=en). |
| **Kaggle Notebooks** | Official notebook docs and terms exist, but this check did not establish current numerical GPU quotas, persistence duration, or checkpoint-retention guarantees from those sources. | Plausible free notebook candidate but cannot responsibly promise it meets the training/storage need until current account-specific quotas and retention are confirmed. [Notebooks documentation](https://www.kaggle.com/docs/notebooks), [Terms](https://www.kaggle.com/terms). |
| **GitHub Codespaces** | Included monthly usage on some plans. | CPU development environment, not a practical free GPU training offer; storage is quota-metered. [Billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces). |
| **Modal** | Signup credits are advertised in current documentation. | Credits are temporary; GPU access/billing requires a valid payment method. Not safe for a strict zero-cost guarantee without payment controls. [GPU guide](https://modal.com/docs/guide/gpu.md), [billing](https://modal.com/docs/guide/billing.md). |
| **Runpod** | No free recurring GPU tier verified. | On-demand compute and persistent volumes are billed; exclude from a $0 plan. [Pod pricing](https://docs.runpod.io/pods/pricing), [storage types](https://docs.runpod.io/pods/storage/types). |

### Recommendation

There is no defensible “free forever” remote destination. For storage alone, Hugging Face documents the largest quantified free private storage in the options reviewed (100 GB), but remote storage of the local corpus/checkpoints/code still needs explicit approval and a review of privacy, license notice, and account policies. For compute, Colab and Kaggle may offer free GPU sessions, but availability, account quotas, runtime lifetime, and persistence are not equivalent to a reliable training host.

**Current execution status:** the checkpoint and accepted corpus are mirrored in the private release, and a CPU-only verification workflow exists locally. Hosted verification awaits a selective code commit/push and manual dispatch. Training remains paused; no GPU host is connected, and no laptop training process is active.

**Recommendation if a separate, user-controlled environment is provisioned:** Google Colab is the most recognizable free GPU notebook option from the providers reviewed, but it is not guaranteed, its free runtime is temporary, and Google explicitly says resources and usage limits fluctuate. Hugging Face documents 100 GB of free private repository storage, but ZeroGPU's free daily allowance (5 GPU minutes) cannot handle sustained training; no Hugging Face credential is connected here. Pairing Hugging Face private storage with Actions CPU jobs might technically transfer the checkpoint, but requires a private repository, securely provisioned token, careful workflow permissions, and measured runtime. This combination has not been set up or verified. Kaggle may be another candidate, but current quotas and retention were not verified. GitHub Actions can provide remote CPU execution using up to the currently displayed included minutes; it cannot provide GPU. No provider can be recommended as working perfectly or free forever.

No additional billing action is currently needed for a bounded job under included Actions usage; the account owner should recheck available minutes and the stop-usage budget immediately before dispatch. Do not grant or paste a token with broader account scope in chat. Any future execution still needs review of live quota, privacy/retention terms, rights notices, and checkpoint destination. Do not upload `.env`, credentials, unrelated code, or private evaluation prompts. No card or payment method should be added.

## Security and next work

- No credentials were shown, rotated, or uploaded. `.env` remains ignored; its historical copy at `ec1eb318733b79ea5bbd114d6220be101325c070` remains a manual remediation. Privately revoke/replace `VEYRA_API_KEY` with its issuer or local service; do not send it in chat.
- The candidate is preserved but not designated best for assistant quality. No more CPU training is recommended on this laptop.
- The manual CPU verification workflow must pass before considering any new training. Any candidate training still needs separate configuration, held-out metrics, actual inference evidence, and preservation of the original best checkpoint. The current corpus is narrow and prior outputs remain incoherent.
