# Job Application API

FastAPI backend for the ApplyDesk / Role Craft platform (`apps/api`).

## Local URLs

Copy and open these in your browser after the API is running:

| Service | URL |
|---------|-----|
| Backend server | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/health |
| API prefix | http://localhost:8000/api |
| Google OAuth start | http://localhost:8000/api/auth/google |

Frontend (separate app): http://localhost:3000

## Start (local)

```bash
cd apps/api
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```
