# ApplyDesk Web

Next.js 16 App Router frontend for the ApplyDesk job-application automation platform.

## Local URLs

Copy and open these in your browser after the servers are running:

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend server | http://localhost:8000 |
| Backend API docs | http://localhost:8000/docs |
| Backend API health | http://localhost:8000/api/health |

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the web env (see `apps/web/.env.example`).

## Start (local)

```bash
cd apps/web
pnpm install
pnpm dev
```
