#!/usr/bin/env python3
"""Rewire the schematic to the real DFR connector symbols (J3 display / J4 touch).

- removes the generic J1/J2 connectors and the stub wires attached to them
- adds stub + NET-attr wires to every pin of J3 / J4, using the existing net names
Records are appended inside the SCH_PAGE document (not after it).
"""
import json, os, sys, collections, shutil

P = sys.argv[1] if len(sys.argv) > 1 else \
    "RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar/sch/SCH/P1.esch2"
BAK = P + ".bak"

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

lines = open(P, encoding="utf-8").read().split("\n")
shutil.copyfile(P, BAK)
print("backup:", BAK)

# ---- locate page doc
start = None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD" and b.get("docType") == "SCH_PAGE":
        start = i
print("page doc starts at line", start, "of", len(lines))

page = [(i, parse(l)) for i, l in enumerate(lines) if i > start]
page = [(i, h, b) for i, (h, b) in page if h]

# ---- documents (scoped per doc: pin ids are only unique inside a document)
docs = []
cur = None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD":
        cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "items": []}
        docs.append(cur)
    if cur is not None:
        cur["items"].append((i, h, b))

sym_pins = {}
for d in docs:
    if d["docType"] != "SYMBOL":
        continue
    pattr = collections.defaultdict(dict)
    raw = []
    for i, h, b in d["items"]:
        if h.get("type") == "PIN":
            raw.append((h["id"], b))
        elif h.get("type") == "ATTR":
            pattr[b.get("parentId")][b.get("key")] = b.get("value")
    sym_pins[d["uuid"]] = [
        dict(num=str(pattr[pid].get("Pin Number")), name=str(pattr[pid].get("Pin Name")),
             x=b.get("x", 0), y=b.get("y", 0), ln=b.get("length", 10), rot=b.get("rotation", 0))
        for pid, b in raw]

comps, attrs, wires, wire_net, lines_of = {}, collections.defaultdict(dict), {}, {}, collections.defaultdict(list)
max_ticket = 0
max_z = 0
for i, h, b in page:
    max_ticket = max(max_ticket, h.get("ticket") or 0)
    t = h.get("type")
    if t == "COMPONENT":
        comps[h["id"]] = (i, b)
    elif t == "ATTR":
        attrs[b.get("parentId")][b.get("key")] = b.get("value")
    elif t == "WIRE":
        wires[h["id"]] = (i, b)
        max_z = max(max_z, b.get("zIndex") or 0)
    elif t == "LINE" and b.get("lineGroup"):
        lines_of[b["lineGroup"]].append((i, h["id"], b))
for i, h, b in page:
    if h.get("type") == "ATTR" and b.get("key") == "NET" and b.get("parentId") in wires:
        wire_net[b["parentId"]] = b.get("value")

# ---- pin tips
def place(cx, cy, dx, dy, rot):
    rot = int(rot) % 360
    return [(cx + dx, cy + dy), (cx - dy, cy + dx), (cx - dx, cy - dy), (cx + dy, cy - dx)][rot // 90]

def tips_for(comp_id):
    i, c = comps[comp_id]
    a = attrs.get(comp_id, {})
    sym = a.get("Symbol")
    out = []
    for pb in sym_pins.get(sym, []):
        num = pb["num"]
        name = pb["name"]
        x, y = pb["x"], pb["y"]
        ln = pb["ln"]
        rot = pb["rot"]
        vx, vy = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}.get(int(rot) % 360, (-1, 0))
        anchor = place(c["x"], c["y"], x, y, c.get("rotation", 0))
        far = place(c["x"], c["y"], x + vx * ln, y + vy * ln, c.get("rotation", 0))
        out.append(dict(num=num, name=name, anchor=anchor, far=far))
    return out

def by_ref(ref):
    for cid, (i, c) in comps.items():
        if attrs.get(cid, {}).get("Designator") == ref:
            return cid
    return None

j1, j2 = by_ref("J1"), by_ref("J2")
j3, j4 = by_ref("J3"), by_ref("J4")
print("J1", j1, "J2", j2, "J3", j3, "J4", j4)

remove = set()          # line indices to drop
if j1 and j2:
    targets = set()
    for cid in (j1, j2):
        for p in tips_for(cid):
            targets.add((round(p["anchor"][0], 2), round(p["anchor"][1], 2)))
            targets.add((round(p["far"][0], 2), round(p["far"][1], 2)))
    dead_wires = set()
    for wid, (i, b) in wires.items():
        for (li, lid, lb) in lines_of.get(wid, []):
            for pt in ((lb.get("startX"), lb.get("startY")), (lb.get("endX"), lb.get("endY"))):
                if (round(pt[0], 2), round(pt[1], 2)) in targets:
                    dead_wires.add(wid)
    for wid in dead_wires:
        remove.add(wires[wid][0])
        for (li, lid, lb) in lines_of.get(wid, []):
            remove.add(li)
        for i, h, b in page:
            if h.get("type") == "ATTR" and b.get("parentId") == wid:
                remove.add(i)
    for cid in (j1, j2):
        remove.add(comps[cid][0])
        for i, h, b in page:
            if h.get("type") == "ATTR" and b.get("parentId") == cid:
                remove.add(i)
    print("removing", len(dead_wires), "wires and components J1/J2")

