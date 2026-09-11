"""Bottom plate + heat-insert bosses — pure consumers of the skirt foot loop.

The plate is the extruded foot polygon; bosses stand inside the loop at sites
picked by landmark, and the plate's screw holes reuse the same sites, so
case/plate alignment is guaranteed by construction [M/D].
"""
import math

from config import CASE


def _dedupe(loop, tol=0.5):
    out = []
    for p in loop:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def _centroid(pts):
    x = sum(p[0] for p in pts) / len(pts)
    y = sum(p[1] for p in pts) / len(pts)
    return x, y


def _segments_cross(a, b, c, d):
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2 = cr(c, d, a), cr(c, d, b)
    d3, d4 = cr(a, b, c), cr(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _uncross(pts):
    """Remove vertices that self-intersect the loop (bowties from inboard
    feet of exposed side edges); the plate just needs to cover the footprint,
    so dropping the inboard-most offender only over-covers the notch."""
    pts = list(pts)
    for _ in range(len(pts)):
        n = len(pts)
        crossing = None
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                if _segments_cross(pts[i], pts[(i + 1) % n],
                                   pts[j], pts[(j + 1) % n]):
                    crossing = (i, (i + 1) % n, j, (j + 1) % n)
                    break
            if crossing:
                break
        if not crossing:
            return pts
        cx, cy = _centroid(pts)
        victim = min(crossing,
                     key=lambda k: (pts[k][0] - cx) ** 2 + (pts[k][1] - cy) ** 2)
        pts.pop(victim)
    return pts


def screw_sites(feet, inset=6.0):
    """5 sites: nearest foot vertices to bbox landmarks, inset toward centroid."""
    pts = _dedupe(feet)
    cx, cy = _centroid(pts)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    landmarks = [
        (min(xs), max(ys)),                    # back-left
        (max(xs), max(ys)),                    # back-right
        (max(xs), min(ys)),                    # front-right
        ((min(xs) + max(xs)) / 2, min(ys)),    # front-middle
        (min(xs), min(ys)),                    # thumb side
    ]
    sites = []
    for lx, ly in landmarks:
        p = min(pts, key=lambda q: (q[0] - lx) ** 2 + (q[1] - ly) ** 2)
        d = math.hypot(cx - p[0], cy - p[1])
        s = (p[0] + (cx - p[0]) / d * inset, p[1] + (cy - p[1]) / d * inset)
        if all(math.hypot(s[0] - t[0], s[1] - t[1]) > 25 for t in sites):
            sites.append(s)
    return sites


def case_bosses(sites):
    """Heat-insert bosses standing on the floor inside the skirt."""
    solids, cuts = [], []
    r_boss = CASE.insert_boss / 2
    for x, y in sites:
        solids.append(f'translate([{x:.2f},{y:.2f},0]) '
                      f'cylinder(h={CASE.insert_boss_h}, r={r_boss}, $fn=32);')
        cuts.append(f'translate([{x:.2f},{y:.2f},-0.5]) '
                    f'cylinder(h={CASE.insert_boss_h + 1}, r={CASE.insert_bore / 2}, $fn=24);')
    return solids, cuts


def bottom_plate_scad(feet, sites, adds=()):
    """Standalone flat plate: foot polygon extruded, countersunk M3 holes,
    plus rails/pockets unioned on top."""
    pts = _uncross(_dedupe(feet))
    poly = ', '.join(f'[{x:.2f},{y:.2f}]' for x, y in pts)
    holes = []
    for x, y in sites:
        holes.append(f'translate([{x:.2f},{y:.2f},-0.5]) '
                     f'cylinder(h={CASE.bottom_t + 1}, r=1.7, $fn=24);')
        holes.append(f'translate([{x:.2f},{y:.2f},-0.01]) '
                     f'cylinder(h=1.7, r1=3.1, r2=1.7, $fn=24);')  # countersink
    return f'''// Bottom plate (right half): projection of the skirt foot loop.
$fn = 24;
difference() {{
  union() {{
    linear_extrude({CASE.bottom_t}) polygon([{poly}]);
    {' '.join(adds)}
  }}
  {' '.join(holes)}
}}
'''
