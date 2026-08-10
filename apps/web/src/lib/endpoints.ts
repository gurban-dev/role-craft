import { apiGet, apiPost, apiPut } from "./api";
import type {
  Application,
  DashboardStats,
  HealthStatus,
  Job,
  Paginated,
  Profile,
  QueueInfo,
  ReadyStatus,
  Run,
  Settings,
  WorkerInfo,
} from "./types";

export const endpoints = {
  dashboardStats: () => apiGet<DashboardStats>("/api/dashboard/stats"),
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
};

export function asList<T>(data: Paginated<T> | T[] | null | undefined): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return data.items ?? [];
}
