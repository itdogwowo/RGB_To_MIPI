# 給下一個 AI 的接手文件（EasyEDA Pro × 本專案）

> 讀這一頁就夠。5 分鐘能上手，之後再按需要去翻 `easyeda-api` 技能的 references。
> 最後更新：2026-10-27 21:20

## ⚡ 現在的狀態（先看這個）

| 項目 | 狀態 |
|---|---|
| EasyEDA Pro | 執行中（4.1.71） |
| Bridge Server | 本次在 49620 跑過（不常駐，重開機就沒了，見 §2） |
| 專案 DRC | **4 筆**（3 懸空線頭 + 1 組浮空腳；原本 66）——2026-10-27 22:20 施工完成 |
| 已完成的施工 | U1 換官方庫件 SSD2828QN4R（C48596）、U1 59 腳上網、U2 1.8V LDO、U3 1.2V LDO、Y1 24MHz、U4/U5 TXS0108E 位準轉換、3.3V 命名統一（詳見整合報告 §14.11） |
| 已知待辦 | ① 去耦電容與 22R 串阻 ② J2 Mockup 封裝換實物 ③ `.git/scratch` 搬出 repo（可選）④ bridge 做成 launchd（可選） |

**接手第一步**：啟動 bridge → `/health` 確認 `edaConnected:true` → 讀 DRC → 繼續清。

---

## 0. 一句話總結

**不要用檔案層猜座標。走 Bridge Server → 在編輯器裡執行 API → 用 DRC 驗證。**

我花了三版才學到：`.esch2` 寫得再漂亮，編輯器不認就是沒連。真正的連線規則（見 §4）只有透過 API 才驗得出來。

---

## 0.5 心智模型：只有一個通道，四種門

EasyEDA 的說明看起來很多套，其實**本體只有一個**：一段 JavaScript 在編輯器裡執行，
就能呼叫全部 API。差別只在「你用哪扇門把那段 JS 送進去」。

| 門 | 是什麼 | 誰用 | 本專案 |
|---|---|---|---|
| **擴展 API** | 本體。`eda.sch_*` / `eda.pcb_*` 那些類別 | 所有門最終都走它 | ✅ 用它 |
| **Bridge Server** | 一個本機 WebSocket/HTTP 服務，`POST /execute` 把 JS 送進編輯器 | agent（我們） | ✅ **走這扇** |
| **CLI `lceda-pro`** | 同一件事的命令列包裝（`invoke --code`） | 有終端的人／Windows | ❌ 這台 Mac 打不到 |
| **MCP** | 把 CLI 包成 MCP server | Claude Code 之類 | ❌ 不需要 |
| **直接改 `.esch2`** | 不是門，是**後門**：改磁碟檔案期待編輯器重讀 | 批次產生檔案時 | ⚠️ 只用在「造符號庫」，連線一律走 API |
| **官方腳本工具鏈** | `init.js` / `add-symbol.js` / `validate.js`，用來**產生檔案** | 從零建專案 | ⚠️ 已用過，但連線要 API 驗 |

**類比**：擴展 API 是插座；Bridge / CLI / MCP 是三條延長線，插的是同一度電；
直接改檔案則是「自己拉電線」——能通，但接錯不會有保險絲，要靠 DRC 才知道。

### 對使用者（你）只有兩件事

1. **開著 EasyEDA Pro**，擴充選單按一次 `API Gateway → Reconnect`
2. 其他都交給 agent（啟 bridge → 執行 JS → 跑 DRC → 出圖）

### 對 agent 只有一條路

```
啟動 bridge → /health → /execute（讀寫）→ sch_Drc.check() → 數字說話
```

---

## 1. 環境現況（這台機器）

| 項目 | 狀態 |
|---|---|
| EasyEDA Pro 客戶端 | **4.1.71**（`/Applications/嘉立创EDA(专业版).app`） |
| 擴充「Run API Gateway」 | 使用者已安裝，需在 EasyEDA 選單 `API Gateway → Reconnect` 才會連上 |
| Node | v26.0.0 |
| Bridge Server | `~/.dsh/skills/easyeda-api/scripts/bridge-server.mjs`（**不會常駐，用完就沒了**） |
| 已安裝技能 | `easyeda-api`（官方）、`easyeda-agent-schematic`（我寫的實戰筆記）、`easyeda-eprj3-format`、`easyeda-eprj3-authoring` |

