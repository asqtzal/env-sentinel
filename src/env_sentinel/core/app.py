"""High-level application wiring for Env-Sentinel."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from typing import Callable

from env_sentinel.config import AppConfig, ConfigManager
from env_sentinel.monitoring import AlertManager
from .runtime import NotificationRuntime
from env_sentinel.storage import LocalStorage
from env_sentinel.utils.logger import get_logger

RuntimeFactory = Callable[[AppConfig, AlertManager, LocalStorage], NotificationRuntime]


class EnvSentinelApp:
    """Coordinate configuration, notification runtime, and shared infrastructure."""

    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        runtime_factory: RuntimeFactory | None = None,
    ) -> None:
        self._logger = get_logger(__name__)
        self._config_manager = config_manager
        self._runtime_factory = runtime_factory or self._default_runtime_factory

        self._config: AppConfig | None = None
        self._alert_manager: AlertManager | None = None
        self._storage: LocalStorage | None = None
        self._runtime: NotificationRuntime | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pending_reload: Future | None = None

        self._config_manager.set_reload_callback(self.handle_config_reload)

    @property
    def alert_manager(self) -> AlertManager:
        if not self._alert_manager:
            raise RuntimeError("EnvSentinelApp has not been started yet")
        return self._alert_manager

    @property
    def storage(self) -> LocalStorage:
        if not self._storage:
            raise RuntimeError("EnvSentinelApp has not been started yet")
        return self._storage

    @property
    def config(self) -> AppConfig:
        if not self._config:
            raise RuntimeError("EnvSentinelApp has not been started yet")
        return self._config

    async def start(self) -> None:
        """Initialize dependencies and start the notification runtime."""
        if self._runtime:
            self._logger.debug("Env-Sentinel runtime already started")
            return

        self._loop = asyncio.get_running_loop()

        config = self._config_manager.load()
        self._config = config

        self._alert_manager = AlertManager(config.alerts)
        if not self._storage:
            self._storage = LocalStorage.from_config(config.storage)
            await self._storage.initialize()

        self._runtime = self._runtime_factory(config, self._alert_manager, self._storage)
        await self._runtime.start()
        await self._runtime.emit_system_event("🚀 Env-Sentinel 起動", "システムを開始しました")
        self._logger.info("Env-Sentinel runtime started")

    async def stop(self) -> None:
        """Stop the notification runtime and release resources."""
        if not self._runtime:
            return
        await self._runtime.emit_system_event("🛑 Env-Sentinel 停止", "システムを停止します")
        await self._runtime.stop()
        self._runtime = None
        self._logger.info("Env-Sentinel runtime stopped")

    def handle_config_reload(self, new_config: AppConfig) -> None:
        """Callback invoked by ConfigManager when configuration changes."""
        old_config = self._config
        self._config = new_config

        if old_config:
            self._log_config_drift(old_config, new_config)

        if not self._runtime or not self._loop:
            return

        future = asyncio.run_coroutine_threadsafe(self._runtime.reload(new_config), self._loop)
        self._pending_reload = future

    async def wait_for_reload(self) -> None:
        """Await completion of the most recently scheduled reload (used in tests)."""
        if not self._pending_reload:
            return
        await asyncio.wrap_future(self._pending_reload)
        self._pending_reload = None

    def _default_runtime_factory(
        self,
        config: AppConfig,
        alert_manager: AlertManager,
        storage: LocalStorage,
    ) -> NotificationRuntime:
        return NotificationRuntime(
            config=config,
            alert_manager=alert_manager,
            storage=storage,
        )

    def _log_config_drift(self, old: AppConfig, new: AppConfig) -> None:
        if old.storage.db_path != new.storage.db_path:
            self._logger.warning(
                "Storage設定が変更されました (旧: %s, 新: %s)。反映にはプロセス再起動が必要です。",
                old.storage.db_path,
                new.storage.db_path,
            )
        if old.alerts != new.alerts:
            self._logger.info("アラート閾値が更新されました (再起動後に適用予定)")
