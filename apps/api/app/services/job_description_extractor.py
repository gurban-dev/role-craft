"""Fetch and clean public job pages before they reach an LLM."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

if TYPE_CHECKING:
    from playwright.async_api import Route


class _VisibleText(HTMLParser):
    """Small dependency-free HTML text extractor that preserves headings/lists."""

    _skip = {"script", "style", "noscript", "svg", "iframe", "nav", "form", "aside"}
    _break = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "br"}
    _noise = re.compile(
        r"(?:^|[-_\s])(?:ads?|advert(?:isement)?s?|sidebar|cookie|recommendations?|"
        r"related|social|share|tracking|breadcrumbs?)(?:$|[-_\s])",
        re.I,
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.main_parts: list[str] = []
        self.depth = 0
        self.main_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        class_and_id = f"{attrs_dict.get('class') or ''} {attrs_dict.get('id') or ''}"
        should_skip = (
            tag in self._skip
            or "hidden" in attrs_dict
            or attrs_dict.get("aria-hidden") == "true"
            or self._noise.search(class_and_id)
        )
        if self.depth or should_skip:
            self.depth += 1
        if tag in {"main", "article"} or attrs_dict.get("role") == "main":
            self.main_depth += 1
        if not self.depth and tag in self._break:
            self.parts.append("\n")
            if self.main_depth:
                self.main_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"main", "article"} and self.main_depth:
            self.main_depth -= 1
        if self.depth:
            self.depth -= 1
        if not self.depth and tag in self._break:
            self.parts.append("\n")
            if self.main_depth:
                self.main_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.depth:
            text = re.sub(r"\s+", " ", data).strip()
            if text:
                self.parts.append(text)
                if self.main_depth:
                    self.main_parts.append(text)


def clean_html_content(html: str) -> str:
    """Convert already-downloaded HTML job content to deduplicated visible text."""
    parser = _VisibleText()
    parser.feed(html)
    source = parser.main_parts or parser.parts
    return _dedupe_visible_text("\n".join(source))


def _dedupe_visible_text(text: str) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        normalized = re.sub(r"\s+", " ", line).strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            lines.append(normalized)
    return "\n".join(lines)


def _public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
        return bool(addresses) and all(
            ipaddress.ip_address(item[4][0]).is_global for item in addresses
        )
    except (OSError, ValueError):
        return False


def _jsonld_job(html: str) -> dict[str, Any] | None:
    for match in re.finditer(
        r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        re.I | re.S,
    ):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        queue = data if isinstance(data, list) else [data]
        while queue:
            item = queue.pop(0)
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("@graph"), list):
                queue.extend(item["@graph"])
            kind = item.get("@type", [])
            if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
                return item
    return None


async def extract_job_page(url: str, *, timeout: float = 12.0) -> dict[str, Any]:
    """Return cleaned public job content; errors are explicit and safe to fall back from."""
    if not _public_http_url(url):
        raise ValueError("Job page URL must resolve to a public HTTP(S) address")
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": "RoleCraftJobReader/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "").lower():
            raise ValueError("Job page did not return HTML")
        html = response.text

    job = _jsonld_job(html) or {}
    parser = _VisibleText()
    parser.feed(html)
    visible = "\n".join(parser.main_parts or parser.parts)
    if len(visible.strip()) < 300 and not job.get("description"):
        try:
            from app.automation.playwright_manager import PlaywrightManager

            async with PlaywrightManager().page() as page:
                async def allow_public_request(route: "Route") -> None:
                    target = route.request.url
                    parsed = urlparse(target)
                    if parsed.scheme in {"http", "https"} and not _public_http_url(target):
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route("**/*", allow_public_request)
                await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                main = page.locator("main, article, [role=main]").first
                if await main.count():
                    visible = await main.inner_text(timeout=int(timeout * 1000))
                else:
                    visible = await page.locator("body").inner_text(timeout=int(timeout * 1000))
        except Exception:
            # Static HTML remains a useful fallback when browser rendering is unavailable.
            pass
    description = job.get("description")
    if isinstance(description, str):
        body = _VisibleText()
        body.feed(description)
        visible = "\n".join(body.parts) or re.sub(r"<[^>]*>", " ", description)
    clean = _dedupe_visible_text(visible)
    if not clean:
        raise ValueError("No visible job content found on the page")
    company = job.get("hiringOrganization") or {}
    applicant_count = job.get("applicantCount")
    if not isinstance(applicant_count, int):
        count_match = re.search(r"\b(\d[\d,]*)\s+applicants?\b", clean, re.I)
        applicant_count = int(count_match.group(1).replace(",", "")) if count_match else None
    account_match = re.search(
        r"\bapplicant\s+(?:account\s+)?(?:id|identifier|number)\s*[:#]?\s*([\w-]+)",
        clean,
        re.I,
    )
    return {
        "job_title": job.get("title"),
        "company": company.get("name") if isinstance(company, dict) else None,
        "job_url": url,
        "job_description": clean,
        "applicant_count": applicant_count,
        "applicant_account_identifier": account_match.group(1) if account_match else None,
        "team_members": [],
        "other_relevant_information": [],
        "token_count_estimate": max(1, len(clean) // 4),
    }
