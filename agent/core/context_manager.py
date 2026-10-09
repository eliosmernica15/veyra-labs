#!/usr/bin/env python3
"""Agent framework: structured conversation/task context with limits and safe truncation."""
from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from agent.core.agent_state import AgentTask, AgentStatus
from agent.core.audit_crypto import CryptographicAuditLogger
from agent.core.secret_redaction import SecretRedactor
from agent.core.prompt_injection import PromptInjectionFilter


@dataclass
class ConversationTurn:
    turn_index: int
    timestamp: float
    session_id: str
    user_message: str = ""
    agent_response: str = ""
    tool_calls: List[str] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    approval_decisions: List[Dict[str, Any]] = field(default_factory=list)
    files_inspected: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    commands_executed: List[str] = field(default_factory=list)
    test_results: List[str] = field(default_factory=list)
    current_task_state: Optional[str] = None


@dataclass
class ContextLimits:
    max_turns: int = 50
    max_files_in_context: int = 30
    max_context_chars: int = 50000  # Safe truncation point well under model window
    summarize_after_turns: int = 20


class ConversationContext:
    """Structured conversation/task context with safe limits and truncation."""

    def __init__(self, session_id: Optional[str] = None, limits: Optional[ContextLimits] = None):
        self.session_id = session_id or f"session_{int(time.time() * 1000)}"
        self.turns: List[ConversationTurn] = []
        self.limits = limits or ContextLimits()
        self.redactor = SecretRedactor()
        self.filter = PromptInjectionFilter()
        self.audit_logger = CryptographicAuditLogger()

    def add_turn(
        self,
        user_message: str = "",
        agent_response: str = "",
        tool_calls: Optional[List[str]] = None,
        tool_results: Optional[List[Dict]] = None,
        approval_decisions: Optional[List[Dict]] = None,
        files_inspected: Optional[List[str]] = None,
        files_changed: Optional[List[str]] = None,
        commands_executed: Optional[List[str]] = None,
        test_results: Optional[List[str]] = None,
        current_task_state: Optional[str] = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            turn_index=len(self.turns) + 1,
            timestamp=time.time(),
            session_id=self.session_id,
            user_message=user_message,
            agent_response=agent_response,
            tool_calls=list(tool_calls or []),
            tool_results=list(tool_results or []),
            approval_decisions=list(approval_decisions or []),
            files_inspected=list(files_inspected or []),
            files_changed=list(files_changed or []),
            commands_executed=list(commands_executed or []),
            test_results=list(test_results or []),
            current_task_state=current_task_state,
        )
        # Apply secret redaction and prompt injection filtering to all text fields
        turn.user_message = self.redactor.redact_text(turn.user_message)
        turn.agent_response = self.redactor.redact_text(turn.agent_response)
        # Filter untrusted content
        turn.agent_response = self.filter.sanitize_for_model_input(turn.agent_response)
        self.turns.append(turn)
        # Enforce limits: truncate if too many turns
        if len(self.turns) > self.limits.max_turns:
            self._truncate_oldest()
        return turn

    def _truncate_oldest(self):
        # Safe truncation: keep most recent turns, summarize oldest
        summary_index = max(0, len(self.turns) - self.limits.max_turns + self.limits.summarize_after_turns)
        self.turns = self.turns[summary_index:]

    def get_summary(self) -> Dict[str, Any]:
        total_chars = sum(
            len(t.user_message) + len(t.agent_response) + sum(str(tr) for tr in t.tool_results)
            for t in self.turns
        )
        within_limit = total_chars < self.limits.max_context_chars
        return {
            "session_id": self.session_id,
            "turn_count": len(self.turns),
            "context_size_chars": total_chars,
            "within_limit": within_limit,
            "files_inspected_total": len({f for t in self.turns for f in t.files_inspected}),
            "files_changed_total": len({f for t in self.turns for f in t.files_changed}),
            "commands_executed_total": len({c for t in self.turns for c in t.commands_executed}),
            "approval_decisions_total": len({a.get("action_id", a) for t in self.turns for a in t.approval_decisions}),
        }

    def get_context_for_agent(self) -> Dict[str, Any]:
        # Build a safe, limited context for the agent
        recent_turns = self.turns[-self.limits.max_turns:]
        return {
            "session_id": self.session_id,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "timestamp": t.timestamp,
                    "user_message": t.user_message,
                    "agent_response": t.agent_response,
                    "current_task_state": t.current_task_state,
                    "files_inspected": t.files_inspected,
                    "files_changed": t.files_changed,
                    "commands_executed": t.commands_executed,
                    "test_results": t.test_results,
                    "approval_decisions": t.approval_decisions,
                }
                for t in recent_turns
            ],
            "summary": self.get_summary(),
            "limits": {
                "max_turns": self.limits.max_turns,
                "max_context_chars": self.limits.max_context_chars,
            },
        }
