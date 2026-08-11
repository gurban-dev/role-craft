import type { Metadata } from "next";
import { DataTable, type Column } from "@/components/DataTable";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { ResearchNote } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Research",
};

export default async function ResearchPage() {
  let notes: ResearchNote[] = [];
  let error: string | null = null;

  try {
    const raw = asList(await endpoints.research());
    notes = raw.map((r) => ({
      id: r.id,
      company: r.company,
      summary:
        (r as ResearchNote).summary
        ?? (r as { problem_summary?: string }).problem_summary
        ?? null,
      highlights: (r as ResearchNote).highlights
        ?? ((r as { evidence?: { claim?: string }[] }).evidence ?? []).map(
          (e) => e.claim ?? "",
        ).filter(Boolean),
      sources: (r as ResearchNote).sources ?? (r as { sources?: string[] }).sources ?? [],
      updated_at: (r as ResearchNote).updated_at
        ?? (r as { created_at?: string }).created_at,
    }));
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load research";
  }

  const columns: Column<ResearchNote>[] = [
    { key: "company", header: "Company", render: (row) => row.company },
    {
      key: "summary",
      header: "Summary",
      className: "max-w-xl",
      render: (row) => (
        <span className="line-clamp-2 text-[var(--muted)]">{row.summary ?? "—"}</span>
      ),
    },
    {
      key: "updated",
      header: "Updated",
      render: (row) => formatDate(row.updated_at),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Research"
        description="Company briefs generated for outreach and applications."
      />
      {error ? <ErrorState title="Could not load research" message={error} /> : null}
      {notes.length === 0 && !error ? (
        <EmptyState
          title="No research notes"
          description="Research is created when applications are prepared."
        />
      ) : (
        <DataTable columns={columns} rows={notes} rowKey={(r) => r.id} />
      )}
    </div>
  );
}
