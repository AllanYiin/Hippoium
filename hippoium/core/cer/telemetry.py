"""Lightweight telemetry hooks."""
from __future__ import annotations
import time
from typing import Callable, Any
from functools import wraps
import logging

logger = logging.getLogger("hippoium.telemetry")
logging.basicConfig(level=logging.INFO)


def trace(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to trace latency & errors."""
    @wraps(fn)
    def _wrap(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            dur = (time.perf_counter() - start) * 1000
            logger.info("TRACE %s took %.2f ms", fn.__qualname__, dur)
    return _wrap
