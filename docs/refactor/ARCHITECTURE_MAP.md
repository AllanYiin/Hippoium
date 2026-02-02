# Architecture Map

## Public Entry Points / 使用入口

### README 公開示例（import path）
- `from hippoium.core.builder.prompt_builder import PromptBuilder`
- `from hippoium.core.cer.compressor import Compressor`

### 主要可用元件
- `hippoium.engine.DefaultContextEngine`：提供 S/M/L 記憶分層、寫入對話、壓縮與查詢。
- `hippoium.core.context_manager.PromptContextSession`：`with` context 的方式建立上下文與 RAG hook。
- `hippoium.adapters.*`：Provider 介接（OpenAI/Anthropic/HTTP/Local）。

---

## 核心資料流（概念）

```
Input (conversation turns)
   -> Context Engine (DefaultContextEngine)
      -> Memory tiers (SCache / MBuffer / LVector)
      -> Compression (Compressor)
   -> Retrieval (retriever modules / hooks)
   -> Prompt Builder (PromptBuilder + TemplateRegistry)
   -> Adapter/Provider (OpenAI/Anthropic/Local)
   -> Output (model response)
```

### 文字版資料流說明
1. **Input**：對話或任務輸入（`write_turn`）。
2. **Memory**：SCache（session），MBuffer（短期），LVector（長期）存放記憶；可透過 TTL/容量限制管理。
3. **Compression**：針對歷史訊息以 hash 去重、diff-patch 壓縮，避免 token 爆量。
4. **Retrieval**：retriever 模組/Hook 可補充外部知識或負向篩選（目前多為框架骨架）。
5. **Prompt Builder**：將記憶、負例、工具提示套入模板或 fallback 組合為 Chat message 列表。
6. **Adapter/Provider**：呼叫外部 LLM 或 embedding 服務（OpenAI/Anthropic/HTTP/Local）。
7. **Output**：回覆內容再回寫到記憶層。

---

## 關鍵模組責任邊界

### 記憶層與管理
- `hippoium.core.memory.stores`：S/M/L/Cold 的 in-memory cache 與 TTL/容量。
- `hippoium.engine.DefaultContextEngine`：統一寫入記憶、壓縮與取回。

### Prompt / Context 管理
- `hippoium.core.context_manager`：管理 `PromptContextSession`、hook、負例與工具資訊。
- `hippoium.core.builder.prompt_builder`：Template + context 組裝成 messages。

### Retriever / Scoring
- `hippoium.core.retriever.*`：預留檢索、rerank、chunking 結構（目前多為空或簡化實作）。

### Provider Adapter
- `hippoium.adapters.base`：抽象介面。
- `hippoium.adapters.openai` / `anthropic` / `http_adapter` / `local`：實際呼叫 Provider。
