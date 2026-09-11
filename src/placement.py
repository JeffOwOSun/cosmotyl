"""Placement math: one function produces every frame; solids and point queries
both consume it (manuform's place/position duality).

key_frame(c, r)      -> world 4x4 (orientation applied)
key_position(c,r,pt) -> world point of a key-local point
thumb_frame(i)       -> world 4x4, anchored through the pipeline
"""
import math

from config import (CASE, COLUMNS, HOME_ROW, PITCH, CAP_CLEAR_PITCH, CAP_BASE_H,
                    THUMB, column_radius, column_z)
from transform import (T, RX, RY, RZ, apply, compose, rot_about, mat_mul)


def row_step(radius):
    """Angular row pitch (rad): socket chord >= PITCH and cap-base chord (7mm
    closer to the arc pivot) >= CAP_CLEAR_PITCH. [U collision-verified]"""
    return max(PITCH / radius, CAP_CLEAR_PITCH / (radius - CAP_BASE_H))


def _key_frame_raw(c, r):
    """Pre-orientation frame. Splay fans the column's ORIENTATION about the
    cluster origin (Cosmos semantics [C]), but the translation is solved so the
    home-row socket lands exactly on the scanned target — otherwise the splay
    lever arm would double-count the stagger already in the scan table. The
    row arc pivots about X through [0,0,R] above the socket top."""
    col = COLUMNS[c]
    R = column_radius(col.travel)
    th = -(r - HOME_ROW) * math.degrees(row_step(R))  # deg; -y rows advance toward user
    target = (col.x, col.y, column_z(col.travel))
    local = apply(RZ(-col.splay), target)
    return compose(
        RZ(col.splay),
        T(*local),
        rot_about(RX(th), 0, 0, R),
    )


def _thumb_frame_raw(i):
    """Anchored: origin follows the inner column's bottom key corner [M].

    'arc' model: key i = cluster frame rotated by θᵢ about the arc center at
    local (0, -R, 0) — the CMC pivot on the WRIST side (toward the user) — so
    its origin lands on C(θ) = (-R sinθ, R(cosθ-1), 0) with tangent-aligned
    orientation (dometyl fan; thumb_placement_models.md §8). θᵢ > 0 extends
    keys toward local -x while curling them back toward the wrist, matching
    the thumb tip sweeping about its base joint."""
    col = THUMB.anchor_col
    r = COLUMNS[col].rows - 1
    corner = apply(_key_frame_raw(col, r), (-CASE.key_w / 2, -CASE.key_d / 2, 0))
    ox, oy, oz = THUMB.offset
    cluster = compose(
        T(corner[0] + ox, corner[1] + oy, corner[2] + oz),
        RZ(THUMB.yaw), RY(THUMB.roll), RX(THUMB.pitch),
    )
    if THUMB.model == 'arc':
        th = i * math.degrees(THUMB.arc_pitch / THUMB.arc_R)
        step = mat_mul(rot_about(RZ(th), 0, -THUMB.arc_R, 0),
                       RX(THUMB.arc_cup * i))
    else:
        step = T(i * THUMB.key_pitch, 0, 0)
    return mat_mul(cluster, step)


def all_raw_frames():
    frames = [(('m', c, r), _key_frame_raw(c, r))
              for c, col in enumerate(COLUMNS) for r in range(col.rows)]
    frames += [(('t', i, 0), _thumb_frame_raw(i)) for i in range(THUMB.keys)]
    return frames


def _orient():
    """Tent + slope, applied once. +tent drops the pinky side (+x) [right half]."""
    return mat_mul(RX(CASE.slope), RY(CASE.tent))


def compute_lift(oriented_frames):
    """lift = clearance - min corner z over all sockets (dometyl's computed
    lift; no magic z constants)."""
    hw, hd = CASE.key_w / 2, CASE.key_d / 2
    lo = min(apply(m, (sx, sy, -CASE.plate_t))[2]
             for _, m in oriented_frames
             for sx in (-hw, hw) for sy in (-hd, hd))
    return CASE.lift_clearance - lo


class Layout:
    """All world frames with orientation + computed lift baked in."""

    def __init__(self):
        o = _orient()
        pre = [(k, mat_mul(o, m)) for k, m in all_raw_frames()]
        lift = compute_lift(pre)
        world = T(0, 0, lift)
        self.lift = lift
        self.frames = {k: mat_mul(world, m) for k, m in pre}

    def key_frame(self, c, r):
        return self.frames[('m', c, r)]

    def thumb_frame(self, i):
        return self.frames[('t', i, 0)]

    def key_position(self, c, r, pt=(0, 0, 0)):
        return apply(self.key_frame(c, r), pt)

    def items(self):
        return self.frames.items()
