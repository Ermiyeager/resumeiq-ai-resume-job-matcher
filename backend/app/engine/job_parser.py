"""Turn a job description into a structured ParsedJob."""

from __future__ import annotations

import re
from collections import Counter

from .keywords import find_skills
from .models import (
    IMPORTANCE_RANK,
    DegreeRequirement,
    Importance,
    JobKeyword,
    JobRequirement,
    ParsedJob,
    RequirementType,
)
from .resume_parser import DEGREE_PATTERNS, FIELD_RE
from .sections import JOB_HEADINGS, split_sections
from .skills_dictionary import QUALIFICATION_CATEGORIES, SKILLS_BY_NAME, SOFT_CATEGORY
from .text import clean_line, normalize, sentences

PREFERRED_CUES = re.compile(
    r"\b(preferred|is a plus|a plus|strong plus|plus\b|nice to have|nice-to-have|bonus|ideally|advantage|"
    r"advantageous|desirable|helpful|not required|but not required|not mandatory|is a bonus)"
)
MANDATORY_CUES = re.compile(
    r"\b(required|must|minimum|at least|essential|mandatory|need to have|you'll need|you will need|"
    r"requires|only)\b"
)
YEARS_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:(?:-|to)\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?)\b(?:'s)?(?:\s+of)?"
    r"(?:\s+[a-z/,&-]+){0,6}?\s+(?:experience|exp\b)"
)
EQUIVALENT_RE = re.compile(r"\b(or equivalent|equivalent experience|or related experience|or relevant experience)\b")
DEGREE_GENERIC = re.compile(r"\b(degree|diploma)\b")

CATEGORY_RULES: list[tuple[str, set[str]]] = [
    ("software_development", {"programming", "framework", "database", "devops", "testing", "web", "mobile"}),
    ("it_support", {"it_support", "networking"}),
    ("cybersecurity", {"security"}),
    ("data_analysis", {"data"}),
    ("sales", {"sales"}),
    ("customer_service", {"customer_service"}),
    ("marketing", {"marketing"}),
    ("human_resources", {"hr"}),
    ("finance", {"finance"}),
    ("administration", {"admin"}),
    ("project_management", {"project_management", "methodology"}),
    ("healthcare_administration", {"healthcare_admin"}),
]


def _line_type(line: str, section: str) -> RequirementType:
    low = normalize(line)
    if PREFERRED_CUES.search(low):
        return RequirementType.PREFERRED
    if section == "preferred":
        return RequirementType.PREFERRED
    if section == "requirements":
        return RequirementType.MANDATORY
    if section == "responsibilities":
        return RequirementType.RESPONSIBILITY
    if MANDATORY_CUES.search(low):
        return RequirementType.MANDATORY
    return RequirementType.CONTEXT


def _importance(category: str, req_type: RequirementType, line: str) -> Importance:
    strong = bool(MANDATORY_CUES.search(normalize(line)))
    if req_type == RequirementType.MANDATORY:
        if category in QUALIFICATION_CATEGORIES or strong:
            return Importance.CRITICAL
        return Importance.HIGH if category != SOFT_CATEGORY else Importance.MEDIUM
    if req_type == RequirementType.RESPONSIBILITY:
        return Importance.HIGH if category != SOFT_CATEGORY else Importance.MEDIUM
    if req_type == RequirementType.PREFERRED:
        return Importance.MEDIUM if category != SOFT_CATEGORY else Importance.LOW
    return Importance.LOW


_TYPE_RANK = {RequirementType.MANDATORY: 3, RequirementType.RESPONSIBILITY: 2,
              RequirementType.PREFERRED: 1, RequirementType.CONTEXT: 0}


def _title(text: str) -> str:
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            continue
        line = re.sub(r"^(job title|title|position|role)\s*:\s*", "", line, flags=re.I)
        return line[:120]
    return "Untitled job"


def _degree(reqs: list[JobRequirement]) -> DegreeRequirement | None:
    for req in reqs:
        low = normalize(req.text)
        for level, name, pattern in DEGREE_PATTERNS:
            if pattern.search(low) or (level == 2 and DEGREE_GENERIC.search(low) and "degree" in low):
                fm = FIELD_RE.search(low)
                return DegreeRequirement(
                    level=level,
                    level_name=name,
                    field=fm.group(1).strip(" ,") if fm else None,
                    mandatory=req.requirement_type == RequirementType.MANDATORY,
                    allows_equivalent_experience=bool(EQUIVALENT_RE.search(low)),
                    evidence=req.text,
                )
    return None


