import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileText, Trash2 } from "lucide-react";
import { analyses, auth, jobs, resumes, type AnalysisSummary, type Job, type Resume } from "../api";
import { useAuth } from "../auth";
import { ErrorText, errorMessage } from "../components/forms";
import { Pill } from "../components/ui";

const date = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

function Panel({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-line bg-surface p-5">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export default function DashboardPage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [resumeList, setResumes] = useState<Resume[]>([]);
  const [jobList, setJobs] = useState<Job[]>([]);
  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [r, j, a] = await Promise.all([resumes.list(), jobs.list(), analyses.list()]);
      setResumes(r.items);
      setJobs(j.items);
      setHistory(a.items);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-semibold">Your job search</h1>
        {user && !user.email_verified && (
          <p className="text-sm text-muted">
            Confirm your email from the link we sent.{" "}
            <button className="font-medium text-brand hover:underline" onClick={() => act(auth.resendVerification)}>
              Send it again
            </button>
          </p>
        )}
      </div>
      <ErrorText>{error}</ErrorText>

      <NewAnalysis resumes={resumeList} jobs={jobList} onStart={async (r, j) => {
        try {
          const a = await analyses.start(r, j);
          navigate(`/analyses/${a.id}`);
        } catch (e) {
          setError(errorMessage(e));
        }
      }} />

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title={`Resumes (${resumeList.length})`}>
          <AddResume onAdd={(fn) => act(fn)} />
          <ul className="mt-4 divide-y divide-line">
            {resumeList.map((r) => (
              <li key={r.id} className="flex items-start justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <FileText size={15} className="shrink-0 text-muted" aria-hidden />
                    <span className="truncate">{r.name}</span>
                  </p>
                  <p className="mt-0.5 text-xs text-muted">
                    Version {r.latest_version?.version_number ?? 1}, {r.latest_version?.parsed_summary.skills?.length ?? 0} skills
                    found, updated {date(r.updated_at)}
                  </p>
                </div>
                <button aria-label={`Delete ${r.name}`} className="rounded p-1 text-muted hover:text-bad"
                        onClick={() => confirm(`Delete “${r.name}”?`) && act(() => resumes.remove(r.id))}>
                  <Trash2 size={15} />
                </button>
              </li>
            ))}
            {loaded && !resumeList.length && <li className="py-3 text-sm text-muted">Add a resume to get started.</li>}
          </ul>
        </Panel>

        <Panel title={`Saved jobs (${jobList.length})`}>
          <AddJob onAdd={(text, company) => act(() => jobs.create(text, company))} />
          <ul className="mt-4 divide-y divide-line">
            {jobList.map((j) => (
              <li key={j.id} className="flex items-start justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{j.job_title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {j.company_name ? `${j.company_name}, ` : ""}{j.keyword_count} keywords, saved {date(j.created_at)}
                  </p>
                </div>
                <button aria-label={`Delete ${j.job_title}`} className="rounded p-1 text-muted hover:text-bad"
                        onClick={() => confirm(`Delete “${j.job_title}”?`) && act(() => jobs.remove(j.id))}>
                  <Trash2 size={15} />
                </button>
              </li>
            ))}
            {loaded && !jobList.length && <li className="py-3 text-sm text-muted">Paste a job post to save it.</li>}
          </ul>
        </Panel>
      </div>

      <Panel title="Analysis history">
        {history.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-sm">
              <thead className="text-left text-xs text-muted">
                <tr>
                  <th className="pb-2 font-medium">Job</th>
                  <th className="pb-2 font-medium">Resume</th>
                  <th className="pb-2 text-right font-medium">Score</th>
                  <th className="pb-2 text-right font-medium">Required gaps</th>
                  <th className="pb-2 text-right font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {history.map((a) => (
                  <tr key={a.id} className="border-t border-line">
                    <td className="py-2 pr-3">
                      <Link to={`/analyses/${a.id}`} className="font-medium text-brand hover:underline">{a.job_title ?? "Deleted job"}</Link>
                    </td>
                    <td className="py-2 pr-3 text-muted">{a.resume_name ?? "Deleted resume"} v{a.version_number}</td>
                    <td className="py-2 text-right font-medium">
                      {a.status === "COMPLETED" ? Math.round(a.overall_score ?? 0) : <Pill tone={a.status === "FAILED" ? "bad" : "neutral"}>{a.status.toLowerCase()}</Pill>}
                    </td>
                    <td className={`py-2 text-right ${a.mandatory_gaps ? "text-bad" : "text-muted"}`}>{a.mandatory_gaps ?? "—"}</td>
                    <td className="py-2 text-right text-muted">{date(a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted">{loaded ? "Your analyses will appear here." : "Loading…"}</p>
        )}
      </Panel>

      <DeleteAccount onDeleted={() => { setUser(null); navigate("/"); }} />
    </div>
  );
}

function NewAnalysis({ resumes: rs, jobs: js, onStart }: {
  resumes: Resume[]; jobs: Job[]; onStart: (resumeId: string, jobId: string) => Promise<void>;
}) {
  const [resumeId, setResumeId] = useState("");
  const [jobId, setJobId] = useState("");
  const [busy, setBusy] = useState(false);
  const r = resumeId || rs[0]?.id || "";
  const j = jobId || js[0]?.id || "";
  const select = "min-w-0 flex-1 rounded-md border border-line bg-page px-3 py-2 text-sm";

  return (
    <Panel title="New analysis">
      {rs.length && js.length ? (
        <form className="flex flex-wrap items-center gap-3" onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          await onStart(r, j);
          setBusy(false);
        }}>
          <select aria-label="Resume" className={select} value={r} onChange={(e) => setResumeId(e.target.value)}>
            {rs.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
          <span className="text-sm text-muted">against</span>
          <select aria-label="Job" className={select} value={j} onChange={(e) => setJobId(e.target.value)}>
            {js.map((x) => <option key={x.id} value={x.id}>{x.job_title}{x.company_name ? ` (${x.company_name})` : ""}</option>)}
          </select>
          <button type="submit" disabled={busy}
                  className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40 dark:text-page">
            {busy ? "Starting…" : "Analyze"}
          </button>
        </form>
      ) : (
        <p className="text-sm text-muted">Add at least one resume and one job below, then compare them here.</p>
      )}
    </Panel>
  );
}

