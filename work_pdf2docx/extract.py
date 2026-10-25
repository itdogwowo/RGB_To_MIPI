"""Extract a structured model of the SSD2828 datasheet PDF.

Output: work_pdf2docx/doc_model.json — a list of per-page blocks:
  {type: heading|para|caption|table|figure, ...}

Coordinate system: PDF points, origin at TOP-LEFT of the page.
"""
import json, re, sys
from collections import defaultdict
import pdfplumber

PDF = "C48596_其他接口_SSD2828QN4R_规格书_WJ73954.PDF"
TOC = json.load(open("work_pdf2docx/toc.json"))

# ---------- helpers ----------

def is_bold(fontname):
    return "Bold" in fontname or ",Bold" in fontname

def is_italic(fontname):
    return "Italic" in fontname or "Oblique" in fontname

def font_family(fontname):
    f = fontname.split("+")[-1]
    if f.startswith("TimesNewRoman") or f.startswith("Times"):
        return "Times New Roman"
    if f.startswith("Arial"):
        return "Arial"
    if f.startswith("Courier"):
        return "Courier New"
    if f.startswith("Symbol") or f.startswith("Wingding"):
        return "Symbol"
    return "Times New Roman"

SMALL = 7.0  # chars smaller than this are sub/superscripts

def build_tokens(page, y_min=0, y_max=10**6, x_min=0, x_max=10**6):
    """Return list of 'lines'; each line = dict(top, bottom, x0, x1, words[]).
    words = dict(text, bold, italic, size, family, sub, sup, x0, x1)."""
    chars = [c for c in page.chars if y_min <= c["top"] <= y_max and x_min <= c["x0"] <= x_max]
    normal = [c for c in chars if round(c["size"], 1) >= SMALL]
    small = [c for c in chars if round(c["size"], 1) < SMALL]

    # --- group normal chars into lines by vertical overlap
    lines = []
    for c in sorted(normal, key=lambda c: (round(c["top"], 1), c["x0"])):
        placed = False
        for ln in lines:
            overlap = min(ln["bottom"], c["bottom"]) - max(ln["top"], c["top"])
            h = min(c["bottom"] - c["top"], ln["bottom"] - ln["top"]) or 1
            if overlap > h * 0.55:
                ln["chars"].append(c)
                ln["top"] = min(ln["top"], c["top"])
                ln["bottom"] = max(ln["bottom"], c["bottom"])
                placed = True
                break
        if not placed:
            lines.append(dict(top=c["top"], bottom=c["bottom"], chars=[c]))
    lines.sort(key=lambda l: (l["top"], min(c["x0"] for c in l["chars"])))

    used = set()
    for ln in lines:
        ln["chars"].sort(key=lambda c: c["x0"])
        ltop, lbot = ln["top"], ln["bottom"]
        # attach sub/superscript chars
        for si, c in enumerate(small):
            if si in used:
                continue
            if ltop - 1 <= (c["top"] + c["bottom"]) / 2 <= lbot + 4:
                # must be horizontally inside the line's span (or just outside)
                xs = [cc["x0"] for cc in ln["chars"]] + [cc["x1"] for cc in ln["chars"]]
                if min(xs) - 6 <= c["x0"] <= max(xs) + 6:
                    c = dict(c)
                    c["_sub"] = 1
                    used.add(si)
                    ln["chars"].append(c)
        ln["chars"].sort(key=lambda c: c["x0"])

    out = []
    for ln in lines:
        words = []
        cur = None
        prev = None
        for c in ln["chars"]:
            fam = font_family(c["fontname"])
            b = is_bold(c["fontname"]); it = is_italic(c["fontname"])
            sz = round(c["size"], 1)
            sub = bool(c.get("_sub"))
            txt = c["text"]
            new = (cur is None or bool(c.get("_sub")) != cur["sub"] or b != cur["bold"]
                   or it != cur["italic"] or abs(sz - cur["size"]) > 0.4
                   or fam != cur["family"]
                   or (prev is not None and (c["x0"] - prev["x1"]) > max(1.1, sz * 0.16))
                   or txt.isspace())
            if txt.isspace():
                cur = None
                prev = c
                continue
            if new:
                cur = dict(text=txt, bold=b, italic=it, size=sz, family=fam, sub=sub,
                           x0=c["x0"], x1=c["x1"])
                words.append(cur)
            else:
                cur["text"] += txt
                cur["x1"] = c["x1"]
            prev = c
        # merge words separated by wide gaps into separate words is handled above;
        # now split words on internal whitespace
        wl = []
        for w in words:
            parts = w["text"].split()
            if len(parts) > 1:
                for p in parts:
                    d = dict(w); d["text"] = p
                    wl.append(d)
            elif parts:
                wl.append(w)
        if not wl:
            continue
        out.append(dict(top=ln["top"], bottom=ln["bottom"],
                        x0=min(w["x0"] for w in wl), x1=max(w["x1"] for w in wl),
                        words=wl))
    return out

