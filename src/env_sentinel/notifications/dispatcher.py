"""Notification queue and rate limiter utilities."""

from __future__ import annotations

import asyncio
import itertools
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from pathlib import Path

from env_sentinel.notifications.base import BaseNotifier
from env_sentinel.notifications.models import NotificationMessage
from env_sentinel.utils.logger import get_logger

from .fallback import NotificationFallbackStore

_PRIORITY_COUNTER = itertools.count()


class RateLimiter(ABC):
    """Abstract rate limiter to throttle notification delivery."""

    @abstractmethod
    async def acquire(self) -> None:
        """Wait until the next send operation may proceed."""


class FixedWindowRateLimiter(RateLimiter):
    """Simple limiter that enforces a minimum interval between sends."""

    def __init__(self, per_minute: int) -> None:
        if per_minute < 1:
            raise ValueError("per_minute must be >= 1")
        self._min_interval = 60.0 / per_minute
        self._last_sent: float = 0.0

    async def acquire(self) -> None:
        loop = asyncio.get_running_loop()
        now = loop.time()
        wait = self._min_interval - (now - self._last_sent)
        if wait > 0:
            await asyncio.sleep(wait)
            now = loop.time()
        self._last_sent = now


class NotificationQueue:
    """Priority queue with background worker to send notifications serially."""

    def __init__(
        self,
        notifier: BaseNotifier,
        *,
        rate_limiter: RateLimiter,
        fallback_store: NotificationFallbackStore | None = None,
    ) -> None:
        self._notifier = notifier
        self._rate_limiter = rate_limiter
        self._fallback_store = fallback_store
        self._queue: asyncio.PriorityQueue[Tuple[int, int, Optional[NotificationMessage]]] = (
            asyncio.PriorityQueue()
        )
        self._worker: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._logger = get_logger(__name__)

    async def start(self) -> None:
        """Start the background worker if not already running."""
        if self._worker and not self._worker.done():
            return
        self._stop_event.clear()
        self._worker = asyncio.create_task(self._run())
        await self._requeue_fallback_messages()

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        if not self._worker:
            return
        await self._queue.put((0, next(_PRIORITY_COUNTER), None))
        self._stop_event.set()
        await self._worker
        self._worker = None

    async def enqueue(self, message: NotificationMessage, priority: int = 0) -> None:
        """Add a message to the queue."""
        await self._queue.put((-priority, next(_PRIORITY_COUNTER), message))

    async def _run(self) -> None:
        while True:
            priority, _, message = await self._queue.get()
            if message is None:
                break
            try:
                await self._rate_limiter.acquire()
                await self._notifier.send_notification(message)
            except Exception:  # pragma: no cover - defensive logging
                self._logger.exception("Failed to deliver notification")
                if self._fallback_store:
                    await self._fallback_store.append(message)
            finally:
                self._queue.task_done()

    async def _requeue_fallback_messages(self) -> None:
        if not self._fallback_store:
            return
        pending = await self._fallback_store.consume()
        for message in pending:
            await self._queue.put((-3, next(_PRIORITY_COUNTER), message))
        if pending:
            self._logger.info("Requeued %s pending notification(s)", len(pending))


__all__ = ["FixedWindowRateLimiter", "NotificationQueue", "RateLimiter"]
