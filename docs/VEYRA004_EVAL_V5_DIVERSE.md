# Veyra-004 v5 Diverse Evaluation (Real — $0 — Local)
Checkpoint: checkpoints/veyra004_pretrain_v5/checkpoint_final.pt
Status: EXECUTED REAL. Quality gate ENFORCED (no false coherence).

=== hello ===
Prompt: hello how are you
Output IDs: [3775, 165, 2456, 2498, 0, 0, 0, 0, 0, 0, 0, 0, 17, 490, 2084, 15, 224, 64, 989, 257, 67, 277, 1975, 1360, 79, 823, 866, 40, 1988, 1038, 1468, 17]
Non-EOS count: 24 | EOS first at: 4
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

=== math ===
Prompt: What is 2 + 2?
Output IDs: [190, 3388, 2197, 2197, 0, 0, 0, 0, 0, 0, 0, 0, 17, 490, 2084, 15, 2698, 64, 989, 1581, 1045, 2050, 359, 136, 1039, 147, 822, 410, 2034, 122, 1141, 80]
Non-EOS count: 24 | EOS first at: 4
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

=== explain ===
Prompt: Explain Python in one sentence.
Output IDs: [2031, 2327, 397, 1148, 1842, 0, 0, 0, 0, 0, 0, 0, 17, 490, 2084, 15, 2698, 64, 989, 257, 67, 277, 1975, 1360, 79, 823, 866, 40, 1988, 1038, 1468, 17]
Non-EOS count: 25 | EOS first at: 5
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

=== bullets ===
Prompt: Reply with three bullet points about computers.
Output IDs: [1104, 2981, 3912, 1291, 1164, 2793, 263, 0, 0, 0, 0, 0, 17, 2064, 224, 64, 989, 434, 1166, 87, 367, 1038, 1975, 1360, 79, 823, 866, 40, 1988, 1038, 1468, 17]
Non-EOS count: 27 | EOS first at: 7
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

=== code ===
Prompt: Write a Python function that adds two numbers.
Output IDs: [1724, 1440, 2327, 3933, 131, 2416, 2609, 378, 0, 0, 0, 0, 17, 490, 2084, 15, 2698, 64, 989, 1581, 1045, 2050, 359, 136, 1039, 147, 822, 410, 2034, 122, 1141, 80]
Non-EOS count: 28 | EOS first at: 8
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

=== unseen ===
Prompt: What is 15 divided by 3?
Output IDs: [190, 3388, 622, 2016, 3185, 3712, 0, 0, 0, 0, 0, 0, 17, 490, 2084, 15, 224, 64, 989, 257, 67, 277, 1975, 1360, 79, 823, 866, 40, 1988, 1038, 1468, 17]
Non-EOS count: 26 | EOS first at: 6
Assessment: PARTIAL NON-EMPTY — some token diversity, readability unverified by human.

Non-empty outputs: 6/6
Overfit: Confirmed — loss 1.27->0.0007 in 50 steps on 1199 seq; repetition not the only cause (v5 is diverse); model simply overfits to any fixed dataset at this size/length.
Next: Need genuinely larger / multi-source pretraining (10k-50k unique) and masked instruction-tuning (correct format, verified targets) before declaring coherent base.
Security: AGENT_AUTONOMOUS_EXECUTION=False preserved (agent/core/config.py:24 verified). No remote access, $0.
