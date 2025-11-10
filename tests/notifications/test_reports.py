"""Tests for ReportGenerator."""

from __future__ import annotations

import asyncio

from env_sentinel.notifications.models import NotificationKind
from env_sentinel.notifications.reports import ReportGenerator
from env_sentinel.sensors import SensorReading


async def _build_reading() -> SensorReading:
    return SensorReading.from_values(temperature=24.5, humidity=51.2)


def test_report_generator_returns_message() -> None:
    async def _run() -> None:
        generator = ReportGenerator(fetch_latest_reading=_build_reading)
        message = await generator.build_report()
        assert message is not None
        assert message.kind == NotificationKind.REPORT
        assert "温度" in message.context.metrics

    asyncio.run(_run())


def test_report_generator_returns_none_when_no_reading() -> None:
    async def _run() -> None:
        async def _no_data():
            return None

        generator = ReportGenerator(fetch_latest_reading=_no_data)
        assert await generator.build_report() is None

    asyncio.run(_run())
