#!/usr/bin/env python3
"""Agent framework: resource limits and cancellation support."""
from __future__ import annotations

import time
import signal
import threading
from typing import Optional, Dict, Any, List


class ResourceLimits:
    """Enforces resource limits against runaway agent execution.

    Requirements:
    - maximum agent iterations
    - per-tool timeout
    - overall task timeout
    - maximum terminal output
    - file-size limits
    - cancellation support (signal-based where supported)
    - protection against uncontrolled subprocess spawning
    """

    def __init__(
        self,
        max_iterations: int = 10,
        per_tool_timeout: float = 30.0,
        overall_task_timeout: float = 300.0,
        max_output_bytes: int = 1024 * 1024,
        max_file_size_bytes: int = 10 * 1024 * 1024,
    ):
        self.max_iterations = max(1, max_iterations)
        self.per_tool_timeout = max(1.0, per_tool_timeout)
        self.overall_task_timeout = max(10.0, overall_task_timeout)
        self.max_output_bytes = max(1024, max_output_bytes)
        self.max_file_size_bytes = max(1024, max_file_size_bytes)
        self.start_time = time.time()
        self.cancelled = False
        self._cancel_event = threading.Event()

    def reset_timer(self):
        self.start_time = time.time()

    def is_within_time_limit(self) -> bool:
        if self.cancelled:
            return False
        elapsed = time.time() - self.start_time
        return elapsed < self.overall_task_timeout

    def is_iteration_within_limit(self, current_iteration: int) -> bool:
        return current_iteration < self.max_iterations

    def check_output_size(self, content: str | bytes) -> bool:
        size = len(content) if isinstance(content, bytes) else len(str(content).encode("utf-8"))
        return size <= self.max_output_bytes

    def truncate_output(self, content: str | bytes, max_bytes: Optional[int] = None) -> str:
        max_b = max_bytes or self.max_output_bytes
        if isinstance(content, bytes):
            return content[:max_b].decode("utf-8", errors="replace")
        encoded = content.encode("utf-8")
        truncated_bytes = encoded[:max_b]
        return truncated_bytes.decode("utf-8", errors="replace")

    def check_file_size(self, file_path: str) -> Dict[str, Any]:
        try:
            size = 0
            import os
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
            else:
                return {"exists": False, "allowed": True, "reason": "File does not exist; no size check needed"}
            allowed = size <= self.max_file_size_bytes
            return {
                "exists": True,
                "size_bytes": size,
                "max_bytes": self.max_file_size_bytes,
                "allowed": allowed,
                "reason": "File within size limit" if allowed else f"File exceeds max size ({size} > {self.max_file_size_bytes})",
            }
        except Exception as exc:
            return {"exists": False, "allowed": False, "reason": f"Failed to check file size: {exc}"}

    def cancel(self):
        """Request cancellation (sets event)."""
        self.cancelled = True
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self.cancelled or self._cancel_event.is_set()

    def get_remaining_time(self) -> float:
        elapsed = time.time() - self.start_time
        return max(0.0, self.overall_task_timeout - elapsed)

    def get_limits_report(self) -> Dict[str, Any]:
        return {
            "max_iterations": self.max_iterations,
            "per_tool_timeout_seconds": self.per_tool_timeout,
            "overall_task_timeout_seconds": self.overall_task_timeout,
            "max_output_bytes": self.max_output_bytes,
            "max_file_size_bytes": self.max_file_size_bytes,
            "cancelled": self.cancelled,
            "remaining_seconds": self.get_remaining_time(),
        }
