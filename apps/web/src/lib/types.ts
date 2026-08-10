export type User = {
  id: string;
  email: string;
  name: string;
};

export type Profile = {
  id: string;
  user_id: string;
  name: string;
  email: string;
  headline?: string | null;
  location?: string | null;
  linkedin_url?: string | null;
  phone?: string | null;
  summary?: string | null;
  skills?: string[];
  updated_at?: string;
};

export type JobStatus =
  | "new"
  | "matched"
  | "queued"
  | "applying"
  | "applied"
  | "rejected"
  | "archived";

export type Job = {
  id: string;
  title: string;
  company: string;
  location?: string | null;
  remote?: boolean;
  url?: string | null;
  source?: string | null;
  status: JobStatus;
  salary_min?: number | null;
  salary_max?: number | null;
  posted_at?: string | null;
  description?: string | null;
  match_score?: number | null;
  created_at?: string;
  updated_at?: string;
};

export type MatchAnalysis = {
  score: number;
  strengths: string[];
  gaps: string[];
  summary?: string | null;
  keywords?: string[];
};

export type ApplicationStatus =
  | "draft"
  | "preparing"
  | "ready"
  | "awaiting_approval"
  | "approved"
  | "submitting"
  | "submitted"
  | "failed"
  | "needs_human"
  | "cancelled";

export type Application = {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  match_score?: number | null;
  created_at?: string;
  updated_at?: string;
  submitted_at?: string | null;
  job?: Job | null;
  match?: MatchAnalysis | null;
  resume?: ResumeSummary | null;
  contact?: Contact | null;
  research?: ResearchNote | null;
  outreach?: OutreachMessage | null;
  automation?: AutomationState | null;
};

export type ResumeSummary = {
  id: string;
  name: string;
  version?: string | null;
  tailored?: boolean;
  file_url?: string | null;
};

export type Contact = {
  id: string;
  name: string;
  email?: string | null;
  title?: string | null;
  company?: string | null;
  linkedin_url?: string | null;
  notes?: string | null;
};

export type ResearchNote = {
  id: string;
  company: string;
  summary?: string | null;
  highlights?: string[];
  sources?: string[];
  updated_at?: string;
};

export type OutreachMessage = {
  id: string;
  channel: "email" | "linkedin" | "other";
  subject?: string | null;
  body?: string | null;
  status?: "draft" | "sent" | "failed";
  sent_at?: string | null;
};

export type AutomationState = {
  status: string;
  last_step?: string | null;
  error?: string | null;
  requires_human?: boolean;
  updated_at?: string;
};

export type Settings = {
  daily_target: number;
  auto_submit: boolean;
  require_approval: boolean;
  preferred_locations?: string[];
  remote_only?: boolean;
  min_match_score?: number;
  notification_email?: string | null;
};

export type DashboardStats = {
  daily_target: number;
  submitted_today: number;
  pipeline: {
    draft: number;
    ready: number;
    awaiting_approval: number;
    submitting: number;
    submitted: number;
    failed: number;
    needs_human: number;
  };
  human_action_queue: Array<{
    id: string;
    application_id: string;
    job_title: string;
    company: string;
    reason: string;
    created_at: string;
  }>;
  match_avg?: number | null;
  active_jobs?: number;
};

export type Run = {
  id: string;
  kind: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  started_at?: string | null;
  finished_at?: string | null;
  message?: string | null;
  meta?: Record<string, unknown>;
};

export type HealthStatus = {
  status: "ok" | "degraded" | "down" | string;
  version?: string;
  detail?: string;
};

export type ReadyStatus = {
  ready: boolean;
  checks?: Record<string, boolean | string>;
};

export type QueueInfo = {
  name: string;
  pending: number;
  active: number;
  failed: number;
};

export type WorkerInfo = {
  id: string;
  name: string;
  status: "idle" | "busy" | "offline" | string;
  last_seen?: string | null;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
};

export type ApiErrorBody = {
  detail?: string | { msg: string }[] | Record<string, unknown>;
  message?: string;
};
