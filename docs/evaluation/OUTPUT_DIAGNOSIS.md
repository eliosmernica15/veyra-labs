# Phase 9 Audit — Poor Output Diagnosis (Evidence-Based)

Observed (from Phase 8 instructions, actual manual test):
Prompt: hiii
Output: hiiiiipdre ofnsudsbl ofinchelo. o usr

Possible causes — assessed with evidence:
- Insufficient training: YES — only 35 steps on synthetic dataset (evidence: step 35, small dataset, small vocab)
- Tiny model capacity: YES — ~565k params, 4 layers, 128 embed (evidence: config + param estimate)
- Tiny dataset: YES — synthetic sample.txt, ~5 train samples (evidence: prepare.py + dataset files)
- Tokenizer issue: NO — ByteLevel decode coherent (verified earlier with fixed tokenizer; output fragments are model-generation artifacts, not tokenizer decode errors)
- Tokenizer/checkpoint mismatch: NO — tokenizer_path in checkpoint matches dataset/processed/tokenizer.json; vocab size consistent (155)
- Inference bug: NO — load_checkpoint uses map_location="cpu"; tokenizer loads correctly; generate uses correct decode path
- Sampling bug: POSSIBLE CONTRIBUTION — temperature=1.0 default; but poor output persists at all settings; not primary cause
- Incorrect checkpoint selection: NO — Studio selects checkpoint_final.pt; inference loads same file; metadata agrees (step 35)
- Context-length issue: NO — sequence within 128 limit
- Model architecture issue: NO — architecture matches Config; weights load correctly; parameter count matches formula
- Another implementation issue: NO EVIDENCE — framework tests pass (114); audit chain valid; safeguards protected; no errors in inference path

Primary root causes: Insufficient training + tiny capacity + tiny dataset.
Not a hidden bug.
Not fixable by prompt change or UI change.
Requires actual larger training with same pipeline.
