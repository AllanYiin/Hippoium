"""Context Lab utilities for comparing raw and Hippoium-processed context."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hippoium.core.context_manager import context_session


@dataclass(slots=True)
class CompressionSnapshot:
    turn: int
    raw_tokens: int
    hippo_tokens: int
    raw_cost_usd: float
    hippo_cost_usd: float
    compression_ratio: float
    cost_compression_ratio: float


MODEL_PRICING_USD_PER_1K = {
    "gpt-4o-mini": {
        "input": 0.00015,
        "cached_input": 0.000075,
        "output": 0.0006,
    }
}


def estimate_tokens(text: str) -> int:
    """Rough token estimator to avoid hard dependency on tokenizer libraries."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def serialize_messages(messages: Iterable[dict[str, str]]) -> str:
    chunks: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        chunks.append(f"[{role}]\n{content}")
    return "\n\n".join(chunks)


def build_context_views(
    messages: list[dict[str, str]],
    latest_user_input: str,
) -> tuple[str, str]:
    """Return two text views: raw assistant context vs Hippoium-compressed context."""
    raw_context = serialize_messages(messages)

    with context_session(rag=False) as session:
        for message in messages[-20:]:
            # Keep context focused on non-system turns for compactness.
            if message.get("role") in {"user", "assistant"}:
                session.add_memory(message.get("content", ""))
        hippo_context = session.build(latest_user_input)

    return raw_context, hippo_context


def estimate_turn_cost(
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    pricing = MODEL_PRICING_USD_PER_1K[model]
    non_cached_input_tokens = max(0, input_tokens - cached_input_tokens)
    return (
        (non_cached_input_tokens / 1000) * pricing["input"]
        + (cached_input_tokens / 1000) * pricing["cached_input"]
        + (output_tokens / 1000) * pricing["output"]
    )


def build_compression_snapshot(
    *,
    turn: int,
    raw_context: str,
    hippo_context: str,
    output_tokens: int,
    cache_hit_ratio: float,
    model: str = "gpt-4o-mini",
) -> CompressionSnapshot:
    raw_tokens = estimate_tokens(raw_context)
    hippo_tokens = estimate_tokens(hippo_context)

    raw_cached = int(raw_tokens * cache_hit_ratio)
    hippo_cached = int(hippo_tokens * cache_hit_ratio)

    raw_cost = estimate_turn_cost(
        input_tokens=raw_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=raw_cached,
        model=model,
    )
    hippo_cost = estimate_turn_cost(
        input_tokens=hippo_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=hippo_cached,
        model=model,
    )

    compression_ratio = hippo_tokens / raw_tokens if raw_tokens else 1.0
    cost_compression_ratio = hippo_cost / raw_cost if raw_cost else 1.0

    return CompressionSnapshot(
        turn=turn,
        raw_tokens=raw_tokens,
        hippo_tokens=hippo_tokens,
        raw_cost_usd=raw_cost,
        hippo_cost_usd=hippo_cost,
        compression_ratio=compression_ratio,
        cost_compression_ratio=cost_compression_ratio,
    )
