import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "./App";
import { AuthProvider } from "./auth";
import type { AnalysisReport } from "./types";

const report: AnalysisReport = {
  job_title: "Customer Support Phone Specialist",
  job_category: "customer_service",
  overall_score: 70,
  interpretation: "Good alignment",
  confidence: "High",
  confidence_reasons: [],
  components: [
    { key: "skills", label: "Technical and functional skills", weight: 0.3, effective_weight: 0.6, score: 90,
      status: "SCORED", contribution: 54, explanation: "9 of 10 job skills confirmed." },
    { key: "education", label: "Education", weight: 0.05, effective_weight: 0, score: null,
      status: "NOT_APPLICABLE", contribution: 0, explanation: "No education requirement." },
  ],
  mandatory_requirements: [{ requirement: "English", kind: "language", status: "PARTIAL", evidence: null }],
  mandatory_gaps: 0,
  keyword_matches: [
    { keyword: "Inbound calls", category: "customer_service", importance: "HIGH", requirement_type: "RESPONSIBILITY",
      match_type: "EXACT_MATCH", confidence: 1, resume_evidence: "Handled 60+ inbound customer calls per day.",
      resume_section: "experience", job_evidence: "Take inbound customer calls", note: "Same wording." },
    { keyword: "Communication", category: "soft_skill", importance: "MEDIUM", requirement_type: "MANDATORY",
      match_type: "MISSING", confidence: 0, resume_evidence: null, resume_section: null,
      job_evidence: "Communicate professionally", note: "No evidence found in the resume." },
  ],
  keyword_match_rate: 50,
  missing_keywords: [],
  requirement_coverage: [],
  ats_checks: [{ check: "Skills section", result: "PASS", detail: "Skills section found." }],
  recommendations: [],
  resume_summary: { sections_found: [], skills_found: [], experience_years: 8.9, education: [], warnings: [] },
  similarity_backend: "tfidf",
  disclaimer: "This is an explainable job-fit estimate, not a hiring decision.",
};

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const notLoggedIn = () => json({ detail: { code: "NOT_AUTHENTICATED", message: "Log in to continue." } }, 401);

function mockApi(routes: Record<string, () => Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const key = Object.keys(routes).find((k) => url.endsWith(k));
    return key ? routes[key]() : json({ detail: { code: "NOT_FOUND", message: "Not found." } }, 404);
  });
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

test("analyze button stays disabled until both documents are provided", () => {
  mockApi({ "/auth/me": notLoggedIn });
  renderAt("/");
  expect(screen.getByRole("button", { name: "Analyze job fit" })).toBeDisabled();
});

test("guest analysis shows score, evidence and filters", async () => {
  const fetchMock = mockApi({ "/auth/me": notLoggedIn, "/analyses/guest": () => json(report) });
  renderAt("/");
  fireEvent.click(screen.getByRole("button", { name: "customer support" }));
  fireEvent.click(screen.getByRole("button", { name: "Analyze job fit" }));

  await waitFor(() => expect(screen.getByText("70")).toBeInTheDocument());
  expect(screen.getByText("Good alignment")).toBeInTheDocument();
  const [, init] = fetchMock.mock.calls.find(([u]) => String(u).endsWith("/analyses/guest"))!;
  expect(new Headers(init?.headers).get("X-Requested-With")).toBe("ResumeIQ");

  fireEvent.click(screen.getByRole("button", { name: "Show evidence for Inbound calls" }));
  expect(screen.getByText("Handled 60+ inbound customer calls per day.")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /Not found \(1\)/ }));
  expect(screen.queryByText("Inbound calls")).not.toBeInTheDocument();
  expect(screen.getByText("Communication")).toBeInTheDocument();
});

test("shows the server's error message", async () => {
  mockApi({
    "/auth/me": notLoggedIn,
    "/analyses/guest": () => json({ code: "OCR_REQUIRED", message: "This PDF looks scanned." }, 422),
  });
  renderAt("/");
  fireEvent.click(screen.getByRole("button", { name: "junior developer" }));
  fireEvent.click(screen.getByRole("button", { name: "Analyze job fit" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This PDF looks scanned.");
});

test("dashboard redirects to login when logged out", async () => {
  mockApi({ "/auth/me": notLoggedIn });
  renderAt("/dashboard");
  expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
});

test("completed analysis page renders the saved report", async () => {
  const user = { id: "u1", email: "a@example.com", full_name: null, role: "USER", email_verified: true,
                 created_at: "2026-11-05T10:00:00Z" };
  mockApi({
    "/auth/me": () => json(user),
    "/analyses/a1": () => json({
      id: "a1", status: "COMPLETED", resume_id: "r1", resume_version_id: "v1", job_description_id: "j1",
      overall_score: 70, mandatory_gaps: 0, created_at: "2026-11-05T10:00:00Z", completed_at: "2026-11-05T10:00:02Z",
      resume_name: "Support CV", job_title: "Customer Support Phone Specialist", version_number: 2,
      report, error_message: null,
    }),
  });
  renderAt("/analyses/a1");
  expect(await screen.findByText("Good alignment")).toBeInTheDocument();
  expect(screen.getByText(/Support CV \(version 2\)/)).toBeInTheDocument();
});
