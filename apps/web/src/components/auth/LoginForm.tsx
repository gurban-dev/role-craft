"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useMemo, useState } from "react";
import { ApiError } from "@/lib/api";
import { loginRequest } from "@/lib/auth";
import { fieldErrors, loginSchema } from "@/lib/validations";
import { useToast } from "@/components/Toast";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";

const ERROR_MESSAGES: Record<string, string> = {
  google_auth_failed: "Google sign-in failed. Please try again.",
  google_not_configured:
    "Google sign-in is not configured. Ask an admin to set Google OAuth credentials.",
};

function LoginFormInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Partial<Record<"email" | "password", string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const oauthError = useMemo(() => {
    const code = searchParams.get("error");
    if (!code) return null;
    return ERROR_MESSAGES[code] ?? ERROR_MESSAGES.google_auth_failed;
  }, [searchParams]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const nextErrors = fieldErrors(loginSchema, { email, password });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await loginRequest(email.trim(), password);
      toast.success("Signed in");
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Login failed";
      setFormError(message);
      toast.error("Login failed", message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      {oauthError ? (
        <p
          className="rounded border border-[var(--danger)]/40 bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]"
          role="alert"
        >
          {oauthError}
        </p>
      ) : null}

      <GoogleSignInButton />

      <div className="relative py-1 text-center text-xs uppercase tracking-wide text-[var(--muted)]">
        <span className="relative z-[1] bg-[var(--surface)] px-2">or</span>
        <span className="absolute left-0 right-0 top-1/2 border-t border-[var(--border)]" />
      </div>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="label">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? "email-error" : undefined}
          />
          {errors.email ? (
            <p id="email-error" className="field-error" role="alert">
              {errors.email}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor="password" className="label">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? "password-error" : undefined}
          />
          {errors.password ? (
            <p id="password-error" className="field-error" role="alert">
              {errors.password}
            </p>
          ) : null}
        </div>

        {formError ? (
          <p
            className="rounded border border-[var(--danger)]/40 bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]"
            role="alert"
          >
            {formError}
          </p>
        ) : null}

        <button type="submit" className="btn-primary w-full" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="text-center text-sm text-[var(--muted)]">
          No account?{" "}
          <Link href="/register" className="font-medium text-[var(--accent)] hover:underline">
            Register
          </Link>
        </p>
      </form>
    </div>
  );
}

export function LoginForm() {
  return (
    <Suspense fallback={<div className="text-sm text-[var(--muted)]">Loading…</div>}>
      <LoginFormInner />
    </Suspense>
  );
}
