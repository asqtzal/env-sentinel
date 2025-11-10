"""Configuration management utilities."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from pydantic import ValidationError

from .models import AppConfig
from env_sentinel.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manage loading, saving, and hot-reloading of application configuration."""

    def __init__(
        self,
        config_path: Path,
        default_path: Path,
        on_reload: Optional[Callable[[AppConfig], None]] = None,
        fallback_callback: Optional[Callable[[Exception], None]] = None,
        poll_interval_seconds: int = 5,
    ) -> None:
        """Initialize the manager.

        Args:
            config_path: Path to the active configuration file.
            default_path: Path to the default configuration template.
            on_reload: Optional callback invoked when configuration is reloaded successfully.
            fallback_callback: Optional callback invoked when invalid configuration is detected.
            poll_interval_seconds: Interval between reload checks when `start_polling` is used.
        """
        self._config_path = config_path
        self._default_path = default_path
        self._on_reload = on_reload
        self._fallback_callback = fallback_callback
        self._poll_interval_seconds = poll_interval_seconds
        self._lock = threading.Lock()
        self._config = AppConfig.defaults()
        self._last_modified: float = 0.0
        self._stop_event = threading.Event()
        self._watcher_thread: Optional[threading.Thread] = None

    @property
    def config(self) -> AppConfig:
        """Return the active configuration."""
        return self._config

    def load(self) -> AppConfig:
        """Load the configuration from disk, creating it if necessary."""
        with self._lock:
            if not self._config_path.exists():
                logger.info("Configuration not found; generating default at %s", self._config_path)
                self._write_default()
            self._config = self._read_config(self._config_path)
            self._last_modified = self._config_path.stat().st_mtime
            logger.debug("Configuration loaded from %s", self._config_path)
            return self._config

    def save(self, config: Optional[AppConfig] = None) -> None:
        """Persist the provided configuration to disk."""
        with self._lock:
            target_config = config or self._config
            serialized = json.dumps(target_config.to_dict(), indent=2, default=str)
            self._config_path.write_text(serialized, encoding="utf-8")
            self._last_modified = self._config_path.stat().st_mtime
            logger.debug("Configuration saved to %s", self._config_path)

    def reload_if_updated(self) -> bool:
        """Reload configuration if the file has changed since the last load."""
        with self._lock:
            if not self._config_path.exists():
                logger.warning("Configuration path %s missing; regenerating default", self._config_path)
                self._write_default()
            current_mtime = self._config_path.stat().st_mtime
            if current_mtime <= self._last_modified:
                return False
            try:
                new_config = self._read_config(self._config_path)
                self._config = new_config
                self._last_modified = current_mtime
                if self._on_reload:
                    self._on_reload(new_config)
                logger.info("Configuration reloaded from %s", self._config_path)
                return True
            except ValidationError as exc:
                logger.error("Invalid configuration detected, reverting to defaults: %s", exc)
                self._config = AppConfig.defaults()
                self._write_default()
                if self._fallback_callback:
                    self._fallback_callback(exc)
                return False

    def start_polling(self) -> None:
        """Start a watcher thread that polls for configuration changes."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._stop_event.clear()
        self._watcher_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watcher_thread.start()

    def stop_polling(self) -> None:
        """Stop the watcher thread."""
        self._stop_event.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=self._poll_interval_seconds * 2)

    def set_reload_callback(self, callback: Optional[Callable[[AppConfig], None]]) -> None:
        """Update the callback invoked after successful reloads."""
        with self._lock:
            self._on_reload = callback

    def _watch_loop(self) -> None:
        """Polling loop for configuration reloads."""
        while not self._stop_event.is_set():
            try:
                self.reload_if_updated()
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Unexpected error watching config: %s", exc)
            time.sleep(self._poll_interval_seconds)

    def _read_config(self, path: Path) -> AppConfig:
        """Read configuration from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig.from_dict(data)

    def _write_default(self) -> None:
        """Write the default configuration to the active config path."""
        default_text = self._default_path.read_text(encoding="utf-8")
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(default_text, encoding="utf-8")
