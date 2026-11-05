import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { runGuestAnalysis, type GuestInput } from "../api";
import type { AnalysisReport } from "../types";
import InputPanel from "../components/InputPanel";
import ReportView from "../components/ReportView";
import { errorMessage } from "../components/forms";
import { useAuth } from "../auth";

export default function GuestPage() {
  const { user } = useAuth();
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  async function submit(input: GuestInput) {
    setBusy(true);
    setError(null);
    try {
      setReport(await runGuestAnalysis(input));
      requestAnimationFrame(() => resultsRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {!user && (
        <p className="mb-4 text-sm text-muted">
          Quick check, nothing saved.{" "}
          <Link to="/register" className="font-medium text-brand hover:underline">Create an account</Link> to keep
          your resumes, compare jobs and see your history.
        </p>
      )}
      <InputPanel busy={busy} onSubmit={submit} />
      {error && (
        <p role="alert" className="mt-4 rounded-md border border-bad/40 bg-bad-soft px-4 py-3 text-sm text-bad">{error}</p>
      )}
      {report && (
        <div ref={resultsRef} className="mt-10 scroll-mt-4" aria-live="polite">
          <ReportView report={report} />
        </div>
      )}
    </>
  );
}
