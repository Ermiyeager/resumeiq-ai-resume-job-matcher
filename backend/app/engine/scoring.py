"""Explainable job-fit scoring.

    S = sum(w_i * s_i)

over the components that could be scored. Unknown components (missing
resume data) and not-applicable ones (nothing required) are excluded and the
remaining weights rescaled, so missing information is never silently counted
as a mismatch. Mandatory requirements are assessed separately so a high
overall score cannot hide a missing licence or degree.
"""

from __future__ import annotations

import re

from ..config import COMPONENT_LABELS, weights_for
from .models import (
    CONFIRMED,
    IMPORTANCE_WEIGHT,
    MATCH_CREDIT,
    KeywordMatch,
    MandatoryItem,
    MatchType,
    ParsedJob,
    ParsedResume,
    RequirementCoverage,
    RequirementType,
    ScoreComponent,
)
from .similarity import SimilarityBackend
from .skills_dictionary import QUALIFICATION_CATEGORIES, SOFT_CATEGORY
from .text import normalize

FIELD_GROUPS = [
    {"computer science", "software engineering", "computer engineering", "information technology",
     "information systems", "data science", "computing", "mathematics", "statistics", "engineering"},
    {"business", "business administration", "marketing", "finance", "economics", "accounting",
     "management", "commerce", "communications"},
    {"nursing", "health administration", "healthcare administration", "public health", "health sciences",
     "medicine", "biology"},
    {"psychology", "human resources", "sociology", "communications"},
]

INTERPRETATION = [
    (90, "Excellent alignment"),
    (80, "Strong alignment"),
    (70, "Good alignment"),
    (60, "Moderate alignment"),
    (40, "Low alignment"),
    (0, "Limited alignment"),
]


def interpret(score: float) -> str:
    for floor, label in INTERPRETATION:
        if score >= floor:
            return label
    return INTERPRETATION[-1][1]


def _keyword_score(matches: list[KeywordMatch]) -> float | None:
    if not matches:
        return None
    total = sum(IMPORTANCE_WEIGHT[m.importance] for m in matches)
    got = sum(IMPORTANCE_WEIGHT[m.importance] * MATCH_CREDIT[m.match_type] for m in matches)
    return 100.0 * got / total


def _fields_related(required: str | None, have: str | None) -> bool | None:
    if not required:
        return True
    if not have:
        return None
    r, h = normalize(required), normalize(have)
    if r in h or h in r:
        return True
    if "related" in r:
        r = r.replace("or related field", "").replace("related field", "").strip()
    for group in FIELD_GROUPS:
        if any(g in r for g in group) and any(g in h for g in group):
            return True
    rt = set(re.findall(r"[a-z]{4,}", r)) - {"field", "related", "degree"}
    return bool(rt & set(re.findall(r"[a-z]{4,}", h)))


def education_assessment(job: ParsedJob, resume: ParsedResume) -> tuple[float | None, str, str, str | None]:
    """(score, status, explanation, evidence). status: SCORED | UNKNOWN | NOT_APPLICABLE."""
    req = job.degree
    if req is None:
        return None, "NOT_APPLICABLE", "The job does not state an education requirement.", None
    if not resume.education:
        if req.allows_equivalent_experience:
            return None, "UNKNOWN", ("No degree was found in the resume. The job accepts equivalent "
                                     "experience, which is assessed under work experience."), None
        return None, "UNKNOWN", "No education details were found in the resume.", None

    best = max(resume.education, key=lambda e: (not e.in_progress, e.level))
    completed = [e for e in resume.education if not e.in_progress]
    top_completed = max((e.level for e in completed), default=0)
    field_ok = _fields_related(req.field, best.field)

    if top_completed >= req.level:
        score = 100.0 if field_ok is not False else 70.0
        why = f"You have a completed {best.level_name} degree"
        why += "" if field_ok is not False else f", but in a different field than {req.field}"
        return score, "SCORED", why + ".", best.evidence
    in_progress = [e for e in resume.education if e.in_progress and e.level >= req.level]
    if in_progress:
        return 60.0, "SCORED", (f"Your {in_progress[0].level_name} degree is still in progress; the job asks for "
                                f"a completed {req.level_name} degree."), in_progress[0].evidence
    if req.allows_equivalent_experience:
        return 50.0, "SCORED", ("Your highest completed degree is below the requirement, but the job accepts "
                                "equivalent experience."), best.evidence
    return 25.0, "SCORED", f"The job asks for a {req.level_name} degree; a lower level was found.", best.evidence


