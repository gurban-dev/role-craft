"""LinkedIn Easy Apply workflow — gated by user/settings flag."""

from __future__ import annotations

from contextvars import ContextVar

from playwright.async_api import Page

from app.automation.models import ApplicationData, ApplicationQuestion, SubmissionResult
from app.automation.workflows.generic import GenericWorkflow
from app.automation.workflows.helpers import page_has_blocker
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

linkedin_easy_apply_enabled: ContextVar[bool] = ContextVar(
    "linkedin_easy_apply_enabled", default=False
)


class LinkedInEasyApplyWorkflow:
    """Handles linkedin.com/jobs apply URLs when Easy Apply fallback is enabled."""

    name = "linkedin_easy_apply"

    def _enabled(self) -> bool:
        return bool(linkedin_easy_apply_enabled.get()) or bool(
            get_settings().linkedin_easy_apply_fallback
        )

    async def can_handle(self, page: Page, url: str) -> bool:
        u = (url or "").lower()
        return "linkedin.com" in u and ("/jobs" in u or "easy-apply" in u)

    async def detect_blocker(self, page: Page) -> bool:
        return await page_has_blocker(page)

    async def extract_questions(self, page: Page) -> list[ApplicationQuestion]:
        return await GenericWorkflow().extract_questions(page)

    async def fill_application(self, page: Page, data: ApplicationData) -> None:
        if not self._enabled():
            logger.info("linkedin_easy_apply_disabled")
            return
        await GenericWorkflow().fill_application(page, data)

    async def submit(self, page: Page) -> SubmissionResult:
        if not self._enabled():
            return SubmissionResult(
                success=False,
                needs_human=True,
                message="LinkedIn Easy Apply fallback is disabled; human action required",
            )
        if await self.detect_blocker(page):
            return SubmissionResult(
                success=False, needs_human=True, message="LinkedIn blocker detected"
            )
        return await GenericWorkflow().submit(page)
