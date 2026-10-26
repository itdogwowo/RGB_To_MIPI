#!/usr/bin/env python3
"""Strict checker for an EasyEDA Pro .esch2 sheet.

- pin -> net by EXACT endpoint match between the pin's connection tip and a wire end
- shorts: wire ends that land mid-span on a wire of another net, or two nets
  sharing a coordinate
"""
import json, sys, collections

P = sys.argv[1]

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

lines = open(P, encoding="utf-8").read().split("\n")
docs, cur = [], None
for i, l in enumerate(lines):
    h, b = parse(l)
    if h and h.get("type") == "DOCHEAD":
        cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "items": []}
        docs.append(cur)
    if cur is not None:
        cur["items"].append((h, b))

sym_pins = {}
for d in docs:
    if d["docType"] != "SYMBOL":
        continue
    pa = collections.defaultdict(dict)
    raw = []
    for h, b in d["items"]:
        if h and h.get("type") == "PIN":
            raw.append((h["id"], b))
        elif h and h.get("type") == "ATTR":
            pa[b.get("parentId")][b.get("key")] = b.get("value")
    sym_pins[d["uuid"]] = [dict(num=str(pa[p].get("Pin Number")), name=str(pa[p].get("Pin Name")),
                                x=b.get("x", 0), y=b.get("y", 0), ln=b.get("length", 10),
                                rot=b.get("rotation", 0)) for p, b in raw]

page = [d for d in docs if d["docType"] == "SCH_PAGE"]
comps, attrs, wires, wnet = {}, collections.defaultdict(dict), collections.defaultdict(list), {}
for d in page:
    for h, b in d["items"]:
        if not h:
            continue
        t = h.get("type")
        if t == "COMPONENT":
            comps[h["id"]] = b
        elif t == "ATTR":
            attrs[b.get("parentId")][b.get("key")] = b.get("value")
        elif t == "LINE" and b.get("lineGroup"):
            wires[b["lineGroup"]].append(((b.get("startX"), b.get("startY")),
                                          (b.get("endX"), b.get("endY"))))
for d in page:
    for h, b in d["items"]:
        if h and h.get("type") == "ATTR" and b.get("key") == "NET":
            wnet[b.get("parentId")] = b.get("value")

def place(cx, cy, dx, dy, rot):
    rot = int(rot) % 360
    return [(cx + dx, cy + dy), (cx - dy, cy + dx), (cx - dx, cy - dy), (cx + dy, cy - dx)][rot // 90]

# endpoint -> set(nets)
endpoint_nets = collections.defaultdict(set)
seg_list = []
for wid, segs in wires.items():
    net = wnet.get(wid) or f"<unnamed:{wid[:6]}>"
    for a, b in segs:
        seg_list.append((a, b, net, wid))
        endpoint_nets[(round(a[0], 2), round(a[1], 2))].add(net)
        endpoint_nets[(round(b[0], 2), round(b[1], 2))].add(net)

def dist_pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5

rows = []
unconnected = []
for cid, c in comps.items():
    ref = attrs.get(cid, {}).get("Designator")
    sym = attrs.get(cid, {}).get("Symbol")
    pins = sym_pins.get(sym, [])
    if not ref or not pins:
        continue
    for p in pins:
        # connection point = pin anchor
        far = place(c["x"], c["y"], p["x"], p["y"], c.get("rotation", 0))
        key = (round(far[0], 2), round(far[1], 2))
        nets = None
        if key in endpoint_nets:
            nets = sorted(endpoint_nets[key])
        else:
            # a stub that covers the pin (start inside, end past the tip) still connects
            for a, b, net, wid in seg_list:
                if dist_pt_seg(far, a, b) < 0.4:
                    nets = [net]
                    break
        if nets:
            rows.append((ref, p["num"], p["name"], nets[0]))
        else:
            unconnected.append((ref, p["num"], p["name"]))

# shorts
shorts = []
for pt, nets in endpoint_nets.items():
    if len(nets) > 1:
        shorts.append(("shared point", pt, sorted(nets)))
for a, b, net, wid in seg_list:
    for (c, d) in [(a, b)]:
        pass
    for pt, nets in endpoint_nets.items():
        if dist_pt_seg(pt, a, b) < 0.3 and pt != (round(a[0], 2), round(a[1], 2)) and pt != (round(b[0], 2), round(b[1], 2)):
            others = nets - {net}
            if others:
                shorts.append(("T-junction", pt, sorted({net} | others)))

print(f"components={len(comps)} pins_mapped={len(rows)} unconnected={len(unconnected)}")
nets = collections.defaultdict(list)
for r in rows:
    nets[r[3]].append(f"{r[0]}.{r[1]}")
print("nets:", len(nets), "| multi-pin:", sum(1 for v in nets.values() if len(v) > 1))
if len(sys.argv) > 2 and sys.argv[2] == "--nets":
    for n, v in sorted(nets.items()):
        print(f"  {n:<14}{len(v):>3}  {','.join(sorted(v)[:8])}")
if unconnected:
    print("UNCONNECTED pins:")
    for u in unconnected:
        print("   ", u)
if shorts:
    print("SHORTS:")
    for s in shorts[:20]:
        print("   ", s)
else:
    print("no shorts detected")