---

## 1.5 兩個已解決／已知的環境問題

### macOS 的「文件檔案夾」權限（TCC）— 已處理

症狀：log 出現 `SQLITE_CANTOPEN`、畫面跳「權限問題 …logs/…log」。

| 事實 | 說明 |
|---|---|
| 檔案權限本身正常 | `tungkinlee:staff`、`-rw-r--r--`、無 `uchg` 旗標 |
| 真正原因 | macOS TCC 對 `~/Documents` 的保護，App 沒有「文件檔案夾」授權 |
| 修法（一次性，**永久有效**） | `tccutil reset SystemPolicyDocumentsFolder cn.lceda.pro` → 重啟 App → 按「允許」；或系統設定 → 隱私權與安全性 → 完全取得磁碟存取權 → 加入 `嘉立創EDA(專業版)` |
| 順手清 | `rm ~/Documents/LCEDA-Pro/logs/logs`（一個 0 byte 怪檔，會卡住日誌清理） |

`auto clear log: …` 每分鐘一筆是**正常的日誌輪替**，不是錯誤。

### `chokidar degraded`（檔案監看降級）— 已知，影響「改檔後編輯器不重讀」

log 會出現：`[folder-watch] chokidar degraded, snapshot takes over …RGB_To_MIPI/…`。

原因：專案資料夾有 **2531 個檔案**，其中 **1613 個是 `.git/scratch`**（早期 clone 的官方 skill repo，14 MB），
把 watcher 壓垮。**這就是「改了 `.esch2` 但編輯器畫面/DRC 不變」的真正原因**，不是權限。

對策：把 `.git/scratch` 搬到 repo 外（技能已安裝在 `~/.dsh/skills`，不需要留）；或直接接受它——
反正現在**一律走 API 改**，不依賴檔案重讀。

### 命名別搞錯（沒有 `.esch3`）

| 檔案 | 是什麼 |
|---|---|
| **`.eprj3`** | 專案**資料夾**（版本號在這） |
| `.esch2` | 原理圖**圖頁**（元件／導線／網路標籤） |
| `.epcb2` | PCB |
| `.epan2` | 拼板 |

「AI 可以改」的不是某個特殊副檔名——`.eprj3` 整個資料夾都是純文字，但**改檔案 ≠ 編輯器會認**，
所以正式流程走 API（§4）。

---

## 2. 五分鐘上手

> ⚠️ **Bridge Server 不會常駐**：每個 session 都要自己拉起來一次。要一勞永逸就做 launchd 常駐（尚未做）。

```bash
# 1) 啟動 bridge（背景執行，別放前景）
node ~/.dsh/skills/easyeda-api/scripts/bridge-server.mjs &

# 2) 確認它在哪個 port（49620-49629）
for p in $(seq 49620 49629); do
  curl -s -m 2 http://localhost:$p/health | grep -q easyeda-bridge && echo "PORT=$p" && break
done

# 3) 確認 EasyEDA 連上了
curl -s http://localhost:49620/health
#   → {"service":"easyeda-bridge","status":"ok","edaConnected":true,"edaWindowCount":1,...}

# 4) 列出視窗（多個的話要 select）
curl -s http://localhost:49620/eda-windows

# 5) 執行一段 JavaScript（重點：code 是 async function body，要 return）
python3 - <<'PY'
import json, urllib.request
code = "const p = await eda.dmt_Project.getCurrentProjectInfo(); return { name: p.name };"
req = urllib.request.Request("http://localhost:49620/execute",
      data=json.dumps({"code": code}).encode(),
      headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req, timeout=120).read().decode())
PY
```

**`edaConnected: false`** ＝ 使用者那邊沒按 Reconnect，或 EasyEDA 沒開。不要自己啟動 GUI（原因見 §5）。

---

## 3. 這個專案的座標

| 東西 | 值 |
|---|---|
| 專案 | `RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar/` |
| 專案 UUID | `592aee40471052db73fde0cef5d0fe6ef3913496a10a916198ca187f1825e096` |
| 原理圖頁 UUID | `7a3203061012a805`（重建頁面會變，用 `getCurrentProjectInfo()` 查） |
| 圖框 | A4 = **1170 × 825**（單位 10 mil，原點左下，Y 向上） |

---

## 4. 連線的唯一正確做法（最重要的一節）

### 4.1 規則

**一個腳位要被認定「接上」，必須同時滿足：**

