import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { analyses, type AnalysisDetail } from "../api";
import ReportView from "../components/ReportView";
import { ErrorText, errorMessage } from "../components/forms";

const POLL_MS = 1500;

export default function AnalysisPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const a = await analyses.get(id);
        if (cancelled) return;
        setAnalysis(a);
        if (a.status === "QUEUED" || a.status === "PROCESSING") timer = setTimeout(load, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(errorMessage(e));
      }
    };
    setAnalysis(null);
    void load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  const rerun = async () => {
    try {
      const a = await analyses.rerun(id);
      navigate(`/analyses/${a.id}`);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <Link to="/dashboard" className="text-sm text-brand hover:underline">Back to dashboard</Link>
          {analysis && (
            <p className="mt-1 text-sm text-muted">
              {analysis.resume_name ?? "Deleted resume"} (version {analysis.version_number}) against{" "}
              {analysis.job_title ?? "a deleted job"}, {new Date(analysis.created_at).toLocaleString()}
            </p>
          )}
        </div>
        {analysis && (analysis.status === "COMPLETED" || analysis.status === "FAILED") && (
          <button onClick={rerun} className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-sunken">Run again</button>
        )}
      </div>
      <ErrorText>{error}</ErrorText>
      {analysis?.status === "QUEUED" || analysis?.status === "PROCESSING" ? (
        <p className="rounded-lg border border-line bg-surface p-8 text-center text-sm text-muted" aria-live="polite">
          Analyzing your resume against the job. This usually takes a few seconds.
        </p>
      ) : null}
      {analysis?.status === "FAILED" && (
        <p role="alert" className="rounded-md border border-bad/40 bg-bad-soft px-4 py-3 text-sm text-bad">
          The analysis failed: {analysis.error_message ?? "unknown error"}. Try running it again.
        </p>
      )}
      {analysis?.status === "COMPLETED" && analysis.report && <ReportView report={analysis.report} />}
    </div>
  );
}
