import pytest
from datetime import timedelta
from hippoium.engine import DefaultContextEngine, _common_overlap
from hippoium.core.neg_vault import NegativeVault
from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.ports.mcp import MemoryItem, ToolSpec


def test_conversation_input_and_memory_management():
    # 建立引擎，設定最大訊息數、最大 token 數、session 存活時間
    engine = DefaultContextEngine(max_messages=3, max_tokens=100, session_ttl=timedelta(minutes=5))
    # 寫入使用者與助理的對話輪次
    engine.write_turn(role="user", content="Hello", metadata={"conv_id": "chat1", "user_id": "alice"})
    engine.write_turn(role="assistant", content="Hi, how can I help you?", metadata={"conv_id": "chat1"})
    engine.write_turn(role="user", content="I need assistance with my account.", metadata={"conv_id": "chat1", "user_id": "alice"})
    engine.write_turn(role="assistant", content="Sure, I can help with your account.", metadata={"conv_id": "chat1"})

    # 檢查短期記憶（MBuffer）：不應包含 "Hello"
    m_vals = list(engine.m_buffer.data.values())
    m_contents = [entry["value"] for entry in m_vals]
    assert "Hello" not in m_contents
    assert "Sure, I can help with your account." in m_contents

    # 檢查長期記憶（LVector）是否包含使用者訊息
    lvec = engine.l_vector.get("user:alice")
    assert lvec is not None

    # 檢查 session 的完整歷史（SCache）：應包含 "Hello"
    ctx = engine.get_context_for_scope(scope="task", key="chat1")
    ctx_contents = [item.content for item in ctx]
    assert any("Hello" in c for c in ctx_contents)
    assert "Sure, I can help with your account." in ctx_contents[-1]


def test_automatic_annotation_and_filtering():
    # 測試自動標註與過濾功能
    engine = DefaultContextEngine()
    # 新增一則應標記為警告的訊息（助理拒絕）
    engine.write_turn(role="assistant", content="I'm sorry, I cannot do that request.", metadata={"conv_id": "chat2"})
    # 新增一則應標記為錯誤的訊息（包含 'Error'）
    engine.write_turn(role="assistant", content="Error: Invalid input provided.", metadata={"conv_id": "chat2"})
    engine.write_turn(role="assistant", content="Here is the information you requested.", metadata={"conv_id": "chat2"})
    # 取得排除錯誤訊息的上下文
    ctx = engine.get_context_for_scope(scope="task", key="chat2", filters={"exclude_err": True})
    contents = [item.content for item in ctx]
    # 檢查錯誤訊息已被過濾
    assert any("the information you requested" in txt for txt in contents)
    assert all("Error: Invalid input" not in txt for txt in contents)
    # 驗證 metadata 中的狀態標註
    history = engine.s_cache.get("chat2")
    assert history is not None
    statuses = [item.metadata.get("status") for item in history]
    assert "WARN" in statuses and "ERR" in statuses and "OK" in statuses


def test_context_compression_dedup_and_diff():
    # 測試重疊偵測與壓縮邏輯
    a = "The user provided details: ABC123"
    b = "ABC123 and additional info."
    overlap = _common_overlap(a, b)
    assert overlap == "ABC123"
    # 建立有重疊內容的歷史
    engine = DefaultContextEngine()
    content1 = "Step 1: Initialize system. Output: SUCCESS."
    content2 = "Output: SUCCESS. Proceed to step 2."
    engine.write_turn("assistant", content1, {"conv_id": "chat3"})
    engine.write_turn("assistant", content2, {"conv_id": "chat3"})
    # 未壓縮時，歷史訊息應完整儲存
    raw_history = engine.s_cache.get("chat3")
    assert raw_history and raw_history[-1].content == content2
    # 取得壓縮後的上下文
    ctx = engine.get_context_for_scope("task", key="chat3")
    assert len(ctx) == 2
    assert ctx[1].metadata.get("compressed") is True
    assert ctx[1].content.startswith("---")


def test_negative_vault_management():
    # 測試負面範例庫管理
    # 保證 vault 初始為空
    assert NegativeVault.list_examples() == []
    # 新增範例並驗證列表
    NegativeVault.add_example("Do not reveal confidential information.")
    NegativeVault.add_example("Avoid producing disallowed content.")
    NegativeVault.add_example("Do not reveal confidential information.")  # 重複，應被忽略
    vault_list = NegativeVault.list_examples()
    assert len(vault_list) == 2
    assert "confidential information" in vault_list[0]
    # 移除範例並驗證
    NegativeVault.remove_example("Avoid producing disallowed content.")
    vault_list = NegativeVault.list_examples()
    assert vault_list == ["Do not reveal confidential information."]


def test_prompt_builder_outputs():
    # 測試提示生成器輸出
    mem1 = MemoryItem(content="User asked for help with billing.", metadata={"role": "user"})
    mem2 = MemoryItem(content="Assistant provided billing information.", metadata={"role": "assistant"})
    context = [mem1, mem2]
    user_query = "I have another question about my account."
    builder = PromptBuilder()
    messages = builder.build(template_id=None, context=context, user_query=user_query)
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == user_query


def test_prompt_builder_negative_and_tools_slots():
    builder = PromptBuilder()
    template = (
        "System: 以下是避免產生的內容：\n"
        "{negative_examples}\n\n"
        "System: 可用工具：\n"
        "{tools}\n\n"
        "{context}\n\n"
        "User: {user_query}"
    )
    builder.registry.register_template("neg_tools", template)
    negs = ["No NSFW.", "Avoid bias."]
    tools = [ToolSpec(name="search", description="web search"), ToolSpec(name="calc", description="calculator")]
    mem = MemoryItem(content="previous", metadata={"role": "user"})
    messages = builder.build(
        template_id="neg_tools",
        context=[mem],
        user_query="hi",
        negative_examples=negs,
        tools=tools,
    )
    system_text = "\n".join(m["content"] for m in messages if m["role"] == "system")
    assert "No NSFW." in system_text
    assert "search: web search" in system_text

