#!/usr/bin/env python3
"""PCB quality gate for the TouchBar carrier board.

Runs through the EasyEDA bridge (/execute) and reports the four things asked for:

  1. 走線角度     — every segment must be 0/45/90 degrees, and no 90-degree CORNER
                    between two connected segments (45-degree chamfer required)
  2. 四層使用     — how much routing sits on each copper layer, and whether the
                    inner layers carry planes rather than random signal
  3. 線寬分配     — width per net class (power nets must be wider than signals)
  4. DRC          — clearance / connection / footprint summary

Usage:
    python3 tools/check_pcb_quality.py            # report only
    python3 tools/check_pcb_quality.py --json out.json
"""
import json
import sys
import urllib.request
import collections

BRIDGE = "http://localhost:49620/execute"
PCB_UUID = "800ccbd68bb33b6e"

CODE = r"""
await eda.dmt_EditorControl.openDocument('%s');
await new Promise(r=>setTimeout(r, 1200));
const raw = await eda.pcb_PrimitiveLine.getAll();
const tracks = raw.map(l => {
  const g = k => (typeof l['getState_'+k] === 'function' ? l['getState_'+k]() : l[k]);
  return { net: g('Net') || '', layer: g('Layer'), width: g('LineWidth'),
           x1: g('StartX'), y1: g('StartY'), x2: g('EndX'), y2: g('EndY') };
});
const vias = (await eda.pcb_PrimitiveVia.getAll()) || [];
const pours = (await eda.pcb_PrimitivePour.getAll()) || [];
const comps = await eda.pcb_PrimitiveComponent.getAll();
const drc = await eda.pcb_Drc.check(true, false, true);
const drcSummary = drc.map(g => ({ name: g.name, count: (g.list||[]).reduce((a,s)=>a+((s.list||[]).length),0) }));
return JSON.stringify({
  tracks, viaCount: vias.length, pourCount: pours.length,
  pourLayers: pours.map(p => (typeof p.getState_Layer === 'function' ? p.getState_Layer() : null)),
  parts: comps.filter(c => c.getState_Designator && c.getState_Designator()).length,
  drc: drcSummary
});
""" % PCB_UUID

POWER_NETS = {"3V3", "1V8", "1V2", "5V", "GND"}


def fetch():
    req = urllib.request.Request(BRIDGE, data=json.dumps({"code": CODE}).encode(),
                                 headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    if not out.get("success"):
        raise SystemExit(f"bridge call failed: {out}")
    return json.loads(out["result"])


TOL_DEG = 0.5          # sub-degree deviation is coordinate noise, not a design angle


def seg_angle(s):
    dx = abs(s["x2"] - s["x1"])
    dy = abs(s["y2"] - s["y1"])
    if dx < 0.01 and dy < 0.01:
        return None
    ang = abs(__import__("math").degrees(__import__("math").atan2(dy, dx)))
    # orthogonal (0 or 90) and diagonal (45) are all legal
    if abs(ang) <= TOL_DEG or abs(ang - 90.0) <= TOL_DEG:
        return 0.0
    if abs(ang - 45.0) <= TOL_DEG:
        return 45.0
    return round(ang, 2)


def main():
    d = fetch()
    tracks = d["tracks"]
    print(f"parts          : {d['parts']}")
    print(f"tracks / vias  : {len(tracks)} / {d['viaCount']}")
    print(f"pours          : {d['pourCount']} (layers {d['pourLayers']})")

    # ---- 1. angles -------------------------------------------------
    degenerate = [s for s in tracks if seg_angle(s) is None]
    bad_angle = [s for s in tracks if seg_angle(s) not in (None, 0.0, 45.0)]
    print("\n[1] 走線角度")
    print(f"    零長度（退化）線段: {len(degenerate)}")
    print(f"    非 0/45/90 度的線段: {len(bad_angle)}")
    for s in bad_angle[:6]:
        print(f"      {s['net']} L{s['layer']} ({s['x1']:.1f},{s['y1']:.1f})->({s['x2']:.1f},{s['y2']:.1f}) "
              f"angle={seg_angle(s)}")
    # corners: group by endpoint, inspect direction pairs
    ends = collections.defaultdict(list)
    for s in tracks:
        ends[(round(s["x1"], 1), round(s["y1"], 1), s["layer"])].append(s)
        ends[(round(s["x2"], 1), round(s["y2"], 1), s["layer"])].append(s)
    right_corners = []
    for pt, segs in ends.items():
        if len(segs) != 2:
            continue
        dirs = []
        for s in segs:
            if (round(s["x1"], 1), round(s["y1"], 1)) == (pt[0], pt[1]):
                dirs.append((s["x2"] - s["x1"], s["y2"] - s["y1"]))
            else:
                dirs.append((s["x1"] - s["x2"], s["y1"] - s["y2"]))
        if len(dirs) == 2:
            a = abs(__import__("math").degrees(__import__("math").atan2(dirs[0][1], dirs[0][0])))
            b = abs(__import__("math").degrees(__import__("math").atan2(dirs[1][1], dirs[1][0])))
            diff = abs(a - b) % 180
            if 80 <= diff <= 100:
                right_corners.append(pt)
    print(f"    90 度轉角（應為 0）: {len(right_corners)}")
    for p in right_corners[:8]:
        print(f"      at ({p[0]}, {p[1]}) layer {p[2]}")

    # ---- 2. layers -------------------------------------------------
    by_layer = collections.Counter(s["layer"] for s in tracks)
    print("\n[2] 四層使用")
    names = {1: "Top", 2: "Bottom", 15: "Inner1", 16: "Inner2"}
    for lid in sorted(set(list(by_layer) + list(d["pourLayers"] or []))):
        if lid is None:
            continue
        print(f"    {names.get(lid, f'layer {lid}'):<8} tracks={by_layer.get(lid, 0):<5} "
              f"pour={'yes' if d['pourLayers'] and lid in d['pourLayers'] else 'no'}")
    signal_layers = [l for l in by_layer if by_layer[l] > 0]
    print(f"    有走線的層: {len(signal_layers)}")
    if len(signal_layers) < 3:
        inner_with_pour = [l for l in (d["pourLayers"] or []) if l in (15, 16)]
        if inner_with_pour:
            print(f"    兩層訊號 + {len(inner_with_pour)} 層平面 → 4 層分工正確")
        else:
            print("    ! 只用了 2 層走線，內層也沒有平面 → 浪費 4 層成本")

    # ---- 3. widths -------------------------------------------------
    print("\n[3] 線寬分配")
    w = collections.Counter(s["width"] for s in tracks)
    for width, n in sorted(w.items(), key=lambda kv: -kv[1]):
        print(f"    {width} mil ({width*0.0254:.3f} mm): {n} 段")
    thin_power = [s for s in tracks if s["net"] in POWER_NETS and (s["width"] or 0) < 12]
    print(f"    電源網路用細線（<12 mil）的段數: {len(thin_power)}")

    # ---- 4. DRC ----------------------------------------------------
    print("\n[4] DRC")
    for g in d["drc"]:
        print(f"    {g['name']}: {g['count']}")

    if "--json" in sys.argv:
        path = sys.argv[sys.argv.index("--json") + 1]
        json.dump({"bad_angle": len(bad_angle), "right_corners": len(right_corners),
                   "layers": dict(by_layer), "widths": dict(w),
                   "drc": d["drc"], "tracks": len(tracks), "vias": d["viaCount"],
                   "pours": d["pourCount"]}, open(path, "w"), ensure_ascii=False, indent=1)
        print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
