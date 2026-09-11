"""Minimal 4x4 matrix helpers for the keywell generator.

Conventions: mm, degrees, Z-up, right-handed. A frame matrix M maps key-local
coordinates (X right/column direction, Y back/row direction, +Z out of the cap)
into world coordinates. Frames land at the SOCKET TOP CENTER of each key.
"""
import math


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def compose(*mats):
    m = mats[0]
    for n in mats[1:]:
        m = mat_mul(m, n)
    return m


def identity():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def T(x, y, z):
    return [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]


def RX(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]]


def RY(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]]


def RZ(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def rot_about(rot_mat, px, py, pz):
    """Rotation about an arbitrary pivot point."""
    return compose(T(px, py, pz), rot_mat, T(-px, -py, -pz))


def apply(m, v):
    x, y, z = v
    return tuple(m[i][0] * x + m[i][1] * y + m[i][2] * z + m[i][3] for i in range(3))


def axes_of(m):
    """Unit axes (columns) of the rotation part."""
    return [tuple(m[i][j] for i in range(3)) for j in range(3)]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def scad_mat(m):
    rows = ', '.join('[' + ', '.join(f'{m[i][j]:.5f}' for j in range(4)) + ']' for i in range(4))
    return f'[{rows}]'
