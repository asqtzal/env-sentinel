"""Tests for NotificationCoordinator."""

from __future__ import annotations

import asyncio

from env_sentinel.config import AppConfig, SlackConfig, SlackMentionPolicy
from env_sentinel.monitoring import Alert, AlertCategory, AlertLevel, AlertManager
from env_sentinel.notifications import MentionPolicy, NotificationCoordinator
from env_sentinel.notifications.base import BaseNotifier
from env_sentinel.notifications.models import NotificationKind, NotificationMessage


class DummyNotifier(BaseNotifier):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[NotificationMessage] = []

    async def send_notification(self, message: NotificationMessage) -> bool:
        self.sent.append(message)
        return True


class DummyAlertManager:
    def __init__(self) -> None:
        self.listener = None

    def register_listener(self, listener):
        self.listener = listener


def test_coordinator_converts_alert_to_notification() -> None:
    notifier = DummyNotifier()
    coordinator = NotificationCoordinator(
        notifier,
        alert_mention_policy=MentionPolicy.CUSTOM,
        alert_mentions=("U999",),
    )
    manager = DummyAlertManager()
    coordinator.attach_alert_manager(manager)  # type: ignore[arg-type]

    alert = Alert(
        level=AlertLevel.WARNING,
        category=AlertCategory.TEMPERATURE,
        subject="temperature_warning_high",
        message="温度が閾値を超過しました",
    )

    asyncio.run(manager.listener(alert))  # type: ignore[func-returns-value]

    assert len(notifier.sent) == 1
    sent = notifier.sent[0]
    assert sent.kind.name == "ALERT"
    assert sent.mention_policy == MentionPolicy.CUSTOM
    assert sent.mention_targets == ("U999",)
    assert "温度アラート" in sent.title


def test_coordinator_from_config_uses_policy(tmp_path) -> None:
    notifier = DummyNotifier()
    slack_config = SlackConfig(
        channel="#alerts",
        alert_mention_policy=SlackMentionPolicy.HERE,
        alert_mention_targets=[],
    )
    coordinator = NotificationCoordinator.from_slack_config(
        notifier,
        config=slack_config,
        fallback_path=tmp_path / "pending.json",
    )

    assert coordinator._alert_mention_policy == MentionPolicy.HERE  # pylint: disable=protected-access


def test_emit_system_event_sends_notification() -> None:
    async def _run() -> None:
        notifier = DummyNotifier()
        coordinator = NotificationCoordinator(notifier)
        await coordinator.emit_system_event(title="起動完了", body="Env-Sentinelを開始しました")
        assert notifier.sent[0].kind == NotificationKind.SYSTEM

    asyncio.run(_run())


def test_report_loop_sends_reports() -> None:
    class StubReportGenerator:
        def __init__(self) -> None:
            self.calls = 0

        async def build_report(self) -> NotificationMessage | None:
            self.calls += 1
            if self.calls == 1:
                return NotificationMessage(
                    kind=NotificationKind.REPORT,
                    title="report",
                    body="body",
                )
            return None

    async def _run() -> None:
        notifier = DummyNotifier()
        generator = StubReportGenerator()
        coordinator = NotificationCoordinator(
            notifier,
            report_interval_seconds=0.01,
            report_generator=generator,
        )
        await coordinator.start()
        await asyncio.sleep(0.05)
        await coordinator.stop()
        assert any(message.kind == NotificationKind.REPORT for message in notifier.sent)

    asyncio.run(_run())


def test_listener_detached_on_stop() -> None:
    async def _run() -> None:
        notifier = DummyNotifier()
        manager = AlertManager(AppConfig.defaults().alerts)
        coordinator = NotificationCoordinator(notifier)
        coordinator.attach_alert_manager(manager)
        assert len(manager._listeners) == 1  # pylint: disable=protected-access
        await coordinator.stop()
        assert len(manager._listeners) == 0  # pylint: disable=protected-access

    asyncio.run(_run())
