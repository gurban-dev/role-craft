import type { Metadata } from "next";
import { ProfileForm } from "@/components/profile/ProfileForm";
import { ErrorState, PageHeader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { endpoints } from "@/lib/endpoints";
import { getCurrentUser } from "@/lib/auth";
import type { Profile } from "@/lib/types";

export const metadata: Metadata = {
  title: "Profile",
};

export default async function ProfilePage() {
  const user = await getCurrentUser();
  let profile: Profile = {
    id: user?.id ?? "me",
    user_id: user?.id ?? "me",
    name: user?.name ?? "",
    email: user?.email ?? "",
  };
  let error: string | null = null;

  try {
    profile = await endpoints.profile();
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : "Failed to load profile";
  }

  return (
    <div>
      <PageHeader
        title="Profile"
        description="Candidate identity used for matching and outreach."
      />
      {error ? (
        <div className="mb-3">
          <ErrorState title="Could not load profile from API" message={error} />
        </div>
      ) : null}
      <p className="mb-3 text-sm text-[var(--muted)]">Account email: {profile.email}</p>
      <ProfileForm initial={profile} />
    </div>
  );
}
