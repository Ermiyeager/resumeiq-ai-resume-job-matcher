import type { AtsCheck, MissingKeyword, Recommendation, RequirementCoverage } from "../types";
import { Pill, Quote, importanceLabel, type Tone } from "./ui";

export function GapList({ items }: { items: MissingKeyword[] }) {
  if (!items.length) return <p className="text-sm text-muted">No keyword gaps. Every job keyword has evidence in your resume.</p>;
  const related = items.filter((i) => i.gap_type === "RELATED_EXPERIENCE");
  const none = items.filter((i) => i.gap_type === "NO_EVIDENCE");
  const sections: [string, MissingKeyword[]][] = [
    ["You have related experience", related],
    ["No evidence found", none],
  ];
  return (
    <div className="grid gap-6">
      <p className="text-sm text-muted">
        Only add a skill to your resume if you actually have it. ResumeIQ can't tell whether you have a skill you
        didn't mention, so each gap below asks you to decide.
      </p>
      {sections.map(([title, list]) =>
        list.length ? (
          <section key={title}>
            <h3 className="mb-2 text-sm font-semibold">{title} ({list.length})</h3>
            <ul className="divide-y divide-line rounded-lg border border-line">
              {list.map((g) => (
                <li key={g.keyword} className="grid gap-2 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{g.keyword}</span>
                    <Pill tone={g.importance === "CRITICAL" || g.importance === "HIGH" ? "bad" : "neutral"}>
                      {importanceLabel[g.importance]}
                    </Pill>
                  </div>
                  <p className="text-sm">{g.recommended_action}</p>
                  <p className="text-xs text-muted">{g.why_it_matters}</p>
                  {g.related_evidence && <Quote label="Related line in your resume">{g.related_evidence}</Quote>}
                </li>
              ))}
            </ul>
          </section>
        ) : null,
      )}
    </div>
  );
}

const coverageTone: Record<RequirementCoverage["status"], [string, Tone]> = {
  COVERED: ["Shown", "good"],
  PARTIAL: ["Partly shown", "warn"],
  NOT_FOUND: ["Not shown", "bad"],
};

export function CoverageList({ items }: { items: RequirementCoverage[] }) {
  if (!items.length) return <p className="text-sm text-muted">The job description doesn't list separate duties.</p>;
  return (
    <ul className="divide-y divide-line rounded-lg border border-line">
      {items.map((c) => (
        <li key={c.requirement} className="grid gap-2 p-3 md:grid-cols-[1fr_auto_1fr] md:items-start md:gap-4">
          <p className="text-sm font-medium">{c.requirement}</p>
          <Pill tone={coverageTone[c.status][1]}>{coverageTone[c.status][0]}</Pill>
          <p className="text-sm text-muted">{c.resume_evidence ?? "No matching line in your resume."}</p>
        </li>
      ))}
    </ul>
  );
}

const priorityTone: Record<Recommendation["priority"], Tone> = { CRITICAL: "bad", HIGH: "warn", MEDIUM: "brand", LOW: "neutral" };

export function RecommendationList({ items }: { items: Recommendation[] }) {
  if (!items.length) return <p className="text-sm text-muted">No changes suggested for this job.</p>;
  return (
    <ol className="grid gap-3">
      {items.map((r, i) => (
        <li key={r.title + i} className="rounded-lg border border-line p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone={priorityTone[r.priority]}>{importanceLabel[r.priority]}</Pill>
            <span className="text-xs text-muted">{r.category}</span>
          </div>
          <h3 className="mt-2 font-semibold">{r.title}</h3>
          <p className="mt-1 text-sm leading-relaxed">{r.description}</p>
          {r.evidence && <div className="mt-3"><Quote label="From your resume">{r.evidence}</Quote></div>}
          <p className="mt-2 text-xs text-muted">Why: {r.why}</p>
        </li>
      ))}
    </ol>
  );
}

const atsTone: Record<AtsCheck["result"], [string, Tone]> = { PASS: ["Pass", "good"], WARNING: ["Warning", "warn"], FAIL: ["Fail", "bad"] };

export function AtsList({ items }: { items: AtsCheck[] }) {
  return (
    <div>
      <p className="mb-3 text-sm text-muted">
        A readability and formatting check, not a universal ATS score. Each ATS parses resumes differently.
      </p>
      <ul className="divide-y divide-line rounded-lg border border-line">
        {items.map((c) => (
          <li key={c.check} className="flex items-start justify-between gap-4 p-3">
            <div>
              <p className="text-sm font-medium">{c.check}</p>
              <p className="mt-0.5 text-sm text-muted">{c.detail}</p>
            </div>
            <Pill tone={atsTone[c.result][1]}>{atsTone[c.result][0]}</Pill>
          </li>
        ))}
      </ul>
    </div>
  );
}
