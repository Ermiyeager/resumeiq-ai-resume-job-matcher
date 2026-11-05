"""Runtime settings read from environment variables.

Kept dependency-free on purpose; every value has a safe development default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./resumeiq.db"))
    storage_dir: Path = field(default_factory=lambda: Path(os.getenv("RESUMEIQ_STORAGE_DIR", "./storage")))
    # inline: run analyses in the request (tests) | background: FastAPI background task | celery: Redis queue
    task_mode: str = field(default_factory=lambda: os.getenv("RESUMEIQ_TASK_MODE", "background"))
    celery_broker_url: str = field(default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    cookie_secure: bool = field(default_factory=lambda: _bool("RESUMEIQ_COOKIE_SECURE", False))
    session_days: int = field(default_factory=lambda: int(os.getenv("RESUMEIQ_SESSION_DAYS", "14")))
    app_url: str = field(default_factory=lambda: os.getenv("RESUMEIQ_APP_URL", "http://localhost:5173"))
    auto_create_tables: bool = field(default_factory=lambda: _bool("RESUMEIQ_AUTO_CREATE_TABLES", False))
    max_resumes_per_user: int = field(default_factory=lambda: int(os.getenv("RESUMEIQ_MAX_RESUMES", "25")))
    max_jobs_per_user: int = field(default_factory=lambda: int(os.getenv("RESUMEIQ_MAX_JOBS", "200")))
    max_analyses_per_day: int = field(default_factory=lambda: int(os.getenv("RESUMEIQ_MAX_ANALYSES_PER_DAY", "100")))


settings = Settings()
