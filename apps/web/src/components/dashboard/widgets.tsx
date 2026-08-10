import type { DashboardStats } from "@/lib/types";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { EmptyState } from "@/components/ui";

export function StatWidget({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "accent" | "warn" | "success";
}) {
  return (
    <div
      className={cn(
        "rounded-md border border-[var(--border)] bg-[var(--surface)] p-3",
        tone === "accent" && "border-[var(--accent)]/30",
        tone === "warn" && "border-[var(--warn)]/40",
        tone === "success" && "border-[var(--success)]/40",
      )}
      data-testid="stat-widget"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-1 font-serif text-3xl font-semibold tabular-nums text-[var(--fg)]">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  );
}

export function DailyTargetWidget({ stats }: { stats: DashboardStats }) {
  const progress =
    stats.daily_target > 0
      ? Math.min(100, Math.round((stats.submitted_today / stats.daily_target) * 100))
      : 0;

  return (
    <div
      className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3"
      data-testid="daily-target-widget"
    >
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Daily target
        </p>
        <p className="text-xs text-[var(--muted)]">{progress}%</p>
      </div>
      <p className="mt-1 font-serif text-3xl font-semibold tabular-nums">
        {stats.submitted_today}
        <span className="text-lg text-[var(--muted)]"> / {stats.daily_target}</span>
      </p>
      <div
        className="mt-3 h-2 overflow-hidden rounded bg-[var(--surface-2)]"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Daily submission progress"
      >
        <div
          className="h-full rounded bg-[var(--accent)] transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export function PipelineWidget({ stats }: { stats: DashboardStats }) {
  const entries = Object.entries(stats.pipeline);
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
        Pipeline
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {entries.map(([key, count]) => (
          <div key={key} className="rounded bg-[var(--surface-2)] px-2 py-1.5">
            <dt className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
              {key.replace(/_/g, " ")}
            </dt>
            <dd className="font-serif text-xl font-semibold tabular-nums">{count}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function HumanActionQueueWidget({ stats }: { stats: DashboardStats }) {
  const items = stats.human_action_queue ?? [];
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Human-action queue
        </p>
        <span className="badge badge-warn">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            title="Queue clear"
            description="No applications currently need manual intervention."
          />
        </div>
      ) : (
        <ul className="mt-3 divide-y divide-[var(--border)]">
          {items.map((item) => (
            <li key={item.id} className="flex items-start justify-between gap-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">
                  {item.job_title} · {item.company}
                </p>
                <p className="text-xs text-[var(--muted)]">{item.reason}</p>
              </div>
              <Link
                href={`/applications/${item.application_id}`}
                className="shrink-0 text-xs font-medium text-[var(--accent)] hover:underline"
              >
                Open
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
