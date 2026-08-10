import { cn } from "@/lib/utils";

const toneMap: Record<string, string> = {
  new: "badge-neutral",
  matched: "badge-info",
  queued: "badge-info",
  applying: "badge-warn",
  applied: "badge-success",
  rejected: "badge-danger",
  archived: "badge-neutral",
  draft: "badge-neutral",
  preparing: "badge-info",
  ready: "badge-info",
  awaiting_approval: "badge-warn",
  approved: "badge-success",
  submitting: "badge-warn",
  submitted: "badge-success",
  failed: "badge-danger",
  needs_human: "badge-warn",
  cancelled: "badge-neutral",
  pending: "badge-neutral",
  running: "badge-info",
  succeeded: "badge-success",
  ok: "badge-success",
  degraded: "badge-warn",
  down: "badge-danger",
  idle: "badge-neutral",
  busy: "badge-info",
  offline: "badge-danger",
};

type StatusBadgeProps = {
  status: string;
  className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = status.replace(/_/g, " ");
  return (
    <span className={cn("badge", toneMap[status] ?? "badge-neutral", className)}>
      {label}
    </span>
  );
}
