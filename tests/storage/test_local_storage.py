"""Tests for the LocalStorage SQLite implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from env_sentinel.config import StorageConfig
from env_sentinel.sensors import SensorReading
from env_sentinel.storage import LocalStorage

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]


def run(coro):
    return asyncio.run(coro)


def make_storage(tmp_path: Path, retention_days: int = 2) -> LocalStorage:
    config = StorageConfig(
        db_path=str(tmp_path / "sensor.db"),
        local_retention_days=retention_days,
    )
    return LocalStorage.from_config(config)


def test_store_and_fetch_readings(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    reading = SensorReading.from_values(temperature=22.5, humidity=50.0, sensor_id="sensor-a")

    result = run(storage.store_reading(reading))
    assert result is True

    readings = run(storage.get_recent_data(hours=1))
    assert len(readings) == 1
    assert readings[0].sensor_id == "sensor-a"
    assert readings[0].temperature == pytest.approx(22.5)


def test_retention_policy_removes_old_rows(tmp_path: Path) -> None:
    storage = make_storage(tmp_path, retention_days=1)
    old_reading = SensorReading(
        timestamp=datetime.now(tz=UTC) - timedelta(days=3),
        temperature=20.0,
        humidity=40.0,
    )
    recent_reading = SensorReading.from_values(temperature=25.0, humidity=55.0, sensor_id="sensor-b")

    run(storage.store_reading(old_reading))
    run(storage.store_reading(recent_reading))

    run(storage.purge_expired_data())

    readings = run(storage.get_recent_data(hours=24))
    assert len(readings) == 1
    assert readings[0].sensor_id == "sensor-b"


def test_invalid_fields_round_trip(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    previous = SensorReading.from_values(temperature=25.0, humidity=55.0)
    invalid = SensorReading(
        timestamp=datetime.now(tz=UTC),
        temperature=150.0,
        humidity=200.0,
    )
    invalid.validate(previous=previous)

    run(storage.store_reading(invalid))
    readings = run(storage.get_recent_data(hours=1))

    assert readings[0].is_valid is False
    assert readings[0].invalid_fields == ("temperature", "humidity")


def test_initialize_is_idempotent(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)

    run(storage.initialize())
    run(storage.initialize())

    assert (tmp_path / "sensor.db").exists()


def test_get_recent_data_limit(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    for idx in range(5):
        run(
            storage.store_reading(
                SensorReading.from_values(
                    temperature=20.0 + idx,
                    humidity=40.0,
                    sensor_id=f"sensor-{idx}",
                )
            )
        )

    readings = run(storage.get_recent_data(hours=1, limit=2))

    assert len(readings) == 2
    assert readings[0].sensor_id != readings[1].sensor_id


def test_health_check_reports_schema_version(tmp_path: Path) -> None:
    storage = make_storage(tmp_path)
    status = run(storage.health_check())

    assert status["status"] == "ok"
    assert status["schema_version"] >= 1
