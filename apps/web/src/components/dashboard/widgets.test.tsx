import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DailyTargetWidget } from "@/components/dashboard/widgets";
import type { DashboardStats } from "@/lib/types";

const stats: DashboardStats = {
  daily_target: 10,
  submitted_today: 4,
  pipeline: {
    draft: 1,
    ready: 2,
    awaiting_approval: 1,
    submitting: 0,
    submitted: 4,
    failed: 0,
    needs_human: 1,
  },
  human_action_queue: [],
};

describe("DailyTargetWidget", () => {
  it("renders progress against the daily target", () => {
    render(<DailyTargetWidget stats={stats} />);
    expect(screen.getByTestId("daily-target-widget")).toBeInTheDocument();
    expect(screen.getByText("Daily target")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("/ 10")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "40");
  });
});
