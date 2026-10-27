#!/usr/bin/env python3
"""repair4: move the design into the A4 frame and make stubs END on the pin anchors.

Lessons from the bridge: EasyEDA connects a pin only when a wire ENDPOINT sits on
the pin coordinate reported by getAllPinsByPrimitiveId(). A wire that merely
passes over the pin does not connect.
"""
import json, os, sys, shutil, collections

P = sys.argv[1]
lines = open(P, encoding="utf-8").read().split("\n")
shutil.copyfile(P, P + ".bak4")

def parse(line):
    head, _, body = line.partition("||")
    if body.endswith("|"):
        body = body[:-1]
    try:
        h = json.loads(head)
    except Exception:
        return None, None
    try:
        b = json.loads(body) if body.strip() else {}
    except Exception:
        b = {}
    return h, b

def rec(h, b):
    return json.dumps(h, separators=(",", ":")) + "||" + json.dumps(b, separators=(",", ":")) + "|"

docs, cur = [], None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD":
        cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "idx": i, "items": []}
        docs.append(cur)
    if cur is not None:
        cur["items"].append((i, h, b))
page = [d for d in docs if d["docType"] == "SCH_PAGE"][0]
p_start = page["idx"]
p_end = docs[docs.index(page) + 1]["idx"] if docs.index(page) + 1 < len(docs) else len(lines)

sym_pins = {}
for d in docs:
    if d["docType"] != "SYMBOL":
        continue
    pa = collections.defaultdict(dict)
    raw = []
    for i, h, b in d["items"]:
        if h and h.get("type") == "PIN":
            raw.append((h["id"], b))
        elif h and h.get("type") == "ATTR":
            pa[b.get("parentId")][b.get("key")] = b.get("value")
    sym_pins[d["uuid"]] = [dict(num=str(pa[i].get("Pin Number")), name=str(pa[i].get("Pin Name")),
                                x=b.get("x", 0), y=b.get("y", 0), ln=b.get("length", 10),
                                rot=int(b.get("rotation", 0)) % 360) for i, b in raw]

comps, attrs, wires, wnet, wlines = {}, collections.defaultdict(dict), {}, {}, collections.defaultdict(list)
for i in range(p_start + 1, p_end):
    h, b = parse(lines[i])
    if not h:
        continue
    t = h.get("type")
    if t == "COMPONENT":
        comps[h["id"]] = (i, b)
    elif t == "ATTR":
        attrs[b.get("parentId")][b.get("key")] = b.get("value")
    elif t == "WIRE":
        wires[h["id"]] = i
    elif t == "LINE" and b.get("lineGroup"):
        wlines[b["lineGroup"]].append((i, b))
for i in range(p_start + 1, p_end):
    h, b = parse(lines[i])
    if h and h.get("type") == "ATTR" and b.get("key") == "NET":
        wnet[b.get("parentId")] = b.get("value")

by_ref = {attrs[c].get("Designator"): c for c in comps if attrs[c].get("Designator")}

