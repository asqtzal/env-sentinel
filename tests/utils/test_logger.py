"""Tests for the logging utilities."""

import logging
from contextlib import ExitStack

from env_sentinel.utils.logger import get_logger


def test_get_logger_configures_root_logger() -> None:
    """Ensure get_logger applies default configuration when handlers are absent."""
    root_logger = logging.getLogger()
    with ExitStack() as cleanup_stack:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            cleanup_stack.callback(root_logger.addHandler, handler)

        logger = get_logger("tests.sample")

        assert logger.name == "tests.sample"
        assert logging.getLogger().handlers, "Handlers should be configured by get_logger"
