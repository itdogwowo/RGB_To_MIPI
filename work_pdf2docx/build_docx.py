"""Build the Word document from the extracted model.

Uses python-docx (bundled runtime). Figures are pre-rendered PNG crops.
"""
import json, re, os, sys, datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

MODEL = json.load(open("work_pdf2docx/doc_model.json"))
FIGS = {m["page"]: [] for m in json.load(open("work_pdf2docx/figs_manifest.json"))}
for m in json.load(open("work_pdf2docx/figs_manifest.json")):
    FIGS[m["page"]].append(m)

TBLIMGS = json.load(open("work_pdf2docx/tables_img_manifest.json"))
TBLIMG_BY_PAGE = {}
for m in TBLIMGS:
    TBLIMG_BY_PAGE.setdefault(m["page"], []).append(m)

TOC = json.load(open("work_pdf2docx/toc.json"))
OUT = "SSD2828QN4_Datasheet_文件版.docx"

PT2CM = 2.54 / 72.0
TEXT_W_CM = 16.6

C_DARK = RGBColor(0x1F, 0x33, 0x64)
C_MID = RGBColor(0x2E, 0x54, 0x96)
C_GREY = RGBColor(0x59, 0x59, 0x59)
C_ACC = RGBColor(0xB4, 0x53, 0x09)

# ---------------------------------------------------------------- helpers

def set_run_font(run, name="Times New Roman", east="Microsoft JhengHei", size=None,
                 bold=None, italic=None, color=None):
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)
    rFonts.set(qn("w:eastAsia"), east)
    rFonts.set(qn("w:cs"), name)


def shade(el, hexcolor):
    tcPr = el.get_or_add_tcPr() if hasattr(el, "get_or_add_tcPr") else el
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor.replace("#", ""))
    tcPr.append(shd)


def set_cell_margins(cell, top=30, bottom=30, left=70, right=70):
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{k}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def set_table_borders(table, color="8EA9C1", sz=6):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def add_field(paragraph, instr, placeholder=""):
    r1 = paragraph.add_run()
    fc1 = OxmlElement("w:fldChar"); fc1.set(qn("w:fldCharType"), "begin")
    r1._r.append(fc1)
    r2 = paragraph.add_run()
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    r2._r.append(it)
    r3 = paragraph.add_run()
    fc2 = OxmlElement("w:fldChar"); fc2.set(qn("w:fldCharType"), "separate")
    r3._r.append(fc2)
    r4 = paragraph.add_run(placeholder)
    r5 = paragraph.add_run()
    fc3 = OxmlElement("w:fldChar"); fc3.set(qn("w:fldCharType"), "end")
    r5._r.append(fc3)
    return r4


def para_border_bottom(paragraph, color="1F3864", sz=8):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(sz))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def para_border_top(paragraph, color="1F3864", sz=8):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), str(sz))
    top.set(qn("w:space"), "10")
    top.set(qn("w:color"), color)
    pbdr.append(top)
    pPr.append(pbdr)


def keep_with_next(paragraph, on=True):
    paragraph.paragraph_format.keep_with_next = on


# ---------------------------------------------------------------- document

doc = Document()

# --- page setup
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.left_margin = Cm(2.2)
sec.right_margin = Cm(2.2)
sec.top_margin = Cm(2.0)
sec.bottom_margin = Cm(1.9)
sec.header_distance = Cm(1.0)
sec.footer_distance = Cm(0.9)
TEXT_W_CM = 21.0 - 4.4

# --- base styles
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
pf = st.paragraph_format
pf.space_before = Pt(0)
pf.space_after = Pt(4)
pf.line_spacing = 1.18

for lvl, size, color, before, after in ((1, 17, C_DARK, 20, 8),
                                        (2, 13, C_MID, 14, 5),
                                        (3, 11, C_DARK, 10, 4)):
    hs = doc.styles[f"Heading {lvl}"]
    hs.font.name = "Arial"
    hs.font.size = Pt(size)
    hs.font.bold = True
    hs.font.color.rgb = color
    hs.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
    hs.paragraph_format.space_before = Pt(before)
    hs.paragraph_format.space_after = Pt(after)
    hs.paragraph_format.keep_with_next = True
    hs.paragraph_format.line_spacing = 1.05

