"""Stable application errors translated to safe HTTP responses."""

from dataclasses import dataclass


@dataclass(eq=False)
class ApplicationError(Exception):
    status_code: int
    code: str
    detail: str


class BadRequestError(ApplicationError):
    def __init__(self, detail: str, code: str = "bad_request") -> None:
        super().__init__(400, code, detail)


class UnauthorizedError(ApplicationError):
    def __init__(
        self, detail: str = "Authentication is required.", code: str = "unauthorized"
    ) -> None:
        super().__init__(401, code, detail)


class ForbiddenError(ApplicationError):
    def __init__(
        self, detail: str = "You do not have permission for this action.", code: str = "forbidden"
    ) -> None:
        super().__init__(403, code, detail)


class NotFoundError(ApplicationError):
    def __init__(self, detail: str, code: str = "not_found") -> None:
        super().__init__(404, code, detail)


class ConflictError(ApplicationError):
    def __init__(self, detail: str, code: str = "conflict") -> None:
        super().__init__(409, code, detail)


class TooManyRequestsError(ApplicationError):
    def __init__(
        self,
        detail: str = "Too many requests. Please try again later.",
        code: str = "rate_limit_exceeded",
        *,
        retry_after_seconds: int = 1,
    ) -> None:
        super().__init__(429, code, detail)
        self.retry_after_seconds = max(1, retry_after_seconds)
