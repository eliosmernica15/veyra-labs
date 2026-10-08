#!/usr/bin/env python3
"""Integration tests for FastAPI backend."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, "services/api")
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system():
    r = client.get("/api/system")
    assert r.status_code == 200
    data = r.json()
    assert "platform" in data


def test_training_config():
    r = client.get("/api/training/config")
    assert r.status_code == 200
    data = r.json()
    assert "batch_size" in data


def test_checkpoints_empty():
    r = client.get("/api/checkpoints")
    assert r.status_code == 200


def test_generate_needs_checkpoint():
    r = client.post("/api/generate", json={"prompt": "hello", "max_new_tokens": 5})
    # Checkpoints exist from smoke test; should return 200 with real output
    assert r.status_code == 200
    assert "output" in r.json()


def test_evaluate_needs_checkpoint():
    r = client.post("/api/evaluate")
    # With real checkpoints present, evaluation succeeds
    assert r.status_code == 200
    data = r.json()
    assert "avg_loss" in data or "perplexity" in data or "step" in data
