from datetime import date
from pathlib import Path

import pytest

from app.engine.similarity import TfidfBackend, TokenOverlapBackend

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 5)


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def backend():
    """Tests use the lexical backend so results are deterministic and need no model download."""
    try:
        import sklearn  # noqa: F401

        return TfidfBackend()
    except ImportError:  # pragma: no cover
        return TokenOverlapBackend()


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    """Factory for API clients sharing one fresh in-memory database.

    Each client has its own cookie jar, so two clients act as two different users.
    Analyses run inline so tests can read results immediately.
    """
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("argon2")
    pytest.importorskip("multipart")
    import dataclasses

    from fastapi.testclient import TestClient

    from app import db, db_models, main, tasks
    from app.mailer import ConsoleMailer, set_mailer
    from app.storage import LocalStorage, set_storage

    db.init_engine("sqlite+pysqlite:///:memory:")
    db.Base.metadata.create_all(db.engine)
    monkeypatch.setattr(tasks, "settings", dataclasses.replace(tasks.settings, task_mode="inline"))
    monkeypatch.setattr(main, "RATE_LIMIT", 100_000)
    storage = LocalStorage(tmp_path / "storage")
    set_storage(storage)
    mailer = ConsoleMailer()
    set_mailer(mailer)

    def make():
        client = TestClient(main.app, headers={"X-Requested-With": "ResumeIQ"})
        client.storage = storage
        client.mailer = mailer
        return client

    yield make
    db.Base.metadata.drop_all(db.engine)
    _ = db_models  # keep the import: it registers the tables
