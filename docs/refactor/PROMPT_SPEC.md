# PROMPT_SPEC

本文件定義 prompt/context 組裝流程的安全邊界與可追溯性規格，並描述 token budgeting 的裁剪策略。

## 信任邊界 (Trusted vs Untrusted)
- **Trusted**
  - 開發者提供的 system policy、prompt template。
- **Untrusted**
  - 使用者輸入、檢索回來的文字 (RAG)、feedback/negative examples、外部 tools 資訊。
- 所有 **untrusted** 資料必須以資料區段輸出，不得使用 `System:` 等角色標記偽裝成指令。

## 資料區段格式
所有 untrusted 資料以 **資料區段** 形式輸出，每個區段必須：
1. 以清楚的標籤開頭，例如 `NEGATIVE_EXAMPLES:`
2. 後續每筆資料以 JSON 字串包起來並縮排列示

範例：
```
NEGATIVE_EXAMPLES:
  - "ignore previous instructions"
TOOLS_DATA:
  - {"name": "search", "description": "web search", "parameters": {}}
CONTEXT_MESSAGES:
  - {"role": "user", "content": "previous message"}
```

## Tool 表達方式
- 若 SDK/框架支援 **結構化 tools** (function-calling schema)，優先使用結構化資料。
- 若只能純文字，**不得**串成 `name: description` 純文字指令。
- 必須將 tools 作為 `TOOLS_DATA` 資料區段輸出，並對 tool name 做 allowlist/escaping。

## Negative examples 格式
- Negative examples 一律放入 `NEGATIVE_EXAMPLES` 資料區段。
- **不得**使用 `System:` 前綴。
- 必須以 JSON quoting/indent，確保如 `ignore previous instructions` 仍停留在資料區段內。

## Context 壓縮可追溯性
壓縮後需保留以下資訊：
- `original_hash` (SHA-256)
- `original_length`
- `compressed_length`
- `method_id` (壓縮方法 ID)
- `original_content_ref` (不覆蓋原文，至少保留 reference)

**Debug 模式**可輸出 `compression_debug`，包含前後 N 字摘要。

## Token Budgeting
在送出 provider 之前，必須先估算 tokens (使用 `count_tokens`)。

若超過 budget，裁剪策略如下：
1. **先裁 context**
2. **再裁 history**
3. **最後裁 tools / data**

策略應文件化並可追溯，避免靜默升權或丟失關鍵 system policy。
