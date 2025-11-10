"""Logging utilities for the Env-Sentinel project."""

from __future__ import annotations

import logging
import os
from logging import Logger
from typing import Union

# ログ形式は運用で参照しやすいように日付・モジュール名・レベルを並べる
LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s] %(message)s"
DEFAULT_LOG_LEVEL = os.getenv("ENV_SENTINEL_LOG_LEVEL", "INFO")


def _normalize_level(level: Union[int, str]) -> int:
    """Normalize logging level to an integer value."""
    if isinstance(level, int):
        return level
    normalized = logging.getLevelName(level.upper())
    if isinstance(normalized, int):
        return normalized
    return logging.INFO


def configure_logging(level: Union[int, str] = DEFAULT_LOG_LEVEL) -> None:
    """Configure the root logger for the application.

    Args:
        level: Logging level as integer or case-insensitive string.
    """
    resolved_level = _normalize_level(level)
    logging.basicConfig(
        level=resolved_level,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> Logger:
    """Return a module-scoped logger instance.

    Ensures default configuration is applied once.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        Logger: Configured logger for the requested name.
    """
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)
