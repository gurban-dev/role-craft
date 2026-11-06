"use client";

import { DataTable, type Column } from "@/components/DataTable";
import { ErrorState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints, type RecentJobMatch } from "@/lib/endpoints";
import { useState } from "react";

export const JOB_REGIONS = [
  "Europe",
  "North America",
  "South America",
  "Asia",
  "Africa",
  "Australia",
] as const;

const columns: Column<RecentJobMatch>[] = [
  { key: "rank", header: "#", render: (row) => row.rank },
  { key: "role", header: "Role", render: (row) => row.role },
  { key: "company", header: "Company", render: (row) => row.company },
  {
    key: "posted",
    header: "Posted",
    render: (row) => formatPosted(row.posted),
  },
  { key: "source", header: "Source", render: (row) => row.source },
  {
    key: "fit",
    header: "Fit Score",
    render: (row) => row.fit_score.toFixed(1),
  },
  {
    key: "apply",
    header: "Apply Link On Company Website",
    render: (row) =>
      row.apply_link ? (
        <a href={row.apply_link} target="_blank" rel="noreferrer" className="underline">
          {row.apply_link}
        </a>
      ) : (
        ""
      ),
  },
];

function formatPosted(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function RecentMatchSearch() {
  const [regions, setRegions] = useState<string[]>(["Europe"]);
  const [rows, setRows] = useState<RecentJobMatch[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function toggleRegion(region: string) {
    setRegions((current) =>
      current.includes(region)
        ? current.filter((item) => item !== region)
        : [...current, region],
    );
  }

  async function onSearch() {
    if (regions.length === 0) {
      setError("Choose at least one region.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const matches = await endpoints.recentJobMatches(regions);
      setRows(matches);
    } catch (err) {
      setRows(null);
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Job search failed",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mb-4 w-full">
      <fieldset className="mb-3">
        <legend className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Region
        </legend>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
          {JOB_REGIONS.map((region) => (
            <label key={region} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={regions.includes(region)}
                onChange={() => toggleRegion(region)}
              />
              {region}
            </label>
          ))}
        </div>
      </fieldset>
      <button
        type="button"
        className="btn-primary"
        onClick={onSearch}
        disabled={pending || regions.length === 0}
        data-testid="recent-match-search"
      >
        {pending ? "Searching last 24 hours…" : "Find matching jobs"}
      </button>
      {error ? (
        <div className="mt-3">
          <ErrorState title="Job search failed" message={error} />
        </div>
      ) : null}
      {rows ? (
        <div className="mt-3" data-testid="recent-match-table">
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(row) => `${row.rank}-${row.apply_link}`}
            emptyTitle="No matching jobs"
            emptyDescription="No roles posted in the last 24 hours scored above 7."
          />
        </div>
      ) : null}
    </div>
  );
}
