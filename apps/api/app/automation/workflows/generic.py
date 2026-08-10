"""Generic application form workflow."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page

from app.automation.models import ApplicationData, ApplicationQuestion, SubmissionResult
from app.automation.playwright_manager import PlaywrightManager
from app.automation.workflows.helpers import fill_by_label, page_has_blocker
from app.core.logging import get_logger

logger = get_logger(__name__)


class GenericWorkflow:
    name = "generic"

    async def can_handle(self, page: Page, url: str) -> bool:
        return True

    async def detect_blocker(self, page: Page) -> bool:
        return await page_has_blocker(page)

    async def extract_questions(self, page: Page) -> list[ApplicationQuestion]:
        questions: list[ApplicationQuestion] = []
        labels = page.locator("label")
        count = await labels.count()
        for i in range(min(count, 50)):
            text = (await labels.nth(i).inner_text()).strip()
            if text:
                questions.append(ApplicationQuestion(label=text))
        return questions

    async def fill_application(self, page: Page, data: ApplicationData) -> None:
        filled_name = await fill_by_label(page, "Full name", data.candidate_name)
        if not filled_name:
            filled_name = await fill_by_label(page, "Name", data.candidate_name)
        if not filled_name:
            name_input = page.locator('input[name="name"], input[name="full_name"]')
            if await name_input.count() > 0:
                await name_input.first.fill(data.candidate_name)

        filled_email = await fill_by_label(page, "Email", data.candidate_email)
        if not filled_email:
            email_input = page.locator('input[name="email"], input[type="email"]')
            if await email_input.count() > 0:
                await email_input.first.fill(data.candidate_email)

        if data.phone:
            await fill_by_label(page, "Phone", data.phone)
        if data.linkedin_url:
            await fill_by_label(page, "LinkedIn", data.linkedin_url)
        if data.resume_path and Path(data.resume_path).exists():
            file_input = page.locator('input[type="file"]')
            if await file_input.count() > 0:
                await file_input.first.set_input_files(data.resume_path)
        for key, value in (data.answers or {}).items():
            if isinstance(value, str):
                await fill_by_label(page, key, value)

    async def submit(self, page: Page) -> SubmissionResult:
        if await self.detect_blocker(page):
            return SubmissionResult(success=False, needs_human=True, message="Blocker detected")

        button = page.get_by_role("button", name="Submit")
        if await button.count() == 0:
            button = page.get_by_role("button", name="Apply")
        if await button.count() == 0:
            return SubmissionResult(
                success=False, needs_human=True, message="Submit button not found"
            )
        await button.first.click()
        try:
            await page.wait_for_selector(
                "[data-mock-success='true'], [data-testid='confirmation']",
                timeout=5000,
            )
        except Exception:
            await page.wait_for_load_state("domcontentloaded")

        if await self.detect_blocker(page):
            return SubmissionResult(success=False, needs_human=True, message="Blocker after submit")

        confirmation = ""
        for sel in (
            "[data-testid='confirmation']",
            "[data-mock-success='true']",
            ".confirmation",
            "h1",
        ):
            loc = page.locator(sel)
            if await loc.count() > 0:
                confirmation = await loc.first.inner_text()
                break
        screenshot = None
        try:
            screenshot = await PlaywrightManager().screenshot(page, f"submit-{self.name}")
        except Exception:
            logger.warning("screenshot_failed")
        success = bool(await page.locator("[data-mock-success='true']").count()) or (
            "thank" in confirmation.lower() or "received" in confirmation.lower()
        )
        return SubmissionResult(
            success=success,
            needs_human=not success,
            confirmation_text=confirmation,
            confirmation_url=page.url,
            screenshot_path=screenshot,
            message=None if success else "Could not confirm submission",
        )
