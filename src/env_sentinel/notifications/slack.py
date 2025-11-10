"""Slack notifier implementation using slack_sdk.AsyncWebClient."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Mapping

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from env_sentinel.monitoring import AlertLevel
from env_sentinel.notifications.base import (
    BaseNotifier,
    NotificationConfigurationError,
    NotificationError,
)
from env_sentinel.notifications.models import MentionPolicy, NotificationMessage

SLACK_BOT_TOKEN_ENV = "ENV_SENTINEL_SLACK_BOT_TOKEN"

LEVEL_COLORS: Dict[AlertLevel, str] = {
    AlertLevel.INFO: "#439FE0",
    AlertLevel.WARNING: "#F2C744",
    AlertLevel.CRITICAL: "#D72B3F",
    AlertLevel.EMERGENCY: "#A30200",
}


class SlackMessageBuilder:
    """Convert NotificationMessage objects into Slack Block Kit payloads."""

    def __init__(self, channel: str) -> None:
        self._channel = channel

    def build_payload(self, message: NotificationMessage) -> Dict[str, Any]:
        """Return a ready-to-send payload for chat.postMessage."""
        mention_text = self._render_mentions(message)
        blocks = list(message.blocks) if message.blocks else self._build_default_blocks(message, mention_text)
        payload: Dict[str, Any] = {
            "channel": self._channel,
            "text": self._compose_plain_text(message, mention_text),
            "blocks": blocks,
        }
        attachments = self._build_attachments(message)
        if attachments:
            payload["attachments"] = attachments
        return payload

    def _build_default_blocks(self, message: NotificationMessage, mention_text: str) -> list[Mapping[str, Any]]:
        blocks: list[Mapping[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": message.title[:150], "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{mention_text} {message.body}".strip()},
            },
        ]

        metrics = message.context.metrics or {}
        if metrics:
            fields = [
                {"type": "mrkdwn", "text": f"*{key}*\n{value}"}
                for key, value in metrics.items()
            ]
            blocks.append({"type": "section", "fields": fields})
        return blocks

    def _build_attachments(self, message: NotificationMessage) -> list[Mapping[str, Any]]:
        if message.attachments:
            return list(message.attachments)
        if message.level is None:
            return []
        color = LEVEL_COLORS.get(message.level)
        if not color:
            return []
        return [
            {
                "color": color,
                "footer": f"Env-Sentinel • {message.timestamp.isoformat()}",
            }
        ]

    def _compose_plain_text(self, message: NotificationMessage, mention_text: str) -> str:
        text = f"{message.title}\n{message.body}"
        if mention_text:
            text = f"{mention_text} {text}"
        return text.strip()

    def _render_mentions(self, message: NotificationMessage) -> str:
        policy = message.mention_policy
        if policy == MentionPolicy.NONE:
            return ""
        if policy == MentionPolicy.HERE:
            return "<!here>"
        if policy == MentionPolicy.CHANNEL:
            return "<!channel>"
        if policy == MentionPolicy.CUSTOM:
            return " ".join(self._normalize_user_id(user_id) for user_id in message.mention_targets if user_id)
        return ""

    @staticmethod
    def _normalize_user_id(user_id: str) -> str:
        if user_id.startswith("<@") and user_id.endswith(">"):
            return user_id
        return f"<@{user_id}>"


class SlackNotifier(BaseNotifier):
    """Send notifications to Slack using the official async SDK."""

    def __init__(
        self,
        *,
        channel: str,
        token: str | None = None,
        client: AsyncWebClient | None = None,
        builder: SlackMessageBuilder | None = None,
    ) -> None:
        super().__init__()
        resolved_token = token or os.getenv(SLACK_BOT_TOKEN_ENV)
        if not resolved_token and client is None:
            raise NotificationConfigurationError(
                "Slack bot token is required. Set ENV_SENTINEL_SLACK_BOT_TOKEN or pass token explicitly."
            )

        self._client = client or AsyncWebClient(token=resolved_token)
        self._builder = builder or SlackMessageBuilder(channel=channel)

    async def send_notification(self, message: NotificationMessage) -> bool:
        payload = self._builder.build_payload(message)
        try:
            await self._client.chat_postMessage(**payload)
            return True
        except SlackApiError as exc:
            self._logger.error("Slack API error: %s", exc.response.get("error"))
            raise NotificationError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.exception("Unexpected Slack notification failure")
            raise NotificationError("Unexpected Slack notifier error") from exc


__all__ = ["SlackMessageBuilder", "SlackNotifier", "SLACK_BOT_TOKEN_ENV"]
