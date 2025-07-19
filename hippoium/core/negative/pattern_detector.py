"""
Helper to detect forbidden patterns for Negative Prompt Injection.
"""
import re
from typing import List


class PatternDetector:
    def __init__(self, patterns: List[str]):
        self._compiled = [re.compile(p, re.I) for p in patterns]

    def detect(self, text: str) -> bool:
        return any(p.search(text) for p in self._compiled)
