"""Domain enums and shared constants."""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    ANALYZING = "ANALYZING"
    MATCHED = "MATCHED"
    RESUME_GENERATING = "RESUME_GENERATING"
    RESUME_READY = "RESUME_READY"
    CONTACT_RESEARCH = "CONTACT_RESEARCH"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPLYING = "APPLYING"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    NEEDS_HUMAN_ACTION = "NEEDS_HUMAN_ACTION"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class MatchRecommendation(StrEnum):
    REJECTED = "REJECTED"
    LOW_MATCH = "LOW_MATCH"
    REVIEW = "REVIEW"
    STRONG_MATCH = "STRONG_MATCH"
    READY_TO_APPLY = "READY_TO_APPLY"


class ContactType(StrEnum):
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"
    TEAM_LEADER = "TEAM_LEADER"
    OTHER = "OTHER"


class JobStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"
    ARCHIVED = "ARCHIVED"


class AutomationTaskType(StrEnum):
    JOB_DISCOVERY = "JOB_DISCOVERY"
    JOB_ANALYSIS = "JOB_ANALYSIS"
    MATCH_SCORING = "MATCH_SCORING"
    RESUME_GENERATION = "RESUME_GENERATION"
    COMPANY_RESEARCH = "COMPANY_RESEARCH"
    CONTACT_DISCOVERY = "CONTACT_DISCOVERY"
    OUTREACH_GENERATION = "OUTREACH_GENERATION"
    APPLICATION_PREPARE = "APPLICATION_PREPARE"
    APPLICATION_SUBMIT = "APPLICATION_SUBMIT"
    DAILY_SCHEDULER = "DAILY_SCHEDULER"
    RETENTION_CLEANUP = "RETENTION_CLEANUP"


class AutomationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class OutreachStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT = "SENT"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"


class ResumeKind(StrEnum):
    CANONICAL = "CANONICAL"
    TAILORED = "TAILORED"


# Valid application state transitions
APPLICATION_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: {
        ApplicationStatus.ANALYZING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.ANALYZING: {
        ApplicationStatus.MATCHED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.MATCHED: {
        ApplicationStatus.RESUME_GENERATING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.RESUME_GENERATING: {
        ApplicationStatus.RESUME_READY,
        ApplicationStatus.FAILED,
        ApplicationStatus.NEEDS_HUMAN_ACTION,
    },
    ApplicationStatus.RESUME_READY: {
        ApplicationStatus.CONTACT_RESEARCH,
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.CONTACT_RESEARCH: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.NEEDS_HUMAN_ACTION,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.READY_FOR_REVIEW: {
        ApplicationStatus.APPLYING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.NEEDS_HUMAN_ACTION,
    },
    ApplicationStatus.APPLYING: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.NEEDS_HUMAN_ACTION,
    },
    ApplicationStatus.NEEDS_HUMAN_ACTION: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLYING,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    },
    ApplicationStatus.SUBMITTED: set(),
    ApplicationStatus.FAILED: {
        ApplicationStatus.READY_FOR_REVIEW,
        ApplicationStatus.APPLYING,
        ApplicationStatus.WITHDRAWN,
    },
    ApplicationStatus.REJECTED: set(),
    ApplicationStatus.WITHDRAWN: set(),
}
