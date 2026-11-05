// Mirrors the backend AnalysisReport (backend/app/engine/models.py).

export type MatchType =
  | "EXACT_MATCH"
  | "SYNONYM_MATCH"
  | "SEMANTIC_MATCH"
  | "PARTIAL_MATCH"
  | "RELATED_SKILL"
  | "MISSING"
  | "NEEDS_VERIFICATION";

export type Importance = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type RequirementType = "MANDATORY" | "PREFERRED" | "RESPONSIBILITY" | "CONTEXT";

export interface KeywordMatch {
  keyword: string;
  category: string;
  importance: Importance;
  requirement_type: RequirementType;
  match_type: MatchType;
  confidence: number;
  resume_evidence: string | null;
  resume_section: string | null;
  job_evidence: string;
  note: string;
}

export interface ScoreComponent {
  key: string;
  label: string;
  weight: number;
  effective_weight: number;
  score: number | null;
  status: "SCORED" | "UNKNOWN" | "NOT_APPLICABLE";
  contribution: number;
  explanation: string;
}

export interface MandatoryItem {
  requirement: string;
  kind: string;
  status: "MET" | "PARTIAL" | "NOT_FOUND" | "UNKNOWN";
  evidence: string | null;
}

export interface MissingKeyword {
  keyword: string;
  category: string;
  importance: Importance;
  requirement_type: RequirementType;
  job_evidence: string;
  related_evidence: string | null;
  gap_type: "RELATED_EXPERIENCE" | "NO_EVIDENCE";
  why_it_matters: string;
  recommended_action: string;
}

export interface RequirementCoverage {
  requirement: string;
  requirement_type: RequirementType;
  status: "COVERED" | "PARTIAL" | "NOT_FOUND";
  score: number;
  resume_evidence: string | null;
}

export interface AtsCheck {
  check: string;
  result: "PASS" | "WARNING" | "FAIL";
  detail: string;
}

export interface Recommendation {
  priority: Importance;
  category: string;
  title: string;
  description: string;
  why: string;
  evidence: string | null;
}

export interface AnalysisReport {
  job_title: string;
  job_category: string;
  overall_score: number;
  interpretation: string;
  confidence: "High" | "Medium" | "Low";
  confidence_reasons: string[];
  components: ScoreComponent[];
  mandatory_requirements: MandatoryItem[];
  mandatory_gaps: number;
  keyword_matches: KeywordMatch[];
  keyword_match_rate: number;
  missing_keywords: MissingKeyword[];
  requirement_coverage: RequirementCoverage[];
  ats_checks: AtsCheck[];
  recommendations: Recommendation[];
  resume_summary: {
    sections_found: string[];
    skills_found: string[];
    experience_years: number | null;
    education: string[];
    warnings: string[];
  };
  similarity_backend: string;
  disclaimer: string;
}
