"""
Route request to llm provider based on cost/latency score.
"""
from __future__ import annotations
from typing import Dict
import random

from hippoium.ports.protocols import LLMClient


class CostRouter:
    def __init__(self, providers: Dict[str, LLMClient]):
        self.providers = providers

    def select(self, prompt: str) -> LLMClient:
        # TODO: real cost & latency model
        return random.choice(list(self.providers.values()))
