#!/usr/bin/env python3
"""Agent framework: multi-step task state persistence and representation."""
from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from enum import Enum


class TaskState(str, Enum):
    RECEIVED = "received"
    PLANNING = "planning"
    INVESTIGATING = "investigating"
    WAITING_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MultiStepTaskState:
    """Explicit multi-step task state with persistence support."""

    def __init__(self, task_id: Optional[str] = None, objective: str = ""):
        self.task_id = task_id or f"task_{int(time.time() * 1000)}"
        self.objective = objective
        self.current_state = TaskState.RECEIVED
        self.states_history: List[Dict[str, Any]] = []
        self.created_at = time.time()
        self.updated_at = time.time()
        self.result_summary: Optional[str] = None
        self.errors: List[str] = []

    def transition_to(self, new_state: TaskState, note: str = ""):
        entry = {
            "from_state": self.current_state.value,
            "to_state": new_state.value,
            "timestamp": time.time(),
            "note": note,
        }
        self.states_history.append(entry)
        self.current_state = new_state
        self.updated_at = time.time()

    def is_terminal(self) -> bool:
        return self.current_state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "current_state": self.current_state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "states_history": self.states_history,
            "terminal": self.is_terminal(),
            "result_summary": self.result_summary,
            "errors": self.errors,
        }

    def recover_from_state(self, state_dict: Dict[str, Any]) -> bool:
        try:
            self.task_id = state_dict.get("task_id", self.task_id)
            self.objective = state_dict.get("objective", self.objective)
            self.current_state = TaskState(state_dict.get("current_state", self.current_state.value))
            self.states_history = list(state_dict.get("states_history", self.states_history))
            self.result_summary = state_dict.get("result_summary", self.result_summary)
            self.errors = list(state_dict.get("errors", self.errors))
            return True
        except Exception:
            return False
