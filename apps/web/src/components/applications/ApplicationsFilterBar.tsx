"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";

const statuses = [
  "",
  "draft",
  "preparing",
  "ready",
  "awaiting_approval",
  "approved",
  "submitting",
  "submitted",
  "failed",
  "needs_human",
  "cancelled",
] as const;

export function ApplicationsFilterBar() {
  const router = useRouter();
  const params = useSearchParams();
  const [pending, startTransition] = useTransition();

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next = new URLSearchParams();
    const q = String(fd.get("q") ?? "").trim();
    const status = String(fd.get("status") ?? "");
    if (q) next.set("q", q);
    if (status) next.set("status", status);
    startTransition(() => {
      router.push(`/applications${next.toString() ? `?${next}` : ""}`);
    });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mb-4 flex flex-wrap items-end gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] p-3"
    >
      <div className="min-w-[12rem] flex-1">
        <label htmlFor="app-q" className="label">
          Search
        </label>
        <input
          id="app-q"
          name="q"
          className="input"
          placeholder="Company, role…"
          defaultValue={params.get("q") ?? ""}
        />
      </div>
      <div className="w-52">
        <label htmlFor="app-status" className="label">
          Status
        </label>
        <select
          id="app-status"
          name="status"
          className="input"
          defaultValue={params.get("status") ?? ""}
        >
          <option value="">All</option>
          {statuses.filter(Boolean).map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>
      <button type="submit" className="btn-primary" disabled={pending}>
        {pending ? "Filtering…" : "Apply"}
      </button>
    </form>
  );
}
