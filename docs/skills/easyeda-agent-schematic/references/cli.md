# lceda-pro CLI 筆記（權威驗證路徑）

來源：
- <https://prodocs.lceda.cn/cn/api/guide/cli.html>
- AI 版（純 ASCII，最完整）：<https://prodocs.lceda.cn/storage/texts/api/guide/cli-for-ai.md>

## 這台機器的實測狀態（2026-10）

| 項目 | 結果 |
|---|---|
| 客戶端版本 | **4.1.71**（`Contents/Resources/app/version.txt`）→ 符合 CLI 需求（≥ 4.1.60） |
| 可執行檔 | `/Applications/嘉立创EDA(专业版).app/Contents/MacOS/LCEDA-Pro`（69 KB launcher） |
| `lceda-pro` 在 PATH | **沒有** |
| 直接跑 `LCEDA-Pro --help` | 印出 **Node 的 `--help`**，不是 CLI 用法 → macOS 上這條進入點還沒打通 |
| 功能是否存在 | `app.js`（3.2 MB）內確實含 `lceda-pro`、`__CLI__`、`resultChannel`、`--mcp std…` 等字串 → **功能在，入口待確認** |

結論：**Windows 版可直接用**；macOS 目前需要先找到正確入口（可能是 `open -a` 帶參數、
或客戶端以某個子命令啟動 CLI），或退而使用「使用者手動開 GUI + 以 bridge 通訊」。

## 為什麼不要由 agent 啟動 GUI

`~/Documents/LCEDA-Pro/` 是 app 的資料目錄（logs、config.json、projects）。
agent 若以子行程方式啟動 app，app 會用 agent 的權限血統寫
`~/Documents/LCEDA-Pro/logs/warn/YYYYMMDD.log` → 就是那個：

```
EACCES: permission denied, open '.../LCEDA-Pro/logs/warn/20261026.log'
```

**做法**：由使用者啟動客戶端；agent 只跑 `doctor` 確認 `connected: true`，再用 `invoke`。

## 常用指令

| 目的 | 指令 |
|---|---|
| 探測 | `lceda-pro doctor` |
| 開專案（隱藏視窗） | `lceda-pro open --path "<abs>.eprj3" --headless true` |
| 列出／關閉工作階段 | `lceda-pro session list` / `session close --session <id> --destroy` |
| 執行 JS | `lceda-pro invoke --session <id> --ext-uuid eda --timeout 120000 --code "$(cat x.js)"` |
| 查類別方法 | `lceda-pro doc api --class-name SCH_PrimitiveWire` |
| 查方法簽名 | `lceda-pro doc api --class-name SCH_PrimitiveComponent --method-name create` |
| 查檔案格式欄位 | `lceda-pro doc format --class-name TWire` |
| MCP 模式 | `lceda-pro --mcp stdio` 或 `--mcp http --port 3030 --token …` |

## 權威驗證會用到的 API

| 需求 | API |
|---|---|
| 元件清單 | `eda.sch_PrimitiveComponent.getAll()` → `getState_Designator()` |
| 腳位＋網路 | `eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id)` → `{ pinNumber, net, x, y }` |
| 導線 | `eda.sch_PrimitiveWire.getAllPrimitiveId()` |
| DRC | `eda.sch_Drc.check(true, false, true)`（strict, 不開面板, 回明細） |
| 網表 | `eda.sch_ManufactureData.getNetlistFile(name, 'Protel2')` → `file.text()` |
| BOM | `eda.sch_ManufactureData.getBomFile(name, 'csv')` |
| 出圖 | `eda.sch_ManufactureData.getPngFile(name, { width: 1400 })` |
| 存檔 | `eda.sch_Document.save()` |

## 硬性規則（官方 AI 文件）

1. `invoke` **一律加 `--ext-uuid eda`**（否則沒有檔案／系統權限）。
2. 路徑用正斜線；寫檔只寫 `APP_PROJECT_DIR` 底下的位置。
3. **不要自己算腳位座標**，一律 `getAllPinsByPrimitiveId()` 讀回。
4. 大量操作分批（每批 20–25 顆），並把 `--timeout` 調大。
5. 變更後等 5–10 秒再查詢（DRC／網表／渲染）。
6. 每個關鍵步驟把回傳 JSON 存檔當證據；最後 `save()` 並核對磁碟產物。
7. 用完 `session close --destroy`。

## 座標與角度（寫檔案時）

| 領域 | 約定 |
|---|---|
| 原理圖 | 單位 10 mil；原點在圖紙左下角，**Y 向上**；A4 = 1170 × 825 |
| PCB | 單位 mil；`layerId` 1 = 頂層、11 = 板框 |
| 角度 | API 逆時針為正；檔案內 `COMPONENT.rotation = (360 − API 角度) % 360` |
