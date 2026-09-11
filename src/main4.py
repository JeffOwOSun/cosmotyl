"""v4: two-piece print (design A). Top sheet = plates + webs + pod, printed on
its side (row-arc normals live in the y-z plane, so a 90-deg roll about y turns
every flat underside into a near-vertical wall). Base = flat convex-hull shell
+ 7 columns ending in Ø6 necks with thread-forming pilot bores; the rods print
WITH the base, standing vertically. Assembly: 7 coarse thread-forming screws
(PT/plastite 3.0 x 12, pan head) dropped in from above BEFORE switches are
clipped in — heads recess below the plate top because upper housings leave
only 2.23mm radial clearance at junctions.

Usage: python3 main4.py [--fast]
"""
import math
import struct
import sys
import os
from pathlib import Path

from render import render, openscad

from config import CASE, COLUMNS, THUMB
from devtool import devtool_scad
from main3 import _holes, _plate, finger_webs, footprint_poly, pod_webs
from placement import Layout
from transform import apply
from verify import report
from web import HD, HW, get

TOP_SCAD, TOP_STL = 'top4_right.scad', 'top4_right.stl'
BASE_SCAD, BASE_STL = 'base4_right.scad', 'base4_right.stl'

# PT 3.0 thread-forming screw in plastic: Ø2.5 pilot, Ø6 boss minimum (2xd),
# Ø3.4 clearance, pan head Ø5.6 x 2.4.
PILOT_R = 1.25
CLEAR_R = 1.7
CBORE_R = 3.0     # Ø6.0 counterbore: 5.6 head + 0.4; keeps 0.26mm web to the
HEAD_H = 2.4      # MX hole corner (junction->hole-corner clearance 3.26mm)
NECK_R = 3.0      # Ø6 neck fits the 3.36mm junction channel
BODY_R = 4.5      # Ø9 column body below the housing zone
NECK_H = 5.0      # housing keep-out reaches only 0.8mm below underside
FLARE_H = 1.5     # 45-deg cone neck->body
SEAT_GAP = 0.15   # conformal seat clearance (subtract sheet lowered by this)

BOARD_J = [(0, 0), (0, 2), (2, 3), (4, 0), (4, 2)]


def _junction(frames_corners):
    ps = [apply(m, (sx, sy, -CASE.plate_t)) for m, sx, sy in frames_corners]
    x = sum(p[0] for p in ps) / len(ps)
    y = sum(p[1] for p in ps) / len(ps)
    z = min(p[2] for p in ps)
    return x, y, z


