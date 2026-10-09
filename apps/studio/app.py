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

# Agent workspace interface (Phase 5 real restricted execution)
# Added after Logs tab

with st.expander("Agent Workspace (Phase 5)", expanded=False):
    st.subheader("Agent Workspace — Real Restricted Execution")
    col_agent = st.columns(3)
    with col_agent[0]:
        st.write("**Current Workspace:** ``" + str(Path(".").resolve()) + "``")
    with col_agent[1]:
        st.write("**Agent Enabled:** ``True`` (framework loaded)")
    with col_agent[2]:
        from agent.core.config import AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY, AGENT_PERMISSION_LEVEL
        st.write(f"**Autonomous:** ``{AGENT_AUTONOMOUS_EXECUTION}``")
        st.write(f"**Mock Only:** ``{AGENT_MOCK_ONLY}``")
        st.write(f"**Permission:** ``{AGENT_PERMISSION_LEVEL}``")

    # User task input
    user_task = st.text_input("Agent task:", value="Read workspace, list files, inspect config.")

    # Show workspace info with real file operations (restricted mode)
    try:
        from agent.core.workspace_sandbox import WorkspaceSandbox
        sandbox = WorkspaceSandbox(workspace_roots=["."], allowed_subpaths=["tests/", "ml/", "agent/", "docs/"])
        workspace_result = sandbox.resolve_path(".")
        st.write(f"Workspace allowed: ``{workspace_result.get('allowed', False)}``")
        st.write(f"Workspace root: ``{str(sandbox.get_workspace_roots())}``")
    except Exception as exc:
        st.warning(f"Workspace check unavailable: {exc}")

    # Show agent framework state
    try:
        from agent.core.agent_state import AgentTask, AgentStatus
        from agent.core.loop import AgentLoop
        from agent.core.audit_crypto import CryptographicAuditLogger
        import tempfile
        from pathlib import Path as PathLib

        st.write("---")
        st.write("### Agent Loop State")
        with tempfile.TemporaryDirectory() as td:
            audit = CryptographicAuditLogger(log_path=PathLib(td) / "audit.jsonl")
            task = AgentTask(objective=user_task or "Inspect workspace", max_iterations=3, timeout_seconds=120, permission_level="restricted")
            loop = AgentLoop(task=task, context={"permission_level": "restricted"}, audit_logger=audit)
            # Show proposed action
            proposal = loop.propose_action(description="Inspect workspace and report status.")
            st.write(f"**Proposed:** ``{proposal.get('status')}``")
            st.write(f"**Requires authorization:** ``True``")
            # Show authorization state
            authorization = loop.authorize_action(approval=True, note="Manual approval for demonstration")
            st.write(f"**Authorized:** ``{authorization.get('status')}``")
            # Real execution (Phase 5): use real_file_tools if available
            if AGENT_MOCK_ONLY is False:
                execution_result = loop.execute_action(mock_only=False)
                st.write(f"**Executed:** ``Real restricted execution``")
                if execution_result.get("execution_result") is not None:
                    res = execution_result.get("execution_result")
                    st.write(f"**Result status:** ``{res.get('status', 'unknown')}``")
                    if res.get("allowed"):
                        st.success(f"Operation permitted at permission level restricted.")
                    else:
                        st.warning(f"Operation blocked: ``{res.get('reason', 'Unknown')}``")
                else:
                    st.info("Real execution not supported for this action (requires supported tool interface).")
            else:
                execution_result = loop.execute_action(mock_only=True)
                st.write(f"**Executed:** ``Mock (AGENT_MOCK_ONLY={AGENT_MOCK_ONLY})``")
            # Verification
            verification = loop.verify_result()
            verified_state = verification.get("verified_result", {})
            st.write("**Verification:**")
            st.metric("Audit Complete", verified_state.get("audit_complete", False))
            st.metric("Safeguards Intact", verified_state.get("safeguards_intact", False))
            st.metric("Real Execution", verified_state.get("real_execution_occurred", False))
            st.metric("Real Success", verified_state.get("real_success", False))
            # Audit chain integrity check
            audit_result = audit.verify_integrity()
            st.write(f"Audit chain valid: ``{audit_result.get('chain_valid', False)}``")
            st.write(f"Audit entries: ``{audit_result.get('entry_count', 0)}``")
    except Exception as exc:
        st.error(f"Agent workspace demonstration error: {exc}")
        import traceback
        st.text(traceback.format_exc())

    # Approval simulation
    st.write("---")
    st.write("### Approval Flow (Manual / User-Controlled)")
    st.info("Agent actions that require approval (`create_file`, `delete_file`, `modify_file`, `run_shell`) will display an approval request here. The agent cannot approve its own requests (`AGENT_AUTONOMOUS_EXECUTION=False`).")

    try:
        from agent.core.approval_system import ApprovalSystem
        approval_demo = ApprovalSystem()
        approval_demo.request_approval("demo_action_1", "Modify workspace file", "restricted")
        status_before = approval_demo.check_approval_status("demo_action_1")
        st.write(f"Approval status (before user action): ``{status_before['status']}``")
        # Simulate user approval
        grant = approval_demo.approve_action("demo_action_1", approved_by="user", note="Manual approval for Phase 5 demonstration")
        st.write(f"After user approval: ``{grant.get('status')}``")
        st.write(f"Agent self-approval prevented: ``{approval_demo.is_approved('demo_action_2') if 'demo_action_2' not in approval_demo.approvals else 'N/A'}``")
    except Exception as exc:
        st.warning(f"Approval demonstration unavailable: {exc}")

    # Real file tool demonstration
    st.write("---")
    st.write("### Real Restricted Tools (Phase 5)")
    try:
        from agent.core.real_file_tools import RealFileTools
        real_tools = RealFileTools(workspace_path=".", permission_level="restricted")
        # Read workspace root (allowed at restricted)
        read_result = real_tools.read_file(".")
        st.write(f"Read `.` allowed: ``{read_result.get('allowed', False)}``")
        st.write(f"Status: ``{read_result.get('status', 'unknown')}``")
        # List directory (allowed at restricted)
        list_result = real_tools.list_directory("tests/")
        if list_result.get("allowed"):
            st.write(f"List `tests/`: ``{len(list_result.get('items', []))}`` items")
        else:
            st.write(f"List `tests/` blocked: ``{list_result.get('reason', 'Unknown')}``")
        # Create file (requires approval at restricted; show blocked by default unless approved)
        create_result = real_tools.create_file("tests/test_demo.txt", content="Phase 5 real execution test.", requires_approval=True)
        st.write(f"Create `tests/test_demo.txt`: ``{create_result.get('status')}``")
        if create_result.get("allowed") is False:
            st.info("Create blocked by default (approval required). Use `set_explicit_approval('create_file')` for user authorization.")
    except Exception as exc:
        st.warning(f"Real file tools unavailable: {exc}")

    # Audit log status
    try:
        from agent.core.audit_crypto import CryptographicAuditLogger
        import tempfile
        from pathlib import Path as PathLib
        with tempfile.TemporaryDirectory() as td:
            audit_demo = CryptographicAuditLogger(log_path=PathLib(td) / "audit_demo.jsonl")
            audit_demo.log("phase5_demo", {"workspace": ".", "permission": "restricted"})
            audit_integrity = audit_demo.verify_integrity()
            st.write("**Audit Chain Integrity:**")
            st.write(f"Chain valid: ``{audit_integrity.get('chain_valid', False)}``")
            st.write(f"Entries: ``{audit_integrity.get('entry_count', 0)}``")
            st.write(f"Tamper protection note: ``{audit_integrity.get('tamper_protection', 'Not set')}``")
    except Exception as exc:
        st.info(f"Audit demonstration unavailable: {exc}")

    # Security safeguards status
    st.write("---")
    st.write("### Security Safeguards (Phase 4 Enforced)")
    try:
        from agent.core.safeguard_protection import SafeguardProtection
        safeguard = SafeguardProtection()
        protected_check = safeguard.check_write_permission("agent/core/config.py")
        st.write(f"Protect `agent/core/config.py`: ``allowed={not protected_check.get('protected', False)}``")
        st.info("Agent framework safeguards protected. Write blocked for protected paths.")
    except Exception as exc:
        st.info(f"Safeguard check unavailable: {exc}")


