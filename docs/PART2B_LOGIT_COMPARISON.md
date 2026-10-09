# Part 2B — Logit/Probability Comparison (Real)
Pretrain 90: predicts varied fragments (not 0); IT 110: predicts 0 (</s>) with high prob
Evidence: tokenizer 0 = </s> (end of sequence); IT learns/outputs EOS immediately
Root cause: instruction format or target construction encourages EOS at response start
Fix direction: ensure response targets don't include premature EOS; use masking; build larger diverse dataset.
