#!/usr/bin/env python3
"""Repair pass 2: use the real DFR connectors, drop the generic ones, clear shorts.

1. delete generic J1/J2 + every wire touching their pins
2. move J3 (DFR display) / J4 (DFR touch) to the right-hand column
3. move decoupling caps C1-C4 out of the level-shifter wiring corridor
4. (re)build stub + NET-attr wires for J3, J4 and the four caps
"""
import json, os, sys, shutil, collections

P = sys.argv[1] if len(sys.argv) > 1 else \
    "RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar/sch/SCH/P1.esch2"

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
shutil.copyfile(P, P + ".bak2")

start = None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD" and b.get("docType") == "SCH_PAGE":
        start = i
page_idx = [i for i in range(start + 1, len(lines))]

docs, cur = [], None
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
    pa = collections.defaultdict(dict)
    raw = []
    for i, h, b in d["items"]:
        if h and h.get("type") == "PIN":
            raw.append((h["id"], b))
        elif h and h.get("type") == "ATTR":
            pa[b.get("parentId")][b.get("key")] = b.get("value")
    sym_pins[d["uuid"]] = [dict(num=str(pa[p].get("Pin Number")), name=str(pa[p].get("Pin Name")),
                                x=b.get("x", 0), y=b.get("y", 0), ln=b.get("length", 10),
                                rot=b.get("rotation", 0)) for p, b in raw]

comps, attrs, wline, wnet, wireline = {}, collections.defaultdict(dict), {}, {}, {}
max_ticket, max_z = 0, 0
for i in page_idx:
    h, b = parse(lines[i])
    if not h:
        continue
    max_ticket = max(max_ticket, h.get("ticket") or 0)
    t = h.get("type")
    if t == "COMPONENT":
        comps[h["id"]] = (i, b)
    elif t == "ATTR":
        attrs[b.get("parentId")][b.get("key")] = b.get("value")
    elif t == "WIRE":
        wline[h["id"]] = i
        max_z = max(max_z, b.get("zIndex") or 0)
    elif t == "LINE" and b.get("lineGroup"):
        wireline.setdefault(b["lineGroup"], []).append((i, b))
for i in page_idx:
    h, b = parse(lines[i])
    if h and h.get("type") == "ATTR" and b.get("key") == "NET":
        wnet[b.get("parentId")] = b.get("value")

def ref_of(cid):
    return attrs.get(cid, {}).get("Designator")

by_ref = {}
for cid in comps:
    r = ref_of(cid)
    if r:
        by_ref[r] = cid

