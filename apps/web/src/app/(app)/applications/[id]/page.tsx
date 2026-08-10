import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ApplicationActions } from "@/components/applications/ApplicationActions";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState, ErrorState, PageHeader, Panel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Application } from "@/lib/types";
import { formatDate, formatPercent } from "@/lib/utils";

type Params = Promise<{ id: string }>;

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { id } = await params;
  return { title: `Application ${id}` };
}

export default async function ApplicationDetailPage({
  params,
}: {
  params: Params;
}) {
  const { id } = await params;

  let app: Application | null = null;
  let loadError: string | null = null;
  let missing = false;

  try {
    app = await endpoints.application(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      missing = true;
    } else {
      loadError = err instanceof Error ? err.message : "Unknown error";
    }
  }

  if (missing) notFound();
  if (loadError || !app) {
    return (
      <ErrorState
        title="Failed to load application"
        message={loadError ?? "Unknown error"}
      />
    );
  }

  const title = app.job?.title ?? `Application ${app.id.slice(0, 8)}`;
  const company = app.job?.company ?? "Unknown company";

  return (
    <div>
      <PageHeader
        title={title}
        description={company}
        actions={
          <>
            <Link href="/applications" className="btn-secondary">
              Back
            </Link>
            <ApplicationActions applicationId={app.id} status={app.status} />
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
        <StatusBadge status={app.status} />
        <span className="text-[var(--muted)]">
          Match {formatPercent(app.match_score ?? app.match?.score)}
        </span>
        <span className="text-[var(--muted)]">
          Updated {formatDate(app.updated_at ?? app.created_at)}
        </span>
        {app.job_id ? (
          <Link
            href={`/jobs/${app.job_id}`}
            className="text-[var(--accent)] hover:underline"
          >
            View job
          </Link>
        ) : null}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Job">
          {app.job ? (
            <div className="space-y-1 text-sm">
              <p className="font-medium">{app.job.title}</p>
              <p className="text-[var(--muted)]">{app.job.company}</p>
              <p className="text-[var(--muted)]">
                {app.job.location || (app.job.remote ? "Remote" : "—")}
              </p>
            </div>
          ) : (
            <EmptyState title="Job missing" />
          )}
        </Panel>

        <Panel title="Match">
          {app.match ? (
            <div className="space-y-2 text-sm">
              <p className="font-serif text-2xl font-semibold">
                {formatPercent(app.match.score)}
              </p>
              {app.match.summary ? <p>{app.match.summary}</p> : null}
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <p className="text-xs uppercase text-[var(--muted)]">Strengths</p>
                  <ul className="list-disc pl-4">
                    {(app.match.strengths.length ? app.match.strengths : ["—"]).map(
                      (s) => (
                        <li key={s}>{s}</li>
                      ),
                    )}
                  </ul>
                </div>
                <div>
                  <p className="text-xs uppercase text-[var(--muted)]">Gaps</p>
                  <ul className="list-disc pl-4">
                    {(app.match.gaps.length ? app.match.gaps : ["—"]).map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title="No match data" />
          )}
        </Panel>

        <Panel title="Resume">
          {app.resume ? (
            <div className="text-sm">
              <p className="font-medium">{app.resume.name}</p>
              <p className="text-[var(--muted)]">
                {app.resume.version ?? "v1"}
                {app.resume.tailored ? " · tailored" : ""}
              </p>
              {app.resume.file_url ? (
                <a
                  href={app.resume.file_url}
                  className="mt-2 inline-block text-[var(--accent)] hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open file
                </a>
              ) : null}
            </div>
          ) : (
            <EmptyState title="No resume attached" />
          )}
        </Panel>

        <Panel title="Contact">
          {app.contact ? (
            <div className="space-y-1 text-sm">
              <p className="font-medium">{app.contact.name}</p>
              <p className="text-[var(--muted)]">{app.contact.title}</p>
              <p className="text-[var(--muted)]">{app.contact.email ?? "—"}</p>
              {app.contact.linkedin_url ? (
                <a
                  href={app.contact.linkedin_url}
                  className="text-[var(--accent)] hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  LinkedIn
                </a>
              ) : null}
            </div>
          ) : (
            <EmptyState title="No contact" />
          )}
        </Panel>

        <Panel title="Research">
          {app.research ? (
            <div className="space-y-2 text-sm">
              <p className="font-medium">{app.research.company}</p>
              <p className="text-[var(--muted)]">{app.research.summary ?? "—"}</p>
              {app.research.highlights?.length ? (
                <ul className="list-disc pl-4">
                  {app.research.highlights.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <EmptyState title="No research notes" />
          )}
        </Panel>

        <Panel title="Outreach">
          {app.outreach ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <StatusBadge status={app.outreach.status ?? "draft"} />
                <span className="text-[var(--muted)]">{app.outreach.channel}</span>
              </div>
              {app.outreach.subject ? (
                <p className="font-medium">{app.outreach.subject}</p>
              ) : null}
              <p className="whitespace-pre-wrap text-[var(--muted)]">
                {app.outreach.body ?? "—"}
              </p>
            </div>
          ) : (
            <EmptyState title="No outreach draft" />
          )}
        </Panel>

        <Panel title="Automation" className="lg:col-span-2">
          {app.automation ? (
            <div className="grid gap-2 text-sm sm:grid-cols-3">
              <div>
                <p className="text-xs uppercase text-[var(--muted)]">Status</p>
                <StatusBadge status={app.automation.status} />
              </div>
              <div>
                <p className="text-xs uppercase text-[var(--muted)]">Last step</p>
                <p>{app.automation.last_step ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-[var(--muted)]">Updated</p>
                <p>{formatDate(app.automation.updated_at)}</p>
              </div>
              {app.automation.error ? (
                <p className="sm:col-span-3 text-[var(--danger)]">{app.automation.error}</p>
              ) : null}
            </div>
          ) : (
            <EmptyState title="No automation state" />
          )}
        </Panel>
      </div>
    </div>
  );
}
