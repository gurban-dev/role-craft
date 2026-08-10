"""Application workflow protocol."""

from __future__ import annotations

from typing import Protocol

from playwright.async_api import Page

from app.automation.models import ApplicationData, ApplicationQuestion, SubmissionResult


class ApplicationWorkflow(Protocol):
    name: str

    async def can_handle(self, page: Page, url: str) -> bool: ...

    async def detect_blocker(self, page: Page) -> bool: ...

    async def extract_questions(self, page: Page) -> list[ApplicationQuestion]: ...

    async def fill_application(self, page: Page, application_data: ApplicationData) -> None: ...

    async def submit(self, page: Page) -> SubmissionResult: ...
