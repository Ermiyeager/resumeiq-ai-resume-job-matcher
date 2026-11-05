"""ATS readability and formatting assessment.

This is NOT a universal ATS score. Applicant tracking systems parse and rank
documents differently; these checks flag common causes of parsing problems.
"""

from __future__ import annotations

import re

from .models import AtsCheck, ParsedResume
from .resume_parser import RANGE_RE
from .text import normalize

_MONTH_NAME = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\b", re.I)
_NUMERIC = re.compile(r"\b\d{1,2}/\d{4}\b")
_METRIC = re.compile(r"\d+\s*%|\$\s?\d|\b\d{2,}\b|\b\d+\s*(?:calls|customers|accounts|clients|projects|"
                     r"tickets|leads|meetings|users|people|team)\b", re.I)


def ats_checks(resume: ParsedResume, file_type: str | None, layout: dict | None,
               keyword_match_rate: float | None) -> list[AtsCheck]:
    layout = layout or {}
    checks: list[AtsCheck] = []
    text = resume.text
    sections = resume.sections

    def add(name, ok, warn_detail, pass_detail, fail=False):
        checks.append(AtsCheck(name, "PASS" if ok else ("FAIL" if fail else "WARNING"),
                               pass_detail if ok else warn_detail))

    add("Text extraction", len(text.strip()) >= 300,
        "Very little text could be read. Text inside images or graphics is invisible to most ATS.",
        f"{len(text.split())} words read from the {file_type.upper() if file_type else 'text'}.",
        fail=len(text.strip()) < 100)

    found = [s for s in ("summary", "skills", "experience", "education") if s in sections]
    add("Standard section headings", len(found) >= 3,
        "Use standard headings such as Summary, Skills, Experience and Education so ATS can find each part.",
        "Standard headings found: " + ", ".join(h.title() for h in found) + ".")

    has_email, has_phone = bool(resume.contact.get("email")), bool(resume.contact.get("phone"))
    add("Contact information", has_email and has_phone,
        "Add " + " and ".join(x for x, ok in (("an email address", has_email), ("a phone number", has_phone))
                              if not ok) + " in the main body (not in a header or footer).",
        "Email and phone number found.")

    month_style = len(_MONTH_NAME.findall(text))
    numeric_style = len(_NUMERIC.findall(text))
    if resume.experience_ranges:
        add("Consistent dates", not (month_style and numeric_style),
            "Dates mix formats (e.g. 'Jan 2020' and '01/2020'). Pick one format throughout.",
            "Date formats are consistent.")
    else:
        add("Employment dates", False, "No employment date ranges were found. Add start and end dates to each role.",
            "")

    add("Skills section", "skills" in sections,
        "Add a dedicated Skills section; many ATS look for one explicitly.", "Skills section found.")

    add("Professional summary", "summary" in sections,
        "A short summary at the top helps recruiters and ATS see your focus quickly.", "Summary found.")

    tables = layout.get("tables", 0)
    cols = layout.get("multi_column_pages", 0)
    boxes = layout.get("text_boxes", 0)
    add("Layout", not (tables or cols or boxes),
        "Tables, columns or text boxes were detected. Some ATS read these out of order; a single-column layout "
        "is safest.", "Single-column layout with no tables or text boxes detected.")

    hf = layout.get("header_footer_chars", 0)
    if file_type == "docx":
        add("Headers and footers", hf == 0,
            "Content was found in the page header or footer. Some ATS skip it, so keep contact details in the body.",
            "No content in headers or footers.")

    symbols = len(re.findall(r"[^\w\s.,;:()/&%$@+#'\"!?-]", text))
    add("Special characters", symbols / max(1, len(text)) < 0.01,
        "Many unusual symbols or icons were found. ATS may misread them; use plain characters.",
        "No excessive symbols.")

    exp = sections.get("experience", "")
    metrics = len(_METRIC.findall(RANGE_RE.sub(" ", normalize(exp)))) if exp else 0
    add("Measurable achievements", metrics >= 2,
        "Few numbers in your experience. If you have real figures (call volume, quality scores, results), add them.",
        "Your experience includes measurable results.")

    words = re.findall(r"[a-z][a-z+#.]{2,}", normalize(text))
    if words:
        from collections import Counter

        common = {"and", "the", "for", "with", "customer", "customers", "experience"}
        top = [(w, c) for w, c in Counter(words).most_common(5) if w not in common]
        stuffed = [w for w, c in top if c / len(words) > 0.04]
        add("Keyword repetition", not stuffed,
            f"'{stuffed[0] if stuffed else ''}' is repeated very often. Repetition without context can look like "
            "keyword stuffing.", "No unusual keyword repetition.")

    if any(w.startswith("INSTRUCTION_TEXT") for w in resume.warnings):
        checks.append(AtsCheck("Instruction-like text", "FAIL",
                               "The resume contains text written as instructions to an AI or ATS (for example, "
                               "\u201cignore previous instructions\u201d). It was not used as evidence. Recruiters "
                               "treat this as a red flag; remove it."))

    if keyword_match_rate is not None:
        checks.append(AtsCheck("Relevant keywords",
                               "PASS" if keyword_match_rate >= 60 else "WARNING",
                               f"{keyword_match_rate:.0f}% of this job's keywords are confirmed in your resume."))
    return checks
