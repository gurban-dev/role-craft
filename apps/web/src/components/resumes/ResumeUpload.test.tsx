import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ResumeUpload } from "@/components/resumes/ResumeUpload";
import type { ResumeSummary } from "@/lib/types";

const { uploadResume, refresh } = vi.hoisted(() => ({
  uploadResume: vi.fn(),
  refresh: vi.fn(),
}));

vi.mock("@/lib/endpoints", () => ({ endpoints: { uploadResume } }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

describe("ResumeUpload", () => {
  afterEach(cleanup);

  beforeEach(() => {
    uploadResume.mockReset();
    refresh.mockReset();
  });

  it("opens the native picker and does nothing when selection is cancelled", async () => {
    const user = userEvent.setup();
    render(<ResumeUpload />);
    const input = screen.getByLabelText("Choose resume file") as HTMLInputElement;
    const picker = vi.spyOn(input, "click").mockImplementation(() => {});

    await user.click(screen.getByRole("button", { name: "Upload Resume" }));

    expect(picker).toHaveBeenCalledOnce();
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it.each(["pdf", "doc", "docx", "txt"])(
    "uploads a selected .%s file and reports success",
    async (extension) => {
      const user = userEvent.setup();
      uploadResume.mockResolvedValue({ original_filename: `resume.${extension}` } as ResumeSummary);
      render(<ResumeUpload />);

      await user.upload(
        screen.getByLabelText("Choose resume file"),
        new File(["resume content"], `resume.${extension}`, { type: "application/octet-stream" }),
      );

      await waitFor(() => expect(uploadResume).toHaveBeenCalledOnce());
      expect(uploadResume.mock.calls[0]?.[0]).toBeInstanceOf(FormData);
      expect(await screen.findByRole("status")).toHaveTextContent(
        `resume.${extension} was saved to your account.`,
      );
      expect(refresh).toHaveBeenCalledOnce();
    },
  );

  it("rejects unsupported files without sending them to the API", async () => {
    const user = userEvent.setup({ applyAccept: false });
    render(<ResumeUpload />);

    await user.upload(
      screen.getByLabelText("Choose resume file"),
      new File(["data"], "resume.rtf", { type: "application/rtf" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Unsupported file type");
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it("rejects files larger than 10 MB without sending them", async () => {
    const user = userEvent.setup();
    render(<ResumeUpload />);
    const large = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.pdf");

    await user.upload(screen.getByLabelText("Choose resume file"), large);

    expect(await screen.findByRole("alert")).toHaveTextContent("10 MB or smaller");
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it("shows upload errors returned by the API", async () => {
    const user = userEvent.setup();
    uploadResume.mockRejectedValue(new Error("Network unavailable"));
    render(<ResumeUpload />);

    await user.upload(
      screen.getByLabelText("Choose resume file"),
      new File(["resume content"], "resume.txt", { type: "text/plain" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
  });
});