# caption style
cap = doc.styles.add_style("FigCaption", 1)
cap.font.name = "Arial"
cap.font.size = Pt(9)
cap.font.bold = True
cap.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
cap.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
cap.paragraph_format.space_before = Pt(3)
cap.paragraph_format.space_after = Pt(9)

# table text style
tt = doc.styles.add_style("CellText", 1)
tt.font.name = "Times New Roman"
tt.font.size = Pt(8.5)
tt.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft JhengHei")
tt.paragraph_format.space_before = Pt(0)
tt.paragraph_format.space_after = Pt(0)
tt.paragraph_format.line_spacing = 1.05

# --- header / footer (different first page)
sec.titlePg = True
hdr = sec.header.paragraphs[0]
hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hdr.add_run("SSD2828QN4  MIPI Master Bridge  ·  規格書文件版")
set_run_font(r, "Arial", "Microsoft JhengHei", 8, color=C_GREY)
para_border_bottom(hdr, "BFBFBF", 4)

ftr = sec.footer.paragraphs[0]
ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = ftr.add_run("— ")
set_run_font(r, "Arial", "Microsoft JhengHei", 8.5, color=C_GREY)
add_field(ftr, " PAGE ", "")
r = ftr.add_run(" —")
set_run_font(r, "Arial", "Microsoft JhengHei", 8.5, color=C_GREY)

# --- document properties
cp = doc.core_properties
cp.title = "SSD2828QN4 MIPI Master Bridge — 規格書文件版"
cp.subject = "SSD2828QN4 datasheet (Rev 1.3) 由 PDF 轉換整理"
cp.author = "文件轉換整理"
cp.comments = "來源: C48596_其他接口_SSD2828QN4R_规格书_WJ73954.PDF (Solomon Systech, Rev 1.3, 168 pages)"
cp.keywords = "SSD2828, MIPI DSI, RGB, SPI, bridge, datasheet"

# ================================================================ cover
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(90)
r = p.add_run("SSD2828QN4")
set_run_font(r, "Arial", "Microsoft JhengHei", 40, bold=True, color=C_DARK)

p = doc.add_paragraph()
r = p.add_run("MIPI Master Bridge")
set_run_font(r, "Arial", "Microsoft JhengHei", 22, bold=False, color=C_MID)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(4)
r = p.add_run("RGB / SPI  →  MIPI DSI  橋接晶片")
set_run_font(r, "Arial", "Microsoft JhengHei", 13, bold=True, color=C_ACC)
para_border_bottom(p, "B45309", 10)

p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(18)
r = p.add_run("規格書文件版（Word）")
set_run_font(r, "Arial", "Microsoft JhengHei", 15, bold=True, color=C_GREY)

rows = [("原廠文件", "C48596_其他接口_SSD2828QN4R_规格书_WJ73954.PDF"),
        ("文件版本", "Rev 1.3  ·  Mar 2013"),
        ("原廠", "Solomon Systech Limited  (Solomon Systech Semiconductor)"),
        ("原始頁數", "168 頁"),
        ("轉換日期", datetime.date.today().strftime("%Y-%m-%d")),
        ("文件用途", "供閱讀、搜尋、標註與技術筆記使用")]
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(16)
t = doc.add_table(rows=len(rows), cols=2)
t.autofit = False
for i, (k, v) in enumerate(rows):
    for j, val in enumerate((k, v)):
        c = t.cell(i, j)
        c.width = Cm(3.4 if j == 0 else 12.0)
        pp = c.paragraphs[0]
        rr = pp.add_run(val)
        set_run_font(rr, "Arial", "Microsoft JhengHei", 9,
                     bold=(j == 0), color=C_GREY if j == 0 else None)
set_table_borders(t, "D9D9D9", 4)
for i in range(len(rows)):
    set_cell_margins(t.cell(i, 0), 40, 40, 60, 60)
    set_cell_margins(t.cell(i, 1), 40, 40, 60, 60)

doc.add_page_break()

