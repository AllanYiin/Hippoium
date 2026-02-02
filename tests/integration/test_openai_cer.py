# tests/integration/test_openai_cer.py
import os
import types

import pytest

from hippoium.factories import create_cer
from hippoium.adapters.openai import OpenAIAdapter
from hippoium.ports.events import Event
from hippoium.core.hooks import hook_registry

# --------------- 測試前置：檢查 openai 套件與 API key ----------------
openai = pytest.importorskip("openai")  # 若未安裝 openai -> skip
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY".lower())
pytest.skip("環境未設定 OPENAI_API_KEY", allow_module_level=True) if not API_KEY else None
# --------------------- 測試案例 --------------------------------------

def test_openai_cer_full_pipeline(monkeypatch):
    """
    目標：驗證 create_cer + OpenAIAdapter 能自動
      1) 捕捉最近對話並觸發壓縮事件
      2) 在 Prompt 中插入負例指令
      3) 觸發 RAG Hook
      4) 成功呼叫 OpenAI 並拿到 str 回覆
    """

    # -- 1. 準備 Hook 計數器 ----------------------------------------
    counters = types.SimpleNamespace(
        before_compression=0,
        after_compression=0,
        before_prompt_injection=0,
        before_rag_query=0
    )

    @hook_registry.register(Event.BEFORE_COMPRESSION)
    def _bc(context, **_):
        counters.before_compression += 1

    @hook_registry.register(Event.AFTER_COMPRESSION)
    def _ac(context, **_):
        counters.after_compression += 1

    @hook_registry.register(Event.BEFORE_PROMPT_INJECTION)
    def _bpi(context, **_):
        counters.before_prompt_injection += 1

    @hook_registry.register(Event.BEFORE_RAG_QUERY)
    def _brq(query, context, **_):
        counters.before_rag_query += 1
        # 模擬取回一份文件當 RAG 結果
        context.add_memory("《模擬 RAG 文件》愛因斯坦於 1915 年提出廣義相對論。")

    # -- 2. 建立 Hippoium CER with OpenAI ---------------------------
    adapter = OpenAIAdapter(api_key=os.environ['OPENAI_API_KEY'], model="gpt-4o")

    cer = create_cer(
        adapter=adapter,
        memory_config=None,         # 用內建 in-mem S/M/L 模式
        enable_negative=True,       # 自動加負例
    )

    # -- 3. 準備兩段對話，確保有「最近記憶」可壓縮 ---------------
    user_turn_1 = "Explain general relativity in two sentences."
    _ = cer.complete(cer.build_prompt(user_turn_1))   # 第一次呼叫

    user_turn_2 = "Now explain it like I'm five."
    full_prompt = cer.build_prompt(user_turn_2)       # 第二次呼叫前先 build

    # 驗證 Prompt 內有負例安全字串
    assert "harmful" in full_prompt.lower()

    # -- 4. 呼叫 OpenAI ---------------------------------------------
    answer = cer.complete(full_prompt)
    assert isinstance(answer, str) and len(answer) > 0

    # -- 5. 驗證事件計數 --------------------------------------------
    # 第二次 build 時應該至少觸發一次壓縮 & prompt injection & RAG
    assert counters.before_compression >= 1
    assert counters.after_compression >= 1
    assert counters.before_prompt_injection >= 1
    assert counters.before_rag_query >= 1
