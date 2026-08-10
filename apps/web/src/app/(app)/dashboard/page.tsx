import type { Metadata } from "next";
import {
  DailyTargetWidget,
  HumanActionQueueWidget,
  PipelineWidget,
  StatWidget,
} from "@/components/dashboard/widgets";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { DashboardStats } from "@/lib/types";

export const metadata: Metadata = {
  title: "Dashboard",
};

const emptyStats: DashboardStats = {
  daily_target: 0,
  submitted_today: 0,
  pipeline: {
    draft: 0,
    ready: 0,
    awaiting_approval: 0,
    submitting: 0,
    submitted: 0,
    failed: 0,
    needs_human: 0,
  },
  human_action_queue: [],
  active_jobs: 0,
};

export default async function DashboardPage() {
  let stats = emptyStats;
  let error: string | null = null;

  try {
    stats = await endpoints.dashboardStats();
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load dashboard";
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Daily throughput, pipeline health, and items waiting on you."
      />
      {error ? <ErrorState title="Dashboard unavailable" message={error} /> : null}
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <DailyTargetWidget stats={stats} />
        <StatWidget
          label="Submitted today"
          value={stats.submitted_today}
          hint="Applications marked submitted"
          tone="success"
        />
        <StatWidget
          label="Active jobs"
          value={stats.active_jobs ?? 0}
          hint="Jobs currently in scope"
        />
        <StatWidget
          label="Avg match"
          value={
            stats.match_avg == null
              ? "—"
              : `${Math.round(stats.match_avg <= 1 ? stats.match_avg * 100 : stats.match_avg)}%`
          }
          hint="Across open pipeline"
          tone="accent"
        />
      </div>
      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <PipelineWidget stats={stats} />
        <HumanActionQueueWidget stats={stats} />
      </div>
    </div>
  );
}
