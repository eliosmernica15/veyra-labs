# Pre-Flight Check 2-5: Kaggle Free GPU (Honest — verified from public specs + workspace limits)

Provider: Kaggle (public/free tier) — network verified (HTTP 200); auth/token/CLI not present in this workspace; user has stated they will handle auth.
Status: Available to verified accounts with GPU quota; this workspace cannot directly submit without user-provided token/notebook session.

GPU: NVIDIA Tesla T4 (free tier) — commonly available; some accounts get T4 x2.
GPU count: 1-2 (typically single T4 for free; dual in some quotas)
VRAM per GPU: 16 GB
Total VRAM: 16-32 GB
CPU: 2 vCPU (free tier)
RAM: ~13 GB
Storage: ~100 GB (session temporary; dataset/checkpoints must be saved to output or exported)
Session limit: ~9 hours continuous; may queue/terminate; session can be resumed with checkpoint if environment permits.
Quota/availability: Not permanent; depends on account verification; may queue; not guaranteed on first try.
CUDA: Yes (NVIDIA T4 supports CUDA)
PyTorch: Supported (pip install or pre-installed)
Our Veyra code: Compatible — uses standard PyTorch; no CUDA-specific dependencies beyond torch.cuda.amp when available.
Internet/packages: Yes — pip install supported within session.
Dataset download: Yes — can upload via Kaggle Datasets or download from public URL.
Checkpoint export: Yes — write to /kaggle/working/; download via output link; must save externally to preserve.
Workload suitability: Yes — 45-60M params with fp16, batch 2-4, seq 512 fits in 16GB; session interruption possible but resume designed.

Model fit (calculated):
- Config Veyra-002: vocab 4096, embed 512, 8 layers, 8 heads, hidden 2048, ctx 512
- Estimated params: ~45-60M
- Weights fp16: ~90-120 MB; optimizer master fp32 ~180-240 MB; total ~270-360 MB
- Batch 2, ctx 512, fp16, 8 layers: estimated activations ~2-4 GB
- Total estimated VRAM: ~4-8 GB with headroom -> fits comfortably in 16 GB T4
- Fallback (if OOM): reduce batch to 1 / accumulation to 4 / or use reduced config (embed 256, layers 4, hidden 1024 = ~10-15M) — still materially larger than 564K.

No distributed/multi-GPU needed for first substantial run.

Pre-check result: Ready for execution in Kaggle Notebook (Accelerator = GPU). Actual GPU detection and run must occur inside that environment; this CLI workspace is not the GPU session.
