"""Configuration models for Env-Sentinel."""

from __future__ import annotations

import json

from pathlib import Path
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, root_validator, validator

ALLOWED_I2C_ADDRESSES = {"0x76", "0x77"}
ALLOWED_CLOUD_PROVIDERS = {"aws"}


class SensorConfig(BaseModel):
    """Configuration values for the sensor subsystem."""

    type: str = Field(default="BME280", regex=r"^[A-Za-z0-9_-]+$")
    i2c_address: str = Field(default="0x76")
    read_interval_seconds: int = Field(default=60, ge=10, le=3600)
    failure_threshold: int = Field(default=3, ge=1, le=10)

    @validator("i2c_address")
    def validate_i2c_address(cls, value: str) -> str:
        """Ensure the configured I2C address is supported."""
        if value not in ALLOWED_I2C_ADDRESSES:
            raise ValueError(f"I2C address must be one of {ALLOWED_I2C_ADDRESSES}")
        return value


class TemperatureThreshold(BaseModel):
    """Temperature thresholds for alerting."""

    min: float = Field(default=18.0, ge=-40.0, le=60.0)
    max: float = Field(default=26.0, ge=-40.0, le=60.0)
    critical_min: float = Field(default=10.0, ge=-50.0, le=60.0)
    critical_max: float = Field(default=35.0, ge=-40.0, le=80.0)

    @root_validator
    def validate_relationships(cls, values: Dict[str, float]) -> Dict[str, float]:
        """Validate logical relationships between temperature thresholds."""
        critical_min = values.get("critical_min")
        min_value = values.get("min")
        max_value = values.get("max")
        critical_max = values.get("critical_max")

        if min_value is not None and max_value is not None and min_value >= max_value:
            raise ValueError("temperature.min must be lower than temperature.max")
        if (
            critical_min is not None
            and min_value is not None
            and critical_min >= min_value
        ):
            raise ValueError("temperature.critical_min must be lower than temperature.min")
        if (
            critical_max is not None
            and max_value is not None
            and critical_max <= max_value
        ):
            raise ValueError("temperature.critical_max must be higher than temperature.max")
        return values


class HumidityThreshold(BaseModel):
    """Humidity thresholds for alerting."""

    min: float = Field(default=40.0, ge=0.0, le=100.0)
    max: float = Field(default=60.0, ge=0.0, le=100.0)
    critical_min: float = Field(default=1.0, ge=0.0, le=100.0)
    critical_max: float = Field(default=99.0, ge=0.0, le=100.0)

    @root_validator
    def validate_bounds(cls, values: Dict[str, float]) -> Dict[str, float]:
        """Ensure humidity min/max and critical ranges are logically ordered."""
        min_value = values.get("min")
        max_value = values.get("max")
        critical_min = values.get("critical_min")
        critical_max = values.get("critical_max")
        if min_value is not None and max_value is not None and min_value >= max_value:
            raise ValueError("humidity.min must be lower than humidity.max")
        if (
            critical_min is not None
            and min_value is not None
            and critical_min >= min_value
        ):
            raise ValueError("humidity.critical_min must be lower than humidity.min")
        if (
            critical_max is not None
            and max_value is not None
            and critical_max <= max_value
        ):
            raise ValueError("humidity.critical_max must be higher than humidity.max")
        return values


class AlertConfig(BaseModel):
    """Aggregated alert thresholds."""

    temperature: TemperatureThreshold = Field(default_factory=TemperatureThreshold)
    humidity: HumidityThreshold = Field(default_factory=HumidityThreshold)


class SlackMentionPolicy(str, Enum):
    """Allowed mention strategies for Slack notifications."""

    NONE = "none"
    HERE = "here"
    CHANNEL = "channel"
    CUSTOM = "custom"


class SlackConfig(BaseModel):
    """Slack notification settings."""

    channel: str = Field(default="#baby-room", min_length=1)
    report_interval_seconds: int = Field(default=1800, ge=300, le=7200)
    rate_limit_per_minute: int = Field(default=1, ge=1, le=5)
    alert_mention_policy: SlackMentionPolicy = Field(default=SlackMentionPolicy.CUSTOM)
    alert_mention_targets: List[str] = Field(default_factory=lambda: ["U0000000000"])

    @validator("channel")
    def validate_channel(cls, value: str) -> str:
        """Ensure the Slack channel looks valid."""
        if not value.startswith("#"):
            raise ValueError("Slack channel must start with '#'")
        return value

    @root_validator
    def validate_mention_targets(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure custom mention policy is accompanied by at least one user."""
        policy = values.get("alert_mention_policy")
        targets = values.get("alert_mention_targets") or []
        if policy == SlackMentionPolicy.CUSTOM and not targets:
            raise ValueError("alert_mention_targets must be set when mention policy is 'custom'")
        return values


class NotificationsConfig(BaseModel):
    """Notification subsystem configuration."""

    slack: SlackConfig = Field(default_factory=SlackConfig)


class StorageConfig(BaseModel):
    """Storage behavior configuration."""

    db_path: Path = Field(default=Path("data/env_sentinel.db"))
    local_retention_days: int = Field(default=90, ge=1, le=365)
    cloud_sync_interval_seconds: int = Field(default=300, ge=60, le=3600)
    cloud_provider: str = Field(default="aws")

    @validator("db_path", pre=True)
    def validate_db_path(cls, value: Any) -> Path:
        """Ensure the db path is present and normalized."""
        if value in (None, "", " "):
            raise ValueError("db_path must not be empty")
        if isinstance(value, Path):
            return value
        return Path(str(value))

    @validator("cloud_provider")
    def validate_provider(cls, value: str) -> str:
        """Restrict storage cloud providers."""
        if value not in ALLOWED_CLOUD_PROVIDERS:
            raise ValueError(f"cloud_provider must be one of {ALLOWED_CLOUD_PROVIDERS}")
        return value


class AppConfig(BaseModel):
    """Top-level configuration model."""

    sensor: SensorConfig = Field(default_factory=SensorConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def defaults(cls) -> "AppConfig":
        """Return an AppConfig populated with default values."""
        return cls()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create a configuration from a plain dictionary."""
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the configuration to a dictionary."""
        return json.loads(self.json())
