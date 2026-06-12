"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root from any nested test module."""

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "loop_harness").is_dir():
            return parent
    raise RuntimeError("Could not locate Loop Harness project root")
