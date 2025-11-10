"""Helpers for generating scheduled report notifications."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from env_sentinel.monitoring import AlertLevel
from env_sentinel.notifications.models import (
    MentionPolicy,
    NotificationContext,
    NotificationKind,
    NotificationMessage,
)
from env_sentinel.sensors import SensorReading

LatestReadingFetcher = Callable[[], Awaitable[Optional[SensorReading]]]


class ReportGenerator:
    """Create NotificationMessage objects for periodic environment reports."""

    def __init__(self, fetch_latest_reading: LatestReadingFetcher) -> None:
        self._fetch_latest_reading = fetch_latest_reading

    async def build_report(self) -> NotificationMessage | None:
        """Generate a report message using the latest sensor reading."""
        reading = await self._fetch_latest_reading()
        if reading is None:
            return None
        metrics = {
            "温度": f"{reading.temperature:.1f}℃",
            "湿度": f"{reading.humidity:.1f}%",
            "測定時刻": reading.timestamp.isoformat(timespec="seconds"),
        }
        body = (
            f"最新の測定値: 温度 {metrics['温度']} / 湿度 {metrics['湿度']} "
            f"(取得: {metrics['測定時刻']})"
        )
        return NotificationMessage(
            kind=NotificationKind.REPORT,
            title="Env-Sentinel 定期レポート",
            body=body,
            level=AlertLevel.INFO,
            mention_policy=MentionPolicy.NONE,
            context=NotificationContext(metrics=metrics),
        )


__all__ = ["ReportGenerator", "LatestReadingFetcher"]
