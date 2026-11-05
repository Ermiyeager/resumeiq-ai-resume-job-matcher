"""Compare a parsed resume with a parsed job.

Keyword matching order (first rule that applies wins):
  1. Exact      - the resume uses the same phrasing as the job.
  2. Synonym    - the resume uses a different phrasing of the same skill.
  3. Weak only  - the skill only appears in a weak context ("learning Docker")
                  -> NEEDS_VERIFICATION.
  4. Partial    - the skill is inferred (Spring Boot -> Java) or suggested by a
                  descriptive phrase ("resolved technical problems").
  5. Related    - a related but different skill is present (MySQL for PostgreSQL).
  6. Semantic   - non-technical skills only: a resume sentence is close in
                  meaning to the job sentence -> SEMANTIC_MATCH or
                  NEEDS_VERIFICATION depending on the threshold.
  7. Missing.

Technical skills never get semantic matches: "Experience with React" and
"Experience with Flutter" look similar as sentences but are different skills.
"""

from __future__ import annotations

import re

from .keywords import find_skills
from .resume_parser import INJECTION_RE
from .models import (
    ExtractedSkill,
    JobKeyword,
    KeywordMatch,
    MatchType,
    ParsedJob,
    ParsedResume,
    RequirementCoverage,
    RequirementType,
)
from .similarity import SimilarityBackend
from .skills_dictionary import SKILLS_BY_NAME, TECHNICAL_CATEGORIES, QUALIFICATION_CATEGORIES
from .text import normalize, sentences

YEARS_RE = re.compile(r"\b\d{1,2}\s*\+?\s*(?:years?|yrs?)\b")

EVIDENCE_SECTIONS_ORDER = ["experience", "projects", "skills", "summary", "achievements", "certifications",
                           "education", "volunteering", "languages", "header", "interests"]


def resume_units(resume: ParsedResume) -> list[tuple[str, str]]:
    """(section, sentence) units used as evidence candidates."""
    units: list[tuple[str, str]] = []
    for section, body in resume.sections.items():
        if section in {"references"}:
            continue
        for sent in sentences(body):
            if len(sent.split()) >= 3 and not INJECTION_RE.search(sent):
                units.append((section, sent))
    return units


def _best_occurrence(skill: ExtractedSkill, explicit: bool, strong_only: bool = True):
    occs = [o for o in skill.occurrences if o.explicit == explicit and (not strong_only or not o.weak_context)]
    if not occs:
        return None
    rank = {s: i for i, s in enumerate(EVIDENCE_SECTIONS_ORDER)}
    return sorted(occs, key=lambda o: rank.get(o.section, 99))[0]


def match_keywords(job: ParsedJob, resume: ParsedResume, backend: SimilarityBackend) -> list[KeywordMatch]:
    skills = {s.name: s for s in resume.skills}
    units = resume_units(resume)
    results: list[KeywordMatch] = []

    # Pre-compute semantic similarity for non-technical keywords in one batch.
    semantic_kws = [kw for kw in job.keywords if kw.name not in skills
                    and kw.category not in TECHNICAL_CATEGORIES | QUALIFICATION_CATEGORIES]
    sem_scores: dict[str, tuple[float, str, str]] = {}
    if semantic_kws and units:
        queries = [kw.contexts[0] for kw in semantic_kws]
        matrix = backend.matrix(queries, [u[1] for u in units])
        for kw, row in zip(semantic_kws, matrix):
            best = max(range(len(row)), key=row.__getitem__)
            sem_scores[kw.name] = (row[best], units[best][1], units[best][0])

    for kw in job.keywords:
        results.append(_match_one(kw, skills, sem_scores, backend))
    return results


