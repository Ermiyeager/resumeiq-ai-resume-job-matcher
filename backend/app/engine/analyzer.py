"""Orchestrates a full analysis: parse -> match -> score -> assess -> recommend."""

from __future__ import annotations

from datetime import date

from .ats import ats_checks
from .job_parser import parse_job
from .matcher import match_keywords, requirement_coverage
from .models import CONFIRMED, AnalysisReport, MatchType, ParsedJob, ParsedResume
from .recommendations import missing_keywords, recommendations
from .resume_parser import parse_resume
from .scoring import build_components, interpret, mandatory_items
from .similarity import SimilarityBackend, get_backend

DISCLAIMER = (
    "This is an explainable job-fit estimate, not a hiring decision or a prediction of ATS acceptance. "
    "Employers and ATS platforms evaluate applications differently, and a high score does not guarantee "
    "an interview."
)


def analyze(resume_text: str, job_text: str, *, file_type: str | None = None, layout: dict | None = None,
            weights: dict[str, float] | None = None, today: date | None = None,
            backend: SimilarityBackend | None = None) -> AnalysisReport:
    backend = backend or get_backend()
    resume = parse_resume(resume_text, today=today)
    job = parse_job(job_text)
    return analyze_parsed(resume, job, file_type=file_type, layout=layout, weights=weights, backend=backend)


def analyze_parsed(resume: ParsedResume, job: ParsedJob, *, file_type: str | None = None,
                   layout: dict | None = None, weights: dict[str, float] | None = None,
                   backend: SimilarityBackend | None = None) -> AnalysisReport:
    backend = backend or get_backend()
    matches = match_keywords(job, resume, backend)
    coverage = requirement_coverage(job, resume, matches, backend)
    components, overall, edu = build_components(job, resume, matches, coverage, backend, weights)
    mandatory = mandatory_items(job, resume, matches, edu)

    confirmed = sum(m.match_type in CONFIRMED for m in matches)
    match_rate = round(100.0 * confirmed / len(matches), 1) if matches else 0.0

    ats = ats_checks(resume, file_type, layout, match_rate if matches else None)
    missing = missing_keywords(matches, resume)
    recs = recommendations(matches, missing, mandatory, coverage, ats, resume)

    confidence, reasons = _confidence(resume, job, components, matches, backend)

    return AnalysisReport(
        job_title=job.title,
        job_category=job.category,
        overall_score=overall,
        interpretation=interpret(overall),
        confidence=confidence,
        confidence_reasons=reasons,
        components=components,
        mandatory_requirements=mandatory,
        mandatory_gaps=sum(i.status == "NOT_FOUND" for i in mandatory),
        keyword_matches=matches,
        keyword_match_rate=match_rate,
        missing_keywords=missing,
        requirement_coverage=coverage,
        ats_checks=ats,
        recommendations=recs,
        resume_summary={
            "sections_found": [s for s in resume.sections if s != "header"],
            "skills_found": [s.name for s in resume.skills if s.explicit],
            "experience_years": round(resume.experience_months / 12, 1) if resume.experience_months else None,
            "education": [f"{e.level_name}{' in ' + e.field if e.field else ''}"
                          f"{' (in progress)' if e.in_progress else ''}" for e in resume.education],
            "contact_found": {k: bool(v) for k, v in resume.contact.items()},
            "warnings": resume.warnings,
        },
        similarity_backend=backend.name,
        disclaimer=DISCLAIMER,
    )


def _confidence(resume, job, components, matches, backend) -> tuple[str, list[str]]:
    score = 1.0
    reasons: list[str] = []
    unknown = [c.label for c in components if c.status == "UNKNOWN"]
    if unknown:
        score -= 0.15 * len(unknown)
        reasons.append("Not enough resume information to score: " + ", ".join(unknown) + ".")
    if len(resume.text.split()) < 150:
        score -= 0.2
        reasons.append("The resume text is short, so there is little evidence to work with.")
    if len(job.keywords) < 4:
        score -= 0.2
        reasons.append("Few specific skills were identified in the job description.")
    uncertain = sum(m.match_type in {MatchType.SEMANTIC_MATCH, MatchType.NEEDS_VERIFICATION} for m in matches)
    if matches and uncertain / len(matches) > 0.3:
        score -= 0.1
        reasons.append("Many matches are meaning-based rather than confirmed.")
    if backend.name == "token-overlap":
        score -= 0.1
        reasons.append("Running with the basic similarity fallback.")
    if not reasons:
        reasons.append("Enough information was found in both documents.")
    label = "High" if score >= 0.8 else "Medium" if score >= 0.55 else "Low"
    return label, reasons
