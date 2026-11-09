"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export function ResumeUpload() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function uploadFile(file: File) {
    if (file.size > MAX_FILE_SIZE) {
      setError("Resume files must be 10 MB or smaller.");
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    const body = new FormData();
    body.append("file", file);
    setPending(true);
    setError(null);
    setSuccess(null);
    try {
      const resume = await endpoints.uploadResume(body);
      setSuccess(`${resume.original_filename ?? file.name} was saved to your account.`);
      if (inputRef.current) inputRef.current.value = "";
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : cause instanceof Error
            ? cause.message
            : "Resume upload failed.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mb-5 rounded-xl border border-[var(--border)] p-4">
      <h2 className="font-semibold">Upload a resume</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        PDF, DOC, DOCX, or UTF-8 text. Files are stored with your account (up to 10 MB).
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          onChange={(event) => {
            setError(null);
            setSuccess(null);
            const selected = event.target.files?.[0];
            if (!selected) return;
            if (!/\.(pdf|doc|docx|txt)$/i.test(selected.name)) {
              setError("Unsupported file type. Choose a PDF, DOC, DOCX, or TXT resume.");
              event.target.value = "";
              return;
            }
            void uploadFile(selected);
          }}
          disabled={pending}
          aria-label="Choose resume file"
        />
        <button
          type="button"
          className="btn-primary resume-upload-button !cursor-pointer"
          disabled={pending}
          onClick={() => {
            if (inputRef.current) {
              inputRef.current.value = "";
              inputRef.current.click();
            }
          }}
        >
          {pending ? "Uploading…" : "Upload Resume"}
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-600" role="alert">{error}</p> : null}
      {success ? <p className="mt-3 text-sm text-green-700" role="status">{success}</p> : null}
    </section>
  );
}