def _match_one(kw: JobKeyword, skills: dict[str, ExtractedSkill], sem_scores, backend) -> KeywordMatch:
    job_evidence = kw.contexts[0]

    def make(match_type: MatchType, confidence: float, occ=None, note: str = "", evidence=None, section=None):
        return KeywordMatch(
            keyword=kw.name,
            category=kw.category,
            importance=kw.importance,
            requirement_type=kw.requirement_type,
            match_type=match_type,
            confidence=round(confidence, 2),
            resume_evidence=occ.sentence if occ else evidence,
            resume_section=occ.section if occ else section,
            job_evidence=job_evidence,
            note=note,
        )

    skill = skills.get(kw.name)
    if skill:
        occ = _best_occurrence(skill, explicit=True)
        if occ:
            surfaces = {o.surface for o in skill.occurrences if o.explicit and not o.weak_context}
            if surfaces & set(kw.surfaces):
                return make(MatchType.EXACT_MATCH, 1.0, occ, "Same wording as the job description.")
            return make(MatchType.SYNONYM_MATCH, 0.9, occ,
                        f"Your resume says \u201c{occ.surface}\u201d; the job says \u201c{kw.surfaces[0]}\u201d.")
        weak = _best_occurrence(skill, explicit=True, strong_only=False)
        if weak and weak.weak_context:
            return make(MatchType.NEEDS_VERIFICATION, 0.4, weak,
                        "Mentioned only as something you are learning or interested in.")
        inferred = _best_occurrence(skill, explicit=False)
        if inferred:
            note = (f"Inferred from \u201c{inferred.surface}\u201d. The skill is not named directly, so "
                    "name it if you have used it.")
            return make(MatchType.PARTIAL_MATCH, 0.6, inferred, note)

    sdef = SKILLS_BY_NAME[kw.name]
    for rel_name in sdef.related:
        rel = skills.get(rel_name)
        if rel:
            occ = _best_occurrence(rel, explicit=True)
            if occ:
                return make(MatchType.RELATED_SKILL, 0.5, occ,
                            f"You have {rel_name}, which is related but not the same as {kw.name}.")
    # reverse relation (resume skill lists this keyword as related)
    for name, rel in skills.items():
        if kw.name in SKILLS_BY_NAME[name].related:
            occ = _best_occurrence(rel, explicit=True)
            if occ:
                return make(MatchType.RELATED_SKILL, 0.5, occ,
                            f"You have {name}, which is related but not the same as {kw.name}.")

    if kw.name in sem_scores:
        score, sent, section = sem_scores[kw.name]
        if score >= backend.strong:
            return make(MatchType.SEMANTIC_MATCH, min(0.85, score), None,
                        "A resume sentence is close in meaning to this requirement. Check that it really applies.",
                        sent, section)
        if score >= backend.weak:
            return make(MatchType.NEEDS_VERIFICATION, score * 0.8, None,
                        "A resume sentence may relate to this requirement. Review it before relying on it.",
                        sent, section)

    return make(MatchType.MISSING, 0.0, None, "No evidence found in the resume.")


def requirement_coverage(job: ParsedJob, resume: ParsedResume, matches: list[KeywordMatch],
                         backend: SimilarityBackend) -> list[RequirementCoverage]:
    """How well each responsibility, and each requirement with no dictionary skill, is covered."""
    handled_elsewhere = {job.degree.evidence if job.degree else None}
    targets = [r for r in job.requirements
               if r.text not in handled_elsewhere and not YEARS_RE.search(normalize(r.text))
               and (r.requirement_type == RequirementType.RESPONSIBILITY
                    or (r.requirement_type in {RequirementType.MANDATORY, RequirementType.PREFERRED}
                        and not r.skills))]
    units = [u for u in resume_units(resume) if u[0] not in {"header", "education", "languages"}]
    if not targets:
        return []
    by_kw = {m.keyword: m for m in matches}
    matrix = backend.matrix([t.text for t in targets], [u[1] for u in units]) if units else None

    out: list[RequirementCoverage] = []
    for i, req in enumerate(targets):
        best_score, best_sent = 0.0, None
        if matrix:
            row = matrix[i]
            j = max(range(len(row)), key=row.__getitem__)
            best_score, best_sent = row[j], units[j][1]
        sem_credit = 1.0 if best_score >= backend.strong else 0.5 if best_score >= backend.weak else 0.0

        kw_credit, kw_evidence = 0.0, None
        if req.skills:
            credits = []
            for name in req.skills:
                m = by_kw.get(name)
                if m and m.match_type in {MatchType.EXACT_MATCH, MatchType.SYNONYM_MATCH}:
                    credits.append(1.0)
                    kw_evidence = kw_evidence or m.resume_evidence
                elif m and m.match_type in {MatchType.PARTIAL_MATCH, MatchType.SEMANTIC_MATCH}:
                    credits.append(0.6)
                    kw_evidence = kw_evidence or m.resume_evidence
                elif m and m.match_type == MatchType.RELATED_SKILL:
                    credits.append(0.3)
                else:
                    credits.append(0.0)
            kw_credit = sum(credits) / len(credits)

        credit = max(sem_credit, kw_credit)
        status = "COVERED" if credit >= 0.8 else "PARTIAL" if credit >= 0.4 else "NOT_FOUND"
        evidence = kw_evidence if kw_credit >= sem_credit and kw_evidence else (best_sent if sem_credit else None)
        out.append(RequirementCoverage(req.text, req.requirement_type, status, round(credit, 2), evidence))
    return out


def find_related_evidence(keyword: str, resume: ParsedResume) -> str | None:
    """A resume sentence touching the same area as a missing keyword, if any."""
    sdef = SKILLS_BY_NAME[keyword]
    names = set(sdef.related) | {n for n, s in SKILLS_BY_NAME.items() if keyword in s.related}
    for section, sent in resume_units(resume):
        for hit in find_skills(sent):
            if hit.skill.name in names:
                return sent
    return None
