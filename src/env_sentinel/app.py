"""Executable entry point for Env-Sentinel."""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from typing import Iterable, Optional

from env_sentinel.config import ConfigManager
from env_sentinel.core import EnvSentinelApp, MonitoringLoop
from env_sentinel.utils.logger import configure_logging, get_logger

LOGGER = get_logger(__name__)


async def run_app(
    *,
    config_path: Path | str = Path("config/app_config.json"),
    default_path: Path | str = Path("config/default_config.json"),
) -> None:
    """Bootstrap Env-Sentinel with configuration reload and graceful shutdown."""
    configure_logging()

    manager = ConfigManager(config_path=Path(config_path), default_path=Path(default_path))
    app = EnvSentinelApp(manager)

    await app.start()
    monitoring_loop = MonitoringLoop(
        config_provider=lambda: app.config,
        alert_manager=app.alert_manager,
        storage=app.storage,
    )
    await monitoring_loop.start()
    manager.start_polling()
    LOGGER.info("Env-Sentinel is running. Press Ctrl+C to stop.")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _handle_stop() -> None:
        if not stop_event.is_set():
            stop_event.set()

    for sig in _supported_signals():
        try:
            loop.add_signal_handler(sig, _handle_stop)
        except NotImplementedError:
            LOGGER.debug("Signal handler not supported for %s on this platform", sig)

    try:
        await stop_event.wait()
    finally:
        manager.stop_polling()
        await monitoring_loop.stop()
        await app.stop()


def _supported_signals() -> Iterable[int]:
    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            yield sig


def main() -> None:
    """CLI entry point (``python -m env_sentinel.app``)."""
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:  # pragma: no cover - handled by signal
        return


if __name__ == "__main__":
    main()