# ---- new wiring for J3 / J4
NETS_J3 = {
    "GND": "GND", "MIPI_CLK_P": "DSI_CLKP", "MIPI_CLK_N": "DSI_CLKN",
    "MIPI_DATA_P": "DSI_D0P", "MIPI_DATA_N": "DSI_D0N",
    "DFR_DISP_TE": "D_TE_18", "DFR_DISP_SYNC": "D_SYNC_18",
    "DFR_DISP_INT": "D_INT_18", "DISP_RESET_L": "D_RST_18",
    "PP1V8": "1V8", "PP3V3": "3V3",
    "DFRDRV_I2C_SCL": "D_I2C_SCL", "DFRDRV_I2C_SDA": "D_I2C_SDA",
}
NETS_J4 = {
    "PANEL_DETECT": "TS_DETECT", "LID": "TS_LID", "DISP_VSYNC": "TS_VSYNC",
    "GPIO2": "TS_GPIO2", "GND": "GND",
    "SPI_MISO_R": "TS_SPI_MISO", "SPI_CS_L": "TS_SPI_CS",
    "SPI_CLK_R": "TS_SPI_CLK", "SPI_MOSI_R": "TS_SPI_MOSI",
    "INT_L": "TS_INT", "ROM_I2C_SCL": "TS_I2C_SCL", "ROM_I2C_SDA": "TS_I2C_SDA",
    "CLKIN_RST_L": "TS_CLK_RST", "RESET_L": "TS_RST", "ROM_WC": "TS_ROM_WC",
    "PP1V8": "1V8", "PP5V": "5V",
}

new_lines = []
ticket = [max_ticket + 1]
z = [max_z + 1]

def nid():
    return os.urandom(8).hex()

def add_wire(p_from, p_to, net):
    wid = nid()
    zz = z[0]; z[0] += 1
    new_lines.append(rec({"type": "WIRE", "ticket": ticket[0], "id": wid}, {"zIndex": zz}))
    ticket[0] += 1
    new_lines.append(rec({"type": "LINE", "ticket": ticket[0], "id": nid()}, {
        "fillColor": None, "fillStyle": None, "strokeColor": None, "strokeStyle": None,
        "strokeWidth": None,
        "startX": p_from[0], "startY": p_from[1], "endX": p_to[0], "endY": p_to[1],
        "lineGroup": wid, "yAxisDirection": "up"}))
    ticket[0] += 1
    new_lines.append(rec({"type": "ATTR", "ticket": ticket[0], "id": nid()}, {
        "x": None, "y": None, "rotation": None, "color": None, "fontFamily": None,
        "fontSize": None, "fontWeight": None, "italic": None, "underline": None,
        "align": None, "value": "[]", "keyVisible": None, "valueVisible": None,
        "key": "Relevance", "fillColor": None, "parentId": wid}))
    ticket[0] += 1
    mx = (p_from[0] + p_to[0]) / 2
    my = (p_from[1] + p_to[1]) / 2
    vert = 1 if p_from[0] == p_to[0] else 0
    new_lines.append(rec({"type": "ATTR", "ticket": ticket[0], "id": nid()}, {
        "x": mx, "y": my, "rotation": 90 if vert else 0, "color": None, "fontFamily": None,
        "fontSize": None, "fontWeight": None, "italic": None, "underline": None,
        "align": None, "value": net, "keyVisible": False, "valueVisible": True,
        "key": "NET", "fillColor": None, "parentId": wid}))
    ticket[0] += 1

for cid, table, label in ((j3, NETS_J3, "J3"), (j4, NETS_J4, "J4")):
    if not cid:
        continue
    n = 0
    for p in tips_for(cid):
        net = table.get(p["name"])
        if not net:
            print("  !! no net for", label, p["num"], p["name"])
            continue
        # outward stub: use the far tip, 40 units in the direction of the pin
        ax, ay = p["anchor"]; fx, fy = p["far"]
        dx = 1 if fx > ax else (-1 if fx < ax else 0)
        dy = 1 if fy > ay else (-1 if fy < ay else 0)
        add_wire((fx, fy), (fx + dx * 40, fy + dy * 40), net)
        n += 1
    print(label, "wired pins:", n)

# ---- write back
out = []
for i, l in enumerate(lines):
    if i in remove:
        continue
    out.append(l)
# append new records at EOF (page doc is the last document)
while out and not out[-1].strip():
    out.pop()
out.extend(new_lines)
open(P, "w", encoding="utf-8").write("\n".join(out))
print("removed", len(remove), "lines; appended", len(new_lines), "records")
