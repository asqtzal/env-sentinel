"""Alert evaluation and state management."""

from __future__ import annotations

import inspect
from collections import deque
from dataclasses import dataclass
from datetime import datetime

try:  # Python 3.11+
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]
from enum import Enum, auto
from typing import Awaitable, Callable, Deque, Optional, Sequence

from env_sentinel.config import AlertConfig
from env_sentinel.sensors.models import (
    SensorAnomalyEvent,
    SensorFailureEvent,
    SensorReading,
)
from env_sentinel.utils.logger import get_logger

from .models import Alert, AlertCategory, AlertLevel

AlertListener = Callable[[Alert], Optional[Awaitable[None]]]


class RangeState(Enum):
    """Represents where a metric currently sits relative to configured thresholds."""

    NORMAL = auto()
    WARNING_LOW = auto()
    WARNING_HIGH = auto()
    CRITICAL_LOW = auto()
    CRITICAL_HIGH = auto()


RANGE_SEVERITY = {
    RangeState.NORMAL: 0,
    RangeState.WARNING_LOW: 1,
    RangeState.WARNING_HIGH: 1,
    RangeState.CRITICAL_LOW: 2,
    RangeState.CRITICAL_HIGH: 2,
}


@dataclass
class MetricStatus:
    """Track the latest state for a monitored metric."""

    state: RangeState = RangeState.NORMAL
    last_updated: Optional[datetime] = None


