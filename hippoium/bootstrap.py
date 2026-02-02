from __future__ import annotations

from datetime import timedelta
from typing import Tuple

from hippoium.adapters.openai import OpenAIAdapter
from hippoium.core.retriever.scorer import HybridScorer
from hippoium.engine import DefaultContextEngine
from hippoium.ports.domain import Config
from hippoium.ports.protocols import EmbeddingClient, LLMClient


def build_config(
    *,
    token_budget: int = 4096,
    cache_tiers: dict | None = None,
    provider: dict | None = None,
    default_model: str | None = None,
    max_messages: int | None = None,
    cache_ttl_s: int | None = None,
) -> Config:
    return Config(
        token_budget=token_budget,
        cache_tiers=cache_tiers or {},
        provider=provider or {},
        default_model=default_model,
        max_messages=max_messages,
        cache_ttl_s=cache_ttl_s,
    )


def _build_default_engine(config: Config) -> DefaultContextEngine:
    session_ttl = None
    if config.cache_ttl_s is not None:
        session_ttl = timedelta(seconds=config.cache_ttl_s)
    return DefaultContextEngine(
        max_messages=config.max_messages or 50,
        max_tokens=config.token_budget,
        session_ttl=session_ttl,
    )


def _build_openai_adapter(config: Config) -> OpenAIAdapter:
    provider = config.provider
    return OpenAIAdapter(
        api_key=provider.get("api_key"),
        model=provider.get("model", config.default_model or "gpt-3.5-turbo"),
    )


def bootstrap(
    config: Config | None = None,
    llm_client: LLMClient | None = None,
    embedding_client: EmbeddingClient | None = None,
) -> Tuple[DefaultContextEngine, LLMClient, EmbeddingClient, HybridScorer]:
    cfg = config or build_config()
    engine = _build_default_engine(cfg)

    if llm_client is None or embedding_client is None:
        provider_type = (cfg.provider or {}).get("type", "openai")
        if provider_type == "openai":
            adapter = _build_openai_adapter(cfg)
            llm_client = llm_client or adapter
            embedding_client = embedding_client or adapter
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    scorer = HybridScorer(embedding_client=embedding_client)
    return engine, llm_client, embedding_client, scorer
