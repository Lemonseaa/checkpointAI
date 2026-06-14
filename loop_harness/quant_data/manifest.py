"""Manifest loading for real A-share data samples."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class AShareSampleManifestEntry(BaseModel):
    """One A-share market data sample described by a human-owned manifest."""

    ts_code: str
    name: str | None = None
    source_vendor: str
    adjusted_mode: str
    start_date: date
    end_date: date
    decision_grade: bool
    license_note: str
    file_path: str
    resolved_path: Path


class AShareSampleManifest(BaseModel):
    """A collection of A-share data samples."""

    entries: list[AShareSampleManifestEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> AShareSampleManifest:
        """Load a manifest and resolve entry paths relative to the manifest."""

        manifest_path = Path(path)
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = [
                cls._entry(entry, base_dir=manifest_path.parent, index=index)
                for index, entry in enumerate(raw.get("entries", []), start=1)
            ]
        except ValidationError as exc:
            raise ValueError(f"Manifest entry failed validation: {exc}") from exc
        except KeyError as exc:
            raise ValueError(f"Manifest entry missing required field: {exc}") from exc
        return cls(entries=entries)

    @staticmethod
    def _entry(raw: dict[str, Any], *, base_dir: Path, index: int) -> AShareSampleManifestEntry:
        try:
            file_path = str(raw["file_path"])
        except KeyError as exc:
            raise ValueError(f"Manifest entry {index} missing required field: file_path") from exc
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            resolved_path = base_dir / resolved_path
        try:
            return AShareSampleManifestEntry(
                **raw,
                resolved_path=resolved_path,
            )
        except ValidationError as exc:
            raise ValueError(f"Manifest entry {index} failed validation: {exc}") from exc
