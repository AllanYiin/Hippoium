"""
Route request to llm provider based on cost/latency score.
"""
from __future__ import annotations
from typing import Dict
import random
from hippoium.adapters.base import BaseAdapter


class CostRouter:
    def __init__(self, providers: Dict[str, BaseAdapter]):
        self.providers = providers

    def select(self, prompt: str) -> BaseAdapter:
        # TODO: real cost & latency model
        return random.choice(list(self.providers.values()))
