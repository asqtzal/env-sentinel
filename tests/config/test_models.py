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
    TemperatureThreshold,
)


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


def test_slack_channel_must_start_with_hash() -> None:
    """Slack channels must include the # prefix."""
    with pytest.raises(ValidationError):
        SlackConfig(channel="baby-room")
