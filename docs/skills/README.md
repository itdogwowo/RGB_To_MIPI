# 技能包

## easyeda-agent-schematic

用檔案層操作在 EasyEDA Pro／嘉立創 EDA（.eprj3）畫與修原理圖，**不啟動 GUI**。

### 安裝

```bash
cp -R docs/skills/easyeda-agent-schematic ~/.dsh/skills/
```

裝好後重新開啟 session，`available_skills` 就會出現 `easyeda-agent-schematic`。

### 內容

| 路徑 | 說明 |
|---|---|
| `SKILL.md` | 主文件：鐵則、連線畫法、驗證紀律、修補流程、交付檢查清單 |
| `references/pitfalls.md` | 格式與連線陷阱的實測筆記 |
| `scripts/verify_sch.py` | 腳位→網路、未接清單、T 接短路檢查 |
| `scripts/render_esch.py` | `.esch2` → PNG 離線預覽 |
| `scripts/mk_lib_entries.py` | 從既有 `.esch2` 抽真實符號成 library entry（含 DOCHEAD／ticket 正規化） |
| `scripts/lceda.sh` | 包裝 `lceda-pro` CLI：`probe` / `doctor` / `verify <專案>` |
| `scripts/verify_via_eda.js` | 用 `invoke` 在編輯器內跑：腳位網路、未接清單、DRC、網表 |
| `references/cli.md` | CLI 用法、權威 API、本機實測狀態 |

（agent 的檔案權限只涵蓋工作區，所以這裡是「先放工作區、再由使用者安裝」。
上面那行 `cp` 請由使用者自己執行。）