# ================================================================ 使用說明
doc.add_heading("使用說明（轉換說明）", level=1)
intro = [
    ("這份文件是什麼", "本文件由原廠 168 頁 PDF 規格書自動轉換、重排而成，目的是讓內容可以搜尋、複製、標註與編輯。"
     "文字、表格與圖片都取自原始 PDF，未改動技術內容。"),
    ("內容完整性", "第 1～18 章（含附錄 1 修訂記錄）全部保留，依原始章節順序排列。"
     "原始 PDF 的封面與目錄頁不重複收錄，改以下方的 Word 自動目錄取代。"),
    ("表格", "原本的表格已轉為 Word 表格，可直接編輯、複製到其他文件，或用 Excel 開啟後做計算。"
     "少數跨頁表格在轉換後會接續成同一個表格。"),
    ("圖片", "所有方塊圖、時序圖、波形圖皆以原圖裁切嵌入（200 dpi）。圖片中的線條、顏色與標註與原 PDF 相同。"),
    ("已知差異", "1) 部分原圖中的極小字（例如波形上的 T 標記）受限於原始解析度，清晰度略低於原 PDF；"
     "2) 表格框線與底色做了簡化統一；3) 上/下標（如 t_PCLK）在正文中保留為下標格式，但無法保證每一處都與原稿一致。"
     "遇到需要引用原文的場合，請以原 PDF 為準。"),
    ("章節 ↔ 原始頁碼", "本文件末尾附有「章節與原 PDF 頁碼對照表」，方便回頭查閱原 PDF。"),
]
for title, body in intro:
    p = doc.add_paragraph()
    r = p.add_run("▍ " + title)
    set_run_font(r, "Arial", "Microsoft JhengHei", 10.5, bold=True, color=C_MID)
    p.paragraph_format.space_before = Pt(6)
    p = doc.add_paragraph(body)
    p.paragraph_format.left_indent = Cm(0.5)

# ================================================================ 目錄
doc.add_heading("目錄", level=1)
p = doc.add_paragraph()
add_field(p, r' TOC \o "1-3" \h \z \u ',
          "（在 Word 中按 F9 或「更新功能變數」即可產生目錄；開啟文件時 Word 也會詢問是否更新。）")
p.paragraph_format.space_after = Pt(10)

settings = doc.settings.element
uf = OxmlElement("w:updateFields")
uf.set(qn("w:val"), "true")
settings.append(uf)

doc.add_page_break()
print("cover + toc done")

# ================================================================ 中文導讀
def heading_cn(text, level=1):
    h = doc.add_heading(text, level=level)
    return h

def body_cn(text, indent=0.0, size=10.5, space_before=0, color=None, bold=False):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    set_run_font(r, "Times New Roman", "Microsoft JhengHei", size, bold=bold, color=color)
    return p

def bullet_cn(text, indent=0.55, size=10.5, em="•"):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(indent + 0.45)
    p.paragraph_format.first_line_indent = Cm(-0.45)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(em + "  ")
    set_run_font(r, "Arial", "Microsoft JhengHei", size, color=C_MID, bold=True)
    r = p.add_run(text)
    set_run_font(r, "Times New Roman", "Microsoft JhengHei", size)
    return p

def simple_table(header, rows, widths=None, header_fill="1F3864", font=8.5,
                 first_col_bold=False, align=None):
    t = doc.add_table(rows=len(rows) + 1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_table_borders(t, "C9D3E0", 4)
    for j, h in enumerate(header):
        c = t.cell(0, j)
        c.width = Cm(widths[j]) if widths else Cm(16.6 / len(header))
        shade(c._tc, header_fill)
        set_cell_margins(c)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h)
        set_run_font(r, "Arial", "Microsoft JhengHei", font, bold=True,
                     color=RGBColor(0xFF, 0xFF, 0xFF))
    repeat_header(t.rows[0])
    for i, row in enumerate(rows, start=1):
        if i % 2 == 0:
            pass
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.width = Cm(widths[j]) if widths else Cm(16.6 / len(header))
            set_cell_margins(c)
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            if align and j < len(align):
                p.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                               "center": WD_ALIGN_PARAGRAPH.CENTER,
                               "right": WD_ALIGN_PARAGRAPH.RIGHT}[align[j]]
            elif j > 0 and len(str(val)) <= 14:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(val))
            set_run_font(r, "Times New Roman", "Microsoft JhengHei", font,
                         bold=(first_col_bold and j == 0))
    return t


doc.add_heading("中文重點導讀", level=1)
p = doc.add_paragraph()
r = p.add_run("以下為依原始規格書內容整理的繁體中文摘要，方便快速掌握重點；技術細節與數值仍請以本文後續章節（原廠原文）為準。")
set_run_font(r, "Times New Roman", "Microsoft JhengHei", 9.5, italic=True, color=C_GREY)
p.paragraph_format.space_after = Pt(8)

