"""Sensor modules for Env-Sentinel."""

from __future__ import annotations

from .base import BaseSensor, SensorClosedError, SensorError, SensorReadError
from .bme280 import (
    BME280Sensor,
    BME280Driver,
    BME280DriverFactory,
    BME280Sample,
    DEFAULT_BME280_BUILDER,
    RASPBERRY_PI_BME280_BUILDER,
    SimulatedBME280Driver,
    create_bme280_builder,
    create_raspberry_pi_driver_factory,
    _load_pi_dependencies as _load_bme280_dependencies,
)
from .factory import SensorBuilder, SensorFactory, SensorFactoryError
from .models import SensorAnomalyEvent, SensorFailureEvent, SensorReading

__all__ = [
    "BaseSensor",
    "BME280Driver",
    "BME280DriverFactory",
    "BME280Sample",
    "BME280Sensor",
    "SensorAnomalyEvent",
    "SensorBuilder",
    "SensorClosedError",
    "SensorError",
    "SensorFactory",
    "SensorFactoryError",
    "SensorFailureEvent",
    "SensorReadError",
    "SensorReading",
    "DEFAULT_BME280_BUILDER",
    "RASPBERRY_PI_BME280_BUILDER",
    "SimulatedBME280Driver",
    "create_bme280_builder",
    "create_default_sensor_factory",
    "create_raspberry_pi_driver_factory",
]


def create_default_sensor_factory(*, prefer_hardware: bool | None = None) -> SensorFactory:
    """Return a SensorFactory preloaded with built-in sensor builders.

    Args:
        prefer_hardware: Force hardware driver usage (`True`), force simulator (`False`),
            or auto-detect modules when ``None``.
    """

    if prefer_hardware is False:
        builder = DEFAULT_BME280_BUILDER
    elif prefer_hardware is True:
        builder = RASPBERRY_PI_BME280_BUILDER
    else:
        try:
            # Attempt to load hardware dependencies to decide the default behavior.
            _load_bme280_dependencies()
        except RuntimeError:
            builder = DEFAULT_BME280_BUILDER
        else:
            builder = RASPBERRY_PI_BME280_BUILDER

    return SensorFactory({"BME280": builder})
