"""Workflow registry."""

from __future__ import annotations

from playwright.async_api import Page

from app.automation.workflows.generic import GenericWorkflow
from app.automation.workflows.greenhouse import GreenhouseWorkflow
from app.automation.workflows.lever import LeverWorkflow
from app.automation.workflows.workday import WorkdayWorkflow

_WORKFLOWS = [
    GreenhouseWorkflow(),
    LeverWorkflow(),
    WorkdayWorkflow(),
    GenericWorkflow(),
]


async def get_workflow_for_url(page: Page, url: str):
    for workflow in _WORKFLOWS:
        if await workflow.can_handle(page, url):
            return workflow
    return GenericWorkflow()


def list_workflows() -> list[str]:
    return [w.name for w in _WORKFLOWS]