def line_text(ln, sep=" "):
    return sep.join(w["text"] for w in ln["words"])

# ---------- table extraction ----------

def rect_color(rect):
    col = rect.get("non_stroking_color")
    if col is None:
        return None
    if isinstance(col, (list, tuple)):
        if len(col) == 3:
            r, g, b = col
        elif len(col) == 1:
            r = g = b = col[0]
        elif len(col) == 4:
            r, g, b = col[0], col[1], col[2]
        else:
            return None
    else:
        r = g = b = col
    # skip white / near white / near black (handled as text)
    r, g, b = [max(0.0, min(1.0, float(v))) for v in (r, g, b)]
    if r > 0.97 and g > 0.97 and b > 0.97:
        return None
    if r < 0.12 and g < 0.12 and b < 0.12:
        return None
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))

def extract_tables(page):
    tables = []
    for t in page.find_tables():
        cells = [c for c in t.cells if c is not None]
        if len(cells) < 4:
            continue
        xs = sorted({round(c[0], 2) for c in cells} | {round(c[2], 2) for c in cells})
        ys = sorted({round(c[1], 2) for c in cells} | {round(c[3], 2) for c in cells})
        if len(xs) < 2 or len(ys) < 2:
            continue
        def idx(arr, v):
            best, bi = 1e9, 0
            for i, a in enumerate(arr):
                if abs(a - v) < best:
                    best, bi = abs(a - v), i
            return bi
        grid = {}
        for c in cells:
            r0, r1 = idx(ys, c[1]), idx(ys, c[3])
            c0, c1 = idx(xs, c[0]), idx(xs, c[2])
            if r1 <= r0 or c1 <= c0:
                continue
            grid[(r0, c0)] = dict(box=[c[0], c[1], c[2], c[3]], rs=r1 - r0, cs=c1 - c0)
        # fills
        rects = [r for r in page.rects
                 if r["x0"] >= t.bbox[0] - 1 and r["x1"] <= t.bbox[2] + 1
                 and r["top"] >= t.bbox[1] - 1 and r["bottom"] <= t.bbox[3] + 1]
        for (r0, c0), cell in grid.items():
            bx = cell["box"]
            fill = None
            for r in rects:
                if abs(r["x0"] - bx[0]) < 1.2 and abs(r["top"] - bx[1]) < 1.2 \
                   and abs(r["x1"] - bx[2]) < 1.2 and abs(r["bottom"] - bx[3]) < 1.2:
                    col = rect_color(r)
                    if col:
                        fill = col
                    break
            if fill:
                cell["fill"] = fill
            # words inside
            lines = build_tokens(page, y_min=bx[1] - 0.5, y_max=bx[3] - 0.5,
                                 x_min=bx[0] + 0.3, x_max=bx[2] - 0.3)
            lines = [l for l in lines if l["top"] >= bx[1] - 1 and l["bottom"] <= bx[3] + 1]
            cell["lines"] = [[dict(text=w["text"], bold=w["bold"], italic=w["italic"],
                                   sub=w["sub"], size=w["size"], x0=w["x0"], x1=w["x1"])
                              for w in l["words"]] for l in lines]
        filled = [c for c in grid.values()
                  if any(w["text"].strip() for l in c.get("lines", []) for w in l)]
        if len(filled) < 3 or len(filled) / max(1, len(grid)) < 0.30:
            continue
        # quality check: borderless-column tables collapse to 1 column
        wide_single = 0
        for (r0, c0), cell in grid.items():
            if cell["cs"] >= 3:
                words = sum(len(l) for l in cell.get("lines", []))
                if words > 6:
                    wide_single += 1
        nrows_ = len(ys) - 1
        poor = (len(xs) - 1 <= 1) or (nrows_ > 2 and wide_single / max(1, nrows_) > 0.34)
        tables.append(dict(bbox=[round(v, 2) for v in t.bbox], render_as_image=poor,
                           nrows=len(ys) - 1, ncols=len(xs) - 1,
                           xedges=[round(v, 2) for v in xs],
                           yedges=[round(v, 2) for v in ys],
                           cells={f"{k[0]},{k[1]}": v for k, v in sorted(grid.items())}))
    tables.sort(key=lambda t: t["bbox"][1])
    return tables

