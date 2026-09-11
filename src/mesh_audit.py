"""Topology and vertical material probes for generated STL files (no dependencies)."""

import math
from collections import defaultdict


def topology(tris):
    """Reject open/nonmanifold edges, inconsistent winding, and zero-area faces.

    Return components joined by edges, preserving each triangle's coordinates.
    This checks combinatorial topology; Boolean re-import checks geometry too.
    """
    edges = defaultdict(list)
    for i, tri in enumerate(tris):
        a, b, c = tri
        u = tuple(b[j] - a[j] for j in range(3))
        v = tuple(c[j] - a[j] for j in range(3))
        cross = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        if len(set(map(tuple, tri))) != 3 or math.hypot(*cross) < 1e-12:
            raise ValueError(f"Degenerate triangle {i}")
        for a, b in zip(tri, (tri[1], tri[2], tri[0])):
            a, b = tuple(a), tuple(b)
            edges[tuple(sorted((a, b)))].append((i, a < b))
    parent = list(range(len(tris)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for edge, faces in edges.items():
        if len(faces) != 2 or faces[0][1] == faces[1][1]:
            raise ValueError(f"Open, nonmanifold, or inconsistently wound edge: {edge}")
        a, b = find(faces[0][0]), find(faces[1][0])
        parent[b] = a
    components = defaultdict(list)
    for i, tri in enumerate(tris):
        components[find(i)].append(tri)
    if not components:
        raise ValueError("Empty mesh")
    return sorted(components.values(), key=len, reverse=True)


def vertical_hits(tris, x, y):
    """Surface Z coordinates along a vertical line through XY."""
    hits = []
    for a, b, c in tris:
        if not (
            min(a[0], b[0], c[0]) - 1e-8 <= x <= max(a[0], b[0], c[0]) + 1e-8
            and min(a[1], b[1], c[1]) - 1e-8 <= y <= max(a[1], b[1], c[1]) + 1e-8
        ):
            continue
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12:
            continue
        u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / det
        v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / det
        w = 1 - u - v
        if min(u, v, w) >= -1e-7:
            hits.append(u * a[2] + v * b[2] + w * c[2])
    return sorted(hits)


def screw_seats(tris, sites, *, plate_thickness, head_height, minimum_floor=1.5):
    """Check the open shaft and an uninterrupted flat bearing ring at every site."""
    for tag, x, y, z in sites:
        seat = z + plate_thickness - head_height
        if vertical_hits(tris, x, y):
            raise ValueError(f"{tag}: screw shaft is obstructed")
        for radius in (1.85, 2.4, 2.85):
            for k in range(64):
                theta = math.tau * k / 64
                hits = vertical_hits(
                    tris, x + radius * math.cos(theta), y + radius * math.sin(theta)
                )
                if not hits or abs(hits[-1] - seat) > 0.002:
                    raise ValueError(
                        f"{tag}: incomplete or uneven screw seat at radius {radius}, sample {k}"
                    )
                if hits[-1] - hits[0] < minimum_floor - 0.002:
                    raise ValueError(f"{tag}: screw-seat floor is too thin")


def column_seats(tris, sites, *, pad_drop, gap):
    """Check that each column supports its bearing pad at the intended height."""
    for tag, x, y, z in sites:
        for k in range(32):
            theta = math.tau * k / 32
            hits = vertical_hits(
                tris, x + 2.5 * math.cos(theta), y + 2.5 * math.sin(theta)
            )
            if not hits or abs(hits[-1] - (z - pad_drop - gap)) > 0.002:
                raise ValueError(
                    f"{tag}: column does not meet the bearing-pad underside"
                )
