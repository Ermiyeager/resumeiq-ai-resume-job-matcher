"""Running analyses outside the request.

RESUMEIQ_TASK_MODE:
  inline      run before the response returns (tests, tiny deployments)
  background  FastAPI background task in the API process (default for local dev)
  celery      queue on Redis; a separate `celery worker` process runs it
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict

from fastapi import BackgroundTasks

from .db import SessionLocal
from .db_models import Analysis, JobDescription, ResumeVersion, utcnow
from .engine.analyzer import analyze_parsed
from .engine.job_parser import parse_job
from .engine.resume_parser import parse_resume
from .settings import settings

log = logging.getLogger("resumeiq.tasks")
ENGINE_VERSION = "engine-0.1"


def report_to_json(report) -> dict:
    """Dataclass report -> plain JSON (str enums serialise as their values)."""
    return json.loads(json.dumps(asdict(report)))


def run_analysis(analysis_id: uuid.UUID | str) -> None:
    analysis_id = uuid.UUID(str(analysis_id))
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None or analysis.status not in {"QUEUED", "FAILED"}:
            return
        analysis.status = "PROCESSING"
        db.commit()

        version = db.get(ResumeVersion, analysis.resume_version_id)
        job = db.get(JobDescription, analysis.job_description_id)
        if version is None or job is None:
            raise LookupError("The resume version or job was deleted before the analysis ran.")

        report = analyze_parsed(
            parse_resume(version.extracted_text),
            parse_job(job.description),
            file_type=version.resume.file_type if version.resume.file_type != "text" else None,
            layout=version.layout_signals or None,
        )
        scores = {c.key: c.score for c in report.components}
        analysis.overall_score = report.overall_score
        analysis.skills_score = scores.get("skills")
        analysis.experience_score = scores.get("experience")
        analysis.education_score = scores.get("education")
        analysis.responsibilities_score = scores.get("responsibilities")
        analysis.certification_score = scores.get("qualifications")
        analysis.soft_skills_score = scores.get("soft_skills")
        analysis.mandatory_gaps = report.mandatory_gaps
        analysis.report = report_to_json(report)
        analysis.error_message = None
        analysis.status = "COMPLETED"
        analysis.completed_at = utcnow()
        db.commit()
    except Exception as exc:  # record the failure; never log resume content
        db.rollback()
        log.exception("Analysis %s failed", analysis_id)
        analysis = db.get(Analysis, analysis_id)
        if analysis is not None:
            analysis.status = "FAILED"
            analysis.error_message = (str(exc) or exc.__class__.__name__)[:500]
            analysis.completed_at = utcnow()
            db.commit()
    finally:
        db.close()


def dispatch(analysis_id: uuid.UUID, background: BackgroundTasks) -> None:
    mode = settings.task_mode
    if mode == "inline":
        run_analysis(analysis_id)
    elif mode == "celery":
        from .celery_app import run_analysis_task

        run_analysis_task.delay(str(analysis_id))
    else:
        background.add_task(run_analysis, analysis_id)
