"""
MemorySampler – selects high-value memories for LoRA corpus.
"""
from __future__ import annotations
from typing import List, Tuple
from random import random
from hippoium.ports.port_types import Message
from hippoium.ports.port_types import SampleStage


class MemorySampler:
    def __init__(self, alpha: float = 0.7):
        self.alpha = alpha  # sampling softness

    def sample(self, msgs: List[Message], k: int) -> Tuple[List[Message], SampleStage]:
        scored = [(m, random()) for m in msgs]  # TODO: replace with heuristic score
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:k]], SampleStage.RAW