doc.add_heading("一、晶片定位與用途", level=2)
body_cn("SSD2828QN4 是一顆 MIPI Master Bridge 橋接晶片：一邊接應用處理器（AP）的傳統並列 RGB 介面或序列 SPI 介面，"
        "另一邊以 MIPI DSI 驅動內建 MIPI slave 介面的 LCD driver IC。常見用途是把只有 RGB/SPI 輸出的 SoC，"
        "接到只吃 MIPI DSI 的面板上（第 1 章、第 4 章）。")
body_cn("支援兩種輸入介面，可由 PS[1:0] 腳位選擇：", indent=0.0)
bullet_cn("並列 RGB（DPI-2.0），資料匯流排可為 16/18/24-bit")
bullet_cn("序列 SPI（DBI-2.0），支援 8-bit 4-wire、8-bit 3-wire、24-bit 3-wire 三種模式")
body_cn("輸出端為 MIPI DSI，最多 4 條 data lane + 1 條 clock lane，每 lane 最高 1Gbps（合計 4Gbps）。", indent=0.0)

doc.add_heading("二、主要規格（第 2 章）", level=2)
simple_table(
    ["項目", "規格"],
    [["序列連結總頻寬", "最高 4Gbps（最多 4 data lanes，每 lane 1Gbps）"],
     ["RGB 介面", "並列 RGB / DPI-2.0，最高 24-bit"],
     ["SPI 介面", "序列 SPI / DBI-2.0，最高 16-bit"],
     ["MIPI 標準", "DSI v1.01.00、DCS v1.02.00、D-PHY v1.00.00"],
     ["最高解析度", "1920 pixels/row @ 60Hz（Video mode）；2560 pixels/row @ 30Hz"],
     ["像素格式", "16 / 18 / 24 bpp（Raw 或 Pixel mode）"],
     ["電源", "MVDD 1.2V ±10%（類比/數位核心與 PLL）；VDDIO 1.8～3.3V ±10%（IO）"],
     ["其他功能", "內建可變輸出 PLL、CABC、ULPS 超低功耗、雙向資料傳輸、TE 同步"],
     ["封裝", "68 QFN-EP（Tray 包裝）；型號 SSD2828QN4"]],
    widths=[3.6, 13.0], first_col_bold=True, align=["left", "left"])

doc.add_heading("三、腳位分組（第 6～7 章）", level=2)
body_cn("68 腳 QFN-EP。下表為功能分組摘要，完整腳號對照請見 Table 6-2，詳細功能說明見 Table 7-1～7-3。")
simple_table(
    ["群組", "主要腳位", "說明"],
    [["電源", "MVDD、VDDIO、GND", "MVDD 1.2V；VDDIO 1.8～3.3V；68 腳中 GND 佔多腳"],
     ["MIPI 輸出", "CLKP/CLKN、DATAP0～3/DATAN0～3", "DSI_0 差動時脈與資料通道"],
     ["RGB 輸入", "DATA0～DATA23、PCLK、DEN、HSYNC、VSYNC", "並列 RGB（DPI-2.0）"],
     ["SPI 輸入", "SCK、SDI、SDO、SDC、CSX0", "3-wire / 4-wire 序列介面"],
     ["介面選擇", "PS0、PS1", "選擇 RGB 或 SPI 介面組合"],
     ["時脈", "TX_CLK_XIN、TX_CLK_XIO、SYS_CLK_OUT", "外部參考時脈輸入 / 系統時脈輸出"],
     ["控制與重置", "RESET、SHUT", "重置與關閉"],
     ["其他", "NC ×3", "未接腳"]],
    widths=[2.6, 6.6, 7.4], first_col_bold=True, align=["left", "left", "left"])

doc.add_heading("四、暫存器速查（第 8 章）", level=2)
body_cn("SSD2828 全部功能都由暫存器設定。透過 SPI 介面以「指令 + 資料」方式存取，位址即 Table 8-1 的 Offset 欄。"
        "各暫存器的位元定義請見 8.1.1～8.1.67 各節（每節：先給 bit map，再給 description 表）。")

