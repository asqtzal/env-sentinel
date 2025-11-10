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
        failure_callback=None,
        anomaly_callback=None,
    ) -> None:
        super().__init__(
            sensor_id="dummy",
            failure_threshold=failure_threshold,
            max_retries=max_retries,
            retry_delay_seconds=0.0,
            failure_callback=failure_callback,
            anomaly_callback=anomaly_callback,
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


class CyclicFailureSensor(BaseSensor):
    """Fails twice before succeeding, every read cycle."""

    def __init__(self, *, failure_callback) -> None:
        super().__init__(
            sensor_id="cyclic",
            failure_threshold=2,
            max_retries=3,
            retry_delay_seconds=0.0,
            failure_callback=failure_callback,
        )
        self._attempt_in_cycle = 0

    async def _read_sensor(self) -> SensorReading:
        self._attempt_in_cycle += 1
        if self._attempt_in_cycle <= 2:
            raise RuntimeError("cycle failure")
        self._attempt_in_cycle = 0
        return SensorReading.from_values(
            temperature=21.0,
            humidity=45.0,
            sensor_id=self.sensor_id,
        )

    async def _close_impl(self) -> None:
        return None


class AnomalySensor(BaseSensor):
    """Always produces out-of-range readings."""

    def __init__(self, *, anomaly_callback) -> None:
        super().__init__(
            sensor_id="anomaly",
            failure_threshold=3,
            max_retries=1,
            retry_delay_seconds=0.0,
            anomaly_callback=anomaly_callback,
        )

    async def _read_sensor(self) -> SensorReading:
        return SensorReading.from_values(
            temperature=120.0,
            humidity=55.0,
            sensor_id=self.sensor_id,
        )

    async def _close_impl(self) -> None:
        return None


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


def test_failure_callback_triggers_once_per_sequence() -> None:
    events = []

    def on_failure(event):
        events.append((event.failure_count, event.failure_threshold))

    sensor = DummySensor(
        failures_before_success=5,
        max_retries=2,
        failure_threshold=2,
        failure_callback=on_failure,
    )

    with pytest.raises(SensorReadError):
        run(sensor.read())

    assert len(events) == 1
    assert events[0] == (2, 2)


def test_failure_callback_resets_after_success() -> None:
    events = []

    def on_failure(event):
        events.append(event.failure_count)

    sensor = CyclicFailureSensor(failure_callback=on_failure)

    run(sensor.read())
    run(sensor.read())

    assert events == [2, 2]


def test_anomaly_callback_receives_invalid_fields() -> None:
    events = []

    def on_anomaly(event):
        events.append(event.invalid_fields)

    sensor = AnomalySensor(anomaly_callback=on_anomaly)

    run(sensor.read())

    assert events == [("temperature",)]
