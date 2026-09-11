"""Socket plates, MX cutouts, and the triangle-hull web (manuform posts [M])."""
from config import CASE, COLUMNS, THUMB
from transform import scad_mat

HW = CASE.key_w / 2
HD = CASE.key_d / 2
POST = 0.8   # post cross-section; >0.1 so hulled sheets can't pinch to shards


def post(m, sx, sy, surface_inset=0.0, edge_inset=0.0):
    """Corner post, inset so its outer face lies exactly on the plate edge."""
    ix = sx - POST / 2 - edge_inset if sx > 0 else sx + POST / 2 + edge_inset
    iy = sy - POST / 2 - edge_inset if sy > 0 else sy + POST / 2 + edge_inset
    return (f'multmatrix({scad_mat(m)}) translate([{ix:.3f},{iy:.3f},{-CASE.plate_t / 2}]) '
            f'cube([{POST},{POST},{CASE.plate_t - 2 * surface_inset:.5f}], center=true);')


def plates_and_holes(layout):
    plates, holes = [], []
    for _, m in layout.items():
        mm = scad_mat(m)
        plates.append(f'multmatrix({mm}) translate([0,0,{-CASE.plate_t / 2}]) '
                      f'cube([{CASE.key_w},{CASE.key_d},{CASE.plate_t}], center=true);')
        holes.append(f'multmatrix({mm}) translate([0,0,{-CASE.plate_t / 2}]) '
                     f'cube([{CASE.mx_hole},{CASE.mx_hole},{CASE.plate_t + 2}], center=true);')
        # keycap clip undercut: 1.5mm ledge at the bottom of the plate
        holes.append(f'multmatrix({mm}) translate([0,0,{-CASE.plate_t + 0.75}]) '
                     f'cube([{CASE.mx_hole + CASE.clip_undercut},'
                     f'{CASE.mx_hole + CASE.clip_undercut},1.5], center=true);')
    return plates, holes


def get(layout, c, r):
    if 0 <= c < len(COLUMNS) and 0 <= r < COLUMNS[c].rows:
        return layout.key_frame(c, r)
    return None


def webs(layout):
    """Row/col/diagonal gap fills + the thumb bridge.

    Frame axes: +x right, +y back (row 0 side), so a key's back edge is +HD
    and its front edge is -HD; rows advance toward -y."""
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
                out.append('hull() {%s%s%s%s}' % (post(A, HW, HD), post(A, HW, -HD),
                                                  post(Rt, -HW, HD), post(Rt, -HW, -HD)))
            if Dn:
                out.append('hull() {%s%s%s%s}' % (post(A, -HW, -HD), post(A, HW, -HD),
                                                  post(Dn, -HW, HD), post(Dn, HW, HD)))
            corners = [(A, HW, -HD)]
            if Rt:
                corners.append((Rt, -HW, -HD))
            if Dn:
                corners.append((Dn, HW, HD))
            if Dg:
                corners.append((Dg, -HW, HD))
            if len(corners) >= 3:
                out.append('hull() {' + ''.join(post(m, sx, sy) for m, sx, sy in corners) + '}')
    out += thumb_bridge(layout)
    return out


def thumb_bridge(layout):
    """Pod back edges up to the well's front lip (inner + index bottoms).

    Key order: higher indices extend toward local -x (left/down); key i's
    LEFT edge joins key i+1's RIGHT edge. Only t0 (under index) and t1
    (under inner) have board keys behind them to bridge to."""
    t = [layout.thumb_frame(i) for i in range(THUMB.keys)]
    a = get(layout, 0, COLUMNS[0].rows - 1)   # inner bottom
    b = get(layout, 1, COLUMNS[1].rows - 1)   # index bottom
    out = [
        # between each adjacent pair of thumb keys
        'hull() {%s%s%s%s}' % (post(t[i], -HW, HD), post(t[i], -HW, -HD),
                               post(t[i + 1], HW, HD), post(t[i + 1], HW, -HD))
        for i in range(THUMB.keys - 1)
    ]
    out += [
        # inner bottom -> t1 back
        'hull() {%s%s%s%s}' % (post(a, -HW, -HD), post(a, HW, -HD),
                               post(t[1], -HW, HD), post(t[1], HW, HD)),
        # corner quad at the a/b/t1/t0 junction
        'hull() {%s%s%s%s}' % (post(a, HW, -HD), post(b, -HW, -HD),
                               post(t[1], HW, HD), post(t[0], -HW, HD)),
        # index bottom -> t0 back
        'hull() {%s%s%s%s}' % (post(b, -HW, -HD), post(b, HW, -HD),
                               post(t[0], -HW, HD), post(t[0], HW, HD)),
    ]
    return out
