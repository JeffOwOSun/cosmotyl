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
import sys
import os
from pathlib import Path

from stl_io import read_stl, write_stl
from mesh_audit import topology, screw_seats, column_seats

from config import CASE, COLUMNS, THUMB
from devtool import devtool_scad
from main3 import _holes, _plate, finger_webs, footprint_poly, pod_webs
from placement import Layout
from transform import apply
from verify import report
from web import HD, HW, get

TOP_SCAD, TOP_STL = "top4_right.scad", "top4_right.stl"
BASE_SCAD, BASE_STL = "base4_right.scad", "base4_right.stl"

# PT 3.0 thread-forming screw in plastic: Ø2.5 pilot, Ø6 boss minimum (2xd),
# Ø3.4 clearance, pan head Ø5.6 x 2.4.
PILOT_R = 1.25
CLEAR_R = 1.7
CBORE_R = 3.0  # Ø6.0 counterbore: 5.6 head + 0.4; keeps 0.26mm web to the
HEAD_CLEARANCE = 0.4  # recess screw heads below adjacent moving-key envelopes
HEAD_H = 2.4  # MX hole corner (junction->hole-corner clearance 3.26mm)
NECK_R = 3.0  # Ø6 neck fits the 3.36mm junction channel
BODY_R = 4.5  # Ø9 column body below the housing zone
NECK_H = 5.0  # housing keep-out reaches only 0.8mm below underside
FLARE_H = 1.5  # 45-deg cone neck->body
SEAT_R = 3.3  # continuous bearing pad around the Ø3.4 screw clearance
SEAT_DROP = 1.5  # extend below the lowest junction corner
SEAT_GAP = 0.15  # conformal seat clearance (subtract sheet lowered by this)

WEB_SURFACE_INSET = 0.02
WEB_EDGE_INSET = 0.10

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
        x, y, z = _junction([(A, HW, -HD), (B, -HW, -HD), (C, HW, HD), (D, -HW, HD)])
        pts.append((f"J{c}{r}", x, y, z))
    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    for i in range(THUMB.keys - 1):
        x, y, z = _junction(
            [(t[i], -HW, HD), (t[i], -HW, -HD), (t[i + 1], HW, HD), (t[i + 1], HW, -HD)]
        )
        pts.append((f"P{i}{i + 1}", x, y, z))
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
        print(
            f"col {tag:4s} at ({x:7.2f},{y:7.2f}) underside z={z:6.2f} "
            f"seat z={z + CASE.plate_t - HEAD_H - HEAD_CLEARANCE:6.2f}"
        )

    # Flat bearing pads prevent the counterbore from breaking through a sloped
    # web. The base columns terminate below each pad underside.
    pads = []
    for tag, x, y, z in cols:
        seat = z + CASE.plate_t - HEAD_H - HEAD_CLEARANCE
        pads.append(
            f"translate([{x:.5f},{y:.5f},{z - SEAT_DROP:.5f}]) "
            f"cylinder(h={seat - z + SEAT_DROP:.5f}, r={SEAT_R}, $fn=64);"
        )

    # --- top sheet: (plates+webs - key holes) - screw clearance/counterbores
    screw_cuts = []
    for tag, x, y, z in cols:
        seat = z + CASE.plate_t - HEAD_H - HEAD_CLEARANCE
        screw_cuts.append(
            f"translate([{x:.5f},{y:.5f},{z - 20:.5f}]) "
            f"cylinder(h=40, r={CLEAR_R}, $fn=32);"
        )
        screw_cuts.append(
            f"translate([{x:.5f},{y:.5f},{seat:.5f}]) "
            f"cylinder(h=30, r={CBORE_R}, $fn=32);"
        )
    body = (
        "difference() { union() {"
        + " ".join(
            fplates
            + finger_webs(
                layout, surface_inset=WEB_SURFACE_INSET, edge_inset=WEB_EDGE_INSET
            )
        )
        + "} "
        + " ".join(fholes)
        + "}"
    )
    pod = (
        "difference() { union() {"
        + " ".join(
            tplates
            + pod_webs(
                layout, surface_inset=WEB_SURFACE_INSET, edge_inset=WEB_EDGE_INSET
            )
        )
        + "} "
        + " ".join(tholes)
        + "}"
    )
    top = (
        "// v4 top sheet: print on its side (see main4.py header)\n"
        "difference() { union() {\n"
        + body
        + "\n"
        + pod
        + "\n"
        + " ".join(pads)
        + "\n} "
        + " ".join(screw_cuts)
        + devtool_scad(layout, clearance=0.05)
        + "}\n"
    )
    open(TOP_SCAD, "w").write(top)

    # --- base: shell + columns ending below the flat bearing pads;
    # revolve each column as one solid, then subtract the pilot bores.
    col_solids, pilots = [], []
    for tag, x, y, z in cols:
        ztop = z - SEAT_DROP - SEAT_GAP  # flat column seat beneath the bearing pad
        profile = [
            (0, 0.5),
            (BODY_R, 0.5),
            (BODY_R, ztop - NECK_H - FLARE_H),
            (NECK_R, ztop - NECK_H),
            (NECK_R, ztop),
            (0, ztop),
        ]
        points = ", ".join(f"[{r:.5f},{h:.5f}]" for r, h in profile)
        col_solids.append(
            f"translate([{x:.5f},{y:.5f},0]) "
            f"rotate_extrude($fn=48) polygon([{points}]);"
        )
        pilot_bottom = max(1.0, ztop - 10.0)
        pilots.append(
            f"translate([{x:.5f},{y:.5f},{pilot_bottom:.5f}]) "
            f"cylinder(h={ztop - pilot_bottom + 1.0:.5f}, r={PILOT_R}, $fn=24);"
        )
    rodlike = [(t, 0, 0, x, y, z) for t, x, y, z in cols]
    poly = footprint_poly(layout, rodlike)
    pstr = ", ".join(f"[{x:.5f},{y:.5f}]" for x, y in poly)
    shell = f"linear_extrude({CASE.bottom_t}) offset(r=2.5, $fn=32) polygon([{pstr}]);"
    base = (
        "// v4 base: shell + screw columns (prints flat, rods vertical)\n"
        "difference() { union() {\n"
        + shell
        + "\n"
        + " ".join(col_solids)
        + "\n} "
        + " ".join(pilots)
        + "}\n"
    )
    open(BASE_SCAD, "w").write(base)

    open("assembled4_right.scad", "w").write(
        f'union() {{ import("{TOP_STL}"); import("{BASE_STL}"); }}\n'
    )
    open("devtool_right.scad", "w").write(devtool_scad(layout))
    print(f"wrote {TOP_SCAD} + {BASE_SCAD}")
    print(
        f"BOM: {len(cols)}x thread-forming screw 3.0x12 pan head "
        f"(pilot Ø{2 * PILOT_R}, boss Ø{2 * NECK_R})"
    )


