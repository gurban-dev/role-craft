import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState, ErrorState, PageHeader, Panel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Job, MatchAnalysis } from "@/lib/types";
import { formatDate, formatPercent } from "@/lib/utils";

type Params = Promise<{ id: string }>;

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { id } = await params;
  return { title: `Job ${id}` };
}

function asMatch(raw: unknown): MatchAnalysis | null {
  if (!raw || typeof raw !== "object") return null;
  const m = raw as Partial<MatchAnalysis>;
  if (typeof m.score !== "number") return null;
  return {
    score: m.score,
    strengths: m.strengths ?? [],
    gaps: m.gaps ?? [],
    summary: m.summary ?? null,
    keywords: m.keywords ?? [],
  };
}

export default async function JobDetailPage({ params }: { params: Params }) {
  const { id } = await params;

  let job: (Job & { match?: unknown; match_analysis?: unknown }) | null = null;
  let loadError: string | null = null;
  let missing = false;

  try {
    job = await endpoints.job(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      missing = true;
    } else {
      loadError = err instanceof Error ? err.message : "Unknown error";
    }
  }

  if (missing) notFound();
  if (loadError || !job) {
    return (
      <ErrorState title="Failed to load job" message={loadError ?? "Unknown error"} />
    );
  }

  const match = asMatch(job.match ?? job.match_analysis);

  return (
    <div>
      <PageHeader
        title={job.title}
        description={`${job.company}${job.location ? ` · ${job.location}` : ""}`}
        actions={
          <Link href="/jobs" className="btn-secondary">
            Back to jobs
          </Link>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <StatusBadge status={job.status} />
        <span className="text-[var(--muted)]">
          Match {formatPercent(job.match_score ?? match?.score)}
        </span>
        <span className="text-[var(--muted)]">
          Posted {formatDate(job.posted_at ?? job.created_at)}
        </span>
        {job.url ? (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            className="text-[var(--accent)] hover:underline"
          >
            Source listing
          </a>
        ) : null}
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <Panel title="Description" className="lg:col-span-2">
          {job.description ? (
            <div className="prose-dense whitespace-pre-wrap text-[var(--fg)]">
              {job.description}
            </div>
          ) : (
            <EmptyState title="No description" description="Listing body not available." />
          )}
        </Panel>
        <Panel title="Match analysis">
          {match ? (
            <div className="space-y-3 text-sm">
              <p className="font-serif text-3xl font-semibold">
                {formatPercent(match.score)}
              </p>
              {match.summary ? (
                <p className="text-[var(--muted)]">{match.summary}</p>
              ) : null}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Strengths
                </p>
                <ul className="mt-1 list-disc pl-4">
                  {(match.strengths.length ? match.strengths : ["—"]).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Gaps
                </p>
                <ul className="mt-1 list-disc pl-4">
                  {(match.gaps.length ? match.gaps : ["—"]).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <EmptyState
              title="No match analysis"
              description="Run matching to populate score, strengths, and gaps."
            />
          )}
        </Panel>
      </div>
    </div>
  );
}
