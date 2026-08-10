"""Greenhouse-like ATS workflow."""

from __future__ import annotations

from playwright.async_api import Page

from app.automation.models import ApplicationData, ApplicationQuestion, SubmissionResult
from app.automation.workflows.generic import GenericWorkflow
from app.automation.workflows.helpers import page_has_blocker


class GreenhouseWorkflow(GenericWorkflow):
    name = "greenhouse"

    async def can_handle(self, page: Page, url: str) -> bool:
        if "greenhouse.io" in url or "boards.greenhouse" in url:
            return True
        return await page.locator("[data-ats='greenhouse'], #application_form").count() > 0

    async def detect_blocker(self, page: Page) -> bool:
        return await page_has_blocker(page)

    async def extract_questions(self, page: Page) -> list[ApplicationQuestion]:
        return await super().extract_questions(page)

    async def fill_application(self, page: Page, data: ApplicationData) -> None:
        await super().fill_application(page, data)

    async def submit(self, page: Page) -> SubmissionResult:
        return await super().submit(page)
