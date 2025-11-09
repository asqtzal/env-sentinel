"""Tests for configuration Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydantic import ValidationError

from env_sentinel.config import (
    AppConfig,
    HumidityThreshold,
    SensorConfig,
    SlackConfig,
    SlackMentionPolicy,
    TemperatureThreshold,
)

from env_sentinel.config.manager import ConfigManager


def test_app_config_defaults_matches_file() -> None:
    """The AppConfig defaults should match the bundled JSON template."""
    config_path = Path("config/default_config.json")
    file_data = json.loads(config_path.read_text(encoding="utf-8"))
    assert AppConfig.defaults().to_dict() == file_data


def test_invalid_i2c_address_raises() -> None:
    """Only supported I2C addresses should be accepted."""
    with pytest.raises(ValidationError):
        SensorConfig(i2c_address="0x75")


def test_temperature_threshold_relationships() -> None:
    """Critical and nominal ranges must maintain logical order."""
    with pytest.raises(ValidationError):
        TemperatureThreshold(min=26.0, max=20.0)
    with pytest.raises(ValidationError):
        TemperatureThreshold(critical_min=20.0, min=18.0)
    with pytest.raises(ValidationError):
        TemperatureThreshold(max=26.0, critical_max=25.0)


def test_humidity_threshold_requires_min_lower_than_max() -> None:
    """Humidity minimum must be lower than maximum."""
    with pytest.raises(ValidationError):
        HumidityThreshold(min=60.0, max=40.0)


def test_humidity_threshold_requires_critical_outside_nominal() -> None:
    """Critical humidity thresholds must surround nominal range."""
    with pytest.raises(ValidationError):
        HumidityThreshold(min=40.0, max=60.0, critical_min=40.0)
    with pytest.raises(ValidationError):
        HumidityThreshold(min=40.0, max=60.0, critical_max=60.0)


def test_slack_channel_must_start_with_hash() -> None:
    """Slack channels must include the # prefix."""
    with pytest.raises(ValidationError):
        SlackConfig(channel="baby-room")


def test_slack_custom_mentions_require_targets() -> None:
    """Custom mention policy must include at least one user."""
    with pytest.raises(ValidationError):
        SlackConfig(alert_mention_policy=SlackMentionPolicy.CUSTOM, alert_mention_targets=[])


def test_slack_non_custom_policy_allows_empty_targets() -> None:
    """Predefined mention policies may omit explicit targets."""
    config = SlackConfig(alert_mention_policy=SlackMentionPolicy.NONE, alert_mention_targets=[])
    assert config.alert_mention_targets == []


def test_config_manager_reload_callback(tmp_path) -> None:
    """Reload callback can be attached after instantiation."""
    config_path = tmp_path / "app_config.json"
    default_path = Path("config/default_config.json")
    config_path.write_text(default_path.read_text(encoding="utf-8"), encoding="utf-8")

    manager = ConfigManager(config_path=config_path, default_path=default_path)
    manager.load()

    triggered: list[AppConfig] = []

    def on_reload(new_config: AppConfig) -> None:
        triggered.append(new_config)

    manager.set_reload_callback(on_reload)

    updated = AppConfig.defaults().copy(
        update={"sensor": {"read_interval_seconds": 120}}
    )
    config_path.write_text(json.dumps(updated.to_dict()), encoding="utf-8")

    assert manager.reload_if_updated() is True
    assert triggered and triggered[0].sensor.read_interval_seconds == 120
