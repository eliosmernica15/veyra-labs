"""Veyra Labs — Configurable decoder-only Transformer (PyTorch)."""
from __future__ import annotations

import math
import torch
import torch.nn as nn
from torch.nn import functional as F


class Config:
    """Model / training hyperparameters — single source of truth."""
    def __init__(self, vocab_size: int = 4096, context_length: int = 128,
                 embed_dim: int = 128, num_layers: int = 4,
                 num_heads: int = 4, hidden_dim: int = 256,
                 dropout: float = 0.1, device: str = "cpu"):
        self.vocab_size = vocab_size
        self.context_length = context_length
        self.embed_dim = embed_dim
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.hidden_dim = hidden_dim
        self.head_dim = embed_dim // num_heads
        assert self.head_dim * num_heads == embed_dim, "embed_dim must divide evenly by num_heads"
        self.dropout = dropout
        self.device = torch.device(device) if device != "cpu" else torch.device("cpu")

    def param_estimate(self) -> int:
        # Rough param count (embeddings + transformer layers + output head)
        emb = self.vocab_size * self.embed_dim
        layer = (4 * (self.embed_dim * self.embed_dim) +  # qkv proj
                self.embed_dim * self.hidden_dim +        # ffn up
                self.hidden_dim * self.embed_dim +        # ffn down
                2 * self.embed_dim)                      # 2 layernorms
        head = self.embed_dim * self.vocab_size
        return emb + self.num_layers * layer + head


