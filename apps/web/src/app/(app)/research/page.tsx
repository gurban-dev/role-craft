import type { Metadata } from "next";
import { DataTable, type Column } from "@/components/DataTable";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { ApiError, apiGet } from "@/lib/api";
import { asList } from "@/lib/endpoints";
import type { Paginated, ResearchNote } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Research",
};

export default async function ResearchPage() {
  let notes: ResearchNote[] = [];
  let error: string | null = null;

  try {
    notes = asList(
      await apiGet<Paginated<ResearchNote> | ResearchNote[]>("/api/research").catch(
        async () => [] as ResearchNote[],
      ),
    );
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
