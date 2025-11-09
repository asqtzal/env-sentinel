"""High-level runtime wiring for notifications."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from env_sentinel.config import AppConfig
from env_sentinel.monitoring import AlertManager
from env_sentinel.notifications import (
    BaseNotifier,
    NotificationCoordinator,
    ReportGenerator,
    SlackNotifier,
)
from env_sentinel.sensors import SensorReading
from env_sentinel.storage import LocalStorage

LatestReadingProvider = Callable[[], Awaitable[Optional[SensorReading]]]


class NotificationRuntime:
    """Coordinates notifier wiring, AlertManager listeners, and report scheduling."""

    def __init__(
        self,
        *,
        config: AppConfig,
        alert_manager: AlertManager,
        latest_reading_provider: LatestReadingProvider | None = None,
        storage: LocalStorage | None = None,
        notifier_factory: Callable[[AppConfig], BaseNotifier] | None = None,
        report_generator_factory: Callable[[LatestReadingProvider], ReportGenerator] | None = None,
    ) -> None:
        self._config = config
        self._alert_manager = alert_manager
        if latest_reading_provider is None:
            if storage is None:
                raise ValueError("latest_reading_provider or storage must be provided")
            self._latest_reading_provider = self._default_latest_provider
        else:
            self._latest_reading_provider = latest_reading_provider
        self._storage = storage
        self._coordinator: NotificationCoordinator | None = None
        self._notifier: BaseNotifier | None = None
        self._lock = asyncio.Lock()
        self._notifier_factory = notifier_factory or self._default_notifier_factory
        self._report_generator_factory = report_generator_factory or (
            lambda fetcher: ReportGenerator(fetcher)
        )

    async def start(self) -> None:
        """Initialize notifier/coordinator and attach to AlertManager."""
        async with self._lock:
            await self._ensure_started()

    async def stop(self) -> None:
        """Stop coordinator and release notifier resources."""
        async with self._lock:
            await self._stop_locked()

    async def emit_system_event(self, title: str, body: str) -> None:
        """Send a system lifecycle notification."""
        coordinator = await self._ensure_started()
        await coordinator.emit_system_event(title=title, body=body)

    async def reload(self, new_config: AppConfig) -> None:
        """Rebuild notifier and coordinator with new configuration."""
        async with self._lock:
            await self._stop_locked()
            self._config = new_config
            await self._ensure_started()

    async def _ensure_started(self) -> NotificationCoordinator:
        if self._coordinator:
            return self._coordinator

        slack_config = self._config.notifications.slack
        self._notifier = self._notifier_factory(self._config)

        report_generator = self._report_generator_factory(self._latest_reading_provider)
        coordinator = NotificationCoordinator.from_slack_config(
            self._notifier,
            config=self._config.notifications.slack,
            report_generator=report_generator,
        )
        coordinator.attach_alert_manager(self._alert_manager)
        await coordinator.start()
        self._coordinator = coordinator
        return coordinator

    async def _default_latest_provider(self) -> Optional[SensorReading]:
        if not self._storage:
            return None
        readings = await self._storage.get_recent_data(hours=24, limit=1)
        return readings[0] if readings else None

    def _default_notifier_factory(self, config: AppConfig) -> BaseNotifier:
        slack_config = config.notifications.slack
        return SlackNotifier(channel=slack_config.channel)

    async def _stop_locked(self) -> None:
        if self._coordinator:
            await self._coordinator.stop()
        if self._notifier:
            await self._notifier.close()
        self._coordinator = None
        self._notifier = None
