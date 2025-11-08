"""BME280 sensor implementation with driver abstraction."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable, Protocol, Tuple

from env_sentinel.config import SensorConfig

from .base import BaseSensor
from .factory import SensorBuilder
from .models import SensorReading


@dataclass
class BME280Sample:
    """Structured reading returned by a BME280 driver."""

    temperature: float
    humidity: float
    pressure: float | None = None


class BME280Driver(Protocol):
    """Protocol describing the operations required from a BME280 driver."""

    async def read_sample(self) -> BME280Sample:
        """Return the latest sample from the sensor."""

    async def close(self) -> None:
        """Release any driver resources."""


class BME280DriverFactory(Protocol):
    """Creates a driver instance for a given configuration."""

    def __call__(self, *, config: SensorConfig) -> BME280Driver:
        """Return a configured driver."""


class SimulatedBME280Driver:
    """Simple driver used for development and unit tests."""

    def __init__(self) -> None:
        self._closed = False

    async def read_sample(self) -> BME280Sample:
        if self._closed:
            raise RuntimeError("BME280 driver is closed")
        # Return a deterministic but realistic-looking sample
        return BME280Sample(temperature=24.5, humidity=48.0, pressure=1012.5)

    async def close(self) -> None:
        self._closed = True


class RaspberryPiBME280Driver(BME280Driver):
    """Hardware-backed BME280 driver using Adafruit CircuitPython libraries."""

    def __init__(self, *, sensor: Any, i2c: Any) -> None:
        self._sensor = sensor
        self._i2c = i2c

    async def read_sample(self) -> BME280Sample:
        def _read() -> BME280Sample:
            temperature = float(self._sensor.temperature)
            humidity = float(self._sensor.relative_humidity)
            pressure_raw = getattr(self._sensor, "pressure", None)
            pressure = float(pressure_raw) if pressure_raw is not None else None
            return BME280Sample(
                temperature=temperature,
                humidity=humidity,
                pressure=pressure,
            )

        return await asyncio.to_thread(_read)

    async def close(self) -> None:
        sensor_close = getattr(self._sensor, "deinit", None)
        if callable(sensor_close):
            sensor_close()
        bus_close = getattr(self._i2c, "deinit", None)
        if callable(bus_close):
            bus_close()


class BME280Sensor(BaseSensor):
    """Concrete BaseSensor implementation backed by a BME280 driver."""

    def __init__(
        self,
        *,
        sensor_id: str,
        driver: BME280Driver,
        config: SensorConfig,
    ) -> None:
        super().__init__(
            sensor_id=sensor_id,
            failure_threshold=config.failure_threshold,
            max_retries=3,
            retry_delay_seconds=0.1,
        )
        self._driver = driver

    async def _read_sensor(self) -> SensorReading:
        sample = await self._driver.read_sample()
        return SensorReading.from_values(
            temperature=sample.temperature,
            humidity=sample.humidity,
            pressure=sample.pressure,
            sensor_id=self.sensor_id,
        )

    async def _close_impl(self) -> None:
        await self._driver.close()


def _load_pi_dependencies() -> Tuple[ModuleType, Any, Any]:
    """Dynamically import modules required for Raspberry Pi operation."""
    required = ("board", "busio", "adafruit_bme280")
    modules: dict[str, ModuleType] = {}
    for name in required:
        try:
            modules[name] = importlib.import_module(name)
        except ImportError as exc:  # pragma: no cover - exercised on hardware
            raise RuntimeError(
                "RaspberryPiBME280Driver requires 'adafruit-circuitpython-bme280' "
                "and 'adafruit-blinka' to be installed on the device.",
            ) from exc

    sensor_cls = getattr(modules["adafruit_bme280"], "Adafruit_BME280_I2C", None)
    if sensor_cls is None:  # pragma: no cover - sanity guard
        raise RuntimeError("Adafruit_BME280_I2C class not available in adafruit_bme280 module")
    return modules["board"], modules["busio"], sensor_cls


def _parse_i2c_address(address: str) -> int:
    try:
        return int(address, 16)
    except ValueError as exc:  # pragma: no cover - config validation should prevent this
        raise ValueError(f"Invalid I2C address '{address}'") from exc


def create_raspberry_pi_driver_factory(
    *,
    dependency_loader: Callable[[], Tuple[ModuleType, Any, Any]] | None = None,
) -> BME280DriverFactory:
    """Create a driver factory that instantiates the hardware-backed driver."""

    loader = dependency_loader or _load_pi_dependencies

    def factory(*, config: SensorConfig) -> BME280Driver:
        board_module, busio_module, sensor_cls = loader()
        i2c = busio_module.I2C(board_module.SCL, board_module.SDA)
        address = _parse_i2c_address(config.i2c_address)
        sensor = sensor_cls(i2c, address=address)
        return RaspberryPiBME280Driver(sensor=sensor, i2c=i2c)

    return factory


def create_bme280_builder(
    driver_factory: BME280DriverFactory | None = None,
) -> SensorBuilder:
    """Return a SensorFactory-compatible builder for BME280 sensors."""

    driver_provider = driver_factory or (lambda *, config: SimulatedBME280Driver())

    def builder(*, sensor_id: str, config: SensorConfig) -> BME280Sensor:
        driver = driver_provider(config=config)
        return BME280Sensor(sensor_id=sensor_id, driver=driver, config=config)

    return builder


DEFAULT_BME280_BUILDER = create_bme280_builder()
RASPBERRY_PI_BME280_BUILDER = create_bme280_builder(
    driver_factory=create_raspberry_pi_driver_factory(),
)