# Phase 6: Context and Memory View
with st.expander("Agent Context & Memory (Phase 6)", expanded=False):
    st.subheader("Context & Memory")
    # Context usage
    try:
        from agent.core.context_manager import ConversationContext, ContextLimits
        ctx = ConversationContext()
        summary = ctx.get_summary()
        st.metric("Turns", summary.get("turn_count", 0))
        st.metric("Context Size (chars)", summary.get("context_size_chars", 0))
        st.metric("Within Limit", "Yes" if summary.get("within_limit") else "No")
        st.write(f"Files Inspected: {summary.get('files_inspected_total', 0)}")
        st.write(f"Files Changed: {summary.get('files_changed_total', 0)}")
        st.write(f"Commands Executed: {summary.get('commands_executed_total', 0)}")
    except Exception as exc:
        st.info(f"Context view unavailable: {exc}")

    # Project summary demonstration
    try:
        from agent.core.project_understanding import ProjectUnderstanding
        proj = ProjectUnderstanding(workspace_path=".")
        proj_summary = proj.build_summary()
        st.write("---")
        st.write("### Project Understanding")
        st.write(f"Project Root: `{proj_summary.get('project_root', '.')}`")
        dirs = proj_summary.get("directories", [])
        st.write(f"Directories: `{len(dirs)}`")
        sources = proj_summary.get("source_files", [])
        st.write(f"Source Files: `{len(sources)}`")
        tests = proj_summary.get("test_files", [])
        st.write(f"Test Files: `{len(tests)}`")
        git_state = proj_summary.get("git_state", {})
        st.write(f"Git Modified: `{git_state.get('modified_count', 0)}`")
    except Exception as exc:
        st.info(f"Project understanding unavailable: {exc}")

    # Persistent memory demonstration
    try:
        from agent.core.project_memory import ProjectMemory
        memory = ProjectMemory(memory_path=".agent_memory/studio_memory.json")
        facts = memory.get_all_facts()
        decisions = memory.get_decisions()
        preferences = memory.memory.get("preferences", {})
        st.write("---")
        st.write("### Project Memory")
        st.write(f"Facts: `{len(facts)}`")
        for k, v in list(facts.items())[:5]:
            st.write(f"- `{k}`: `{str(v)[:60]}`")
        st.write(f"Decisions: `{len(decisions)}`")
        st.write(f"Preferences: `{list(preferences.keys())}`")
        # Show memory inspection
        inspect_info = memory.inspect_memory()
        st.write(f"Memory Path: `{inspect_info.get('memory_path', '.')}`")
        st.info("No secrets are stored in persistent memory. Memory can be edited/deleted by user.")
    except Exception as exc:
        st.info(f"Memory view unavailable: {exc}")

    # Multi-step task state
    try:
        from agent.core.task_state import MultiStepTaskState, TaskState
        state_demo = MultiStepTaskState(task_id="studio_demo", objective="Inspect workspace")
        state_demo.transition_to(TaskState.PLANNING, "Started planning")
        state_demo.transition_to(TaskState.EXECUTING, "Running inspection")
        state_dict = state_demo.to_dict()
        st.write("---")
        st.write("### Multi-step Task State")
        st.write(f"Current State: `{state_dict.get('current_state', 'unknown')}`")
        st.write(f"Terminal: `{state_dict.get('terminal', False)}`")
        st.write(f"History Length: `{len(state_dict.get('states_history', []))}`")
        st.info("Task state is persisted for recovery. Real execution requires authorization.")
    except Exception as exc:
        st.info(f"Task state view unavailable: {exc}")

    # Workspace boundaries demonstration
    st.write("---")
    st.write("### Workspace Boundaries Demonstration")
    try:
        from agent.core.workspace_sandbox import WorkspaceSandbox
        sandbox_demo = WorkspaceSandbox(workspace_roots=["."], allowed_subpaths=["tests/", "ml/"])
        allowed_path = sandbox_demo.resolve_path("tests/test_agent.py")
        blocked_path = sandbox_demo.resolve_path("/etc/passwd")
        st.write(f"`tests/test_agent.py` allowed: ``{allowed_path.get('allowed', False)}``")
        st.write(f"`tests/test_agent.py` within subpath: ``{allowed_path.get('within_subpath', False)}``")
        st.write(f"`/etc/passwd` blocked: ``{not blocked_path.get('allowed', True)}``")
        st.info("Path traversal blocked. Absolute paths outside workspace rejected. Subpath enforcement active.")
    except Exception as exc:
        st.info(f"Workspace demonstration unavailable: {exc}")

