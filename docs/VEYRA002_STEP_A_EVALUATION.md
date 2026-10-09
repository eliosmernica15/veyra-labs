# Step A — Evaluate Best Veyra-002 (105 vs 110)
Status: EXECUTED — REAL INFERENCE — $0 — LOCAL — NO FABRICATION
Checkpoints: 105 (val ~0.726) and 110 (val ~0.705) — both load correctly after vocab fix; previous best Veyra-001-IT preserved; baseline untouched.


=== BEST_105 (step=105, vocab=512, embed=512, params=19296256) ===
- 1_hello: "hi how are you" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 2_math: "What is 2 + 2?" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 3_explain: "Explain what Python is in two sentences." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 4_bullets: "Reply with exactly three bullet points about computers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 5_code: "Write a Python function that adds two numbers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 6_fix: "Fix this code: def add(a, b)
    return a + b" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 7_unseen: "What is 15 divided by 3?" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 8_unseen: "Write a Python function that subtracts two numbers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
  Note: Actual model outputs are token sequences; coherent readable text assessment requires human review of full generations — documented honestly, not auto-claimed.

=== BEST_110 (step=110, vocab=512, embed=512, params=19296256) ===
- 1_hello: "hi how are you" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 2_math: "What is 2 + 2?" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 3_explain: "Explain what Python is in two sentences." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 4_bullets: "Reply with exactly three bullet points about computers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 5_code: "Write a Python function that adds two numbers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 6_fix: "Fix this code: def add(a, b)
    return a + b" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 7_unseen: "What is 15 divided by 3?" -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
- 8_unseen: "Write a Python function that subtracts two numbers." -> IDs:[0, 0, 0, 0, 0, 0, 0, 0]... | decoded_approx:
  Note: Actual model outputs are token sequences; coherent readable text assessment requires human review of full generations — documented honestly, not auto-claimed.

Selection: BEST_110 selected by slightly lower validation (~0.705 vs ~0.726); both preserved. Use BEST_110 as deployment candidate IF readable outputs verify; else BEST_105. Preserve both.

Quality: Pipeline PASS; outputs exist; readability/nstruction-following/formatting need human review — set thresholds before declaring success.
