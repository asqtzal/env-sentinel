"""Abstract base class and shared helpers for Env-Sentinel sensors."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import inspect
from typing import Awaitable, Callable, Optional, Union

from env_sentinel.sensors.models import (
    SensorAnomalyEvent,
    SensorFailureEvent,
    SensorReading,
)
from env_sentinel.utils.logger import get_logger


FailureCallback = Callable[[SensorFailureEvent], Union[Optional[Awaitable[None]], None]]
AnomalyCallback = Callable[[SensorAnomalyEvent], Union[Optional[Awaitable[None]], None]]


class SensorError(RuntimeError):
    """Base exception for sensor related failures."""


class SensorClosedError(SensorError):
    """Raised when attempting to use a sensor that has already been closed."""

    def __init__(self, sensor_id: str) -> None:
        super().__init__(f"Sensor '{sensor_id}' is closed")
        self.sensor_id = sensor_id


class SensorReadError(SensorError):
    """Raised when a sensor fails to produce a reading after retries."""

    def __init__(
        self,
        sensor_id: str,
        attempts: int,
        last_error: Optional[Exception] = None,
    ) -> None:
        message = f"Failed to read from sensor '{sensor_id}' after {attempts} attempt(s)"
        if last_error:
            message = f"{message}: {last_error}"
        super().__init__(message)
        self.sensor_id = sensor_id
        self.attempts = attempts
        self.last_error = last_error


class BaseSensor(ABC):
    """Common functionality for concrete sensor implementations.

    Provides retry handling, health monitoring and validation helpers while
    delegating hardware-specific interactions to subclasses.
    """

    def __init__(
        self,
        sensor_id: str,
        *,
        failure_threshold: int = 3,
        max_retries: int = 3,
        retry_delay_seconds: float = 0.0,
        failure_callback: FailureCallback | None = None,
        anomaly_callback: AnomalyCallback | None = None,
    ) -> None:
        if not sensor_id:
            raise ValueError("sensor_id must be a non-empty string")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")

        self.sensor_id = sensor_id
        self.failure_threshold = failure_threshold
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self._failure_callback = failure_callback
        self._anomaly_callback = anomaly_callback

        self._consecutive_failures = 0
        self._last_valid_reading: Optional[SensorReading] = None
        self._last_error: Optional[Exception] = None
        self._closed = False
        self._failure_reported = False
        self._logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    async def __aenter__(self) -> "BaseSensor":
        self._ensure_open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def last_valid_reading(self) -> Optional[SensorReading]:
        """Return the last valid reading emitted by the sensor."""
        return self._last_valid_reading

    @property
    def failure_count(self) -> int:
        """Return the number of consecutive read failures."""
        return self._consecutive_failures

    @property
    def last_error(self) -> Optional[Exception]:
        """Return the most recent exception raised during a read attempt."""
        return self._last_error

    @property
    def is_closed(self) -> bool:
        """Indicate whether the sensor has been closed."""
        return self._closed

    async def read(self) -> SensorReading:
        """Read a measurement from the sensor with retry handling."""
        self._ensure_open()
        last_error: Optional[Exception] = None
        attempts = 0

        for attempt in range(1, self.max_retries + 1):
            attempts = attempt
            try:
                reading = await self._read_sensor()
            except Exception as exc:  # pragma: no cover - managed in helper
                last_error = exc
                should_retry = await self._handle_attempt_failure(attempt, exc)
                if not should_retry:
                    break
                continue

            await self._handle_attempt_success(reading)
            return reading

        raise SensorReadError(sensor_id=self.sensor_id, attempts=attempts, last_error=last_error)

    async def close(self) -> None:
        """Release any resources associated with the sensor."""
        if self._closed:
            return
        await self._close_impl()
        self._closed = True

    async def health_check(self) -> bool:
        """Return True when the sensor is considered healthy."""
        if self._closed:
            return False
        if self._consecutive_failures >= self.failure_threshold:
            return False
        return await self._perform_health_check()

    async def on_read_success(self, reading: SensorReading) -> None:
        """Hook executed after a successful read. Subclasses may override."""

    async def on_read_failure(self, attempt: int, error: Exception) -> None:
        """Hook executed after a failed read attempt. Subclasses may override."""

    async def _perform_health_check(self) -> bool:
        """Hook for subclasses to provide device-specific health diagnostics."""
        return True

    def _should_retry(self, attempt: int, error: Exception) -> bool:
        """Decide whether the next retry attempt should be executed."""
        return attempt < self.max_retries

    def _get_retry_delay(self, attempt: int) -> float:
        """Return the delay (in seconds) to wait before the next retry."""
        return self.retry_delay_seconds

    def _ensure_open(self) -> None:
        """Ensure the sensor has not been closed before continuing."""
        if self._closed:
            raise SensorClosedError(self.sensor_id)

    async def _handle_attempt_success(self, reading: SensorReading) -> None:
        """Record bookkeeping for successful read attempts."""
        # Align emitted reading metadata with the sensor instance
        reading.sensor_id = self.sensor_id

        previous = self._last_valid_reading
        reading.validate(previous=previous)
        if reading.is_valid:
            self._last_valid_reading = reading
        await self._emit_anomaly_event(reading)

        self._consecutive_failures = 0
        self._last_error = None
        if self._failure_reported:
            self._failure_reported = False
        await self.on_read_success(reading)

    async def _handle_attempt_failure(self, attempt: int, error: Exception) -> bool:
        """Record failure bookkeeping and optionally schedule another retry."""
        self._consecutive_failures += 1
        self._last_error = error
        self._logger.warning(
            "Sensor %s read attempt %s failed: %s",
            self.sensor_id,
            attempt,
            error,
        )
        await self.on_read_failure(attempt, error)
        if (
            not self._failure_reported
            and self._consecutive_failures >= self.failure_threshold
        ):
            self._failure_reported = True
            await self._emit_failure_event()

        if not self._should_retry(attempt, error):
            return False

        delay = self._get_retry_delay(attempt)
        if delay > 0:
            await asyncio.sleep(delay)
        return True

    @abstractmethod
    async def _read_sensor(self) -> SensorReading:
        """Perform a hardware-specific read operation."""

    @abstractmethod
    async def _close_impl(self) -> None:
        """Release hardware-specific resources."""

    async def _emit_failure_event(self) -> None:
        """Notify subscribers when the sensor is considered failed."""
        if not self._failure_callback:
            return
        event = SensorFailureEvent(
            sensor_id=self.sensor_id,
            failure_count=self._consecutive_failures,
            failure_threshold=self.failure_threshold,
            last_error=self._last_error,
        )
        await self._invoke_callback(self._failure_callback, event)

    async def _emit_anomaly_event(self, reading: SensorReading) -> None:
        """Notify subscribers when a reading contains invalid data."""
        if not self._anomaly_callback or reading.is_valid:
            return
        event = SensorAnomalyEvent(
            sensor_id=self.sensor_id,
            reading=reading,
            invalid_fields=reading.invalid_fields,
        )
        await self._invoke_callback(self._anomaly_callback, event)

    async def _invoke_callback(
        self,
        callback: Callable[[object], Optional[Awaitable[None]] | None],
        event: object,
    ) -> None:
        """Invoke callback that may be synchronous or asynchronous."""
        result = callback(event)
        if inspect.isawaitable(result):
            await result  # type: ignore[func-returns-value]
