import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Sign in",
};

export default function LoginPage() {
  return (
    <div className="auth-card">
      <div className="mb-6">
        <p className="font-serif text-2xl font-semibold tracking-tight">ApplyDesk</p>
        <h1 className="mt-1 text-sm text-[var(--muted)]">
          Sign in to your application pipeline
        </h1>
      </div>
      <LoginForm />
    </div>
  );
}