# ---------- graphics / figures ----------

def graphics_clusters(page, exclude_boxes):
    objs = []
    for kind in ("lines", "curves", "rects"):
        for o in (getattr(page, kind) or []):
            if o["x1"] - o["x0"] < 0.4 and o["bottom"] - o["top"] < 0.4:
                continue
            cx, cy = (o["x0"] + o["x1"]) / 2, (o["top"] + o["bottom"]) / 2
            if any(b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1 for b in exclude_boxes):
                continue
            objs.append([o["x0"], o["top"], o["x1"], o["bottom"]])
    for o in page.images:
        cx, cy = (o["x0"] + o["x1"]) / 2, (o["top"] + o["bottom"]) / 2
        if any(b[0] - 1 <= cx <= b[2] + 1 and b[1] - 1 <= cy <= b[3] + 1 for b in exclude_boxes):
            continue
        objs.append([o["x0"], o["top"], o["x1"], o["bottom"]])
    # union-find clustering with tolerance
    tol = 7
    n = len(objs)
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for i in range(n):
        for j in range(i + 1, n):
            a, b = objs[i], objs[j]
            if (a[0] - tol <= b[2] and b[0] - tol <= a[2]
                    and a[1] - tol <= b[3] and b[1] - tol <= a[3]):
                union(i, j)
    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    clusters = []
    for idxs in groups.values():
        xs0 = min(objs[i][0] for i in idxs); xs1 = max(objs[i][2] for i in idxs)
        ys0 = min(objs[i][1] for i in idxs); ys1 = max(objs[i][3] for i in idxs)
        clusters.append(dict(bbox=[xs0, ys0, xs1, ys1], n=len(idxs)))
    clusters.sort(key=lambda c: (c["bbox"][0] * c["bbox"][1]))
    return clusters

# ---------- page assembly ----------

CAP_RE = re.compile(r"^(Table|Figure)\s+(\d+)\s*[-\u2013]\s*(\d+)\s*[:\-\u2013]?")
NUM_RE = re.compile(r"^(\d+(?:\.\d+)+|\d+)\s+([A-Z].*)$")
FOOTER_RE = re.compile(r"Rev\s+1\.3\s+P\s+\d+/168")

TOC_BY_NUM = {}
for e in TOC:
    if e["num"]:
        TOC_BY_NUM[e["num"]] = e

def in_box(ln, box, pad=1.0):
    cx, cy = (ln["x0"] + ln["x1"]) / 2, (ln["top"] + ln["bottom"]) / 2
    return box[0] - pad <= cx <= box[2] + pad and box[1] - pad <= cy <= box[3] + pad

CONTENT_TOP, CONTENT_BOTTOM = 62, 782
TEXT_W = 500.0