def tips(cid):
    i, c = comps[cid]
    a = attrs.get(cid, {})
    out = []
    for p in sym_pins.get(a.get("Symbol"), []):
        vx, vy = {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}.get(int(p["rot"]) % 360, (-1, 0))
        def place(dx, dy):
            rot = int(c.get("rotation", 0)) % 360
            base = [(c["x"] + dx, c["y"] + dy), (c["x"] - dy, c["y"] + dx),
                    (c["x"] - dx, c["y"] - dy), (c["x"] + dy, c["y"] - dx)]
            return base[rot // 90]
        out.append(dict(num=p["num"], name=p["name"],
                        anchor=place(p["x"], p["y"]),
                        far=place(p["x"] + vx * p["ln"], p["y"] + vy * p["ln"])))
    return out

remove = set()

def kill_wires_touching(points):
    pts = {(round(x, 2), round(y, 2)) for x, y in points}
    dead = set()
    for wid, segs in wireline.items():
        for i, b in segs:
            for p in ((b.get("startX"), b.get("startY")), (b.get("endX"), b.get("endY"))):
                if (round(p[0], 2), round(p[1], 2)) in pts:
                    dead.add(wid)
    for wid in dead:
        remove.add(wline[wid])
        for i, b in wireline[wid]:
            remove.add(i)
        for i in page_idx:
            h, b = parse(lines[i])
            if h and h.get("type") == "ATTR" and b.get("parentId") == wid:
                remove.add(i)
    return len(dead)

# 1) generic connectors out
for ref in ("J1", "J2"):
    cid = by_ref.get(ref)
    if not cid:
        continue
    n = kill_wires_touching([p["anchor"] for p in tips(cid)] + [p["far"] for p in tips(cid)])
    remove.add(comps[cid][0])
    for i in page_idx:
        h, b = parse(lines[i])
        if h and h.get("type") == "ATTR" and b.get("parentId") == cid:
            remove.add(i)
    print(f"removed {ref} and {n} wires")

# 2) move real connectors / caps
MOVES = {"J3": (900, 250), "J4": (900, 545),
         "C1": (900, 770), "C2": (940, 770), "C3": (980, 770), "C4": (1020, 770)}
for ref, (x, y) in MOVES.items():
    cid = by_ref.get(ref)
    if not cid:
        print("!! missing", ref); continue
    i, c = comps[cid]
    c["x"], c["y"] = x, y
    h, _ = parse(lines[i])
    lines[i] = rec(h, c)

# 3) caps: drop old stubs then rebuild
CAP_RAIL = {"C1": "3V3", "C2": "1V2", "C3": "1V8", "C4": "3V3"}
for ref, rail in CAP_RAIL.items():
    cid = by_ref.get(ref)
    if not cid:
        continue
    kill_wires_touching([p["far"] for p in tips(cid)] + [p["anchor"] for p in tips(cid)])

# 4) new stubs
new_lines = []
tick = [max_ticket + 1]
zz = [max_z + 1]

def add_wire(a, b, net):
    wid = os.urandom(8).hex()
    new_lines.append(rec({"type": "WIRE", "ticket": tick[0], "id": wid}, {"zIndex": zz[0]}))
    tick[0] += 1; zz[0] += 1
    new_lines.append(rec({"type": "LINE", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "fillColor": None, "fillStyle": None, "strokeColor": None, "strokeStyle": None,
        "strokeWidth": None, "startX": a[0], "startY": a[1], "endX": b[0], "endY": b[1],
        "lineGroup": wid, "yAxisDirection": "up"}))
    tick[0] += 1
    new_lines.append(rec({"type": "ATTR", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "x": None, "y": None, "rotation": None, "color": None, "fontFamily": None,
        "fontSize": None, "fontWeight": None, "italic": None, "underline": None,
        "align": None, "value": "[]", "keyVisible": None, "valueVisible": None,
        "key": "Relevance", "fillColor": None, "parentId": wid}))
    tick[0] += 1
    vert = a[0] == b[0]
    new_lines.append(rec({"type": "ATTR", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "x": (a[0] + b[0]) / 2, "y": (a[1] + b[1]) / 2, "rotation": 90 if vert else 0,
        "color": None, "fontFamily": None, "fontSize": None, "fontWeight": None,
        "italic": None, "underline": None, "align": None, "value": net,
        "keyVisible": False, "valueVisible": True, "key": "NET",
        "fillColor": None, "parentId": wid}))
    tick[0] += 1

NETS_J3 = {"GND": "GND", "MIPI_CLK_P": "DSI_CLKP", "MIPI_CLK_N": "DSI_CLKN",
           "MIPI_DATA_P": "DSI_D0P", "MIPI_DATA_N": "DSI_D0N",
           "DFR_DISP_TE": "D_TE_18", "DFR_DISP_SYNC": "D_SYNC_18",
           "DFR_DISP_INT": "D_INT_18", "DISP_RESET_L": "D_RST_18",
           "PP1V8": "1V8", "PP3V3": "3V3",
           "DFRDRV_I2C_SCL": "D_I2C_SCL", "DFRDRV_I2C_SDA": "D_I2C_SDA"}
NETS_J4 = {"PANEL_DETECT": "TS_DETECT", "LID": "TS_LID", "DISP_VSYNC": "TS_VSYNC",
           "GPIO2": "TS_GPIO2", "GND": "GND", "SPI_MISO_R": "TS_SPI_MISO",
           "SPI_CS_L": "TS_SPI_CS", "SPI_CLK_R": "TS_SPI_CLK", "SPI_MOSI_R": "TS_SPI_MOSI",
           "INT_L": "TS_INT", "ROM_I2C_SCL": "TS_I2C_SCL", "ROM_I2C_SDA": "TS_I2C_SDA",
           "CLKIN_RST_L": "TS_CLK_RST", "RESET_L": "TS_RST", "ROM_WC": "TS_ROM_WC",
           "PP1V8": "1V8", "PP5V": "5V"}

for ref, table in (("J3", NETS_J3), ("J4", NETS_J4)):
    cid = by_ref.get(ref)
    if not cid:
        continue
    n = 0
    for p in tips(cid):
        net = table.get(p["name"])
        if not net:
            print("  !! no net", ref, p["num"], p["name"]); continue
        ax, ay = p["anchor"]; fx, fy = p["far"]
        dx = 1 if fx > ax else (-1 if fx < ax else 0)
        dy = 1 if fy > ay else (-1 if fy < ay else 0)
        add_wire((fx, fy), (fx + dx * 40, fy + dy * 40), net)
        n += 1
    print(ref, "pins wired:", n)

for ref, rail in CAP_RAIL.items():
    cid = by_ref.get(ref)
    if not cid:
        continue
    ps = tips(cid)
    top = max(ps, key=lambda p: p["far"][1])
    bot = min(ps, key=lambda p: p["far"][1])
    add_wire(top["far"], (top["far"][0], top["far"][1] + 25), rail)
    add_wire(bot["far"], (bot["far"][0], bot["far"][1] - 25), "GND")

out = [l for i, l in enumerate(lines) if i not in remove]
while out and not out[-1].strip():
    out.pop()
out.extend(new_lines)
open(P, "w", encoding="utf-8").write("\n".join(out))
print("removed", len(remove), "lines, added", len(new_lines))
