"""Storage modules for Env-Sentinel."""

from .local import LocalStorage, StorageError

__all__ = ["LocalStorage", "StorageError"]
