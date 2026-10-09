#!/usr/bin/env python3
"""Agent framework configuration — names and feature flags remain configurable."""
from __future__ import annotations

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv(override=False)


COMPANY_NAME = os.getenv("VEYRA_COMPANY_NAME", "Veyra Labs")
PLATFORM_NAME = os.getenv("VEYRA_PLATFORM_NAME", "Veyra AI")
STUDIO_NAME = os.getenv("VEYRA_STUDIO_NAME", "Veyra Studio")
CLI_NAME = os.getenv("VEYRA_CLI_NAME", "veyra")
DEFAULT_MODEL = os.getenv("VEYRA_DEFAULT_MODEL", "Veyra Prime")
CODING_MODEL = os.getenv("VEYRA_CODING_MODEL", "Veyra Code")
IMAGE_MODEL = os.getenv("VEYRA_IMAGE_MODEL", "Veyra Vision")
VIDEO_MODEL = os.getenv("VEYRA_VIDEO_MODEL", "Veyra Motion")
AUDIO_MODEL = os.getenv("VEYRA_AUDIO_MODEL", "Veyra Voice")
RESEARCH_AGENT = os.getenv("VEYRA_RESEARCH_AGENT", "Veyra Research")

AGENT_ENABLED = os.getenv("VEYRA_AGENT_ENABLED", "false").lower() in ("true", "1", "yes")
AGENT_AUTONOMOUS_EXECUTION = False  # Disabled in Phase 3; must remain False until Phase 4 security
AGENT_MOCK_ONLY = False  # Phase 5: real restricted execution enabled (not autonomous)
AGENT_AUDIT_ENABLED = True
AGENT_MAX_ITERATIONS = int(os.getenv("VEYRA_AGENT_MAX_ITERATIONS", "10"))
AGENT_TIMEOUT_SECONDS = float(os.getenv("VEYRA_AGENT_TIMEOUT_SECONDS", "300"))
AGENT_PERMISSION_LEVEL = os.getenv("VEYRA_AGENT_PERMISSION_LEVEL", "restricted")
