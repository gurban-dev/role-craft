"use client";

import { useRouter } from "next/navigation";
import { useRef, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

export function ResumeUpload() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a resume file first.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("Resume files must be 10 MB or smaller.");
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
      setFile(null);
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
    <form className="mb-5 rounded-xl border border-[var(--border)] p-4" onSubmit={onSubmit}>
      <h2 className="font-semibold">Upload a resume</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        PDF, DOCX, or UTF-8 text. Files are stored with your account (up to 10 MB).
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setError(null);
            setSuccess(null);
          }}
          disabled={pending}
          aria-label="Choose resume file"
        />
        <button type="submit" className="btn-primary" disabled={pending || !file}>
          {pending ? "Uploading…" : "Upload resume"}
        </button>
      </div>
      {error ? <p className="mt-3 text-sm text-red-600" role="alert">{error}</p> : null}
      {success ? <p className="mt-3 text-sm text-green-700" role="status">{success}</p> : null}
    </form>
  );
}
