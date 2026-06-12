"""Candidate generation boundaries for safe workflow optimization."""

from __future__ import annotations

from pydantic import BaseModel


class CandidateChange(BaseModel):
    """One proposed workflow change before shadow validation."""

    change_type: str
    magnitude: float = 0.0
    target: str | None = None


class CandidateBoundaryResult(BaseModel):
    """Allowed/blocked classification for one candidate change."""

    level: str
    reason: str


class CandidateBoundary:
    """Keep candidate generation bounded to evidence-safe changes."""

    ALLOWED = {"prompt_patch", "parameter_tune", "node_toggle", "adapter_config"}
    BLOCKED = {"auto_live_trade", "auto_publish", "workflow_rewrite", "delete_data"}

    def classify(self, change: CandidateChange) -> CandidateBoundaryResult:
        """Classify a candidate change without executing it."""

        if change.change_type in self.BLOCKED:
            return CandidateBoundaryResult(level="blocked", reason=f"{change.change_type} is never auto-generated.")
        if change.change_type not in self.ALLOWED:
            return CandidateBoundaryResult(level="approval", reason=f"{change.change_type} requires human review.")
        if change.magnitude > 0.3:
            return CandidateBoundaryResult(level="approval", reason="Large change magnitude requires human review.")
        return CandidateBoundaryResult(level="allowed", reason="Small bounded candidate change.")
