import { apiFetch, apiGet, apiPost, apiPut } from "./api";
import type {
  Application,
  Contact,
  DashboardStats,
  HealthStatus,
  Job,
  OutreachMessage,
  Paginated,
  Profile,
  QueueInfo,
  ReadyStatus,
  ResearchNote,
  ResumeSummary,
  Run,
  Settings,
  WorkerInfo,
} from "./types";

export type RecentJobMatch = {
  rank: number;
  role: string;
  company: string;
  posted: string;
  source: string;
  fit_score: number;
  apply_link: string;
  location?: string | null;
  applicant_count?: number | null;
};

export const endpoints = {
  dashboardStats: () => apiGet<DashboardStats>("/api/dashboard/stats"),
  recentJobMatches: (regions: string[], postedWithinHours: number) =>
    apiPost<RecentJobMatch[]>("/api/jobs/eea-search", {
      query: "software engineer",
      limit: 10,
      sources: ["linkedin_apify"],
      regions,
      posted_within_hours: postedWithinHours,
    }),
  jobs: (query = "") =>
    apiGet<Paginated<Job> | Job[]>(`/api/jobs${query ? `?${query}` : ""}`),
  job: (id: string) => apiGet<Job & { match?: unknown }>(`/api/jobs/${id}`),
  applications: (query = "") =>
    apiGet<Paginated<Application> | Application[]>(
      `/api/applications${query ? `?${query}` : ""}`,
    ),
  application: (id: string) => apiGet<Application>(`/api/applications/${id}`),
  prepareApplication: (id: string) =>
    apiPost<Application>(`/api/applications/${id}/prepare`),
  approveApplication: (id: string) =>
    apiPost<Application>(`/api/applications/${id}/approve`),
  submitApplication: (id: string) =>
    apiPost<Application>(`/api/applications/${id}/submit`),
  profile: () => apiGet<Profile>("/api/profile"),
  updateProfile: (body: Partial<Profile>) => apiPut<Profile>("/api/profile", body),
  settings: () => apiGet<Settings>("/api/settings"),
  updateSettings: (body: Partial<Settings>) =>
    apiPut<Settings>("/api/settings", body),
  runs: () => apiGet<Paginated<Run> | Run[]>("/api/runs"),
  health: () => apiGet<HealthStatus>("/api/health"),
  ready: () => apiGet<ReadyStatus>("/api/ready"),
  queues: () => apiGet<QueueInfo[]>("/api/dev/queues").catch(() => [] as QueueInfo[]),
  workers: () =>
    apiGet<WorkerInfo[]>("/api/dev/workers").catch(() => [] as WorkerInfo[]),
  contacts: () => apiGet<Paginated<Contact> | Contact[]>("/api/contacts"),
  resumes: () => apiGet<Paginated<ResumeSummary> | ResumeSummary[]>("/api/resumes"),
  uploadResume: (body: FormData) =>
    apiFetch<ResumeSummary>("/api/resumes", { method: "POST", body }),
  research: () => apiGet<Paginated<ResearchNote> | ResearchNote[]>("/api/research"),
  outreach: () =>
    apiGet<Paginated<OutreachMessage> | OutreachMessage[]>("/api/outreach"),
  approveOutreach: (id: string) =>
    apiPost<OutreachMessage>(`/api/outreach/${id}/approve`),
  sendOutreach: (id: string) => apiPost<OutreachMessage>(`/api/outreach/${id}/send`),
};

export function asList<T>(data: Paginated<T> | T[] | null | undefined): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return data.items ?? [];
}
