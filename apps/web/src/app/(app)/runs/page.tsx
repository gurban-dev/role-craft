import type { Metadata } from "next";
import { DataTable, type Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { Run } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Runs",
};

export default async function RunsPage() {
  let runs: Run[] = [];
  let error: string | null = null;

  try {
    runs = asList(await endpoints.runs());
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load runs";
  }

  const columns: Column<Run>[] = [
    { key: "kind", header: "Kind", render: (row) => row.kind },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "started",
      header: "Started",
      render: (row) => formatDate(row.started_at),
    },
    {
      key: "finished",
      header: "Finished",
      render: (row) => formatDate(row.finished_at),
    },
    {
      key: "message",
      header: "Message",
      className: "max-w-md",
      render: (row) => (
        <span className="line-clamp-2 text-[var(--muted)]">{row.message ?? "—"}</span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Runs"
        description="Discovery, matching, and automation worker executions."
      />
      {error ? <ErrorState title="Could not load runs" message={error} /> : null}
      <DataTable
        columns={columns}
        rows={runs}
        rowKey={(r) => r.id}
        emptyTitle="No runs yet"
        emptyDescription="Pipeline runs will appear here once workers start."
      />
    </div>
  );
}
