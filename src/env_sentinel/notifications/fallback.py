"""Persistence helpers for notifications that could not be delivered immediately."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from env_sentinel.monitoring import AlertLevel
from env_sentinel.notifications.models import (
    MentionPolicy,
    NotificationContext,
    NotificationKind,
    NotificationMessage,
)


class NotificationFallbackStore:
    """Store pending notifications on disk so they can be retried later."""

    def __init__(self, path: Path | str = Path("data/pending_notifications.json")) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def append(self, message: NotificationMessage) -> None:
        """Persist a notification for later retry."""
        async with self._lock:
            payloads = await self._read_all()
            payloads.append(self._serialize(message))
            await self._write(payloads)

    async def consume(self) -> list[NotificationMessage]:
        """Return and remove all stored notifications."""
        async with self._lock:
            payloads = await self._read_all()
            if not payloads:
                return []
            await self._remove()
            return [self._deserialize(payload) for payload in payloads]

    async def _read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return await asyncio.to_thread(lambda: json.loads(self._path.read_text(encoding="utf-8")))

    async def _write(self, payloads: list[dict[str, Any]]) -> None:
        await asyncio.to_thread(self._write_sync, payloads)

    def _write_sync(self, payloads: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding="utf-8")

    async def _remove(self) -> None:
        if self._path.exists():
            await asyncio.to_thread(self._path.unlink)

    @staticmethod
    def _serialize(message: NotificationMessage) -> dict[str, Any]:
        context = {
            "metrics": message.context.metrics,
            "extra": message.context.extra,
        }
        return {
            "kind": message.kind.value,
            "title": message.title,
            "body": message.body,
            "level": message.level.value if message.level else None,
            "mention_policy": message.mention_policy.value,
            "mention_targets": list(message.mention_targets),
            "context": context,
            "timestamp": message.timestamp.isoformat(),
        }

    @staticmethod
    def _deserialize(payload: Mapping[str, Any]) -> NotificationMessage:
        level = payload.get("level")
        mention_policy = MentionPolicy(payload["mention_policy"])
        message = NotificationMessage(
            kind=NotificationKind(payload["kind"]),
            title=payload["title"],
            body=payload["body"],
            level=AlertLevel(level) if level else None,
            mention_policy=mention_policy,
            mention_targets=tuple(payload.get("mention_targets", ())),
            context=NotificationContext(
                metrics=payload.get("context", {}).get("metrics"),
                extra=payload.get("context", {}).get("extra"),
            ),
            timestamp=datetime.fromisoformat(payload["timestamp"]),
        )
        return message


__all__ = ["NotificationFallbackStore"]
