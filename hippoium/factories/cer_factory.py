# hippoium/factories/cer_factory.py
"""
Factory for building a ready-to-use Context-Engine Runtime (CER).

公開方法:
    create_cer(...)
"""

from typing import Optional, Any, Dict

from hippoium.core.cer.runtime import ContextEngineRuntime
from hippoium.core.builder.prompt_builder import PromptBuilder

# 若你 adapter / retriever class 放在別處，請自行調整 import
from hippoium.adapters.base import BaseAdapter
from hippoium.retriever_factory import create_retriever   # 假設已有


def create_cer(
    *,
    adapter: BaseAdapter,
    memory_config: Optional[Any] = None,
    retriever_config: Optional[Dict[str, Any]] = None,
    enable_negative: bool = False,
    **runtime_kwargs,
) -> ContextEngineRuntime:
    """
    建立一個 CER 並把依賴（Adapter / Memory / Retriever / PromptBuilder）都接好。
    參數:
        adapter           : 任何繼承 BaseAdapter 的 LLM 介面 (OpenAIAdapter / MyHTTPAdapter …)
        memory_config     : S/M/L 記憶體後端設定 (None = in-memory)
        retriever_config  : 建 RAG 檢索器的設定 (None = 預設 VectorRetriever)
        enable_negative   : 是否啟用自動反例 / 安全約束
    """
    # 1) ContextEngineRuntime
    cer = ContextEngineRuntime(memory_config=memory_config, enable_negative=enable_negative, **runtime_kwargs)

    # 2) PromptBuilder 綁定
    builder = PromptBuilder()
    cer.set_prompt_builder(builder)

    # 3) Retriever (RAG)
    if retriever_config is not None:
        retriever = create_retriever(**retriever_config)
        cer.set_retriever(retriever)

    # 4) LLM Adapter
    cer.set_llm_adapter(adapter)

    return cer