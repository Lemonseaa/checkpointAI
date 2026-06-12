"""Minimal adapter SDK contract for external workflow producers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WorkflowAdapterSDK(ABC):
    """Small interface external workflow adapters can implement."""

    @abstractmethod
    def describe_workflow(self) -> dict[str, Any]:
        """Return workflow structure and configurable surfaces."""

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute one external workflow run."""

    @abstractmethod
    def export_trace(self, run_id: str) -> list[dict[str, Any]]:
        """Return trace events for one run."""

    @abstractmethod
    def export_metrics(self, run_id: str) -> dict[str, float]:
        """Return metrics for one run."""