1. 有一條導線的**端點正好落在** `getAllPinsByPrimitiveId()` 回報的 `(x, y)` 上；
2. 該導線上有**網路標籤**（`createNetLabel`），同名標籤才會合併成同一條網路。

**「線跨過腳位」不算連接。** 這是我前面全部失敗的原因——線從腳位內側 6 單位畫到外側 38 單位，視覺上穿過腳，電氣上完全沒接。

### 4.2 正確寫法

```js
const comps = await eda.sch_PrimitiveComponent.getAll();
const c = comps.find(x => x.getState_Designator() === 'U1');
const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
// pins[i] = { pinNumber, pinName, x, y, rotation, pinLength, ... }  ← x,y 就是接點

const p = pins[0];
const ex = p.x + 40, ey = p.y;              // 往外畫 40
await eda.sch_PrimitiveWire.create([[p.x, p.y, ex, ey]]);   // 端點貼在腳位上
await eda.sch_PrimitiveAttribute.createNetLabel(ex, ey, 'IO15_RGB_D0');
```

「往外」的方向：用該元件所有腳位的**重心**判斷（腳位在重心右邊就往右，上面就往上）。這比解讀 `rotation` 可靠。

### 4.3 常用 API 速查

| 目的 | 呼叫 |
|---|---|
| 元件清單／位號 | `eda.sch_PrimitiveComponent.getAll()` → `getState_Designator()` |
| 腳位＋接點座標 | `getAllPinsByPrimitiveId(id)` |
| 移動元件 | `eda.sch_PrimitiveComponent.modify(id, {x, y})`（**只對真正的元件有效**，電源旗標會報錯） |
| 畫線 | `eda.sch_PrimitiveWire.create([[x1,y1,x2,y2], ...])` |
| 命名網路 | `eda.sch_PrimitiveAttribute.createNetLabel(x, y, net)` |
| 刪線 | `eda.sch_PrimitiveWire.delete([...ids])`（可一次全刪） |
| DRC | `eda.sch_Drc.check(true, false, true)` → 明細陣列 |
| 存檔 | `eda.sch_Document.save()`（存檔後等 5–10 秒再查 DRC） |
| 出圖 | `eda.sch_ManufactureData.getPngFile('x', {width:1500})` → File，用 FileReader 轉 base64 |
| 開頁面 | `eda.dmt_EditorControl.openDocument(pageUuid)` |

---

## 5. 六個坑（都踩過）

| # | 坑 | 症狀 | 正解 |
|---|---|---|---|
| 1 | **線跨過腳位** | 看起來有線，DRC 一片浮空 | 端點必須落在腳位上（§4） |
| 2 | **只有 wire 的 NET 屬性、沒有 net label** | 線有名字，但網路不合併 | 一定要 `createNetLabel` |
| 3 | **由 agent 啟動 EasyEDA GUI** | `EACCES: permission denied .../LCEDA-Pro/logs/warn/*.log` | 讓使用者自己開；agent 只跑 `/health`、`/execute` |
| 4 | **改磁碟上的 `.esch2` 期待編輯器重讀** | 檔案改了、編輯器畫面/DRC 完全沒變（實測 `openProject()` 也不會重讀） | 一律用 API 改 |
| 5 | **物件跑到圖框外** | DRC 幾百筆 `OBJECTOUTSIDESHEET` | 設計要在 x 0–1170、y 0–825 內 |
| 6 | **`modify()` 用在電源旗標／圖框** | `仅当器件类型为元件时允许使用该函数进行修改` | 只對 component 用；旗標用刪除或重建 |
| 7 | **`sch_PrimitiveAttribute.modify(id,{fontSize:7})`** | 實際存成 **700**（×100），整頁變巨大藍字 | 要傳 **0.07**；改完務必重出圖檢查 |
| 8 | **`sch_PrimitivePin.modify(id,{noConnected:true})`**（NC 旗標） | NC 標記畫到圖框外 → 多 2 筆 `OBJECTOUTSIDESHEET` | 不要用，改放 `×` 文字標記（28 腳已這樣標） |
| 9 | **`getAllPinsByPrimitiveId()` 的座標** | 有時是 **symbol 本地座標**（U3 pin4 回報 y=-240） | 移元件時用「舊座標＋位移量」；不要拿它當絕對座標去畫線 |
| 10 | **兩個元件間距 < 5 單位** | 兩條 stub 會**合併成一條 wire** → 短路 | 移動後用 `getNetlistFile()` 逐腳 diff（lost/added 必須為空） |

