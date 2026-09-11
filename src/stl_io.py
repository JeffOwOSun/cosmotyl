"""Lossless-coordinate STL reads and explicit binary STL writes."""

import math
import struct
from pathlib import Path


def read_stl(path):
    data = Path(path).read_bytes()
    # A binary header may also start with 'solid'; validate its record length.
    if len(data) >= 84 and len(data) == 84 + 50 * struct.unpack_from("<I", data, 80)[0]:
        return [
            tuple(
                tuple(struct.unpack_from("<3f", data, offset + 12 + v * 12))
                for v in range(3)
            )
            for offset in range(84, len(data), 50)
        ]
    tris, vertices = [], []
    for line in data.decode("ascii").splitlines():
        words = line.split()
        if words[:1] == ["vertex"]:
            if len(words) != 4:
                raise ValueError("Malformed STL vertex")
            vertices.append(tuple(map(float, words[1:])))
            if len(vertices) == 3:
                tris.append(tuple(vertices))
                vertices = []
    if vertices or not tris:
        raise ValueError("Incomplete or empty STL")
    return tris


def write_stl(path, tris):
    with Path(path).open("wb") as f:
        f.write(b"Cosmotyl binary STL".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            n = (
                u[1] * v[2] - u[2] * v[1],
                u[2] * v[0] - u[0] * v[2],
                u[0] * v[1] - u[1] * v[0],
            )
            length = math.hypot(*n)
            if not length:
                raise ValueError("Cannot export a degenerate triangle")
            f.write(struct.pack("<12fH", *(x / length for x in n), *a, *b, *c, 0))
