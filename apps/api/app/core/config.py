"""Application configuration validated at startup."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Job Application Automation"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api"

    database_url: str = Field(
        default="postgresql+asyncpg://jaa:jaa@localhost:5432/jaa",
        description="Async SQLAlchemy database URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://jaa:jaa@localhost:5432/jaa",
        description="Sync database URL for Alembic/Celery",
    )
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    jwt_secret: str = Field(default="change-me-jwt-secret-use-openssl-rand-hex-32")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "jaa_session"
    csrf_cookie_name: str = "jaa_csrf"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated allowed CORS origins",
    )

    # LLM
    llm_provider: Literal["openai"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str | None = None
    llm_max_retries: int = 3
    llm_timeout_seconds: float = 60.0

    # Application quality controls
    daily_application_limit: int = 10
    min_match_score: float = 0.65
    min_resume_score: float = 0.70
    min_outreach_evidence_confidence: float = 0.60
    min_contact_confidence: float = 0.55
    min_answer_confidence: float = 0.70
    auto_submit_enabled: bool = False
    outreach_enabled: bool = True
    browser_automation_enabled: bool = True
    linkedin_easy_apply_fallback: bool = False

    # Scoring weights (must sum ~1.0)
    weight_technical: float = 0.30
    weight_experience: float = 0.20
    weight_seniority: float = 0.15
    weight_location: float = 0.10
    weight_domain: float = 0.10
    weight_salary: float = 0.05
    weight_preference: float = 0.10

    # Rate limits
    rate_limit_job_discovery_per_hour: int = 30
    rate_limit_llm_per_hour: int = 200
    rate_limit_browser_per_hour: int = 20
    rate_limit_research_per_hour: int = 40
    browser_max_concurrency: int = 1

    # Storage
    storage_path: str = "./storage"
    encryption_key: str | None = None  # Fernet key; derived from secret_key if unset

    # Retention (days); 0 = keep forever
    retention_days_applications: int = 365
    retention_days_automation_runs: int = 90
    retention_days_ai_usage: int = 180

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: object) -> object:
        if isinstance(value, list):
            return ",".join(str(v).strip() for v in value if str(v).strip())
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def require_openai_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in the environment to use AI features."
            )
        return self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
