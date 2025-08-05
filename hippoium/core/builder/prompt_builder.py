"""
PromptBuilder – assemble trimmed chunks into final prompt.
"""
from __future__ import annotations
from typing import List, Optional
from hippoium.ports.mcp import MemoryItem
from hippoium.core.builder.template_registry import TemplateRegistry


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
        context: List[MemoryItem] = [],
        user_query: str = ""
    ) -> List[dict]:
        """
        Returns a list of {"role": ..., "content": ...} messages suitable for Chat API.
        """
        messages: List[dict] = []

        if template_id:
            template = self.registry.get_template(template_id)
            if template:
                slots = self.registry.get_template_slots(template_id)
                fill_vals = {}

                if any(slot in slots for slot in ("history", "context")):
                    history_lines = []
                    for item in context:
                        role = item.metadata.get("role", "assistant")
                        history_lines.append(f"{role.capitalize()}: {item.content}")
                    fill_vals["history"] = "\n".join(history_lines)
                    fill_vals["context"] = fill_vals["history"]

                if "user_query" in slots:
                    fill_vals["user_query"] = user_query

                prompt_text = template.content.format(**fill_vals)
                lines = [line.strip() for line in prompt_text.splitlines() if line.strip()]

                # strict role parsing
                known_roles = ("user", "assistant", "system")
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

        # fallback: no template
        for item in context:
            role = item.metadata.get("role", "assistant")
            messages.append({"role": role, "content": item.content})
        messages.append({"role": "user", "content": user_query})

        return messages