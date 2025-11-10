"""Tests for MonitoringLoop."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from env_sentinel.config import AppConfig
from env_sentinel.core.loop import MonitoringLoop
from env_sentinel.monitoring import AlertManager
from env_sentinel.sensors import BaseSensor, SensorFactory
from env_sentinel.sensors.models import SensorReading
from env_sentinel.storage import LocalStorage


class StubSensor(BaseSensor):
    def __init__(
        self,
        readings: list[SensorReading],
        label: str,
        closed_labels: list[str],
    ) -> None:
        super().__init__(sensor_id=f"stub-{label}", failure_threshold=3)
        self._readings = readings
        self._index = 0
        self._label = label
        self._closed_labels = closed_labels

    async def _read_sensor(self) -> SensorReading:
        reading = self._readings[self._index]
        if self._index < len(self._readings) - 1:
            self._index += 1
        return reading

    async def _close_impl(self) -> None:
        self._closed_labels.append(self._label)
        return


def _make_config(tmp_path, sensor_type: str = "stub", interval: float = 0.05) -> AppConfig:
    base = AppConfig.defaults()
    sensor_cfg = base.sensor.copy(update={"type": sensor_type, "read_interval_seconds": interval})
    storage_cfg = base.storage.copy(update={"db_path": tmp_path / "loop.db"})
    return base.copy(update={"sensor": sensor_cfg, "storage": storage_cfg})


def test_monitoring_loop_stores_and_alerts(tmp_path) -> None:
    async def _run() -> None:
        config = _make_config(tmp_path)
        alert_manager = AlertManager(config.alerts)
        storage = LocalStorage.from_config(config.storage)
        await storage.initialize()

        readings_map = {
            "stub": [SensorReading.from_values(temperature=27.0, humidity=50.0)],
            "stub2": [SensorReading.from_values(temperature=22.0, humidity=60.0)],
        }
        created_labels: list[str] = []
        closed_labels: list[str] = []

        def builder_for(label: str):
            def builder(*, sensor_id, config):
                created_labels.append(label)
                return StubSensor(readings_map[label], label, closed_labels)

            return builder

        factory = SensorFactory({"stub": builder_for("stub"), "stub2": builder_for("stub2")})

        state = SimpleNamespace(config=config, alert_manager=alert_manager, storage=storage)
        loop = MonitoringLoop(
            config_provider=lambda: state.config,
            alert_manager=state.alert_manager,
            storage=state.storage,
            sensor_factory=factory,
        )
        await loop.start()
        await asyncio.sleep(0.2)
        assert created_labels == ["stub"]

        state.config = state.config.copy(
            update={"sensor": state.config.sensor.copy(update={"type": "stub2"})}
        )
        await asyncio.sleep(0.2)
        await loop.stop()

        assert alert_manager.get_recent_alerts()
        recent = await storage.get_recent_data(hours=1)
        assert len(recent) >= 1
        assert "stub2" in created_labels
        assert "stub" in closed_labels

    asyncio.run(_run())
