"""Tests for the SensorFactory implementation."""

from __future__ import annotations

import asyncio

import pytest

from env_sentinel.config import SensorConfig
from env_sentinel.sensors import (
    BaseSensor,
    SensorFactory,
    SensorFactoryError,
    SensorReading,
)


class DummySensor(BaseSensor):
    """Simple sensor used to observe factory wiring."""

    def __init__(self, sensor_id: str, failure_threshold: int) -> None:
        super().__init__(
            sensor_id=sensor_id,
            failure_threshold=failure_threshold,
            max_retries=1,
            retry_delay_seconds=0.0,
        )
        self.closed = False

    async def _read_sensor(self) -> SensorReading:
        return SensorReading.from_values(
            temperature=23.0,
            humidity=50.0,
            sensor_id=self.sensor_id,
        )

    async def _close_impl(self) -> None:
        self.closed = True


def build_dummy_sensor(*, sensor_id: str, config: SensorConfig) -> BaseSensor:
    return DummySensor(sensor_id=sensor_id, failure_threshold=config.failure_threshold)


def run(coro):
    return asyncio.run(coro)


def test_factory_creates_registered_sensor() -> None:
    factory = SensorFactory()
    factory.register("BME280", build_dummy_sensor)
    config = SensorConfig(type="BME280", failure_threshold=4)

    sensor = factory.create(config=config, sensor_id="sensor-main")

    assert isinstance(sensor, DummySensor)
    assert sensor.sensor_id == "sensor-main"
    assert sensor.failure_threshold == 4
    # smoke test read/close to ensure returned sensor behaves
    assert run(sensor.read()).is_valid is True
    run(sensor.close())
    assert sensor.is_closed is True


def test_factory_raises_for_unknown_type() -> None:
    factory = SensorFactory()
    config = SensorConfig(type="UNKNOWN")

    with pytest.raises(SensorFactoryError):
        factory.create(config=config, sensor_id="sensor-x")


def test_register_requires_overwrite_flag() -> None:
    factory = SensorFactory({"BME280": build_dummy_sensor})

    with pytest.raises(SensorFactoryError):
        factory.register("BME280", build_dummy_sensor)

    # Allow overwriting when flagged
    factory.register("BME280", build_dummy_sensor, overwrite=True)


def test_factory_rejects_non_sensor_builder() -> None:
    def bad_builder(*, sensor_id: str, config: SensorConfig):  # type: ignore[return-type]
        return "not-a-sensor"

    factory = SensorFactory({"Mock": bad_builder})
    config = SensorConfig(type="Mock")

    with pytest.raises(SensorFactoryError):
        factory.create(config=config, sensor_id="sensor-bad")
