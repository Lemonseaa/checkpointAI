"""Trace normalization helpers for external workflow adapters."""

from __future__ import annotations

from typing import Any

from loop_harness.evidence.models import TraceEvent


class TraceNormalizer:
    """Convert loose external trace dictionaries into TraceEvent objects."""

    def normalize(self, events: list[dict[str, Any]]) -> list[TraceEvent]:
        """Normalize common trace field aliases."""

        normalized: list[TraceEvent] = []
        for event in events:
            node_id = str(event.get("node_id") or event.get("node") or event.get("step_id") or "unknown")
            status = str(event.get("status") or ("succeeded" if event.get("ok") is True else "unknown"))
            normalized.append(
                TraceEvent(
                    node_id=node_id,
                    status=status,
                    duration_ms=self._float_or_none(event.get("duration_ms", event.get("latency"))),
                    cost=self._float_or_none(event.get("cost")),
                    input_summary=self._text_or_none(event.get("input_summary", event.get("input"))),
                    output_summary=self._text_or_none(event.get("output_summary", event.get("output"))),
                    metrics=event.get("metrics", {}),
                    error=self._text_or_none(event.get("error")),
                    metadata={key: value for key, value in event.items() if key not in {"metrics"}},
                )
            )
        return normalized

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if isinstance(value, int | float):
            return float(value)
        return None

    @staticmethod
    def _text_or_none(value: Any) -> str | None:
        if value is None:
            return None
        return str(value)
