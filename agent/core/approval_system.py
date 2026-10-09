#!/usr/bin/env python3
"""Agent framework: approval system for high-impact actions with explicit user authorization."""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from enum import Enum
import time


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    AUTO_DENIED = "auto_denied"


class ApprovalSystem:
    """Explicit approval mechanism for high-impact agent actions.

    The agent must NOT be able to approve its own high-impact actions.
    Approval must come from an external/user-controlled mechanism.
    """

    def __init__(self, approval_timeout_seconds: float = 300.0):
        self.approvals: Dict[str, Dict[str, Any]] = {}
        self.approval_timeout_seconds = approval_timeout_seconds
        # Protection: approval system must be protected from agent modification
        self._protected_keys = {"approval_timeout_seconds", "approvals"}

    def request_approval(self, action_id: str, action_description: str, permission_level: str, reason: str = "") -> Dict[str, Any]:
        """Create an approval request. Does NOT auto-approve."""
        request = {
            "action_id": action_id,
            "action_description": action_description,
            "permission_level": permission_level,
            "reason": reason,
            "status": ApprovalStatus.PENDING.value,
            "requested_at": time.time(),
            "approved_by": None,
            "denied_by": None,
            "approval_note": None,
        }
        self.approvals[action_id] = request
        return {
            "approval_id": action_id,
            "status": ApprovalStatus.PENDING.value,
            "requires_approval": True,
            "auto_approved": False,
            "message": f"Approval required for action '{action_description}' at permission level '{permission_level}'.",
        }

    def approve_action(self, action_id: str, approved_by: str, note: str = "User authorization") -> Dict[str, Any]:
        """Explicitly approve an action from an external/user-controlled source.

        This method must be called by a user or external authorization service,
        not by the agent itself.
        """
        if action_id not in self.approvals:
            return {"approved": False, "reason": f"Approval request '{action_id}' not found", "status": ApprovalStatus.DENIED.value}
        request = self.approvals[action_id]
        # Check expiration
        if time.time() - request["requested_at"] > self.approval_timeout_seconds:
            request["status"] = ApprovalStatus.EXPIRED.value
            return {"approved": False, "reason": "Approval request expired", "status": ApprovalStatus.EXPIRED.value}
        request["status"] = ApprovalStatus.APPROVED.value
        request["approved_by"] = approved_by
        request["approval_note"] = note
        return {
            "approved": True,
            "action_id": action_id,
            "status": ApprovalStatus.APPROVED.value,
            "approved_by": approved_by,
            "note": note,
            "message": "Approval granted by external authorization.",
        }

    def deny_action(self, action_id: str, denied_by: str = "system", note: str = "Denied by policy or user") -> Dict[str, Any]:
        """Deny an approval request."""
        if action_id not in self.approvals:
            return {"approved": False, "reason": f"Approval request '{action_id}' not found", "status": ApprovalStatus.DENIED.value}
        request = self.approvals[action_id]
        request["status"] = ApprovalStatus.DENIED.value
        request["denied_by"] = denied_by
        request["approval_note"] = note
        return {
            "approved": False,
            "action_id": action_id,
            "status": ApprovalStatus.DENIED.value,
            "denied_by": denied_by,
            "note": note,
            "message": "Approval denied.",
        }

    def is_approved(self, action_id: str) -> bool:
        if action_id not in self.approvals:
            return False
        request = self.approvals[action_id]
        # If expired, deny
        if time.time() - request["requested_at"] > self.approval_timeout_seconds:
            request["status"] = ApprovalStatus.EXPIRED.value
            return False
        return request["status"] == ApprovalStatus.APPROVED.value

    def check_approval_status(self, action_id: str) -> Dict[str, Any]:
        if action_id not in self.approvals:
            return {"found": False, "status": "unknown"}
        request = self.approvals[action_id]
        return {
            "found": True,
            "status": request["status"],
            "requested_at": request["requested_at"],
            "approved_by": request.get("approved_by"),
            "approval_note": request.get("approval_note"),
        }

    def get_pending_approvals(self) -> List[str]:
        return [k for k, v in self.approvals.items() if v["status"] == ApprovalStatus.PENDING.value]

    def auto_deny_expired(self) -> int:
        """Auto-deny expired approvals (not automatic approval)."""
        count = 0
        for action_id, request in self.approvals.items():
            if request["status"] == ApprovalStatus.PENDING.value:
                if time.time() - request["requested_at"] > self.approval_timeout_seconds:
                    request["status"] = ApprovalStatus.EXPIRED.value
                    request["denied_by"] = "system_expiry"
                    request["approval_note"] = "Expired before approval granted."
                    count += 1
        return count

    def is_protected(self, key: str) -> bool:
        return key in self._protected_keys
