"""Fixtures for configuration tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def config_paths(tmp_path: Path) -> Iterator[tuple[Path, Path]]:
    """Create temporary active and default config paths."""
    default_src = Path("config/default_config.json")
    default_copy = tmp_path / "default_config.json"
    default_copy.write_text(default_src.read_text(encoding="utf-8"), encoding="utf-8")

    active_path = tmp_path / "app_config.json"
    yield active_path, default_copy
