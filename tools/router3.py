#!/usr/bin/env python3
"""Router v3 — adds radial escape stubs for fine-pitch pads.

The QFN-68 has 0.4 mm pitch: pad gap 7.4 mil < 2*clearance, so the pad ring seals
itself under any naive obstacle inflation.  Real designers escape radially along
the pad's long axis.  This does the same:

  for every pad   : determine outward direction (long axis, away from component centre)
                    stub = pad centre -> pad edge + STUB_OUT
                    carve that narrow corridor back into the free space
  A*              : runs between stub ends, never from the pad centre

Outputs segments (net, layer, width, endpoints) ready for pcb_PrimitiveLine.create.
"""
import heapq
import json
import math
import sys

CELL = 4.0
BOARD_W, BOARD_H = 2755.9055, 1102.3622
EDGE_KEEP = 10.0
CLEAR = 4.0
STUB_OUT = 26.0
STUB_HALF = 5.0

WIDTHS = {"signal": 6.0, "power": 16.0}
POWER_NETS = {"3V3", "1V8", "1V2", "5V"}

NX = int(math.ceil(BOARD_W / CELL))
NY = int(math.ceil(BOARD_H / CELL))


def c2i(v):
    return int(round(v / CELL))


def i2c(i):
    return i * CELL


def width_for(net):
    return WIDTHS["power"] if net in POWER_NETS else WIDTHS["signal"]


def escape_dir(pad, centroid):
    """long axis of the pad, pointing away from the component centre"""
    w, h = pad["w"], pad["h"]
    cx, cy = centroid
    if h >= w:
        return (0.0, 1.0 if pad["y"] >= cy else -1.0), h / 2.0
    return (1.0 if pad["x"] >= cx else -1.0, 0.0), w / 2.0


class Grid:
    def __init__(self):
        self.blocked = {1: set(), 2: set()}

    def block_rect(self, layer, x, y, w, h, pad=0.0):
        for ix in range(c2i(x - w / 2 - pad), c2i(x + w / 2 + pad) + 1):
            for iy in range(c2i(y - h / 2 - pad), c2i(y + h / 2 + pad) + 1):
                self.blocked[layer].add((ix, iy))

    def carve(self, layer, p0, p1, half):
        x0, y0 = p0
        x1, y1 = p1
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / (CELL / 2)))
        for k in range(steps + 1):
            cx = x0 + (x1 - x0) * k / steps
            cy = y0 + (y1 - y0) * k / steps
            for ix in range(c2i(cx - half), c2i(cx + half) + 1):
                for iy in range(c2i(cy - half), c2i(cy + half) + 1):
                    self.blocked[layer].discard((ix, iy))


NEI = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def astar(grid, layer, start, goal, extra):
    blocked = grid.blocked[layer]
    gx, gy = goal
    openq = [(0.0, 0.0, start)]
    came = {}
    cost = {start: 0.0}
    seen = set()
    while openq:
        _, g0, cur = heapq.heappop(openq)
        if cur in seen:
            continue
        seen.add(cur)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        cx, cy = cur
        for dx, dy in NEI:
            n = (cx + dx, cy + dy)
            if not (0 <= n[0] < NX and 0 <= n[1] < NY):
                continue
            if n in blocked or n in extra:
                continue
            ng = g0 + (1.41421356 if dx and dy else 1.0)
            if ng < cost.get(n, 1e18):
                cost[n] = ng
                came[n] = cur
                heapq.heappush(openq, (ng + math.hypot(n[0] - gx, n[1] - gy), ng, n))
    return None


def simplify(path):
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        a = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
        b = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        if a != b:
            out.append(path[i])
    out.append(path[-1])
    return out


def chamfer(pts, cut=3):
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        ax, ay = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        bx, by = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        orth_a = not (ax and ay)
        orth_b = not (bx and by)
        if orth_a and orth_b and (ax * by - ay * bx) != 0:
            la, lb = abs(ax) + abs(ay), abs(bx) + abs(by)
            c = max(1, min(cut, la - 1 if la > 1 else 1, lb - 1 if lb > 1 else 1))
            p0 = (pts[i][0] - math.copysign(c, ax), pts[i][1] - math.copysign(c, ay))
            p1 = (pts[i][0] + math.copysign(c, bx), pts[i][1] + math.copysign(c, by))
            if p0 != out[-1]:
                out.append(p0)
            out.append(p1)
        else:
            out.append(pts[i])
    if pts[-1] != out[-1]:
        out.append(pts[-1])
    ded = [out[0]]
    for p in out[1:]:
        if p != ded[-1]:
            ded.append(p)
    return ded


