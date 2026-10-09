# Veyra-003 Architecture Design (New Versioned Track)
Status: DESIGN — VERSIONED — PRESERVES Veyra-001/002
Reference: Veyra-002 ~19.3M params (vocab=512, embed=512, layers=4 or 8, heads=4/8, hidden=2048/256, context=128/512)
Veyra-003 proposed (evidence-based improvement, not arbitrary growth):
- vocab_size: 512 (compatible with v2/v3 tokenizer; redesign future if needed)
- embed_dim: 768 (more capacity; head_dim = 64 with 12 heads)
- num_layers: 8 (deeper; more representation)
- num_heads: 12 (head_dim = 64; divisible)
- hidden_dim: 3072 (standard 4x embed)
- context_length: 512 (longer context for instruction + response)
- dropout: 0.15 (slightly stronger regularization)
- device: cpu (local $0)
Estimated params: ~45-55M (embed 512*768 + layers 8*(4*768*768 + 2*768*3072) + head). Not excessive for local CPU; manageable.
Changes from Veyra-002: larger embed/heads/layers/context; dropout adjusted; new versioned init checkpoint; compatible tokenizer; data pipeline fixed (causal shift + continuous sequences).
Not claimed as superior to frontier models — only as evidence-based improvement over Veyra-002 with documented fixes.
