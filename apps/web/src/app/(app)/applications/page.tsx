import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { ApplicationsFilterBar } from "@/components/applications/ApplicationsFilterBar";
import { DataTable, type Column } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { Application } from "@/lib/types";
import { formatDate, formatPercent } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Applications",
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ApplicationsPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q : "";
  const status = typeof sp.status === "string" ? sp.status : "";
  const query = new URLSearchParams();
  if (q) query.set("q", q);
  if (status) query.set("status", status);

  let applications: Application[] = [];
  let error: string | null = null;
  try {
    applications = asList(await endpoints.applications(query.toString()));
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load applications";
  }

  const columns: Column<Application>[] = [
    {
      key: "job",
      header: "Application",
      render: (row) => (
        <div>
          <Link
            href={`/applications/${row.id}`}
            className="font-medium text-[var(--accent)] hover:underline"
          >
            {row.job?.title ?? `Application ${row.id.slice(0, 8)}`}
          </Link>
          <div className="text-xs text-[var(--muted)]">
            {row.job?.company ?? "Unknown company"}
          </div>
        </div>
      ),
    },
    {
      key: "match",
      header: "Match",
      render: (row) => formatPercent(row.match_score ?? row.match?.score),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "updated",
      header: "Updated",
      render: (row) => formatDate(row.updated_at ?? row.created_at),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Applications"
        description="Track preparation, approval, submission, and human-action states."
      />
      <Suspense fallback={null}>
        <ApplicationsFilterBar />
      </Suspense>
      {error ? (
        <ErrorState title="Could not load applications" message={error} />
      ) : null}
      <DataTable
        columns={columns}
        rows={applications}
        rowKey={(row) => row.id}
        emptyTitle="No applications"
        emptyDescription="Create applications from matched jobs to populate this list."
      />
    </div>
  );
}
