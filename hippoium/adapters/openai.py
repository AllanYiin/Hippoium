"""
OpenAI adapter (stub) – replace with real openai import in prod.
"""
from __future__ import annotations
from typing import List
from hippoium.adapters.base import BaseAdapter
import random


class OpenAIAdapter(BaseAdapter):
    name = "openai"

    def complete(self, prompt: str, **kwargs) -> str:
        # TODO: call openai.ChatCompletion
        return f"[OpenAI mock] {prompt[:50]}..."

    def embeddings(self, text: str) -> List[float]:
        return [random.random() for _ in range(1536)]
