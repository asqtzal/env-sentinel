"""Tests for Slack notifier and message builder."""

from __future__ import annotations

import asyncio

import pytest

from env_sentinel.monitoring import AlertLevel
from env_sentinel.notifications import (
    MentionPolicy,
    NotificationConfigurationError,
    NotificationContext,
    NotificationKind,
    NotificationMessage,
)
from env_sentinel.notifications.slack import SlackMessageBuilder, SlackNotifier


class DummySlackClient:
    """Minimal async client stub capturing chat_postMessage payloads."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def chat_postMessage(self, **payload):  # type: ignore[override]
        self.calls.append(payload)
        return {"ok": True}


def _sample_message() -> NotificationMessage:
    context = NotificationContext(metrics={"温度": "25.0℃", "湿度": "45%"})
    return NotificationMessage(
        kind=NotificationKind.ALERT,
        title="⚠️ 温度が上昇",
        body="26℃ を超過しました",
        level=AlertLevel.WARNING,
        mention_policy=MentionPolicy.CUSTOM,
        mention_targets=("U123",),
        context=context,
    )


def test_builder_adds_mentions_and_metrics() -> None:
    builder = SlackMessageBuilder(channel="#dummy")
    message = _sample_message()
    payload = builder.build_payload(message)

    assert payload["channel"] == "#dummy"
    assert payload["text"].startswith("<@U123>")
    assert payload["blocks"][0]["type"] == "header"
    assert any(field["text"].startswith("*温度*") for field in payload["blocks"][2]["fields"])
    assert payload["attachments"][0]["color"] == "#F2C744"


def test_slack_notifier_uses_injected_client() -> None:
    client = DummySlackClient()
    notifier = SlackNotifier(channel="#test", client=client, builder=SlackMessageBuilder("#test"))
    message = _sample_message()

    result = asyncio.run(notifier.send_notification(message))

    assert result is True
    assert len(client.calls) == 1
    assert client.calls[0]["channel"] == "#test"


def test_notifier_requires_token_when_no_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV_SENTINEL_SLACK_BOT_TOKEN", raising=False)
    with pytest.raises(NotificationConfigurationError):
        SlackNotifier(channel="#needs-token")
