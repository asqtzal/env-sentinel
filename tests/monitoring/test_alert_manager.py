"""Tests for the AlertManager."""

from __future__ import annotations

import asyncio
from typing import List

import pytest

from env_sentinel.config import AppConfig
from env_sentinel.monitoring import AlertCategory, AlertLevel, AlertManager
from env_sentinel.sensors.models import SensorAnomalyEvent, SensorFailureEvent, SensorReading


@pytest.fixture()
def alert_manager() -> AlertManager:
    config = AppConfig.defaults().alerts
    return AlertManager(config, history_limit=5)


def test_temperature_warning_emitted_once(alert_manager: AlertManager) -> None:
    """Entering warning range emits one alert; staying there does not."""
    reading = SensorReading.from_values(temperature=27.0, humidity=50.0)
    alerts = asyncio.run(alert_manager.evaluate_reading(reading))
    assert len(alerts) == 1
    assert alerts[0].level == AlertLevel.WARNING
    assert alerts[0].category == AlertCategory.TEMPERATURE

    reading_repeat = SensorReading.from_values(temperature=27.5, humidity=55.0)
    alerts = asyncio.run(alert_manager.evaluate_reading(reading_repeat))
    assert alerts == []


def test_temperature_normalization(alert_manager: AlertManager) -> None:
    """Returning to normal range emits a normalization alert."""
    asyncio.run(
        alert_manager.evaluate_reading(SensorReading.from_values(temperature=28.0, humidity=50.0))
    )
    alerts = asyncio.run(
        alert_manager.evaluate_reading(
            SensorReading.from_values(temperature=24.0, humidity=50.0)
        )
    )
    assert len(alerts) == 1
    normalization = alerts[0]
    assert normalization.level == AlertLevel.INFO
    assert normalization.subject == "temperature_normalized"


def test_humidity_critical_threshold(alert_manager: AlertManager) -> None:
    """Crossing humidity critical thresholds emits CRITICAL alerts."""
    reading = SensorReading.from_values(temperature=22.0, humidity=0.5)
    alerts = asyncio.run(alert_manager.evaluate_reading(reading))
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.level == AlertLevel.CRITICAL
    assert alert.category == AlertCategory.HUMIDITY


def test_sensor_failure_event(alert_manager: AlertManager) -> None:
    """Sensor failure events become EMERGENCY alerts."""
    event = SensorFailureEvent(
        sensor_id="sensor-1",
        failure_count=3,
        failure_threshold=3,
        last_error=RuntimeError("boom"),
    )
    alerts = asyncio.run(alert_manager.handle_sensor_failure(event))
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.level == AlertLevel.EMERGENCY
    assert alert.category == AlertCategory.SENSOR
    assert "sensor-1" in alert.message


def test_sensor_anomaly_event(alert_manager: AlertManager) -> None:
    """Sensor anomaly events propagate as EMERGENCY alerts."""
    reading = SensorReading.from_values(temperature=200.0, humidity=10.0)
    event = SensorAnomalyEvent(
        sensor_id="sensor-1",
        reading=reading,
        invalid_fields=("temperature",),
    )
    alerts = asyncio.run(alert_manager.handle_sensor_anomaly(event))
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.level == AlertLevel.EMERGENCY
    assert alert.reading is reading


def test_listener_invoked(alert_manager: AlertManager) -> None:
    """Registered listeners receive every alert."""
    received: List[str] = []

    def listener(alert):
        received.append(alert.subject)

    alert_manager.register_listener(listener)
    asyncio.run(
        alert_manager.evaluate_reading(SensorReading.from_values(temperature=27.0, humidity=50.0))
    )
    assert received == ["temperature_warning_high"]


def test_history_is_capped(alert_manager: AlertManager) -> None:
    """History deque keeps only the most recent alerts."""
    for temp in (27.0, 24.0, 9.0, 24.0, 70.0, 50.0):
        asyncio.run(
            alert_manager.evaluate_reading(
                SensorReading.from_values(temperature=temp, humidity=90.0)
            )
        )
    assert len(alert_manager.get_recent_alerts()) <= 5
