"""Notification modules for Env-Sentinel."""

from .base import BaseNotifier, NotificationConfigurationError, NotificationError
from .coordinator import NotificationCoordinator
from .dispatcher import FixedWindowRateLimiter, NotificationQueue, RateLimiter
from .fallback import NotificationFallbackStore
from .models import MentionPolicy, NotificationContext, NotificationKind, NotificationMessage
from .reports import ReportGenerator
from .slack import SlackNotifier, SlackMessageBuilder, SLACK_BOT_TOKEN_ENV

__all__ = [
    "BaseNotifier",
    "NotificationCoordinator",
    "NotificationQueue",
    "RateLimiter",
    "FixedWindowRateLimiter",
    "ReportGenerator",
    "NotificationFallbackStore",
    "SlackNotifier",
    "SlackMessageBuilder",
    "SLACK_BOT_TOKEN_ENV",
    "MentionPolicy",
    "NotificationConfigurationError",
    "NotificationContext",
    "NotificationError",
    "NotificationKind",
    "NotificationMessage",
]
