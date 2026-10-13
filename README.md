# AI Job Application Automation Platform

A full-stack platform that discovers software engineering roles, ranks matches, tailors truthful resumes, researches companies and contacts, prepares outreach, and submits applications through Playwright workflows with human approval by default.

**Quality over volume:** Default daily target of 10 high-quality applications. Match thresholds are never lowered to reach the target.

## Architecture

```text
apps/
├── web/       Next.js 16, React 19, Tailwind CSS 4
└── api/       FastAPI, SQLAlchemy, Celery, Playwright

packages/shared/   Shared constants
infrastructure/    Docker and deployment configuration
```

## Tech Stack

| Component | Version |
|---|---|
| Node.js / pnpm | 22+ / 10+ |
| Next.js / React | 16.3.0 / 19.2.x |
| Python / uv | 3.12 / 0.12.x |
| FastAPI / Pydantic / SQLAlchemy | 0.141.1 / 2.13.4 / 2.0.51 |
| PostgreSQL / Redis | 16 / 7 |
| Celery | 5.6.3 |
| Playwright | 1.62.0 |

## Prerequisites

- Docker Desktop with Docker Compose, recommended.
- Alternatively, Node.js, pnpm, Python 3.12, uv, PostgreSQL 16, and Redis 7.
- An OpenAI API key for AI features.

## Quick Start

### Linux / macOS

From the repository root:

```bash
cp .env.example .env
```

Configure `SECRET_KEY`, `JWT_SECRET`, and `OPENAI_API_KEY` in `.env`, then run:

```bash
WEB_GID=$(id -g) docker compose up --build
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Configure the required secrets in `.env`, then run:

```powershell
docker compose up --build
```

The Windows command assumes `WEB_GID` is not required by your Compose configuration.

Open:

- Frontend: http://localhost:3000
- API documentation: http://localhost:8000/docs
- API health: http://localhost:8000/api/health

To start the production configuration:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Local Development

Requires PostgreSQL 16 and Redis 7 running locally. Configure `DATABASE_URL` and `REDIS_URL` in `.env`.

### 1. Start the API

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run playwright install chromium
uv run uvicorn app.main:app --reload --port 8000
```

### 2. Start the Celery worker

In a separate terminal:

```bash
cd apps/api
uv run celery -A app.workers.celery_app.celery_app worker --loglevel=INFO
```

On Windows, use:

```powershell
uv run celery -A app.workers.celery_app.celery_app worker --pool=solo --loglevel=INFO
```

### 3. Start the optional scheduler

```bash
cd apps/api
uv run celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

### 4. Start the frontend

In another terminal:

```bash
cd apps/web
pnpm install
pnpm dev
```

On Windows, run the same commands in PowerShell.

## Environment Configuration

See `.env.example` for all supported variables.

Key settings:

- `DATABASE_URL`, `REDIS_URL`: database and Redis connections.
- `SECRET_KEY`, `JWT_SECRET`: security secrets.
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `LLM_PROVIDER`: AI configuration.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`: optional Google sign-in.
- `WEB_APP_URL`, `CORS_ORIGINS`: frontend URL and allowed origins.
- `AUTO_SUBMIT_ENABLED=false`: human approval by default.
- `DAILY_APPLICATION_LIMIT=10`, `MIN_MATCH_SCORE`, `MIN_RESUME_SCORE`: application limits and quality thresholds.

**Never commit real secrets or API keys.**

## Database Migrations

Run from `apps/api`:

```bash
uv run alembic upgrade head
```

Generate a migration after changing database models:

```bash
uv run alembic revision --autogenerate -m "description"
```

Review generated migrations before applying them.

## Testing

Backend:

```bash
cd apps/api
uv run ruff check app tests
uv run mypy app
uv run pytest -q
```

Frontend:

```bash
cd apps/web
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Automation workflows:

```bash
cd apps/api
uv run pytest tests/test_automation_workflows.py -q
```

## Extending the Platform

- **Job sources:** Implement `JobSource` in `apps/api/app/integrations/job_sources/` and register it in `registry.py`.
- **ATS workflows:** Implement a workflow in `apps/api/app/automation/workflows/` and register it in `registry.py`.
- **LLM providers:** Implement `LLMProvider` and extend the provider factory.

## Security

- Human approval is required by default.
- No CAPTCHA or MFA bypasses.
- Resume claims and research findings must be evidence-based.
- Credentials are encrypted at rest.
- Secrets and sensitive credentials must never appear in logs.

## License

Proprietary. Internal use only.