function AddResume({ onAdd }: { onAdd: (fn: () => Promise<unknown>) => Promise<void> }) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [pasting, setPasting] = useState(false);
  const [name, setName] = useState("");
  const [text, setText] = useState("");

  const submitText = async (e: FormEvent) => {
    e.preventDefault();
    await onAdd(() => resumes.fromText(name || "Pasted resume", text));
    setText("");
    setName("");
    setPasting(false);
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-sunken" onClick={() => fileInput.current?.click()}>
          Upload PDF, DOCX or TXT
        </button>
        <button className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-sunken" onClick={() => setPasting((p) => !p)}>
          {pasting ? "Cancel" : "Paste text"}
        </button>
        <input ref={fileInput} type="file" accept=".pdf,.docx,.txt" className="sr-only" aria-label="Upload resume file"
               onChange={(e) => {
                 const file = e.target.files?.[0];
                 if (file) void onAdd(() => resumes.upload(file));
                 e.target.value = "";
               }} />
      </div>
      {pasting && (
        <form className="mt-3 grid gap-2" onSubmit={submitText}>
          <input aria-label="Resume name" placeholder="Name, e.g. Customer support CV" value={name}
                 onChange={(e) => setName(e.target.value)} className="rounded-md border border-line bg-page px-3 py-2 text-sm" />
          <textarea aria-label="Resume text" required minLength={50} rows={6} value={text} onChange={(e) => setText(e.target.value)}
                    className="rounded-md border border-line bg-page p-3 text-sm" placeholder="Paste your resume" />
          <button type="submit" className="justify-self-start rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-white dark:text-page">
            Save resume
          </button>
        </form>
      )}
    </div>
  );
}

function AddJob({ onAdd }: { onAdd: (text: string, company: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [company, setCompany] = useState("");

  if (!open) {
    return (
      <button className="rounded-md border border-line px-3 py-1.5 text-sm hover:bg-sunken" onClick={() => setOpen(true)}>
        Add a job post
      </button>
    );
  }
  return (
    <form className="grid gap-2" onSubmit={async (e) => {
      e.preventDefault();
      await onAdd(text, company);
      setText("");
      setCompany("");
      setOpen(false);
    }}>
      <input aria-label="Company" placeholder="Company (optional)" value={company} onChange={(e) => setCompany(e.target.value)}
             className="rounded-md border border-line bg-page px-3 py-2 text-sm" />
      <textarea aria-label="Job description" required minLength={30} rows={6} value={text} onChange={(e) => setText(e.target.value)}
                className="rounded-md border border-line bg-page p-3 text-sm" placeholder="Paste the full job post" />
      <div className="flex gap-2">
        <button type="submit" className="rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-white dark:text-page">Save job</button>
        <button type="button" className="rounded-md px-3 py-1.5 text-sm text-muted" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}

function DeleteAccount({ onDeleted }: { onDeleted: () => void }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  return (
    <section className="rounded-lg border border-line p-5">
      <h2 className="text-base font-semibold">Delete account</h2>
      <p className="mt-1 text-sm text-muted">Permanently deletes your account, every uploaded file, and all analyses.</p>
      {open ? (
        <form className="mt-3 flex flex-wrap items-center gap-2" onSubmit={async (e) => {
          e.preventDefault();
          try {
            await auth.deleteAccount(password);
            onDeleted();
          } catch (err) {
            setError(errorMessage(err));
          }
        }}>
          <input type="password" aria-label="Confirm password" placeholder="Your password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} className="rounded-md border border-line bg-page px-3 py-2 text-sm" />
          <button type="submit" className="rounded-md bg-bad px-3 py-2 text-sm font-semibold text-white dark:text-page">
            Delete everything
          </button>
          <ErrorText>{error}</ErrorText>
        </form>
      ) : (
        <button className="mt-3 text-sm font-medium text-bad hover:underline" onClick={() => setOpen(true)}>Delete my account</button>
      )}
    </section>
  );
}
