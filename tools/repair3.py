#!/usr/bin/env python3
"""repair3: rewire the sheet on the CURRENT file using in-file geometry.

- keeps every component the user placed (real SSD2828, real DFR connectors,
  real X6511WV-27H ESP headers J1/J2)
- removes the generated J6/J7 header symbols
- drops every existing wire and redraws stubs at the real pin anchors
- adds a pin -> GPIO -> net table next to each ESP header
"""
import json, os, sys, collections, shutil

P = sys.argv[1]
lines = open(P, encoding="utf-8").read().split("\n")
shutil.copyfile(P, P + ".bak3")

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

# ---- docs
docs, cur = [], None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD":
        cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "idx": i, "items": []}
        docs.append(cur)
    if cur is not None:
        cur["items"].append((i, h, b))
page = [d for d in docs if d["docType"] == "SCH_PAGE"][0]
p_start, p_end = page["idx"], (docs[docs.index(page) + 1]["idx"] if docs.index(page) + 1 < len(docs) else len(lines))

sym_pins = {}
sym_line_of = {}
for d in docs:
    if d["docType"] != "SYMBOL":
        continue
    pa = collections.defaultdict(dict)
    raw = []
    for i, h, b in d["items"]:
        if h and h.get("type") == "PIN":
            raw.append((h["id"], i, b))
        elif h and h.get("type") == "ATTR":
            pa[b.get("parentId")][b.get("key")] = b.get("value")
    sym_pins[d["uuid"]] = [dict(num=str(pa[i].get("Pin Number")), name=str(pa[i].get("Pin Name")),
                                x=b.get("x", 0), y=b.get("y", 0), ln=b.get("length", 10),
                                rot=int(b.get("rotation", 0)) % 360) for i, _, b in raw]

# ---- page objects
comps, attrs, wires, wnet = {}, collections.defaultdict(dict), {}, {}
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
        wires[h["id"]] = (i, b)
for i in range(p_start + 1, p_end):
    h, b = parse(lines[i])
    if h and h.get("type") == "ATTR" and b.get("key") == "NET":
        wnet[b.get("parentId")] = b.get("value")

by_ref = {}
for cid in comps:
    r = attrs.get(cid, {}).get("Designator")
    if r:
        by_ref[r] = cid

