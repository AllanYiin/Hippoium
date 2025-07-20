"""Token Throttling runtime orchestration."""
from __future__ import annotations
from collections import deque
from statistics import fmean
from hippoium.ports.port_types import TrimPolicy
from hippoium.ports.constants import MAX_TOKENS_PROMPT
from hippoium.ports.protocols import TokenMeter
from hippoium.core.utils.token_counter import count_tokens


class EWMA:
    """Simple EWMA estimator."""
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value: float | None = None

    def update(self, x: float) -> float:
        self.value = x if self.value is None else self.value * (1 - self.alpha) + x * self.alpha
        return self.value


class SimpleTokenMeter(TokenMeter):
    def __init__(self, limit: int = MAX_TOKENS_PROMPT):
        self.limit = limit
        self.consumed: int = 0

    def update(self, consumed: int) -> None:
        self.consumed += consumed

    def remaining(self) -> int:
        return max(self.limit - self.consumed, 0)


class TokenThrottler:
    def __init__(self, policy: TrimPolicy = TrimPolicy.DIFF_PATCH):
        self.policy = policy
        self.budget_estimator = EWMA()
        self.history = deque(maxlen=50)

    def register_usage(self, text: str) -> None:
        tokens = count_tokens(text)
        self.history.append(tokens)
        self.budget_estimator.update(tokens)

    def current_budget(self) -> int:
        est = self.budget_estimator.value or 0
        return int(MAX_TOKENS_PROMPT - est)
