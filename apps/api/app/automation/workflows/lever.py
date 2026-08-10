"""Lever-like ATS workflow."""

from __future__ import annotations

from playwright.async_api import Page

from app.automation.models import SubmissionResult
from app.automation.workflows.generic import GenericWorkflow
from app.automation.workflows.helpers import page_has_blocker


class LeverWorkflow(GenericWorkflow):
    name = "lever"

    async def can_handle(self, page: Page, url: str) -> bool:
        if "lever.co" in url or "jobs.lever" in url:
            return True
        return await page.locator("[data-ats='lever'], .application-form").count() > 0

    async def detect_blocker(self, page: Page) -> bool:
        return await page_has_blocker(page)

    async def submit(self, page: Page) -> SubmissionResult:
        return await super().submit(page)
