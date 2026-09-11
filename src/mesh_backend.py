"""Evaluate the literal CSG subset emitted by main4 using Manifold.

OpenSCAD 2021's CGAL export/re-import path loses topology at nearly coplanar
plate lofts. Both SCAD and the mesh build consume the same generated geometry;
this evaluator supports only its literal primitives and fails on unknown ops.
It does not execute arbitrary OpenSCAD code. Angles and dimensions are already
resolved by the Python generator before parsing.
"""

import ast
import re
from pathlib import Path

import manifold3d as md
import numpy as np


class Parser:
    def __init__(self, s):
        self.tokens = re.findall(
            r'"[^"\\]*(?:\\.[^"\\]*)*"|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?|[$\w]+|[^\s]',
            re.sub(r"//[^\n]*", "", s),
        )
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, t=None):
        v = self.tokens[self.i]
        self.i += 1
        if t is not None and v != t:
            raise ValueError(f"Expected {t}, found {v}")
        return v

    def value(self):
        if self.peek() == "[":
            self.take()
            a = []
            while self.peek() != "]":
                a.append(self.value())
                if self.peek() != "]":
                    self.take(",")
            self.take("]")
            return a
        t = self.take()
        if t in ("true", "false", "undef"):
            return {"true": True, "false": False, "undef": None}[t]
        return ast.literal_eval(t)

    def node(self):
        op = self.take()
        self.take("(")
        args = []
        kw = {}
        while self.peek() != ")":
            if self.tokens[self.i + 1] == "=":
                key = self.take()
                self.take("=")
                kw[key] = self.value()
            else:
                args.append(self.value())
            if self.peek() != ")":
                self.take(",")
        self.take(")")
        children = []
        if self.peek() == ";":
            self.take()
        elif self.peek() == "{":
            self.take()
            while self.peek() != "}":
                children.append(self.node())
            self.take("}")
        else:
            children = [self.node()]
        return op, args, kw, children


def evaluate(n):
    op, a, k, children = n
    cs = [evaluate(c) for c in children]
    if op in ("union", "group"):
        return md.Manifold.batch_boolean(cs, md.OpType.Add)
    if op == "difference":
        return md.Manifold.batch_boolean(cs, md.OpType.Subtract)
    if op == "intersection":
        return md.Manifold.batch_boolean(cs, md.OpType.Intersect)
    if op == "hull":
        return md.Manifold.batch_hull(cs)
    if op == "multmatrix":
        return cs[0].transform(a[0][:3])
    if op == "translate":
        return cs[0].translate(a[0])
    if op == "cube":
        return md.Manifold.cube(
            k.get("size", a[0] if a else None), k.get("center", False)
        )
    if op == "cylinder":
        return md.Manifold.cylinder(
            k["h"],
            k.get("r", k.get("r1")),
            k.get("r", k.get("r2", -1)),
            int(k.get("$fn", 32)),
            k.get("center", False),
        )
    if op == "polygon":
        return md.CrossSection([k.get("points", a[0] if a else None)])
    if op == "offset":
        return cs[0].offset(k["r"], circular_segments=32)
    if op == "rotate_extrude":
        return cs[0].revolve(circular_segments=int(k.get("$fn", 32)))
    if op == "linear_extrude":
        return cs[0].extrude(k.get("height", a[0] if a else None))
    raise RuntimeError(op)


def load_mesh(path):
    from mesh_audit import topology
    from stl_io import read_stl

    tris = read_stl(path)
    topology(tris)
    vertices, index, faces = [], {}, []
    for tri in tris:
        face = []
        for v in tri:
            if v not in index:
                index[v] = len(vertices)
                vertices.append(v)
            face.append(index[v])
        faces.append(face)
    solid = md.Manifold(
        md.Mesh(
            np.asarray(vertices, dtype=np.float32), np.asarray(faces, dtype=np.uint32)
        )
    )
    if solid.status() != md.Error.NoError:
        raise ValueError(f"Invalid solid: {path}: {solid.status()}")
    return solid


def render_mesh(scad, stl):
    from mesh_audit import topology
    from stl_io import read_stl, write_stl

    parser = Parser(Path(scad).read_text())
    solid = evaluate(parser.node())
    if parser.peek() is not None:
        raise ValueError("Unexpected extra geometry after root CSG node")
    if solid.status() != md.Error.NoError or solid.is_empty():
        raise ValueError(f"Invalid or empty geometry: {scad}: {solid.status()}")
    # Remove numerical remnants far below manufacturing resolution. Topology is
    # checked again after float32 STL serialization, not just in memory.
    mesh = solid.simplify(1e-5).to_mesh()
    tris = [
        tuple(tuple(float(c) for c in mesh.vert_properties[i, :3]) for i in f)
        for f in mesh.tri_verts
    ]
    write_stl(stl, tris)
    parts = topology(read_stl(stl))
    print(f"{stl}: {len(tris)} triangles, {len(parts)} closed component(s)")
    return load_mesh(stl)


def require_empty(a, b, label):
    result = a ^ b
    if result.status() != md.Error.NoError or not result.is_empty():
        raise ValueError(f"{label}: nonempty intersection ({result.volume():.9g} mm3)")
    print(f"{label}: CLEAN (empty intersection)")
