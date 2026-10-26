---
name: easyeda-agent-schematic
description: 用「檔案層操作」在 EasyEDA Pro／嘉立創 EDA（.eprj3）專案裡畫或修改原理圖，不啟動 GUI。當 agent 要畫原理圖、接線、修「打開後全部沒連」、批次放元件、讀寫 .esch2、驗證網路、或遇到 validate.js 崩潰、EACCES 讀不到 ~/Documents/LCEDA-Pro/logs 時載入。Use when drawing, wiring or debugging an EasyEDA Pro schematic from an agent, especially when connections appear missing or the client log path is denied.
---

# EasyEDA Pro 原理圖：agent 安全操作手冊

這份 skill 的目的是讓 agent**在完全不啟動 EDA GUI 的情況下**，把原理圖改對、驗對。
起點是實際踩過的坑：三版都「看起來畫好了」，使用者一開就說「全部沒有連接」。

---

## 0. 先選路：有 CLI 就用 CLI，沒有才退回檔案層

EasyEDA Pro 客戶端（**v4.1.60+**）內建命令列客戶端 `lceda-pro`（國際版叫 `easyeda-pro`），
它可以把**正在跑的編輯器當後端**執行任意擴充 API：

```bash
lceda-pro doctor                                   # 探測橋接端點
lceda-pro open --path <專案.eprj3> --headless true  # 開一個（隱藏）工作階段
lceda-pro invoke --session <S> --ext-uuid eda --code "$(cat verify_via_eda.js)"
lceda-pro session close --session <S> --destroy
lceda-pro doc api --class-name SCH_PrimitiveWire   # 查 API
lceda-pro doc format --class-name TWire            # 查檔案欄位定義
```

**這是唯一「權威」的驗證方式**：`sch_PrimitiveWire` / `getAllPinsByPrimitiveId()` 回傳的
`net` 就是編輯器認定的連線，`sch_Drc.check()` 與 `sch_ManufactureData.getNetlistFile()`
也是編輯器算出來的。不用再從座標猜腳位接點。

判準：

| 情況 | 用哪條路 |
|---|---|
| `doctor` 顯示 `connected: true`（使用者的編輯器開著） | **CLI**：`invoke` 驗證、導網表、跑 DRC |
| 只有磁碟上的檔案，沒有執行中的編輯器 | **檔案層**（本文件第 2 節之後），並在交付時說明「未經編輯器驗證」 |
| 需要 GUI 才能做的事（安裝 .eext、開啟「允許外部互動」） | 請使用者做 |

`lceda-pro` 的 `--help`、`doc api`、`doc format` 回傳的欄位說明是**最準的規格來源**，
比從真機樣本反推可靠。寫檔案前先 `doc format --class-name TWire` 之類查一次。

用 `scripts/lceda.sh` 包好上述流程：`probe` / `doctor` / `verify <專案>`。

## 0.1 第一鐵則：不要替使用者啟動 GUI



`~/Documents/LCEDA-Pro/` 是應用程式自己的目錄（logs、快取、授權）。agent 若用
`open -a`、AppleScript、CDP attach 或任何方式喚起 EasyEDA Pro，app 會以 agent 的權限
血統去寫 `~/Documents/LCEDA-Pro/logs/warn/*.log`，於是出現：

```
EACCES: permission denied, open '.../LCEDA-Pro/logs/warn/20261026.log'
```

這是 agent 越界，不是使用者環境壞掉。**做法：只改檔案；要親眼看圖請使用者自己開。**
交付時明確說「我沒有啟動客戶端」。

其他好處：不開 GUI 就不會有「客戶端記憶體是舊版／存檔覆蓋你的修改」的競爭問題。
（若使用者已開著專案，請他關閉或改完後重新載入。）

---

## 1. 先判斷你要哪一種做法

| 情境 | 做法 |
|---|---|
| 從零產生一張圖、放大量元件、建符號／封裝 | 用官方 CLI（`init.js`、`generate-symbol.js`、`add-symbol.js`、`add-wire.js`）。見 `easyeda-eprj3-authoring` |
| 在**使用者已經改過的**專案上補線、修線、換符號 | **不要重建**，直接在原檔上加／刪記錄（重建會弄丟他的元件與封裝） |
| 讀懂某個腳位接到哪 | 自己解析 `.esch2`，不要問 GUI |

重建 vs 就地修補的分界：**只要使用者動過那張圖，就就地修補。**

---

## 2. 檔案常識（寫錯這裡，圖會靜默壞掉）

- 原理圖單位 **0.01 inch**；A4 圖框 1170 × 825。
- 一行一筆：`{"type":"…","ticket":N,"id":"16位hex"}||{…body…}|`
- LF、每行結尾 `|`、**檔尾沒有換行**、最後一行也沒有 `|`。
- **追加式日誌**：刪除＝再寫一行空 body，或直接移除該行（官方 skill 用移除）。
- **新記錄要插在它所屬文件的區段內**（下一個 `DOCHEAD` 之前）。除非該文件是最後一個，
  否則 append 到檔尾會被歸到錯的文件，等於沒加。
- `id` 用 16 位 hex；`ticket` 取全檔最大值 +1 遞增。

---

## 3. 連線：唯一可靠的畫法

EasyEDA 認的是**腳位那條線**，而「腳位錨點」與「腳位外端點」常常不是同一點，
只對端點就會出現「全部沒連」。

