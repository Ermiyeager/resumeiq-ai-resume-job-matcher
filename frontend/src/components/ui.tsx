import type { ReactNode } from "react";
import type { Importance, MatchType } from "../types";

export type Tone = "good" | "brand" | "warn" | "bad" | "neutral";

const toneClass: Record<Tone, string> = {
  good: "bg-good-soft text-good",
  brand: "bg-brand-soft text-brand",
  warn: "bg-warn-soft text-warn",
  bad: "bg-bad-soft text-bad",
  neutral: "bg-sunken text-muted",
};

export function Pill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${toneClass[tone]}`}>
      {children}
    </span>
  );
}

export const matchLabel: Record<MatchType, string> = {
  EXACT_MATCH: "Exact match",
  SYNONYM_MATCH: "Synonym",
  PARTIAL_MATCH: "Implied",
  SEMANTIC_MATCH: "Similar meaning",
  RELATED_SKILL: "Related skill",
  NEEDS_VERIFICATION: "Check this",
  MISSING: "Not found",
};

export const matchTone: Record<MatchType, Tone> = {
  EXACT_MATCH: "good",
  SYNONYM_MATCH: "good",
  PARTIAL_MATCH: "brand",
  SEMANTIC_MATCH: "brand",
  RELATED_SKILL: "warn",
  NEEDS_VERIFICATION: "warn",
  MISSING: "bad",
};

export const importanceLabel: Record<Importance, string> = {
  CRITICAL: "Critical",
  HIGH: "High",
  MEDIUM: "Medium",
  LOW: "Low",
};

export function Quote({ label, children }: { label: string; children: ReactNode }) {
  return (
    <figure className="min-w-0">
      <figcaption className="mb-1 text-xs font-medium text-muted">{label}</figcaption>
      <blockquote className="border-l-2 border-line pl-3 text-sm leading-relaxed">{children}</blockquote>
    </figure>
  );
}
