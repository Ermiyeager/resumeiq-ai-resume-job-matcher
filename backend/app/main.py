"""ResumeIQ API.

Two ways to analyze:
- Guest: POST /analyses/guest is stateless. Files are read in memory and discarded.
- Registered: resumes and jobs are saved, analyses run in the background and are kept as history.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db as database
from .engine.analyzer import analyze_parsed
from .engine.extraction import MAX_FILE_BYTES, DocumentError, extract
from .engine.job_parser import parse_job
from .engine.models import AnalysisReport, ParsedJob
from .engine.resume_parser import parse_resume
from .engine.similarity import get_backend
from .routers import analyses, auth, jobs, resumes
from .security import CSRF_HEADER, CSRF_VALUE
from .settings import settings

API = "/api/v1"
MAX_JOB_CHARS = 30_000
MAX_RESUME_CHARS = 60_000
RATE_LIMIT = int(os.getenv("RESUMEIQ_RATE_LIMIT", "60"))  # write requests per minute per client
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if database.engine is None:  # tests install their own engine first
        database.init_engine()
    if settings.auto_create_tables:  # dev convenience; use `alembic upgrade head` otherwise
        from . import db_models  # noqa: F401

        database.Base.metadata.create_all(database.engine)
    yield


app = FastAPI(
    title="ResumeIQ API",
    version="0.2.0",
    description="Explainable resume and job-description matching. Scores are estimates, not hiring decisions.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("RESUMEIQ_CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", CSRF_HEADER],
)

# ------------------------------------------------------------------ middleware

_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """Cross-site forms can't set custom headers, so requiring one blocks CSRF."""
    if request.method in UNSAFE_METHODS and request.url.path.startswith(API):
        if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            return JSONResponse(status_code=403, content={"code": "CSRF_HEADER_MISSING",
                                                          "message": f"Send the {CSRF_HEADER} header."})
    return await call_next(request)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Simple in-memory sliding-window limit. Replace with Redis when running more than one worker."""
    if request.url.path.startswith(API) and request.method in UNSAFE_METHODS:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = _hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= RATE_LIMIT:
            return JSONResponse(status_code=429, content={"code": "RATE_LIMITED",
                                                          "message": "Too many requests. Try again in a minute."})
        window.append(now)
    return await call_next(request)


@app.exception_handler(DocumentError)
async def document_error_handler(_: Request, exc: DocumentError):
    status = 413 if exc.code == "FILE_TOO_LARGE" else 415 if exc.code in {"UNSUPPORTED_TYPE", "TYPE_MISMATCH"} else 422
    return JSONResponse(status_code=status, content={"code": exc.code, "message": exc.message})


# ---------------------------------------------------------------------- models


class JobText(BaseModel):
    text: str = Field(min_length=30, max_length=MAX_JOB_CHARS, description="The full job description.")


class Health(BaseModel):
    status: str
    similarity_backend: str


class ParsedResumeOut(BaseModel):
    sections: list[str]
    contact: dict[str, bool]
    skills: list[dict]
    education: list[dict]
    experience_years: float | None
    warnings: list[str]
    text: str


# ------------------------------------------------------------------- helpers


def _read_upload(upload: UploadFile) -> tuple[str, str, dict]:
    data = upload.file.read(MAX_FILE_BYTES + 1)
    doc = extract(upload.filename or "", data)
    return doc.text[:MAX_RESUME_CHARS], doc.file_type, doc.layout_signals


def _job(text: str) -> ParsedJob:
    try:
        return parse_job(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_JOB", "message": str(exc)}) from exc


# ------------------------------------------------------------------ endpoints


@app.get(f"{API}/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", similarity_backend=get_backend().name)


@app.post(f"{API}/resumes/parse", response_model=ParsedResumeOut)
def parse_resume_endpoint(file: UploadFile = File(...)) -> ParsedResumeOut:
    """Extract and structure a resume so the user can review what was read."""
    text, _, _ = _read_upload(file)
    resume = parse_resume(text)
    return ParsedResumeOut(
        sections=[s for s in resume.sections if s != "header"],
        contact={k: bool(v) for k, v in resume.contact.items()},
        skills=[{"name": s.name, "category": s.category, "explicit": s.explicit, "weak_only": s.only_weak}
                for s in resume.skills],
        education=[asdict(e) for e in resume.education],
        experience_years=round(resume.experience_months / 12, 1) if resume.experience_months else None,
        warnings=resume.warnings,
        text=text,
    )


@app.post(f"{API}/jobs/parse", response_model=ParsedJob)
def parse_job_endpoint(body: JobText) -> ParsedJob:
    """Identify the job's requirements, their type and importance."""
    return _job(body.text)


@app.post(f"{API}/analyses/guest", response_model=AnalysisReport, tags=["guest"])
def guest_analysis(
    job_text: str = Form(..., min_length=30, max_length=MAX_JOB_CHARS),
    resume_text: str | None = Form(None, max_length=MAX_RESUME_CHARS),
    resume_file: UploadFile | None = File(None),
) -> AnalysisReport:
    """Guest mode: compare a resume (file or pasted text) with a job description. Nothing is saved."""
    file_type, layout = None, None
    if resume_file is not None and resume_file.filename:
        text, file_type, layout = _read_upload(resume_file)
    elif resume_text and len(resume_text.strip()) >= 50:
        text = resume_text
    else:
        raise HTTPException(status_code=422, detail={"code": "MISSING_RESUME",
                                                     "message": "Upload a resume or paste at least a few lines."})
    resume = parse_resume(text)
    job = _job(job_text)
    return analyze_parsed(resume, job, file_type=file_type, layout=layout)


for router in (auth.router, auth.account, resumes.router, jobs.router, analyses.router):
    app.include_router(router, prefix=API)
