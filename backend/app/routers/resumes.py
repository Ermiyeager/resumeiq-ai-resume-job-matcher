from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..db_models import Resume, ResumeVersion, User, utcnow
from ..deps import current_user, get_owned
from ..engine.extraction import MAX_FILE_BYTES, extract
from ..engine.resume_parser import parse_resume
from ..schemas import (
    Message,
    Page,
    ResumeOut,
    ResumeTextIn,
    ResumeUpdateIn,
    VersionDetailOut,
    VersionIn,
    VersionOut,
)
from ..settings import settings
from ..storage import get_storage

router = APIRouter(prefix="/resumes", tags=["resumes"])
MAX_TEXT = 60_000


def summarize(text: str) -> dict:
    """What the user sees after upload, so they can check the extraction."""
    parsed = parse_resume(text)
    return {
        "sections": [s for s in parsed.sections if s != "header"],
        "skills": [s.name for s in parsed.skills if s.explicit],
        "inferred_skills": [s.name for s in parsed.skills if not s.explicit],
        "education": [f"{e.level_name}{' in ' + e.field if e.field else ''}{' (in progress)' if e.in_progress else ''}"
                      for e in parsed.education],
        "experience_years": round(parsed.experience_months / 12, 1) if parsed.experience_months else None,
        "contact_found": {k: bool(v) for k, v in parsed.contact.items()},
        "warnings": parsed.warnings,
        "word_count": len(text.split()),
    }


def resume_out(resume: Resume) -> ResumeOut:
    out = ResumeOut.model_validate(resume)
    if resume.versions:
        out.latest_version = VersionOut.model_validate(resume.versions[-1])
    return out


def _check_quota(db: Session, user: User) -> None:
    count = db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user.id,
                                                                     Resume.deleted_at.is_(None)))
    if count >= settings.max_resumes_per_user:
        raise HTTPException(status_code=409, detail={
            "code": "LIMIT_REACHED",
            "message": f"You can keep up to {settings.max_resumes_per_user} resumes. Delete one to add another."})


def _create(db: Session, user: User, *, name: str, text: str, file_type: str, filename: str | None = None,
            size: int | None = None, storage_key: str | None = None, layout: dict | None = None) -> Resume:
    resume = Resume(user_id=user.id, name=name, original_filename=filename, file_type=file_type,
                    file_size=size, storage_key=storage_key)
    resume.versions.append(ResumeVersion(version_number=1, extracted_text=text[:MAX_TEXT],
                                         parsed_summary=summarize(text[:MAX_TEXT]), layout_signals=layout or {},
                                         note="Original upload" if filename else "Pasted text"))
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.post("/upload", response_model=ResumeOut, status_code=201)
def upload_resume(file: UploadFile = File(...), name: str | None = Form(None, max_length=200),
                  user: User = Depends(current_user), db: Session = Depends(get_db)) -> ResumeOut:
    _check_quota(db, user)
    data = file.file.read(MAX_FILE_BYTES + 1)
    doc = extract(file.filename or "", data)  # raises DocumentError -> 4xx with a code
    key = get_storage().save(data, doc.file_type)
    try:
        resume = _create(db, user, name=(name or file.filename or "Resume").strip()[:200], text=doc.text,
                         file_type=doc.file_type, filename=(file.filename or "")[:255], size=len(data),
                         storage_key=key, layout=doc.layout_signals)
    except Exception:
        get_storage().delete(key)
        raise
    return resume_out(resume)


@router.post("/text", response_model=ResumeOut, status_code=201)
def create_from_text(body: ResumeTextIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ResumeOut:
    _check_quota(db, user)
    return resume_out(_create(db, user, name=body.name.strip(), text=body.text, file_type="text"))


@router.get("", response_model=Page[ResumeOut])
def list_resumes(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: User = Depends(current_user), db: Session = Depends(get_db)) -> Page[ResumeOut]:
    where = (Resume.user_id == user.id, Resume.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(Resume).where(*where)) or 0
    rows = db.scalars(select(Resume).where(*where).order_by(Resume.updated_at.desc()).limit(limit).offset(offset))
    return Page(items=[resume_out(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> ResumeOut:
    return resume_out(get_owned(db, Resume, resume_id, user))


@router.get("/{resume_id}/parsed", response_model=VersionDetailOut)
def parsed_resume(resume_id: uuid.UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> VersionDetailOut:
    """Latest version's text and extracted information, for the user to review."""
    resume = get_owned(db, Resume, resume_id, user)
    return VersionDetailOut.model_validate(resume.versions[-1])


@router.put("/{resume_id}", response_model=ResumeOut)
def rename_resume(resume_id: uuid.UUID, body: ResumeUpdateIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> ResumeOut:
    resume = get_owned(db, Resume, resume_id, user)
    resume.name = body.name.strip()
    db.commit()
    return resume_out(resume)


@router.delete("/{resume_id}", response_model=Message)
def delete_resume(resume_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Message:
    """Soft-deletes the record (history keeps its scores) and removes the stored file right away."""
    resume = get_owned(db, Resume, resume_id, user)
    if resume.storage_key:
        get_storage().delete(resume.storage_key)
        resume.storage_key = None
    resume.deleted_at = utcnow()
    db.commit()
    return Message(message="Resume deleted.")


@router.get("/{resume_id}/versions", response_model=list[VersionOut])
def list_versions(resume_id: uuid.UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db)) -> list[VersionOut]:
    resume = get_owned(db, Resume, resume_id, user)
    return [VersionOut.model_validate(v) for v in reversed(resume.versions)]


@router.get("/{resume_id}/versions/{version_id}", response_model=VersionDetailOut)
def get_version(resume_id: uuid.UUID, version_id: uuid.UUID, user: User = Depends(current_user),
                db: Session = Depends(get_db)) -> VersionDetailOut:
    resume = get_owned(db, Resume, resume_id, user)
    version = next((v for v in resume.versions if v.id == version_id), None)
    if version is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not found."})
    return VersionDetailOut.model_validate(version)


@router.post("/{resume_id}/versions", response_model=VersionOut, status_code=201)
def create_version(resume_id: uuid.UUID, body: VersionIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)) -> VersionOut:
    """Save edited resume text as a new version. Earlier versions are kept unchanged."""
    resume = get_owned(db, Resume, resume_id, user)
    number = (resume.versions[-1].version_number if resume.versions else 0) + 1
    version = ResumeVersion(version_number=number, extracted_text=body.text, parsed_summary=summarize(body.text),
                            layout_signals={}, note=body.note)
    resume.versions.append(version)
    resume.updated_at = utcnow()
    db.commit()
    return VersionOut.model_validate(version)
