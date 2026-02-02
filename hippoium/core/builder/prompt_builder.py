"""
PromptBuilder – assemble trimmed chunks into final prompt.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from hippoium.core.builder.formatters import (
    format_context_items,
    format_negative_examples,
    format_tools_block,
    format_user_query,
    serialize_tools,
)
from hippoium.core.utils.token_counter import count_tokens
from hippoium.ports.domain import MemoryItem, ToolSpec
from hippoium.core.builder.template_registry import TemplateRegistry


@dataclass
class PromptPayload:
    messages: List[dict]
    tools: List[dict]
    token_count: int
    trimmed: dict


class PromptBuilder:
    """Builds the final prompt (as chat message list) by injecting context and user query into a template."""
    def __init__(self, template_path: str = ""):
        self.registry = TemplateRegistry()
        if template_path:
            try:
                self.registry.load_from_path(template_path)
            except FileNotFoundError:
                pass  # optional

    def build(
        self,
        template_id: Optional[str] = None,
        context: Optional[List[MemoryItem]] = None,
        user_query: str = "",
        negative_examples: Optional[List[str]] = None,
        tools: Optional[List[ToolSpec]] = None,
        token_budget: Optional[int] = None,
    ) -> List[dict]:
        """
        Returns a list of {"role": ..., "content": ...} messages suitable for Chat API.
        """
        payload = self.build_payload(
            template_id=template_id,
            context=context,
            user_query=user_query,
            negative_examples=negative_examples,
            tools=tools,
            token_budget=token_budget,
        )
        return payload.messages

    def build_payload(
        self,
        template_id: Optional[str] = None,
        context: Optional[List[MemoryItem]] = None,
        user_query: str = "",
        negative_examples: Optional[List[str]] = None,
        tools: Optional[List[ToolSpec]] = None,
        token_budget: Optional[int] = None,
    ) -> PromptPayload:
        messages: List[dict] = []
        context = list(context or [])
        negative_examples = list(negative_examples or [])
        tools = list(tools or [])
        tools_payload = serialize_tools(tools)
        trimmed = {"context": 0, "negative_examples": 0, "tools": 0}

        if template_id:
            template = self.registry.get_template(template_id)
            if template:
                messages = self._build_from_template(
                    template_id,
                    context,
                    user_query,
                    negative_examples,
                    tools,
                )
                messages, trimmed = self._apply_token_budget(
                    template_id,
                    messages,
                    context,
                    user_query,
                    negative_examples,
                    tools,
                    token_budget,
                )
                return PromptPayload(
                    messages=messages,
                    tools=tools_payload,
                    token_count=self._count_message_tokens(messages),
                    trimmed=trimmed,
                )

        # fallback: no template
        for item in context:
            role = item.metadata.get("role", "assistant")
            messages.append({"role": role, "content": item.content})
        messages.append({"role": "user", "content": user_query})
        if token_budget is not None:
            messages = self._trim_fallback_messages(messages, token_budget)

        return PromptPayload(
            messages=messages,
            tools=tools_payload,
            token_count=self._count_message_tokens(messages),
            trimmed=trimmed,
        )

    def _build_from_template(
        self,
        template_id: str,
        context: List[MemoryItem],
        user_query: str,
        negative_examples: List[str],
        tools: List[ToolSpec],
    ) -> List[dict]:
        template = self.registry.get_template(template_id)
        if not template:
            return []
        slots = self.registry.get_template_slots(template_id)
        fill_vals: dict[str, str] = {}

        if any(slot in slots for slot in ("history", "context")):
            formatted_context = format_context_items(context)
            fill_vals["history"] = formatted_context
            fill_vals["context"] = formatted_context

        if any(slot in slots for slot in ("negative_examples", "negatives")):
            neg_text = format_negative_examples(negative_examples)
            fill_vals["negative_examples"] = neg_text
            fill_vals["negatives"] = neg_text

        if "tools" in slots:
            fill_vals["tools"] = format_tools_block(tools)

        if "user_query" in slots:
            fill_vals["user_query"] = format_user_query(user_query)

        prompt_text = template.content.format(**fill_vals)
        lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]

        # strict role parsing (trusted template only)
        known_roles = ("user", "assistant", "system")
        messages: List[dict] = []
        for line in lines:
            if ":" in line:
                role_candidate, content = line.split(":", 1)
                role = role_candidate.strip().lower()
                if role in known_roles:
                    messages.append({"role": role, "content": content.lstrip()})
                else:
                    messages.append({"role": "system", "content": line})
            else:
                messages.append({"role": "system", "content": line})
        return messages

    def _apply_token_budget(
        self,
        template_id: str,
        messages: List[dict],
        context: List[MemoryItem],
        user_query: str,
        negative_examples: List[str],
        tools: List[ToolSpec],
        token_budget: Optional[int],
    ) -> tuple[List[dict], dict]:
        trimmed = {"context": 0, "negative_examples": 0, "tools": 0}
        if token_budget is None:
            return messages, trimmed

        while self._count_message_tokens(messages) > token_budget:
            if context:
                context.pop(0)
                trimmed["context"] += 1
            elif tools:
                tools.pop()
                trimmed["tools"] += 1
            elif negative_examples:
                negative_examples.pop()
                trimmed["negative_examples"] += 1
            else:
                break
            messages = self._build_from_template(
                template_id,
                context,
                user_query,
                negative_examples,
                tools,
            )
            if not messages:
                break
        return messages, trimmed

    def _trim_fallback_messages(self, messages: List[dict], token_budget: int) -> List[dict]:
        trimmed = list(messages)
        while trimmed and self._count_message_tokens(trimmed) > token_budget:
            if len(trimmed) > 1:
                trimmed.pop(0)
            else:
                break
        return trimmed

    def _count_message_tokens(self, messages: List[dict]) -> int:
        return int(count_tokens([m.get("content", "") for m in messages]))
