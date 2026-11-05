"""Section detection for resumes and job descriptions.

A line is treated as a heading when it is short, does not read like a
sentence, and matches a known heading phrase (or ends with a colon in job
descriptions). This works across templates because it does not depend on
fonts or positions, which are not available for TXT and DOCX input.
"""

from __future__ import annotations

import re

from .text import clean_line, normalize

RESUME_HEADINGS: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "profile", "professional profile", "about me",
                "objective", "career objective", "career summary", "overview"),
    "skills": ("skills", "technical skills", "core skills", "key skills", "core competencies",
               "competencies", "skills and abilities", "areas of expertise", "expertise", "tools",
               "technologies", "skills & tools"),
    "experience": ("experience", "work experience", "professional experience", "employment history",
                   "employment", "work history", "career history", "relevant experience",
                   "contract experience"),
    "education": ("education", "education and training", "academic background", "academic history",
                  "qualifications", "education & training"),
    "certifications": ("certifications", "certificates", "licenses", "licenses and certifications",
                       "certifications and licenses", "professional development", "training"),
    "projects": ("projects", "personal projects", "academic projects", "key projects", "portfolio"),
    "languages": ("languages", "language skills"),
    "achievements": ("achievements", "awards", "accomplishments", "honors", "awards and achievements"),
    "volunteering": ("volunteering", "volunteer experience", "volunteer work"),
    "interests": ("interests", "hobbies", "hobbies and interests", "personal interests"),
    "references": ("references",),
}

JOB_HEADINGS: dict[str, tuple[str, ...]] = {
    "preferred": ("preferred", "preferred qualifications", "nice to have", "nice-to-have", "bonus",
                  "bonus points", "pluses", "a plus", "desirable", "good to have"),
    "requirements": ("requirements", "required", "qualifications", "required qualifications",
                     "what we're looking for", "what we are looking for", "what you'll need",
                     "what you need", "who you are", "must have", "must-have", "what makes a good fit",
                     "the kind of person we want", "you should have", "about you", "skills",
                     "you'll fit well if you", "you should be able to", "minimum qualifications",
                     "key skills", "ideal candidate", "who we're looking for"),
    "responsibilities": ("responsibilities", "key responsibilities", "what you'll do", "what you will do",
                         "duties", "the role", "what the role looks like", "what you'll handle",
                         "day to day", "what the day may look like", "your role", "role overview",
                         "job duties", "you will", "in this role"),
    "other": ("about us", "about the company", "benefits", "perks", "what we offer", "what we provide",
              "how to apply", "to apply", "remote work", "remote position", "compensation", "salary",
              "summary", "who this is for", "the work style", "initial engagement", "who we're targeting",
              "how success will be measured", "location"),
}


def _heading_key(line: str) -> str:
    key = normalize(clean_line(line)).strip(" :.-")
    return re.sub(r"\s+", " ", key)


def match_heading(line: str, table: dict[str, tuple[str, ...]], allow_colon: bool = False) -> str | None:
    raw = clean_line(line)
    if not raw or len(raw.split()) > 8:
        return None
    key = _heading_key(raw)
    if not key:
        return None
    for section, phrases in table.items():
        if key in phrases:
            return section
    # Prefix match for headings like "Experience (2018 - present)" or "Skills:"
    for section, phrases in table.items():
        for phrase in phrases:
            if key.startswith(phrase + " ") and not raw.endswith("."):
                rest = key[len(phrase):].strip()
                if rest[:1] in "(|/&" or re.fullmatch(r"[\d\s\-–present()]+", rest):
                    return section
    if allow_colon and raw.endswith(":"):
        return "unknown"
    return None


def split_sections(text: str, table: dict[str, tuple[str, ...]], first_section: str,
                   allow_colon: bool = False) -> list[tuple[str, str]]:
    """Return an ordered list of (section, body_text). Repeated sections are kept separately."""
    out: list[tuple[str, list[str]]] = [(first_section, [])]
    for raw in text.splitlines():
        if not raw.strip():
            continue
        section = match_heading(raw, table, allow_colon)
        if section is not None:
            out.append((section, []))
            # "Skills: Python, Java" -> keep the inline content
            raw_clean = clean_line(raw)
            if ":" in raw_clean:
                rest = raw_clean.split(":", 1)[1].strip()
                if rest:
                    out[-1][1].append(rest)
            continue
        # Inline heading with content, e.g. "Skills: Python, Java, SQL"
        cleaned = clean_line(raw)
        if ":" in cleaned and len(cleaned.split(":", 1)[0].split()) <= 3:
            head = match_heading(cleaned.split(":", 1)[0], table)
            if head is not None:
                out.append((head, [cleaned.split(":", 1)[1].strip()]))
                continue
        out[-1][1].append(raw)
    return [(name, "\n".join(body)) for name, body in out if body or name != first_section]


def merge_sections(parts: list[tuple[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for name, body in parts:
        merged[name] = (merged.get(name, "") + "\n" + body).strip()
    return merged
