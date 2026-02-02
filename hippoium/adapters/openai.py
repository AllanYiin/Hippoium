"""OpenAI Adapter – 使用官方 API 進行補全與嵌入計算。"""
from __future__ import annotations
from collections.abc import Iterable, Sequence
import importlib
import importlib.util
import logging
import os
import time
from typing import List, Union

from hippoium.adapters.base import BaseAdapter
from hippoium.adapters.retry import RetryConfig, retry
from hippoium.errors import (
    AuthError,
    BadRequestError,
    ProviderError,
    RateLimitError,
    TimeoutError,
    TransientServerError,
    is_retryable_error,
)
from hippoium.ports.domain import Message

_openai_spec = importlib.util.find_spec("openai")
openai = importlib.import_module("openai") if _openai_spec else None

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-3.5-turbo",
        *,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        if openai is None:  # pragma: no cover
            raise ImportError("openai package is required for OpenAIAdapter")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        self.model = model
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()

    def complete(self, prompt: Union[str, Sequence[dict], Sequence[Message]], **kwargs) -> str:
        """呼叫 ChatCompletion 取得模型回覆。"""
        messages = self._normalize_messages(prompt)
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        timeout = kwargs.get("timeout", self.timeout)
        attempts = 0

        def _call(attempt: int) -> dict:
            nonlocal attempts
            attempts = attempt
            try:
                return openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    api_key=self.api_key,
                    timeout=timeout,
                )
            except Exception as exc:  # noqa: BLE001 - wrap SDK exceptions
                raise self._map_openai_error(exc) from exc

        start = time.monotonic()
        response = retry(
            _call,
            config=self.retry_config,
            is_retryable=is_retryable_error,
            logger=logger,
            log_context=f"provider=openai model={model}",
        )
        elapsed = time.monotonic() - start
        request_id = response.get("id")
        logger.info(
            "OpenAI completion success; request_id=%s attempts=%s elapsed=%.2fs model=%s",
            request_id,
            attempts,
            elapsed,
            model,
        )
        return response["choices"][0]["message"]["content"]

    def embeddings(self, text: str, **kwargs) -> List[float]:
        """取得文字的向量嵌入。"""
        return self.embed([text], **kwargs)[0]

    def embed(self, texts: Iterable[str], **kwargs) -> List[List[float]]:
        """取得多筆文字向量嵌入。"""
        model = kwargs.get("model", "text-embedding-ada-002")
        timeout = kwargs.get("timeout", self.timeout)
        input_texts = list(texts)
        attempts = 0

        def _call(attempt: int) -> dict:
            nonlocal attempts
            attempts = attempt
            try:
                return openai.Embedding.create(
                    model=model,
                    input=input_texts,
                    api_key=self.api_key,
                    timeout=timeout,
                )
            except Exception as exc:  # noqa: BLE001 - wrap SDK exceptions
                raise self._map_openai_error(exc) from exc

        start = time.monotonic()
        resp = retry(
            _call,
            config=self.retry_config,
            is_retryable=is_retryable_error,
            logger=logger,
            log_context=f"provider=openai embedding_model={model}",
        )
        elapsed = time.monotonic() - start
        request_id = resp.get("id")
        logger.info(
            "OpenAI embedding success; request_id=%s attempts=%s elapsed=%.2fs model=%s inputs=%s",
            request_id,
            attempts,
            elapsed,
            model,
            len(input_texts),
        )
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

    @staticmethod
    def _map_openai_error(exc: Exception) -> ProviderError:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
        request_id = getattr(exc, "request_id", None)
        name = exc.__class__.__name__.lower()
        message = str(exc) or "OpenAI request failed"

        if status_code == 429 or ("rate" in name and "limit" in name):
            return RateLimitError(message, status_code=status_code, request_id=request_id, cause=exc)
        if "timeout" in name:
            return TimeoutError(message, status_code=status_code, request_id=request_id, cause=exc)
        if status_code and 500 <= status_code <= 599:
            return TransientServerError(message, status_code=status_code, request_id=request_id, cause=exc)
        if status_code in (401, 403) or "auth" in name or "permission" in name:
            return AuthError(message, status_code=status_code, request_id=request_id, cause=exc)
        if status_code and 400 <= status_code <= 499:
            return BadRequestError(message, status_code=status_code, request_id=request_id, cause=exc)
        return ProviderError(message, status_code=status_code, request_id=request_id, cause=exc)
