#!/usr/bin/env python3
"""Render an EasyEDA Pro .esch2 sheet to PNG (layout sanity check only).

Draws: frame border, block rectangles, component bodies with pin stubs,
wires and net names. Not pixel-accurate to the client.
"""
import json, sys, collections
from PIL import Image, ImageDraw, ImageFont

def parse(path):
    recs = []
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        head, _, body = line.partition("||")
        if body.endswith("|"):
            body = body[:-1]
        try:
            h = json.loads(head)
        except Exception:
            continue
        try:
            b = json.loads(body) if body.strip() else {}
        except Exception:
            b = {}
        recs.append((h, b))
    return recs

def docs(recs):
    out, cur = [], None
    for h, b in recs:
        if h.get("type") == "DOCHEAD":
            cur = {"docType": b.get("docType"), "items": []}
            out.append(cur)
        if cur is not None:
            cur["items"].append((h, b))
    return out

def main(path, out, scale=2):
    recs = parse(path)
    ds = docs(recs)
    symbols = {}
    for d in ds:
        if d["docType"] == "SYMBOL":
            pins = []
            for h, b in d["items"]:
                if h.get("type") == "PIN":
                    pins.append(b)
            symbols[id(d)] = pins
    # map symbol uuid -> pins
    sym_by_uuid = {}
    for d in ds:
        if d["docType"] == "SYMBOL":
            title = next((b.get("title") for h, b in d["items"] if h.get("type") == "META"), "")
            uuid = None
            for h, b in d["items"]:
                if h.get("type") == "DOCHEAD":
                    uuid = b.get("uuid")
            pins = [b for h, b in d["items"] if h.get("type") == "PIN"]
            if uuid:
                sym_by_uuid[uuid] = pins
    page = [d for d in ds if d["docType"] == "SCH_PAGE"]
    if not page:
        print("no SCH_PAGE"); return
    items = page[0]["items"]
    comps, attrs, texts, rects = [], collections.defaultdict(dict), [], []
    wires = collections.defaultdict(list)
    wire_net = {}
    for h, b in items:
        t = h.get("type")
        if t == "COMPONENT":
            comps.append((h.get("id"), b))
        elif t == "ATTR":
            attrs[b.get("parentId")][b.get("key")] = b.get("value")
            if b.get("key") == "NET" and b.get("value"):
                wire_net[b.get("parentId")] = b["value"]
        elif t == "TEXT":
            texts.append(b)
        elif t == "RECT":
            rects.append(b)
        elif t == "LINE" and b.get("lineGroup"):
            wires[b["lineGroup"]].append(((b.get("startX"), b.get("startY")),
                                          (b.get("endX"), b.get("endY"))))

    # auto-fit: collect every coordinate, map to a canvas with margin
    xs, ys = [], []
    for cid, b in comps:
        xs.append(b.get("x", 0)); ys.append(b.get("y", 0))
    for wid, segs in wires.items():
        for a, b in segs:
            xs += [a[0], b[0]]; ys += [a[1], b[1]]
    for r in rects:
        xs += [r.get("dotX1", 0), r.get("dotX2", 0)]
        ys += [r.get("dotY1", 0), r.get("dotY2", 0)]
    for t in texts:
        xs.append(t.get("x", 0)); ys.append(t.get("y", 0))
    CX0, CX1 = min(xs) - 40, max(xs) + 40
    CY0, CY1 = min(ys) - 40, max(ys) + 40
    x0, y1 = CX0, CY1
    W = int(CX1 - CX0); H = int(CY1 - CY0)
    img = Image.new("RGB", (W * scale, H * scale), "white")
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 7 * scale)
        fontb = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 8 * scale)
    except Exception:
        font = fontb = ImageFont.load_default()

    def px(x, y):
        return ((x - x0) * scale, (y1 - y) * scale)

    dr.rectangle([2, 2, W * scale - 2, H * scale - 2], outline="black", width=2)
    for r in rects:
        rx1, rx2 = r.get("dotX1", 0), r.get("dotX2", 0)
        ry1, ry2 = r.get("dotY1", 0), r.get("dotY2", 0)
        sx0 = (min(rx1, rx2) - x0) * scale
        sx1 = (max(rx1, rx2) - x0) * scale
        sy0 = (y1 - max(ry1, ry2)) * scale
        sy1 = (y1 - min(ry1, ry2)) * scale
        dr.rectangle([sx0, sy0, sx1, sy1], outline=(150, 150, 150), width=1)
    for t in texts:
        x, y = px(t.get("x", 0), t.get("y", 0))
        dr.text((x, y), t.get("value", ""), fill=(20, 30, 120), font=fontb)
    # wires
    for wid, segs in wires.items():
        net = wire_net.get(wid, "")
        col = (120, 160, 220) if net else (140, 140, 140)
        for a, b in segs:
            dr.line([px(*a), px(*b)], fill=col, width=1)
        if net and segs:
            a, b = segs[0]
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            dr.text(((mx - x0) * scale + 2, (y1 - my) * scale - 3), net, fill=(200, 60, 40), font=font)
    # components
    for cid, b in comps:
        a = attrs.get(cid, {})
        ref = a.get("Designator") or ""
        symuuid = a.get("Symbol")
        pins = sym_by_uuid.get(symuuid, [])
        if not pins:
            continue
        cx, cy = b.get("x", 0), b.get("y", 0)
        xs = [p["x"] for p in pins]
        ys = [p["y"] for p in pins]
        px1, px2 = cx + min(xs), cx + max(xs)
        py1, py2 = cy + min(ys), cy + max(ys)
        bx0, bx1 = (px1 - CX0) * scale, (px2 - CX0) * scale
        by0, by1 = (CY1 - py2) * scale, (CY1 - py1) * scale
        dr.rectangle([bx0, by0, bx1, by1], outline=(30, 90, 30), width=2)
        dr.text((bx0 + 2, by0 - 9 * scale / 2), ref, fill=(0, 90, 0), font=fontb)
        # pin stubs
        for p in pins:
            px0, py0 = cx + p["x"], cy + p["y"]
            L = p.get("length", 10)
            rot = p.get("rotation", 0)
            dx, dy = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}.get(rot % 360, (-1, 0))
            dr.line([px(px0, py0), px(px0 + dx * L, py0 + dy * L)], fill=(30, 90, 30), width=1)
        dr.text((bx0 + 2, by1 + 2), str(a.get("Name") or "")[:22], fill=(90, 90, 90), font=font)
    img.save(out)
    print("wrote", out, "wires:", len(wires), "components:", len(comps))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