### DRC 規則對照

| 規則 | 意思 | 正常值 |
|---|---|---|
| `OBJECTOUTSIDESHEET` | 物件在圖框外 | 0 |
| `NETOBJECTONGRID` | 網路圖元沒有真的連上（有線沒接點） | 0 |
| `SHOWFLOATING` | 浮空網路（只有一段線） | 0 |
| `CHECKFLOATPIN` | 有腳位完全沒接 | 只剩刻意未接的（NC、未用 lane） |
| `SHOWDANDLING` | 線的一端懸空 | 盡量 0 |
| `ONENETNAME` | 網路只有名字、沒有第二個接點 | 盡量 0 |
| `MISSFOOTPRINT` | 未指定封裝 | 要選料才會歸零 |

---

## 6. 本專案的目前狀態（接手起點）

上次跑完 `sch_Drc.check()`：

| 規則 | 數量 |
|---|---|
| `SHOWDANDLING` | 11 |
| `ONENETNAME` | 14 |
| `MISSFOOTPRINT` | 14 |
| `CHECKFLOATPIN` | 1（未用 DSI lane／NC／SYS_CLK_OUT 等） |
| **合計** | **40**（修正前是 534） |

已完成：16 顆元件搬進 A4 圖框、207 條舊線刪除、206 條 stub 以端點貼腳重畫、206 個網路標籤建立。

**今天另外處理掉的環境問題**（詳見 §1.5）：
- `SQLITE_CANTOPEN` / 權限對話框 → `tccutil reset SystemPolicyDocumentsFolder cn.lceda.pro` + 重啟 App + 按允許（**永久有效**，不用每次做）
- `~/Documents/LCEDA-Pro/logs/logs` 0 byte 怪檔 → 已刪
- `chokidar degraded` → 原因是 `.git/scratch` 1613 個檔案；**尚未搬**，屬可選優化

**待辦**：
1. 清掉 11 筆 `SHOWDANDLING` + 14 筆 `ONENETNAME`（多半是標籤沒貼在線端）
2. 重排間距（目前 stub 互相穿越，視覺很擠）
3. 指定封裝（SSD2828 = QFN-68 / JLC C48596；其餘待定）

備份：`docs/refs/P1_user-edit_backup.esch2`、`/tmp/before_repair4.esch2`、各 `*.bak*`。

---

## 7. 標準工作流程（照這個順序做）

```
啟動 bridge → /health 確認 edaConnected → /eda-windows 選視窗
   → 讀現況（元件、腳位、DRC）
   → 用 API 修改（modify / create / delete / createNetLabel）
   → save() → 等 8 秒 → DRC
   → 數字不對就再修，直到規則歸零
   → getPngFile 出圖給使用者看
```

**每次修改都要有 DRC 前後對照**，不要用「我覺得接好了」交付。

---

## 8. 給下一個 AI 的啟動提示詞（可直接貼）

**完整版**（新視窗開場直接貼）：

```
請先讀 AGENTS.md 與 docs/AI_HANDOFF.md（尤其 §0.5 心智模型、§1.5 環境問題、§4 連線規則），
然後接手這個 EasyEDA Pro 專案。

專案：RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar
現況：DRC 40 筆（11 懸空線頭 SHOWDANDLING / 14 單名網路 ONENETNAME /
      14 未指定封裝 MISSFOOTPRINT / 1 浮空腳）

請照這個順序做：
1. 啟動 bridge：node ~/.dsh/skills/easyeda-api/scripts/bridge-server.mjs &
2. curl -s localhost:49620/health → 確認 "edaConnected":true
   （false 就請我按 EasyEDA 的 API Gateway → Reconnect）
3. 讀 DRC 基線：eda.sch_Drc.check(true, false, true)
4. 清掉 SHOWDANDLING 與 ONENETNAME；MISSFOOTPRINT 先列清單給我選料
5. 每步附 DRC 前後數字，最後用 sch_ManufactureData.getPngFile 出一張圖

鐵則（違反會壞事）：
- 不要啟動 EasyEDA GUI（會踩 macOS TCC，出現 EACCES …/LCEDA-Pro/logs）
- 連線＝線端點正好落在 getAllPinsByPrimitiveId 回報的 (x,y) 上，
  並用 sch_PrimitiveAttribute.createNetLabel 命名；線「跨過」腳位不算連接
- 改磁碟上的 .esch2 編輯器不會重讀（chokidar 已降級），一律用 /execute
- 沒有 .esch3；.eprj3 是專案、.esch2 是原理圖頁

另外兩件可選（我点头才做）：
- 把 .git/scratch 搬出 repo（2531→918 檔，修復 chokidar）
- bridge 做成 launchd 常駐
```