# 由 Table 8-1 抽出暫存器清單
regs = []
for pg in MODEL:
    if pg["page"] not in (23, 24):
        continue
    for it in pg["items"]:
        if it["type"] != "table":
            continue
        for r in range(it["nrows"]):
            vals = []
            for c in range(it["ncols"]):
                cell = it["cells"].get(f"{r},{c}")
                if cell is None:
                    vals.append("")
                    continue
                txt = " ".join(" ".join(w["text"] for w in ln) for ln in cell["lines"]).strip()
                vals.append(txt)
            if len(vals) >= 4 and re.match(r"^0x[0-9A-Fa-f]{2}$", vals[0][:4]):
                regs.append([vals[0][:4], vals[2] if len(vals) > 2 else "",
                             vals[1], vals[3] if len(vals) > 3 else ""])
regs = [r for r in regs if r[1]]

body_cn(f"共 {len(regs)} 個暫存器（Offset 0xB0～0xDD）。以下為完整位址、助憶符號、名稱與重置值速查；"
        "個別位元欄位請點回對應的 8.1.x 節。", space_before=4)
half = (len(regs) + 1) // 2
for i in range(half):
    pass
# 兩欄並排的緊湊表格（每列放兩組）
qa = regs[:half]
qb = regs[half:]
rows = []
for i in range(half):
    a = qa[i]
    b = qb[i] if i < len(qb) else ["", "", "", ""]
    rows.append([a[0], a[1], a[3], b[0], b[1], b[3]])
t = simple_table(["Offset", "Mnemonic", "Reset", "Offset", "Mnemonic", "Reset"],
                 rows, widths=[1.9, 4.2, 2.2, 1.9, 4.2, 2.2], font=8,
                 align=["center"] * 6)
doc.add_paragraph().paragraph_format.space_after = Pt(2)

doc.add_heading("五、上電初始化順序（第 15 章）", level=2)
body_cn("原廠的 power up sequence 圖（第 15 章）重點如下，各步驟之間的間隔時間見圖上標註：")
simple_table(
    ["順序", "動作", "備註"],
    [["1", "VDDIO（VDDIOC / MAVDDV）上電", "電源時序的第一個"],
     ["2", "MVDD（VCC12A / MDVDD / MAVDD）上電", "在原圖中緊接 VDDIO/MAVDDV 之後"],
     ["3", "放開 RESB（重置）", "重置釋放後才能存取暫存器"],
     ["4", "提供 TX_CLK", "外部參考時脈"],
     ["5", "透過輸入介面（SPI）下指令：PEN=1 開 PLL", "例：0xB9 = 0x0001（PLL ON）"],
     ["6", "離開 ULP 模式", "例：0xB7 = 0x0300"],
     ["7", "SLP=0、VEN&HS=1，進入 Video mode", "例：0xB7 = 0x0309（Video mode ON）"],
     ["8", "送 RGB 訊號", "最後才讓 RGB 訊號有效"]],
    widths=[1.6, 8.0, 7.0], first_col_bold=True, align=["center", "left", "left"])
body_cn("對應的關機（power off）順序見第 16 章；休眠進出（sleep in/out）的時序範例見第 17 章。", space_before=4)

doc.add_heading("六、章節導覽：想找什麼看哪裡", level=2)
simple_table(
    ["需求", "章節", "原 PDF 頁"],
    [["這是什麼晶片、有哪些功能", "1. General Description、2. Features", "9–10"],
     ["接腳定義與腳位功能", "6. Pin Assignment、7. Pin Description", "18–22"],
     ["暫存器位址與每個 bit 的意義", "8. Command Table（8.1.x 各節）", "23–101"],
     ["RGB 時序參數（HSA/HBP/HFP 等）", "8.1.2～8.1.8、9.3 Operating Modes", "26–33、102 起"],
     ["PLL 倍率怎麼設、MIPI 速率怎麼算", "8.1.10～8.1.12、9.4（Table 9-10～9-12）", "36–38、123–124"],
     ["MIPI DSI 封包結構與資料順序", "9.2（Packet、Data Type、Endian）", "115–121"],
     ["SPI 介面怎麼下指令（3-wire/4-wire）", "10. SPI Interface", "139–148"],
     ["電氣規格（電壓、電流、驅動能力）", "11～13. Ratings / DC Characteristics", "149–153"],
     ["時序規格（SPI、RGB、Reset、TX_CLK）", "14. AC Characteristics", "154–158"],
     ["上電 / 關機 / 休眠順序", "15～17", "159–161"],
     ["封裝尺寸、絲印、Tray 資訊", "18. Package / 附錄", "165–168"]],
    widths=[6.4, 7.0, 3.2], align=["left", "left", "center"])

