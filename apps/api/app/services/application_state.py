"""Application status transition helper."""

from __future__ import annotations

from app.core.exceptions import ValidationAppError
from app.models.enums import APPLICATION_TRANSITIONS, ApplicationStatus


def can_transition(current: ApplicationStatus | str, target: ApplicationStatus | str) -> bool:
    cur = ApplicationStatus(current)
    tgt = ApplicationStatus(target)
    return tgt in APPLICATION_TRANSITIONS.get(cur, set())


def transition(
    current: ApplicationStatus | str,
    target: ApplicationStatus | str,
    *,
    allow_same: bool = True,
) -> ApplicationStatus:
    """Validate and return the target status.

    Raises ValidationAppError when the transition is illegal.
    """
    cur = ApplicationStatus(current)
    tgt = ApplicationStatus(target)
    if allow_same and cur == tgt:
        return tgt
    allowed = APPLICATION_TRANSITIONS.get(cur, set())
    if tgt not in allowed:
        raise ValidationAppError(
            f"Illegal application transition: {cur.value} -> {tgt.value}"
        )
    return tgt
