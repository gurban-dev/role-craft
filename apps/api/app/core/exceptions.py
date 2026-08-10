"""Shared exceptions."""


class AppError(Exception):
    def __init__(self, message: str, *, code: str = "app_error", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found", status_code=404)


class AuthError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="unauthorized", status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, code="forbidden", status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, code="conflict", status_code=409)


class ValidationAppError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error", status_code=422)


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error", status_code=503)


class QualityGateError(AppError):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message, code="quality_gate_failed", status_code=409)
        self.details = details or {}


class NeedsHumanActionError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="needs_human_action", status_code=409)