_read_tris = read_stl


def orient_audit(path):
    """Report the downward-flat (unprintable, tilt<45 deg) area fraction of the
    top sheet for candidate print rotations about the y axis."""
    tris = _read_tris(path)
    print(f"\n--- print-orientation audit: {path} ({len(tris)} tris) ---")
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
        print(
            f"  Ry({deg:+4d}): downward-flat area = {frac * 100:5.1f}%"
            f"  ({bad:7.0f} of {tot:.0f} mm2)"
        )
        if best is None or frac < best[1]:
            best = (deg, frac)
    print(f"  best: Ry({best[0]:+d}) with {best[1] * 100:.1f}% unprintable area")
    return best[0]


def _rot_drop(tris, deg):
    """Rotate about y by deg, then drop so min z = 0."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = [tuple((x * ca + z * sa, y, -x * sa + z * ca) for x, y, z in t) for t in tris]
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
    print(f"--- flat-down patch audit (Ry({deg:+d}), bridge<= {bridge_max}mm) ---")
    bad = 0
    for g in groups.values():
        area = sum(a for _, a in g)
        pts = [v for t, _ in g for v in t]
        zlo = min(v[2] for v in pts)
        span = min(
            max(v[0] * math.cos(th) + v[1] * math.sin(th) for v in pts)
            - min(v[0] * math.cos(th) + v[1] * math.sin(th) for v in pts)
            for th in [k * math.pi / 18 for k in range(18)]
        )
        if zlo < 0.3 or span <= bridge_max or area < 3.0:
            continue
        bad += 1
        cx = sum(v[0] for v in pts) / len(pts)
        cy = sum(v[1] for v in pts) / len(pts)
        print(
            f"  PROBLEM patch: area={area:6.0f}mm2 span={span:5.1f}mm "
            f"z={zlo:5.1f} at ({cx:6.1f},{cy:6.1f})"
        )
    if not bad:
        print("  all flat-down patches rest on the bed or bridge — PRINTS SUPPORT-FREE")
    return bad


def export_print(path, deg):
    """Split disconnected parts (board sheet, thumb pod), rotate each to the
    print orientation and drop it onto the bed."""
    tris = _read_tris(path)
    parts = topology(tris)
    if len(parts) != 2:
        raise RuntimeError(f"Expected board and pod, found {len(parts)} components")
    for i, part in enumerate(parts):
        dropped = _rot_drop(part, deg)
        name = f"top4_print_{'board' if i == 0 else 'pod'}.stl"
        write_stl(name, dropped)
        if len(topology(read_stl(name))) != 1:
            raise RuntimeError(f"{name}: expected one closed printed part")
        print(f"wrote {name} ({len(part)} tris, print-oriented Ry({deg:+d}))")


def main():
    layout = Layout()
    if report(layout):
        sys.exit("verification failed; not rendering")
    build(layout)
    if "--fast" in sys.argv:
        return
    from mesh_backend import render_mesh, require_empty
    import manifold3d as md

    top = render_mesh(TOP_SCAD, TOP_STL)
    base = render_mesh(BASE_SCAD, BASE_STL)
    dev = render_mesh("devtool_right.scad", "devtool_right.stl")
    require_empty(top, dev, "top/switch envelope")
    require_empty(base, dev, "base/switch envelope")
    require_empty(top, base, "top/base assembly")
    for tag, x, y, z in column_pts(layout):
        seat = z + CASE.plate_t - HEAD_H - HEAD_CLEARANCE
        head = md.Manifold.cylinder(HEAD_H, 2.8, circular_segments=64).translate(
            (x, y, seat)
        )
        require_empty(head, dev, f"{tag} screw head/switch envelope")
    screw_seats(
        read_stl(TOP_STL),
        column_pts(layout),
        plate_thickness=CASE.plate_t,
        head_height=HEAD_H + HEAD_CLEARANCE,
    )
    column_seats(
        read_stl(BASE_STL), column_pts(layout), pad_drop=SEAT_DROP, gap=SEAT_GAP
    )
    print("all seven screw seats: complete flat bearing rings and clear shafts")

    best = orient_audit(TOP_STL)
    patch_audit(TOP_STL, best)
    export_print(TOP_STL, best)


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    main()