def merge_blocks(boxes, gap=26, xovl=8):
    """Merge graphic boxes that vertically follow each other with overlapping x range."""
    boxes = sorted(boxes, key=lambda b: b[1])
    out = []
    for b in boxes:
        if out:
            m = out[-1]
            if b[0] < m[2] + xovl and b[2] > m[0] - xovl and b[1] - m[3] < gap:
                m[0] = min(m[0], b[0]); m[1] = min(m[1], b[1])
                m[2] = max(m[2], b[2]); m[3] = max(m[3], b[3])
                continue
        out.append(list(b))
    return out

def process_page(page, pageno):
    tables = extract_tables(page)
    tbl_boxes = [t["bbox"] for t in tables]
    lines = build_tokens(page, y_min=CONTENT_TOP, y_max=CONTENT_BOTTOM)
    lines = [ln for ln in lines if not FOOTER_RE.search(line_text(ln))]

    # graphics blocks (candidate figure bodies), ignoring anything inside tables
    clusters = graphics_clusters(page, tbl_boxes)
    g = [c["bbox"] for c in clusters
         if (c["bbox"][2] - c["bbox"][0]) > 25 and (c["bbox"][3] - c["bbox"][1]) > 6
         and c["bbox"][1] >= CONTENT_TOP and c["bbox"][3] <= CONTENT_BOTTOM]
    gblocks = [b for b in merge_blocks(g) if (b[2] - b[0]) > 40 and (b[3] - b[1]) > 15]
    # drop blocks that sit entirely inside a table bbox
    def inside_tbl_box(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        return any(tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3] for tb in tbl_boxes)
    gblocks = [b for b in gblocks if not inside_tbl_box(b)]

    # split graphic blocks at figure/table caption lines that cross them
    cap_lines = [ln for ln in lines
                 if CAP_RE.match(line_text(ln)) is not None
                 and line_text(ln).lower().startswith(("figure ", "table "))]
    split_blocks = []
    for b in gblocks:
        pieces = [b]
        for cl in cap_lines:
            new_pieces = []
            for pc in pieces:
                if pc[1] + 4 < cl["top"] and cl["bottom"] + 4 < pc[3]:
                    top = [pc[0], pc[1], pc[2], cl["top"] - 2]
                    bot = [pc[0], cl["bottom"] + 2, pc[2], pc[3]]
                    if top[3] - top[1] > 12:
                        new_pieces.append(top)
                    if bot[3] - bot[1] > 12:
                        new_pieces.append(bot)
                else:
                    new_pieces.append(pc)
            pieces = new_pieces
        split_blocks.extend(pieces)
    gblocks = split_blocks

    def in_gblock(ln):
        return any(in_box(ln, b, pad=1.0) for b in gblocks)

    # text lines outside tables
    tlines = [ln for ln in lines if not any(in_box(ln, tb, pad=0.5) for tb in tbl_boxes)]

    # ---- paragraph grouping over text lines that are not inside graphic blocks
    free = [ln for ln in tlines if not in_gblock(ln)]
    paras = []
    cur = None
    for ln in free:
        txt = line_text(ln)
        hm = NUM_RE.match(txt)
        is_heading = False
        if hm and hm.group(1) in TOC_BY_NUM:
            t_norm = re.sub(r"[^a-z0-9]", "", TOC_BY_NUM[hm.group(1)]["title"].lower())[:14]
            rest = re.sub(r"[^a-z0-9]", "", txt[hm.end(1):].lower())[:14]
            is_heading = bool(t_norm) and (rest.startswith(t_norm[:10]) or t_norm.startswith(rest[:10]))
        is_bullet = txt[:1] in "\u2022\u00b7\u25aa\u25cf" or txt.startswith("\u00d8")
        mcap = CAP_RE.match(txt)
        is_caption = bool(mcap) and txt.lower().startswith(("table ", "figure ")) and (
            ":" in txt[:16] or (ln["x0"] > 95 and len(txt) < 140))
        if is_caption and paras and paras[-1]["kind"] == "caption" \
           and 0 <= ln["top"] - paras[-1]["bottom"] < 7:
            paras[-1]["lines"].append(ln)
            paras[-1]["bottom"] = ln["bottom"]
            paras[-1]["text"] = paras[-1]["text"] + " " + txt
            cur = None
            continue
        if (not is_caption and not is_heading and paras
                and paras[-1]["kind"] == "caption"
                and 0 <= ln["top"] - paras[-1]["bottom"] < 8 and len(txt) < 70):
            paras[-1]["lines"].append(ln)
            paras[-1]["bottom"] = ln["bottom"]
            paras[-1]["text"] = paras[-1]["text"] + " " + txt
            cur = None
            continue
        if is_caption or is_heading:
            cur = None
            paras.append(dict(kind="caption" if is_caption else "heading", lines=[ln],
                              top=ln["top"], bottom=ln["bottom"],
                              text=txt, num=(hm.group(1) if is_heading else None)))
            continue
        is_item = bool(re.match(r"^\d+\.\s", txt)) and ln["x0"] < (cur["x0"] + 2.5 if cur else 999)
        newpara = (cur is None or is_bullet or is_item or (ln["top"] - cur["bottom"]) > 6.5
                   or (abs(ln["x0"] - cur["x0"]) > 30 and (ln["top"] - cur["bottom"]) > 3.2))
        if newpara:
            cur = dict(kind="para", lines=[], top=ln["top"], bottom=ln["bottom"],
                       bullet=is_bullet, item=is_item)
            paras.append(cur)
        cur["lines"].append(ln)
        cur["bottom"] = ln["bottom"]
        cur["x0"] = min(cur.get("x0", ln["x0"]), ln["x0"])

    for pr in paras:
        if pr["kind"] == "para":
            w = max(ln["x1"] for ln in pr["lines"]) - min(ln["x0"] for ln in pr["lines"])
            pr["width"] = w
            y0 = min(ln["top"] for ln in pr["lines"])
            y1 = max(ln["bottom"] for ln in pr["lines"])
            overlaps_gfx = any(y0 < b[3] - 2 and y1 > b[1] + 2 for b in gblocks)
            pr["prose"] = (w > TEXT_W * 0.55 and pr["x0"] <= 78
                           and not pr["bullet"] and not overlaps_gfx)

    # ---- assemble ordered elements
    elems = []
    for pr in paras:
        blk = [ln["top"] for ln in pr["lines"]] + [ln["bottom"] for ln in pr["lines"]]
        pr["y0"], pr["y1"] = min(blk), max(blk)
        pr["x0"] = min(ln["x0"] for ln in pr["lines"])
        pr["x1"] = max(ln["x1"] for ln in pr["lines"])
        elems.append(pr)
    for b in gblocks:
        elems.append(dict(kind="gfx", bbox=b, y0=b[1], y1=b[3], x0=b[0], x1=b[2]))
    for t in tables:
        elems.append(dict(kind="table", bbox=t["bbox"], y0=t["bbox"][1], y1=t["bbox"][3],
                          x0=t["bbox"][0], x1=t["bbox"][2], table=t))
    elems.sort(key=lambda e: (e["y0"], e["x0"]))

    # ---- split into runs at prose paragraphs / headings / tables
    runs, cur_run = [], []
    for el in elems:
        if el["kind"] in ("table", "heading") or (el["kind"] == "para" and el.get("prose")):
            if cur_run:
                runs.append(cur_run); cur_run = []
            runs.append([el])
        else:
            cur_run.append(el)
    if cur_run:
        runs.append(cur_run)

    # ---- within runs, attach figure captions to adjacent graphics
    out = []
    for run in runs:
        if len(run) == 1 and run[0]["kind"] != "gfx":
            out.append(run[0]); continue
        caps = [i for i, e in enumerate(run) if e["kind"] == "caption"
                and e["text"].lower().startswith("figure")]
        if not caps:
            out.extend(run); continue
        used = set()
        segs = []
        prev = 0
        for ci in caps:
            segs.append(run[prev:ci]); segs.append([run[ci]]); prev = ci + 1
        segs.append(run[prev:])
        # segs: [before0, cap0, after0(before1), cap1, after1 ...]
        for si, seg in enumerate(segs):
            cap = seg[0] if len(seg) == 1 and seg[0]["kind"] == "caption" else None
            if not cap:
                continue
            before = segs[si - 1] if si > 0 else []
            after = segs[si + 1] if si + 1 < len(segs) else []
            # only consider graphics as figure body
            def score(segx, is_before):
                gs = [e for e in segx if e["kind"] == "gfx" and id(e) not in used]
                if not gs:
                    return (1e9, 0.0)
                if is_before:
                    dist = cap["y0"] - max(e["y1"] for e in gs)
                else:
                    dist = min(e["y0"] for e in gs) - cap["y1"]
                area = sum((e["y1"] - e["y0"]) for e in gs)
                return (max(dist, 0), -area)
            sb, sa = score(before, True), score(after, False)
            body = before if sb[0] <= sa[0] + 12 else after
            body = [e for e in body if e["kind"] in ("gfx", "para") and id(e) not in used]
            if not body:
                continue
            for e in body:
                used.add(id(e))
            # absorb label paragraphs that sit vertically inside the figure band
            by0 = min(e["y0"] for e in body); by1 = max(e["y1"] for e in body)
            for e in list(before) + list(after):
                if id(e) in used or e["kind"] != "para":
                    continue
                if e["y0"] >= by0 - 2 and e["y1"] <= by1 + 2:
                    body.append(e); used.add(id(e))
            x0 = min(e["x0"] for e in body); x1 = max(e["x1"] for e in body)
            y0 = min(e["y0"] for e in body); y1 = max(e["y1"] for e in body)
            out.append(dict(kind="figure", bbox=[x0, y0, x1, y1], caption=cap["text"],
                            y0=y0, y1=y1, x0=x0, x1=x1, cap_above=(sb <= sa)))
            used.add(id(cap))
        for e in run:
            if id(e) in used:
                continue
            out.append(e)
    # promote leftover graphic blocks to caption-less figures
    for e in out:
        if e["kind"] == "gfx":
            e["kind"] = "figure"
            e["caption"] = e.get("caption")
            e["cap_above"] = False
            e["bbox"] = [e["x0"], e["y0"], e["x1"], e["y1"]]

    # widen figure boxes over text lines that begin inside the drawing
    for e in [x for x in out if x["kind"] in ("figure", "gfx")]:
        for ln in free:
            cy = (ln["top"] + ln["bottom"]) / 2
            if e["y0"] + 1 <= cy <= e["y1"] - 1 and e["x0"] - 2 <= ln["x0"] <= e["x1"] + 2:
                if ln["x1"] > e["x1"]:
                    e["x1"] = ln["x1"]
                    if e["kind"] == "figure":
                        e["bbox"][2] = ln["x1"]
    # merge adjacent caption-less figure fragments (row of a diagram, stacked panels)
    merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            a = out[i]
            if a["kind"] != "figure" or a.get("caption"):
                continue
            for j in range(len(out)):
                if i == j:
                    continue
                b = out[j]
                if b["kind"] != "figure" or b.get("caption"):
                    continue
                vgap = max(a["y0"], b["y0"]) - min(a["y1"], b["y1"])
                xovl = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
                hgap = max(a["x0"], b["x0"]) - min(a["x1"], b["x1"])
                yovl = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
                if (vgap < 46 and xovl > 0) or (hgap < 60 and yovl > 0):
                    a["y0"] = min(a["y0"], b["y0"]); a["y1"] = max(a["y1"], b["y1"])
                    a["x0"] = min(a["x0"], b["x0"]); a["x1"] = max(a["x1"], b["x1"])
                    a["bbox"] = [a["x0"], a["y0"], a["x1"], a["y1"]]
                    out.remove(b)
                    merged = True
                    break
            if merged:
                break
    figs = [e for e in out if e["kind"] == "figure"]

    # post-pass: absorb label paragraphs that lie fully inside a figure box
    absorbed = set()
    changed = True
    while changed:
        changed = False
        for f in figs:
            for e in out:
                if e["kind"] != "para" or id(e) in absorbed:
                    continue
                if (e["y0"] >= f["y0"] - 1 and e["y1"] <= f["y1"] + 1
                        and e["x0"] >= f["x0"] - 6 and e["x1"] <= f["x1"] + 6
                        ):
                    absorbed.add(id(e))
                    f["bbox"][0] = min(f["bbox"][0], e["x0"])
                    f["bbox"][2] = max(f["bbox"][2], e["x1"])
                    f["x0"], f["x1"] = f["bbox"][0], f["bbox"][2]
                    changed = True
    out = [e for e in out if id(e) not in absorbed]

    # drop tables that are swallowed by a figure box (they are part of a drawing)
    fboxes = [e["bbox"] for e in out if e["kind"] == "figure"]
    keep = []
    for e in out:
        if e["kind"] == "table":
            tb = e["bbox"]
            area = max(1.0, (tb[2] - tb[0]) * (tb[3] - tb[1]))
            swallowed = False
            for fb in fboxes:
                ix = max(0.0, min(tb[2], fb[2]) - max(tb[0], fb[0]))
                iy = max(0.0, min(tb[3], fb[3]) - max(tb[1], fb[1]))
                if ix * iy / area > 0.75:
                    swallowed = True
                    break
            if swallowed:
                continue
        keep.append(e)
    out = keep

    # leftovers: gfx without caption -> figure without caption
    out.sort(key=lambda e: (e["y0"], e["x0"]))
    items = []
    for e in out:
        if e["kind"] == "heading":
            h = TOC_BY_NUM[e["num"]]
            items.append(dict(type="heading", level=h["level"], num=e["num"],
                              text=e["text"], y=round(e["y0"], 1)))
        elif e["kind"] == "caption":
            items.append(dict(type="caption", text=e["text"], y=round(e["y0"], 1)))
        elif e["kind"] == "para":
            items.append(dict(type="para", bullet=e.get("bullet", False),
                              item=e.get("item", False), words=para_words(e),
                              x0=round(e["x0"], 1), y=round(e["y0"], 1)))
        elif e["kind"] == "table":
            items.append(dict(type="table", **e["table"], y=round(e["y0"], 1)))
        elif e["kind"] == "figure":
            items.append(dict(type="figure", bbox=[round(v, 2) for v in e["bbox"]],
                              caption=e.get("caption"), cap_above=e.get("cap_above", False),
                              y=round(e["y0"], 1)))
        elif e["kind"] == "gfx":
            items.append(dict(type="figure", bbox=[round(v, 2) for v in e["bbox"]],
                              caption=None, cap_above=False, y=round(e["y0"], 1)))
    return items, tables


def para_words(para):
    """Flatten lines to word runs, keeping bold/italic/sub flags."""
    words = []
    prev = None
    prev_i = -1
    for i, ln in enumerate(para["lines"]):
        wl = ln["words"]
        if para.get("bullet") and i == 0:
            wl = wl[1:]
        for w in wl:
            if prev is not None:
                gap = w["x0"] - prev["x1"]
                if i != prev_i or gap > 0.85:
                    words.append(dict(text=" ", bold=False, italic=False, sub=False, size=0))
            words.append(w)
            prev = w
            prev_i = i
    return words


def main():
    pages_out = []
    with pdfplumber.open(PDF) as pdf:
        for pageno in range(1, len(pdf.pages) + 1):
            page = pdf.pages[pageno - 1]
            items, tables = process_page(page, pageno)
            pages_out.append(dict(page=pageno, items=items))
            print(f"page {pageno}: {len(items)} items", file=sys.stderr)
    json.dump(pages_out, open("work_pdf2docx/doc_model.json", "w"), ensure_ascii=False)
    print("wrote model", sum(len(p['items']) for p in pages_out), "items")

if __name__ == "__main__":
    main()
