"""Initial schema: users, sessions, tokens, resumes, versions, jobs, analyses.

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(JSONB(), "postgresql")


def ts(name, nullable=True):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200)),
        sa.Column("role", sa.String(20), nullable=False),
        ts("email_verified_at"),
        sa.Column("preferences", JSONType, nullable=False),
        ts("created_at", False),
        ts("updated_at", False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        ts("created_at", False),
        ts("expires_at", False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        ts("expires_at", False),
        ts("used_at"),
        ts("created_at", False),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"], unique=True)

    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size", sa.Integer()),
        sa.Column("storage_key", sa.String(100)),
        ts("deleted_at"),
        ts("created_at", False),
        ts("updated_at", False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index("ix_resumes_user_active", "resumes", ["user_id", "deleted_at"])

    op.create_table(
        "resume_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("resume_id", sa.Uuid(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("parsed_summary", JSONType, nullable=False),
        sa.Column("layout_signals", JSONType, nullable=False),
        sa.Column("note", sa.String(300)),
        ts("created_at", False),
        sa.UniqueConstraint("resume_id", "version_number"),
    )
    op.create_index("ix_resume_versions_resume_id", "resume_versions", ["resume_id"])

    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_title", sa.String(200), nullable=False),
        sa.Column("company_name", sa.String(200)),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parsed", JSONType, nullable=False),
        ts("deleted_at"),
        ts("created_at", False),
        ts("updated_at", False),
    )
    op.create_index("ix_job_descriptions_user_id", "job_descriptions", ["user_id"])
    op.create_index("ix_jobs_user_active", "job_descriptions", ["user_id", "deleted_at"])

    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", sa.Uuid(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_version_id", sa.Uuid(), sa.ForeignKey("resume_versions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("job_description_id", sa.Uuid(), sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("analysis_version", sa.String(20), nullable=False),
        sa.Column("overall_score", sa.Float()),
        sa.Column("skills_score", sa.Float()),
        sa.Column("experience_score", sa.Float()),
        sa.Column("education_score", sa.Float()),
        sa.Column("responsibilities_score", sa.Float()),
        sa.Column("certification_score", sa.Float()),
        sa.Column("soft_skills_score", sa.Float()),
        sa.Column("mandatory_gaps", sa.Integer()),
        sa.Column("report", JSONType),
        sa.Column("error_message", sa.String(500)),
        ts("created_at", False),
        ts("completed_at"),
    )
    op.create_index("ix_resume_analyses_user_id", "resume_analyses", ["user_id"])
    op.create_index("ix_resume_analyses_resume_id", "resume_analyses", ["resume_id"])
    op.create_index("ix_resume_analyses_job_description_id", "resume_analyses", ["job_description_id"])
    op.create_index("ix_analyses_user_created", "resume_analyses", ["user_id", "created_at"])


def downgrade() -> None:
    for table in ("resume_analyses", "job_descriptions", "resume_versions", "resumes", "auth_tokens",
                  "user_sessions", "users"):
        op.drop_table(table)
