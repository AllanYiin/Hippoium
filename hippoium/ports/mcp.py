# hippoium/ports/mcp.py

from typing import Optional, Union, Any, Dict, List
from pydantic import BaseModel

class MemoryItem(BaseModel):
    """Represents a unit of memory (context) with optional metadata."""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class PromptTemplate(BaseModel):
    """Represents a prompt template with optional placeholders."""
    content: str
    name: Optional[str] = None
    description: Optional[str] = None

class ToolSpec(BaseModel):
    """Represents a tool's specification for use in context or MCP integration."""
    name: str
    description: Optional[str] = None
    # Optionally, define input/output schema for the tool if needed
    parameters_schema: Optional[Dict[str, Any]] = None

class MCPMessage(BaseModel):
    """
    Represents a message in the Model Context Protocol (MCP) format (JSON-RPC 2.0).
    Can be converted to/from internal structures like MemoryItem, PromptTemplate, and ToolSpec.
    """
    jsonrpc: str = "2.0"
    id: Optional[Union[int, str]] = None
    method: Optional[str] = None
    params: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[Any] = None

    @classmethod
    def from_memory_item(cls, item: MemoryItem, request_id: Optional[Union[int, str]] = None) -> "MCPMessage":
        """
        Create an MCP message from a MemoryItem. This could be used to send memory content via MCP.
        For example, using a hypothetical 'loadMemory' method to provide context.
        """
        return cls(jsonrpc="2.0", id=request_id, method="loadMemory",
                   params={"content": item.content, "metadata": item.metadata})

    @classmethod
    def from_prompt(cls, prompt: PromptTemplate, request_id: Optional[Union[int, str]] = None) -> "MCPMessage":
        """
        Create an MCP request message from a PromptTemplate.
        This could be used to send a prompt to an MCP server or client.
        """
        return cls(jsonrpc="2.0", id=request_id, method="submitPrompt",
                   params={"content": prompt.content})

    @classmethod
    def from_tool_spec(cls, tool: ToolSpec, request_id: Optional[Union[int, str]] = None) -> "MCPMessage":
        """
        Create an MCP message from a ToolSpec.
        This could be used to register or describe a tool in JSON-RPC format (e.g., for tool availability).
        """
        return cls(jsonrpc="2.0", id=request_id, method="registerTool",
                   params={"name": tool.name, "description": tool.description,
                           "parameters": tool.parameters_schema})

    def to_memory_item(self) -> MemoryItem:
        """
        Convert an MCP message to a MemoryItem, if possible.
        If this message contains memory content (in params or result), produce a MemoryItem.
        """
        data = None
        if isinstance(self.result, dict):
            data = self.result
        elif isinstance(self.params, dict) and (self.method and "Memory" in self.method):
            data = self.params
        if data is not None:
            content = data.get("content", "")
            metadata = data.get("metadata")
            return MemoryItem(content=content, metadata=metadata)
        raise ValueError("MCPMessage cannot be converted to MemoryItem")

    def to_prompt_template(self) -> PromptTemplate:
        """
        Convert an MCP message to a PromptTemplate, if possible.
        If this message contains prompt content (e.g. in params or result), return a PromptTemplate.
        """
        if isinstance(self.params, dict) and self.method == "submitPrompt":
            return PromptTemplate(content=self.params.get("content", ""))
        if isinstance(self.result, dict) and "content" in self.result:
            # In case the response encapsulates prompt content
            return PromptTemplate(content=self.result.get("content", ""))
        if isinstance(self.result, str):
            # If the result is a direct string, treat it as prompt content
            return PromptTemplate(content=self.result)
        raise ValueError("MCPMessage cannot be converted to PromptTemplate")

    def to_tool_spec(self) -> ToolSpec:
        """
        Convert an MCP message to a ToolSpec, if possible.
        If this message contains tool specification details, return a ToolSpec.
        """
        if isinstance(self.params, dict) and self.method == "registerTool":
            return ToolSpec(name=self.params.get("name", ""),
                            description=self.params.get("description"),
                            parameters_schema=self.params.get("parameters"))
        if isinstance(self.result, dict) and "name" in self.result:
            # If result contains tool info
            return ToolSpec(name=self.result.get("name", ""),
                            description=self.result.get("description"),
                            parameters_schema=self.result.get("parameters"))
        raise ValueError("MCPMessage cannot be converted to ToolSpec")