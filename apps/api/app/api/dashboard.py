"""Dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas import DashboardStats
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(user: CurrentUser, db: DbSession) -> DashboardStats:
    return await DashboardService(db).stats(user)
