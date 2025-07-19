"""
Quick heuristic to score prompt complexity for routing.
"""
import math
from hippoium.core.utils.token_counter import count_tokens


def score_complexity(prompt: str) -> float:
    t = count_tokens(prompt)
    return math.log1p(t)
