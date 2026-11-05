import type { AnalysisReport } from "../types";
import { Pill, type Tone } from "./ui";

const SHADES = [1, 0.8, 0.64, 0.5, 0.38, 0.28];

function scoreTone(score: number): Tone {
  if (score >= 80) return "good";
  if (score >= 60) return "brand";
  if (score >= 40) return "warn";
  return "bad";
}

export default function ScoreSummary({ report }: { report: AnalysisReport }) {
  const scored = report.components.filter((c) => c.status === "SCORED");
  const unearned = Math.max(0, 100 - scored.reduce((s, c) => s + c.contribution, 0));

  return (
    <section className="rounded-lg border border-line bg-surface p-5 sm:p-6" aria-labelledby="score-heading">
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
        <div>
          <h2 id="score-heading" className="text-sm font-medium text-muted">
            Job fit for {report.job_title}
          </h2>
          <p className="mt-1 flex items-baseline gap-3">
            <span className="text-6xl font-semibold tracking-tight">{Math.round(report.overall_score)}</span>
            <span className="text-lg text-muted">/ 100</span>
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm">
            <Pill tone={scoreTone(report.overall_score)}>{report.interpretation}</Pill>
            <span className="text-muted">{report.confidence} confidence</span>
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
          <dt className="text-muted">Keywords confirmed</dt>
          <dd className="text-right font-medium">{Math.round(report.keyword_match_rate)}%</dd>
          <dt className="text-muted">Required items not found</dt>
          <dd className={`text-right font-medium ${report.mandatory_gaps ? "text-bad" : ""}`}>{report.mandatory_gaps}</dd>
          <dt className="text-muted">Experience found</dt>
          <dd className="text-right font-medium">
            {report.resume_summary.experience_years != null ? `${report.resume_summary.experience_years} yrs` : "—"}
          </dd>
        </dl>
      </div>

      {/* The score, taken apart: each segment is the points a component contributed. */}
      <div className="mt-6">
        <div className="flex h-4 w-full overflow-hidden rounded-sm bg-sunken" role="img"
             aria-label={`Score breakdown: ${scored.map((c) => `${c.label} ${c.contribution.toFixed(1)} points`).join(", ")}`}>
          {scored.map((c, i) => (
            <div
              key={c.key}
              className="h-full border-r border-surface bg-brand last:border-r-0"
              style={{ width: `${c.contribution}%`, opacity: SHADES[i % SHADES.length] }}
              title={`${c.label}: ${c.contribution.toFixed(1)} points`}
            />
          ))}
          {unearned > 0 && <div className="h-full flex-1" />}
        </div>

        <table className="mt-4 w-full text-sm">
          <caption className="sr-only">How the score is calculated</caption>
          <thead className="text-left text-xs text-muted">
            <tr>
              <th className="pb-2 font-medium">Component</th>
              <th className="pb-2 text-right font-medium">Score</th>
              <th className="pb-2 text-right font-medium">Weight</th>
              <th className="pb-2 text-right font-medium">Points</th>
            </tr>
          </thead>
          <tbody>
            {report.components.map((c) => {
              const idx = scored.indexOf(c);
              return (
                <tr key={c.key} className="border-t border-line align-top">
                  <td className="py-2 pr-3">
                    <span className="flex items-center gap-2 font-medium">
                      <span
                        className={`size-2.5 shrink-0 rounded-sm ${idx >= 0 ? "bg-brand" : "border border-line"}`}
                        style={idx >= 0 ? { opacity: SHADES[idx % SHADES.length] } : undefined}
                        aria-hidden
                      />
                      {c.label}
                    </span>
                    <span className="mt-0.5 block pl-4.5 text-xs leading-snug text-muted">{c.explanation}</span>
                  </td>
                  <td className="py-2 text-right">
                    {c.status === "SCORED" ? Math.round(c.score ?? 0) : c.status === "UNKNOWN" ? "Unknown" : "n/a"}
                  </td>
                  <td className="py-2 text-right text-muted">{Math.round(c.effective_weight * 100)}%</td>
                  <td className="py-2 text-right font-medium">{c.status === "SCORED" ? c.contribution.toFixed(1) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {report.components.some((c) => c.status !== "SCORED") && (
          <p className="mt-2 text-xs text-muted">
            Components that couldn't be scored are left out and the remaining weights are scaled up, so missing
            information isn't counted as a mismatch.
          </p>
        )}
      </div>

      {report.confidence !== "High" && (
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted">
          {report.confidence_reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
      )}
    </section>
  );
}
