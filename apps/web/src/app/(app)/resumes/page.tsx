import type { Metadata } from "next";
import { DataTable, type Column } from "@/components/DataTable";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { ResumeSummary } from "@/lib/types";

export const metadata: Metadata = {
  title: "Resumes",
};

export default async function ResumesPage() {
  let resumes: ResumeSummary[] = [];
  let error: string | null = null;

  try {
    const raw = asList(await endpoints.resumes());
    resumes = raw.map((r) => ({
      id: r.id,
      name: (r as ResumeSummary & { kind?: string }).name
        ?? (r as { kind?: string }).kind
        ?? "Resume",
      version: (r as { version?: string | number | null }).version?.toString() ?? null,
      tailored: (r as { kind?: string }).kind === "TAILORED",
      file_url: (r as { file_path?: string | null }).file_path ?? null,
    }));
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load resumes";
  }

  const columns: Column<ResumeSummary>[] = [
    { key: "name", header: "Name", render: (row) => row.name },
    { key: "version", header: "Version", render: (row) => row.version ?? "—" },
    {
      key: "tailored",
      header: "Tailored",
      render: (row) => (row.tailored ? "Yes" : "No"),
    },
    {
      key: "file",
      header: "File",
      render: (row) =>
        row.file_url ? (
          <a
            href={row.file_url}
            className="text-[var(--accent)] hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            Download
          </a>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Resumes"
        description="Base and tailored resume variants used by the pipeline."
      />
      {error ? <ErrorState title="Could not load resumes" message={error} /> : null}
      {resumes.length === 0 && !error ? (
        <EmptyState
          title="No resumes"
          description="Upload or generate resumes from settings / prepare flows."
        />
      ) : (
        <DataTable columns={columns} rows={resumes} rowKey={(r) => r.id} />
      )}
    </div>
  );
}
