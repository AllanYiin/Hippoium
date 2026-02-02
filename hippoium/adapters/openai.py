"""OpenAI Adapter – 使用官方 API 進行補全與嵌入計算。"""
from __future__ import annotations
from collections.abc import Iterable, Sequence
from typing import List, Union
import os

from hippoium.adapters.base import BaseAdapter
from hippoium.ports.domain import Message

try:  # pragma: no cover - optional dependency
    import openai
except Exception:  # pragma: no cover
    openai = None


class OpenAIAdapter(BaseAdapter):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str = "gpt-3.5-turbo") -> None:
        if openai is None:  # pragma: no cover
            raise ImportError("openai package is required for OpenAIAdapter")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.model = model

    def complete(self, prompt: Union[str, Sequence[dict], Sequence[Message]], **kwargs) -> str:
        """呼叫 ChatCompletion 取得模型回覆。"""
        messages = self._normalize_messages(prompt)
        response = openai.ChatCompletion.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.7),
            api_key=self.api_key,
        )
        return response["choices"][0]["message"]["content"]

    def embeddings(self, text: str, **kwargs) -> List[float]:
        """取得文字的向量嵌入。"""
        return self.embed([text], **kwargs)[0]

    def embed(self, texts: Iterable[str], **kwargs) -> List[List[float]]:
        """取得多筆文字向量嵌入。"""
        model = kwargs.get("model", "text-embedding-ada-002")
        input_texts = list(texts)
        resp = openai.Embedding.create(model=model, input=input_texts, api_key=self.api_key)
        return [item["embedding"] for item in resp["data"]]

    @staticmethod
    def _normalize_messages(prompt: Union[str, Sequence[dict], Sequence[Message]]) -> list[dict]:
        if isinstance(prompt, str):
            return [{"role": "user", "content": prompt}]
        if isinstance(prompt, Sequence):
            messages = list(prompt)
            for idx, msg in enumerate(messages):
                if isinstance(msg, Message):
                    messages[idx] = {"role": msg.role, "content": msg.content}
                    continue
                if not isinstance(msg, dict):
                    raise ValueError(f"Message at index {idx} must be a dict")
                if "role" not in msg or "content" not in msg:
                    raise ValueError(f"Message at index {idx} must include role and content")
            return list(messages)
        raise ValueError("Prompt must be a string or a sequence of message dicts")