def parse_job(text: str) -> ParsedJob:
    if not text or len(text.strip()) < 30:
        raise ValueError("The job description is too short to analyze.")

    parts = split_sections(text, JOB_HEADINGS, first_section="intro", allow_colon=True)
    requirements: list[JobRequirement] = []
    for section, body in parts:
        for sent in sentences(body):
            if len(sent.split()) < 2:
                continue
            req_type = _line_type(sent, section)
            skills = [h.skill.name for h in find_skills(sent) if h.explicit]
            requirements.append(JobRequirement(sent, req_type, section, skills))

    # The title line itself counts as context for keyword extraction.
    title = _title(text)

    keywords: dict[str, JobKeyword] = {}
    for req in requirements:
        for hit in find_skills(req.text):
            if not hit.explicit:
                continue
            skill = hit.skill
            imp = _importance(skill.category, req.requirement_type, req.text)
            kw = keywords.get(skill.name)
            if kw is None:
                keywords[skill.name] = JobKeyword(skill.name, skill.category, imp, req.requirement_type, 1,
                                                  [hit.surface], [req.text])
                continue
            kw.frequency += 1
            if hit.surface not in kw.surfaces:
                kw.surfaces.append(hit.surface)
            if req.text not in kw.contexts:
                kw.contexts.append(req.text)
            if IMPORTANCE_RANK[imp] > IMPORTANCE_RANK[kw.importance]:
                kw.importance = imp
            if _TYPE_RANK[req.requirement_type] > _TYPE_RANK[kw.requirement_type]:
                kw.requirement_type = req.requirement_type

    # Frequently repeated context-only keywords are worth more than a passing mention.
    for kw in keywords.values():
        if kw.importance == Importance.LOW and kw.frequency >= 3:
            kw.importance = Importance.MEDIUM

    # ---- years of experience
    required_years = None
    years_mandatory = False
    for req in requirements:
        m = YEARS_RE.search(normalize(req.text))
        if m:
            required_years = int(m.group(1))
            years_mandatory = req.requirement_type == RequirementType.MANDATORY
            break

    category = _category(list(keywords.values()), title)
    return ParsedJob(
        title=title,
        category=category,
        requirements=requirements,
        keywords=sorted(keywords.values(), key=lambda k: (-IMPORTANCE_RANK[k.importance], k.name.lower())),
        required_years=required_years,
        required_years_mandatory=years_mandatory,
        degree=_degree(requirements),
    )


def _category(keywords: list[JobKeyword], title: str) -> str:
    title_low = normalize(title)
    title_hints = {
        "software_development": ("developer", "engineer", "programmer", "software"),
        "it_support": ("it support", "help desk", "helpdesk", "technician", "desktop support"),
        "cybersecurity": ("security", "soc analyst"),
        "data_analysis": ("data analyst", "data scientist", "analytics"),
        "sales": ("sales", "sdr", "appointment setter", "business development", "cold calling"),
        "customer_service": ("customer support", "customer service", "call agent", "phone support",
                             "resolutions", "call center", "support specialist"),
        "marketing": ("marketing", "seo", "content"),
        "human_resources": ("hr ", "recruiter", "human resources", "talent"),
        "finance": ("accountant", "finance", "bookkeeper", "banking"),
        "administration": ("assistant", "administrative", "admin", "office manager", "virtual assistant"),
        "project_management": ("project manager", "scrum master", "program manager"),
        "healthcare_administration": ("medical", "healthcare", "patient"),
    }
    for cat, hints in title_hints.items():
        if any(h in title_low for h in hints):
            return cat
    counts: Counter[str] = Counter()
    for kw in keywords:
        for cat, cats in CATEGORY_RULES:
            if kw.category in cats:
                counts[cat] += 1
    return counts.most_common(1)[0][0] if counts else "general"


def skill_def(name: str):
    return SKILLS_BY_NAME[name]
