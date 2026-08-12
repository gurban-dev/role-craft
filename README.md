# AI Job Application Automation Platform

Production-ready full-stack system that discovers software engineering roles, ranks matches, tailors truthful resumes, researches companies/contacts, prepares outreach, and submits applications through modular Playwright workflows — with human approval by default.

**Quality over volume.** Default daily target: 10 high-quality applications. The system never lowers the match threshold merely to reach 10.

## Architecture

```
apps/web          Next.js 16 (App Router) + React 19 + Tailwind 4 + TanStack Query
apps/api          FastAPI + SQLAlchemy 2 + Celery + Playwright
packages/shared   Shared constants (optional)
infrastructure/   Dockerfiles, migrations helpers, deployment notes
```

**Discovery → Decision → Execution** are separated. Browser automation never decides that a role is suitable.

## Stack (pinned)

| Layer | Versions |
|-------|----------|
| Node / pnpm | 22+ / 10+ |
| Next.js / React | 16.3.0 / 19.2.x |
| Python / uv | 3.12 / 0.12.x |
| FastAPI / Pydantic / SQLAlchemy | 0.141.1 / 2.13.4 / 2.0.51 |
| Celery / Redis / PostgreSQL | 5.6.3 / 7 / 16 |
| Playwright | 1.62.0 |
| LLM | OpenAI (configurable `LLMProvider`; only OpenAI implemented) |

## Prerequisites

- Docker + Compose (recommended for full stack), **or** local PostgreSQL 16 + Redis 7
- Node.js ≥ 20.9 (22 LTS recommended), pnpm
- Python 3.12, uv
- Playwright browser binaries (`uv run playwright install --with-deps chromium`)

## Quick start (Docker)

```bash
cp .env.example .env
# Set SECRET_KEY, JWT_SECRET, and OPENAI_API_KEY (required for AI features)

docker compose up --build
```

Services:

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API / OpenAPI | http://localhost:8000/docs |
| Postgres | localhost:5432 |
| Redis | localhost:6379 |

Production compose: `docker compose -f docker-compose.prod.yml up --build -d`

## Local development (without Docker daemon)

```bash
# Infra (examples using local binaries)
redis-server --daemonize yes
# PostgreSQL 16 listening on 127.0.0.1:5432 with user/db `jaa`

cp .env.example .env
# Point DATABASE_URL / REDIS_URL at localhost (see .env.example)

# API
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=INFO

# Optional beat scheduler
uv run celery -A app.workers.celery_app.celery_app beat --loglevel=INFO

# Playwright browsers
uv run playwright install --with-deps chromium

# Web
cd apps/web
pnpm install
pnpm dev
```

## Environment variables

See [`.env.example`](.env.example). Critical:

- `SECRET_KEY`, `JWT_SECRET` — session/crypto secrets
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `WEB_APP_URL` — optional Google sign-in
- `DATABASE_URL`, `REDIS_URL`, `CELERY_*`
- `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL`
- `AUTO_SUBMIT_ENABLED=false` (Approval Mode default)
- `DAILY_APPLICATION_LIMIT=10`, `MIN_MATCH_SCORE`, `MIN_RESUME_SCORE`

**Never commit real API keys.** If `OPENAI_API_KEY` is missing, AI operations fail clearly with a configuration error.

## Database migrations

```bash
cd apps/api
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"   # when schema changes
```

## Authentication

HTTP-only JWT cookie (`jaa_session`) + CSRF cookie (`jaa_csrf`). Send `X-CSRF-Token` on mutating requests from the browser.

**Google sign-in:** set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` (must match the authorized redirect URI in Google Cloud Console — default `http://localhost:8000/api/auth/google/callback`). Also set `WEB_APP_URL` to your frontend origin. Users can continue with Google from login/register; matching emails link to existing password accounts.

## Daily workflow

1. Job discovery (Remotive, Arbeitnow, Greenhouse public boards)
2. Dedup + deterministic scoring
3. Quality threshold filter
4. Resume tailor + validation + PDF (claims must exist in candidate profile)
5. Company research (evidence required)
6. Contact discovery (recruiter first; never both recruiter + hiring manager)
7. Outreach generation (skipped if evidence weak)
8. Application prep → **human Approve & Submit** (default)
9. Playwright submit on official/ATS URL
10. Record result; CAPTCHA/MFA → `NEEDS_HUMAN_ACTION` (no bypass)

## Adding extensions

### New job source

Implement `JobSource` in `apps/api/app/integrations/job_sources/` and register in `registry.py`.

### New ATS workflow

Implement `ApplicationWorkflow` under `apps/api/app/automation/workflows/` and register in `registry.py`. Prefer role/label locators; never sleep as primary sync; pause on CAPTCHA/MFA.

### New LLM provider

Implement `LLMProvider` Protocol in `apps/api/app/integrations/llm/` and extend `factory.py`. Keep business logic provider-agnostic.

## Testing

```bash
# API
cd apps/api
uv run ruff check app tests
uv run mypy app
uv run pytest -q

# Frontend
cd apps/web
pnpm lint && pnpm typecheck && pnpm test && pnpm build

# Automation fixtures (mock Greenhouse/Lever/CAPTCHA pages)
cd apps/api
uv run pytest tests/test_automation_workflows.py -q
```

## Health

- `GET /api/health` — liveness
- `GET /api/ready` — Postgres + Redis readiness

## Security notes

- No CAPTCHA/MFA/bot-detection bypass
- No fabricated CV claims, research, or contacts
- Credentials encrypted at rest; secrets via environment only
- Structured logs redact secrets; never log API keys or cookies
- Conservative rate limits; idempotent application submits with DB constraints

## Troubleshooting

| Issue | Fix |
|-------|-----|
| AI calls fail | Set `OPENAI_API_KEY` |
| Playwright missing browsers | `uv run playwright install --with-deps chromium` |
| Migrations fail | Check `DATABASE_URL` and Postgres connectivity |
| Worker idle | Ensure Redis URL matches API; check `celery worker` logs |
| CORS errors | Set `CORS_ORIGINS` to your web origin(s) |

## License

Proprietary — internal use.