def experience_assessment(job: ParsedJob, resume: ParsedResume, coverage: list[RequirementCoverage],
                          backend: SimilarityBackend) -> tuple[float | None, str, str]:
    parts: list[float] = []
    notes: list[str] = []

    years = resume.experience_months / 12 if resume.experience_months else None
    if job.required_years:
        if years is None:
            notes.append(f"The job asks for {job.required_years}+ years; no employment dates were found.")
        else:
            parts.append(min(1.0, years / job.required_years) * 100)
            notes.append(f"About {years:.1f} years found against {job.required_years}+ required.")
    elif years is not None:
        notes.append(f"About {years:.1f} years of dated experience found.")

    exp_text = resume.sections.get("experience") or resume.sections.get("projects")
    if exp_text:
        lines = [ln for ln in exp_text.splitlines() if ln.strip()][:60]
        row = backend.matrix([job.title], lines)[0] if lines else [0.0]
        title_sim = max(row) if row else 0.0
        resp_items = [c for c in coverage if c.requirement_type == RequirementType.RESPONSIBILITY]
        resp = (sum(c.score for c in resp_items) / len(resp_items)) if resp_items else None
        relevance = 1.0 if title_sim >= backend.strong else 0.6 if title_sim >= backend.weak else 0.3
        if resp is not None:
            relevance = max(relevance, resp)
        parts.append(relevance * 100)
        notes.append("Role relevance is based on how closely your experience matches the job title and duties.")
    if not parts:
        return None, "UNKNOWN", " ".join(notes) or "No work experience details were found."
    return sum(parts) / len(parts), "SCORED", " ".join(notes)


def mandatory_items(job: ParsedJob, resume: ParsedResume, matches: list[KeywordMatch],
                    edu: tuple) -> list[MandatoryItem]:
    items: list[MandatoryItem] = []
    resume_is_english = _looks_english(resume.text)
    for m in matches:
        if m.requirement_type != RequirementType.MANDATORY or m.category == SOFT_CATEGORY:
            continue
        kind = "certification" if m.category == "certification" else \
            "language" if m.category == "language" else "skill"
        if m.match_type in CONFIRMED:
            status = "MET"
        elif m.match_type == MatchType.MISSING:
            status = "NOT_FOUND"
            if kind == "language" and m.keyword == "English" and resume_is_english:
                status = "PARTIAL"
        else:
            status = "PARTIAL"
        evidence = m.resume_evidence
        if status == "PARTIAL" and kind == "language" and not evidence:
            evidence = "The resume is written in English, but proficiency is not stated."
        items.append(MandatoryItem(m.keyword, kind, status, evidence))

    if job.degree and job.degree.mandatory and not job.degree.allows_equivalent_experience:
        score, status, why, evidence = edu
        label = f"{job.degree.level_name} degree" + (f" in {job.degree.field}" if job.degree.field else "")
        if status == "UNKNOWN":
            items.append(MandatoryItem(label, "degree", "UNKNOWN", None))
        else:
            st = "MET" if score >= 100 else "PARTIAL" if score >= 60 else "NOT_FOUND"
            items.append(MandatoryItem(label, "degree", st, evidence or why))

    if job.required_years and job.required_years_mandatory:
        label = f"{job.required_years}+ years of experience"
        if resume.experience_months is None:
            items.append(MandatoryItem(label, "experience", "UNKNOWN", None))
        else:
            yrs = resume.experience_months / 12
            st = "MET" if yrs >= job.required_years else "PARTIAL" if yrs >= job.required_years * 0.6 else "NOT_FOUND"
            items.append(MandatoryItem(label, "experience", st, f"About {yrs:.1f} years of dated experience found."))
    return items


