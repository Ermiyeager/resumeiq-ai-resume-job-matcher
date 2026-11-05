from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..db_models import Analysis, JobDescription, Resume, ResumeVersion, User, utcnow
from ..deps import current_user, get_owned
from ..schemas import AnalysisDetailOut, AnalysisIn, AnalysisOut, Page
from ..settings import settings
from ..tasks import ENGINE_VERSION, dispatch

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not found."})


def _labels(db: Session, a: Analysis) -> dict:
    resume = db.get(Resume, a.resume_id)
    job = db.get(JobDescription, a.job_description_id)
    version = db.get(ResumeVersion, a.resume_version_id)
    return {"resume_name": resume.name if resume else None, "job_title": job.job_title if job else None,
            "version_number": version.version_number if version else None}


def analysis_out(db: Session, a: Analysis, detail: bool = False) -> AnalysisOut:
    model = AnalysisDetailOut if detail else AnalysisOut
    return model.model_validate(a).model_copy(update=_labels(db, a))


def _owned_analysis(db: Session, analysis_id: uuid.UUID, user: User) -> Analysis:
    a = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id))
    if a is None:
        raise _not_found()
    return a


@router.post("", response_model=AnalysisOut, status_code=202)
def start_analysis(body: AnalysisIn, background: BackgroundTasks, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> AnalysisOut:
    """Queue an analysis of a saved resume (latest version unless one is given) against a saved job."""
    since = utcnow() - timedelta(days=1)
    today = db.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id == user.id,
                                                                       Analysis.created_at >= since))
    if today >= settings.max_analyses_per_day:
        raise HTTPException(status_code=429, detail={"code": "DAILY_LIMIT",
                                                     "message": "You've reached today's analysis limit."})
    resume = get_owned(db, Resume, body.resume_id, user)
    job = get_owned(db, JobDescription, body.job_id, user)
    if body.resume_version_id:
        version = next((v for v in resume.versions if v.id == body.resume_version_id), None)
        if version is None:
            raise _not_found()
    else:
        version = resume.versions[-1]

    a = Analysis(user_id=user.id, resume_id=resume.id, resume_version_id=version.id,
                 job_description_id=job.id, status="QUEUED", analysis_version=ENGINE_VERSION)
    db.add(a)
    db.commit()
    dispatch(a.id, background)
    db.refresh(a)
    return analysis_out(db, a)


@router.get("", response_model=Page[AnalysisOut])
def list_analyses(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                  resume_id: uuid.UUID | None = None, job_id: uuid.UUID | None = None,
                  user: User = Depends(current_user), db: Session = Depends(get_db)) -> Page[AnalysisOut]:
    where = [Analysis.user_id == user.id]
    if resume_id:
        where.append(Analysis.resume_id == resume_id)
    if job_id:
        where.append(Analysis.job_description_id == job_id)
    total = db.scalar(select(func.count()).select_from(Analysis).where(*where)) or 0
    rows = db.scalars(select(Analysis).where(*where).order_by(Analysis.created_at.desc()).limit(limit).offset(offset))
    return Page(items=[analysis_out(db, a) for a in rows], total=total, limit=limit, offset=offset)


@router.get("/{analysis_id}", response_model=AnalysisDetailOut)
def get_analysis(analysis_id: uuid.UUID, user: User = Depends(current_user),
                 db: Session = Depends(get_db)) -> AnalysisOut:
    return analysis_out(db, _owned_analysis(db, analysis_id, user), detail=True)


@router.post("/{analysis_id}/reanalyze", response_model=AnalysisOut, status_code=202)
def reanalyze(analysis_id: uuid.UUID, background: BackgroundTasks, user: User = Depends(current_user),
              db: Session = Depends(get_db)) -> AnalysisOut:
    """Run the same resume version and job again (for example after an engine update)."""
    old = _owned_analysis(db, analysis_id, user)
    return start_analysis(AnalysisIn(resume_id=old.resume_id, job_id=old.job_description_id,
                                     resume_version_id=old.resume_version_id), background, user, db)
