"""Support skirt: ruled loft from the plate boundary edge to the z=0 plane.

Boundary edges are directed CCW (interior on the left, viewed from +z),
greedily chained by nearest endpoints, and every edge AND every inter-edge
gap is hulled with floor pads at the corners' vertical projections — the
degenerate d1=d2=0 wall [D adapted, your no-wall call]. Foot segments are
recorded in loop order for the bottom plate outline.
"""
import math

from config import CASE, COLUMNS, THUMB
from transform import apply
from web import HD, HW, get, post


def boundary_edges(layout):
    """Directed (frame, corner1, corner2) for every exposed plate edge.

    CCW convention: left (-HW,+HD)->(-HW,-HD), front (-HW,-HD)->(+HW,-HD),
    right (+HW,-HD)->(+HW,+HD), back (+HW,+HD)->(-HW,+HD)."""
    edges = []
    skip_front = {(0, COLUMNS[0].rows - 1), (1, COLUMNS[1].rows - 1)}  # thumb bridge
    for c in range(len(COLUMNS)):
        for r in range(COLUMNS[c].rows):
            A = get(layout, c, r)
            if A is None:
                continue
            if get(layout, c - 1, r) is None:
                edges.append((A, (-HW, HD), (-HW, -HD)))
            if get(layout, c + 1, r) is None:
                edges.append((A, (HW, -HD), (HW, HD)))
            if r == 0:
                edges.append((A, (HW, HD), (-HW, HD)))
            if get(layout, c, r + 1) is None and (c, r) not in skip_front:
                edges.append((A, (-HW, -HD), (HW, -HD)))
    # thumb pod exposed sides (t0 = right/anchor key; higher indices extend
    # left). The bridge consumes t0/t1 back (+HD) edges, inter-key webs the
    # left/right pairs; everything else lofts to the floor.
    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    edges += [(t[i], (HW, HD), (-HW, HD)) for i in range(2, THUMB.keys)]
    edges.append((t[-1], (-HW, HD), (-HW, -HD)))
    edges += [(t[i], (-HW, -HD), (HW, -HD)) for i in range(THUMB.keys)]
    edges.append((t[0], (HW, -HD), (HW, HD)))
    return edges


def _foot(m, corner):
    p = apply(m, (corner[0], corner[1], -CASE.plate_t))
    return (p[0], p[1])


def chain_edges(layout, edges):
    """Greedy nearest-start chaining into one closed loop."""
    used = [False] * len(edges)
    order = [0]
    used[0] = True
    for _ in range(len(edges) - 1):
        cur_end = _foot(edges[order[-1]][0], edges[order[-1]][2])
        best, best_d = None, None
        for i, e in enumerate(edges):
            if used[i]:
                continue
            s = _foot(e[0], e[1])
            d = math.hypot(s[0] - cur_end[0], s[1] - cur_end[1])
            if best is None or d < best_d:
                best, best_d = i, d
        order.append(best)
        used[best] = True
    return [edges[i] for i in order]


def _floor_pad(x, y):
    return (f'translate([{x:.3f},{y:.3f},0.05]) '
            f'cube([{CASE.skirt_t},{CASE.skirt_t},0.1], center=true);')


def _loft(m1, c1, m2, c2):
    f1, f2 = _foot(m1, c1), _foot(m2, c2)
    return 'hull() {%s%s%s%s}' % (post(m1, *c1), post(m2, *c2),
                                  _floor_pad(*f1), _floor_pad(*f2))


def skirt(layout):
    """Loft solids + the ordered foot polygon [(x,y), ...] at z=0."""
    loop = chain_edges(layout, boundary_edges(layout))
    solids, feet = [], []
    n = len(loop)
    for i, (m, c1, c2) in enumerate(loop):
        solids.append(_loft(m, c1, m, c2))            # the edge itself
        nm, nc1, _ = loop[(i + 1) % n]
        solids.append(_loft(m, c2, nm, nc1))          # gap to the next edge
        feet.append(_foot(m, c1))
        feet.append(_foot(m, c2))
    return solids, feet