class RotaryPositionalEmbedding(nn.Module):
    """Simplified rotary positional embeddings (RoPE) for causal attention."""
    def __init__(self, head_dim: int, max_len: int = 512):
        super().__init__()
        inv_freq = 1.0 / (10000 ** (torch.arange(0, head_dim, 2).float() / head_dim))
        self.register_buffer("inv_freq", inv_freq)
        t = torch.arange(max_len, dtype=torch.float32)
        freqs = torch.outer(t, inv_freq)  # (max_len, head_dim/2)
        # Precompute cos/sin pairs
        self.register_buffer("cos", torch.cos(freqs).unsqueeze(1))  # (max_len, 1, head_dim/2)
        self.register_buffer("sin", torch.sin(freqs).unsqueeze(1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply RoPE to query/key tensors (last 2 dims: seq_len, head_dim)."""
        # x: (..., seq_len, head_dim)
        seq_len = x.shape[-2]
        cos = self.cos[:seq_len]   # (seq_len, 1, head_dim/2)
        sin = self.sin[:seq_len]   # (seq_len, 1, head_dim/2)
        x1, x2 = x[..., ::2], x[..., 1::2]
        # Rotate
        rotated = torch.stack([-x2, x1], dim=-1).flatten(-2, -1)
        return x * cos + rotated * sin


class CausalSelfAttention(nn.Module):
    def __init__(self, config: Config):
        super().__init__()
        self.n_heads = config.num_heads
        self.head_dim = config.head_dim
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(config.embed_dim, 3 * config.embed_dim, bias=False)
        self.proj = nn.Linear(config.embed_dim, config.embed_dim, bias=False)
        # Positional info handled externally (learnable pos_embed in main model)
        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        # QKV projection
        qkv = self.qkv(x)  # (B, T, 3*C)
        q, k, v = qkv.split(C, dim=-1)
        # Reshape to multi-head
        q = q.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)  # (B, H, T, D)
        k = k.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        # Causal masked scaled dot-product attention (no RoPE for simplicity; positions handled via pos_embed)
        mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
        scores = (q @ k.transpose(-2, -1)) * self.scale  # (B, H, T, T)
        scores = scores.masked_fill(mask.unsqueeze(0).unsqueeze(0), float("-inf"))
        attn = F.softmax(scores, dim=-1)
        attn = self.attn_dropout(attn)

        out = attn @ v  # (B, H, T, D)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        out = self.proj(out)
        out = self.resid_dropout(out)
        return out


class FeedForward(nn.Module):
    def __init__(self, embed_dim: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, config: Config):
        super().__init__()
        self.ln1 = nn.LayerNorm(config.embed_dim)
        self.attn = CausalSelfAttention(config)
        self.ln2 = nn.LayerNorm(config.embed_dim)
        self.ffn = FeedForward(config.embed_dim, config.hidden_dim, config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Pre-normalization architecture (more stable)
        x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x


class VeyraPrime(nn.Module):
    """Veyra Prime decoder-only Transformer (trainable, real weights)."""
    def __init__(self, config: Config | None = None):
        super().__init__()
        if config is None:
            config = Config()
        self.config = config
        self.tok_embed = nn.Embedding(config.vocab_size, config.embed_dim)
        # Learnable positional embeddings (simpler, works well for small models)
        self.pos_embed = nn.Embedding(config.context_length, config.embed_dim)
        self.blocks = nn.ModuleList([TransformerBlock(config) for _ in range(config.num_layers)])
        self.ln_final = nn.LayerNorm(config.embed_dim)
        self.lm_head = nn.Linear(config.embed_dim, config.vocab_size, bias=False)
        # Tie output head weights to token embeddings (standard practice)
        self.tok_embed.weight = self.tok_embed.weight  # identity reference for tie
        # Actually tie: share weights explicitly
        self.tok_embed.weight = nn.Parameter(torch.randn(config.vocab_size, config.embed_dim) * 0.02)
        # Re-instantiate with shared params
        # (Simpler: just set head weight = embed weight at init and after load)
        self.apply(self._init_weights)
        # Tie after init
        self.lm_head.weight = self.tok_embed.weight
        self.param_estimate_ = config.param_estimate()

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.constant_(module.bias, 0)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        B, T = idx.shape
        assert T <= self.config.context_length, f"Sequence length {T} exceeds max {self.config.context_length}"
        # Token + positional embeddings
        tok_emb = self.tok_embed(idx)  # (B, T, C)
        pos = torch.arange(T, device=idx.device).unsqueeze(0).expand(B, T)
        pos_emb = self.pos_embed(pos)
        x = tok_emb + pos_emb
        # Transformer blocks
        for block in self.blocks:
            x = block(x)
        x = self.ln_final(x)
        logits = self.lm_head(x)  # (B, T, vocab_size)
        return logits

    def generate(self, idx: torch.Tensor, max_new_tokens: int = 20,
                 temperature: float = 1.0, top_k: int | None = 50,
                 top_p: float = 1.0, seed: int | None = None) -> torch.Tensor:
        """Autoregressive generation from trained weights. Real inference."""
        if seed is not None:
            torch.manual_seed(seed)
        for _ in range(max_new_tokens):
            # Crop to context window
            idx_cond = idx if idx.shape[1] <= self.config.context_length else idx[:, -self.config.context_length:]
            logits = self.forward(idx_cond)  # (B, T, V)
            logits = logits[:, -1, :] / temperature  # (B, V)
            # Top-k filtering
            if top_k is not None and top_k > 0:
                v = logits.size(-1)
                k_actual = min(top_k, v)
                values, _ = torch.topk(logits, k_actual, dim=-1)
                min_val = values[:, -1].unsqueeze(-1)
                logits = torch.where(logits < min_val, torch.tensor(float("-inf"), device=logits.device), logits)
            # Top-p (nucleus) filtering — simplified to avoid dtype issue
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True, dim=-1)
                sorted_probs = F.softmax(sorted_logits, dim=-1)
                cumsum = sorted_probs.cumsum(dim=-1)
                sorted_indices_to_remove = cumsum > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = False
                # Direct indexing for batch size 1 (typical for generation)
                for b in range(logits.size(0)):
                    sorted_idx = sorted_indices[b]
                    remove_mask = sorted_indices_to_remove[b]
                    # Set removed vocab positions to -inf directly
                    delete_indices = sorted_idx[remove_mask]
                    if delete_indices.numel() > 0:
                        logits[b, delete_indices] = float("-inf")
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)  # (B, 1)
            idx = torch.cat([idx, next_token], dim=1)
            # Optional: stop on EOS token if vocabulary includes it (not enforced by default)
        return idx

    def compute_loss(self, batch: tuple[torch.Tensor, torch.Tensor]) -> torch.Tensor:
        x, y = batch
        logits = self.forward(x)
        # Shift for next-token prediction: logits[:, :-1] vs y[:, 1:] if aligned,
        # but we assume x and y are already aligned: x=sequence[:-1], y=sequence[1:]
        B, T, V = logits.shape
        # Causal next-token: predict token at position i+1 from position i
        # If y is already next-token targets aligned with x, use direct; else shift
        # For continuous sequences (pretraining): x=seq[:T-1], y=seq[1:] -> logits[:, :-1] vs y
        if y.size(1) == logits.size(1) - 1:
            loss = F.cross_entropy(logits[:, :-1, :].reshape(-1, V), y.reshape(-1), ignore_index=-1, reduction="mean")
        else:
            loss = F.cross_entropy(logits.reshape(B * T, V), y.reshape(B * T), ignore_index=-1, reduction="mean")
        return loss

    @property
    def device(self) -> torch.device:
        return self.config.device
