"""Shared helpers for ATS workflows."""

from __future__ import annotations

from playwright.async_api import Page

BLOCKER_SELECTORS = [
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "[data-testid='captcha']",
    "#captcha",
    "text=Verify you are human",
    "text=Two-factor",
    "text=multi-factor",
    "text=Enter the code we sent",
    "[data-blocker='captcha']",
    "[data-blocker='mfa']",
]


async def page_has_blocker(page: Page) -> bool:
    for sel in BLOCKER_SELECTORS:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0 and await loc.first.is_visible():
                return True
        except Exception:
            continue
    content = (await page.content()).lower()
    if "data-mock-success" in content:
        return False
    markers = (
        'data-blocker=',
        'id="captcha"',
        "recaptcha",
        "hcaptcha",
        "two-factor",
        "multi-factor authentication",
    )
    return any(marker in content for marker in markers)


async def fill_by_label(page: Page, label: str, value: str) -> bool:
    try:
        field = page.get_by_label(label, exact=False)
        if await field.count() > 0:
            await field.first.fill(value)
            return True
    except Exception:
        pass
    try:
        field = page.get_by_role("textbox", name=label)
        if await field.count() > 0:
            await field.first.fill(value)
            return True
    except Exception:
        pass
    return False
