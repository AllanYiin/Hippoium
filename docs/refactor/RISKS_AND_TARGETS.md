# Risks & Targets

## 高風險點（從目前 code 觀察）

1. **Mutable default argument**
   - `PromptBuilder.build()` 的 `context: List[MemoryItem] = []` 為可變預設值，可能造成跨呼叫共享狀態的 bug。

2. **全域狀態 / Hook Registry**
   - `hook_registry` 是全域單例，且 `notify` 會吞掉 hook 例外（目前沒有 logging），一旦 hook 出錯很難追查。

3. **時間處理為 naive datetime**
   - `datetime.utcnow()` 被 Python 標記為 deprecated，tests 也已出現警告；同時缺少 timezone-aware 時間處理。

4. **Provider adapter 缺少 timeout / retry**
   - OpenAI adapter 直接呼叫 API，沒有明確 timeout/retry，面對網路不穩定或 API slow/hang 有風險。

5. **記憶層完全 in-memory**
   - SCache/MBuffer/LVector 為 in-memory，沒有 persistence；重啟即遺失、無法跨 process 分享。

6. **Session/Scope 預設值不夠明確**
   - DefaultContextEngine 在 metadata 缺少 session 時會使用 `default`，可能導致不同 session 交叉污染。

---

## Stage 目標清單（建議分期）

### Stage 1 — Safety & Observability
- 將 `datetime.utcnow()` 改為 timezone-aware。
- 移除 mutable default args，補上 safe default。
- Hook registry 增加 logging（但避免敏感資訊）。
- Provider adapter 加入基本 timeout/retry（可配置）。

### Stage 2 — Memory & Retrieval Stabilization
- 抽象記憶層介面，提供 disk/redis backend 的替代實作。
- 建立統一的 Retrieval Pipeline（目前 retriever 仍多為骨架）。
- 加入負例/正例資料流的測試覆蓋。

### Stage 3 — Prompt & Token Strategy
- 明確定義 token budget policy（head/tail/diff-patch 的選擇邏輯）。
- 將 PromptBuilder 的模板管理抽象成可測試模組。
- 針對 prompt injection 提供防護策略與測試案例。

### Stage 4 — Provider/Tooling Hardening
- Adapter 層增加 streaming、錯誤統一處理與 observability。
- 引入統一的 config 管理（env/typed config）。
- 加入性能與壓力測試基線。
