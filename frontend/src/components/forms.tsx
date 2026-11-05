import type { InputHTMLAttributes, ReactNode } from "react";

export function Field({ label, hint, ...props }: { label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="font-medium">{label}</span>
      <input
        {...props}
        className="rounded-md border border-line bg-page px-3 py-2 text-sm placeholder:text-muted"
      />
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mx-auto mt-10 max-w-md rounded-lg border border-line bg-surface p-6">
      <h1 className="mb-5 text-xl font-semibold">{title}</h1>
      {children}
    </div>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return children ? <p role="alert" className="text-sm text-bad">{children}</p> : null;
}

export function SubmitButton({ busy, children }: { busy: boolean; children: ReactNode }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="rounded-md bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40 dark:text-page"
    >
      {children}
    </button>
  );
}

export const errorMessage = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Try again.";
