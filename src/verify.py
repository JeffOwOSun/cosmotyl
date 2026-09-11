"""Verification gates. Run me: python3 verify.py

Gate 1: keycap OBB collision (3D SAT, frustum two-slab cap model) [U ported].
Gate 2: interior clearance under the web at the battery/XIAO bays.
Plus a frame report for eyeballing staggers/splay/tent.
"""
import math

from config import CASE, COLUMNS, BATTERY, THUMB
from placement import Layout
from transform import apply, axes_of, dot, cross


def cap_obbs(m):
    axes = axes_of(m)
    return [
        (apply(m, (0, 0, 6.6)), axes, (9.15, 9.15, 0.6)),   # cap base slab
        (apply(m, (0, 0, 12.8)), axes, (6.5, 6.5, 0.6)),    # cap top slab
    ]


def obb_overlap(A, B, margin=0.0):
    (ca, ax, ha), (cb, bx, hb) = A, B
    d = (cb[0] - ca[0], cb[1] - ca[1], cb[2] - ca[2])
    tests = list(ax) + list(bx) + [cross(u, v) for u in ax for v in bx]
    for L in tests:
        n = math.sqrt(dot(L, L))
        if n < 1e-6:
            continue
        L = (L[0] / n, L[1] / n, L[2] / n)
        ra = sum(h * abs(dot(L, u)) for h, u in zip(ha, ax))
        rb = sum(h * abs(dot(L, u)) for h, u in zip(hb, bx))
        if abs(dot(L, d)) > ra + rb + margin:
            return False
    return True


def check_collisions(layout):
    boxes = [(k, cap_obbs(m)) for k, m in layout.items()]
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (ka, A), (kb, B) = boxes[i], boxes[j]
            if any(obb_overlap(a, b) for a in A for b in B):
                bad.append((ka, kb))
    return bad


def min_web_height(layout, x0, y0, rad=25.0):
    """Lowest socket-underside z among keys whose center projects within rad
    of (x0, y0) — a conservative bay headroom probe."""
    best = None
    for _, m in layout.items():
        p = apply(m, (0, 0, -CASE.plate_t))
        if math.hypot(p[0] - x0, p[1] - y0) <= rad:
            best = p[2] if best is None else min(best, p[2])
    return best


def report(layout):
    print(f'lift = {layout.lift:.2f} mm  (interior clearance {CASE.lift_clearance})')
    print('\n--- home row world positions (socket top centers) ---')
    for c, col in enumerate(COLUMNS):
        x, y, z = layout.key_position(c, 2)
        print(f'{col.name:7s} ({x:7.2f}, {y:7.2f}, {z:6.2f})')
    print('\n--- thumb keys ---')
    for i in range(THUMB.keys):
        x, y, z = apply(layout.thumb_frame(i), (0, 0, 0))
        print(f'thumb{i}  ({x:7.2f}, {y:7.2f}, {z:6.2f})')

    bad = check_collisions(layout)
    print(f'\n--- keycap OBB collisions: {len(bad)} ---')
    for a, b in bad:
        print('COLLISION:', a, b)

    failures = len(bad)
    print('\n--- bay headroom (socket underside above floor) ---')
    for label, (x0, y0) in [('battery (under middle home)', tuple(layout.key_position(2, 2))[:2]),
                            ('xiao (back, index)', tuple(layout.key_position(1, 0))[:2])]:
        h = min_web_height(layout, x0, y0)
        need = BATTERY.h + CASE.bottom_t
        if h is None:
            print(f'{label}: no nearby geometry; cannot verify')
            failures += 1
        else:
            print(f'{label}: {h:.1f} mm  (battery+plate needs {need:.1f})')
            failures += int(h < need)
    return failures


if __name__ == '__main__':
    lay = Layout()
    raise SystemExit(1 if report(lay) else 0)
