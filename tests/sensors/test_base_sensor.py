"""Tests for the BaseSensor abstraction."""

from __future__ import annotations

import asyncio

import pytest

from env_sentinel.sensors import (
    BaseSensor,
    SensorClosedError,
    SensorReadError,
    SensorReading,
)


class DummySensor(BaseSensor):
    """Test double that simulates deterministic failure/success patterns."""

    def __init__(
        self,
        *,
        failures_before_success: int = 0,
        failure_threshold: int = 3,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            sensor_id="dummy",
            failure_threshold=failure_threshold,
            max_retries=max_retries,
            retry_delay_seconds=0.0,
        )
        self.failures_before_success = failures_before_success
        self.read_calls = 0
        self.close_calls = 0

    async def _read_sensor(self) -> SensorReading:
        self.read_calls += 1
        if self.read_calls <= self.failures_before_success:
            raise RuntimeError("simulated read failure")

        return SensorReading.from_values(
            temperature=24.0,
            humidity=55.0,
            sensor_id=self.sensor_id,
        )

    async def _close_impl(self) -> None:
        self.close_calls += 1

    def _get_retry_delay(self, attempt: int) -> float:
        """Avoid slow sleeps in tests."""
        return 0.0


def run(coro):
    """Helper to execute async functions inside synchronous tests."""
    return asyncio.run(coro)


def test_read_returns_value_without_retry() -> None:
    sensor = DummySensor()

    reading = run(sensor.read())

    assert reading.sensor_id == "dummy"
    assert sensor.failure_count == 0
    assert sensor.last_valid_reading is reading


def test_read_retries_until_success() -> None:
    sensor = DummySensor(failures_before_success=2, max_retries=3)

    reading = run(sensor.read())

    assert reading.is_valid is True
    assert sensor.read_calls == 3
    assert sensor.failure_count == 0


def test_read_raises_after_exhausting_retries() -> None:
    sensor = DummySensor(failures_before_success=5, max_retries=2)

    with pytest.raises(SensorReadError) as excinfo:
        run(sensor.read())

    assert excinfo.value.attempts == 2
    assert isinstance(sensor.last_error, RuntimeError)
    assert sensor.failure_count == 2


def test_health_check_respects_failure_threshold() -> None:
    sensor = DummySensor(failures_before_success=10, max_retries=1, failure_threshold=2)

    for _ in range(2):
        with pytest.raises(SensorReadError):
            run(sensor.read())

    assert sensor.failure_count == 2
    assert run(sensor.health_check()) is False


def test_close_marks_sensor_closed_and_is_idempotent() -> None:
    sensor = DummySensor()

    run(sensor.close())
    run(sensor.close())

    assert sensor.is_closed is True
    assert sensor.close_calls == 1

    with pytest.raises(SensorClosedError):
        run(sensor.read())
