"""Aggregate API router."""

from fastapi import APIRouter

from app.api import (
    applications,
    auth,
    contacts,
    dashboard,
    health,
    jobs,
    profile,
    research,
    resumes,
    runs,
    settings,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(resumes.router)
api_router.include_router(contacts.router)
api_router.include_router(research.router)
api_router.include_router(settings.router)
api_router.include_router(runs.router)
api_router.include_router(dashboard.router)
