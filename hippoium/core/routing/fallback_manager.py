"""
FallbackManager – retries with alternative provider on failure.
"""
from __future__ import annotations
import logging
from hippoium.adapters.base import BaseAdapter

logger = logging.getLogger("hippoium.fallback")


class FallbackManager:
    def __init__(self, primary: BaseAdapter, secondary: BaseAdapter):
        self.primary = primary
        self.secondary = secondary

    def execute(self, prompt: str) -> str:
        try:
            return self.primary.complete(prompt)
        except Exception as e:
            logger.warning("Primary failed: %s; falling back", e)
            return self.secondary.complete(prompt)
