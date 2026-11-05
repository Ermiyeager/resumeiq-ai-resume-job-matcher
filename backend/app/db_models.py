"""ORM models.

Conventions: UUID primary keys, UTC timestamps, soft deletion (deleted_at) for
user content, and JSON columns that become JSONB on PostgreSQL. Storage keys
for uploaded files live here but are never returned by the API.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow,
                                                 nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="USER")  # USER | ADMIN
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    preferences: Mapped[dict] = mapped_column(JSONType, default=dict)

    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan",
                                                       passive_deletes=True)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SHA-256 of the cookie value
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class AuthToken(Base):
    """Single-use tokens for email verification and password reset."""

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(30))  # verify_email | reset_password
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"
    __table_args__ = (Index("ix_resumes_user_active", "user_id", "deleted_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(10))  # pdf | docx | txt | text
    file_size: Mapped[int | None] = mapped_column(Integer)
    storage_key: Mapped[str | None] = mapped_column(String(100))  # private; never exposed
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True,
        order_by="ResumeVersion.version_number",
    )


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (UniqueConstraint("resume_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text)
    parsed_summary: Mapped[dict] = mapped_column(JSONType, default=dict)
    layout_signals: Mapped[dict] = mapped_column(JSONType, default=dict)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resume: Mapped[Resume] = relationship(back_populates="versions")


class JobDescription(TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (Index("ix_jobs_user_active", "user_id", "deleted_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_title: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict] = mapped_column(JSONType, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Analysis(Base):
    __tablename__ = "resume_analyses"
    __table_args__ = (Index("ix_analyses_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    resume_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resume_versions.id", ondelete="CASCADE"))
    job_description_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                                                          index=True)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED")  # QUEUED | PROCESSING | COMPLETED | FAILED
    analysis_version: Mapped[str] = mapped_column(String(20))
    overall_score: Mapped[float | None] = mapped_column(Float)
    skills_score: Mapped[float | None] = mapped_column(Float)
    experience_score: Mapped[float | None] = mapped_column(Float)
    education_score: Mapped[float | None] = mapped_column(Float)
    responsibilities_score: Mapped[float | None] = mapped_column(Float)
    certification_score: Mapped[float | None] = mapped_column(Float)
    soft_skills_score: Mapped[float | None] = mapped_column(Float)
    mandatory_gaps: Mapped[int | None] = mapped_column(Integer)
    report: Mapped[dict | None] = mapped_column(JSONType)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
