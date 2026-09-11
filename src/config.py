"""Design-as-data for the Cosmotyl keywell generator.

All dimensions mm, angles deg. Z-up world frame, right half canonical:
+x toward pinky, -y toward the user, +z up. See keywell_generator_design.md.

Provenance tags: [U] scan-derived example design values,
[C] Cosmos internals, [M] dactyl-manuform, [D] dometyl.
"""
from dataclasses import dataclass


@dataclass
class Column:
    name: str
    x: float        # spread along +x [U scan, incl. anti-collision widening]
    y: float        # front-back stagger; -y = toward user [U scan]
    splay: float    # deg about +z, cluster-origin cumulative fan [C]
    travel: float   # scanned finger travel driving the bowl radius [U]
    rows: int = 4   # number of rows in this column


# gen_case.py COLS converted: y_world = -z_design, z-offset comes from travel.
COLUMNS = [
    Column('inner',  x=0.0,   y=-9.8,  splay=10.7,  travel=37.1),
    Column('index',  x=21.7,  y=-4.3,  splay=4.0,   travel=33.8),
    Column('middle', x=42.6,  y=0.0,   splay=0.0,   travel=53.1, rows=5),
    Column('ring',   x=63.0,  y=-2.4,  splay=-1.5,  travel=47.8, rows=5),
    Column('pinky',  x=85.7,  y=-15.2, splay=-11.4, travel=43.2),
    Column('outer',  x=104.7, y=-18.8, splay=-11.4, travel=43.2),
]

HOME_ROW = 2
PITCH = 18.5            # arc chord at socket top [U]
CAP_CLEAR_PITCH = 18.9  # required chord at cap base, 7mm above socket [U]
CAP_BASE_H = 7.0        # cap-base measurement height above socket top [U]

# Column height drop: longer travel -> deeper bowl floor. [U gen_case base_y]
def column_z(travel):
    return -(travel - 34.0) * 0.3

# Bowl radius from scanned travel, clamped. [U gen_case radius_for]
def column_radius(travel):
    return min(75.0, max(55.0, travel * 1.4))


@dataclass
class Thumb:
    """Anchored thumb pod: origin = corner of inner-column bottom key + offset [M].

    Seeded from the decoded Cosmos Curved pose + accepted (-4,-6,0) nudge, then
    pushed forward so the pod's back edge clears the well lip: our compact well
    (22.6 deg row arc vs Cosmos 15) puts the lip ~15mm closer to home row, and a
    tucked-under pod forces the seam sheet to roof the thumb caps."""
    anchor_col: int = 0
    offset: tuple = (16.8, -9.3, -20.8)
    # Euler seed from the accepted Cosmos Curved-3 pose (Rz*Ry*Rx order) [C]
    yaw: float = 34.4
    roll: float = -24.8
    pitch: float = -11.9
    keys: int = 3
    key_pitch: float = -20.0               # -x local: away from palm, descending
    # v2 fan-arc model (thumb_placement_models.md §8): keys on a planar circular
    # arc about the CMC pivot at local (0, -arc_R, 0) (wrist side), tangent-aligned.
    model: str = 'arc'                     # 'arc' | 'line'
    arc_R: float = 85.0                    # mm, bounded [70, 100] by scan sagitta
    arc_pitch: float = 21.2                # chord per key (dometyl: 21.1 at R=85);
                                           # 20.0 collides caps at 13.5 deg/key
    arc_cup: float = 0.0                   # deg/key roll about tangent (dome cup)


@dataclass
class Case:
    tent: float = 12.0            # deg, canonical [U]
    slope: float = 0.0            # backward rotation, deg about x
    lift_clearance: float = 8.0   # min interior height after lift [U]
    key_w: float = 19.0           # socket plate square (draw size) [U]
    key_d: float = 18.5
    plate_t: float = 4.7          # web/socket thickness [C]
    mx_hole: float = 14.15        # MX cutout w/ print shrink [U]
    clip_undercut: float = 1.4    # keycap clip ledge widening [U]
    skirt_t: float = 2.0          # ruled-loft support skirt [U]
    bottom_t: float = 2.5         # bottom plate [D->thicker]
    insert_bore: float = 4.0      # M3 heat insert
    insert_boss: float = 8.0
    insert_boss_h: float = 6.0
    cap_top: float = 16.1         # MX 6.2 + XDA 9.9 [C], for cap models


@dataclass
class Battery:
    """EEMB LP603449 drives the pocket; 522332 fits the same pocket. [U]"""
    l: float = 50.0
    w: float = 35.0
    h: float = 6.5


@dataclass
class Wrist:
    extension: float = 80.0   # [C]
    taper: float = 10.0       # deg [C]
    max_width: float = 100.0  # [C]
    slope: float = 5.0        # deg [C]
    tenting: float = 6.0      # deg [C]
    clearance: float = 1.0    # pad<->case gap [U]
    height: float = 22.0      # top surface at back-left (thumb-side) corner
    round: float = 3.0        # top-rim roundover radius


THUMB = Thumb()
CASE = Case()
BATTERY = Battery()
WRIST = Wrist()
