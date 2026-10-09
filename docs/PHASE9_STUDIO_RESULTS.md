# Phase 9 Studio Manual Test — Verification Only

Status: VERIFICATION (5-step smoke), NOT capable assistant.
Model: Veyra-001 / checkpoint: checkpoints/veyra001_smoke.pt / step: 5 / tokenizer: tokenizer_veyra001.json

Baseline comparison prompts (same as Phase 8 audit):
- hiiii (baseline: broken fragments)
- Hello, who are you?
- What is 2 + 2?
- What is Python?
- Write a Python function that adds two numbers.

Results (honest, no embellishment):

### hiiii
Prompt: hiiii
Output shape: [1, 20, 200]
Predicted token IDs (first 10): [147, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Note: VERIFICATION ONLY — 5-step smoke; output is numeric token sequence, not coherent language. Baseline (hiiii -> broken) also poor. No improvement claimed.

### hello_who
Prompt: Hello, who are you?
Output shape: [1, 20, 200]
Predicted token IDs (first 10): [147, 147, 147, 147, 0, 0, 0, 0, 0, 0]
Note: VERIFICATION ONLY — 5-step smoke; output is numeric token sequence, not coherent language. Baseline (hiiii -> broken) also poor. No improvement claimed.

### 2_plus_2
Prompt: What is 2 + 2?
Output shape: [1, 20, 200]
Predicted token IDs (first 10): [147, 147, 147, 147, 0, 0, 0, 0, 0, 0]
Note: VERIFICATION ONLY — 5-step smoke; output is numeric token sequence, not coherent language. Baseline (hiiii -> broken) also poor. No improvement claimed.

### what_is_python
Prompt: What is Python?
Output shape: [1, 20, 200]
Predicted token IDs (first 10): [147, 147, 147, 0, 0, 0, 0, 0, 0, 0]
Note: VERIFICATION ONLY — 5-step smoke; output is numeric token sequence, not coherent language. Baseline (hiiii -> broken) also poor. No improvement claimed.

### python_add
Prompt: Write a Python function that adds two numbers.
Output shape: [1, 20, 200]
Predicted token IDs (first 10): [70, 147, 147, 147, 147, 65, 65, 65, 0, 0]
Note: VERIFICATION ONLY — 5-step smoke; output is numeric token sequence, not coherent language. Baseline (hiiii -> broken) also poor. No improvement claimed.

Conclusion: Smoke model produces numeric outputs only; coherent language not achieved. Milestone remains at 'smoke / gibberish'. Full milestone (coherent -> instruction -> reasoning) requires substantial remote-GPU training — not executed.
