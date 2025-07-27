
import types
import json
from hippoium.utils.convert_mcp import MCPConverter
from hippoium.utils.converter_registry import ConverterRegistry

def create_dummy_memory(content="Example memory content", key="mem1"):
    return types.SimpleNamespace(content=content, key=key, metadata={"description": "Dummy memory"})

def create_dummy_prompt(name="SamplePrompt", content="This is a prompt template."):
    return types.SimpleNamespace(name=name, content=content, description="Dummy prompt template")

def create_dummy_tool(name="dummy_tool"):
    params = {
        "arg1": {"type": "string", "description": "First argument"},
        "arg2": {"type": "integer", "description": "Second argument"}
    }
    return types.SimpleNamespace(name=name, description="Dummy tool for testing", parameters=params)

def test_mcp_conversion_roundtrip():
    converter = MCPConverter()
    # Create dummy internal objects
    mem = create_dummy_memory()
    prompt = create_dummy_prompt()
    tool = create_dummy_tool()

    # Convert to MCP format
    mem_data = converter.convert_memory_item(mem)
    prompt_data = converter.convert_prompt_template(prompt)
    tool_data = converter.convert_tool_spec(tool)

    # Ensure keys in converted data are as expected
    assert "uri" in mem_data and "content" in mem_data
    assert mem.key in mem_data["uri"]
    assert prompt_data.get("template") == prompt.content
    assert tool_data.get("name") == tool.name

    # Parse back to internal objects
    mem_back = converter.parse_memory_item(mem_data)
    prompt_back = converter.parse_prompt_template(prompt_data)
    tool_back = converter.parse_tool_spec(tool_data)

    # Verify the content and properties are preserved
    assert getattr(mem_back, "content", None) == mem.content
    assert getattr(prompt_back, "content", None) == prompt.content
    assert getattr(tool_back, "name", None) == tool.name
    assert hasattr(tool_back, "parameters") and tool_back.parameters.get("arg1", {}).get("description") == "First argument"

def test_registry_integration_mcp():
    # Prepare a config dict for registry
    config = {
        "default_llm_provider": "anthropic",
        "default_output_format": "mcp",
        "auto_detect_format": True,
        "converters": {
            "mcp": "utils.convert_mcp.MCPConverter",
            "a2a": "utils.convert_a2a.A2AConverter"
        }
    }
    registry = ConverterRegistry(config)
    # Create dummy objects
    mem = create_dummy_memory(content="Hello world", key="memX")
    prompt = create_dummy_prompt(name="TestPrompt", content="Test prompt content.")
    tool = create_dummy_tool(name="test_tool")

    # Convert using registry (to default format which is MCP)
    mem_data = registry.convert_to_format(registry.default_output_format, mem)
    prompt_data = registry.convert_to_format("mcp", prompt)
    tool_data = registry.convert_to_format("mcp", tool)
    # They should match MCPConverter's output keys
    assert isinstance(mem_data, dict) and "uri" in mem_data and "content" in mem_data

    # Form a combined MCP context
    mcp_context = {
        "resources": [mem_data],
        "prompts": [prompt_data],
        "tools": [tool_data]
    }
    # Auto-detect and parse the context back to internal objects
    parsed = registry.parse_context(mcp_context)
    # Verify all sections parsed
    assert "memory_items" in parsed and "prompt_templates" in parsed and "tool_specs" in parsed
    mem_back = parsed["memory_items"][0]
    prompt_back = parsed["prompt_templates"][0]
    tool_back = parsed["tool_specs"][0]
    # Check that content and names are preserved in parsed objects
    assert getattr(mem_back, "content", None) == mem.content
    assert getattr(prompt_back, "content", None) == prompt.content
    assert getattr(tool_back, "name", None) == tool.name