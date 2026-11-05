from __future__ import annotations

import json
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..db_models import JobDescription, User, utcnow
from ..deps import current_user, get_owned
from ..engine.job_parser import parse_job
from ..schemas import JobDetailOut, JobIn, JobOut, JobUpdateIn, Message, Page
from ..settings import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse(text: str) -> dict:
    try:
        return json.loads(json.dumps(asdict(parse_job(text))))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_JOB", "message": str(exc)}) from exc


def job_out(job: JobDescription, detail: bool = False) -> JobOut:
    data = {"keyword_count": len(job.parsed.get("keywords", []))}
    model = JobDetailOut if detail else JobOut
    return model.model_validate(job).model_copy(update=data)


@router.post("", response_model=JobDetailOut, status_code=201)
def create_job(body: JobIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobOut:
    count = db.scalar(select(func.count()).select_from(JobDescription).where(
        JobDescription.user_id == user.id, JobDescription.deleted_at.is_(None)))
    if count >= settings.max_jobs_per_user:
        raise HTTPException(status_code=409, detail={"code": "LIMIT_REACHED",
                                                     "message": "You've reached the saved job limit."})
    parsed = _parse(body.description)
    job = JobDescription(user_id=user.id, description=body.description, parsed=parsed,
                         job_title=(body.job_title or parsed["title"]).strip()[:200],
                         company_name=body.company_name, category=parsed["category"])
    db.add(job)
    db.commit()
    return job_out(job, detail=True)


@router.get("", response_model=Page[JobOut])
def list_jobs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              user: User = Depends(current_user), db: Session = Depends(get_db)) -> Page[JobOut]:
    where = (JobDescription.user_id == user.id, JobDescription.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(JobDescription).where(*where)) or 0
    rows = db.scalars(select(JobDescription).where(*where).order_by(JobDescription.updated_at.desc())
                      .limit(limit).offset(offset))
    return Page(items=[job_out(j) for j in rows], total=total, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobDetailOut)
def get_job(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> JobOut:
    return job_out(get_owned(db, JobDescription, job_id, user), detail=True)


@router.put("/{job_id}", response_model=JobDetailOut)
def update_job(job_id: uuid.UUID, body: JobUpdateIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)) -> JobOut:
    job = get_owned(db, JobDescription, job_id, user)
    if body.description is not None:
        job.parsed = _parse(body.description)
        job.description = body.description
        job.category = job.parsed["category"]
    if body.job_title is not None:
        job.job_title = body.job_title.strip() or job.job_title
    if body.company_name is not None:
        job.company_name = body.company_name.strip() or None
    job.updated_at = utcnow()
    db.commit()
    return job_out(job, detail=True)


@router.delete("/{job_id}", response_model=Message)
def delete_job(job_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Message:
    job = get_owned(db, JobDescription, job_id, user)
    job.deleted_at = utcnow()
    db.commit()
    return Message(message="Job deleted.")
