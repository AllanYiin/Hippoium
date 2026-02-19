"""Factory helpers for creating a lightweight Context Engine Runtime (CER)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hippoium.adapters.base import BaseAdapter
from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.core.hooks import hook_registry
from hippoium.core.neg_vault import NegativeVault
from hippoium.ports.domain import MemoryItem
from hippoium.ports.events import Event


@dataclass
class ContextEngineRuntime:
    """Minimal runtime for prompt building and completion used by tests."""

    llm_adapter: BaseAdapter
    prompt_builder: PromptBuilder = field(default_factory=PromptBuilder)
    enable_negative: bool = False

    def __post_init__(self) -> None:
        self._memory: list[MemoryItem] = []

    def set_prompt_builder(self, builder: PromptBuilder) -> None:
        self.prompt_builder = builder

    def set_llm_adapter(self, adapter: BaseAdapter) -> None:
        self.llm_adapter = adapter

    def add_memory(self, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._memory.append(MemoryItem(content=content, metadata=metadata or {}))

    def build_prompt(self, user_query: str) -> str:
        if self._memory:
            hook_registry.notify(Event.BEFORE_COMPRESSION, self)
            hook_registry.notify(Event.AFTER_COMPRESSION, self)

        hook_registry.notify(Event.BEFORE_RAG_QUERY, user_query, self)

        negative_examples: list[str] = []
        if self.enable_negative:
            default_negative = "Avoid harmful or unsafe outputs."
            if default_negative not in NegativeVault.list_examples():
                NegativeVault.add_example(default_negative)
            negative_examples = NegativeVault.list_examples()

        hook_registry.notify(Event.BEFORE_PROMPT_INJECTION, self)
        messages = self.prompt_builder.build(
            context=list(self._memory),
            user_query=user_query,
            negative_examples=negative_examples,
        )
        return "\n".join(msg.get("content", "") for msg in messages)

    def complete(self, prompt: str, **kwargs: Any) -> str:
        hook_registry.notify(Event.BEFORE_LLM_CALL, prompt)
        output = self.llm_adapter.complete(prompt, **kwargs)
        hook_registry.notify(Event.AFTER_LLM_CALL, output)
        return output


def create_cer(
    *,
    adapter: BaseAdapter,
    memory_config: Any | None = None,
    retriever_config: dict[str, Any] | None = None,
    enable_negative: bool = False,
    **runtime_kwargs: Any,
) -> ContextEngineRuntime:
    """Build a ready-to-use CER runtime.

    `memory_config`, `retriever_config`, and extra kwargs are accepted for backward
    compatibility but intentionally ignored by this lightweight implementation.
    """
    _ = (memory_config, retriever_config, runtime_kwargs)
    cer = ContextEngineRuntime(llm_adapter=adapter, enable_negative=enable_negative)
    cer.set_prompt_builder(PromptBuilder())
    return cer
