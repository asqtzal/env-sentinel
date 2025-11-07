"""Tests for SensorReading data model."""

from __future__ import annotations

from datetime import UTC, datetime

from env_sentinel.sensors.models import SensorReading


def test_validate_accepts_valid_values() -> None:
    """Validate returns True when values are within physical ranges."""
    reading = SensorReading(
        timestamp=datetime.now(tz=UTC),
        temperature=25.0,
        humidity=50.0,
        pressure=1005.0,
        sensor_id="sensor-a",
    )

    assert reading.validate() is True
    assert reading.is_valid is True


def test_validate_corrects_with_previous_reading() -> None:
    """Out-of-range values fall back to previous measurements when available."""
    previous = SensorReading(
        timestamp=datetime.now(tz=UTC),
        temperature=24.0,
        humidity=55.0,
    )
    current = SensorReading(
        timestamp=datetime.now(tz=UTC),
        temperature=-100.0,
        humidity=150.0,
    )

    result = current.validate(previous)

    assert result is False
    assert current.temperature == previous.temperature
    assert current.humidity == previous.humidity
    assert current.is_valid is False


def test_from_values_sets_timestamp_and_id() -> None:
    """Factory helper populates timestamp and sensor_id."""
    reading = SensorReading.from_values(temperature=22.5, humidity=45.0, sensor_id="sensor-b")

    assert reading.sensor_id == "sensor-b"
    assert reading.timestamp.tzinfo is UTC