doc.add_page_break()
print("quick guide done")

# ================================================================ 正文
SKIP_PAGES = {1, 3, 4, 5, 6, 7, 8}

def flatten(model):
    blocks = []
    for pg in model:
        if pg["page"] in SKIP_PAGES:
            continue
        for it in pg["items"]:
            b = dict(it)
            b["page"] = pg["page"]
            blocks.append(b)
    return blocks

BLOCKS = flatten(MODEL)

def block_text(b):
    return "".join(w["text"] for w in b.get("words", [])).strip()

# --- 跨頁段落接續
merged = []
for b in BLOCKS:
    if (merged and b["type"] == "para" and merged[-1]["type"] == "para"
            and b["page"] > merged[-1]["page"]
            and not b.get("bullet") and not b.get("item")
            and not merged[-1].get("bullet") and not merged[-1].get("item")):
        prev_text = block_text(merged[-1])
        cur_text = block_text(b)
        if prev_text and cur_text and not re.search(r"[.:;!?)\]]$", prev_text) \
           and re.match(r"[a-z(]", cur_text):
            merged[-1]["words"] += b["words"]
            merged[-1]["_pages"] = merged[-1].get("_pages", [merged[-1]["page"]]) + [b["page"]]
            continue
    merged.append(b)
BLOCKS = merged
print("blocks:", len(BLOCKS))

def add_words(paragraph, words, size=10.5, color=None):
    for w in words:
        if w["text"] == " ":
            r = paragraph.add_run(" ")
            set_run_font(r, "Times New Roman", "Microsoft JhengHei", size, color=color)
            continue
        r = paragraph.add_run(w["text"])
        set_run_font(r, "Times New Roman", "Microsoft JhengHei", size,
                     bold=w.get("bold"), italic=w.get("italic"), color=color)
        if w.get("sub"):
            r.font.subscript = True
        if w.get("sup"):
            r.font.superscript = True


def add_caption(text, keep=True):
    p = doc.add_paragraph(style="FigCaption")
    m = re.match(r"^(Table|Figure)\s+([\d\-–]+)\s*[:\-–]\s*(.*)$", text)
    if m:
        r = p.add_run(m.group(1) + " " + m.group(2) + "：")
        set_run_font(r, "Arial", "Microsoft JhengHei", 9, bold=True, color=C_MID)
        r = p.add_run(m.group(3))
        set_run_font(r, "Arial", "Microsoft JhengHei", 9, bold=True)
    else:
        r = p.add_run(text)
        set_run_font(r, "Arial", "Microsoft JhengHei", 9, bold=True)
    if keep:
        keep_with_next(p)
    return p


def cell_tokens(entry):
    lines = entry.get("lines", [])
    tokens = []
    for i, line in enumerate(lines):
        if i:
            prev_x1 = max(w["x1"] for w in lines[i - 1]) if lines[i - 1] else 0
            deliberate = (entry["box"][2] - 3 - prev_x1) > 16
            tokens.append(("__BR__" if deliberate else " ", False, False, False))
        for j, w in enumerate(line):
            if j:
                gap = w["x0"] - line[j - 1]["x1"]
                tokens.append((" " if gap > 0.85 else "", False, False, False))
            tokens.append((w["text"], w.get("bold"), w.get("italic"), w.get("sub")))
    return tokens


def col_widths(tb):
    ex = tb["xedges"]
    nc = tb["ncols"]
    maxw = TEXT_W_CM
    nat = [(ex[i + 1] - ex[i]) * PT2CM for i in range(nc)]
    mins = []
    for c in range(nc):
        longest = 0
        for cell in tb["cells"].values():
            ci = min(range(len(ex)), key=lambda k: abs(ex[k] - cell["box"][0]))
            if ci != c:
                continue
            for line in cell.get("lines", []):
                for w in line:
                    longest = max(longest, len(w["text"]))
        base_min = 0.42 if nc >= 16 else 0.62
        mins.append(max(base_min, longest * 0.14 + 0.18))
    total = sum(nat)
    if total > maxw:
        nat = [v * maxw / total for v in nat]
    deficit = sum(max(0.0, mins[i] - nat[i]) for i in range(nc))
    if deficit > 0:
        slack = [max(0.0, nat[i] - mins[i]) for i in range(nc)]
        ssum = sum(slack)
        if ssum > 0:
            nat = [nat[i] - deficit * slack[i] / ssum if slack[i] > 0 else nat[i]
                   for i in range(nc)]
        nat = [max(nat[i], mins[i]) for i in range(nc)]
    tot = sum(nat)
    if tot > maxw:
        nat = [v * maxw / tot for v in nat]
    return nat


