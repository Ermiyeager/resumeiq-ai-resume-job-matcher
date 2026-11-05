import { useRef, useState } from "react";
import { FileText, Upload, X } from "lucide-react";
import { samples, type SampleName } from "../samples";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED = [".pdf", ".docx", ".txt"];

interface Props {
  busy: boolean;
  onSubmit: (input: { jobText: string; resumeText: string; resumeFile: File | null }) => void;
}

export default function InputPanel({ busy, onSubmit }: Props) {
  const [resumeText, setResumeText] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobText, setJobText] = useState("");
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  function pickFile(file: File | undefined) {
    if (!file) return;
    const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
    if (!ACCEPTED.includes(ext)) return setFileError("Choose a PDF, DOCX or TXT file.");
    if (file.size > MAX_BYTES) return setFileError("This file is larger than 10 MB.");
    setFileError(null);
    setResumeFile(file);
  }

  function loadSample(name: SampleName) {
    setResumeFile(null);
    setResumeText(samples[name].resume);
    setJobText(samples[name].job);
  }

  const hasResume = resumeFile !== null || resumeText.trim().length >= 50;
  const hasJob = jobText.trim().length >= 30;

  return (
    <form
      className="grid gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (hasResume && hasJob) onSubmit({ jobText, resumeText, resumeFile });
      }}
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="flex flex-col rounded-lg border border-line bg-surface p-4">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <h2 className="text-base font-semibold">Your resume</h2>
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium text-brand hover:bg-brand-soft"
              onClick={() => fileInput.current?.click()}
            >
              <Upload size={15} aria-hidden /> Upload a file
            </button>
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPTED.join(",")}
              className="sr-only"
              aria-label="Upload resume file"
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
          </div>

          {resumeFile ? (
            <div className="flex flex-1 items-center justify-between gap-3 rounded-md bg-sunken px-3 py-3">
              <span className="flex min-w-0 items-center gap-2 text-sm">
                <FileText size={18} className="shrink-0 text-muted" aria-hidden />
                <span className="truncate">{resumeFile.name}</span>
                <span className="shrink-0 text-muted">{(resumeFile.size / 1024).toFixed(0)} KB</span>
              </span>
              <button
                type="button"
                className="rounded p-1 text-muted hover:text-ink"
                aria-label="Remove file"
                onClick={() => {
                  setResumeFile(null);
                  if (fileInput.current) fileInput.current.value = "";
                }}
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <textarea
              aria-label="Resume text"
              className="min-h-64 flex-1 resize-y rounded-md border border-line bg-page p-3 text-sm leading-relaxed placeholder:text-muted"
              placeholder="Paste your resume here, or upload a PDF, DOCX or TXT file (10 MB max)."
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                pickFile(e.dataTransfer.files[0]);
              }}
            />
          )}
          {fileError && <p className="mt-2 text-sm text-bad" role="alert">{fileError}</p>}
        </section>

        <section className="flex flex-col rounded-lg border border-line bg-surface p-4">
          <h2 className="mb-3 text-base font-semibold">Job description</h2>
          <textarea
            aria-label="Job description"
            className="min-h-64 flex-1 resize-y rounded-md border border-line bg-page p-3 text-sm leading-relaxed placeholder:text-muted"
            placeholder="Paste the full job post, including requirements and responsibilities."
            value={jobText}
            onChange={(e) => setJobText(e.target.value)}
          />
        </section>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Try a sample:{" "}
          {(Object.keys(samples) as SampleName[]).map((name, i) => (
            <span key={name}>
              {i > 0 && ", "}
              <button type="button" className="font-medium text-brand underline-offset-2 hover:underline" onClick={() => loadSample(name)}>
                {name.toLowerCase()}
              </button>
            </span>
          ))}
        </p>
        <button
          type="submit"
          disabled={busy || !hasResume || !hasJob}
          className="rounded-md bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 dark:text-page"
        >
          {busy ? "Analyzing…" : "Analyze job fit"}
        </button>
      </div>
    </form>
  );
}
