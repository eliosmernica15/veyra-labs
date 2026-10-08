#!/usr/bin/env python3
"""Agent framework: clearly labeled mock/stub tools for framework architecture verification ONLY."""
# IMPORTANT: These are MOCK/STUB implementations. They must NEVER be presented as real file/command execution.
# Phase 4 must implement real, restricted, audited tool executions with workspace boundaries.

from __future__ import annotations

from agent.core.tool_interface import ToolSchema

MOCK_READ_FILE = ToolSchema(
    tool_name="read_file_mock",
    description="MOCK/STUB: Reads a permitted file. Does NOT perform real file access in Phase 3.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (must be within workspace)"},
        },
        "required": ["path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "status": {"type": "string"},
            "mock_warning": {"type": "string"},
        },
    },
    is_mock=True,
    permission_required="restricted",
    timeout_seconds=5.0,
    allowed_workspace_paths=[".", "datasets/", "ml/", "configs/", "tests/"],
)

MOCK_LIST_DIR = ToolSchema(
    tool_name="list_dir_mock",
    description="MOCK/STUB: Lists permitted directory contents. Does NOT perform real directory access in Phase 3.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string"},
            "mock_warning": {"type": "string"},
        },
    },
    is_mock=True,
    permission_required="restricted",
    timeout_seconds=5.0,
)

MOCK_SEARCH_PROJECT = ToolSchema(
    tool_name="search_project_mock",
    description="MOCK/STUB: Searches permitted project files. Does NOT run real search in Phase 3.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "workspace": {"type": "string"},
        },
        "required": ["pattern"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "matches": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string"},
            "mock_warning": {"type": "string"},
        },
    },
    is_mock=True,
    permission_required="restricted",
    timeout_seconds=10.0,
)

MOCK_RUN_TEST = ToolSchema(
    tool_name="run_test_mock",
    description="MOCK/STUB: Runs an explicitly permitted test command. Does NOT execute real tests in Phase 3.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Test command (must be in allowlist for Phase 4)"},
        },
        "required": ["command"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "object"},
            "status": {"type": "string"},
            "mock_warning": {"type": "string"},
        },
    },
    is_mock=True,
    permission_required="restricted",
    timeout_seconds=30.0,
)

MOCK_EDIT_FILE = ToolSchema(
    tool_name="edit_file_mock",
    description="MOCK/STUB: Applies a controlled file edit. Does NOT modify files in Phase 3.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "modified": {"type": "boolean"},
            "status": {"type": "string"},
            "mock_warning": {"type": "string"},
        },
    },
    is_mock=True,
    permission_required="standard",
    timeout_seconds=15.0,
)

ALL_MOCK_TOOLS = [
    MOCK_READ_FILE,
    MOCK_LIST_DIR,
    MOCK_SEARCH_PROJECT,
    MOCK_RUN_TEST,
    MOCK_EDIT_FILE,
]
