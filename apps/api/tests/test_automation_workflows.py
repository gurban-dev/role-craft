"""Playwright workflow tests against local mock ATS pages."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.automation.models import ApplicationData
from app.automation.registry import get_workflow_for_url
from app.automation.workflows.helpers import page_has_blocker

FIXTURES = Path(__file__).parent / "fixtures" / "ats"


@pytest.mark.asyncio
async def test_greenhouse_success() -> None:
    path = (FIXTURES / "greenhouse.html").resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(path)
        workflow = await get_workflow_for_url(page, path)
        assert workflow.name == "greenhouse"
        data = ApplicationData(
            job_title="Software Engineer",
            company="Acme",
            candidate_name="Demo User",
            candidate_email="demo@example.com",
        )
        await workflow.fill_application(page, data)
        result = await workflow.submit(page)
        assert result.success
        assert not result.needs_human
        await browser.close()


@pytest.mark.asyncio
async def test_captcha_pauses() -> None:
    path = (FIXTURES / "captcha.html").resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(path)
        assert await page_has_blocker(page)
        await browser.close()


@pytest.mark.asyncio
async def test_mfa_pauses() -> None:
    path = (FIXTURES / "mfa.html").resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(path)
        assert await page_has_blocker(page)
        await browser.close()


@pytest.mark.asyncio
async def test_lever_success() -> None:
    path = (FIXTURES / "lever.html").resolve().as_uri()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(path)
        workflow = await get_workflow_for_url(page, path)
        assert workflow.name == "lever"
        data = ApplicationData(
            job_title="Backend Engineer",
            company="LeverCo",
            candidate_name="Demo User",
            candidate_email="demo@example.com",
        )
        await workflow.fill_application(page, data)
        result = await workflow.submit(page)
        assert result.success
        await browser.close()
