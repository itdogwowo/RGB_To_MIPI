"""Extract connectivity from an EasyEDA Pro .esch2 schematic page.

Wires are WIRE records whose geometry lives in LINE records sharing `lineGroup`.
Pins are PIN records inside SYMBOL documents; their absolute position is obtained by
placing the symbol at the COMPONENT position.

Usage:
  python3 esch_netlist.py <P1.esch2> [--part J1] [--csv out.csv]
"""
import json, sys, collections, csv

TOL = 0.75          # schematic unit (~0.01 inch) tolerance for connectivity

def parse_records(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            head, sep, body = line.partition("||")
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

def split_docs(recs):
    docs, cur = [], None
    for h, b in recs:
        if h.get("type") == "DOCHEAD":
            cur = {"docType": b.get("docType"), "uuid": b.get("uuid"), "items": []}
            docs.append(cur)
        if cur is not None:
            cur["items"].append((h, b))
    return docs

def symbol_pins(doc):
    pins, attrs = {}, collections.defaultdict(dict)
    for h, b in doc["items"]:
        t = h.get("type")
        if t == "PIN":
            pins[h["id"]] = dict(number="", name="", x=b.get("x", 0), y=b.get("y", 0),
                                 length=b.get("length", 0), rot=b.get("rotation", 0))
        elif t == "ATTR":
            attrs[b.get("parentId")][b.get("key")] = b.get("value")
    for pid, p in pins.items():
        p["number"] = str(attrs[pid].get("Pin Number", "") or "")
        p["name"] = str(attrs[pid].get("Pin Name", "") or "")
    return pins

def rot_vec(rot):
    rot = int(rot) % 360
    return {0: (-1, 0), 90: (0, 1), 180: (1, 0), 270: (0, -1)}.get(rot, (-1, 0))

def place(cx, cy, dx, dy, rot, mirror):
    rot = int(rot) % 360
    if mirror:
        dx = -dx
    if rot == 0:
        rx, ry = dx, dy
    elif rot == 90:
        rx, ry = -dy, dx
    elif rot == 180:
        rx, ry = -dx, -dy
    else:
        rx, ry = dy, -dx
    return (cx + rx, cy + ry)

class UF:
    def __init__(self):
        self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

def dist_pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def key(pt):
    if len(pt) == 2 and isinstance(pt[0], str):
        return pt
    return (round(pt[0], 2), round(pt[1], 2))

def extract(path):
    recs = parse_records(path)
    docs = split_docs(recs)
    sym_by_uuid = {}
    for d in docs:
        if d["docType"] == "SYMBOL":
            sym_by_uuid[d["uuid"]] = symbol_pins(d)
    dev_name = {}
    for d in docs:
        if d["docType"] == "DEVICE":
            title = next((b.get("title") for h, b in d["items"] if h.get("type") == "META"), "")
            dev_name[d["uuid"]] = title

    pages = [d for d in docs if d["docType"] == "SCH_PAGE"]
    out = []
    for page in pages:
        title = next((b.get("title") for h, b in page["items"] if h.get("type") == "META"), "")
        items = page["items"]
        wire_lines = collections.defaultdict(list)
        for h, b in items:
            if h.get("type") == "LINE" and b.get("lineGroup"):
                wire_lines[b["lineGroup"]].append(
                    ((b.get("startX", 0), b.get("startY", 0)),
                     (b.get("endX", 0), b.get("endY", 0))))
        comps, attrs = {}, collections.defaultdict(dict)
        wire_net = {}
        for h, b in items:
            if h.get("type") == "COMPONENT":
                comps[h["id"]] = b
            elif h.get("type") == "ATTR":
                attrs[b.get("parentId")][b.get("key")] = b.get("value")
                if b.get("key") == "NET" and b.get("value"):
                    wire_net[b.get("parentId")] = b["value"]

        uf = UF()
        all_segs = []
        for wid, segs in wire_lines.items():
            for a, b in segs:
                uf.union(key(a), key(b))
            for i in range(len(segs)):
                for j in range(i + 1, len(segs)):
                    for p in segs[i]:
                        for q in segs[j]:
                            if abs(p[0] - q[0]) < TOL and abs(p[1] - q[1]) < TOL:
                                uf.union(key(p), key(q))
            all_segs.extend(segs)

        # global T-junction pass: a wire endpoint touching another wire's middle
        for i in range(len(all_segs)):
            for j in range(len(all_segs)):
                if i == j:
                    continue
                a, b = all_segs[i]
                for pt in (a, b):
                    if dist_pt_seg(pt, all_segs[j][0], all_segs[j][1]) < TOL:
                        uf.union(key(pt), key(all_segs[j][0]))

        def attach(pt):
            """Union pt with any wire it touches (including mid-span)."""
            k = key(pt)
            if k in uf.p:
                return uf.find(k)
            for a, b in all_segs:
                if dist_pt_seg(pt, a, b) < TOL:
                    uf.union(k, key(a))
                    return uf.find(k)
            return None
        pin_rows = []
        for cid, c in comps.items():
            a = attrs[cid]
            desig = a.get("Designator", "")
            sym_uuid = a.get("Symbol", "")
            pins = sym_by_uuid.get(sym_uuid)
            if not pins:
                continue
            cx, cy = c.get("x", 0), c.get("y", 0)
            rot = c.get("rotation", 0)
            mirror = bool(c.get("isMirror"))
            for pid, p in pins.items():
                vx, vy = rot_vec(p["rot"])
                far_local = (p["x"] + vx * p["length"], p["y"] + vy * p["length"])
                pts = [place(cx, cy, p["x"], p["y"], rot, mirror),
                       place(cx, cy, far_local[0], far_local[1], rot, mirror)]
                node = None
                for pt in (pts[1], pts[0]):      # far tip first, anchor second
                    n2 = attach(pt)
                    if n2 is not None:
                        node = n2
                        break
                pin_rows.append(dict(desig=desig, number=p["number"], name=p["name"],
                                     pts=pts, node=node,
                                     device=dev_name.get(a.get("Device", ""), ""),
                                     value=a.get("Value", "")))
        netname = {}
        for cid, c in comps.items():
            a = attrs[cid]
            nm = a.get("Name", "") or ""
            dev = dev_name.get(a.get("Device", ""), "")
            if dev.startswith("Netport") or dev.startswith("Power") or dev.startswith("Ground"):
                nname = (a.get("Net") or a.get("Value") or nm or "").strip()
                pt = (c.get("x", 0), c.get("y", 0))
                n2 = attach(pt)
                if n2 is not None:
                    uf.union(key(("NET", nname)), n2)
                else:
                    uf.union(key(("NET", nname)), key(("NETPT", id(cid))))
                netname.setdefault(key(("NET", nname)), nname)
        nodes = {uf.find(n) for n in uf.p}
        name_of = {n: None for n in nodes}
        # net names carried by WIRE records (NET attribute)
        for wid, segs in wire_lines.items():
            nm = wire_net.get(wid)
            if not nm:
                continue
            for a, b in segs:
                for pt in (a, b):
                    k = key(pt)
                    if k in uf.p:
                        name_of[uf.find(k)] = nm
        for k, nname in netname.items():
            name_of[uf.find(k)] = nname
        # give unnamed nets a stable label so connectivity is still visible
        unnamed = [n for n in nodes if not name_of[n]]
        for i, n in enumerate(sorted(unnamed, key=lambda t: (t[0][0] if isinstance(t[0], tuple) else 0))):
            name_of[n] = f"N${i + 1}"
        for row in pin_rows:
            net = ""
            if row["node"] is not None:
                net = name_of.get(uf.find(row["node"]), "") or ""
            out.append(dict(page=title, desig=row["desig"], number=row["number"],
                            name=row["name"], net=net, device=row["device"],
                            value=str(row["value"])[:40]))
    return out

if __name__ == "__main__":
    path = sys.argv[1]
    rows = extract(path)
    part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else None
    rows.sort(key=lambda r: (r["desig"], r["number"]))
    sel = [r for r in rows if part is None or r["desig"] == part]
    if "--csv" in sys.argv:
        out = sys.argv[sys.argv.index("--csv") + 1]
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["page", "desig", "number", "name", "net", "device", "value"])
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} pin rows to {out}")
    if part:
        for r in sel:
            print(f"{r['desig']:<7}{r['number']:>4}  {r['name'][:20]:<21}{r['net'][:30]}")
