import type { Metadata } from "next";
import { SettingsForm } from "@/components/settings/SettingsForm";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Settings } from "@/lib/types";

export const metadata: Metadata = {
  title: "Settings",
};

const defaults: Settings = {
  daily_target: 5,
  auto_submit: false,
  require_approval: true,
  remote_only: false,
  min_match_score: 70,
  notification_email: null,
};

export default async function SettingsPage() {
  let settings = defaults;
  let error: string | null = null;

  try {
    settings = await endpoints.settings();
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load settings";
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Targets, approval gates, and matching thresholds."
      />
      {error ? (
        <div className="mb-3">
          <ErrorState
            title="Using defaults (API unavailable)"
            message={error}
          />
        </div>
      ) : null}
      <SettingsForm initial={settings} />
    </div>
  );
}
