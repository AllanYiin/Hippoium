from __future__ import annotations

from dataclasses import dataclass
import logging
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: float = 0.1


def _compute_delay(attempt: int, config: RetryConfig) -> float:
    delay = min(config.max_delay, config.base_delay * (2 ** (attempt - 1)))
    if config.jitter:
        delay += random.uniform(0, config.jitter)
    return delay


def retry(
    operation: Callable[[int], T],
    *,
    config: RetryConfig,
    is_retryable: Callable[[BaseException], bool],
    logger: logging.Logger,
    log_context: str,
) -> T:
    for attempt in range(1, config.max_attempts + 1):
        try:
            return operation(attempt)
        except Exception as exc:  # noqa: BLE001 - re-raise after policy check
            if attempt >= config.max_attempts or not is_retryable(exc):
                raise
            delay = _compute_delay(attempt, config)
            logger.warning(
                "Retryable provider error; attempt=%s/%s delay=%.2fs error=%s request_id=%s %s",
                attempt,
                config.max_attempts,
                delay,
                exc.__class__.__name__,
                getattr(exc, "request_id", None),
                log_context,
            )
            time.sleep(delay)
    raise RuntimeError("Retry loop exited unexpectedly")