**可靠做法：一條線跨過整隻腳。**

```
錨點 A = 元件位置 + 腳位座標（要依元件 rotation 旋轉）
方向 d = 腳位朝外的單位向量（也要依元件 rotation 旋轉）
起點  = A − d × 6                 # 略微伸進元件體內
終點  = A + d × (腳長 + 28)       # 伸出腳尖之外
```

這樣不論客戶端把接點定義在錨點、腳尖還是線段上，腳都會落在線裡。代價是視覺上
線會蓋住腳位一小段，可接受。

**依元件 rotation 旋轉座標**（原理圖為 y 向上、逆時針為正）：

```
rot   0: (x, y)        90: (-y, x)      180: (-x, -y)     270: (y, -x)
```

**命名**：把 GPIO／接腳資訊放進網路名（例：`IO15_RGB_D0`、`IO22_SPI_SCK`），
兩端同名即相連，審圖時一眼就知道接到哪隻腳。這比事後貼文字表格可靠——
`TEXT` 記錄的欄位形狀沒有官方樣本，別亂加。

---

## 4. 驗證紀律：從產出反推，不要相信產生器

寫完一定自己做這三件事（腳本見 `scripts/`）：

1. **逐行解析**：每行 `head||body`、JSON 合法、沒有壞行。
2. **腳位對線**：對每個腳位算錨點，量它到**每一條線段**的距離，< 0.4 才算接上。
   （只看線端點會誤判，因為連線可能是 T 接或線跨過腳位。）
3. **短路檢查**：兩條不同網路的線在同一點相遇、或某條線的端點落在別條線的中段上。

```bash
python scripts/verify_sch.py path/to/P1.esch2 --nets
python scripts/render_esch.py path/to/P1.esch2 preview.png   # 離線預覽給人看
```

真正的短路長這樣（實際抓到過）：去耦電容的 stub 端點 `(660,725)` 正好落在
`TS_INT` 訊號線的中段 → `3V3` 與 `TS_INT` 短路。**T 接是最常見的意外短路。**

---

## 5. 六個會讓你「以為畫好了」的坑

| # | 坑 | 症狀 | 對策 |
|---|---|---|---|
| 1 | 只對腳位端點畫線 | 使用者一開：全部沒連接 | 用第 3 節的「跨過整隻腳」 |
| 2 | `validate.js` 崩潰 | `Cannot read properties of undefined` | 客戶端寫 `{"type":"DOCHEAD","ticket":N}`，官方驗證器只認完全等於 `{"type":"DOCHEAD"}`。**這是驗證器限制，不是檔案壞**；改用幾何檢查 |
| 3 | `yAxisDirection` 混用 | 元件與線上下鏡像、看似連著其實沒連 | 同一檔案內一致（缺省＝`"down"`）；客戶端存檔會自己正規化，所以「開檔存一次」也能修 |
| 4 | 匯入客戶端符號沒正規化 | add-symbol 找不到文件、ticket 重複 | 匯入前把 DOCHEAD 正規化成 `{"type":"DOCHEAD"}`、ticket 1..N 重編（`scripts/mk_lib_entries.py` 已處理） |
| 5 | 移動元件沒重畫線 | 元件在、線留在原地 | 搬元件＝刪掉它的線並依新座標重畫 |
| 6 | 重建整個專案 | 使用者的封裝、MPN、排版全消失 | 使用者動過的圖只做就地修補；動手前先備份 |

---

## 6. 就地修補的流程（最常用）

1. `cp P1.esch2 P1.esch2.bak`（備份，出事可回）
2. 解析：文件清單 → 元件 → 每個元件的符號腳位（腳位 id 只在**同一份文件內**唯一，
   解析時務必以文件為界，否則會拿到別顆元件的腳名）
3. 決定要保留誰：使用者後放的「真元件」優先，自己先前產生的泛用符號要刪掉，
   否則同一塊板會有兩組接頭
4. 刪掉舊線（連 `WIRE` / `LINE` / 它的 `ATTR` 一起），只留元件
5. 依第 3 節重畫所有 stub，網路名照設計表
6. 跑 `scripts/verify_sch.py`，把短路修到 0
7. `scripts/render_esch.py` 產一張 PNG 給使用者看
8. 交付時說明：改了什麼、哪幾隻腳刻意不接、請他自己開客戶端確認

---

## 7. 交付前檢查清單

- [ ] 每個「應該接」的腳位，到線段距離 < 0.4
- [ ] 0 短路（含 T 接）
- [ ] 檔尾沒有換行、每行 JSON 合法
- [ ] 沒有重複的接頭／重複的 IC 符號
- [ ] 未接的腳位能說出理由（未用 lane、TF 卡腳、備用）
- [ ] 有備份、有 PNG 預覽、有給使用者的「請自己開」說明
- [ ] **沒有啟動過 GUI**

---

## 8. 附帶腳本

| 檔案 | 用途 |
|---|---|
| `scripts/verify_sch.py` | 腳位→網路對應、未接清單、T 接短路檢查 |
| `scripts/render_esch.py` | 把 `.esch2` 畫成 PNG（自動 fit，支援正負 y） |
| `scripts/mk_lib_entries.py` | 從既有 `.esch2` 抽出真實符號成 library entry（含正規化） |

用法與參數直接看檔案開頭的說明；三支都只依賴 Python 標準庫 + Pillow（render 才需要）。

更細的格式陷阱見 `references/pitfalls.md`。
