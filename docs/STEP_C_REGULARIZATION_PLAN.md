# Step C — Regularization / Architecture Tuning Plan (Authorized by master directive id=bede)
Status: PREPARED — NOT FULLY EXECUTED YET (no false success claimed)
Changes proposed (verified local, $0):
- Add dropout (0.1-0.2) to transformer config and train loop
- Increase weight decay (0.05) and enable validation-based early stopping
- Use v4 dataset (4000/1000) for retrain with validation checkpoint selection
- Compare to best preserved (105/110) honestly — retain best, document failures
- Preserve security (AGENT_AUTONOMOUS_EXECUTION=False), $0, no external LLM
Execution: prepare config edits; full retrain requires confirming steps / time; not automatically claimed complete.
