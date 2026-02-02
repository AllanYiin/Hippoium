# Release Checklist

## 版本與文件
- [ ] 更新版本號（`pyproject.toml`）。
- [ ] 更新 `README.md` 與相關文件，確保範例可跑且內容一致。
- [ ] 更新 `CHANGELOG.md`（若存在）並列出主要變更。

## 打包與測試
- [ ] `pip install -e .` 成功，且 `import hippoium` 可用。
- [ ] `python examples/minimal.py` 可正常執行。
- [ ] `python examples/openai_live.py`（需 `OPENAI_API_KEY`，CI 預設不跑）。

## 版本發佈
- [ ] 建立 git tag（例如 `vX.Y.Z`）。
- [ ] 推送 tag 至遠端。
- [ ] 確認 CI 全綠（tests / lint / build）。
