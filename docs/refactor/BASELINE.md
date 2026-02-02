# Baseline 盤點

## 專案結構掃描（主要 packages/modules、tests、設定檔）

### 主要套件與模組
- `hippoium/`：核心 Python 套件。
  - `core/`：核心邏輯（context manager、memory、retriever、builder、training 等）。
  - `adapters/`：LLM/Embedding Provider 介接（OpenAI、Anthropic、HTTP、Local）。
  - `ports/`：Protocol/Schema/Enum 定義。
  - `engine.py`：DefaultContextEngine（整體記憶與壓縮流程）。
- `docs/`：文件與指南。
- `examples/`、`examples_plugins/`：示例。
- `tools/`：工具腳本。

### Tests
- `tests/`：依功能拆分子目錄。
  - `compression/`
  - `context/`
  - `integration/`
  - `performance/`
  - `retrieval/`
  - `unit/`

### 設定檔/依賴檔
- `pyproject.toml`：build system、依賴、dev tools（pytest/black/ruff/pre-commit）。
- `requirements.txt`：核心與 LoRA 依賴。
- 未發現 `setup.cfg`、`setup.py`、`Makefile`。

---

## 安裝方式

### 基本安裝（依 README）
```bash
python -m venv .venv && source .venv/bin/activate
pip install hippoium
```

### 開發/測試（建議）
```bash
pip install -e .[dev]
```

### LoRA 訓練（選用）
```bash
pip install -e .[train]
```

### 以 requirements.txt 安裝（替代方案）
```bash
pip install -r requirements.txt
```

---

## 測試方式與結果

### 嘗試執行
```bash
python -m pytest -q
```

### 結果
- ✅ 19 passed, 1 skipped, 56 warnings
- 主要 warning 來自 `datetime.utcnow()` 的 DeprecationWarning（memory stores 內）。

---

## Lint / Format

### 專案設定中可用工具
- `black`
- `ruff`
- `pre-commit`

### 建議指令（尚未執行）
```bash
black .
ruff check .
pre-commit run --all-files
```

---

## 目前已知問題（從掃描與測試警告整理）

- `datetime.utcnow()` 已被標記為 deprecated，tests 執行時會產生多個 warning，代表時間處理可能需要改為 timezone-aware 的 `datetime.now(datetime.UTC)`。
- Adapter 類別（例如 OpenAI）沒有明確 timeout/retry 配置，長時間或不穩定的 API 呼叫風險較高。
