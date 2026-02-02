# tests/test_convert_a2a.py

import types

from hippoium.utils.convert_a2a import A2AConverter
from hippoium.utils.converter_registry import ConverterRegistry


def create_dummy_memory(content="Memory content for A2A", key="memA2A"):
    return types.SimpleNamespace(
        content=content, key=key, name="MemoryItem"
    )  # include name for artifact


def create_dummy_prompt(name="A2APrompt", content="System instruction."):
    return types.SimpleNamespace(name=name, content=content)


def create_dummy_tool(name="a2a_tool"):
    params = {"x": {"type": "number", "description": "X value"}}
    return types.SimpleNamespace(
        name=name, description="Tool for A2A test", parameters=params
    )


def test_a2a_conversion_roundtrip():
    converter = A2AConverter()
    mem = create_dummy_memory()
    prompt = create_dummy_prompt()
    tool = create_dummy_tool()

    # Convert to A2A format
    mem_data = converter.convert_memory_item(mem)
    prompt_msg = converter.convert_prompt_template(prompt)
    tool_cap = converter.convert_tool_spec(tool)

    # Check structure of converted data
    assert "artifactId" in mem_data and mem_data["parts"][0].get("text") == mem.content
    assert prompt_msg.get("role") == "system" and isinstance(
        prompt_msg.get("parts"), list
    )
    assert tool_cap["name"] == tool.name and "parameters" in tool_cap

    # Parse back to internal objects
    mem_back = converter.parse_memory_item(mem_data)
    prompt_back = converter.parse_prompt_template(prompt_msg)
    tool_back = converter.parse_tool_spec(tool_cap)

    # Verify content and fields
    assert getattr(mem_back, "content", None) == mem.content
    assert getattr(prompt_back, "content", None) == prompt.content
    assert getattr(tool_back, "name", None) == tool.name
    assert hasattr(tool_back, "parameters") and "x" in tool_back.parameters

def test_registry_integration_a2a():
    config = {
        "default_llm_provider": "anthropic",
        "default_output_format": "a2a",
        "auto_detect_format": True,
        "converters": {
            "mcp": "utils.convert_mcp.MCPConverter",
            "a2a": "utils.convert_a2a.A2AConverter",
        },
    }
    registry = ConverterRegistry(config)
    mem = create_dummy_memory(content="A2A mem content", key="memY")
    prompt = create_dummy_prompt(name="Instruction", content="Follow the rules.")
    tool = create_dummy_tool(name="calc_tool")

    # Convert using registry to A2A format
    mem_data = registry.convert_to_format("a2a", mem)
    prompt_msg = registry.convert_to_format("a2a", prompt)
    tool_cap = registry.convert_to_format("a2a", tool)
    # Build an A2A context (Agent Card + message history)
    a2a_context = {
        "capabilities": [tool_cap],
        "artifacts": [mem_data],
        "history": [prompt_msg],
    }
    # Auto-detect format and parse context
    fmt = registry.detect_format(a2a_context)
    assert fmt == "a2a"
    parsed = registry.parse_context(a2a_context)
    # Verify parsed content
    assert (
        "tool_specs" in parsed
        and "memory_items" in parsed
        and "prompt_templates" in parsed
    )
    mem_back = parsed["memory_items"][0]
    prompt_back = parsed["prompt_templates"][0]
    tool_back = parsed["tool_specs"][0]
    assert getattr(mem_back, "content", None) == mem.content
    assert getattr(prompt_back, "content", None) == prompt.content
    assert getattr(tool_back, "name", None) == tool.name
