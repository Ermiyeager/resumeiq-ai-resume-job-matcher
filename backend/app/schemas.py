"""Request and response schemas for the stateful API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    message: str


# ------------------------------------------------------------------- auth


class RegisterIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        local, _, domain = v.partition("@")
        if not local or "." not in domain or " " in v or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Enter a valid email address.")
        return v


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=256)


class EmailIn(BaseModel):
    email: str = Field(max_length=320)


class ResetPasswordIn(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=256)


class TokenIn(BaseModel):
    token: str = Field(max_length=200)


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=256)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    email_verified: bool
    created_at: datetime


# ---------------------------------------------------------------- resumes


class ResumeTextIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=50, max_length=60_000)


class ResumeUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class VersionIn(BaseModel):
    text: str = Field(min_length=50, max_length=60_000)
    note: str | None = Field(default=None, max_length=300)


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    note: str | None
    created_at: datetime
    parsed_summary: dict


class VersionDetailOut(VersionOut):
    extracted_text: str


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    original_filename: str | None
    file_type: str
    file_size: int | None
    created_at: datetime
    updated_at: datetime
    latest_version: VersionOut | None = None


# ------------------------------------------------------------------- jobs


class JobIn(BaseModel):
    description: str = Field(min_length=30, max_length=30_000)
    job_title: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)


class JobUpdateIn(BaseModel):
    description: str | None = Field(default=None, min_length=30, max_length=30_000)
    job_title: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_title: str
    company_name: str | None
    category: str
    created_at: datetime
    updated_at: datetime
    keyword_count: int = 0


class JobDetailOut(JobOut):
    description: str
    parsed: dict


# --------------------------------------------------------------- analyses


class AnalysisIn(BaseModel):
    resume_id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    resume_id: uuid.UUID
    resume_version_id: uuid.UUID
    job_description_id: uuid.UUID
    overall_score: float | None
    mandatory_gaps: int | None
    analysis_version: str
    created_at: datetime
    completed_at: datetime | None
    resume_name: str | None = None
    job_title: str | None = None
    version_number: int | None = None


class AnalysisDetailOut(AnalysisOut):
    report: dict | None
    error_message: str | None
