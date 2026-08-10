"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/Toast";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import type { Profile } from "@/lib/types";

export function ProfileForm({ initial }: { initial: Profile }) {
  const router = useRouter();
  const toast = useToast();
  const [name, setName] = useState(initial.name);
  const [headline, setHeadline] = useState(initial.headline ?? "");
  const [location, setLocation] = useState(initial.location ?? "");
  const [phone, setPhone] = useState(initial.phone ?? "");
  const [linkedin, setLinkedin] = useState(initial.linkedin_url ?? "");
  const [summary, setSummary] = useState(initial.summary ?? "");
  const [skills, setSkills] = useState((initial.skills ?? []).join(", "));
  const [saving, setSaving] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await endpoints.updateProfile({
        name,
        headline: headline || null,
        location: location || null,
        phone: phone || null,
        linkedin_url: linkedin || null,
        summary: summary || null,
        skills: skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      toast.success("Profile updated");
      router.refresh();
    } catch (err) {
      toast.error(
        "Update failed",
        err instanceof ApiError || err instanceof Error ? err.message : undefined,
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="max-w-2xl space-y-4 rounded-md border border-[var(--border)] bg-[var(--surface)] p-4"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="name" className="label">
            Name
          </label>
          <input
            id="name"
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="headline" className="label">
            Headline
          </label>
          <input
            id="headline"
            className="input"
            value={headline}
            onChange={(e) => setHeadline(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="location" className="label">
            Location
          </label>
          <input
            id="location"
            className="input"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="phone" className="label">
            Phone
          </label>
          <input
            id="phone"
            className="input"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label htmlFor="linkedin" className="label">
          LinkedIn URL
        </label>
        <input
          id="linkedin"
          className="input"
          value={linkedin}
          onChange={(e) => setLinkedin(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="skills" className="label">
          Skills (comma-separated)
        </label>
        <input
          id="skills"
          className="input"
          value={skills}
          onChange={(e) => setSkills(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="summary" className="label">
          Summary
        </label>
        <textarea
          id="summary"
          className="input min-h-28"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </div>
      <button type="submit" className="btn-primary" disabled={saving}>
        {saving ? "Saving…" : "Save profile"}
      </button>
    </form>
  );
}
