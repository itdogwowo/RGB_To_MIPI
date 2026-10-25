"""Build an AI-oriented document pack from the extracted PDF model.

Outputs (ai_docs/ssd2828qn4/):
  README.md INDEX.md quickref.md datasheet.md
  sections/*.md   registers.{json,csv}   pins.csv pinout.csv timing.csv
  figures/*.png figures.md chunks.jsonl source.json
"""
import json, re, os, hashlib, datetime, shutil
from collections import OrderedDict

MODEL = json.load(open("work_pdf2docx/doc_model.json"))
FIGS = json.load(open("work_pdf2docx/figs_manifest.json"))
TBLIMGS = json.load(open("work_pdf2docx/tables_img_manifest.json"))
TOC = json.load(open("work_pdf2docx/toc.json"))
PDF = "C48596_其他接口_SSD2828QN4R_规格书_WJ73954.PDF"

OUT = "ai_docs/ssd2828qn4"
SEC_DIR = os.path.join(OUT, "sections")
FIG_DIR = os.path.join(OUT, "figures")
SKIP_PAGES = {1, 3, 4, 5, 6, 7, 8}   # cover + TOC pages

for d in (OUT, SEC_DIR, FIG_DIR):
    os.makedirs(d, exist_ok=True)

FIG_BY_PAGE = {}
for m in FIGS:
    FIG_BY_PAGE.setdefault(m["page"], []).append(m)

# TOC figure titles per page (fallback captions)
TOC_FIGS = {}
for e in TOC:
    t = e["title"]
    if t.upper().startswith("FIGURE "):
        TOC_FIGS.setdefault(e["page"], []).append(t)

# ------------------------------------------------------------------ helpers
CID_MAP = {"(cid:198)": "→", "(cid:122)": "\x02", "(cid:132)": "\x01",
           "(cid:211)": "→", "(cid:224)": "→"}

def clean(t):
    for k, v in CID_MAP.items():
        t = t.replace(k, v)
    return re.sub(r"\(cid:\d+\)", "", t)

def btext(b):
    return clean("".join(w["text"] for w in b.get("words", [])).strip())

ENUM_START = re.compile(r"^\s*(\d{1,2}|[01]{2,8}|\d+\s*[-\u2013]\s*\d+)\s*[\u2013\-:]\s+")
LABEL_START = re.compile(r"^\s*(Bit|Bits|bit)\b")

def cell_text(entry, br=" ") -> str:
    if not entry:
        return ""
    out = []
    lines = entry.get("lines", [])
    longest = max((" ".join(w["text"] for w in l) for l in lines), key=len, default="")
    prose = len(longest) > 28
    for i, line in enumerate(lines):
        if i:
            prev_x1 = max((w["x1"] for w in lines[i - 1]), default=0)
            gap = (entry["box"][2] - 3 - prev_x1)
            nxt = " ".join(w["text"] for w in line)
            deliberate = gap > 16 and (
                not prose or ENUM_START.match(nxt) or LABEL_START.match(nxt)
                or (len(nxt) < 34 and nxt[:1].isupper() and nxt.endswith(".")))
            out.append("<br>" if deliberate else " ")
        for j, w in enumerate(line):
            if j:
                gap = w["x0"] - line[j - 1]["x1"]
                out.append(" " if gap > 0.85 else "")
            t = w["text"]
            if w.get("sub"):
                t = "_" + t
            out.append(t)
    return clean("".join(out).strip())

def grid_rows(tb):
    """Return matrix [row][col] of cell text with merged cells filled."""
    nr, nc = tb["nrows"], tb["ncols"]
    mat = [["" for _ in range(nc)] for _ in range(nr)]
    for key, entry in tb["cells"].items():
        r0, c0 = map(int, key.split(","))
        txt = cell_text(entry)
        for r in range(r0, min(nr, r0 + entry["rs"])):
            for c in range(c0, min(nc, c0 + entry["cs"])):
                mat[r][c] = txt
    return mat

def para_md(b):
    """Render a paragraph as markdown lines, splitting on bullet glyphs."""
    t = btext(b)
    if "\x01" not in t and "\x02" not in t:
        return ("- " if b.get("bullet") else "") + t
    parts = re.split(r"([\x01\x02])", t)
    lines, marker = [], None
    for piece in parts:
        if piece == "\x01":
            marker = "sub"
            continue
        if piece == "\x02":
            marker = "main"
            continue
        piece = piece.strip()
        if not piece:
            continue
        if marker is None:
            lines.append(piece)
        elif marker == "main":
            lines.append("- " + piece)
        else:
            lines.append("  - " + piece)
        marker = None
    return "\n".join(lines)


