import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecentMatchSearch } from "@/components/dashboard/RecentMatchSearch";

vi.mock("@/lib/endpoints", () => ({
  endpoints: {
    recentJobMatches: vi.fn(),
  },
}));

import { endpoints } from "@/lib/endpoints";

describe("RecentMatchSearch", () => {
  beforeEach(() => {
    vi.mocked(endpoints.recentJobMatches).mockReset();
  });

  it("shows only the scored job table after search", async () => {
    vi.mocked(endpoints.recentJobMatches).mockResolvedValue([
      {
        rank: 1,
        role: "Software Engineer",
        company: "Acme",
        posted: "2026-11-06T22:00:00Z",
        source: "Google",
        fit_score: 8.2,
        apply_link: "https://careers.acme.example/jobs/1",
      },
    ]);

    render(<RecentMatchSearch />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Asia" }));
    await userEvent.click(screen.getByTestId("recent-match-search"));
    expect(endpoints.recentJobMatches).toHaveBeenCalledWith(["Europe", "Asia"]);

    expect(await screen.findByTestId("recent-match-table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "#" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Role" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Company" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Posted" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Source" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Fit Score" })).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Apply Link On Company Website" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Software Engineer")).toBeInTheDocument();
    expect(screen.getByText("8.2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "https://careers.acme.example/jobs/1" })).toHaveAttribute(
      "href",
      "https://careers.acme.example/jobs/1",
    );
  });
});
