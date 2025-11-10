"""Tests for EnvSentinelApp orchestration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from env_sentinel.config import AppConfig, ConfigManager
from env_sentinel.core import NotificationRuntime
from env_sentinel.core.app import EnvSentinelApp
from env_sentinel.monitoring import AlertManager
from env_sentinel.storage import LocalStorage


class StubRuntime:
    """Lightweight stub matching NotificationRuntime's public interface."""

    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.events: list[tuple[str, str]] = []
        self.reloads: list[AppConfig] = []

    async def start(self) -> None:  # type: ignore[override]
        self.started = True

    async def stop(self) -> None:  # type: ignore[override]
        self.stopped = True

    async def emit_system_event(self, title: str, body: str) -> None:  # type: ignore[override]
        self.events.append((title, body))

    async def reload(self, new_config: AppConfig) -> None:  # type: ignore[override]
        self.reloads.append(new_config)


def _runtime_factory(stub: StubRuntime):
    def _factory(
        config: AppConfig,
        alert_manager: AlertManager,
        storage: LocalStorage,
    ) -> NotificationRuntime:
        return stub  # type: ignore[return-value]

    return _factory


def _write_config(tmp_path) -> Path:
    config_data = json.loads(Path("config/default_config.json").read_text(encoding="utf-8"))
    config_data["storage"]["db_path"] = str(tmp_path / "env.db")
    config_path = tmp_path / "app_config.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    return config_path


def test_env_app_start_stop_and_reload(tmp_path) -> None:
    async def _run() -> None:
        config_path = _write_config(tmp_path)
        manager = ConfigManager(config_path=config_path, default_path=Path("config/default_config.json"))
        stub_runtime = StubRuntime()
        app = EnvSentinelApp(
            config_manager=manager,
            runtime_factory=_runtime_factory(stub_runtime),
        )

        await app.start()
        assert stub_runtime.started is True
        assert app.alert_manager is not None

        new_config = AppConfig.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
        new_config = new_config.copy(
            update={
                "notifications": new_config.notifications.copy(
                    update={
                        "slack": new_config.notifications.slack.copy(
                            update={"alert_mention_targets": ["U42"]}
                        )
                    }
                )
            }
        )
        app.handle_config_reload(new_config)
        await app.wait_for_reload()
        assert stub_runtime.reloads

        await app.stop()
        assert stub_runtime.stopped is True
        assert any("起動" in title for title, _ in stub_runtime.events)
        assert any("停止" in title for title, _ in stub_runtime.events)

    asyncio.run(_run())
