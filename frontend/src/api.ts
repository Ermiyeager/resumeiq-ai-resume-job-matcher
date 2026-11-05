import type { AnalysisReport } from "./types";

export class ApiError extends Error {
  constructor(public code: string, message: string, public status = 0) {
    super(message);
  }
}

const BASE = "/api/v1";

/** All calls send cookies and the CSRF header the backend requires on writes. */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Requested-With", "ResumeIQ");
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(BASE + path, { ...init, headers, credentials: "include" });
  } catch {
    throw new ApiError("NETWORK", "Can't reach the ResumeIQ server. Check that the backend is running on port 8000.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail && typeof body.detail === "object" && !Array.isArray(body.detail) ? body.detail : body;
    if (detail.code) throw new ApiError(detail.code, detail.message, res.status);
    if (res.status === 422) throw new ApiError("VALIDATION", "Some fields are missing or too short.", 422);
    throw new ApiError("SERVER", `The request failed (error ${res.status}). Try again.`, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);

// ---------------------------------------------------------------- types

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  email_verified: boolean;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ResumeVersion {
  id: string;
  version_number: number;
  note: string | null;
  created_at: string;
  parsed_summary: {
    sections?: string[];
    skills?: string[];
    experience_years?: number | null;
    warnings?: string[];
    word_count?: number;
  };
}

export interface Resume {
  id: string;
  name: string;
  original_filename: string | null;
  file_type: string;
  file_size: number | null;
  created_at: string;
  updated_at: string;
  latest_version: ResumeVersion | null;
}

export interface Job {
  id: string;
  job_title: string;
  company_name: string | null;
  category: string;
  created_at: string;
  updated_at: string;
  keyword_count: number;
}

export type AnalysisStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface AnalysisSummary {
  id: string;
  status: AnalysisStatus;
  resume_id: string;
  resume_version_id: string;
  job_description_id: string;
  overall_score: number | null;
  mandatory_gaps: number | null;
  created_at: string;
  completed_at: string | null;
  resume_name: string | null;
  job_title: string | null;
  version_number: number | null;
}

export interface AnalysisDetail extends AnalysisSummary {
  report: AnalysisReport | null;
  error_message: string | null;
}

// ------------------------------------------------------------ endpoints

export interface GuestInput {
  jobText: string;
  resumeText?: string;
  resumeFile?: File | null;
}

export function runGuestAnalysis(input: GuestInput): Promise<AnalysisReport> {
  const form = new FormData();
  form.append("job_text", input.jobText);
  if (input.resumeFile) form.append("resume_file", input.resumeFile);
  else if (input.resumeText) form.append("resume_text", input.resumeText);
  return request("/analyses/guest", { method: "POST", body: form });
}

export const auth = {
  me: () => request<User>("/auth/me"),
  register: (email: string, password: string, full_name?: string) =>
    request<User>("/auth/register", { method: "POST", body: json({ email, password, full_name }) }),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: json({ email, password }) }),
  logout: () => request<{ message: string }>("/auth/logout", { method: "POST" }),
  verifyEmail: (token: string) => request<User>("/auth/verify-email", { method: "POST", body: json({ token }) }),
  resendVerification: () => request<{ message: string }>("/auth/resend-verification", { method: "POST" }),
  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", { method: "POST", body: json({ email }) }),
  resetPassword: (token: string, password: string) =>
    request<{ message: string }>("/auth/reset-password", { method: "POST", body: json({ token, password }) }),
  deleteAccount: (password: string) =>
    request<{ message: string }>("/account", { method: "DELETE", body: json({ password }) }),
};

export const resumes = {
  list: () => request<Page<Resume>>("/resumes?limit=100"),
  upload: (file: File, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (name) form.append("name", name);
    return request<Resume>("/resumes/upload", { method: "POST", body: form });
  },
  fromText: (name: string, text: string) =>
    request<Resume>("/resumes/text", { method: "POST", body: json({ name, text }) }),
  remove: (id: string) => request<{ message: string }>(`/resumes/${id}`, { method: "DELETE" }),
};

export const jobs = {
  list: () => request<Page<Job>>("/jobs?limit=100"),
  create: (description: string, company_name?: string) =>
    request<Job>("/jobs", { method: "POST", body: json({ description, company_name: company_name || null }) }),
  remove: (id: string) => request<{ message: string }>(`/jobs/${id}`, { method: "DELETE" }),
};

export const analyses = {
  list: () => request<Page<AnalysisSummary>>("/analyses?limit=50"),
  get: (id: string) => request<AnalysisDetail>(`/analyses/${id}`),
  start: (resume_id: string, job_id: string) =>
    request<AnalysisSummary>("/analyses", { method: "POST", body: json({ resume_id, job_id }) }),
  rerun: (id: string) => request<AnalysisSummary>(`/analyses/${id}/reanalyze`, { method: "POST" }),
};
