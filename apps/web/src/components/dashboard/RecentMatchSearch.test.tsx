import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RecentMatchSearch } from "@/components/dashboard/RecentMatchSearch";

vi.mock("@/lib/endpoints", () => ({
  endpoints: {
    recentJobMatches: vi.fn(),
  },
}));

import { endpoints } from "@/lib/endpoints";

describe("RecentMatchSearch", () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.mocked(endpoints.recentJobMatches).mockReset();
  });

  it("sends independent region arrangements and seniority to the search API", async () => {
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
    for (const region of ["North America", "South America", "Africa"]) {
      await userEvent.click(screen.getByRole("checkbox", { name: `Include ${region}` }));
    }
    for (const arrangement of ["In-person", "Hybrid"]) {
      await userEvent.click(screen.getByRole("checkbox", { name: `Europe ${arrangement}` }));
      await userEvent.click(screen.getByRole("checkbox", { name: `Asia ${arrangement}` }));
    }
    await userEvent.click(screen.getByRole("checkbox", { name: "Senior" }));
    await userEvent.click(screen.getByTestId("recent-match-search"));
    expect(endpoints.recentJobMatches).toHaveBeenCalledWith(
      ["Europe", "Asia"],
      24,
      true,
      true,
      {
        Europe: ["remote"],
        "North America": ["in_person", "remote", "hybrid"],
        "South America": ["in_person", "remote", "hybrid"],
        Asia: ["remote"],
        Africa: ["in_person", "remote", "hybrid"],
      },
    );

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

  it("sends independent seniority checkbox states, including an empty selection", async () => {
    vi.mocked(endpoints.recentJobMatches).mockResolvedValue([]);
    render(<RecentMatchSearch />);

    const nonSenior = screen.getByRole("checkbox", { name: "Non-senior" });
    const senior = screen.getByRole("checkbox", { name: "Senior" });
    const search = screen.getByTestId("recent-match-search");
    expect(screen.queryByRole("radio", { name: "Both" })).not.toBeInTheDocument();
    expect(nonSenior).toBeChecked();
    expect(senior).not.toBeChecked();

    const arrangements = {
      Europe: ["in_person", "remote", "hybrid"],
      "North America": ["in_person", "remote", "hybrid"],
      "South America": ["in_person", "remote", "hybrid"],
      Asia: ["in_person", "remote", "hybrid"],
      Africa: ["in_person", "remote", "hybrid"],
    };
    const regions = ["Europe", "North America", "South America", "Asia", "Africa"];

    await userEvent.click(search);
    expect(endpoints.recentJobMatches).toHaveBeenLastCalledWith(
      regions,
      24,
      true,
      false,
      arrangements,
    );

    await userEvent.click(nonSenior);
    await userEvent.click(senior);
    expect(nonSenior).not.toBeChecked();
    expect(senior).toBeChecked();
    await userEvent.click(search);
    expect(endpoints.recentJobMatches).toHaveBeenLastCalledWith(
      regions,
      24,
      false,
      true,
      arrangements,
    );

    await userEvent.click(nonSenior);
    expect(nonSenior).toBeChecked();
    expect(senior).toBeChecked();
    await userEvent.click(search);
    expect(endpoints.recentJobMatches).toHaveBeenLastCalledWith(
      regions,
      24,
      true,
      true,
      arrangements,
    );

    await userEvent.click(senior);
    expect(nonSenior).toBeChecked();
    expect(senior).not.toBeChecked();
    await userEvent.click(search);
    expect(endpoints.recentJobMatches).toHaveBeenLastCalledWith(
      regions,
      24,
      true,
      false,
      arrangements,
    );

    await userEvent.click(nonSenior);
    expect(nonSenior).not.toBeChecked();
    expect(senior).not.toBeChecked();
    await userEvent.click(search);
    expect(endpoints.recentJobMatches).toHaveBeenLastCalledWith(
      regions,
      24,
      false,
      false,
      arrangements,
    );
  });
});