class AlertManager:
    """Evaluate sensor readings and emit alerts while preventing duplicates."""

    def __init__(
        self,
        config: AlertConfig,
        *,
        history_limit: int = 100,
    ) -> None:
        self._config = config
        self._temperature_status = MetricStatus()
        self._humidity_status = MetricStatus()
        self._listeners: list[AlertListener] = []
        self._history: Deque[Alert] = deque(maxlen=history_limit)
        self._logger = get_logger(__name__)

    def register_listener(self, listener: AlertListener) -> None:
        """Register a callback invoked whenever an alert is emitted."""
        self._listeners.append(listener)

    def unregister_listener(self, listener: AlertListener) -> None:
        """Remove a previously registered listener if present."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            return

    def get_recent_alerts(self, limit: Optional[int] = None) -> list[Alert]:
        """Return the most recent alerts, newest last."""
        items = list(self._history)
        if limit is None or limit >= len(items):
            return items.copy()
        return items[-limit:]

    async def evaluate_reading(self, reading: SensorReading) -> list[Alert]:
        """Evaluate a sensor reading and emit alerts on state transitions."""
        alerts: list[Alert] = []

        temp_state = self._classify_temperature(reading.temperature)
        alerts.extend(self._handle_metric_transition("temperature", temp_state, reading))

        humidity_state = self._classify_humidity(reading.humidity)
        alerts.extend(self._handle_metric_transition("humidity", humidity_state, reading))

        if alerts:
            await self._dispatch_alerts(alerts)
        return alerts

    async def handle_sensor_failure(self, event: SensorFailureEvent) -> list[Alert]:
        """Convert a sensor failure event into an emergency alert."""
        alert = Alert(
            level=AlertLevel.EMERGENCY,
            category=AlertCategory.SENSOR,
            subject="sensor_failure",
            message=(
                f"🚨 センサ {event.sensor_id} が {event.failure_count} 回連続で失敗しました "
                f"(閾値 {event.failure_threshold})"
            ),
            details={
                "sensor_id": event.sensor_id,
                "failure_count": event.failure_count,
                "failure_threshold": event.failure_threshold,
                "last_error": repr(event.last_error) if event.last_error else None,
            },
        )
        await self._dispatch_alerts([alert])
        return [alert]

    async def handle_sensor_anomaly(self, event: SensorAnomalyEvent) -> list[Alert]:
        """Convert a sensor anomaly event into an emergency alert."""
        invalid_fields = ", ".join(event.invalid_fields)
        alert = Alert(
            level=AlertLevel.EMERGENCY,
            category=AlertCategory.SENSOR,
            subject="sensor_anomaly",
            message=(
                f"🚨 センサ {event.sensor_id} に異常値を検出しました "
                f"(項目: {invalid_fields or '不明'})"
            ),
            reading=event.reading,
            details={
                "sensor_id": event.sensor_id,
                "invalid_fields": event.invalid_fields,
            },
        )
        await self._dispatch_alerts([alert])
        return [alert]

    def _classify_temperature(self, value: float) -> RangeState:
        thresholds = self._config.temperature
        if value <= thresholds.critical_min:
            return RangeState.CRITICAL_LOW
        if value < thresholds.min:
            return RangeState.WARNING_LOW
        if value >= thresholds.critical_max:
            return RangeState.CRITICAL_HIGH
        if value > thresholds.max:
            return RangeState.WARNING_HIGH
        return RangeState.NORMAL

    def _classify_humidity(self, value: float) -> RangeState:
        thresholds = self._config.humidity
        if value <= thresholds.critical_min:
            return RangeState.CRITICAL_LOW
        if value < thresholds.min:
            return RangeState.WARNING_LOW
        if value >= thresholds.critical_max:
            return RangeState.CRITICAL_HIGH
        if value > thresholds.max:
            return RangeState.WARNING_HIGH
        return RangeState.NORMAL

    def _handle_metric_transition(
        self,
        metric: str,
        new_state: RangeState,
        reading: SensorReading,
    ) -> list[Alert]:
        status = self._temperature_status if metric == "temperature" else self._humidity_status
        previous_state = status.state
        if previous_state == new_state:
            return []

        status.state = new_state
        tz = reading.timestamp.tzinfo or UTC
        status.last_updated = datetime.now(tz=tz)
        if new_state == RangeState.NORMAL:
            return [self._build_normalization_alert(metric, reading)]

        if RANGE_SEVERITY[new_state] > RANGE_SEVERITY[previous_state]:
            return [self._build_state_alert(metric, new_state, reading)]

        if RANGE_SEVERITY[new_state] < RANGE_SEVERITY[previous_state]:
            # Severity decreased but still abnormal. Emit informational warning of current state.
            return [self._build_state_alert(metric, new_state, reading)]

        # Different abnormal category at same severity (e.g., low -> high). Emit alert as well.
        return [self._build_state_alert(metric, new_state, reading)]

    def _build_state_alert(
        self,
        metric: str,
        state: RangeState,
        reading: SensorReading,
    ) -> Alert:
        level = AlertLevel.WARNING if RANGE_SEVERITY[state] == 1 else AlertLevel.CRITICAL
        metric_label = "温度" if metric == "temperature" else "湿度"
        direction = "低下" if "LOW" in state.name else "上昇"
        subject = f"{metric}_{state.name.lower()}"
        unit = "℃" if metric == "temperature" else "%"
        message = (
            f"⚠️ {metric_label}が許容範囲から{direction}しました: "
            f"{getattr(reading, metric):.1f}{unit}"
        )
        if level == AlertLevel.CRITICAL:
            message = message.replace("⚠️", "🚨", 1)
        return Alert(
            level=level,
            category=AlertCategory.TEMPERATURE if metric == "temperature" else AlertCategory.HUMIDITY,
            subject=subject,
            message=message,
            reading=reading,
            details={
                "value": getattr(reading, metric),
                "state": state.name.lower(),
            },
        )

    def _build_normalization_alert(
        self,
        metric: str,
        reading: SensorReading,
    ) -> Alert:
        metric_label = "温度" if metric == "temperature" else "湿度"
        cfg = self._config.temperature if metric == "temperature" else self._config.humidity
        subject = f"{metric}_normalized"
        unit = "℃" if metric == "temperature" else "%"
        message = (
            f"✅ {metric_label}が正常範囲に戻りました "
            f"({cfg.min}〜{cfg.max}{unit}) "
            f"- 現在値 {getattr(reading, metric):.1f}{unit}"
        )
        return Alert(
            level=AlertLevel.INFO,
            category=AlertCategory.TEMPERATURE if metric == "temperature" else AlertCategory.HUMIDITY,
            subject=subject,
            message=message,
            reading=reading,
            details={
                "value": getattr(reading, metric),
                "range": (cfg.min, cfg.max),
            },
        )

    async def _dispatch_alerts(self, alerts: Sequence[Alert]) -> None:
        self._history.extend(alerts)
        for listener in list(self._listeners):
            for alert in alerts:
                try:
                    result = listener(alert)
                    if inspect.isawaitable(result):
                        await result  # type: ignore[func-returns-value]
                except Exception:  # pragma: no cover - defensive logging
                    self._logger.exception("Alert listener failed")


__all__ = ["AlertManager", "Alert", "AlertLevel", "AlertCategory"]
