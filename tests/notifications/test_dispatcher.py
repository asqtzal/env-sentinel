"""Tests for NotificationQueue and rate limiter utilities."""

from __future__ import annotations

import asyncio

import pytest

from env_sentinel.notifications.dispatcher import FixedWindowRateLimiter, NotificationQueue, RateLimiter
from env_sentinel.notifications.fallback import NotificationFallbackStore
from env_sentinel.notifications.models import NotificationKind, NotificationMessage
from env_sentinel.notifications.base import BaseNotifier


class DummyLimiter(RateLimiter):
    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


class DummyNotifier(BaseNotifier):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []
        self.raise_once = False

    async def send_notification(self, message: NotificationMessage) -> bool:
        if self.raise_once:
            self.raise_once = False
            raise RuntimeError("fail")
        self.sent.append(message.title)
        return True


def _message(title: str) -> NotificationMessage:
    return NotificationMessage(
        kind=NotificationKind.ALERT,
        title=title,
        body="body",
    )


def test_queue_respects_priority() -> None:
    async def _run() -> None:
        notifier = DummyNotifier()
        limiter = DummyLimiter()
        queue = NotificationQueue(notifier, rate_limiter=limiter)
        await queue.start()
        await queue.enqueue(_message("low"), priority=0)
        await queue.enqueue(_message("critical"), priority=3)
        await asyncio.sleep(0)
        await queue.stop()
        assert notifier.sent[0] == "critical"
        assert notifier.sent[1] == "low"
        assert limiter.calls == 2

    asyncio.run(_run())


def test_fixed_window_rate_limiter_enforces_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        limiter = FixedWindowRateLimiter(per_minute=60)
        sleep_calls: list[float] = []

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        monkeypatch.setattr("asyncio.sleep", fake_sleep)
        loop = asyncio.get_running_loop()
        start = loop.time()
        limiter._last_sent = start  # pylint: disable=protected-access
        await limiter.acquire()
        assert sleep_calls

    asyncio.run(_run())


def test_fallback_store_requeues_messages(tmp_path) -> None:
    async def _run() -> None:
        notifier = DummyNotifier()
        limiter = DummyLimiter()
        fallback = NotificationFallbackStore(tmp_path / "pending.json")
        queue = NotificationQueue(notifier, rate_limiter=limiter, fallback_store=fallback)
        notifier.raise_once = True
        await queue.start()
        await queue.enqueue(_message("will fail"), priority=0)
        await asyncio.sleep(0.1)
        await queue.stop()
        assert not notifier.sent

        notifier.raise_once = False
        queue2 = NotificationQueue(notifier, rate_limiter=limiter, fallback_store=fallback)
        await queue2.start()
        await asyncio.sleep(0.1)
        await queue2.stop()
        assert notifier.sent == ["will fail"]

    asyncio.run(_run())
