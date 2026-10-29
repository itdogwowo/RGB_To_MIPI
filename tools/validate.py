#!/usr/bin/env python3
"""Exact clearance validator for generated PCB geometry.

Works in mil.  Reports every segment whose real distance to a foreign pad or a
foreign trace is below the board rule (6 mil clearance).

  distance(segment, rect)  -> min distance between the segment centreline and the
                              rect boundary (0 if the centreline touches the rect)
  violation                -> dist < trace_half + 6
"""
import json
import math
import sys

CLEAR = 6.0


def seg_rect_dist(x1, y1, x2, y2, rx0, ry0, rx1, ry1):
    """min distance between the segment and the axis-aligned rect"""
    # if either endpoint is inside -> 0
    for (px, py) in ((x1, y1), (x2, y2)):
        if rx0 <= px <= rx1 and ry0 <= py <= ry1:
            return 0.0
    # distance to the 4 edges, clipped
    best = 1e18
    edges = [
        (rx0, ry0, rx1, ry0), (rx1, ry0, rx1, ry1),
        (rx1, ry1, rx0, ry1), (rx0, ry1, rx0, ry0),
    ]
    for (ax, ay, bx, by) in edges:
        d = seg_seg_dist(x1, y1, x2, y2, ax, ay, bx, by)
        if d < best:
            best = d
    return best


def seg_seg_dist(x1, y1, x2, y2, x3, y3, x4, y4):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def on_seg(p, q, r):
        return min(p[0], r[0]) - 1e-9 <= q[0] <= max(p[0], r[0]) + 1e-9 and \
               min(p[1], r[1]) - 1e-9 <= q[1] <= max(p[1], r[1]) + 1e-9

    p1, p2, p3, p4 = (x1, y1), (x2, y2), (x3, y3), (x4, y4)
    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    if abs(d1) < 1e-9 and on_seg(p3, p1, p4):
        return 0.0
    if abs(d2) < 1e-9 and on_seg(p3, p2, p4):
        return 0.0
    if abs(d3) < 1e-9 and on_seg(p1, p3, p2):
        return 0.0
    if abs(d4) < 1e-9 and on_seg(p1, p4, p2):
        return 0.0
    return min(pt_seg(p1, p3, p4), pt_seg(p2, p3, p4), pt_seg(p3, p1, p2), pt_seg(p4, p1, p2))


def pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main():
    pads = json.load(open(sys.argv[1]))["pads"]
    segs = json.load(open(sys.argv[2]))["segs"]
    print(f"tracks {len(segs)}  pads {len(pads)}")

    # pad rects
    rects = []
    for p in pads:
        tht = bool(p.get("hole"))
        rects.append((p["net"], p["x"] - p["w"] / 2, p["y"] - p["h"] / 2,
                      p["x"] + p["w"] / 2, p["y"] + p["h"] / 2,
                      None if tht else p.get("layer")))

    pad_viol = []
    for s in segs:
        half = s["width"] / 2.0
        for (net, rx0, ry0, rx1, ry1, only_layer) in rects:
            if net == s["net"]:
                continue
            # an SMD pad only conflicts with copper on its own layer
            if only_layer is not None and only_layer != s["layer"]:
                continue
            d = seg_rect_dist(s["x1"], s["y1"], s["x2"], s["y2"], rx0, ry0, rx1, ry1)
            if d < half + CLEAR - 1e-6:
                pad_viol.append((s["net"], round(d, 2), round(rx0), round(ry0)))
                break

    # segment vs segment (same layer, different net)
    by_layer = {}
    for s in segs:
        by_layer.setdefault(s["layer"], []).append(s)
    seg_viol = []
    for layer, lst in by_layer.items():
        for i in range(len(lst)):
            a = lst[i]
            for j in range(i + 1, len(lst)):
                b = lst[j]
                if a["net"] == b["net"]:
                    continue
                # quick bbox reject
                if (min(a["x1"], a["x2"]) > max(b["x1"], b["x2"]) + 40 or
                        max(a["x1"], a["x2"]) < min(b["x1"], b["x2"]) - 40 or
                        min(a["y1"], a["y2"]) > max(b["y1"], b["y2"]) + 40 or
                        max(a["y1"], a["y2"]) < min(b["y1"], b["y2"]) - 40):
                    continue
                d = seg_seg_dist(a["x1"], a["y1"], a["x2"], a["y2"],
                                 b["x1"], b["y1"], b["x2"], b["y2"])
                if d < (a["width"] + b["width"]) / 2 + CLEAR - 1e-6:
                    seg_viol.append((a["net"], b["net"], round(d, 2)))

    print(f"\nsegment vs foreign pad : {len(pad_viol)}")
    for v in pad_viol[:12]:
        print("   ", v)
    print(f"segment vs foreign seg : {len(seg_viol)}")
    for v in seg_viol[:12]:
        print("   ", v)

    bad_nets = sorted({v[0] for v in pad_viol} | {v[0] for v in seg_viol} | {v[1] for v in seg_viol if len(v) > 2})
    print(f"\nnets involved: {len(bad_nets)}")
    json.dump({"pad_viol": pad_viol, "seg_viol": seg_viol, "bad_nets": bad_nets},
              open(sys.argv[3], "w"))


if __name__ == "__main__":
    main()
