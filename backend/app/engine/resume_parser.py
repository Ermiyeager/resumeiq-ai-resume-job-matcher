"""Turn resume text into a structured ParsedResume."""

from __future__ import annotations

import re
from datetime import date

from .keywords import find_skills, implied_by, is_weak_context
from .models import EducationEntry, ExtractedSkill, ParsedResume, SkillOccurrence
from .sections import RESUME_HEADINGS, merge_sections, split_sections
from .skills_dictionary import SKILLS_BY_NAME
from .text import normalize, sentences

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]?\d{3,4}[\s.-]?\d{3,4}")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w-]+", re.I)
# Text that addresses an AI/ATS instead of a human reader. It is kept as data,
# excluded from skill evidence, and reported to the user.
INJECTION_RE = re.compile(
    r"(ignore (all |any )?(the )?(previous|prior|above) instructions|disregard (all |the )?(previous|prior|above)|"
    r"you are (now )?(an? |the )?(ai|assistant|bot|scoring|language model)|system prompt|"
    r"(report|give|assign|rate)( this| the)?( candidate| resume)? (a )?100 ?%|"
    r"(chatgpt|claude|gpt|llm|ai model|ats)[,:]? (please )?(rank|score|select|recommend))",
    re.I,
)

# ------------------------------------------------------------------ degrees

DEGREE_PATTERNS: list[tuple[int, str, re.Pattern]] = [
    (4, "Doctorate", re.compile(r"\b(ph\.?\s?d|doctorate|doctoral|d\.phil)\b")),
    (3, "Master's", re.compile(r"\b(master'?s?|m\.?b\.?a|msc|m\.sc|m\.s\.|m\.a\.|meng)\b")),
    (2, "Bachelor's", re.compile(r"\b(bachelor'?s?|b\.?sc|bsc|b\.s\.|b\.a\.|beng|undergraduate degree|"
                                 r"four-year degree|4-year degree)\b")),
    (1, "Associate", re.compile(r"\b(associate'?s? degree|associate of|a\.a\.s?\.?)\b")),
]
FIELD_RE = re.compile(
    r"(?:degree|bachelor'?s?|master'?s?|b\.?sc|bsc|msc|ph\.?d|science|arts|associate'?s?)"
    r"(?: degree)?\s+(?:of science |of arts )?in\s+([a-z][a-z &/,-]{2,60}?)"
    r"(?=\s+(?:or|and|from|at|with|\d)\b|[.;,(\n|]|$)"
)
IN_PROGRESS_RE = re.compile(r"\b(expected|in progress|anticipated|candidate|currently pursuing|"
                            r"currently studying|pursuing|ongoing|present)\b")

# -------------------------------------------------------------------- dates

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MONTH_WORD = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|" \
              r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE = rf"(?:{_MONTH_WORD}\.?\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
RANGE_RE = re.compile(rf"({_DATE})\s*(?:-|to|until|through)\s*({_DATE}|present|current|now|today)")


def _parse_date(token: str, today: date, is_end: bool) -> tuple[int, int] | None:
    token = token.strip().rstrip(".")
    if token in {"present", "current", "now", "today"}:
        return today.year, today.month
    m = re.match(rf"({_MONTH_WORD})\.?\s+(\d{{4}})", token)
    if m:
        return int(m.group(2)), _MONTHS[m.group(1)[:3]]
    m = re.match(r"(\d{1,2})/(\d{4})", token)
    if m and 1 <= int(m.group(1)) <= 12:
        return int(m.group(2)), int(m.group(1))
    m = re.match(r"(\d{4})$", token)
    if m:
        return int(m.group(1)), (12 if is_end else 1)
    return None


def experience_months(text: str, today: date) -> tuple[int | None, list[str]]:
    """Total months covered by date ranges, with overlapping jobs merged."""
    intervals: list[tuple[int, int]] = []
    found: list[str] = []
    for m in RANGE_RE.finditer(normalize(text)):
        start = _parse_date(m.group(1), today, False)
        end = _parse_date(m.group(2), today, True)
        if not start or not end:
            continue
        s = start[0] * 12 + start[1] - 1
        e = end[0] * 12 + end[1] - 1
        if not (1950 <= start[0] <= today.year + 1) or e < s:
            continue
        e = min(e, today.year * 12 + today.month - 1)
        intervals.append((s, e))
        found.append(m.group(0))
    if not intervals:
        return None, []
    intervals.sort()
    total = 0
    cur_s, cur_e = intervals[0]
    for s, e in intervals[1:]:
        if s <= cur_e + 1:
            cur_e = max(cur_e, e)
        else:
            total += cur_e - cur_s + 1
            cur_s, cur_e = s, e
    total += cur_e - cur_s + 1
    return total, found


def parse_education(text: str) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    for line in sentences(text):
        low = normalize(line)
        for level, name, pattern in DEGREE_PATTERNS:
            if pattern.search(low):
                fm = FIELD_RE.search(low)
                entries.append(EducationEntry(
                    level=level,
                    level_name=name,
                    field=fm.group(1).strip(" ,") if fm else None,
                    in_progress=bool(IN_PROGRESS_RE.search(low)),
                    evidence=line,
                ))
                break
    return entries


def parse_resume(text: str, today: date | None = None) -> ParsedResume:
    today = today or date.today()
    parts = split_sections(text, RESUME_HEADINGS, first_section="header")
    sections = merge_sections(parts)
    warnings: list[str] = []

    contact = {
        "email": _first(EMAIL_RE, text),
        "phone": _first(PHONE_RE, sections.get("header", text[:600])),
        "linkedin": _first(LINKEDIN_RE, text),
    }

    # ---- skills, per section so evidence knows where it came from
    by_name: dict[str, ExtractedSkill] = {}
    injection_lines: list[str] = []

    def add(name: str, occ: SkillOccurrence) -> None:
        skill = by_name.setdefault(name, ExtractedSkill(name, SKILLS_BY_NAME[name].category))
        skill.occurrences.append(occ)

    for section, body in parts:
        if section in {"references"}:
            continue
        for sent in sentences(body):
            if INJECTION_RE.search(sent):
                injection_lines.append(sent)
                continue
            weak = is_weak_context(sent, section)
            for hit in find_skills(sent):
                add(hit.skill.name, SkillOccurrence(hit.surface, sent, section, hit.explicit, weak))
                if hit.explicit and not weak:
                    for inferred in implied_by(hit.skill.name):
                        add(inferred, SkillOccurrence(hit.surface, sent, section, False, weak))

    # ---- education
    edu_text = sections.get("education") or sections.get("certifications") or ""
    education = parse_education(edu_text) if edu_text else parse_education(text)

    # ---- experience dates (only from experience-like sections when present)
    exp_text = "\n".join(sections.get(k, "") for k in ("experience", "volunteering")).strip()
    if not exp_text:
        exp_text = "\n".join(body for name, body in parts if name not in {"education", "certifications"})
        if "experience" not in sections:
            warnings.append("No work experience section heading was found.")
    months, ranges = experience_months(exp_text, today)

    if injection_lines:
        warnings.append("INSTRUCTION_TEXT: The resume contains text addressed to an AI or ATS. It was ignored.")
    if not contact["email"]:
        warnings.append("No email address was found.")

    return ParsedResume(
        text=text,
        sections=sections,
        contact=contact,
        skills=sorted(by_name.values(), key=lambda s: s.name.lower()),
        education=education,
        experience_months=months,
        experience_ranges=ranges,
        warnings=warnings,
    )


def _first(pattern: re.Pattern, text: str) -> str | None:
    m = pattern.search(text)
    return m.group(0) if m else None
