import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-4">
      <div>
        <h1 className="font-serif text-2xl font-semibold tracking-tight text-[var(--fg)]">
          {title}
        </h1>
        {description ? (
          <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function Panel({
  title,
  children,
  className,
  actions,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-md border border-[var(--border)] bg-[var(--surface)]",
        className,
      )}
    >
      {title ? (
        <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-3 py-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            {title}
          </h2>
          {actions}
        </div>
      ) : null}
      <div className="p-3">{children}</div>
    </section>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="rounded-md border border-dashed border-[var(--border)] px-4 py-8 text-center">
      <p className="text-sm font-medium">{title}</p>
      {description ? (
        <p className="mt-1 text-sm text-[var(--muted)]">{description}</p>
      ) : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
}: {
  title?: string;
  message?: string;
}) {
  return (
    <div
      role="alert"
      className="rounded-md border border-[var(--danger)]/40 bg-[var(--danger-soft)] px-4 py-3 text-sm"
    >
      <p className="font-medium text-[var(--danger)]">{title}</p>
      {message ? <p className="mt-1 text-[var(--fg)]">{message}</p> : null}
    </div>
  );
}

export function LoadingBlock({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--border)]" />
      <div className="h-24 animate-pulse rounded bg-[var(--border)]/60" />
      <div className="h-4 w-2/3 animate-pulse rounded bg-[var(--border)]" />
    </div>
  );
}
