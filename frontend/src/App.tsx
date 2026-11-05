import { BrowserRouter, Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, RequireAuth, useAuth } from "./auth";
import GuestPage from "./pages/GuestPage";
import DashboardPage from "./pages/DashboardPage";
import AnalysisPage from "./pages/AnalysisPage";
import { ForgotPasswordPage, LoginPage, RegisterPage, ResetPasswordPage, VerifyEmailPage } from "./pages/AuthPages";

function Header() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const nav = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-2.5 py-1.5 text-sm ${isActive ? "font-semibold text-ink" : "text-muted hover:text-ink"}`;

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 py-6">
      <Link to="/" className="text-lg font-bold tracking-tight">
        Resume<span className="text-brand">IQ</span>
      </Link>
      <nav className="flex items-center gap-1" aria-label="Main">
        <NavLink to="/" end className={nav}>Quick check</NavLink>
        {user && <NavLink to="/dashboard" className={nav}>Dashboard</NavLink>}
        {!loading && !user && <NavLink to="/login" className={nav}>Log in</NavLink>}
        {!loading && !user && (
          <Link to="/register" className="ml-1 rounded-md bg-brand px-3 py-1.5 text-sm font-semibold text-white dark:text-page">
            Sign up
          </Link>
        )}
        {user && (
          <button className="rounded-md px-2.5 py-1.5 text-sm text-muted hover:text-ink"
                  onClick={async () => { await logout(); navigate("/"); }}>
            Log out
          </button>
        )}
      </nav>
    </header>
  );
}

export function AppRoutes() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<GuestPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
          <Route path="/analyses/:id" element={<RequireAuth><AnalysisPage /></RequireAuth>} />
          <Route path="*" element={<p className="py-16 text-center text-sm text-muted">This page doesn’t exist. <Link to="/" className="text-brand">Go home</Link></p>} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
