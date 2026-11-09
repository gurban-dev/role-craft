from __future__ import annotations

import json
from pathlib import Path

from app.services.job_description_extractor import (
    _VisibleText,
    _jsonld_job,
    clean_html_content,
)


FIXTURE = Path(__file__).parent / "fixtures" / "job_description.html"


def test_job_page_extracts_jsonld_and_omits_scripts_styles_and_navigation() -> None:
    html = FIXTURE.read_text()

    job = _jsonld_job(html)
    parser = _VisibleText()
    parser.feed(html)
    text = " ".join(parser.parts)

    assert job is not None
    assert job["title"] == "Backend Engineer"
    assert job["hiringOrganization"]["name"] == "Example Co"
    assert "Build reliable services." in text
    assert "Home About Careers" not in text
    assert "window.tracker" not in text
    assert ".banner" not in text
    assert json.loads(json.dumps(job))["@type"] == "JobPosting"


def test_clean_html_description_keeps_job_text_and_strips_markup_and_duplicates() -> None:
    cleaned = clean_html_content(FIXTURE.read_text())

    assert "Backend Engineer" in cleaned
    assert "Build reliable services." in cleaned
    assert "window.tracker" not in cleaned
    assert "<p>" not in cleaned
    assert cleaned.count("Build reliable services.") == 1