def anchor(cid, p):
    i, c = comps[cid]
    rot = int(c.get("rotation", 0)) % 360
    dx, dy = p["x"], p["y"]
    return [(c["x"] + dx, c["y"] + dy), (c["x"] - dy, c["y"] + dx),
            (c["x"] - dx, c["y"] - dy), (c["x"] + dy, c["y"] - dx)][rot // 90]

def outward(cid, p):
    i, c = comps[cid]
    rot = int(c.get("rotation", 0)) % 360
    # pin rotation already points away from the body
    vx, vy = {0: (-1, 0), 90: (0, -1), 180: (1, 0), 270: (0, 1)}[p["rot"]]
    return [(vx, vy), (-vy, vx), (-vx, -vy), (vy, -vx)][rot // 90]

# ---- remove: generated headers J6/J7, every wire
remove = set()
for ref in ("J6", "J7"):
    cid = by_ref.get(ref)
    if not cid:
        continue
    for i in range(p_start + 1, p_end):
        h, b = parse(lines[i])
        if not h:
            continue
        if h.get("type") == "ATTR" and b.get("parentId") == cid:
            remove.add(i)
    remove.add(comps[cid][0])
for wid, (i, b) in wires.items():
    remove.add(i)
    for j in range(p_start + 1, p_end):
        h, b = parse(lines[j])
        if h and h.get("type") == "LINE" and b.get("lineGroup") == wid:
            remove.add(j)
        if h and h.get("type") == "ATTR" and b.get("parentId") == wid:
            remove.add(j)

# ---- move the ESP headers to readable spots
MOVES = {"J1": (960, -560, 180), "J2": (960, -240, 180),
         "C5": (600, -100, 90), "C6": (740, -100, 90)}
for ref, (x, y, rot) in MOVES.items():
    cid = by_ref.get(ref)
    if not cid:
        print("!! missing", ref); continue
    i, c = comps[cid]
    c["x"], c["y"] = x, y
    c["rotation"] = rot
    h, _ = parse(lines[i])
    lines[i] = rec(h, c)

# ---- net tables
J1_NETS = {str(i + 1): f"RGB_D{i}" for i in range(21)}
J1_NETS.update({"27": "GND", "22": None, "23": None, "24": None, "25": None, "26": None})
J2_NETS = {"1": "RGB_D21", "2": "RGB_D22", "3": "RGB_D23", "4": "RGB_PCLK", "5": "RGB_DE",
           "6": "RGB_VSYNC", "7": "SPI_SCK", "8": "SPI_MOSI", "11": "SPI_MISO",
           "12": "SPI_CS", "13": "SPI_DC", "15": "SSD_RST", "16": "TE", "17": "T_CS",
           "18": "T_INT", "19": "T_RST", "20": "I2C_SDA", "21": "I2C_SCL", "22": "D_RST",
           "25": "3V3", "27": "5V", "9": "GND", "14": "GND", "26": "GND"}
J1_GPIO = ["IO15", "IO14", "IO13", "IO12", "IO11", "IO10", "IO9", "IO6", "IO5", "IO4",
           "IO3", "IO2", "IO54", "IO53", "IO52", "IO50", "IO49", "IO48", "IO47", "IO46",
           "IO45", "IO44", "IO43", "IO40", "IO41", "IO42", "GND"]
J2_GPIO = ["IO16", "IO17", "IO18", "IO19", "IO20", "IO21", "IO22", "IO23", "GND", "IO39",
           "IO38", "IO37", "IO36", "GND", "IO34", "IO33", "IO32", "IO26", "IO27", "IO28",
           "IO29", "IO30", "IO31", "LDO_VO4", "3V3", "GND", "5V"]

GPIO_OF = {}
for i, g in enumerate(J1_GPIO[:21]):
    GPIO_OF[f"RGB_D{i}"] = g
GPIO_OF.update({"RGB_D21": "IO16", "RGB_D22": "IO17", "RGB_D23": "IO18",
                "RGB_PCLK": "IO19", "RGB_DE": "IO20", "RGB_VSYNC": "IO21",
                "SPI_SCK": "IO22", "SPI_MOSI": "IO23", "SPI_MISO": "IO38",
                "SPI_CS": "IO37", "SPI_DC": "IO36", "SSD_RST": "IO34",
                "TE": "IO33", "T_CS": "IO32", "T_INT": "IO26", "T_RST": "IO27",
                "I2C_SDA": "IO28", "I2C_SCL": "IO29", "D_RST": "IO30"})
RAILS = {"GND", "3V3", "5V", "1V8", "1V2"}

def netname(func):
    if not func:
        return None
    if func in RAILS:
        return func
    g = GPIO_OF.get(func)
    return f"{g}_{func}" if g else func


U1_NETS = {f"DATA{i}": f"RGB_D{i}" for i in range(24)}
U1_NETS.update({"PCLK": "RGB_PCLK", "DEN": "RGB_DE", "VSYNC": "RGB_VSYNC", "HSYNC": "GND",
                "DATAP0": "DSI_D0P", "DATAN0": "DSI_D0N", "CLKP": "DSI_CLKP", "CLKN": "DSI_CLKN",
                "SCK": "SPI_SCK", "SDI": "SPI_MOSI", "SDO": "SPI_MISO", "CSX0": "SPI_CS",
                "SDC": "SPI_DC", "RESET": "SSD_RST", "SHUT": "GND", "PS0": "GND", "PS1": "3V3",
                "TX_CLK_XIN": "XTAL_IN", "TX_CLK_XIO": "XTAL_OUT",
                "MVDD": "1V2", "VDDIO": "3V3", "GND": "GND", "69": "GND"})
J3_NETS = {"GND": "GND", "MIPI_CLK_P": "DSI_CLKP", "MIPI_CLK_N": "DSI_CLKN",
           "MIPI_DATA_P": "DSI_D0P", "MIPI_DATA_N": "DSI_D0N",
           "DFR_DISP_TE": "D_TE_18", "DFR_DISP_SYNC": "D_SYNC_18",
           "DFR_DISP_INT": "D_INT_18", "DISP_RESET_L": "D_RST_18",
           "PP1V8": "1V8", "PP3V3": "3V3",
           "DFRDRV_I2C_SCL": "D_I2C_SCL", "DFRDRV_I2C_SDA": "D_I2C_SDA"}
J4_NETS = {"PANEL_DETECT": "TS_DETECT", "LID": "TS_LID", "DISP_VSYNC": "TS_VSYNC",
           "GPIO2": "TS_GPIO2", "GND": "GND", "SPI_MISO_R": "TS_SPI_MISO",
           "SPI_CS_L": "TS_SPI_CS", "SPI_CLK_R": "TS_SPI_CLK", "SPI_MOSI_R": "TS_SPI_MOSI",
           "INT_L": "TS_INT", "ROM_I2C_SCL": "TS_I2C_SCL", "ROM_I2C_SDA": "TS_I2C_SDA",
           "CLKIN_RST_L": "TS_CLK_RST", "RESET_L": "TS_RST", "ROM_WC": "TS_ROM_WC",
           "PP1V8": "1V8", "PP5V": "5V"}
U4_NETS = {"20": "3V3", "11": "1V8", "10": "GND", "1": "1V8",
           "19": "D_RST", "18": "TE", "2": "D_RST_18", "3": "D_TE_18"}
U5_NETS = {"20": "3V3", "11": "1V8", "10": "GND", "1": "1V8",
           "19": "SPI_SCK", "18": "SPI_MOSI", "17": "SPI_MISO", "16": "T_CS",
           "15": "T_INT", "14": "T_RST", "13": "I2C_SDA", "12": "I2C_SCL",
           "2": "TS_SPI_CLK", "3": "TS_SPI_MOSI", "4": "TS_SPI_MISO", "5": "TS_SPI_CS",
           "6": "TS_INT", "7": "TS_RST", "8": "TS_I2C_SDA", "9": "TS_I2C_SCL"}
CAP_NETS = {"C1": ("3V3", "GND"), "C2": ("1V2", "GND"), "C3": ("1V8", "GND"),
            "C4": ("3V3", "GND"), "C5": ("XTAL_IN", "GND"), "C6": ("XTAL_OUT", "GND")}

new_lines = []
tick = [max((parse(l)[0] or {}).get("ticket", 0) or 0 for l in lines) + 1]
zz = [1]

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
    vert = abs(a[0] - b[0]) < 0.01
    new_lines.append(rec({"type": "ATTR", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "x": (a[0] + b[0]) / 2, "y": (a[1] + b[1]) / 2, "rotation": 90 if vert else 0,
        "color": None, "fontFamily": None, "fontSize": None, "fontWeight": None,
        "italic": None, "underline": None, "align": None, "value": net,
        "keyVisible": False, "valueVisible": True, "key": "NET",
        "fillColor": None, "parentId": wid}))
    tick[0] += 1

def add_text(s, x, y, size=7):
    new_lines.append(rec({"type": "TEXT", "ticket": tick[0], "id": os.urandom(8).hex()}, {
        "partId": "pid8a0e77bacb214e", "groupId": "", "locked": False, "zIndex": zz[0],
        "x": x, "y": y, "rotation": 0, "value": s, "color": None, "fillColor": None,
        "fontFamily": None, "fontSize": size, "strikeout": False, "underline": False,
        "italic": False, "fontWeight": False, "align": "LEFT_MIDDLE",
        "yAxisDirection": "up"}))
    tick[0] += 1; zz[0] += 1

wired = 0
for cid, (i, c) in comps.items():
    ref = attrs.get(cid, {}).get("Designator")
    if not ref or ref in ("J6", "J7"):
        continue
    pins = sym_pins.get(attrs[cid].get("Symbol"), [])
    for p in pins:
        if ref in ("J1", "J2"):
            net = (J1_NETS if ref == "J1" else J2_NETS).get(p["num"])
        elif ref == "U1":
            net = U1_NETS.get(p["name"])
        elif ref == "J3":
            net = J3_NETS.get(p["name"])
        elif ref == "J4":
            net = J4_NETS.get(p["name"])
        elif ref == "U4":
            net = U4_NETS.get(p["num"])
        elif ref == "U5":
            net = U5_NETS.get(p["num"])
        elif ref in ("U2", "U3"):
            net = {"1": "3V3", "2": "GND", "3": "3V3", "5": "1V8" if ref == "U2" else "1V2"}.get(p["num"])
        elif ref == "Y1":
            net = {"1": "XTAL_IN", "2": "XTAL_OUT"}.get(p["num"])
        elif ref in CAP_NETS:
            a, b = CAP_NETS[ref]
            net = a if (pins.index(p) == 0) else b
        else:
            net = None
        if not net:
            continue
        A = anchor(cid, p)
        d = outward(cid, p)
        L = p.get("ln", 10)
        # start a little inside the body, end well past the pin so the wire
        # passes over the connection point whichever end the client uses
        start = (A[0] - d[0] * 6, A[1] - d[1] * 6)
        end = (A[0] + d[0] * (L + 28), A[1] + d[1] * (L + 28))
        add_wire(start, end, netname(net))
        wired += 1

# ---- (no TEXT records: shape unverified, GPIO is carried in the net names)
out = [l for i, l in enumerate(lines) if i not in remove]
while out and not out[-1].strip():
    out.pop()
out.extend(new_lines)
open(P, "w", encoding="utf-8").write("\n".join(out))
print(f"removed {len(remove)} lines, added {len(new_lines)} records, wired {wired} pins")
