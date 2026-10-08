#!/usr/bin/env python3
"""Veyra Studio — Python-only Streamlit interface."""
from __future__ import annotations

import streamlit as st
import requests
import json
from pathlib import Path
import torch

st.set_page_config(page_title="Veyra Studio", layout="wide")
st.title("Veyra Studio")

# Sidebar: system info
with st.sidebar:
    st.header("System")
    try:
        r = requests.get("http://localhost:8000/api/system", timeout=3)
        info = r.json() if r.status_code == 200 else {"error": "API unreachable"}
    except Exception as exc:
        info = {"error": str(exc)}
    st.json(info)

# Main tabs: Overview | Models | Training | Chat | Evaluation | Logs
tabs = st.tabs(["Overview", "Models", "Training", "Chat", "Evaluation", "Logs"])

with tabs[0]:
    st.subheader("Overview")
    st.write("Veyra Labs — Real AI model development platform (Python-first).")
    st.info("Checkpoints, model config, and hardware info shown above.")
    # Try to load latest checkpoint info
    try:
        r = requests.get("http://localhost:8000/api/checkpoints", timeout=3)
        data = r.json() if r.status_code == 200 else {}
        checkpoints = data.get("checkpoints", [])
        if checkpoints:
            st.write(f"Available checkpoints: {len(checkpoints)}")
            for cp in checkpoints[:3]:
                st.code(str(cp.get("path", "unknown")) + f" (step={cp.get('step')})")
        else:
            st.warning("No checkpoints found in checkpoints/.")
    except Exception as exc:
        st.error(f"Could not connect to backend: {exc}")

with tabs[1]:
    st.subheader("Models")
    try:
        r = requests.get("http://localhost:8000/api/models", timeout=3)
        data = r.json() if r.status_code == 200 else {}
        st.json(data)
    except Exception as exc:
        st.error(f"Backend unreachable: {exc}")

with tabs[2]:
    st.subheader("Training")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Configuration (from .env / backend):")
        try:
            r = requests.get("http://localhost:8000/api/training/config", timeout=3)
            cfg = r.json() if r.status_code == 200 else {}
            st.json(cfg)
        except Exception as exc:
            st.error(str(exc))
    with col2:
        st.write("Status")
        # Show latest checkpoint info
        try:
            r = requests.get("http://localhost:8000/api/checkpoints", timeout=3)
            checkpoints = r.json().get("checkpoints", []) if r.status_code == 200 else []
            if checkpoints:
                latest = checkpoints[0]
                st.metric("Latest Step", latest.get("step", "N/A"))
                st.metric("Vocab Size", latest.get("vocab_size", "N/A"))
            else:
                st.info("Run training first.")
        except Exception as exc:
            st.error(str(exc))

with tabs[3]:
    st.subheader("Chat (Inference)")
    prompt = st.text_input("Prompt:", value="The quick brown fox jumps over")
    temperature = st.slider("Temperature", 0.1, 2.0, 1.0, 0.1)
    max_new = st.slider("Max new tokens", 5, 100, 20)
    if st.button("Generate"):
        try:
            payload = {
                "prompt": prompt,
                "max_new_tokens": max_new,
                "temperature": temperature,
                "top_k": 50,
                "top_p": 0.9,
            }
            r = requests.post("http://localhost:8000/api/generate", json=payload, timeout=30)
            if r.status_code == 200:
                result = r.json()
                st.success("Generation complete.")
                st.write(f"**Checkpoint:** `{result.get('checkpoint', 'unknown')}` (step {result.get('step', 'N/A')})")
                st.write(f"**Prompt:** {result.get('prompt', '')}")
                st.code(result.get("output", ""), language="text")
            else:
                st.error(f"Generate failed: {r.status_code} — {r.text}")
        except Exception as exc:
            st.error(f"Request error: {exc}")
    st.caption("Uses real loaded checkpoint weights — no simulated responses.")

with tabs[4]:
    st.subheader("Evaluation")
    if st.button("Run Evaluation"):
        try:
            r = requests.post("http://localhost:8000/api/evaluate", timeout=60)
            if r.status_code == 200:
                result = r.json()
                st.success("Evaluation completed.")
                st.json(result)
            else:
                st.error(f"Evaluate failed: {r.status_code} — {r.text}")
        except Exception as exc:
            st.error(f"Request error: {exc}")
    st.info("Evaluation measures validation loss, perplexity, tokenizer round-trip, and checkpoint equivalence.")

with tabs[5]:
    st.subheader("Logs")
    try:
        r = requests.get("http://localhost:8000/api/training/test_run/logs", timeout=3)
        logs = r.json().get("logs", []) if r.status_code == 200 else []
        for line in logs:
            st.text(line)
    except Exception as exc:
        st.info("No live training logs available (run a training job via CLI or backend). See console for backend logs.")
    st.caption("Secrets and sensitive values are redacted at the backend level (not shown here).")
