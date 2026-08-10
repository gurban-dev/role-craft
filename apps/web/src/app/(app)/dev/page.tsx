import type { Metadata } from "next";
import { StatusBadge } from "@/components/StatusBadge";
import { DataTable, type Column } from "@/components/DataTable";
import { EmptyState, ErrorState, PageHeader, Panel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { asList, endpoints } from "@/lib/endpoints";
import type { HealthStatus, QueueInfo, ReadyStatus, Run, WorkerInfo } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Developer health",
};

export default async function DevPage() {
  let health: HealthStatus | null = null;
  let ready: ReadyStatus | null = null;
  let runs: Run[] = [];
  let queues: QueueInfo[] = [];
  let workers: WorkerInfo[] = [];
  const errors: string[] = [];

  async function load<T>(label: string, fn: () => Promise<T>): Promise<T | null> {
    try {
      return await fn();
    } catch (err) {
      errors.push(
        `${label}: ${err instanceof ApiError || err instanceof Error ? err.message : "failed"}`,
      );
      return null;
    }
  }

  health = await load("health", () => endpoints.health());
  ready = await load("ready", () => endpoints.ready());
  runs = asList((await load("runs", () => endpoints.runs())) ?? []);
  queues = (await load("queues", () => endpoints.queues())) ?? [];
  workers = (await load("workers", () => endpoints.workers())) ?? [];

  const queueColumns: Column<QueueInfo>[] = [
    { key: "name", header: "Queue", render: (r) => r.name },
    { key: "pending", header: "Pending", render: (r) => r.pending },
    { key: "active", header: "Active", render: (r) => r.active },
    { key: "failed", header: "Failed", render: (r) => r.failed },
  ];

  const workerColumns: Column<WorkerInfo>[] = [
    { key: "name", header: "Worker", render: (r) => r.name || r.id },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "seen",
      header: "Last seen",
      render: (r) => formatDate(r.last_seen),
    },
  ];

  const runColumns: Column<Run>[] = [
    { key: "kind", header: "Kind", render: (r) => r.kind },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "started",
      header: "Started",
      render: (r) => formatDate(r.started_at),
    },
    {
      key: "message",
      header: "Message",
      className: "max-w-md",
      render: (r) => (
        <span className="line-clamp-2 text-[var(--muted)]">{r.message ?? "—"}</span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Developer health"
        description="API readiness, recent runs, worker liveness, and queue depth."
      />

      {errors.length > 0 ? (
        <div className="mb-3">
          <ErrorState title="Some probes failed" message={errors.join(" · ")} />
        </div>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <Panel title="Health">
          {health ? (
            <div className="flex items-center gap-3 text-sm">
              <StatusBadge status={health.status} />
              <span className="text-[var(--muted)]">
                {health.version ? `v${health.version}` : "no version"}
              </span>
              {health.detail ? <span>{health.detail}</span> : null}
            </div>
          ) : (
            <EmptyState title="Health endpoint unavailable" />
          )}
        </Panel>
        <Panel title="Ready">
          {ready ? (
            <div className="space-y-2 text-sm">
              <StatusBadge status={ready.ready ? "ok" : "down"} />
              {ready.checks ? (
                <ul className="mt-2 space-y-1">
                  {Object.entries(ready.checks).map(([k, v]) => (
                    <li key={k} className="flex justify-between gap-2">
                      <span className="text-[var(--muted)]">{k}</span>
                      <span className="font-mono text-xs">{String(v)}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <EmptyState title="Ready endpoint unavailable" />
          )}
        </Panel>
      </div>

      <div className="mt-3">
        <Panel title="Recent runs">
          <DataTable
            columns={runColumns}
            rows={runs}
            rowKey={(r) => r.id}
            emptyTitle="No runs"
            emptyDescription="GET /api/runs will populate this table."
          />
        </Panel>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <Panel title="Queues">
          <DataTable
            columns={queueColumns}
            rows={queues}
            rowKey={(r) => r.name}
            emptyTitle="No queue data"
            emptyDescription="Expose GET /api/dev/queues from the API for live depth."
          />
        </Panel>
        <Panel title="Workers">
          <DataTable
            columns={workerColumns}
            rows={workers}
            rowKey={(r) => r.id}
            emptyTitle="No workers reported"
            emptyDescription="Expose GET /api/dev/workers for worker heartbeats."
          />
        </Panel>
      </div>
    </div>
  );
}
