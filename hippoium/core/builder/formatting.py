from __future__ import annotations

import json
import re
from typing import Any, Iterable, Sequence

from hippoium.ports.domain import MemoryItem, ToolSpec

_TOOL_NAME_ALLOWLIST = re.compile(r"[^a-zA-Z0-9_.-]+")
_ROLE_ALLOWLIST = {"user", "assistant", "system"}


def _normalize_role(role: str) -> str:
    role_lower = role.strip().lower()
    if role_lower in _ROLE_ALLOWLIST:
        return role_lower
    return "unknown"


def sanitize_tool_name(name: str) -> str:
    cleaned = _TOOL_NAME_ALLOWLIST.sub("_", name.strip())
    return cleaned or "tool"


def sanitize_text(text: str) -> str:
    return text.replace("\r", " ").strip()


def format_data_section(label: str, items: Sequence[Any]) -> str:
    if not items:
        return ""
    lines = [f"{label}:"]
    for item in items:
        payload = json.dumps(item, ensure_ascii=False, sort_keys=True)
        lines.append(f"  - {payload}")
    return "\n".join(lines)


def format_context_items(items: Iterable[MemoryItem]) -> str:
    entries = [
        {"role": _normalize_role(item.metadata.get("role", "assistant")), "content": item.content}
        for item in items
    ]
    return format_data_section("CONTEXT_MESSAGES", entries)


def format_negative_examples(negatives: Sequence[str]) -> str:
    cleaned = [sanitize_text(item) for item in negatives]
    return format_data_section("NEGATIVE_EXAMPLES", cleaned)


def format_tool_specs(tools: Sequence[ToolSpec]) -> str:
    entries = []
    for tool in tools:
        entries.append(
            {
                "name": sanitize_tool_name(tool.name),
                "description": sanitize_text(tool.description or ""),
                "parameters": tool.parameters,
            }
        )
    return format_data_section("TOOLS_DATA", entries)


def format_user_query(query: str) -> str:
    return format_data_section("USER_QUERY", [sanitize_text(query)])
