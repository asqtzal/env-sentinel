"""Alert-related data models for the monitoring module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.9 compatibility
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]

from env_sentinel.sensors.models import SensorReading


class AlertLevel(str, Enum):
    """Severity levels for alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertCategory(str, Enum):
    """Categories describing the source of an alert."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    SENSOR = "sensor"


@dataclass
class Alert:
    """Normalized alert payload consumed by notifier modules."""

    level: AlertLevel
    category: AlertCategory
    subject: str
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    reading: Optional[SensorReading] = None
    details: dict[str, Any] = field(default_factory=dict)
