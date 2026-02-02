# Hippoium

> **Hippoium** 是一顆「放在 LLM 之前的記憶元素（Memory Element）」，專門處理上下文治理、記憶分層、RAG 強化與自動微調資料匯出，讓任何語言模型或多‑Agent 框架都能少花 tokens、少犯錯、又能持續進化。

&#x20;&#x20;

---

## ✨ 主要特色

| 類別                         | 功能亮點                                                              |
| -------------------------- | ----------------------------------------------------------------- |
| **Context Trimmer**        | 雜湊去重、Diff‑Patch 壓縮、負向 RAG 過濾，平均可節省 30‑60 % tokens                 |
| **Hierarchical Memory**    | 三層 CER（S‑Cache / M‑Buffer / L‑Vector）+ Cold Store，自動 TTL & 熱度升降級  |
| **Auto‑Label & Neg‑Vault** | 以 ERR/WARN 打標訊息並自動寫入反例庫，降低錯誤放大循環                                  |
| **Hybrid Retriever**       | 正向 cos sim − β × 負向 sim 混合評分，重複段落 Intra‑Sim 去冗餘                   |
| **Token Throttling**       | EWMA 動態預算 + Head/ Tail / Diff‑Patch TrimPolicy                    |
| **Code‑Copy Write‑Back**   | DataFrame／程式碼直接寫入共享 Store，不再浪費文字描述                                |
| **Auto LoRA Pipeline**     | MemorySampler → DataCleaner → PairBuilder → LoRATrainer，全自動產生微調語料 |

---

## 📦 安裝

### 本地安裝

```bash
# 建議使用 Python 3.9 以上
python -m venv .venv && source .venv/bin/activate
pip install -e .            # 本地開發安裝
pip install -e .[dev]        # 含測試與格式化工具
pip install -e .[train]      # 需要 LoRA 訓練管線時使用
```

### PyPI（可選）

若已發布至 PyPI，可直接安裝核心功能：

```bash
pip install hippoium
```

> **注意**：LoRA 訓練需額外安裝 `torch`、`transformers`、`peft`，已在 `[train]` extra 中列出。

---

## 🚀 快速上手

> **提醒**：以下範例使用 Mock 客戶端，不會呼叫任何真實 LLM（請在每次對話都記得這是 Mock 模式）。

```python
from hippoium.core.builder.prompt_builder import PromptBuilder
from hippoium.engine import DefaultContextEngine

engine = DefaultContextEngine()
engine.write_turn("user", "你好，請簡短介紹 Hippoium")
context = engine.get_context_for_scope("task")
messages = PromptBuilder().build(context=context, user_query="請用一句話說明用途")

class MockLLM:
    def complete(self, messages, **_):
        return "（Mock 回覆）Hippoium 是 LLM 記憶治理層。"

print(MockLLM().complete(messages))
```

### API Key 與 Mock 模式

* **有需要實際呼叫模型時**，請使用環境變數設定金鑰，例如 `OPENAI_API_KEY`。
* **範例程式中的 Mock 客戶端**只用來演示流程，不會觸發任何外部 API，請務必注意。

### 範例程式

* `examples/minimal.py`：使用 Mock LLM/Embedding client 組裝 prompt（不需金鑰）。
* `examples/openai_live.py`：需要 `OPENAI_API_KEY`，並在 CI 預設不執行。

---

## 🗂️ 專案目錄簡介

```
hippoium/
├─ core/                  # 核心邏輯
│  ├─ cer/                # Context / Execution / Retrieval
│  ├─ memory/             # 分層記憶管理
│  ├─ retriever/          # 混合檢索 & 去重
│  ├─ builder/            # Prompt 生成器與注入器
│  ├─ negative/           # 反例庫與自動標註
│  ├─ patch/              # Diff‑Patch 版本控管
│  ├─ routing/            # 多 Provider 成本/延遲路由
│  └─ training/           # LoRA 資料管線
├─ adapters/              # LLM / Embedding Provider 介接
├─ ports/                 # Enum、Protocol、Schema 定義
└─ examples/              # 範例程式
```

---

## 🤝 參與貢獻

1. Fork 專案並建立新分支：`git checkout -b feature/your-feature`
2. 提交 Commit 時請遵循 [Conventional Commits](https://www.conventionalcommits.org/) 格式。
3. 在 PR 中附上單元測試（`pytest`）與說明。
4. 通過 CI 後由 Maintainer Merge。

---

## 🛡️ 版權與授權

本專案遵循 MIT License。詳細內容請見 `LICENSE` 檔案。

---

## 📮 聯絡方式

對 Hippoium 有任何疑問或建議，歡迎寄信至 [**dev@hippoium.ai**](mailto\:dev@hippoium.ai)。