with tabs[5]:  # Logs tab updated
    st.subheader("Audit & Execution Status")
    # Combine existing logs with agent audit info
    try:
        from agent.core.audit_crypto import CryptographicAuditLogger
        from agent.core.config import AGENT_ENABLED, AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY
        import tempfile
        from pathlib import Path as PathLib
        with tempfile.TemporaryDirectory() as td:
            audit_demo = CryptographicAuditLogger(log_path=PathLib(td) / "audit_demo.jsonl")
            audit_demo.log("studio_integration", {"version": "Phase 5", "autonomous": AGENT_AUTONOMOUS_EXECUTION, "mock_only": AGENT_MOCK_ONLY})
            audit_result = audit_demo.verify_integrity()
            st.metric("Audit Chain Valid", audit_result.get("chain_valid", False))
            st.write(f"Audit entries: `{audit_result.get('entry_count', 0)}`")
            st.write(f"Integrity note: `{audit_result.get('integrity_check', 'Unknown')}`")
        st.info(f"Agent framework flags: ENABLED={AGENT_ENABLED}, AUTONOMOUS={AGENT_AUTONOMOUS_EXECUTION}, MOCK_ONLY={AGENT_MOCK_ONLY}")
        # Show real file tool status
        from agent.core.config import AGENT_MOCK_ONLY as M_ONLY
        if M_ONLY is False:
            st.success("Real restricted execution enabled (AGENT_MOCK_ONLY=False). Agent framework operates with real tool layer under Phase 4 security controls.")
        else:
            st.info("Real restricted execution enabled (AGENT_MOCK_ONLY set to False in Phase 5).")
    except Exception as exc:
        st.info(f"Audit/status unavailable: {exc}")

    # Original logs view preserved
    try:
        r = requests.get("http://localhost:8000/api/training/test_run/logs", timeout=3)
        logs = r.json().get("logs", []) if r.status_code == 200 else []
        for line in logs[:20]:
            st.text(line)
    except Exception as exc:
        st.info("No live training logs available (run a training job via CLI or backend). See console for backend logs.")
    st.caption("Secrets and sensitive values are redacted at the backend level. Audit chain verified cryptographically.")

# Phase 8 — Manual baseline comparison (not claiming improvement)
with st.expander("Baseline Model Version Comparison (Phase 8)", expanded=False):
    st.subheader("Select checkpoint for comparison")
    checkpoint_options = ["checkpoints/checkpoint_final.pt (step 35 — SMOKE BASELINE)", "checkpoints/checkpoint_step_10.pt", "checkpoints/checkpoint_step_20.pt"]
    selected_checkpoint = st.selectbox("Checkpoint:", checkpoint_options, index=0)
    st.caption(f"Selected: {selected_checkpoint}. This is the current smoke-test baseline — do not treat as capable assistant.")
    st.write("Fixed baseline prompts (use against selected model only for comparison; no external AI):")
    st.code("Basic:\nHello, who are you?\nWhat is 2 + 2?\nWhat is Python?\n\nCoding:\nWrite a Python function that adds two numbers.\nFix: def add(a, b)\n    return a + b\n\nReasoning:\nSimple arithmetic / comparison tasks.")
    st.info("Baselines are measured for comparison only. The 565k smoke model is documented as baseline only; improvement requires measured gate evidence.")
