"""Playwright browser lifecycle manager."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PlaywrightManager:
    def __init__(self, *, headless: bool = True) -> None:
        self.headless = headless
        self.settings = get_settings()

    @asynccontextmanager
    async def page(self) -> AsyncIterator[Page]:
        if not self.settings.browser_automation_enabled:
            raise RuntimeError("Browser automation is disabled")
        async with async_playwright() as p:
            browser: Browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()
                await browser.close()

    async def screenshot(self, page: Page, name: str) -> str:
        path = Path(self.settings.storage_path) / "screenshots"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{name}.png"
        await page.screenshot(path=str(file_path), full_page=True)
        logger.info("screenshot_saved", path=str(file_path))
        return str(file_path)