def _looks_english(text: str) -> bool:
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) < 30:
        return False
    common = {"the", "and", "with", "for", "of", "to", "in", "a"}
    return sum(w in common for w in words) / len(words) > 0.05


def build_components(job: ParsedJob, resume: ParsedResume, matches: list[KeywordMatch],
                     coverage: list[RequirementCoverage], backend: SimilarityBackend,
                     weight_override: dict[str, float] | None = None):
    weights = weights_for(job.category, weight_override)
    skills = [m for m in matches if m.category not in QUALIFICATION_CATEGORIES and m.category != SOFT_CATEGORY]
    quals = [m for m in matches if m.category in QUALIFICATION_CATEGORIES]
    soft = [m for m in matches if m.category == SOFT_CATEGORY]

    edu = education_assessment(job, resume)
    exp = experience_assessment(job, resume, coverage, backend)

    raw: dict[str, tuple[float | None, str, str]] = {}

    s = _keyword_score(skills)
    raw["skills"] = (s, "SCORED", f"{sum(m.match_type in CONFIRMED for m in skills)} of {len(skills)} "
                                  "job skills confirmed, weighted by importance.") if s is not None else \
        (None, "NOT_APPLICABLE", "No specific skills were identified in the job description.")
    raw["experience"] = exp
    raw["education"] = edu[:3]

    if coverage:
        resp = 100.0 * sum(c.score for c in coverage) / len(coverage)
        covered = sum(c.status == "COVERED" for c in coverage)
        raw["responsibilities"] = (resp, "SCORED", f"{covered} of {len(coverage)} duties and requirements "
                                                   "clearly reflected in your resume.")
    else:
        raw["responsibilities"] = (None, "NOT_APPLICABLE", "No responsibilities were listed.")

    q = _keyword_score(quals)
    if q is not None:
        # English stated implicitly by an English resume counts as partial evidence.
        if any(m.keyword == "English" and m.match_type == MatchType.MISSING for m in quals) and _looks_english(resume.text):
            fixed = [m if m.keyword != "English" else _with_type(m, MatchType.PARTIAL_MATCH) for m in quals]
            q = _keyword_score(fixed)
        raw["qualifications"] = (q, "SCORED", f"{sum(m.match_type in CONFIRMED for m in quals)} of {len(quals)} "
                                              "certifications or language requirements confirmed.")
    else:
        raw["qualifications"] = (None, "NOT_APPLICABLE", "No certifications or language requirements were found.")

    so = _keyword_score(soft)
    raw["soft_skills"] = (so, "SCORED", f"{sum(m.match_type in CONFIRMED for m in soft)} of {len(soft)} soft "
                                        "skills named in your resume.") if so is not None else \
        (None, "NOT_APPLICABLE", "No soft skills were listed.")

    overall, effective = combine({k: (sc if st == "SCORED" else None) for k, (sc, st, _) in raw.items()}, weights)
    components: list[ScoreComponent] = []
    for key in weights:
        score, status, why = raw[key]
        eff = effective[key]
        components.append(ScoreComponent(key, COMPONENT_LABELS[key], round(weights[key], 4), round(eff, 4),
                                         round(score, 1) if score is not None else None, status,
                                         round((score or 0.0) * eff, 2), why))
    return components, round(overall, 1), edu


def combine(scores: dict[str, float | None], weights: dict[str, float]) -> tuple[float, dict[str, float]]:
    """S = sum(w_i * s_i) over scored components, with weights rescaled to exclude unknown ones."""
    known = {k: v for k, v in scores.items() if v is not None}
    total_weight = sum(weights[k] for k in known)
    if total_weight == 0:
        return 0.0, {k: 0.0 for k in weights}
    effective = {k: (weights[k] / total_weight if k in known else 0.0) for k in weights}
    return sum(effective[k] * known[k] for k in known), effective


def _with_type(m: KeywordMatch, t: MatchType) -> KeywordMatch:
    from dataclasses import replace

    return replace(m, match_type=t)
