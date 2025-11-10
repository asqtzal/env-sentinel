"""Tests for the ConfigManager."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from env_sentinel.config import AppConfig
from env_sentinel.config.manager import ConfigManager


def write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_load_creates_default_when_missing(config_paths: tuple[Path, Path]) -> None:
    """Missing config file should be created from default and loaded."""
    active_path, default_path = config_paths
    manager = ConfigManager(active_path, default_path)

    config = manager.load()

    assert active_path.exists()
    assert config.to_dict() == load_json(active_path)


def test_save_persists_changes(config_paths: tuple[Path, Path]) -> None:
    """save() should write provided config to disk."""
    active_path, default_path = config_paths
    manager = ConfigManager(active_path, default_path)
    config = manager.load()
    updated = config.copy(update={"sensor": {"read_interval_seconds": 120}})

    manager.save(updated)

    stored = load_json(active_path)
    assert stored["sensor"]["read_interval_seconds"] == 120


def test_reload_if_updated_invokes_callback(config_paths: tuple[Path, Path]) -> None:
    """Reload should re-parse file and invoke callback."""
    active_path, default_path = config_paths
    manager = ConfigManager(active_path, default_path)
    manager.load()

    reloaded_configs: list[AppConfig] = []

    def on_reload(config: AppConfig) -> None:
        reloaded_configs.append(config)

    manager._on_reload = on_reload  # pylint: disable=protected-access

    data = load_json(active_path)
    data["sensor"]["failure_threshold"] = 4
    write_config(active_path, data)

    updated = manager.reload_if_updated()

    assert updated
    assert manager.config.sensor.failure_threshold == 4
    assert reloaded_configs and reloaded_configs[0].sensor.failure_threshold == 4


def test_reload_invalid_config_triggers_fallback(config_paths: tuple[Path, Path]) -> None:
    """Invalid configuration should fall back to defaults and call fallback callback."""
    active_path, default_path = config_paths
    manager = ConfigManager(active_path, default_path)
    manager.load()
    fallback_errors: list[ValidationError] = []

    manager._fallback_callback = lambda exc: fallback_errors.append(exc)  # pylint: disable=protected-access

    data = load_json(active_path)
    data["sensor"]["read_interval_seconds"] = 5  # below minimum
    write_config(active_path, data)

    manager.reload_if_updated()

    assert manager.config.sensor.read_interval_seconds == 60
    assert fallback_errors, "Fallback callback should be invoked"


def test_start_stop_polling(config_paths: tuple[Path, Path]) -> None:
    """Polling loop should pick up file changes."""
    active_path, default_path = config_paths
    reloaded = []

    def on_reload(config: AppConfig) -> None:
        reloaded.append(config)

    manager = ConfigManager(
        active_path,
        default_path,
        on_reload=on_reload,
        poll_interval_seconds=1,
    )
    manager.load()
    manager.start_polling()

    try:
        data = load_json(active_path)
        data["sensor"]["failure_threshold"] = 5
        write_config(active_path, data)

        timeout = time.time() + 5
        while time.time() < timeout and not reloaded:
            time.sleep(0.2)
    finally:
        manager.stop_polling()

    assert reloaded, "Polling should detect changes and trigger callback"