def column_pts(layout):
    """(tag, x, y, z_underside_min) for the 5 board + 2 pod screw columns."""
    pts = []
    for c, r in BOARD_J:
        A, B = get(layout, c, r), get(layout, c + 1, r)
        C, D = get(layout, c, r + 1), get(layout, c + 1, r + 1)
        x, y, z = _junction([(A, HW, -HD), (B, -HW, -HD),
                             (C, HW, HD), (D, -HW, HD)])
        pts.append((f'J{c}{r}', x, y, z))
    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    for i in range(THUMB.keys - 1):
        x, y, z = _junction([(t[i], -HW, HD), (t[i], -HW, -HD),
                             (t[i + 1], HW, HD), (t[i + 1], HW, -HD)])
        pts.append((f'P{i}{i + 1}', x, y, z))
    return pts


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

    cols = column_pts(layout)
    for tag, x, y, z in cols:
        print(f'col {tag:4s} at ({x:7.2f},{y:7.2f}) underside z={z:6.2f} '
              f'seat z={z + CASE.plate_t - HEAD_H:6.2f}')

    # --- top sheet: (plates+webs - key holes) - screw clearance/counterbores
    screw_cuts = []
    for tag, x, y, z in cols:
        seat = z + CASE.plate_t - HEAD_H
        screw_cuts.append(f'translate([{x:.2f},{y:.2f},{z - 20:.2f}]) '
                          f'cylinder(h=40, r={CLEAR_R}, $fn=32);')
        screw_cuts.append(f'translate([{x:.2f},{y:.2f},{seat:.2f}]) '
                          f'cylinder(h=30, r={CBORE_R}, $fn=32);')
    body = ('difference() { union() {' + ' '.join(fplates + finger_webs(layout)) +
            '} ' + ' '.join(fholes) + '}')
    pod = ('difference() { union() {' + ' '.join(tplates + pod_webs(layout)) +
           '} ' + ' '.join(tholes) + '}')
    top = ('// v4 top sheet: print on its side (see main4.py header)\n'
           'difference() { union() {\n' + body + '\n' + pod + '\n} ' +
           ' '.join(screw_cuts) + '}\n')
    open(TOP_SCAD, 'w').write(top)

    # --- base: shell + columns, conformally trimmed by the (lowered) sheet,
    # minus pilot bores.
    col_solids, pilots = [], []
    for tag, x, y, z in cols:
        ztop = z + 2.0  # overshoot; trimmed flush-minus-SEAT_GAP below
        col_solids.append(
            f'translate([{x:.2f},{y:.2f},0.5]) '
            f'cylinder(h={ztop - NECK_H - FLARE_H - 0.5:.2f}, r={BODY_R}, $fn=48);'
            f'translate([{x:.2f},{y:.2f},{ztop - NECK_H - FLARE_H:.2f}]) '
            f'cylinder(h={FLARE_H}, r1={BODY_R}, r2={NECK_R}, $fn=48);'
            f'translate([{x:.2f},{y:.2f},{ztop - NECK_H:.2f}]) '
            f'cylinder(h={NECK_H:.2f}, r={NECK_R}, $fn=48);')
        pilots.append(f'translate([{x:.2f},{y:.2f},{ztop - 14:.2f}]) '
                      f'cylinder(h=18, r={PILOT_R}, $fn=24);')
    rodlike = [(t, 0, 0, x, y, z) for t, x, y, z in cols]
    poly = footprint_poly(layout, rodlike)
    pstr = ', '.join(f'[{x:.2f},{y:.2f}]' for x, y in poly)
    shell = f'linear_extrude({CASE.bottom_t}) offset(r=2.5) polygon([{pstr}]);'
    sheet_uncut = ('union() {' + ' '.join(fplates + finger_webs(layout) +
                                          tplates + pod_webs(layout)) + '}')
    base = ('// v4 base: shell + screw columns (prints flat, rods vertical)\n'
            'difference() { union() {\n' + shell + '\n' +
            ' '.join(col_solids) + '\n} '
            f'translate([0,0,{-SEAT_GAP}]) {sheet_uncut} ' +
            ' '.join(pilots) + '}\n')
    open(BASE_SCAD, 'w').write(base)

    open('assembled4_right.scad', 'w').write(
        f'union() {{ import("{TOP_STL}"); import("{BASE_STL}"); }}\n')
    open('devtool_right.scad', 'w').write(devtool_scad(layout))
    print(f'wrote {TOP_SCAD} + {BASE_SCAD}')
    print(f'BOM: {len(cols)}x thread-forming screw 3.0x12 pan head '
          f'(pilot Ø{2 * PILOT_R}, boss Ø{2 * NECK_R})')


def _read_tris(path):
    data = open(path, 'rb').read()
    tris = []
    if data[:5] == b'solid' and b'facet' in data[:300]:
        cur = []
        for line in data.decode('ascii', 'ignore').splitlines():
            parts = line.split()
            if parts[:1] == ['vertex']:
                cur.append(tuple(float(v) for v in parts[1:4]))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
    else:
        n = struct.unpack('<I', data[80:84])[0]
        off = 84
        for _ in range(n):
            tris.append(tuple(struct.unpack_from('<3f', data, off + 12 + v * 12)
                              for v in range(3)))
            off += 50
    return tris


def orient_audit(path):
    """Report the downward-flat (unprintable, tilt<45 deg) area fraction of the
    top sheet for candidate print rotations about the y axis."""
    tris = _read_tris(path)
    print(f'\n--- print-orientation audit: {path} ({len(tris)} tris) ---')
    best = None
    for deg in (0, 78, 90, 102, -78, -90, -102):
        a = math.radians(deg)
        ca, sa = math.cos(a), math.sin(a)
        tot = bad = 0.0
        for p, q, r in tris:
            ux, uy, uz = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
            vx, vy, vz = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            area = 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)
            if area < 1e-9:
                continue
            nz_rot = -sa * nx + ca * nz  # Ry(a) applied to the normal
            tot += area
            if nz_rot / (2 * area) < -math.cos(math.radians(45)):
                bad += area
        frac = bad / tot if tot else 0.0
        print(f'  Ry({deg:+4d}): downward-flat area = {frac * 100:5.1f}%'
              f'  ({bad:7.0f} of {tot:.0f} mm2)')
        if best is None or frac < best[1]:
            best = (deg, frac)
    print(f'  best: Ry({best[0]:+d}) with {best[1] * 100:.1f}% unprintable area')
    return best[0]


