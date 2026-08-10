"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useToast } from "@/components/Toast";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";

type Action = "prepare" | "approve" | "submit";

export function ApplicationActions({
  applicationId,
  status,
}: {
  applicationId: string;
  status: string;
}) {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState<Action | null>(null);
  const [confirm, setConfirm] = useState<Action | null>(null);

  async function run(action: Action) {
    setPending(action);
    try {
      if (action === "prepare") await endpoints.prepareApplication(applicationId);
      if (action === "approve") await endpoints.approveApplication(applicationId);
      if (action === "submit") await endpoints.submitApplication(applicationId);
      toast.success(`${action[0]!.toUpperCase()}${action.slice(1)} succeeded`);
      setConfirm(null);
      router.refresh();
    } catch (err) {
      toast.error(
        `${action} failed`,
        err instanceof ApiError || err instanceof Error ? err.message : undefined,
      );
    } finally {
      setPending(null);
    }
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-secondary"
          disabled={pending !== null}
          onClick={() => setConfirm("prepare")}
        >
          Prepare
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={pending !== null || status === "submitted"}
          onClick={() => setConfirm("approve")}
        >
          Approve
        </button>
        <button
          type="button"
          className="btn-primary"
          disabled={pending !== null || status === "submitted"}
          onClick={() => setConfirm("submit")}
        >
          Submit
        </button>
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={
          confirm === "submit"
            ? "Submit application?"
            : confirm === "approve"
              ? "Approve application?"
              : "Prepare application?"
        }
        description={
          confirm === "submit"
            ? "This will enqueue automation to submit the application."
            : confirm === "approve"
              ? "Marks the packet approved and ready for submission."
              : "Rebuilds resume, outreach, and research artifacts."
        }
        confirmLabel={confirm ? confirm[0]!.toUpperCase() + confirm.slice(1) : "Confirm"}
        busy={pending !== null}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm) void run(confirm);
        }}
      />
    </>
  );
}
