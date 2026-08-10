import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Register",
};

export default function RegisterPage() {
  return (
    <div className="auth-card">
      <div className="mb-6">
        <p className="font-serif text-2xl font-semibold tracking-tight">ApplyDesk</p>
        <h1 className="mt-1 text-sm text-[var(--muted)]">
          Create an account to start automating applications
        </h1>
      </div>
      <RegisterForm />
    </div>
  );
}
