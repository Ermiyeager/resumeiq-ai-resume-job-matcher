import { Fragment, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { KeywordMatch, MatchType } from "../types";
import { Pill, Quote, importanceLabel, matchLabel, matchTone } from "./ui";

type Filter = "all" | "confirmed" | "review" | "missing";

const groups: Record<Exclude<Filter, "all">, MatchType[]> = {
  confirmed: ["EXACT_MATCH", "SYNONYM_MATCH"],
  review: ["PARTIAL_MATCH", "SEMANTIC_MATCH", "RELATED_SKILL", "NEEDS_VERIFICATION"],
  missing: ["MISSING"],
};

const typeLabel = { MANDATORY: "Required", PREFERRED: "Preferred", RESPONSIBILITY: "Duty", CONTEXT: "Mentioned" };

export default function KeywordTable({ matches }: { matches: KeywordMatch[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);
  const visible = filter === "all" ? matches : matches.filter((m) => groups[filter].includes(m.match_type));
  const count = (f: Filter) => (f === "all" ? matches.length : matches.filter((m) => groups[f].includes(m.match_type)).length);

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Filter keywords">
        {(["all", "confirmed", "review", "missing"] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
            className={`rounded-md border px-3 py-1 text-sm ${
              filter === f ? "border-brand bg-brand-soft font-medium text-brand" : "border-line text-muted hover:text-ink"
            }`}
          >
            {{ all: "All", confirmed: "Confirmed", review: "To review", missing: "Not found" }[f]} ({count(f)})
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full min-w-[34rem] text-sm">
          <thead className="bg-sunken text-left text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Keyword</th>
              <th className="px-3 py-2 font-medium">In the job</th>
              <th className="px-3 py-2 font-medium">Importance</th>
              <th className="px-3 py-2 font-medium">In your resume</th>
              <th className="w-8 px-3 py-2"><span className="sr-only">Evidence</span></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((m) => {
              const isOpen = open === m.keyword;
              return (
                <Fragment key={m.keyword}>
                  <tr
                    className="cursor-pointer border-t border-line hover:bg-sunken/60"
                    onClick={() => setOpen(isOpen ? null : m.keyword)}
                  >
                    <td className="px-3 py-2 font-medium">{m.keyword}</td>
                    <td className="px-3 py-2 text-muted">{typeLabel[m.requirement_type]}</td>
                    <td className="px-3 py-2 text-muted">{importanceLabel[m.importance]}</td>
                    <td className="px-3 py-2"><Pill tone={matchTone[m.match_type]}>{matchLabel[m.match_type]}</Pill></td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        aria-label={`${isOpen ? "Hide" : "Show"} evidence for ${m.keyword}`}
                        className="rounded p-0.5 text-muted"
                        onClick={(e) => {
                          e.stopPropagation();
                          setOpen(isOpen ? null : m.keyword);
                        }}
                      >
                        <ChevronDown size={16} className={isOpen ? "rotate-180 transition-transform" : "transition-transform"} />
                      </button>
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="bg-sunken/40">
                      <td colSpan={5} className="px-3 pb-4 pt-2">
                        <div className="grid gap-4 md:grid-cols-2">
                          <Quote label="Job description">{m.job_evidence}</Quote>
                          <Quote label={m.resume_section ? `Your resume, ${m.resume_section}` : "Your resume"}>
                            {m.resume_evidence ?? <span className="text-muted">Nothing found.</span>}
                          </Quote>
                        </div>
                        <p className="mt-3 text-xs text-muted">
                          {m.note} Confidence {Math.round(m.confidence * 100)}%.
                        </p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {!visible.length && (
              <tr><td colSpan={5} className="px-3 py-6 text-center text-muted">No keywords in this group.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
