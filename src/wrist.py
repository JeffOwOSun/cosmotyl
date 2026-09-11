"""Wrist rest — conformal pad in front of the finger well (step 8).

Footprint: the back edge traces the case silhouette's lower (front) envelope
offset by WRIST.clearance, spanning from the middle-column line to the case's
right edge; sides taper inward toward a straight front edge `extension` mm
ahead of the case. The top is a plane tilted by slope (about x) and tenting
(about y); the rim is rounded by minkowski with a sphere after shrinking the
footprint, and a floor slab keeps the bottom flat at z=0 for printing.
"""
import math

from bottom import _dedupe, _uncross
from config import WRIST


def _lower_envelope(poly, x, pad=1.5):
    """Min boundary y of the (closed) polygon over the window [x-pad, x+pad]."""
    ys = []
    n = len(poly)
    for xs in (x - pad, x, x + pad):
        for i in range(n):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
            if (x1 <= xs <= x2) or (x2 <= xs <= x1):
                if abs(x2 - x1) < 1e-9:
                    ys.extend([y1, y2])
                else:
                    t = (xs - x1) / (x2 - x1)
                    ys.append(y1 + t * (y2 - y1))
    return min(ys) if ys else None


def footprint(layout, feet):
    """Pad outline (CCW) + the back polyline for clearance verification."""
    poly = _uncross(_dedupe(feet))
    # Left limit: boundary line between index and middle columns.
    ix = layout.key_position(1, 2)[0]
    mx = layout.key_position(2, 2)[0]
    x_left = (ix + mx) / 2
    x_max = min(max(p[0] for p in poly), x_left + WRIST.max_width)
    # Scan the lower envelope; the pad must stop where the case front ends
    # (the silhouette rises steeply around the front-right corner).
    xs = [x_left + i * 2.0 for i in range(int((x_max - x_left) / 2.0) + 1)]
    env = [(x, _lower_envelope(poly, x)) for x in xs]
    env = [(x, y) for x, y in env if y is not None]
    y_min = min(y for _, y in env)
    x_right = max(x for x, y in env if y <= y_min + 12.0)
    back = [(x, y - WRIST.clearance - 0.25)
            for x, y in env if x <= x_right and y <= y_min + 12.0]
    y_front = min(y for _, y in back) - WRIST.extension
    t = WRIST.extension * math.tan(math.radians(WRIST.taper))
    outline = back + [(x_right - t, y_front), (x_left + t, y_front)]
    return outline, back


def wrist_scad(layout, feet):
    outline, back = footprint(layout, feet)
    r = WRIST.round
    xl, yb = back[0]
    poly = ', '.join(f'[{x:.2f},{y:.2f}]' for x, y in outline)
    return f'''// Wrist rest (right half): conformal pad, flat bottom at z=0.
$fn = 32;
intersection() {{
  minkowski() {{
    intersection() {{
      linear_extrude(80) offset(r={-r}) polygon([{poly}]);
      // top plane: height at back-left corner, slope about x, tenting about y
      translate([{xl:.2f},{yb:.2f},{WRIST.height - r}])
        rotate([{WRIST.slope},{WRIST.tenting},0])
          translate([0,0,-500]) cube(1000, center=true);
    }}
    sphere({r}, $fn=20);
  }}
  translate([-200,-300,0]) cube([600,600,200]);  // flat printable bottom
}}
'''


def verify_clearance(feet, back):
    """Min horizontal gap from the pad's back edge to the case silhouette."""
    poly = _uncross(_dedupe(feet))
    n = len(poly)

    def seg_dist(p, a, b):
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))

    return min(seg_dist(p, poly[i], poly[(i + 1) % n])
               for p in back for i in range(n))
