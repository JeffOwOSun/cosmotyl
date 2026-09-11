"""v3: floating plates. Steps: (1) lay out keys as full plates, (2) loft
adjacent side faces flush (web.py posts sit exactly on plate edges), (3) cut
holes. The thumb pod floats — no surface connection to the board — and both
bodies stand on vertical rods anchored in a flat bottom shell.

Usage: python3 main3.py [--fast]
"""
import math
import sys
import os
from pathlib import Path

from render import render, openscad

from config import CASE, COLUMNS, THUMB
from devtool import devtool_scad
from placement import Layout
from transform import apply, scad_mat
from verify import report
from web import HD, HW, get, post

OUT_SCAD = 'case3_right.scad'
OUT_STL = 'case3_right.stl'
ROD_R = 3.0          # rod radius (Ø6)
EMBED = 1.5          # rod overlap into the plate/web underside for CSG fusion


def _plate(m):
    return (f'multmatrix({scad_mat(m)}) translate([0,0,{-CASE.plate_t / 2}]) '
            f'cube([{CASE.key_w},{CASE.key_d},{CASE.plate_t}], center=true);')


def _holes(m):
    # Extend the clip relief below the plate to avoid a coincident bottom face.
    # Its upper ledge stays 1.5 mm above the plate underside.
    mm = scad_mat(m)
    return (f'multmatrix({mm}) translate([0,0,{-CASE.plate_t / 2}]) '
            f'cube([{CASE.mx_hole},{CASE.mx_hole},{CASE.plate_t + 2}], center=true);'
            f'multmatrix({mm}) translate([0,0,{-CASE.plate_t + 0.25}]) '
            f'cube([{CASE.mx_hole + CASE.clip_undercut},'
            f'{CASE.mx_hole + CASE.clip_undercut},2.5], center=true);')


def finger_webs(layout, surface_inset=0.0, edge_inset=0.0):
    """Row/col/diagonal lofts between finger keys only (no thumb bridge)."""
    def corner(m, sx, sy):
        return post(m, sx, sy, surface_inset, edge_inset)

    out = []
    for c in range(len(COLUMNS)):
        for r in range(max(col.rows for col in COLUMNS)):
            A = get(layout, c, r)
            if A is None:
                continue
            Rt = get(layout, c + 1, r)
            Dn = get(layout, c, r + 1)
            Dg = get(layout, c + 1, r + 1)
            if Rt:
                out.append('hull() {%s%s%s%s}' % (corner(A, HW, HD), corner(A, HW, -HD),
                                                  corner(Rt, -HW, HD), corner(Rt, -HW, -HD)))
            if Dn:
                out.append('hull() {%s%s%s%s}' % (corner(A, -HW, -HD), corner(A, HW, -HD),
                                                  corner(Dn, -HW, HD), corner(Dn, HW, HD)))
            corners = [(A, HW, -HD)]
            if Rt:
                corners.append((Rt, -HW, -HD))
            if Dn:
                corners.append((Dn, HW, HD))
            if Dg:
                corners.append((Dg, -HW, HD))
            if len(corners) >= 3:
                out.append('hull() {' + ''.join(corner(m, sx, sy) for m, sx, sy in corners) + '}')
    return out


def pod_webs(layout, surface_inset=0.0, edge_inset=0.0):
    """Lofts between adjacent thumb keys only."""
    def corner(m, sx, sy):
        return post(m, sx, sy, surface_inset, edge_inset)

    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    return ['hull() {%s%s%s%s}' % (corner(t[i], -HW, HD), corner(t[i], -HW, -HD),
                                   corner(t[i + 1], HW, HD), corner(t[i + 1], HW, -HD))
            for i in range(THUMB.keys - 1)]


FLAT_TILT = 42.0     # deg; undersides flatter than this need anchors (45 - margin)


def _tilt(m):
    """Underside tilt from horizontal (deg): 0 = flat overhang, 90 = vertical."""
    return math.degrees(math.acos(min(1.0, abs(m[2][2]))))


def _rod(x, y, z_top):
    return (f'translate([{x:.2f},{y:.2f},0.5]) '
            f'cylinder(h={z_top - 0.5:.2f}, r={ROD_R}, $fn=32);')