def _rot_drop(tris, deg):
    """Rotate about y by deg, then drop so min z = 0."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = [tuple((x * ca + z * sa, y, -x * sa + z * ca) for x, y, z in t)
           for t in tris]
    zmin = min(v[2] for t in out for v in t)
    return [tuple((x, y, z - zmin) for x, y, z in t) for t in out]


def patch_audit(path, deg, bridge_max=8.0):
    """Group downward-flat triangles (after rotation) into connected patches;
    a patch is OK if it rests on the bed or its minor-axis span bridges."""
    tris = _rot_drop(_read_tris(path), deg)
    flat = []
    for t in tris:
        p, q, r = t
        ux, uy, uz = (q[0] - p[0], q[1] - p[1], q[2] - p[2])
        vx, vy, vz = (r[0] - p[0], r[1] - p[1], r[2] - p[2])
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        area = 0.5 * math.hypot(*n)
        if area > 1e-9 and n[2] / (2 * area) < -math.cos(math.radians(45)):
            flat.append((t, area))
    vid, parent = {}, []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    tri_root = []
    for t, _ in flat:
        ids = []
        for v in t:
            k = tuple(round(c, 2) for c in v)
            if k not in vid:
                vid[k] = len(parent)
                parent.append(len(parent))
            ids.append(vid[k])
        for b in ids[1:]:
            ra, rb = find(ids[0]), find(b)
            if ra != rb:
                parent[rb] = ra
        tri_root.append(ids[0])
    groups = {}
    for (t, area), r0 in zip(flat, tri_root):
        groups.setdefault(find(r0), []).append((t, area))
    print(f'--- flat-down patch audit (Ry({deg:+d}), bridge<= {bridge_max}mm) ---')
    bad = 0
    for g in groups.values():
        area = sum(a for _, a in g)
        pts = [v for t, _ in g for v in t]
        zlo = min(v[2] for v in pts)
        span = min(
            max(v[0] * math.cos(th) + v[1] * math.sin(th) for v in pts) -
            min(v[0] * math.cos(th) + v[1] * math.sin(th) for v in pts)
            for th in [k * math.pi / 18 for k in range(18)])
        if zlo < 0.3 or span <= bridge_max or area < 3.0:
            continue
        bad += 1
        cx = sum(v[0] for v in pts) / len(pts)
        cy = sum(v[1] for v in pts) / len(pts)
        print(f'  PROBLEM patch: area={area:6.0f}mm2 span={span:5.1f}mm '
              f'z={zlo:5.1f} at ({cx:6.1f},{cy:6.1f})')
    if not bad:
        print('  all flat-down patches rest on the bed or bridge — '
              'PRINTS SUPPORT-FREE')
    return bad


def export_print(path, deg):
    """Split disconnected parts (board sheet, thumb pod), rotate each to the
    print orientation and drop it onto the bed."""
    tris = _read_tris(path)
    vid, parent = {}, []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    roots = []
    for t in tris:
        ids = []
        for v in t:
            k = tuple(round(c, 3) for c in v)
            if k not in vid:
                vid[k] = len(parent)
                parent.append(len(parent))
            ids.append(vid[k])
        for b in ids[1:]:
            ra, rb = find(ids[0]), find(b)
            if ra != rb:
                parent[rb] = ra
        roots.append(ids[0])
    comps = {}
    for t, r0 in zip(tris, roots):
        comps.setdefault(find(r0), []).append(t)
    parts = sorted(comps.values(), key=len, reverse=True)
    if len(parts) != 2:
        raise RuntimeError(f"Expected board and pod, found {len(parts)} components")
    for i, part in enumerate(parts):
        dropped = _rot_drop(part, deg)
        name = f'top4_print_{"board" if i == 0 else "pod"}.stl'
        with open(name, 'w') as f:
            f.write('solid p\n')
            for a, b, c in dropped:
                f.write(' facet normal 0 0 0\n  outer loop\n')
                for v in (a, b, c):
                    f.write(f'   vertex {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n')
                f.write('  endloop\n endfacet\n')
            f.write('endsolid p\n')
        print(f'wrote {name} ({len(part)} tris, print-oriented Ry({deg:+d}))')


def main():
    layout = Layout()
    if report(layout):
        sys.exit('verification failed; not rendering')
    build(layout)
    if '--fast' in sys.argv:
        return
    for scad, stl in ((TOP_SCAD, TOP_STL), (BASE_SCAD, BASE_STL),
                      ('devtool_right.scad', 'devtool_right.stl')):
        render(scad, stl)
    open('interference4.scad', 'w').write(
        'intersection() { union() { import("top4_right.stl"); '
        'import("base4_right.stl"); } import("devtool_right.stl"); }\n')
    render('interference4.scad', 'interference4.stl', expect_empty=True)

    best = orient_audit(TOP_STL)
    patch_audit(TOP_STL, best)
    export_print(TOP_STL, best)


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    main()
