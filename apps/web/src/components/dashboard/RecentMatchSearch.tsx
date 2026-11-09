"use client";

import { DataTable, type Column } from "@/components/DataTable";
import { ErrorState } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints, type RecentJobMatch } from "@/lib/endpoints";
import type {
  JobRegion,
  JobSeniorityFilter,
  JobWorkArrangement,
  RegionWorkArrangements,
} from "@/lib/types";
import { useState } from "react";

// With as const, the TypeScript compiler transforms it into
// a readonly tuple. This strips away all methods that mutate
// data and blocks direct index assignments.
export const JOB_REGIONS = [
  "Europe",
  "North America",
  "South America",
  "Asia",
  "Africa",
] as const satisfies readonly JobRegion[];

const WORK_ARRANGEMENTS: { value: JobWorkArrangement; label: string }[] = [
  { value: "in_person", label: "In-person" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
];

const INITIAL_REGION_ARRANGEMENTS: RegionWorkArrangements = {
  Europe: ["in_person", "remote", "hybrid"],
  "North America": ["in_person", "remote", "hybrid"],
  "South America": ["in_person", "remote", "hybrid"],
  Asia: ["in_person", "remote", "hybrid"],
  Africa: ["in_person", "remote", "hybrid"],
};

const columns: Column<RecentJobMatch>[] = [
  { key: "rank", header: "#", render: (row) => row.rank },
  { key: "role", header: "Role", render: (row) => row.role },
  { key: "company", header: "Company", render: (row) => row.company },
  { key: "location", header: "Location", render: (row) => row.location || "—" },
  {
    key: "posted",
    header: "Posted",
    render: (row) => formatPosted(row.posted),
  },
  { key: "source", header: "Source", render: (row) => row.source },
  {
    key: "applicants",
    header: "Applicants",
    render: (row) => row.applicant_count ?? "—",
  },
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
  const [regions, setRegions] = useState<JobRegion[]>([...JOB_REGIONS]);
  const [regionWorkArrangements, setRegionWorkArrangements] =
    useState<RegionWorkArrangements>(INITIAL_REGION_ARRANGEMENTS);
  const [seniority, setSeniority] = useState<JobSeniorityFilter>("non_senior");
  const [postedWithinHours, setPostedWithinHours] = useState(24);
  const [rows, setRows] = useState<RecentJobMatch[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function toggleRegion(region: JobRegion) {
    setRegions((current) =>
      current.includes(region)
        ? current.filter((item) => item !== region)
        : [...current, region],
    );
  }

  function toggleWorkArrangement(region: JobRegion, arrangement: JobWorkArrangement) {
    setRegionWorkArrangements((current) => {
      const selected = current[region];
      return {
        ...current,
        [region]: selected.includes(arrangement)
          ? selected.filter((value) => value !== arrangement)
          : [...selected, arrangement],
      };
    });
  }

  async function onSearch() {
    const activeRegions = JOB_REGIONS.filter(
      (region) => regions.includes(region) && regionWorkArrangements[region].length > 0,
    );
    if (activeRegions.length === 0) {
      setError("Select at least one continent and work arrangement.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const matches = await endpoints.recentJobMatches(
        activeRegions,
        postedWithinHours,
        seniority,
        regionWorkArrangements,
      );
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
          Posted within
        </legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {[
            { hours: 24, label: "Past 24 hours" },
            { hours: 72, label: "Past 72 hours" },
            { hours: 168, label: "Past 7 days" },
            { hours: 720, label: "Past month" },
          ].map((range) => (
            <label
              key={range.hours}
              className={`flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                postedWithinHours === range.hours
                  ? "border-[var(--accent)] text-[var(--accent)]"
                  : "border-[var(--border)] text-[var(--fg)]"
              }`}
            >
              <input
                type="radio"
                name="posted-within-hours"
                value={range.hours}
                checked={postedWithinHours === range.hours}
                onChange={() => {
                  setPostedWithinHours(range.hours);
                  setRows(null);
                  setError(null);
                }}
              />
              {range.label}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="mb-3">
        <legend className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Seniority
        </legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {([
            ["non_senior", "Non-senior"],
            ["senior", "Senior"],
            ["both", "Both"],
          ] as const).map(([value, label]) => (
            <label key={value} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="job-seniority"
                value={value}
                checked={seniority === value}
                onChange={() => setSeniority(value)}
              />
              {label}
            </label>
          ))}
        </div>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Jobs with unclear seniority are excluded from all three choices.
        </p>
      </fieldset>
      <fieldset className="mb-3">
        <legend className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Continents and work arrangements
        </legend>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Select a continent and the work arrangements you will consider there. A continent with no
          arrangement selected is excluded.
        </p>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {JOB_REGIONS.map((region) => (
            <fieldset key={region} className="rounded-md border border-[var(--border)] p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="checkbox"
                  checked={regions.includes(region)}
                  aria-label={`Include ${region}`}
                  onChange={() => toggleRegion(region)}
                />
                {region}
              </label>
              <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                {WORK_ARRANGEMENTS.map((arrangement) => (
                  <label key={arrangement.value} className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      aria-label={`${region} ${arrangement.label}`}
                      checked={regionWorkArrangements[region].includes(arrangement.value)}
                      disabled={!regions.includes(region)}
                      onChange={() => toggleWorkArrangement(region, arrangement.value)}
                    />
                    {arrangement.label}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}
        </div>
      </fieldset>
      <button
        type="button"
        className="btn-primary"
        onClick={onSearch}
        disabled={pending || !JOB_REGIONS.some((region) => regions.includes(region) && regionWorkArrangements[region].length > 0)}
        data-testid="recent-match-search"
      >
        {pending ? "Searching…" : "Find matching jobs"}
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
            emptyDescription="No LinkedIn jobs met every filter, including a verified applicant count below 100 and a resume-fit score of at least 8/10. Try a wider date window."
          />
        </div>
      ) : null}
    </div>
  );
}
