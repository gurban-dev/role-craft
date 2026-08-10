import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type Column<T> = {
  key: string;
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle?: string;
  emptyDescription?: string;
  loading?: boolean;
  skeletonRows?: number;
  className?: string;
};

export function DataTableSkeleton({
  columns = 5,
  rows = 6,
}: {
  columns?: number;
  rows?: number;
}) {
  return (
    <div className="overflow-hidden rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <div className="border-b border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
        <div className="flex gap-4">
          {Array.from({ length: columns }).map((_, i) => (
            <div key={i} className="h-3 w-20 animate-pulse rounded bg-[var(--border)]" />
          ))}
        </div>
      </div>
      <div className="divide-y divide-[var(--border)]">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4 px-3 py-3">
            {Array.from({ length: columns }).map((_, c) => (
              <div
                key={c}
                className="h-3 flex-1 animate-pulse rounded bg-[var(--border)]/70"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyTitle = "No results",
  emptyDescription = "Nothing matches the current filters.",
  loading = false,
  skeletonRows = 6,
  className,
}: DataTableProps<T>) {
  if (loading) {
    return <DataTableSkeleton columns={columns.length} rows={skeletonRows} />;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[var(--border)] bg-[var(--surface)] px-4 py-10 text-center">
        <p className="text-sm font-medium text-[var(--fg)]">{emptyTitle}</p>
        <p className="mt-1 text-sm text-[var(--muted)]">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--surface)]",
        className,
      )}
    >
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className="bg-[var(--surface-2)] text-xs uppercase tracking-wide text-[var(--muted)]">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn("px-3 py-2 font-medium", col.className)}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="hover:bg-[var(--surface-2)]/70">
              {columns.map((col) => (
                <td key={col.key} className={cn("px-3 py-2 align-middle", col.className)}>
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
