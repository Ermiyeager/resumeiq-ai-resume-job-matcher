"""Data models for the ResumeIQ analysis engine.

They are plain dataclasses so the engine has no web-framework dependency.
FastAPI accepts dataclasses directly as response models, so these double
as the documented API response schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    SYNONYM_MATCH = "SYNONYM_MATCH"
    SEMANTIC_MATCH = "SEMANTIC_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    RELATED_SKILL = "RELATED_SKILL"
    MISSING = "MISSING"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


# How much each match type counts toward a score. Only exact and synonym
# matches are treated as confirmed skills.
MATCH_CREDIT: dict[MatchType, float] = {
    MatchType.EXACT_MATCH: 1.0,
    MatchType.SYNONYM_MATCH: 1.0,
    MatchType.SEMANTIC_MATCH: 0.7,
    MatchType.PARTIAL_MATCH: 0.6,
    MatchType.RELATED_SKILL: 0.35,
    MatchType.NEEDS_VERIFICATION: 0.25,
    MatchType.MISSING: 0.0,
}

CONFIRMED = {MatchType.EXACT_MATCH, MatchType.SYNONYM_MATCH}


class Importance(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


IMPORTANCE_WEIGHT = {
    Importance.CRITICAL: 4.0,
    Importance.HIGH: 3.0,
    Importance.MEDIUM: 2.0,
    Importance.LOW: 1.0,
}
IMPORTANCE_RANK = {Importance.LOW: 0, Importance.MEDIUM: 1, Importance.HIGH: 2, Importance.CRITICAL: 3}


class RequirementType(str, Enum):
    MANDATORY = "MANDATORY"
    PREFERRED = "PREFERRED"
    RESPONSIBILITY = "RESPONSIBILITY"
    CONTEXT = "CONTEXT"


# ---------------------------------------------------------------- resume side


@dataclass
class SkillOccurrence:
    surface: str          # the exact phrase found in the text
    sentence: str         # the sentence it was found in (evidence)
    section: str          # resume section, e.g. "experience"
    explicit: bool        # False when inferred (e.g. Spring Boot -> Java)
    weak_context: bool    # e.g. "currently learning Docker"


@dataclass
class ExtractedSkill:
    name: str
    category: str
    occurrences: list[SkillOccurrence] = field(default_factory=list)

    @property
    def explicit(self) -> bool:
        return any(o.explicit for o in self.occurrences)

    @property
    def only_weak(self) -> bool:
        return all(o.weak_context for o in self.occurrences)


@dataclass
class EducationEntry:
    level: int                    # 1 associate, 2 bachelor, 3 master, 4 doctorate
    level_name: str
    field: str | None
    in_progress: bool
    evidence: str


@dataclass
class ParsedResume:
    text: str
    sections: dict[str, str]
    contact: dict[str, str | None]
    skills: list[ExtractedSkill]
    education: list[EducationEntry]
    experience_months: int | None
    experience_ranges: list[str]
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------- job side


@dataclass
class JobRequirement:
    text: str
    requirement_type: RequirementType
    section: str
    skills: list[str]


@dataclass
class JobKeyword:
    name: str
    category: str
    importance: Importance
    requirement_type: RequirementType
    frequency: int
    surfaces: list[str]
    contexts: list[str]


@dataclass
class DegreeRequirement:
    level: int
    level_name: str
    field: str | None
    mandatory: bool
    allows_equivalent_experience: bool
    evidence: str


@dataclass
class ParsedJob:
    title: str
    category: str
    requirements: list[JobRequirement]
    keywords: list[JobKeyword]
    required_years: int | None
    required_years_mandatory: bool
    degree: DegreeRequirement | None


# ---------------------------------------------------------------- the report


@dataclass
class KeywordMatch:
    keyword: str
    category: str
    importance: Importance
    requirement_type: RequirementType
    match_type: MatchType
    confidence: float
    resume_evidence: str | None
    resume_section: str | None
    job_evidence: str
    note: str


@dataclass
class RequirementCoverage:
    requirement: str
    requirement_type: RequirementType
    status: str            # COVERED | PARTIAL | NOT_FOUND
    score: float           # 0-1 credit from keyword evidence or meaning-based similarity
    resume_evidence: str | None


@dataclass
class ScoreComponent:
    key: str
    label: str
    weight: float          # configured weight (0-1)
    effective_weight: float  # weight after redistributing unknown components
    score: float | None    # 0-100, None when unknown / not applicable
    status: str            # SCORED | UNKNOWN | NOT_APPLICABLE
    contribution: float    # points added to the overall score
    explanation: str


@dataclass
class MandatoryItem:
    requirement: str
    kind: str              # skill | degree | experience | certification | language
    status: str            # MET | PARTIAL | NOT_FOUND | UNKNOWN
    evidence: str | None


@dataclass
class MissingKeyword:
    keyword: str
    category: str
    importance: Importance
    requirement_type: RequirementType
    job_evidence: str
    related_evidence: str | None
    gap_type: str          # RELATED_EXPERIENCE | NO_EVIDENCE
    why_it_matters: str
    recommended_action: str


@dataclass
class AtsCheck:
    check: str
    result: str            # PASS | WARNING | FAIL
    detail: str


@dataclass
class Recommendation:
    priority: Importance
    category: str
    title: str
    description: str
    why: str
    evidence: str | None


@dataclass
class AnalysisReport:
    job_title: str
    job_category: str
    overall_score: float
    interpretation: str
    confidence: str        # High | Medium | Low
    confidence_reasons: list[str]
    components: list[ScoreComponent]
    mandatory_requirements: list[MandatoryItem]
    mandatory_gaps: int
    keyword_matches: list[KeywordMatch]
    keyword_match_rate: float
    missing_keywords: list[MissingKeyword]
    requirement_coverage: list[RequirementCoverage]
    ats_checks: list[AtsCheck]
    recommendations: list[Recommendation]
    resume_summary: dict
    similarity_backend: str
    disclaimer: str
