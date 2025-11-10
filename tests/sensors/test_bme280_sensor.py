"""Tests for the BME280 sensor implementation."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

import env_sentinel.sensors.bme280 as bme280_module
from env_sentinel.config import SensorConfig
from env_sentinel.sensors import (
    BME280Driver,
    BME280Sample,
    BME280Sensor,
    DEFAULT_BME280_BUILDER,
    SensorFactory,
    SensorReadError,
    create_bme280_builder,
    create_raspberry_pi_driver_factory,
)


class FakeDriver(BME280Driver):
    def __init__(self, *, sample: BME280Sample, fail_times: int = 0) -> None:
        self.sample = sample
        self.fail_times = fail_times
        self.closed = False
        self._reads = 0

    async def read_sample(self) -> BME280Sample:
        self._reads += 1
        if self._reads <= self.fail_times:
            raise RuntimeError("temporary failure")
        return self.sample

    async def close(self) -> None:
        self.closed = True


def run(coro):
    return asyncio.run(coro)


def test_bme280_sensor_returns_sensor_reading() -> None:
    sample = BME280Sample(temperature=21.5, humidity=42.0, pressure=1008.1)
    driver = FakeDriver(sample=sample)
    config = SensorConfig()
    sensor = BME280Sensor(sensor_id="bme-1", driver=driver, config=config)

    reading = run(sensor.read())

    assert reading.temperature == pytest.approx(21.5)
    assert reading.humidity == pytest.approx(42.0)
    assert reading.pressure == pytest.approx(1008.1)
    run(sensor.close())
    assert driver.closed is True


def test_bme280_sensor_retries_driver_failures() -> None:
    sample = BME280Sample(temperature=19.0, humidity=50.0, pressure=None)
    driver = FakeDriver(sample=sample, fail_times=2)
    config = SensorConfig(failure_threshold=3)
    sensor = BME280Sensor(sensor_id="bme-2", driver=driver, config=config)

    reading = run(sensor.read())

    assert reading.is_valid is True


def test_bme280_sensor_raises_after_retries_exhausted() -> None:
    sample = BME280Sample(temperature=19.0, humidity=50.0, pressure=None)
    driver = FakeDriver(sample=sample, fail_times=10)
    sensor = BME280Sensor(sensor_id="bme-fail", driver=driver, config=SensorConfig(failure_threshold=2))

    with pytest.raises(SensorReadError):
        run(sensor.read())


def test_bme280_builder_uses_driver_factory() -> None:
    created_configs: list[SensorConfig] = []

    def driver_factory(*, config: SensorConfig) -> BME280Driver:
        created_configs.append(config)
        return FakeDriver(sample=BME280Sample(temperature=20.0, humidity=40.0, pressure=1010.0))

    builder = create_bme280_builder(driver_factory=driver_factory)
    sensor = builder(sensor_id="sensor-x", config=SensorConfig(type="BME280"))

    assert isinstance(sensor, BME280Sensor)
    assert created_configs and created_configs[0].type == "BME280"


def test_default_builder_can_be_registered_in_factory() -> None:
    factory = SensorFactory({"BME280": DEFAULT_BME280_BUILDER})
    sensor = factory.create(config=SensorConfig(type="BME280"), sensor_id="sensor-123")

    assert isinstance(sensor, BME280Sensor)


def test_raspberry_pi_driver_factory_uses_dependencies(monkeypatch) -> None:
    board = SimpleNamespace(SCL="scl", SDA="sda")

    class FakeI2C:
        def __init__(self) -> None:
            self.closed = False

        def deinit(self) -> None:
            self.closed = True

    class FakeBusio:
        def I2C(self, scl: Any, sda: Any) -> FakeI2C:
            assert scl == "scl"
            assert sda == "sda"
            return FakeI2C()

    class FakeSensorHw:
        def __init__(self, i2c: FakeI2C, address: int) -> None:
            self._i2c = i2c
            self.temperature = 22.2
            self.relative_humidity = 55.5
            self.pressure = 1000.5
            self.address = address

        def deinit(self) -> None:
            self._i2c.deinit()

    def fake_loader():
        return board, FakeBusio(), FakeSensorHw

    monkeypatch.setattr(bme280_module, "_load_pi_dependencies", fake_loader)

    factory = create_raspberry_pi_driver_factory()
    driver = factory(config=SensorConfig(i2c_address="0x77"))

    sample = run(driver.read_sample())

    assert sample.temperature == pytest.approx(22.2)
    assert sample.humidity == pytest.approx(55.5)
    assert sample.pressure == pytest.approx(1000.5)
    run(driver.close())


def test_raspberry_pi_driver_factory_requires_dependencies(monkeypatch) -> None:
    def fake_loader():
        raise RuntimeError("missing hardware libs")

    monkeypatch.setattr(bme280_module, "_load_pi_dependencies", fake_loader)

    factory = create_raspberry_pi_driver_factory()

    with pytest.raises(RuntimeError, match="missing hardware libs"):
        factory(config=SensorConfig())


def test_raspberry_pi_driver_factory_i2c_failure() -> None:
    board = SimpleNamespace(SCL="scl", SDA="sda")

    class BrokenBusio:
        def I2C(self, scl: Any, sda: Any) -> None:
            raise OSError("I2C bus busy")

    def dependency_loader():
        return board, BrokenBusio(), object()

    factory = create_raspberry_pi_driver_factory(dependency_loader=dependency_loader)

    with pytest.raises(OSError, match="I2C bus busy"):
        factory(config=SensorConfig())


def test_raspberry_pi_driver_propagates_sensor_errors() -> None:
    class FlakySensor:
        def __init__(self) -> None:
            self.relative_humidity = 10.0
            self.pressure = 1000.0

        @property
        def temperature(self) -> float:
            raise RuntimeError("sensor read failed")

        def deinit(self) -> None:
            pass

    class DummyI2C:
        def deinit(self) -> None:
            pass

    driver = bme280_module.RaspberryPiBME280Driver(sensor=FlakySensor(), i2c=DummyI2C())

    with pytest.raises(RuntimeError, match="sensor read failed"):
        run(driver.read_sample())
