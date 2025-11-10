"""Abstract interface for notification backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final

from env_sentinel.notifications.models import NotificationMessage
from env_sentinel.utils.logger import get_logger

LOGGER_NAME: Final = "env_sentinel.notifications"


class NotificationError(RuntimeError):
    """Raised when delivering or preparing a notification fails."""


class NotificationConfigurationError(NotificationError):
    """Raised when required configuration (e.g., Slack token) is missing."""


class BaseNotifier(ABC):
    """Common notifier interface to deliver messages to downstream services."""

    def __init__(self) -> None:
        self._logger = get_logger(LOGGER_NAME)

    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Deliver a normalized notification to the downstream service."""

    async def close(self) -> None:
        """Release any resources held by the notifier."""
        # Default implementations do not hold resources.
        return None


__all__ = [
    "BaseNotifier",
    "NotificationConfigurationError",
    "NotificationError",
]
