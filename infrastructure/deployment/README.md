# Deployment

## Fastest path: Docker Compose on a single VM

1. Provision Ubuntu 24.04+ with Docker Engine + Compose plugin.
2. Clone the repo, copy `.env.example` to `.env`, set `SECRET_KEY`, `JWT_SECRET`, and `OPENAI_API_KEY`.
3. Run `docker compose -f docker-compose.prod.yml up --build -d`.
4. Migrations run in the API container start command.
5. Point a reverse proxy at the web service (port 3000). Keep the API private when possible.

## Split deploy

- **Web**: container or Node host running `pnpm build && pnpm start` with `NEXT_PUBLIC_API_URL`.
- **API + workers**: image from `infrastructure/docker/Dockerfile.api`; scale the browser worker separately.
- **Postgres / Redis**: managed services; update URLs in `.env`.

Playwright workers need adequate shared memory (`ipc: host` in Compose) and Chromium dependencies (installed in the API image).
