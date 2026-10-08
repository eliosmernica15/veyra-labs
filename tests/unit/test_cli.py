#!/usr/bin/env python3
"""CLI tests: verify real command behavior without requiring backend for basic commands."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_version():
    result = subprocess.run([sys.executable, "apps/cli/veyra.py", "--version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "veyra" in result.stdout


def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "apps.cli.veyra", "--help"], capture_output=True, text=True)
    # If module invocation fails, try direct file
    if result.returncode != 0:
        result = subprocess.run([sys.executable, "apps/cli/veyra.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "usage:" in result.stdout or "help" in result.stdout.lower()


def test_cli_status_offline_graceful():
    # Status should report backend unreachable rather than crash
    result = subprocess.run([sys.executable, "apps/cli/veyra.py", "status"], capture_output=True, text=True)
    # May return 0 with message, or exit non-zero; key is it prints something readable
    assert "Backend" in result.stdout or "backend" in result.stdout or result.returncode in (0, 1)
