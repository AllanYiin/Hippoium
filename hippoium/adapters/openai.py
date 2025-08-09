"""OpenAI Adapter – 使用官方 API 進行補全與嵌入計算。"""
from __future__ import annotations
from typing import List, Union, Sequence
import os

from hippoium.adapters.base import BaseAdapter

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
        openai.api_key = self.api_key
        self.model = model

    def complete(self, prompt: Union[str, Sequence[dict]], **kwargs) -> str:
        """呼叫 ChatCompletion 取得模型回覆。"""
        messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
        response = openai.ChatCompletion.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response["choices"][0]["message"]["content"]

    def embeddings(self, text: str, **kwargs) -> List[float]:
        """取得文字的向量嵌入。"""
        model = kwargs.get("model", "text-embedding-ada-002")
        resp = openai.Embedding.create(model=model, input=text)
        return resp["data"][0]["embedding"]

