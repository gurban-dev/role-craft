"""Structured logging with correlation context."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

import structlog

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
application_id_var: ContextVar[str] = ContextVar("application_id", default="")
job_id_var: ContextVar[str] = ContextVar("job_id", default="")
task_id_var: ContextVar[str] = ContextVar("task_id", default="")


SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "openai_api_key",
    "authorization",
    "cookie",
    "cookies",
    "secret",
    "csrf",
}


def _drop_sensitive(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_KEYS or key.lower().endswith(("_key", "_secret")):
            event_dict[key] = "[REDACTED]"
    return event_dict


def _inject_context(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    if cid := correlation_id_var.get():
        event_dict.setdefault("correlation_id", cid)
    if uid := user_id_var.get():
        event_dict.setdefault("user_id", uid)
    if aid := application_id_var.get():
        event_dict.setdefault("application_id", aid)
    if jid := job_id_var.get():
        event_dict.setdefault("job_id", jid)
    if tid := task_id_var.get():
        event_dict.setdefault("task_id", tid)
    return event_dict


def setup_logging(*, json_logs: bool = True) -> None:
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _inject_context,
        _drop_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def new_correlation_id() -> str:
    cid = str(uuid4())
    correlation_id_var.set(cid)
    return cid
