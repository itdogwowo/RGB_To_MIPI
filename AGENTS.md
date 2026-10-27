# AGENTS.md — 給 AI 代理的入口

**先讀 [`docs/AI_HANDOFF.md`](docs/AI_HANDOFF.md)**（328 行，含 §0.5 心智模型、§1.5 環境問題、§4 連線規則、§8 可直接貼的啟動提示詞）。

## 五條不能忘的規則

1. **不要啟動 EasyEDA GUI**——會踩 macOS TCC，出現 `EACCES …/LCEDA-Pro/logs/*.log`。讓使用者開。
2. **連線＝線端點正好落在 pin 座標上 + `createNetLabel`**。線「跨過」腳位不算連接（這是前幾版全錯的原因）。
3. **改磁碟上的 `.esch2` 編輯器不會重讀**（`chokidar degraded`）。一律用 bridge 的 `/execute` 改。
4. **交付要有 DRC 前後數字**，不要用「看起來接好了」當證據。
5. 命名：`.eprj3` 是專案資料夾、`.esch2` 是原理圖頁——**沒有 `.esch3`**。

## 起手式

```bash
node ~/.dsh/skills/easyeda-api/scripts/bridge-server.mjs &
curl -s localhost:49620/health     # 要看到 "edaConnected":true
```

## 相關技能

| 技能 | 用途 |
|---|---|
| `easyeda-api` | 官方 API 參考 + bridge server |
| `easyeda-agent-schematic` | 實戰筆記：連線規則、DRC 判讀、檔案格式陷阱 |
| `easyeda-eprj3-format` / `easyeda-eprj3-authoring` | `.eprj3` 格式 / 官方腳本工具鏈 |
