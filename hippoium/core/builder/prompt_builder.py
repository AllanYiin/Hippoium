"""
PromptBuilder – assemble trimmed chunks into final prompt.
"""
from __future__ import annotations
import re
from typing import List, Optional
from hippoium.ports.domain import MemoryItem, ToolSpec
from hippoium.core.builder.template_registry import TemplateRegistry
from hippoium.core.builder.formatting import (
    format_context_items,
    format_negative_examples,
    format_tool_specs,
)
from hippoium.core.utils.token_counter import count_tokens


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
        history: Optional[List[MemoryItem]] = None,
        user_query: str = "",
        negative_examples: Optional[List[str]] = None,
        tools: Optional[List[ToolSpec]] = None,
        token_budget: Optional[int] = None,
    ) -> List[dict]:
        """
        Returns a list of {"role": ..., "content": ...} messages suitable for Chat API.
        """
        context_items = list(context or [])
        history_items = list(history or [])
        negative_examples = negative_examples or []
        tools = tools or []

        if history is None:
            history_items = context_items

        def _render_messages(
            ctx_items: List[MemoryItem],
            hist_items: List[MemoryItem],
            negs: List[str],
            tool_specs: List[ToolSpec],
        ) -> List[dict]:
            output: List[dict] = []
            if template_id:
                template = self.registry.get_template(template_id)
                if template:
                    slots = self.registry.get_template_slots(template_id)
                    fill_vals = {}

                    if any(slot in slots for slot in ("history", "context")):
                        history_text = format_context_items(hist_items)
                        context_text = format_context_items(ctx_items)
                        fill_vals["history"] = history_text
                        fill_vals["context"] = context_text

                    if any(slot in slots for slot in ("negative_examples", "negatives")):
                        neg_text = format_negative_examples(negs)
                        fill_vals["negative_examples"] = neg_text
                        fill_vals["negatives"] = neg_text

                    if "tools" in slots:
                        fill_vals["tools"] = format_tool_specs(tool_specs)

                    if "user_query" in slots:
                        fill_vals["user_query"] = user_query

                    prompt_text = template.content.format(**fill_vals)
                    lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]

                    role_pattern = re.compile(r"^(user|assistant|system)\\s*:", re.IGNORECASE)
                    for line in lines:
                        match = role_pattern.match(line)
                        if match:
                            role = match.group(1).lower()
                            content = line.split(":", 1)[1].lstrip()
                            output.append({"role": role, "content": content})
                        else:
                            output.append({"role": "system", "content": line})
                    return output
            for item in ctx_items:
                role = item.metadata.get("role", "assistant")
                output.append({"role": role, "content": item.content})
            output.append({"role": "user", "content": user_query})
            return output

        messages = _render_messages(context_items, history_items, negative_examples, tools)
        if token_budget is not None:
            messages = self._apply_token_budget(
                context_items=context_items,
                history_items=history_items,
                negative_examples=negative_examples,
                tools=tools,
                user_query=user_query,
                token_budget=token_budget,
                render=_render_messages,
            )
        return messages

    @staticmethod
    def _estimate_tokens(messages: List[dict]) -> int:
        return count_tokens([msg["content"] for msg in messages])

    def _apply_token_budget(
        self,
        *,
        context_items: List[MemoryItem],
        history_items: List[MemoryItem],
        negative_examples: List[str],
        tools: List[ToolSpec],
        user_query: str,
        token_budget: int,
        render,
    ) -> List[dict]:
        ctx_items = list(context_items)
        hist_items = list(history_items)
        negs = list(negative_examples)
        tool_specs = list(tools)

        messages = render(ctx_items, hist_items, negs, tool_specs)
        estimated = self._estimate_tokens(messages)

        while estimated > token_budget and ctx_items:
            ctx_items.pop(0)
            if history_items is context_items:
                hist_items = ctx_items
            messages = render(ctx_items, hist_items, negs, tool_specs)
            estimated = self._estimate_tokens(messages)

        while estimated > token_budget and history_items is not context_items and hist_items:
            hist_items.pop(0)
            messages = render(ctx_items, hist_items, negs, tool_specs)
            estimated = self._estimate_tokens(messages)

        while estimated > token_budget and tool_specs:
            tool_specs.pop()
            messages = render(ctx_items, hist_items, negs, tool_specs)
            estimated = self._estimate_tokens(messages)

        while estimated > token_budget and negs:
            negs.pop()
            messages = render(ctx_items, hist_items, negs, tool_specs)
            estimated = self._estimate_tokens(messages)

        return messages
