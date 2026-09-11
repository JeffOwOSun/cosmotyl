"""Devtool: full keyswitch + XDA keycap + travel envelope models [not printed].

Purpose: (a) show the real occupied volume in the viewer, (b) act as a hard
interference gate — intersection(devtool, case) must be empty, because the
case (plates with holes cut, webs, skirt) must never enter the volume a
switch or a moving keycap needs. MX numbers: flange sits on the plate top
(key-frame z=0); upper housing 15.6 sq x 6.2 tall; lower housing 14 sq x 5.5
below plate top plus 3.3 mm pins. XDA cap: 18.2 sq base at z=6.2 unpressed,
14.5 sq top at z=16.1; 4 mm travel drops the base to z=2.2, so the envelope
frustum spans z=2.2..16.1.
"""
from config import CASE, COLUMNS
from transform import scad_mat


def _frustum(m, w1, z1, w2, z2):
    """Hull of two thin square slabs in the key frame = conservative frustum."""
    return ('multmatrix(%s) hull() {'
            'translate([0,0,%.2f]) cube([%.2f,%.2f,0.1], center=true);'
            'translate([0,0,%.2f]) cube([%.2f,%.2f,0.1], center=true);}'
            % (scad_mat(m), z1, w1, w1, z2, w2, w2))


def _box(m, w, d, z1, z2):
    return ('multmatrix(%s) translate([0,0,%.2f]) '
            'cube([%.2f,%.2f,%.2f], center=true);'
            % (scad_mat(m), (z1 + z2) / 2, w, d, abs(z2 - z1)))


def key_devtool(m, clearance=0.0):
    e = clearance
    return [
        _frustum(m, 18.2 + 2*e, 2.2 - e, 14.5 + 2*e, 16.1 + e),      # XDA cap incl. 4mm travel
        _box(m, 15.6 + 2*e, 15.6 + 2*e, -e, 6.2 + e),           # upper housing
        _box(m, 14.0 + 2*e, 14.0 + 2*e, -CASE.plate_t - 0.8 - e, e),  # lower housing
        _box(m, 4.0 + 2*e, 4.0 + 2*e, -CASE.plate_t - 4.1 - e, -CASE.plate_t - 0.8 + e),  # pins
    ]


def devtool_scad(layout, clearance=0.0):
    solids = []
    for _, m in layout.items():
        solids += key_devtool(m, clearance)
    return ('// Devtool: switches + XDA caps + travel envelopes (NOT printed).\n'
            'union() {\n' + '\n'.join(solids) + '\n}\n')


def interference_scad(layout):
    """Empty result = case never intrudes into switch/cap volumes."""
    return ('// Interference check: must render to an EMPTY mesh.\n'
            'intersection() {\n'
            '  import("case_right.stl");\n'
            '  import("devtool_right.stl");\n'
            '}\n')
