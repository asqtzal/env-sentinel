"""Notification data models shared across notifier implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

try:  # Python 3.11+
    from datetime import UTC
except ImportError:  # Python 3.9 compatibility
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[assignment]

from env_sentinel.monitoring import Alert, AlertLevel


class NotificationKind(str, Enum):
    """High-level classification for outbound notifications."""

    ALERT = "alert"
    REPORT = "report"
    SYSTEM = "system"


class MentionPolicy(str, Enum):
    """Control how Slack mentions are applied to a message."""

    NONE = "none"
    HERE = "here"
    CHANNEL = "channel"
    CUSTOM = "custom"


@dataclass
class NotificationContext:
    """Additional structured context to enrich a notification."""

    alert: Alert | None = None
    metrics: Mapping[str, Any] | None = None
    extra: Mapping[str, Any] | None = None


@dataclass
class NotificationMessage:
    """Normalized notification payload consumed by BaseNotifier implementations."""

    kind: NotificationKind
    title: str
    body: str
    level: AlertLevel | None = None
    mention_policy: MentionPolicy = MentionPolicy.NONE
    mention_targets: tuple[str, ...] = ()
    context: NotificationContext = field(default_factory=NotificationContext)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    blocks: list[Mapping[str, Any]] = field(default_factory=list)
    attachments: list[Mapping[str, Any]] = field(default_factory=list)

    def with_blocks(self, blocks: Sequence[Mapping[str, Any]]) -> "NotificationMessage":
        """Return a copy with Block Kit payload attached."""
        self.blocks = list(blocks)
        return self


__all__ = [
    "MentionPolicy",
    "NotificationContext",
    "NotificationKind",
    "NotificationMessage",
]
