# hippoium/ports/mcp.py

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from hippoium.ports.domain import MemoryItem, ToolSpec


class PromptTemplate(BaseModel):
    """Represents a prompt template with optional placeholders."""

    content: str
    name: str | None = None
    description: str | None = None


class MCPMessage(BaseModel):
    """
    Represents a message in the Model Context Protocol (MCP) format.

    The message follows JSON-RPC 2.0 and can be converted to or from
    MemoryItem, PromptTemplate, and ToolSpec.
    """

    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str | None = None
    params: Any | None = None
    result: Any | None = None
    error: Any | None = None

    @classmethod
    def from_memory_item(
        cls,
        item: MemoryItem,
        request_id: int | str | None = None,
    ) -> MCPMessage:
        """Create an MCP message that carries memory content."""
        return cls(
            jsonrpc="2.0",
            id=request_id,
            method="loadMemory",
            params={"content": item.content, "metadata": item.metadata},
        )

    @classmethod
    def from_prompt(
        cls,
        prompt: PromptTemplate,
        request_id: int | str | None = None,
    ) -> MCPMessage:
        """Create an MCP request message from a prompt template."""
        return cls(
            jsonrpc="2.0",
            id=request_id,
            method="submitPrompt",
            params={"content": prompt.content},
        )

    @classmethod
    def from_tool_spec(
        cls,
        tool: ToolSpec,
        request_id: int | str | None = None,
    ) -> MCPMessage:
        """Create an MCP message from a tool specification."""
        return cls(
            jsonrpc="2.0",
            id=request_id,
            method="registerTool",
            params={
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema,
            },
        )

    def to_memory_item(self) -> MemoryItem:
        """Convert an MCP message to MemoryItem when applicable."""
        data = None
        if isinstance(self.result, dict):
            data = self.result
        elif (
            isinstance(self.params, dict)
            and self.method
            and "Memory" in self.method
        ):
            data = self.params

        if data is not None:
            content = data.get("content", "")
            metadata = data.get("metadata") or {}
            return MemoryItem(content=content, metadata=metadata)

        raise ValueError("MCPMessage cannot be converted to MemoryItem")

    def to_prompt_template(self) -> PromptTemplate:
        """Convert an MCP message to PromptTemplate when applicable."""
        if isinstance(self.params, dict) and self.method == "submitPrompt":
            return PromptTemplate(content=self.params.get("content", ""))
        if isinstance(self.result, dict) and "content" in self.result:
            return PromptTemplate(content=self.result.get("content", ""))
        if isinstance(self.result, str):
            return PromptTemplate(content=self.result)

        raise ValueError("MCPMessage cannot be converted to PromptTemplate")

    def to_tool_spec(self) -> ToolSpec:
        """Convert an MCP message to ToolSpec when applicable."""
        if isinstance(self.params, dict) and self.method == "registerTool":
            return ToolSpec(
                name=self.params.get("name", ""),
                description=self.params.get("description"),
                args_schema=self.params.get("parameters"),
            )
        if isinstance(self.result, dict) and "name" in self.result:
            return ToolSpec(
                name=self.result.get("name", ""),
                description=self.result.get("description"),
                args_schema=self.result.get("parameters"),
            )

        raise ValueError("MCPMessage cannot be converted to ToolSpec")
