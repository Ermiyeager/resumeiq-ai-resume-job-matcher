import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { auth } from "../api";
import { useAuth } from "../auth";
import { Card, ErrorText, Field, SubmitButton, errorMessage } from "../components/forms";

function useSubmit(action: () => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, onSubmit };
}

export function LoginPage() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, onSubmit } = useSubmit(async () => {
    setUser(await auth.login(email, password));
    navigate(from, { replace: true });
  });

  return (
    <Card title="Log in">
      <form className="grid gap-4" onSubmit={onSubmit}>
        <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" autoComplete="current-password" required value={password}
               onChange={(e) => setPassword(e.target.value)} />
        <ErrorText>{error}</ErrorText>
        <SubmitButton busy={busy}>{busy ? "Logging in…" : "Log in"}</SubmitButton>
      </form>
      <p className="mt-5 flex justify-between text-sm">
        <Link to="/forgot-password" className="text-brand hover:underline">Forgot password?</Link>
        <Link to="/register" className="text-brand hover:underline">Create an account</Link>
      </p>
    </Card>
  );
}

export function RegisterPage() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { busy, error, onSubmit } = useSubmit(async () => {
    setUser(await auth.register(email, password, name || undefined));
    navigate("/dashboard", { replace: true });
  });

  return (
    <Card title="Create your account">
      <form className="grid gap-4" onSubmit={onSubmit}>
        <Field label="Name (optional)" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" autoComplete="new-password" required minLength={10} value={password}
               hint="At least 10 characters." onChange={(e) => setPassword(e.target.value)} />
        <ErrorText>{error}</ErrorText>
        <SubmitButton busy={busy}>{busy ? "Creating account…" : "Create account"}</SubmitButton>
      </form>
      <p className="mt-5 text-sm text-muted">
        Already have an account? <Link to="/login" className="text-brand hover:underline">Log in</Link>
      </p>
    </Card>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState("");
  const { busy, error, onSubmit } = useSubmit(async () => setSent((await auth.forgotPassword(email)).message));

  return (
    <Card title="Reset your password">
      {sent ? (
        <p className="text-sm">{sent}</p>
      ) : (
        <form className="grid gap-4" onSubmit={onSubmit}>
          <Field label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <ErrorText>{error}</ErrorText>
          <SubmitButton busy={busy}>{busy ? "Sending…" : "Send reset link"}</SubmitButton>
        </form>
      )}
    </Card>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState("");
  const { busy, error, onSubmit } = useSubmit(async () =>
    setDone((await auth.resetPassword(params.get("token") ?? "", password)).message),
  );

  return (
    <Card title="Choose a new password">
      {done ? (
        <p className="text-sm">{done} <Link to="/login" className="text-brand hover:underline">Log in</Link></p>
      ) : (
        <form className="grid gap-4" onSubmit={onSubmit}>
          <Field label="New password" type="password" autoComplete="new-password" required minLength={10}
                 hint="At least 10 characters." value={password} onChange={(e) => setPassword(e.target.value)} />
          <ErrorText>{error}</ErrorText>
          <SubmitButton busy={busy}>{busy ? "Saving…" : "Save new password"}</SubmitButton>
        </form>
      )}
    </Card>
  );
}

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const { setUser } = useAuth();
  const [state, setState] = useState<"working" | "done" | string>("working");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // tokens are single-use; StrictMode runs effects twice in development
    started.current = true;
    auth.verifyEmail(params.get("token") ?? "")
      .then((u) => { setUser(u); setState("done"); })
      .catch((e) => setState(errorMessage(e)));
  }, [params, setUser]);

  return (
    <Card title="Confirm your email">
      <p className="text-sm">
        {state === "working" ? "Confirming…" : state === "done" ? "Your email is confirmed." : state}
      </p>
      {state === "done" && <Link to="/dashboard" className="mt-4 inline-block text-sm text-brand hover:underline">Go to your dashboard</Link>}
    </Card>
  );
}
