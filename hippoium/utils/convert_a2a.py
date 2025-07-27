# utils/convert_a2a.py

from typing import Any, Dict
from hippoium.utils.converter_registry import BaseConverter

class A2AConverter(BaseConverter):
    """Converter for Google's Agent-to-Agent (A2A) protocol format."""
    name = "a2a"

    def convert_memory_item(self, item: Any) -> Dict[str, Any]:
        """Convert an internal MemoryItem to A2A artifact format (as a dict)."""
        # Represent memory as an A2A artifact with text content.
        artifact_id = getattr(item, "key", None) or str(id(item))
        artifact = {
            "artifactId": artifact_id,
            "name": getattr(item, "name", None) or "memory",
            "parts": [
                {
                    "kind": "text",
                    "text": item.content
                }
            ]
        }
        # If the memory content is not plain text, e.g. binary data,
        # you could use kind "file" with base64 encoding (not shown here).
        return artifact

    def parse_memory_item(self, data: Dict[str, Any]) -> Any:
        """Parse an A2A artifact dict back into an internal MemoryItem object."""
        # Expect data keys: artifactId, name, parts (with at least one part containing content)
        parts = data.get("parts", [])
        content = ""
        if parts:
            # find the first text part
            for part in parts:
                if part.get("kind") == "text" and "text" in part:
                    content = part["text"]
                    break
            else:
                # if no text part, and there's a file part, skip decoding for simplicity
                content = str(parts[0])  # fallback: represent non-text content as str
        key = data.get("artifactId")
        metadata = {"name": data.get("name", "")}
        try:
            from hippoium.core.memory import MemoryItem as _MemoryItem
            return _MemoryItem(content=content, key=key, metadata=metadata)
        except ImportError:
            dummy = type("MemoryItem", (), {})()
            dummy.content = content
            dummy.key = key
            dummy.metadata = metadata
            return dummy

    def convert_prompt_template(self, template: Any) -> Dict[str, Any]:
        """Convert an internal PromptTemplate to A2A message format (system role)."""
        # Represent prompt template as a system message in A2A.
        prompt_message = {
            "role": "system",
            "parts": [
                {
                    "kind": "text",
                    "text": template.content
                }
            ]
        }
        # (A2A typically doesn't include prompt templates in agent cards, but we model it as a message.)
        return prompt_message

    def parse_prompt_template(self, data: Dict[str, Any]) -> Any:
        """Parse an A2A message dict (system prompt) back into an internal PromptTemplate object."""
        # Expect data keys: role, parts (list of parts with text).
        parts = data.get("parts", [])
        content = ""
        if parts:
            for part in parts:
                if part.get("kind") == "text" and "text" in part:
                    content = part["text"]
                    break
        name = "system_prompt"
        description = None
        try:
            from hippoium.core.prompt import PromptTemplate as _PromptTemplate
            return _PromptTemplate(name=name, content=content, description=description)
        except ImportError:
            dummy = type("PromptTemplate", (), {})()
            dummy.name = name
            dummy.content = content
            dummy.description = description
            return dummy

    def convert_tool_spec(self, tool: Any) -> Dict[str, Any]:
        """Convert an internal ToolSpec to A2A capability format."""
        # Represent tool as an A2A capability (similar to an agent card entry).
        capability = {
            "name": tool.name,
            "description": getattr(tool, "description", "") or "",
            "parameters": tool.parameters if hasattr(tool, "parameters") else {}
        }
        # In a full A2A Agent Card, capabilities might include endpoints or auth, which are omitted here.
        return capability

    def parse_tool_spec(self, data: Dict[str, Any]) -> Any:
        """Parse an A2A capability dict back into an internal ToolSpec object."""
        name = data.get("name") or ""
        description = data.get("description") or ""
        parameters = data.get("parameters") or {}
        try:
            from hippoium.core.tool import ToolSpec as _ToolSpec
            return _ToolSpec(name=name, description=description, parameters=parameters)
        except ImportError:
            dummy = type("ToolSpec", (), {})()
            dummy.name = name
            dummy.description = description
            dummy.parameters = parameters
            return dummy