def add_table_img(tb, page, k):
    cands = TBLIMG_BY_PAGE.get(page, [])
    best = None
    for m in cands:
        d = abs(m["bbox"][1] - tb["bbox"][1]) + abs(m["bbox"][0] - tb["bbox"][0])
        if best is None or d < best[0]:
            best = (d, m)
    if not best:
        return
    m = best[1]
    w_cm = min(TEXT_W_CM, (tb["bbox"][2] - tb["bbox"][0]) * PT2CM + 0.2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    p.add_run().add_picture(m["path"], width=Cm(w_cm))


def add_table(tb):
    ex, ey = tb["xedges"], tb["yedges"]
    nr, nc = tb["nrows"], tb["ncols"]
    widths = col_widths(tb)
    FONT = 8.5
    SIDE = 60
    if sum(widths) / max(1, nc) < 1.15 or nc >= 16:
        FONT = 7.0 if nc < 24 else 6.5
        SIDE = 26
    tbl = doc.add_table(rows=nr, cols=nc)
    tbl.autofit = False
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = tbl._tbl.tblPr
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    set_table_borders(tbl, "9BB0C6", 4)

    for j, wcm in enumerate(widths):
        tbl.columns[j].width = Cm(wcm)

    def fill_cell(cell, entry):
        box = entry["box"]
        filled = entry.get("fill")
        if filled:
            shade(cell._tc, filled)
            rr, gg, bb = int(filled[1:3], 16), int(filled[3:5], 16), int(filled[5:7], 16)
            lum = (0.299 * rr + 0.587 * gg + 0.114 * bb) / 255
            fg = RGBColor(0xFF, 0xFF, 0xFF) if lum < 0.55 else None
        else:
            fg = None
        tokens = cell_tokens(entry)
        p = cell.paragraphs[0]
        p.style = doc.styles["CellText"]
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        text_all = "".join(t[0] for t in tokens).replace("__BR__", " ").strip()
        if len(text_all) <= 12 and "__BR__" not in [t[0] for t in tokens]:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # first line may be bold in headers
        for tok, bold, italic, sub in tokens:
            if tok == "__BR__":
                p.add_run().add_break()
                continue
            if tok == " ":
                r = p.add_run(" ")
                set_run_font(r, "Times New Roman", "Microsoft JhengHei", FONT, color=fg)
                continue
            if tok == "":
                continue
            r = p.add_run(tok)
            set_run_font(r, "Times New Roman", "Microsoft JhengHei", FONT,
                         bold=bold, italic=italic, color=fg)
            if sub:
                r.font.subscript = True
        if not tokens:
            set_run_font(p.add_run(""), "Times New Roman", "Microsoft JhengHei", FONT)

    for r in range(nr):
        cant_split(tbl.rows[r])
    handled = set()
    for key, entry in tb["cells"].items():
        r0, c0 = map(int, key.split(","))
        if (r0, c0) in handled:
            continue
        rs, cs = entry["rs"], entry["cs"]
        if rs > 1 or cs > 1:
            cell = tbl.cell(r0, c0).merge(tbl.cell(r0 + rs - 1, c0 + cs - 1))
            for extra in cell.paragraphs[1:]:
                extra._element.getparent().remove(extra._element)
            for rr in range(r0, r0 + rs):
                for cc in range(c0, c0 + cs):
                    handled.add((rr, cc))
        else:
            cell = tbl.cell(r0, c0)
            handled.add((r0, c0))
        set_cell_margins(cell, 14, 14, SIDE, SIDE)
        fill_cell(cell, entry)
        from docx.enum.table import WD_ALIGN_VERTICAL
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # header row emphasis
    hdr_vert = any(v["rs"] > 1 for v in tb["cells"].values() if v["box"][1] <= tb["yedges"][1] + 0.5)
    if tb["nrows"] > 1 and not hdr_vert:
        repeat_header(tbl.rows[0])
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return tbl


def add_figure(block, k):
    page = block["page"]
    bbox = block["bbox"]
    w_cm = (bbox[2] - bbox[0]) * PT2CM
    w_cm = min(w_cm, TEXT_W_CM)
    w_cm = max(w_cm, 4.0)
    cands = [f for f in FIGS.get(page, []) if abs(f["crop"][0] - max(0, bbox[0] - 6)) < 30
             and abs(f["crop"][1] - max(0, bbox[1] - 6)) < 30]
    path = cands[0]["path"] if cands else None
    if not path or not os.path.exists(path):
        return
    cap = block.get("caption")
    if cap and block.get("cap_above"):
        add_caption(cap, keep=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    if cap:
        keep_with_next(p, True)
    run = p.add_run()
    run.add_picture(path, width=Cm(w_cm))
    if cap and not block.get("cap_above"):
        add_caption(cap, keep=False)


# --- build body
page_fig_counter = {}
table_img_counter = {}
prev_type = None
for idx, b in enumerate(BLOCKS):
    t = b["type"]
    if t == "heading":
        text = b["text"]
        if b["page"] == 2 and text.startswith("Appendix"):
            text = "Appendix 1  IC Revision history of SSD2828 Specification"
        h = doc.add_heading(text, level=min(int(b["level"]), 3))
        if b["level"] <= 1:
            h.paragraph_format.space_before = Pt(26)
            h.paragraph_format.space_after = Pt(10)
            para_border_top(h)
    elif t == "para":
        words = b["words"]
        if not words:
            continue
        _ptxt = block_text(b)
        if b["page"] == 2 and _ptxt.startswith("Appendix"):
            h = doc.add_heading("Appendix 1  IC Revision history of SSD2828 Specification", level=1)
            h.paragraph_format.space_before = Pt(26)
            h.paragraph_format.space_after = Pt(10)
            h.paragraph_format.page_break_before = True
            para_border_top(h)
            continue
        if b.get("bullet"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.85)
            p.paragraph_format.first_line_indent = Cm(-0.42)
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run("•  ")
            set_run_font(r, "Arial", "Microsoft JhengHei", 10.5, bold=True, color=C_MID)
            add_words(p, words)
        elif b.get("item"):
            ind = min(2.2, max(0.55, (b.get("x0", 71.9) - 53.9) * PT2CM))
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(ind + 0.3)
            p.paragraph_format.first_line_indent = Cm(-0.52)
            p.paragraph_format.space_after = Pt(3)
            add_words(p, words)
        else:
            txt = block_text(b)
            ind = min(2.2, max(0.0, (b.get("x0", 53.9) - 53.9) * PT2CM))
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(5)
            if txt.strip() in ("Offset Address",):
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif ind > 0.15:
                p.paragraph_format.left_indent = Cm(ind)
            add_words(p, words)
    elif t == "caption":
        add_caption(b["text"], keep=True)
    elif t == "table":
        if b.get("render_as_image"):
            k = table_img_counter.get(b["page"], 0) + 1
            table_img_counter[b["page"]] = k
            add_table_img(b, b["page"], k)
        else:
            add_table(b)
    elif t == "figure":
        k = page_fig_counter.get(b["page"], 0) + 1
        page_fig_counter[b["page"]] = k
        add_figure(b, k)
    prev_type = t

# ================================================================ 附錄：章節對照
doc.add_heading("附錄：章節與原 PDF 頁碼對照", level=1)
p = doc.add_paragraph()
r = p.add_run("本文件經過重排，頁碼與原 PDF 不同。若需要回頭對照原始 PDF（或引用頁碼給同事），"
              "可用下表查詢各章節在原始 PDF 中的起始頁。")
set_run_font(r, "Times New Roman", "Microsoft JhengHei", 9.5, italic=True, color=C_GREY)

rows = []
for e in TOC:
    if e["level"] in (1, 2) and e["num"]:
        rows.append((e["num"], e["title"], str(e["page"])))
half = (len(rows) + 1) // 2
left, right = rows[:half], rows[half:]
trows = []
for i in range(half):
    a = left[i]
    bb = right[i] if i < len(right) else ("", "", "")
    trows.append([a[0], a[1][:58], a[2], bb[0], bb[1][:58], bb[2]])
simple_table(["節", "標題", "原頁", "節", "標題", "原頁"], trows,
             widths=[1.1, 6.3, 1.2, 1.1, 6.3, 1.2], font=7.5,
             align=["center", "left", "center", "center", "left", "center"])

doc.save(OUT)
print("saved", OUT)