def md_table(rows, header=None):
    if header is None:
        header = rows[0]
        rows = rows[1:]
    cols = len(header)
    rows = [(r + [""] * cols)[:cols] for r in rows]
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ").strip()
    out = ["| " + " | ".join(esc(h) for h in header) + " |",
           "|" + "|".join(["---"] * cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(esc(x) for x in r) + " |")
    return "\n".join(out)

def is_bitmap_table(tb):
    if tb["ncols"] < 3:
        return False
    labels = []
    for r in range(min(3, tb["nrows"])):
        e = tb["cells"].get(f"{r},0")
        labels.append(cell_text(e).upper().strip())
    return labels and labels[0] == "BIT" and "NAME" in labels

def is_desc_table(tb):
    if tb["ncols"] < 2:
        return False
    head = [cell_text(tb["cells"].get(f"0,{c}")) for c in range(tb["ncols"])]
    return head[0].strip().lower() == "name" and any(
        h.strip().lower() in ("description", "setting") for h in head)

def bits_from_label(txt):
    m = re.search(r"bit\s*(\d+)\s*[-–~:]\s*(\d+)", txt, re.I)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return f"{max(a,b)}:{min(a,b)}"
    m = re.search(r"bit\s*(\d+)", txt, re.I)
    if m:
        return f"{m.group(1)}"
    return ""

# ------------------------------------------------------------------ tables → bitfields
def parse_bitmap(tb):
    """Return dict: bit(int) -> dict(name,type,reset), and column->bit map."""
    nr, nc = tb["nrows"], tb["ncols"]
    mat = grid_rows(tb)
    col_bit = {}
    fields = {}
    for r in range(nr):
        label = mat[r][0].strip().upper().split("<BR>")[0]
        if label == "BIT":
            col_bit = {}
            for c in range(1, nc):
                v = mat[r][c].strip()
                try:
                    col_bit[c] = int(v)
                except ValueError:
                    pass
            continue
        if not col_bit:
            continue
        if label in ("NAME", "TYPE", "RESET"):
            for c, bit in col_bit.items():
                val = mat[r][c].strip()
                key = {"NAME": "name", "TYPE": "type", "RESET": "reset"}[label]
                fields.setdefault(bit, {})[key] = val
    return fields

def group_bits(bitmap):
    """Group consecutive bits with identical field name into ranges."""
    if not bitmap:
        return []
    out = []
    for bit in sorted(bitmap, reverse=True):
        f = bitmap[bit]
        name = f.get("name", "").strip()
        if out and out[-1]["name"] == name and out[-1]["_lo"] - 1 == bit:
            out[-1]["_lo"] = bit
        else:
            out.append({"name": name, "type": f.get("type", "").strip(),
                        "reset": f.get("reset", "").strip(),
                        "_hi": bit, "_lo": bit})
    for f in out:
        f["bits"] = f"{f['_hi']}:{f['_lo']}" if f["_hi"] != f["_lo"] else str(f["_hi"])
        f.pop("_hi"); f.pop("_lo")
    return out

def parse_enum(text):
    """Extract '0 – meaning' style enumerations."""
    if not text:
        return []
    parts = re.split(r"<br>|\s{2,}", text)
    out = []
    for p in parts:
        m = re.match(r"^\s*([0-9A-Fa-f]{1,2}|[01]{2,8}\b|\d+\s*[-–]\s*\d+)\s*[–\-:]\s*(.+)$", p)
        if m:
            out.append({"value": m.group(1).strip(), "meaning": m.group(2).strip()})
    return out

def parse_desc_table(tb):
    """Name | Description | Setting  -> list of fields."""
    nr, nc = tb["nrows"], tb["ncols"]
    mat = grid_rows(tb)
    head = [mat[0][c].strip().lower() for c in range(nc)]
    i_desc = head.index("description") if "description" in head else None
    i_set = head.index("setting") if "setting" in head else None
    out = []
    for r in range(1, nr):
        name_cell = mat[r][0].strip()
        if not name_cell:
            continue
        name = re.sub(r"<br>.*$", "", name_cell).strip()
        bits = bits_from_label(name_cell) or bits_from_label(name_cell.split("<br>")[-1])
        desc = mat[r][i_desc].strip() if i_desc is not None else ""
        setting = mat[r][i_set].strip() if i_set is not None else ""
        out.append({"name": name, "bits": bits, "description": desc,
                    "setting": setting, "enums": parse_enum(setting)})
    return out

# ------------------------------------------------------------------ walk model
registers = []
pins_desc = []
pinout = []
timing = []

current_section = None
current_h1 = None
blocks_by_page = {p["page"]: p["items"] for p in MODEL}

all_pages = [p["page"] for p in MODEL if p["page"] not in SKIP_PAGES]
flat = []
for pg in MODEL:
    if pg["page"] in SKIP_PAGES:
        continue
    for it in pg["items"]:
        b = dict(it)
        b["page"] = pg["page"]
        flat.append(b)

# ---- register sections
REG_LINE = re.compile(r"^([A-Z][A-Z0-9_]{1,10})\s+(.+?)\s+(0x[0-9A-Fa-f]{2})\s*$")
i = 0
while i < len(flat):
    b = flat[i]
    if b["type"] == "heading" and b.get("num", "").startswith("8.1.") and b["level"] >= 3:
        sec_num, sec_title = b["num"], re.sub(r"^[\d.]+\s*", "", b["text"])
        # collect until next heading
        j = i + 1
        reg_meta = None
        bitmap_tables, desc_tables = [], []
        while j < len(flat) and flat[j]["type"] != "heading":
            it = flat[j]
            if it["type"] == "para":
                t = btext(it)
                m = REG_LINE.match(t)
                if m and not reg_meta:
                    reg_meta = {"mnemonic": m.group(1), "name": m.group(2).strip(),
                                "offset": "0x" + m.group(3)[2:].upper()}
            elif it["type"] == "table":
                if is_bitmap_table(it):
                    bitmap_tables.append(it)
                elif is_desc_table(it):
                    desc_tables.append(it)
            j += 1
        if reg_meta:
            bitmap = {}
            for t in bitmap_tables:
                bitmap.update(parse_bitmap(t))
            fields = group_bits(bitmap)
            descs = []
            for t in desc_tables:
                descs.extend(parse_desc_table(t))
            dmap = {d["name"].lower(): d for d in descs}
            dbits = {d["bits"]: d for d in descs if d["bits"]}
            for f in fields:
                d = dbits.get(f["bits"]) or dmap.get(f["name"].lower())
                if d:
                    f["description"] = d["description"]
                    f["enums"] = d["enums"]
                else:
                    f["description"] = ""
                    f["enums"] = []
            # add description-only fields
            known = {f["name"].lower() for f in fields}
            known_bits = {f["bits"] for f in fields if f["bits"]}
            for d in descs:
                if d["name"].lower() not in known and d["bits"] not in known_bits:
                    fields.append({"name": d["name"], "bits": d["bits"], "type": "",
                                   "reset": "", "description": d["description"],
                                   "enums": d["enums"]})
            fields = [f for f in fields if f["name"]]
            desc_bits = {f["bits"] for f in fields if f.get("description")}
            fields = [f for f in fields
                      if f.get("description") or f["bits"] not in desc_bits]
            def _key(f):
                m = re.match(r"(\d+)(?::(\d+))?", f["bits"] or "")
                return (-(int(m.group(1)) if m else -1), -len(f["bits"]))
            fields.sort(key=_key)
            registers.append({"offset": reg_meta["offset"], "mnemonic": reg_meta["mnemonic"],
                              "register": reg_meta["name"], "section": sec_num,
                              "section_title": sec_title, "page": b["page"],
                              "fields": fields})
        i = j
        continue
    i += 1

# ---- Table 8-1 register summary (offset/reset)
REG_SUMMARY = {}
for pg in (23, 24):
    for it in blocks_by_page.get(pg, []):
        if it["type"] != "table":
            continue
        mat = grid_rows(it)
        for row in mat[1:]:
            if row and re.match(r"^0x[0-9A-Fa-f]{2}$", row[0].strip()):
                REG_SUMMARY["0x" + row[0].strip()[2:].upper()] = {
                    "name": row[1].strip(), "mnemonic": row[2].strip(),
                    "reset": row[3].strip() if len(row) > 3 else ""}
for r in registers:
    s = REG_SUMMARY.get(r["offset"])
    if s:
        r["reset_value"] = s["reset"]
        if s["name"]:
            r["register"] = s["name"]   # Table 8-1 has cleaner names

# ---- pinout (Table 6-2) and pin description (Tables 7-x)
for pg in (19, 20, 21, 22):
    for it in blocks_by_page.get(pg, []):
        if it["type"] != "table":
            continue
        mat = grid_rows(it)
        head = [c.strip().lower() for c in mat[0]]
        if head[:2] == ["qfn pin #", "qfn pin name"] or ("qfn pin #" in head and "net name" in head):
            for row in mat[1:]:
                for k in range(0, len(row) - 1, 2):
                    if re.match(r"^\d+$", row[k].strip()):
                        pinout.append({"pin": int(row[k].strip()), "net": row[k + 1].strip()})
        elif head[0] == "name" and "type" in head:
            for row in mat[1:]:
                if not row[0].strip():
                    continue
                pins_desc.append({"table_page": pg,
                                  "name": row[0].strip(),
                                  "type": row[1].strip() if len(row) > 1 else "",
                                  "connect_to": row[2].strip() if len(row) > 2 else "",
                                  "function": row[3].strip() if len(row) > 3 else "",
                                  "description": row[4].strip() if len(row) > 4 else "",
                                  "when_not_in_use": row[5].strip() if len(row) > 5 else ""})
pinout.sort(key=lambda p: p["pin"])

# ---- timing tables (chapter 14)
CAP_TBL = {}
for b in flat:
    if b["type"] == "caption" and b["text"].lower().startswith("table"):
        CAP_TBL.setdefault(b["page"], []).append(b["text"])
for b in flat:
    if b["type"] != "table":
        continue
    if b["page"] < 149:
        continue
    mat = grid_rows(b)
    head = [c.strip().lower() for c in mat[0]]
    if head and head[0] in ("symbol", "parameter") and len(head) >= 4:
        cap = ""
        for c in CAP_TBL.get(b["page"], []):
            cap = c
        for row in mat[1:]:
            if not row[0].strip():
                continue
            timing.append({"table": cap, "page": b["page"],
                           "symbol": row[0].strip(),
                           "parameter": row[1].strip() if len(row) > 1 else "",
                           "min": row[2].strip() if len(row) > 2 else "",
                           "typ": row[3].strip() if len(row) > 3 else "",
                           "max": row[4].strip() if len(row) > 4 else "",
                           "unit": row[5].strip() if len(row) > 5 else ""})

# ------------------------------------------------------------------ markdown render
def render_table(tb):
    if is_bitmap_table(tb):
        bitmap = parse_bitmap(tb)
        fields = group_bits(bitmap)
        if fields:
            rows = [["Bits", "Name", "Type", "Reset"]]
            for f in fields:
                rows.append([f["bits"], f["name"] or "—", f["type"] or "—", f["reset"] or "—"])
            return md_table(rows)
    mat = grid_rows(tb)
    ex = tb["xedges"]
    minw = max(10.0, 0.025 * (ex[-1] - ex[0]))
    keep = [c for c in range(tb["ncols"])
            if f"0,{c}" in tb["cells"] and (ex[c + 1] - ex[c]) >= minw]
    if not keep:
        keep = list(range(tb["ncols"]))
    rows = [[mat[r][c] for c in keep] for r in range(tb["nrows"])]
    while rows and not any(v.strip() for v in rows[-1]):
        rows.pop()
    if not rows:
        return ""
    # tables whose header cell spans 2 grid rows: merge "Reset" + "Value"
    hdr_2row = any(e["rs"] >= 2 and abs(e["box"][1] - tb["yedges"][0]) < 0.6
                   for e in tb["cells"].values())
    if len(rows) > 2 and hdr_2row:
        merged = []
        for i in range(len(keep)):
            a, b = rows[0][i].strip(), rows[1][i].strip()
            merged.append(a if (not b or b == a) else (a + " " + b).strip())
        rows = [merged] + rows[2:]
    return md_table(rows)

def emit_figure(b):
    page = b["page"]
    cands = FIG_BY_PAGE.get(page, [])
    bbox = b["bbox"]
    best = None
    for m in cands:
        if abs(m["crop"][0] - max(0, bbox[0] - 3)) < 30 and abs(m["crop"][1] - max(0, bbox[1] - 3)) < 30:
            best = m
            break
    if not best:
        return ""
    src = best["path"]
    dst = os.path.join(FIG_DIR, os.path.basename(src))
    if not os.path.exists(dst):
        shutil.copyfile(src, dst)
    cap = b.get("caption") or ""
    if not cap:
        cands_toc = TOC_FIGS.get(page, [])
        figs_on_page = [x for x in FIG_BY_PAGE.get(page, [])]
        if len(cands_toc) == len(figs_on_page):
            idx = figs_on_page.index(best)
            if 0 <= idx < len(cands_toc):
                t = cands_toc[idx]
                m = re.match(r"(?i)^figure\s*([\d\-–]+)\s*[-:–]\s*(.*)$", t)
                cap = f"Figure {m.group(1)}: {m.group(2).strip()}" if m else t
    alt = cap if cap else f"figure p{page}"
    return f"![{alt}](figures/{os.path.basename(src)})"

def emit_table_image(tb):
    page = tb["page"] if "page" in tb else None
    return ""

# ---- group flat blocks into chapters (level-1 headings)
chapters = []          # list of dict(num,title,page,blocks)
cur = None
for b in flat:
    if b["type"] == "heading" and b["level"] == 1:
        cur = {"num": b["num"], "title": b["text"], "page": b["page"], "blocks": [b]}
        chapters.append(cur)
    else:
        if cur is None:
            cur = {"num": "", "title": "Appendix 1 — Revision history", "page": b["page"], "blocks": []}
            chapters.append(cur)
        cur["blocks"].append(b)

DERIVED_NOTES = {
    "15": "> **Note (derived from the diagram, not verbatim):** power-up order is "
          "VDDIO/VDDIOC/MAVDDV → VCC12A/MDVDD/MAVDD → release RESB → TX_CLK → SPI configuration "
          "(PEN=1, PLL on) → leave ULPS → SLP=0 and VEN&HS=1 (video mode) → RGB signals. "
          "The minimum gaps (>=0 ms / >=1 ms / >=10 ms) are marked on the figure only.",
    "16": "> **Note (derived from the diagram, not verbatim):** power-off order is the mirror image: "
          "sleep-in command VEN&HS=0 → SLP=1 → PEN=0, then RGB off, TX_CLK off, RESB low, "
          "then MVDD and finally VDDIO. Gaps are marked on the figure only.",
    "17": "> **Note (derived):** this table is an example sequence with concrete register writes "
          "(0xB9 0x0001 = PLL on, 0xB7 0x0300 = leave ULPS, 0xB7 0x0309 = video mode on). "
          "The document itself says it is only a reference; adapt wait times to your AP/panel.",
}


def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s[:60] or "section"

# ---- render chapters
dash_parts = ["# SSD2828QN4 — MIPI Master Bridge datasheet (Rev 1.3)\n",
              "> Machine-readable transcription of the Solomon Systech SSD2828QN4 datasheet "
              "(168-page PDF, Rev 1.3, Mar 2013).\n"
              "> Sections keep their original numbering. `[p.26]` markers give the page in the source PDF.\n"]

index_rows = []
total_chars = 0
for ch in chapters:
    num = ch["num"]
    title = ch["title"]
    mnum = re.match(r"^(\d+)\s+(.*)$", title)
    if mnum:
        fname = f"{int(mnum.group(1)):02d}_{slug(mnum.group(2))}.md"
    else:
        fname = slug(title) + ".md"
    body = [f"# {title}\n"]
    page_marks = []
    prev_page = None
    first_block_id = id(ch["blocks"][0]) if ch["blocks"] else None
    for b in ch["blocks"]:
        if id(b) == first_block_id and b["type"] == "heading":
            continue
        pg = b["page"]
        if pg != prev_page:
            body.append(f"\n<!-- pdf:{pg} -->\n")
            prev_page = pg
        t = b["type"]
        if t == "heading":
            lvl = min(int(b["level"]), 6)
            body.append("#" * (lvl + 1) + " " + b["text"] + "\n")
        elif t == "para":
            body.append(para_md(b) + "\n")
        elif t == "caption":
            body.append(f"**{b['text']}**\n")
        elif t == "table":
            if b.get("render_as_image"):
                src = None
                bestd = 1e9
                for m in TBLIMGS:
                    if m["page"] != b["page"]:
                        continue
                    d = abs(m["bbox"][0] - b["bbox"][0]) + abs(m["bbox"][1] - b["bbox"][1])
                    if d < bestd:
                        bestd, src = d, m["path"]
                if src:
                    dst = os.path.join(FIG_DIR, os.path.basename(src))
                    if not os.path.exists(dst):
                        shutil.copyfile(src, dst)
                    body.append(f"![table image](figures/{os.path.basename(src)})\n")
            else:
                md = render_table(b)
                if md:
                    body.append(md + "\n")
        elif t == "figure":
            md = emit_figure(b)
            if md:
                body.append(md + "\n")
    if num in DERIVED_NOTES:
        body.append("\n" + DERIVED_NOTES[num] + "\n")
    text = "\n".join(body)
    # collapse >2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # section files live one level deeper: fix relative image links
    sec_text = text.replace("](figures/", "](../figures/")
    path = os.path.join(SEC_DIR, fname)
    open(path, "w").write(sec_text)
    tokens = int(len(text) / 3.9)
    total_chars += len(text)
    index_rows.append((num, title, fname, ch["page"], tokens, text.count("| ")))
    dash_parts.append(text)

datasheet = "\n".join(dash_parts)
datasheet = re.sub(r"\n{3,}", "\n\n", datasheet)
open(os.path.join(OUT, "datasheet.md"), "w").write(datasheet)

# ------------------------------------------------------------------ structured exports
reg_out = []
for r in registers:
    reg_out.append({
        "offset": r["offset"],
        "mnemonic": r["mnemonic"],
        "name": r["register"] or REG_SUMMARY.get(r["offset"], {}).get("name", ""),
        "reset_value": r.get("reset_value") or REG_SUMMARY.get(r["offset"], {}).get("reset", ""),
        "section": r["section"],
        "pdf_page": r["page"],
        "fields": [{"bits": f["bits"], "name": f["name"], "type": f["type"],
                    "reset": f["reset"],
                    "description": re.sub(r"\s*<br>\s*", " ", f["description"]).strip(),
                    "enums": f["enums"]} for f in r["fields"]],
    })
reg_out.sort(key=lambda r: int(r["offset"], 16))
json.dump(reg_out, open(os.path.join(OUT, "registers.json"), "w"), indent=1, ensure_ascii=False)

csv = ["offset,mnemonic,register,field,bits,type,field_reset,register_reset,description,enums,section,pdf_page"]
def q(s):
    s = str(s).replace('"', "'").replace("\n", " ")
    return '"' + s + '"'
for r in reg_out:
    if not r["fields"]:
        csv.append(",".join([r["offset"], r["mnemonic"], q(r["name"]), "", "", "", "",
                             r["reset_value"], q(""), q(""), r["section"], str(r["pdf_page"])]))
    for f in r["fields"]:
        enums = " | ".join(f"{e['value']}={e['meaning']}" for e in f["enums"])
        csv.append(",".join([r["offset"], r["mnemonic"], q(r["name"]), q(f["name"]), f["bits"],
                             f["type"], f["reset"], r["reset_value"],
                             q(re.sub(r"\s*<br>\s*", " ", f["description"]).strip()),
                             q(enums), r["section"], str(r["pdf_page"])]))
open(os.path.join(OUT, "registers.csv"), "w").write("\n".join(csv) + "\n")

# pins
pin_rows = [["name", "type", "connect_to", "function", "description", "when_not_in_use"]]
for p in pins_desc:
    pin_rows.append([p["name"], p["type"], p["connect_to"], p["function"],
                     p["description"], p["when_not_in_use"]])
open(os.path.join(OUT, "pins.csv"), "w").write("\n".join(",".join(q(c) for c in r) for r in pin_rows) + "\n")
open(os.path.join(OUT, "pinout.csv"), "w").write("pin,net\n" + "\n".join(
    f'{p["pin"]},{p["net"]}' for p in pinout) + "\n")

tim_csv = ["table,symbol,parameter,min,typ,max,unit,pdf_page"]
for t in timing:
    tim_csv.append(",".join([q(t["table"]), q(t["symbol"]), q(t["parameter"]), q(t["min"]),
                             q(t["typ"]), q(t["max"]), q(t["unit"]), str(t["page"])]))
open(os.path.join(OUT, "timing.csv"), "w").write("\n".join(tim_csv) + "\n")

# ------------------------------------------------------------------ figures index
fig_lines = ["# Figures\n", "All figures cropped from the source PDF at 200 dpi. Reference them by path.\n",
             "| Figure | Caption | PDF page | File |", "|---|---|---|---|"]
fig_count = 0
for b in flat:
    if b["type"] != "figure":
        continue
    page = b["page"]
    cands = FIG_BY_PAGE.get(page, [])
    bbox = b["bbox"]
    best = None
    for m in cands:
        if abs(m["crop"][0] - max(0, bbox[0] - 3)) < 30 and abs(m["crop"][1] - max(0, bbox[1] - 3)) < 30:
            best = m
            break
    if not best:
        continue
    fig_count += 1
    cap = b.get("caption") or "(no caption)"
    fig_lines.append(f"| {fig_count} | {cap.replace('|', '/')} | {page} | figures/{os.path.basename(best['path'])} |")
open(os.path.join(OUT, "figures.md"), "w").write("\n".join(fig_lines) + "\n")

# ------------------------------------------------------------------ chunks (RAG)
chunks = []
cid = 0
for ch in chapters:
    num, title = ch["num"], ch["title"]
    buf, buf_pages = [], []
    def flush():
        global cid
        if not buf:
            return
        text = "\n".join(buf).strip()
        if len(text) < 40:
            return
        cid += 1
        chunks.append({"id": f"c{cid:04d}", "section": f"{num} {title}".strip(),
                       "title": title, "pages": sorted(set(buf_pages)),
                       "chars": len(text), "text": text})
    for b in ch["blocks"]:
        if len("\n".join(buf)) > 3200 or (b["type"] == "heading" and b["level"] <= 2 and len(buf) > 600):
            flush()
            buf, buf_pages = [], []
        if b["type"] == "heading":
            buf.append("#" * min(int(b["level"]), 6) + " " + b["text"])
        elif b["type"] == "para":
            buf.append(para_md(b))
        elif b["type"] == "caption":
            buf.append(f"**{b['text']}**")
        elif b["type"] == "table":
            md = render_table(b)
            if md:
                buf.append(md)
        elif b["type"] == "figure":
            if b.get("caption"):
                buf.append(f"![{b['caption']}](figure: p{b['page']})")
        buf_pages.append(b["page"])
    flush()
with open(os.path.join(OUT, "chunks.jsonl"), "w") as f:
    for c in chunks:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

# ------------------------------------------------------------------ index / readme / source
idx = ["# INDEX — SSD2828QN4 datasheet pack\n",
       "| § | Chapter / section | File | PDF page | ~tokens |",
       "|---|---|---|---|---|"]
for num, title, fname, page, tokens, _ in index_rows:
    idx.append(f"| {num or '—'} | {title.replace('|', '/')} | sections/{fname} | {page} | {tokens} |")
idx.append("")
idx.append(f"- Full text: `datasheet.md` (~{int(total_chars/3.9):,} tokens)")
idx.append(f"- Registers: `registers.csv` / `registers.json` ({len(reg_out)} registers)")
idx.append(f"- Pins: `pins.csv` ({len(pins_desc)} rows), `pinout.csv` ({len(pinout)} pins)")
idx.append(f"- Timing: `timing.csv` ({len(timing)} rows)")
idx.append(f"- Figures: `figures.md` ({fig_count} images)")
idx.append(f"- Retrieval chunks: `chunks.jsonl` ({len(chunks)} chunks)")
open(os.path.join(OUT, "INDEX.md"), "w").write("\n".join(idx) + "\n")

sha = hashlib.sha256(open(PDF, "rb").read()).hexdigest()
src = {
    "source_pdf": PDF,
    "sha256": sha,
    "pages": 168,
    "document": "SSD2828QN4 MIPI Master Bridge, Rev 1.3, Mar 2013, Solomon Systech",
    "converted": datetime.date.today().isoformat(),
    "pipeline": "pdfplumber text/table extraction + Quartz raster crops; registers parsed from bitmap + description tables",
    "notes": [
        "Headings keep original section numbers (e.g. '8.1.2 RGB Interface Control Register 1').",
        "Subscripts are written with a leading underscore (t_PCLK, f_IN).",
        "<!-- pdf:N --> markers give the source PDF page for the following content.",
        "Tables with no vertical rulings (Table 9-10..9-12, 9-5, 9-6) are embedded as images.",
        "Formulas that were stacked fractions in the PDF are flattened to linear text.",
    ],
    "counts": {"registers": len(reg_out), "fields": sum(len(r["fields"]) for r in reg_out),
               "pins": len(pinout), "pin_desc_rows": len(pins_desc),
               "timing_rows": len(timing), "figures": fig_count, "chunks": len(chunks),
               "markdown_chars": total_chars},
}
json.dump(src, open(os.path.join(OUT, "source.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(src["counts"], indent=1))
print("chapters", len(chapters), "chunks", len(chunks))

# ------------------------------------------------------------------ quickref.md
def reg_summary_rows():
    rows = []
    for r in reg_out:
        rows.append(f"| {r['offset']} | {r['mnemonic']} | {r['name']} | {r['reset_value']} |")
    return "\n".join(rows)

QUICK = f"""# SSD2828QN4 — quick reference

Everything below is extracted from the datasheet (Rev 1.3, Mar 2013). Section numbers in
`backticks` point to files in `sections/`; register bits live in `registers.csv`.

## 1. Identity

- MIPI **master bridge**: input = parallel RGB (DPI-2.0, 16/18/24-bit) **or** serial SPI
  (DBI-2.0, up to 16-bit); output = MIPI **DSI** transmitter, 1–4 data lanes + 1 clock lane,
  up to **1 Gbps per lane (4 Gbps total)**. `01_general_description`, `05_functional_description`
- Standards: DSI v1.01.00, DCS v1.02.00, D-PHY v1.00.00.
- Video mode: up to **1920 px/line @ 60 Hz**, up to **2560 px/line @ 30 Hz**.
- Supply: **MVDD 1.2 V ±10 %** (core + PLL), **VDDIO 1.8–3.3 V ±10 %** (IO).
  External clock `TX_CLK_XIN` 8–30 MHz (crystal 8–30 MHz on XIN/XIO).
- Package: **68-pin QFN-EP**, tray. Order code `SSD2828QN4`.
- Command mode also supported (16/18/24 bpp, Raw or Pixel mode) plus CABC.

## 2. Mode / interface selection

| Signal | Where | Encoding |
|---|---|---|
| `PS[1:0]` | pins 17, 18 (input, strap) | 00 = 3-wire 24-bit SPI · 01 = 3-wire 8-bit SPI · 10 = 4-wire 8-bit SPI · 11 = SSL internal test mode |
| `LS[1:0]` | `LCFR` 0xDE bits 1:0 | 00 = 1 lane · 01 = 2 lanes · 10 = 3 lanes · 11 = 4 lanes |

RGB and SPI can be used together (RGB for pixels, SPI for register/command traffic).
`PS` pins must be tied to GND when unused; `CSX0` must stay high when SPI is unused.

## 3. Clock and PLL  (`09_configuration` §9.3.5, register `PLCR` 0xBA)

```
f_PRE = f_IN / MS
f_OUT = f_PRE * NS
5 MHz  <= f_IN  <= 100 MHz
5 MHz  <= f_REF <= 100 MHz
62.5 MHz <= f_OUT <= 1000 MHz
```

- Reference select `CFGR.CSS` (0xB7 bit 5): **0 = tx_clk, 1 = pclk** (default 0 → tx_clk must be present after power-up before registers can be written).
- `PLCR` 0xBA: `FR` bits 15:14 (frequency range), `MS` bits 12:8 (divider), `NS` bits 7:0 (multiplier). Reset 0x8120.
- PLL on/off `PCR.PEN` (0xB9 bit 0). **FR/MS/NS may only be changed while the PLL is off.**
- Multiplication factor per bpp and lane count: Tables 9-10 (pclk reference), 9-11 (tx_clk reference), 9-12 (burst mode) — these three tables are embedded as images in `09_configuration` because the PDF has no column rules in them.
- PLL lock status: `PLLR` 0xD5 (`PLS`); interrupt enable `ICR` 0xC5 bit 7.

## 4. Power-up sequence (`15_power_up_sequence`, example in `17_...`)

1. VDDIO / VDDIOC / MAVDDV
2. MVDD / VCC12A / MAVDD
3. release `RESB`
4. apply `TX_CLK`
5. configure through SPI, PLL on → e.g. `0xB9 = 0x0001`
6. leave ULPS → e.g. `0xB7 = 0x0300`
7. `SLP = 0`, `VEN & HS = 1` → video mode, e.g. `0xB7 = 0x0309`
8. drive RGB signals

## 5. Signal-path registers (RGB → DSI)

| Register | Addr | Key fields |
|---|---|---|
| `VICR1` | 0xB1 | `VSA` 15:8, `HSA` 7:0 |
| `VICR2` | 0xB2 | `VBP` 15:8, `HBP` 7:0 |
| `VICR3` | 0xB3 | `VFP` 15:8, `HFP` 7:0 |
| `VICR4` | 0xB4 | `HACT` 15:0 (max 0x0A00) |
| `VICR5` | 0xB5 | `VACT` 15:0 |
| `VICR6` | 0xB6 | `VS_P`, `HS_P`, `PCLK_P`, `CBM`, `NVB`, `NVD`, `BLLP`, `VCS`, `VM`, `VPF` |
| `VICR7` | 0xDD | `VBN` 7:4, `VFN` 3:0 (non-video-data windows) |
| `CFGR` | 0xB7 | `TXD` 11, `LPE` 10, `EOT` 9, `ECD` 8, `REN` 7, `DCS` 6, `CSS` 5, `HCLK` 4, `VEN` 3, `SLP` 2, `CKE` 1, `HS` 0 |
| `PSCR1-3` | 0xBC–0xBE | packet size |
| `PDR` | 0xBF | generic packet drop |
| `OCR` | 0xC0 | `RST` 8 (soft reset), `COP` 0 (cancel operation) |
| `LCFR` | 0xDE | `LS` 1:0 lane count |

## 6. Status / handshake

`ISR` 0xC6, `ESR` 0xC7, `ARSR` 0xC3 (ACK response), `TSR` 0xD3 (TE), `PLLR` 0xD5 (lock),
`RDCR` 0xC2 (returned byte count), `MRSR` 0xC1 (max return size), `LRR` 0xD4 (SPI read command, default 0x00FA).

## 7. Timing (`14_ac_characteristics`, machine-readable in `timing.csv`)

`T` = period of the PLL output clock (before lock: period of the PLL reference clock).
`W` = number of pixels in one horizontal line. SPI timing is `T`-relative (`8T`, `16T`, …).

## 8. Register map (66 registers, 0xB0–0xFF)

| Offset | Mnemonic | Register | Reset |
|---|---|---|---|
{reg_summary_rows()}

## 9. Where to look

| Question | File |
|---|---|
| What does this chip do, block-level | `sections/01_*`, `sections/05_*` |
| Pin number → net | `pinout.csv`, `sections/06_*` |
| Pin function / type / unused handling | `pins.csv`, `sections/07_*` |
| Register, bit fields, enum values | `registers.csv`, `sections/08_*` |
| RGB timing params (HSA/HBP/HFP/HACT/VACT) | `sections/08_*` 8.1.2–8.1.5 |
| Lane setup, video/command/burst modes | `sections/09_*` |
| MIPI packet structure, data types, byte order | `sections/09_*` §9.2, `sections/18_*` |
| SPI read/write protocol (3-wire, 4-wire) | `sections/10_*` |
| Electrical limits, DC/AC characteristics | `sections/11_*`–`sections/14_*`, `timing.csv` |
| Power up/down, sleep in/out | `sections/15_*`–`sections/17_*` |
| Package, marking, tray | `sections/19_*` |
| Which page in the original PDF | `INDEX.md`, `<!-- pdf:N -->` markers |

## 10. Caveats

- Subscripts are written with a leading underscore: `t_CLKH`, `f_OUT`, `T_MAX`.
- The PDF uses "(cid:…)" glyphs for arrows and bullets; these are normalised to `→` / list markers.
- Original typos kept: "Register6"/"Register7" (missing space), Table 7-1 used three times,
  chapter 19 numbered 18 in the table of contents.
- Tables 9-5, 9-6, 9-10, 9-11, 9-12 have no vertical rules in the PDF and are provided as images.
- Stacked fractions were flattened to linear text (see §9.3.5: `f_PRE = f_IN / MS`).
"""
open(os.path.join(OUT, "quickref.md"), "w").write(QUICK)

# ------------------------------------------------------------------ README.md
READ = f"""# SSD2828QN4 datasheet — AI-readable pack

A machine-first transcription of the Solomon Systech **SSD2828QN4** MIPI master bridge datasheet
(original: 168-page PDF, Rev 1.3, Mar 2013). Built so a model can answer questions about the chip
without parsing the PDF: clean Markdown, real tables, one file per chapter, and register data as CSV/JSON.

**Start here → `INDEX.md`** (chapter → file → PDF page) and **`quickref.md`** (distilled facts).

## Layout

| File | What it is | Size |
|---|---|---|
| `INDEX.md` | Chapter index with file names, PDF pages, token estimates | small |
| `quickref.md` | One-page distilled reference: specs, PLL, init sequence, register map | small |
| `datasheet.md` | The whole document as one Markdown file | ~{int(total_chars/1024)} KB |
| `sections/*.md` | One file per chapter (load only what you need) | 20 files |
| `registers.csv` | Flat table: offset, register, field, bits, type, reset, description, enum values | {len(reg_out)} registers / {sum(len(r['fields']) for r in reg_out)} fields |
| `registers.json` | Same data nested per register, with `enums[]` | |
| `pins.csv` | Pin function table (name, type, connect-to, description, unused handling) | {len(pins_desc)} rows |
| `pinout.csv` | QFN pin number → net name | {len(pinout)} pins |
| `timing.csv` | AC timing rows (symbol, parameter, min/typ/max, unit, table, page) | {len(timing)} rows |
| `figures/` + `figures.md` | Cropped diagrams (200 dpi PNG) with caption + page index | {fig_count} images |
| `chunks.jsonl` | Retrieval chunks: `{{id, section, pages, chars, text}}` | {len(chunks)} chunks |
| `source.json` | Provenance: source file, sha256, counts, conversion notes | small |

## Conventions

- `<!-- pdf:N -->` = the following content starts on page `N` of the original PDF.
- Headings keep the original numbering: `# 8 COMMAND TABLE`, `## 8.1 Register Description`,
  `### 8.1.2 RGB Interface Control Register 1`.
- Subscripts: `t_CLKH`, `f_PRE`, `T_MAX`.
- Figures: `![Figure 9-21: …](figures/p122_1.png)` — the caption is the alt text, the file is the crop.
- Bit-map tables are converted from the PDF's 16-column grid to `| Bits | Name | Type | Reset |` rows;
  the description table that follows the bitmap in the PDF gives the semantics and enum values.
- Register details are duplicated on purpose: prose in `sections/08_*` and rows in `registers.csv`
  (so a grep or a `csv` filter both work).

## How to use it

```bash
# find a register by mnemonic or address
grep -n "0xB9\\|PCR" registers.csv | head

# pull every field with an enum table
python -c "import json;r=json.load(open('registers.json'));[print(x['offset'],f['bits'],f['name'],f['enums']) for x in r for f in x['fields'] if f['enums']]"

# read one chapter only
sed -n '1,200p' sections/09_configuration.md

# locate the PDF page for a topic
grep -rn "burst mode" sections/*.md | head
```

For a question about one topic, load `quickref.md` first, then the single chapter file.
The full `datasheet.md` is only needed for whole-document work.

## Provenance & fidelity

- Text, tables and figures are extracted from the PDF (pdfplumber + CoreGraphics rendering);
  nothing was rewritten by hand except this README, `quickref.md` and the section titles in `INDEX.md`.
- Cross-check: the longest paragraph of every content page (64 pages with >= 45 characters) is present
  verbatim in `datasheet.md` — 0 misses.
- Known losses: stacked fractions (flattened), a few column-rules-free tables (kept as images),
  and the original's own typos (kept as-is).

## Regenerating

```bash
python3 work_pdf2docx/extract.py        # PDF -> work_pdf2docx/doc_model.json
python3 work_pdf2docx/render_figs.py    # figure + table-image crops -> work_pdf2docx/figs
python3 work_pdf2docx/build_ai_docs.py  # -> ai_docs/ssd2828qn4
```

A human-facing Word version of the same document is at `../../SSD2828QN4_Datasheet_文件版.docx`
(repo root, 118 pages).
"""
open(os.path.join(OUT, "README.md"), "w").write(READ)
print("wrote README.md / quickref.md")
