"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/Toast";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Settings } from "@/lib/types";

export function SettingsForm({ initial }: { initial: Settings }) {
  const router = useRouter();
  const toast = useToast();
  const [dailyTarget, setDailyTarget] = useState(initial.daily_target);
  const [autoSubmit, setAutoSubmit] = useState(initial.auto_submit);
  const [requireApproval, setRequireApproval] = useState(initial.require_approval);
  const [remoteOnly, setRemoteOnly] = useState(Boolean(initial.remote_only));
  const [minMatch, setMinMatch] = useState(initial.min_match_score ?? 0);
  const [notificationEmail, setNotificationEmail] = useState(
    initial.notification_email ?? "",
  );
  const [saving, setSaving] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await endpoints.updateSettings({
        daily_target: dailyTarget,
        auto_submit: autoSubmit,
        require_approval: requireApproval,
        remote_only: remoteOnly,
        min_match_score: minMatch,
        notification_email: notificationEmail || null,
      });
      toast.success("Settings saved");
      router.refresh();
    } catch (err) {
      toast.error(
        "Save failed",
        err instanceof ApiError || err instanceof Error ? err.message : undefined,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="max-w-xl space-y-4 rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
    >
      <div>
        <label htmlFor="daily_target" className="label">
          Daily target
        </label>
        <input
          id="daily_target"
          type="number"
          min={0}
          className="input"
          value={dailyTarget}
          onChange={(e) => setDailyTarget(Number(e.target.value))}
        />
      </div>
      <div>
        <label htmlFor="min_match" className="label">
          Minimum match score
        </label>
        <input
          id="min_match"
          type="number"
          min={0}
          max={100}
          className="input"
          value={minMatch}
          onChange={(e) => setMinMatch(Number(e.target.value))}
        />
      </div>
      <div>
        <label htmlFor="notification_email" className="label">
          Notification email
        </label>
        <input
          id="notification_email"
          type="email"
          className="input"
          value={notificationEmail}
          onChange={(e) => setNotificationEmail(e.target.value)}
        />
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={autoSubmit}
          onChange={(e) => setAutoSubmit(e.target.checked)}
        />
        Auto-submit approved applications
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={requireApproval}
          onChange={(e) => setRequireApproval(e.target.checked)}
        />
        Require human approval before submit
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={remoteOnly}
          onChange={(e) => setRemoteOnly(e.target.checked)}
        />
        Remote-only roles
      </label>
      <button type="submit" className="btn-primary" disabled={saving}>
        {saving ? "Saving…" : "Save settings"}
      </button>
    </form>
  );
}
