"""Rule-based recommendations.

Rules:
- Every recommendation says why it was generated and points to evidence.
- A missing skill is never suggested for the resume unless the candidate has
  it. Wording always asks the user to confirm first.
- No invented metrics, employers, titles, dates or qualifications.
"""

from __future__ import annotations

from .matcher import find_related_evidence
from .models import (
    IMPORTANCE_RANK,
    AtsCheck,
    Importance,
    KeywordMatch,
    MandatoryItem,
    MatchType,
    MissingKeyword,
    ParsedResume,
    Recommendation,
    RequirementCoverage,
    RequirementType,
)

_WHY = {
    RequirementType.MANDATORY: "It is listed as a requirement for this role.",
    RequirementType.RESPONSIBILITY: "It is part of the day-to-day work described in the job.",
    RequirementType.PREFERRED: "It is listed as preferred; it can set you apart but is not essential.",
    RequirementType.CONTEXT: "It is mentioned in the job description.",
}


def missing_keywords(matches: list[KeywordMatch], resume: ParsedResume) -> list[MissingKeyword]:
    out: list[MissingKeyword] = []
    for m in matches:
        if m.match_type not in {MatchType.MISSING, MatchType.RELATED_SKILL, MatchType.NEEDS_VERIFICATION}:
            continue
        related = m.resume_evidence if m.match_type != MatchType.MISSING else find_related_evidence(m.keyword, resume)
        if related:
            gap = "RELATED_EXPERIENCE"
            action = (f"If you have used {m.keyword}, name it in the bullet where you did that work. If you have "
                      f"not, describe the related experience accurately and do not list {m.keyword}.")
        else:
            gap = "NO_EVIDENCE"
            action = (f"If you have {m.keyword} experience that is missing from your resume, add it with "
                      f"context about where you used it. If you don't, leave it out; consider learning it if "
                      f"it appears in many jobs you want.")
        out.append(MissingKeyword(
            keyword=m.keyword,
            category=m.category,
            importance=m.importance,
            requirement_type=m.requirement_type,
            job_evidence=m.job_evidence,
            related_evidence=related,
            gap_type=gap,
            why_it_matters=_WHY[m.requirement_type],
            recommended_action=action,
        ))
    out.sort(key=lambda x: (-IMPORTANCE_RANK[x.importance], x.gap_type != "RELATED_EXPERIENCE", x.keyword))
    return out


def recommendations(matches: list[KeywordMatch], missing: list[MissingKeyword], mandatory: list[MandatoryItem],
                    coverage: list[RequirementCoverage], ats: list[AtsCheck],
                    resume: ParsedResume) -> list[Recommendation]:
    recs: list[Recommendation] = []

    for item in mandatory:
        if item.status == "NOT_FOUND":
            recs.append(Recommendation(
                Importance.CRITICAL, "Mandatory requirement",
                f"Check the requirement: {item.requirement}",
                f"The job lists {item.requirement} as required and it was not found in your resume. If you meet "
                f"it, state it clearly. If you don't, be aware this may rule out the application regardless "
                f"of the overall score.",
                "Mandatory requirements are assessed separately from the overall score.", None))
        elif item.status == "UNKNOWN":
            recs.append(Recommendation(
                Importance.HIGH, "Missing information",
                f"Add the details needed to assess: {item.requirement}",
                "The resume doesn't include enough information to check this requirement "
                "(for example, dates or degree details).",
                "Missing information is shown separately from confirmed gaps.", None))

    for m in matches:
        if m.match_type == MatchType.PARTIAL_MATCH and m.importance in {Importance.CRITICAL, Importance.HIGH}:
            recs.append(Recommendation(
                Importance.HIGH, "Use the job's terminology",
                f"Name {m.keyword} explicitly",
                f"Your resume suggests {m.keyword} but never names it. If it is accurate, use the term "
                f"\u201c{m.keyword}\u201d in the relevant bullet so recruiters and ATS see it.",
                m.note, m.resume_evidence))
        elif m.match_type == MatchType.SEMANTIC_MATCH and m.importance != Importance.LOW:
            recs.append(Recommendation(
                Importance.MEDIUM, "Highlight existing experience",
                f"Connect your experience to \u201c{m.keyword}\u201d",
                f"This sentence is close in meaning to the job's {m.keyword} requirement. If it truly reflects "
                f"that skill, consider wording it so the connection is clear.",
                "Meaning-based matches are not counted as confirmed skills.", m.resume_evidence))

    for mk in missing:
        if mk.importance in {Importance.CRITICAL, Importance.HIGH} and mk.gap_type == "RELATED_EXPERIENCE":
            recs.append(Recommendation(
                Importance.HIGH, "Highlight transferable experience",
                f"Show how your experience relates to {mk.keyword}",
                mk.recommended_action, mk.why_it_matters, mk.related_evidence))

    soft_missing = [m for m in matches if m.category == "soft_skill" and m.match_type == MatchType.MISSING
                    and m.requirement_type in {RequirementType.MANDATORY, RequirementType.RESPONSIBILITY}]
    if soft_missing:
        names = ", ".join(m.keyword.lower() for m in soft_missing)
        recs.append(Recommendation(
            Importance.MEDIUM, "Soft skills",
            "Show the soft skills this job asks for",
            f"The job asks for {names}. Your resume doesn't name these. Where they are true for you, show them "
            "through a real example in your summary or experience (for instance, how you handled a specific "
            "situation) rather than listing them as words.",
            "Recruiters look for evidence of soft skills, not just the words.", soft_missing[0].job_evidence))

    not_found = [c for c in coverage if c.status == "NOT_FOUND" and c.requirement_type == RequirementType.RESPONSIBILITY]
    if not_found:
        recs.append(Recommendation(
            Importance.MEDIUM, "Work experience",
            f"{len(not_found)} job duties aren't reflected in your resume",
            "If you have done any of these, add a bullet describing what you did, using your own real "
            "examples: " + "; ".join(c.requirement for c in not_found[:4]),
            "Recruiters look for evidence that you have done the day-to-day work.", None))

    for check in ats:
        if check.result in {"WARNING", "FAIL"} and check.check != "Relevant keywords":
            recs.append(Recommendation(
                Importance.HIGH if check.result == "FAIL" else Importance.LOW,
                "ATS readability", check.check, check.detail,
                "Formatting issues can stop an ATS from reading parts of your resume.", None))

    recs.sort(key=lambda r: -IMPORTANCE_RANK[r.priority])
    return recs
