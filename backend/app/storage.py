"""Private file storage for uploaded resumes.

Files get random names, live outside any public folder, and are only read
back through authorised API calls. Swap LocalStorage for an S3-compatible
implementation in production; the interface stays the same.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Protocol

from .settings import settings


class Storage(Protocol):
    def save(self, data: bytes, extension: str) -> str: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or "/" in key or "\\" in key or key.startswith("."):
            raise ValueError("Invalid storage key")
        return self.root / key

    def save(self, data: bytes, extension: str) -> str:
        key = f"{secrets.token_hex(16)}.{extension}"
        path = self._path(key)
        path.write_bytes(data)
        os.chmod(path, 0o600)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(settings.storage_dir)
    return _storage


def set_storage(storage: Storage) -> None:
    """Used by tests."""
    global _storage
    _storage = storage
