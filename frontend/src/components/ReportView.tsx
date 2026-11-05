import { useState } from "react";
import type { AnalysisReport } from "../types";
import ScoreSummary from "./ScoreSummary";
import MandatoryList from "./MandatoryList";
import KeywordTable from "./KeywordTable";
import { AtsList, CoverageList, GapList, RecommendationList } from "./Details";

type Tab = "keywords" | "gaps" | "duties" | "recommendations" | "ats";

export default function ReportView({ report }: { report: AnalysisReport }) {
  const [tab, setTab] = useState<Tab>("keywords");
  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "keywords", label: "Keywords", count: report.keyword_matches.length },
    { id: "gaps", label: "Gaps", count: report.missing_keywords.length },
    { id: "duties", label: "Duties", count: report.requirement_coverage.length },
    { id: "recommendations", label: "Recommendations", count: report.recommendations.length },
    { id: "ats", label: "ATS readability" },
  ];

  return (
    <div className="grid gap-5">
      <ScoreSummary report={report} />
      <MandatoryList items={report.mandatory_requirements} />

      <section className="rounded-lg border border-line bg-surface p-5">
        <div role="tablist" aria-label="Report details" className="-mx-1 mb-5 flex gap-1 overflow-x-auto border-b border-line">
          {tabs.map((t) => (
            <button
              key={t.id}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm ${
                tab === t.id ? "border-brand font-semibold text-ink" : "border-transparent text-muted hover:text-ink"
              }`}
            >
              {t.label}
              {t.count !== undefined && <span className="ml-1.5 text-muted">{t.count}</span>}
            </button>
          ))}
        </div>
        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {tab === "keywords" && <KeywordTable matches={report.keyword_matches} />}
          {tab === "gaps" && <GapList items={report.missing_keywords} />}
          {tab === "duties" && <CoverageList items={report.requirement_coverage} />}
          {tab === "recommendations" && <RecommendationList items={report.recommendations} />}
          {tab === "ats" && <AtsList items={report.ats_checks} />}
        </div>
      </section>

      <p className="text-xs leading-relaxed text-muted">
        {report.disclaimer} Similarity method: {report.similarity_backend}.
      </p>
    </div>
  );
}
