"""Sensor data models and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.9 compatibility
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]
from typing import Optional

TEMPERATURE_MIN = -40.0
TEMPERATURE_MAX = 85.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0


@dataclass
class SensorReading:
    """Single sensor reading for temperature, humidity, and optional pressure."""

    timestamp: datetime
    temperature: float
    humidity: float
    pressure: Optional[float] = None
    sensor_id: str = "sensor-001"
    is_valid: bool = True
    invalid_fields: tuple[str, ...] = field(init=False, default_factory=tuple)

    def validate(self, previous: Optional["SensorReading"] = None) -> bool:
        """Validate the reading and optionally fall back to previous values.

        Args:
            previous: Optional previous valid reading for fallback.

        Returns:
            bool: True if the reading stays within physical ranges.
                False when out-of-range values were detected (even if they
                were overwritten using ``previous``).
        """
        errors = []
        if not TEMPERATURE_MIN <= self.temperature <= TEMPERATURE_MAX:
            errors.append("temperature")
            if previous is not None:
                self.temperature = previous.temperature

        if not HUMIDITY_MIN <= self.humidity <= HUMIDITY_MAX:
            errors.append("humidity")
            if previous is not None:
                self.humidity = previous.humidity

        self.is_valid = not errors
        self.invalid_fields = tuple(errors)
        return self.is_valid

    @classmethod
    def from_values(
        cls,
        temperature: float,
        humidity: float,
        pressure: Optional[float] = None,
        sensor_id: str = "sensor-001",
    ) -> "SensorReading":
        """Factory helper that timestamps the reading with current UTC time."""
        return cls(
            timestamp=datetime.now(tz=UTC),
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            sensor_id=sensor_id,
        )


@dataclass
class SensorFailureEvent:
    """Event emitted when a sensor exceeds the configured failure threshold."""

    sensor_id: str
    failure_count: int
    failure_threshold: int
    last_error: Optional[Exception]


@dataclass
class SensorAnomalyEvent:
    """Event emitted when a reading contains invalid/adjusted values."""

    sensor_id: str
    reading: SensorReading
    invalid_fields: tuple[str, ...]