def place(cx, cy, dx, dy, rot):
    rot = int(rot) % 360
    return [(cx + dx, cy + dy), (cx - dy, cy + dx), (cx - dx, cy - dy), (cx + dy, cy - dx)][rot // 90]

def anchors(cid):
    i, c = comps[cid]
    out = []
    for p in sym_pins.get(attrs[cid].get("Symbol"), []):
        ax, ay = place(c["x"], c["y"], p["x"], p["y"], c.get("rotation", 0))
        out.append((p, ax, ay))
    return out

# ---- 1. recover the intended net of every pin from the existing stubs
def dist_pt_seg(pt, a, b):
    ax, ay = a; bx, by = b; px, py = pt
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5

seglist = []
for wid, segs in wlines.items():
    net = wnet.get(wid)
    if not net:
        continue
    for i, b in segs:
        seglist.append(((b["startX"], b["startY"]), (b["endX"], b["endY"]), net))

pin_net = {}
for ref, cid in by_ref.items():
    for p, ax, ay in anchors(cid):
        best = None
        for a, b, net in seglist:
            d = dist_pt_seg((ax, ay), a, b)
            if d < 6 and (best is None or d < best[0]):
                best = (d, net)
        if best:
            pin_net[(ref, p["num"])] = best[1]

# ---- 2. new layout (all inside the A4 frame)
LAYOUT = {
    "J3": (120, 540), "J4": (120, 200),
    "U4": (370, 560), "U5": (370, 210),
    "U1": (640, 420),
    "J1": (1010, 580), "J2": (1010, 290),
    "U2": (330, 80), "U3": (460, 80), "Y1": (580, 80),
    "C1": (860, 90), "C2": (900, 90), "C3": (940, 90), "C4": (980, 90),
    "C5": (700, 150), "C6": (760, 150),
}

# ---- 3. drop every wire
remove = set()
for wid, i in wires.items():
    remove.add(i)
    for j, b in wlines.get(wid, []):
        remove.add(j)
for i in range(p_start + 1, p_end):
    h, b = parse(lines[i])
    if h and h.get("type") == "ATTR" and b.get("parentId") in wires:
        remove.add(i)

# ---- 4. move components
for ref, (x, y) in LAYOUT.items():
    cid = by_ref.get(ref)
    if not cid:
        print("!! missing", ref); continue
    i, c = comps[cid]
    c["x"], c["y"] = x, y
    h, _ = parse(lines[i])
    lines[i] = rec(h, c)

# ---- 5. new stubs: endpoint exactly on the pin anchor
max_ticket = max((parse(l)[0] or {}).get("ticket", 0) or 0 for l in lines) + 1
tick = [max_ticket]
zz = [1]
new_lines = []

def add_wire(a, b, net):
    wid = os.urandom(8).hex()
    new_lines.append(rec({"type": "WIRE", "ticket": tick[0], "id": wid}, {"zIndex": zz[0]})); tick[0] += 1; zz[0] += 1
    new_lines.append(rec({"type": "LINE", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "fillColor": None, "fillStyle": None, "strokeColor": None, "strokeStyle": None,
        "strokeWidth": None, "startX": a[0], "startY": a[1], "endX": b[0], "endY": b[1],
        "lineGroup": wid, "yAxisDirection": "up"})); tick[0] += 1
    new_lines.append(rec({"type": "ATTR", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "x": None, "y": None, "rotation": None, "color": None, "fontFamily": None,
        "fontSize": None, "fontWeight": None, "italic": None, "underline": None,
        "align": None, "value": "[]", "keyVisible": None, "valueVisible": None,
        "key": "Relevance", "fillColor": None, "parentId": wid})); tick[0] += 1
    vert = abs(a[0] - b[0]) < 0.01
    new_lines.append(rec({"type": "ATTR", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "x": (a[0] + b[0]) / 2, "y": (a[1] + b[1]) / 2, "rotation": 90 if vert else 0,
        "color": None, "fontFamily": None, "fontSize": None, "fontWeight": None,
        "italic": None, "underline": None, "align": None, "value": net,
        "keyVisible": False, "valueVisible": True, "key": "NET",
        "fillColor": None, "parentId": wid})); tick[0] += 1

STUB = 40
wired = 0
for ref, cid in by_ref.items():
    pts = anchors(cid)
    if not pts:
        continue
    cx = sum(a[1] for a in pts) / len(pts)
    cy = sum(a[2] for a in pts) / len(pts)
    for p, ax, ay in pts:
        net = pin_net.get((ref, p["num"]))
        if not net:
            continue
        dx, dy = ax - cx, ay - cy
        if abs(dx) >= abs(dy):
            ux, uy = (1 if dx >= 0 else -1), 0
        else:
            ux, uy = 0, (1 if dy >= 0 else -1)
        add_wire((ax, ay), (ax + ux * STUB, ay + uy * STUB), net)
        wired += 1

out = [l for i, l in enumerate(lines) if i not in remove]
while out and not out[-1].strip():
    out.pop()
out.extend(new_lines)
open(P, "w", encoding="utf-8").write("\n".join(out))
print(f"pins with net: {len(pin_net)}, stubs: {wired}, removed lines: {len(remove)}")
