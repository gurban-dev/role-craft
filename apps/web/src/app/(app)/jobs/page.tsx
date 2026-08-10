import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { DataTable, type Column } from "@/components/DataTable";
import { JobsFilterBar } from "@/components/jobs/JobsFilterBar";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { Job } from "@/lib/types";
import { formatDate, formatPercent } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Jobs",
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function JobsPage({
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

  let jobs: Job[] = [];
  let error: string | null = null;
  try {
    jobs = asList(await endpoints.jobs(query.toString()));
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load jobs";
  }

  const columns: Column<Job>[] = [
    {
      key: "title",
      header: "Role",
      render: (row) => (
        <div>
          <Link
            href={`/jobs/${row.id}`}
            className="font-medium text-[var(--accent)] hover:underline"
          >
            {row.title}
          </Link>
          <div className="text-xs text-[var(--muted)]">{row.company}</div>
        </div>
      ),
    },
    {
      key: "location",
      header: "Location",
      render: (row) => row.location || (row.remote ? "Remote" : "—"),
    },
    {
      key: "match",
      header: "Match",
      render: (row) => formatPercent(row.match_score),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "posted",
      header: "Posted",
      render: (row) => formatDate(row.posted_at ?? row.created_at),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Jobs"
        description="Discovered roles with match scores and pipeline status."
      />
      <Suspense fallback={null}>
        <JobsFilterBar />
      </Suspense>
      {error ? <ErrorState title="Could not load jobs" message={error} /> : null}
      <DataTable
        columns={columns}
        rows={jobs}
        rowKey={(row) => row.id}
        emptyTitle="No jobs found"
        emptyDescription="Adjust filters or wait for the next discovery run."
      />
    </div>
  );
}
