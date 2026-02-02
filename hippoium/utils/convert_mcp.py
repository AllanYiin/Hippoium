# utils/convert_mcp.py

from typing import Any

from hippoium.utils.converter_registry import BaseConverter


class MCPConverter(BaseConverter):
    """Converter for Anthropic's Model Context Protocol (MCP) format."""
    name = "mcp"

    def convert_memory_item(self, item: Any) -> dict[str, Any]:
        """Convert an internal MemoryItem to MCP resource format (as a dict)."""
        # Assume MemoryItem has attributes: content (str), key (optional id),
        # metadata (dict)
        uri = None
        if hasattr(item, "key") and item.key:
            # use provided key to form URI
            uri = f"memory://{item.key}"
        else:
            # generate a dummy URI if no key (e.g., using id of object)
            uri = f"memory://{id(item)}"
        mime = "text/plain"
        # if metadata has mime_type, use it
        if hasattr(item, "metadata") and item.metadata and "mime_type" in item.metadata:
            mime = item.metadata["mime_type"]
        # prepare MCP resource dictionary
        resource = {
            "uri": uri,
            "mime_type": mime,
            "content": item.content,
        }
        # include a display name or description if available
        if hasattr(item, "metadata") and item.metadata:
            desc = item.metadata.get("description") or item.metadata.get("name")
            if desc:
                resource["description"] = desc
        return resource

    def parse_memory_item(self, data: dict[str, Any]) -> Any:
        """Parse an MCP resource dict back into an internal MemoryItem object."""
        # Expect data keys: uri, mime_type, content, description (optional)
        content = data.get("content")
        # Extract key from URI if possible
        key = None
        uri = data.get("uri", "")
        if uri:
            # strip scheme if present
            key = uri.split("://", 1)[-1]
        # Metadata can include mime_type and description
        metadata = {}
        if "mime_type" in data:
            metadata["mime_type"] = data["mime_type"]
        if "description" in data:
            metadata["description"] = data["description"]
        # Construct MemoryItem (assuming a constructor:
        # MemoryItem(content, key, metadata)).
        # If actual MemoryItem is defined elsewhere, import and use it here.
        try:
            from hippoium.core.memory import MemoryItem as _MemoryItem
            return _MemoryItem(content=content, key=key, metadata=metadata)
        except ImportError:
            # Fallback if core classes are not available (e.g. during tests)
            dummy = type("MemoryItem", (), {})()
            dummy.content = content
            dummy.key = key
            dummy.metadata = metadata
            return dummy

    def convert_prompt_template(self, template: Any) -> dict[str, Any]:
        """Convert an internal PromptTemplate to MCP prompt format."""
        # Assume PromptTemplate has attributes: name (str) and content (str)
        name = template.name if hasattr(template, "name") else None
        prompt_data = {
            "name": name or "prompt",
            "template": template.content,
        }
        # Optionally include description if present
        if hasattr(template, "description"):
            desc = template.description
            if desc:
                prompt_data["description"] = desc
        return prompt_data

    def parse_prompt_template(self, data: dict[str, Any]) -> Any:
        """Parse an MCP prompt dict back into an internal PromptTemplate object."""
        # Expect data keys: name, template, description (optional)
        name = data.get("name") or ""
        content = data.get("template") or ""
        description = data.get("description") or None
        # Construct PromptTemplate (assuming PromptTemplate(name, content, description))
        try:
            from hippoium.core.prompt import PromptTemplate as _PromptTemplate
            return _PromptTemplate(name=name, content=content, description=description)
        except ImportError:
            dummy = type("PromptTemplate", (), {})()
            dummy.name = name
            dummy.content = content
            dummy.description = description
            return dummy

    def convert_tool_spec(self, tool: Any) -> dict[str, Any]:
        """Convert an internal ToolSpec to MCP tool descriptor format."""
        # Assume ToolSpec has attributes: name, description, parameters (dict)
        description = tool.description if hasattr(tool, "description") else ""
        tool_data = {
            "name": tool.name,
            "description": description or "",
            "parameters": tool.parameters if hasattr(tool, "parameters") else {},
        }
        return tool_data

    def parse_tool_spec(self, data: dict[str, Any]) -> Any:
        """Parse an MCP tool descriptor dict back into an internal ToolSpec object."""
        # Expect data keys: name, description, parameters
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