def rods(layout):
    """Support-free rod distribution [print audit 2026-09-10]:

    Every underside flatter than FLAT_TILT is an unprintable overhang, and the
    only places a Ø6 rod fits under the board are 4-key junctions (radial
    clearance 3.36mm to the housing diagonals) and outboard of boundary edges
    (interior edge gaps are 4.5mm < Ø6). So: a junction rod at every interior
    junction touching a flat key, plus an outboard edge rod on every boundary
    edge of a flat key. Max unanchored bridge = pitch - Ø6 ≈ 12.5mm.
    """
    out, pts = [], []

    def junction(frames_corners):
        ps = [apply(m, (sx, sy, -CASE.plate_t)) for m, sx, sy in frames_corners]
        x = sum(p[0] for p in ps) / len(ps)
        y = sum(p[1] for p in ps) / len(ps)
        z = min(p[2] for p in ps)
        return x, y, z

    def edge_rod(m, sx, sy, tag):
        p = apply(m, (sx, sy, -CASE.plate_t))
        out.append(_rod(p[0], p[1], p[2] + 1.2))
        pts.append((tag, 0, 0, p[0], p[1], p[2]))

    # Interior 4-key junction rods wherever a flat key touches the junction.
    for c in range(len(COLUMNS) - 1):
        for r in range(max(COLUMNS[c].rows, COLUMNS[c + 1].rows)):
            A, B = get(layout, c, r), get(layout, c + 1, r)
            C, D = get(layout, c, r + 1), get(layout, c + 1, r + 1)
            if not (A is not None and B is not None
                    and C is not None and D is not None):
                continue
            if min(_tilt(A), _tilt(B), _tilt(C), _tilt(D)) >= FLAT_TILT:
                continue
            x, y, z = junction([(A, HW, -HD), (B, -HW, -HD),
                                (C, HW, HD), (D, -HW, HD)])
            out.append(_rod(x, y, z + EMBED))
            pts.append(('board', c, r, x, y, z))

    # Outboard edge rods on every boundary edge of a flat finger key.
    for c in range(len(COLUMNS)):
        for r in range(COLUMNS[c].rows):
            m = get(layout, c, r)
            if _tilt(m) >= FLAT_TILT:
                continue
            if c == 0 or get(layout, c - 1, r) is None:
                edge_rod(m, -HW - 1.0, 0.0, f'edgeL{c}{r}')
            if get(layout, c + 1, r) is None:
                edge_rod(m, HW + 1.0, 0.0, f'edgeR{c}{r}')
            if r == 0:
                edge_rod(m, 0.0, HD + 1.0, f'edgeB{c}{r}')
            if get(layout, c, r + 1) is None:
                edge_rod(m, 0.0, -HD - 1.0, f'edgeF{c}{r}')

    # Thumb pod: junction rods between pairs + outboard ring (all keys flat).
    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    for i in range(THUMB.keys - 1):
        x, y, z = junction([(t[i], -HW, HD), (t[i], -HW, -HD),
                            (t[i + 1], HW, HD), (t[i + 1], HW, -HD)])
        out.append(_rod(x, y, z + EMBED))
        pts.append(('podJ', i, i + 1, x, y, z))
    edge_rod(t[0], HW + 1.0, 0.0, 'pod0R')
    edge_rod(t[THUMB.keys - 1], -HW - 1.0, 0.0, 'pod2L')
    for i in range(THUMB.keys):
        edge_rod(t[i], 0.0, -HD - 1.0, f'podF{i}')
        edge_rod(t[i], 0.0, HD + 1.0, f'podB{i}')
    return out, pts


def _hull2d(pts):
    """Andrew monotone chain; returns CCW convex hull of 2D points."""
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))
    if len(pts) <= 2:
        return pts

    def cro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cro(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cro(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def footprint_poly(layout, rod_pts):
    """Convex hull of the XY projection of every solid: all plate corners
    (top and bottom faces of finger + thumb plates; webs are hulls of these
    same corners so they project inside) plus each rod's base circle."""
    pts = []
    hw, hd = CASE.key_w / 2, CASE.key_d / 2
    for _, m in layout.items():
        for sx in (-hw, hw):
            for sy in (-hd, hd):
                for sz in (0.0, -CASE.plate_t):
                    p = apply(m, (sx, sy, sz))
                    pts.append((p[0], p[1]))
    for _, _, _, x, y, _ in rod_pts:
        for k in range(12):
            a = k * math.pi / 6
            pts.append((x + ROD_R * math.cos(a), y + ROD_R * math.sin(a)))
    return _hull2d(pts)


def build(layout):
    fplates, fholes, tplates, tholes = [], [], [], []
    for c in range(len(COLUMNS)):
        for r in range(COLUMNS[c].rows):
            m = layout.key_frame(c, r)
            fplates.append(_plate(m))
            fholes.append(_holes(m))
    for i in range(THUMB.keys):
        m = layout.thumb_frame(i)
        tplates.append(_plate(m))
        tholes.append(_holes(m))

    body = ('difference() { union() {' + ' '.join(fplates + finger_webs(layout)) +
            '} ' + ' '.join(fholes) + '}')
    pod = ('difference() { union() {' + ' '.join(tplates + pod_webs(layout)) +
           '} ' + ' '.join(tholes) + '}')
    rod_scads, rod_pts = rods(layout)
    for tag, a, b, x, y, z in rod_pts:
        print(f'rod {tag:5s} ({a},{b}) at ({x:7.2f},{y:7.2f}) top z={z:6.2f}')
    poly = footprint_poly(layout, rod_pts)
    pstr = ', '.join(f'[{x:.2f},{y:.2f}]' for x, y in poly)
    shell = (f'linear_extrude({CASE.bottom_t}) offset(r=2.5) '
             f'polygon([{pstr}]);')

    scad = ('// v3: floating plates + pod on rods over a bottom shell\n'
            'union() {\n' + body + '\n' + pod + '\n' +
            ' '.join(rod_scads) + '\n' + shell + '\n}\n')
    open(OUT_SCAD, 'w').write(scad)
    uncut = ('// v3 uncut loft reference (steps 1-2, before hole cuts)\n'
             'union() {' + ' '.join(fplates + finger_webs(layout) +
                                    tplates + pod_webs(layout)) + '}\n')
    open('uncut3_right.scad', 'w').write(uncut)
    open('devtool_right.scad', 'w').write(devtool_scad(layout))
    print(f'wrote {OUT_SCAD} + uncut3_right.scad')


def main():
    layout = Layout()
    if report(layout):
        sys.exit('verification failed; not rendering')
    build(layout)
    if '--fast' in sys.argv:
        return
    render(OUT_SCAD, OUT_STL)
    from stl_clean import clean
    ncomp, dropped = clean(OUT_STL)
    print(f'wrote {OUT_STL} ({ncomp} raw components; dropped {dropped} tris)')
    render('devtool_right.scad', 'devtool_right.stl')
    open('interference3.scad', 'w').write(
        'intersection() { import("case3_right.stl"); '
        'import("devtool_right.stl"); }\n')
    render('interference3.scad', 'interference3.stl', expect_empty=True)


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    main()
