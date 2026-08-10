import type { Metadata } from "next";
import { DataTable, type Column } from "@/components/DataTable";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui";
import { ApiError, apiGet } from "@/lib/api";
import type { Contact, Paginated } from "@/lib/types";
import { asList } from "@/lib/endpoints";

export const metadata: Metadata = {
  title: "Contacts",
};

export default async function ContactsPage() {
  let contacts: Contact[] = [];
  let error: string | null = null;

  try {
    contacts = asList(
      await apiGet<Paginated<Contact> | Contact[]>("/api/contacts").catch(async () => {
        // Soft-fallback when contacts endpoint is not yet available
        return [] as Contact[];
      }),
    );
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load contacts";
  }

  const columns: Column<Contact>[] = [
    {
      key: "name",
      header: "Name",
      render: (row) => (
        <div>
          <div className="font-medium">{row.name}</div>
          <div className="text-xs text-[var(--muted)]">{row.title ?? "—"}</div>
        </div>
      ),
    },
    { key: "company", header: "Company", render: (row) => row.company ?? "—" },
    { key: "email", header: "Email", render: (row) => row.email ?? "—" },
    {
      key: "linkedin",
      header: "LinkedIn",
      render: (row) =>
        row.linkedin_url ? (
          <a
            href={row.linkedin_url}
            className="text-[var(--accent)] hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            Profile
          </a>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Contacts"
        description="Hiring managers and referrals linked to applications."
      />
      {error ? <ErrorState title="Could not load contacts" message={error} /> : null}
      {contacts.length === 0 && !error ? (
        <EmptyState
          title="No contacts yet"
          description="Contacts appear as applications are prepared."
        />
      ) : (
        <DataTable columns={columns} rows={contacts} rowKey={(r) => r.id} />
      )}
    </div>
  );
}
