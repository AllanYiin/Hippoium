"""
Hybrid retrieval scorer: pos-sim − β × neg-sim.
"""
from __future__ import annotations
from typing import Sequence, List
from hippoium.ports.port_types import ScoreFn
from hippoium.ports.port_types import Message
from hippoium.ports.constants import DEFAULT_BETA
import random


class HybridScorer:
    def __init__(self, beta: float = DEFAULT_BETA, mode: ScoreFn = ScoreFn.HYBRID):
        self.beta = beta
        self.mode = mode

    def _mock_sim(self, a: str, b: str) -> float:
        """Placeholder similarity (0-1)."""
        return random.random()

    def score(self, query: str, docs: Sequence[Message]) -> List[float]:
        scores = []
        for d in docs:
            pos = self._mock_sim(query, d.content)
            neg = self._mock_sim(query[::-1], d.content)  # dummy neg
            if self.mode is ScoreFn.POS_COS:
                s = pos
            elif self.mode is ScoreFn.NEG_COS:
                s = 1 - neg
            else:
                s = pos - self.beta * neg
            scores.append(s)
        return scores
