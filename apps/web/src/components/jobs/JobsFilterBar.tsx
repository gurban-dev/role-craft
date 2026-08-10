"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useTransition } from "react";

const statuses = [
  "",
  "new",
  "matched",
  "queued",
  "applying",
  "applied",
  "rejected",
  "archived",
] as const;

export function JobsFilterBar() {
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
      router.push(`/jobs${next.toString() ? `?${next}` : ""}`);
    });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mb-4 flex flex-wrap items-end gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] p-3"
    >
      <div className="min-w-[12rem] flex-1">
        <label htmlFor="job-q" className="label">
          Search
        </label>
        <input
          id="job-q"
          name="q"
          className="input"
          placeholder="Title, company…"
          defaultValue={params.get("q") ?? ""}
        />
      </div>
      <div className="w-44">
        <label htmlFor="job-status" className="label">
          Status
        </label>
        <select
          id="job-status"
          name="status"
          className="input"
          defaultValue={params.get("status") ?? ""}
        >
          <option value="">All</option>
          {statuses.filter(Boolean).map((s) => (
            <option key={s} value={s}>
              {s}
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
