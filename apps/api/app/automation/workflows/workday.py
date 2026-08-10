"""Workday-like multi-step ATS workflow."""

from __future__ import annotations

from playwright.async_api import Page

from app.automation.models import ApplicationData, SubmissionResult
from app.automation.workflows.generic import GenericWorkflow
from app.automation.workflows.helpers import fill_by_label, page_has_blocker


class WorkdayWorkflow(GenericWorkflow):
    name = "workday"

    async def can_handle(self, page: Page, url: str) -> bool:
        if "myworkdayjobs.com" in url or "workday" in url:
            return True
        return (
            await page.locator(
                "[data-ats='workday'], [data-automation-id='applyButton']"
            ).count()
            > 0
        )

    async def detect_blocker(self, page: Page) -> bool:
        return await page_has_blocker(page)

    async def fill_application(self, page: Page, data: ApplicationData) -> None:
        # Multi-step: fill visible fields then click Next if present
        for _ in range(5):
            if await self.detect_blocker(page):
                return
            await fill_by_label(page, "Name", data.candidate_name)
            await fill_by_label(page, "Email", data.candidate_email)
            next_btn = page.get_by_role("button", name="Next")
            if await next_btn.count() > 0 and await next_btn.first.is_visible():
                await next_btn.first.click()
                await page.wait_for_load_state("domcontentloaded")
            else:
                break
        await super().fill_application(page, data)

    async def submit(self, page: Page) -> SubmissionResult:
        return await super().submit(page)
