# Memory/Cache/Retrieval Hardening

## 範圍
本文件針對 `memory/cache/retrieval` 子系統的可預測性與可測性進行說明，並描述可擴充的介面與一致的策略。

## 一致行為規範
### Eviction 策略（統一）
- **容量驅逐（capacity eviction）**：所有 tier 使用 **FIFO**（`OrderedDict.popitem(last=False)`）。
- **TTL 驅逐**：採用 **惰性清理**（lazy eviction），在 `get` 與 `put` 觸發過期檢查。
- **Oversize**：`MBuffer` 對單筆 `max_tokens` 超限採用 **拒絕寫入**（`ValueError`）。

### Thread-safety
所有 in-memory store 皆以 `threading.RLock` 保護關鍵區段，避免並行讀寫時不一致。

### Clock 注入
TTL 判斷與 sweep 皆依賴可注入 `Clock`（預設 `RealClock`），確保測試可控。

### Namespace/隔離
- 透過 `build_namespaced_key(namespace, key)` 統一命名規則，避免多 session/user 混用時碰撞。
- 預設不強制 namespace，呼叫端可針對 session/user 明確加前綴。

## Vector 檢索
- `LVector` 支援最小可用 `similarity_search`（cosine + top_k）。
- 若值為 `VectorEntry` 才參與向量比對，其餘值仍可作為一般 key-value 使用。
- 向量索引介面以 `VectorIndex` 協定隔離，可在未來替換為 ANN（faiss/hnswlib）實作。

## 使用建議
- Session/使用者隔離：
  - `build_namespaced_key(session_id, key)`
  - `build_namespaced_key("user", user_id)`
- LVector 作為檢索：
  - `put_vector(key, embedding, payload)`
  - `similarity_search(query_vector, top_k=K)`
