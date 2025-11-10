"""Sensor factory utilities for instantiating concrete sensor implementations."""

from __future__ import annotations

from typing import Mapping, MutableMapping, Protocol

from env_sentinel.config import SensorConfig

from .base import BaseSensor


class SensorFactoryError(RuntimeError):
    """Raised when the factory cannot fulfill a sensor creation request."""


class SensorBuilder(Protocol):
    """Callable interface every sensor builder must implement."""

    def __call__(self, *, sensor_id: str, config: SensorConfig) -> BaseSensor:
        """Return a configured sensor instance."""


class SensorFactory:
    """Factory responsible for constructing sensors from configuration."""

    def __init__(self, builders: Mapping[str, SensorBuilder] | None = None) -> None:
        self._builders: MutableMapping[str, SensorBuilder] = {}
        if builders:
            for sensor_type, builder in builders.items():
                self.register(sensor_type, builder)

    def register(
        self,
        sensor_type: str,
        builder: SensorBuilder,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register a sensor builder for the provided type."""
        key = self._normalize(sensor_type)
        if not overwrite and key in self._builders:
            raise SensorFactoryError(f"Sensor type '{sensor_type}' is already registered")
        self._builders[key] = builder

    def unregister(self, sensor_type: str) -> None:
        """Remove a previously registered sensor type if present."""
        key = self._normalize(sensor_type)
        self._builders.pop(key, None)

    def create(self, *, config: SensorConfig, sensor_id: str) -> BaseSensor:
        """Create a sensor instance based on the provided configuration."""
        key = self._normalize(config.type)
        builder = self._builders.get(key)
        if builder is None:
            raise SensorFactoryError(f"Unsupported sensor type '{config.type}'")

        sensor = builder(sensor_id=sensor_id, config=config)
        if not isinstance(sensor, BaseSensor):
            raise SensorFactoryError(
                f"Builder for '{config.type}' must return a BaseSensor instance",
            )
        return sensor

    @staticmethod
    def _normalize(sensor_type: str) -> str:
        normalized = sensor_type.strip().lower()
        if not normalized:
            raise ValueError("sensor_type must be a non-empty string")
        return normalized