def build(pads):
    centroids = {}
    for p in pads:
        acc = centroids.setdefault(p["comp"], [0.0, 0.0, 0])
        acc[0] += p["x"]
        acc[1] += p["y"]
        acc[2] += 1
    for k, v in centroids.items():
        centroids[k] = (v[0] / v[2], v[1] / v[2])

    grid = Grid()
    for p in pads:
        for layer in (1, 2):
            grid.block_rect(layer, p["x"], p["y"], max(p["w"], CELL), max(p["h"], CELL), CLEAR + 3.0)

    stubs = {}
    for p in pads:
        (dx, dy), half = escape_dir(p, centroids[p["comp"]])
        reach = half + STUB_OUT
        tip = (p["x"] + dx * reach, p["y"] + dy * reach)
        # near a board edge the outward direction can leave the board: flip it
        if not (EDGE_KEEP < tip[0] < BOARD_W - EDGE_KEEP and EDGE_KEEP < tip[1] < BOARD_H - EDGE_KEEP):
            dx, dy = -dx, -dy
            tip = (p["x"] + dx * reach, p["y"] + dy * reach)
        stubs[id(p)] = tip
        for layer in (1, 2):
            grid.carve(layer, (p["x"], p["y"]), tip, STUB_HALF)
    return grid, stubs


def route(pads, skip_gnd=True):
    nets = {}
    for p in pads:
        if p["net"]:
            nets.setdefault(p["net"], []).append(p)
    grid, stubs = build(pads)

    todo = [n for n in nets if not (skip_gnd and n == "GND")]

    def span(n):
        ps = nets[n]
        return max(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for a in ps for b in ps)
    todo.sort(key=span)

    extra = {1: set(), 2: set()}
    segs, fails = [], []

    for net in todo:
        ps = nets[net]
        w = width_for(net)
        cx, cy = BOARD_W / 2, BOARD_H / 2
        ps = sorted(ps, key=lambda p: math.hypot(p["x"] - cx, p["y"] - cy))
        done = []
        # the first pad defines the net origin
        tip0 = stubs[id(ps[0])]
        done.append((c2i(tip0[0]), c2i(tip0[1]), 1))
        segs.append({"net": net, "layer": 1, "width": w,
                     "x1": ps[0]["x"], "y1": ps[0]["y"], "x2": tip0[0], "y2": tip0[1]})
        for p in ps[1:]:
            tip = stubs[id(p)]
            goal = (c2i(tip[0]), c2i(tip[1]))
            best = None
            for (ax, ay, al) in done:
                for layer in (al, 2 if al == 1 else 1):
                    path = astar(grid, layer, (ax, ay), goal, extra[layer])
                    if path:
                        best = (layer, path)
                        break
                if best:
                    break
            if not best:
                fails.append(f"{net}:{p['comp']}.{p['n']}")
                continue
            layer, path = best
            pts = chamfer(simplify(path))
            for a, b in zip(pts, pts[1:]):
                segs.append({"net": net, "layer": layer, "width": w,
                             "x1": i2c(a[0]), "y1": i2c(a[1]), "x2": i2c(b[0]), "y2": i2c(b[1])})
                steps = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
                for k in range(steps + 1):
                    ix = a[0] + round((b[0] - a[0]) * k / steps) if steps else a[0]
                    iy = a[1] + round((b[1] - a[1]) * k / steps) if steps else a[1]
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            extra[layer].add((ix + dx, iy + dy))
            segs.append({"net": net, "layer": layer, "width": w,
                         "x1": p["x"], "y1": p["y"], "x2": tip[0], "y2": tip[1]})
            done.append((goal[0], goal[1], layer))
    return segs, fails


if __name__ == "__main__":
    pads = json.load(open(sys.argv[1]))["pads"]
    segs, fails = route(pads)
    json.dump({"segs": segs, "fails": fails}, open(sys.argv[2], "w"))
    print(f"segments: {len(segs)}   failed: {len(fails)}")
    for f in fails[:15]:
        print("  FAIL", f)