**短版**（趕時間用）：

```
照 AGENTS.md 與 docs/AI_HANDOFF.md 接手 EasyEDA 專案：
啟 bridge → 確認 edaConnected → 讀 DRC → 清 SHOWDANDLING/ONENETNAME。
不要啟 GUI；連線要用 createNetLabel + 端點貼 pin；每步附 DRC 前後數字。
```

## 9. CLI 模式（`lceda-pro`）vs Bridge：該用哪個

EasyEDA Pro 客戶端（**v4.1.60+**）內建命令列客戶端，國際版叫 `easyeda-pro`、陸版 `lceda-pro`，
它與 Bridge 是**同一個能力的兩種入口**：

| 目的 | CLI | Bridge（我們實際在用） |
|---|---|---|
| 探測 | `lceda-pro doctor` | `GET /health` |
| 開專案 | `lceda-pro open --path x.eprj3 [--headless true]` | 使用者自己開；`GET /eda-windows` 查視窗 |
| 執行 JS | `lceda-pro invoke --session S --ext-uuid eda --code "…"` | `POST /execute {"code":"…"}` |
| 查 API | `lceda-pro doc api --class-name SCH_PrimitiveWire` | 讀 `~/.dsh/skills/easyeda-api/references/` |
| 查格式 | `lceda-pro doc format --class-name TWire` | 讀 `~/.dsh/skills/easyeda-api/format/` |
| 收尾 | `lceda-pro session close --session S --destroy` | 不用（視窗是使用者的） |
| MCP | `lceda-pro --mcp stdio` / `--mcp http --port 3030` | 不需要，直接打 HTTP |

### 這台 Mac 的實測（2026-10）

| # | 嘗試 | 結果 |
|---|---|---|
| 1 | `LCEDA-Pro --help` | 印出 **Node 的說明** → 被繼承的 `ELECTRON_RUN_AS_NODE=1` 強迫進入 node 模式 |
| 2 | `env -u ELECTRON_RUN_AS_NODE LCEDA-Pro --help` / `doctor` / `--version` | **無輸出**（15–20 秒）→ 只啟動 GUI，子命令沒被路由 |
| 3 | 同上 + `--user-data-dir=/tmp/...`（繞開單一實例） | **無輸出** |
| 4 | `ELECTRON_RUN_AS_NODE=1 LCEDA-Pro .../app/app.js --help` | `Cannot find module 'electron'`（app.js 一定要 Electron 執行環境） |
| 5 | 找獨立 CLI 執行檔 / shim | 全機只有 `Contents/MacOS/LCEDA-Pro`（69 KB，Electron 啟動器），`/usr/local/bin`、`~/.local/bin` 都沒有 `lceda-pro` |
| 6 | `lceda-pro` 在 PATH | 無 |

**結論：macOS 這版（4.1.71）沒有把 CLI 子命令接出來。** 不是設定問題，是打包時沒做那條入口。

**結論**：這台 Mac 從 shell 打不到 CLI 子命令，而且由 agent 啟動 GUI 會踩到
`EACCES …/LCEDA-Pro/logs/warn/*.log`。**所以本專案一律走 Bridge。**

（Windows 版依官方文件可直接用；若之後在 Windows 上接手，上表的 CLI 欄位就是用法。）

### 如果非要用 CLI（例如 Windows）

```bash
lceda-pro --help                       # 看全部指令
lceda-pro doctor                       # 探測（connected:false = 編輯器沒開）
lceda-pro open --path "D:/proj/My/My.eprj3" --headless true
lceda-pro invoke --session <S> --ext-uuid eda --timeout 120000 --code "$(cat script.js)"
lceda-pro doc api --class-name SCH_PrimitiveWire
lceda-pro doc format --class-name TWire
lceda-pro session close --session <S> --destroy
```

`invoke` 的 `code` 是 **async function body**，要 `return`；加 `--ext-uuid eda` 才有檔案／系統權限。
