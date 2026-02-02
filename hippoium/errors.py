from __future__ import annotations

from typing import Optional


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.cause = cause


class RateLimitError(ProviderError):
    pass


class TimeoutError(ProviderError):
    pass


class TransientServerError(ProviderError):
    pass


class BadRequestError(ProviderError):
    pass


class AuthError(ProviderError):
    pass


def is_retryable_error(error: BaseException) -> bool:
    return isinstance(error, (RateLimitError, TimeoutError, TransientServerError))
