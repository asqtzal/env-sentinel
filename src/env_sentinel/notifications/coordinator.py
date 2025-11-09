"""Glue code that connects AlertManager events to notifier implementations."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Sequence

from env_sentinel.config import SlackConfig, SlackMentionPolicy
from env_sentinel.monitoring import Alert, AlertCategory, AlertLevel, AlertManager
from env_sentinel.notifications.base import BaseNotifier
from pathlib import Path

from env_sentinel.notifications.dispatcher import FixedWindowRateLimiter, NotificationQueue, RateLimiter
from env_sentinel.notifications.reports import ReportGenerator
from env_sentinel.notifications.fallback import NotificationFallbackStore
from env_sentinel.notifications.models import (
    MentionPolicy,
    NotificationContext,
    NotificationKind,
    NotificationMessage,
)
from env_sentinel.utils.logger import get_logger

AlertListener = Callable[[Alert], Awaitable[None] | None]

ALERT_EMOJI = {
    AlertLevel.INFO: "ℹ️",
    AlertLevel.WARNING: "⚠️",
    AlertLevel.CRITICAL: "🚨",
    AlertLevel.EMERGENCY: "🆘",
}


class NotificationCoordinator:
    """Route AlertManager events to the configured notifier and queue delivery."""

    def __init__(
        self,
        notifier: BaseNotifier,
        *,
        alert_mention_policy: MentionPolicy = MentionPolicy.NONE,
        alert_mentions: Sequence[str] | None = None,
        queue: NotificationQueue | None = None,
        report_interval_seconds: int | None = None,
        report_generator: ReportGenerator | None = None,
    ) -> None:
        self._notifier = notifier
        self._alert_mention_policy = alert_mention_policy
        self._alert_mentions = tuple(alert_mentions or ())
        self._queue = queue
        self._report_interval = report_interval_seconds
        self._report_generator = report_generator
        self._report_task: asyncio.Task[None] | None = None
        self._report_stop = asyncio.Event()
        self._logger = get_logger(__name__)
        self._alert_listener: AlertListener | None = None
        self._attached_manager: AlertManager | None = None

    async def start(self) -> None:
        """Start queue worker if configured."""
        if self._queue:
            await self._queue.start()
        if self._report_generator and self._report_interval:
            if self._report_task and not self._report_task.done():
                return
            self._report_stop.clear()
            self._report_task = asyncio.create_task(self._report_loop())

    async def stop(self) -> None:
        """Stop queue worker if configured."""
        if self._queue:
            await self._queue.stop()
        if self._report_task:
            self._report_stop.set()
            await self._report_task
            self._report_task = None
        self._detach_alert_listener()

    def attach_alert_manager(self, manager: AlertManager) -> None:
        """Register the coordinator as an AlertManager listener."""
        if self._alert_listener is None:
            self._alert_listener = self._build_listener()
        manager.register_listener(self._alert_listener)
        self._attached_manager = manager

    @classmethod
    def from_slack_config(
        cls,
        notifier: BaseNotifier,
        *,
        config: SlackConfig,
        report_generator: ReportGenerator | None = None,
        fallback_path: Path | str | None = None,
    ) -> "NotificationCoordinator":
        """Factory that instantiates the coordinator from SlackConfig."""
        policy = cls._map_policy(config.alert_mention_policy)
        mentions = tuple(config.alert_mention_targets or ())
        rate_limiter = FixedWindowRateLimiter(config.rate_limit_per_minute)
        fallback_store = NotificationFallbackStore(Path(fallback_path) if fallback_path else Path("data/pending_notifications.json"))
        queue = NotificationQueue(
            notifier,
            rate_limiter=rate_limiter,
            fallback_store=fallback_store,
        )
        return cls(
            notifier,
            alert_mention_policy=policy,
            alert_mentions=mentions,
            queue=queue,
            report_interval_seconds=config.report_interval_seconds,
            report_generator=report_generator,
        )

    def _build_listener(self) -> AlertListener:
        async def _listener(alert: Alert) -> None:
            message = self._build_alert_notification(alert)
            await self._safe_send(message)

        return _listener

    async def _safe_send(self, message: NotificationMessage) -> None:
        try:
            await self._send(message)
        except Exception:  # pragma: no cover - delegated to notifier tests
            self._logger.exception("Failed to deliver notification")

    async def emit_system_event(
        self,
        *,
        title: str,
        body: str,
        level: AlertLevel = AlertLevel.INFO,
        mention_policy: MentionPolicy = MentionPolicy.NONE,
    ) -> None:
        """Send a system lifecycle/status notification."""
        message = NotificationMessage(
            kind=NotificationKind.SYSTEM,
            title=title,
            body=body,
            level=level,
            mention_policy=mention_policy,
        )
        await self._safe_send(message)

    async def _report_loop(self) -> None:
        assert self._report_generator is not None
        assert self._report_interval is not None
        try:
            while not self._report_stop.is_set():
                message = await self._report_generator.build_report()
                if message:
                    await self._safe_send(message)
                try:
                    await asyncio.wait_for(
                        self._report_stop.wait(),
                        timeout=self._report_interval,
                    )
                except asyncio.TimeoutError:
                    continue
        except Exception:  # pragma: no cover - defensive logging
            self._logger.exception("Report loop encountered an error")

    def _build_alert_notification(self, alert: Alert) -> NotificationMessage:
        emoji = ALERT_EMOJI.get(alert.level, "ℹ️")
        category_label = self._render_category(alert.category)
        title = f"{emoji} {category_label}"
        context = NotificationContext(alert=alert)
        return NotificationMessage(
            kind=NotificationKind.ALERT,
            title=title,
            body=alert.message,
            level=alert.level,
            mention_policy=self._alert_mention_policy,
            mention_targets=self._alert_mentions,
            context=context,
        )

    async def _send(self, message: NotificationMessage) -> None:
        if self._queue:
            priority = self._priority_for_message(message)
            await self._queue.enqueue(message, priority=priority)
        else:
            await self._notifier.send_notification(message)

    @staticmethod
    def _priority_for_message(message: NotificationMessage) -> int:
        if not message.level:
            return 0
        priorities = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.CRITICAL: 2,
            AlertLevel.EMERGENCY: 3,
        }
        return priorities.get(message.level, 0)

    def _detach_alert_listener(self) -> None:
        if self._attached_manager and self._alert_listener:
            self._attached_manager.unregister_listener(self._alert_listener)
        self._attached_manager = None

    @staticmethod
    def _render_category(category: AlertCategory) -> str:
        mapping = {
            AlertCategory.TEMPERATURE: "温度アラート",
            AlertCategory.HUMIDITY: "湿度アラート",
            AlertCategory.SENSOR: "センサアラート",
        }
        return mapping.get(category, category.value)

    @staticmethod
    def _map_policy(policy: SlackMentionPolicy | MentionPolicy) -> MentionPolicy:
        if isinstance(policy, MentionPolicy):
            return policy
        mapping = {
            SlackMentionPolicy.NONE: MentionPolicy.NONE,
            SlackMentionPolicy.HERE: MentionPolicy.HERE,
            SlackMentionPolicy.CHANNEL: MentionPolicy.CHANNEL,
            SlackMentionPolicy.CUSTOM: MentionPolicy.CUSTOM,
        }
        return mapping[policy]


__all__ = ["NotificationCoordinator"]
