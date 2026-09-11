"""Regression checks against the delivered print files, not just source strings."""

import contextlib
import importlib.util
import io
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import CASE
from main4 import HEAD_CLEARANCE, HEAD_H, SEAT_DROP, SEAT_GAP, column_pts
from mesh_audit import screw_seats, topology, vertical_hits
from placement import Layout
from stl_io import read_stl


class PrintedMeshes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meshes = {
            name: read_stl(ROOT / "output" / f"{name}.stl")
            for name in (
                "top4_right",
                "base4_right",
                "top4_print_board",
                "top4_print_pod",
            )
        }
        cls.sites = column_pts(Layout())

    def test_closed_consistently_wound_parts(self):
        for name, triangles in self.meshes.items():
            with self.subTest(name=name):
                self.assertEqual(
                    len(topology(triangles)), 2 if name == "top4_right" else 1
                )

    def test_all_seven_seats_have_material_and_clear_shafts(self):
        self.assertEqual(len(self.sites), 7)
        screw_seats(
            self.meshes["top4_right"],
            self.sites,
            plate_thickness=CASE.plate_t,
            head_height=HEAD_H + HEAD_CLEARANCE,
        )

    def test_column_tops_meet_bearing_pads_with_gap(self):
        for tag, x, y, z in self.sites:
            for k in range(16):
                a = math.tau * k / 16
                hits = vertical_hits(
                    self.meshes["base4_right"],
                    x + 2.5 * math.cos(a),
                    y + 2.5 * math.sin(a),
                )
                with self.subTest(site=tag, sample=k):
                    self.assertTrue(hits)
                    self.assertAlmostEqual(
                        hits[-1], z - SEAT_DROP - SEAT_GAP, delta=0.002
                    )

    def test_print_parts_rest_on_bed(self):
        for name in ("top4_print_board", "top4_print_pod", "base4_right"):
            self.assertAlmostEqual(
                min(v[2] for t in self.meshes[name] for v in t), 0, delta=1e-5
            )

    def test_topology_rejects_missing_or_reversed_face(self):
        part = self.meshes["top4_print_pod"]
        with self.assertRaises(ValueError):
            topology(part[1:])
        with self.assertRaises(ValueError):
            topology([tuple(reversed(part[0])), *part[1:]])


@unittest.skipUnless(
    importlib.util.find_spec("manifold3d"), "install requirements.txt for solid checks"
)
class SolidChecks(unittest.TestCase):
    def test_published_assembly_and_switch_clearances(self):
        import manifold3d as md

        from mesh_backend import load_mesh, require_empty

        top = load_mesh(ROOT / "output/top4_right.stl")
        base = load_mesh(ROOT / "output/base4_right.stl")
        dev = load_mesh(ROOT / "output/devtool_right.stl")
        with contextlib.redirect_stdout(io.StringIO()):
            require_empty(top, base, "assembly")
            require_empty(top, dev, "top")
            require_empty(base, dev, "base")
            for tag, x, y, z in column_pts(Layout()):
                head = md.Manifold.cylinder(
                    HEAD_H, 2.8, circular_segments=64
                ).translate((x, y, z + CASE.plate_t - HEAD_H - HEAD_CLEARANCE))
                require_empty(head, dev, tag)

    def test_backend_nested_transforms_and_boolean_cut(self):
        from mesh_backend import Parser, evaluate

        solid = evaluate(
            Parser(
                "difference() { translate([2,3,4]) cube([4,4,4]); "
                "translate([3,4,3]) cube([2,2,6]); }"
            ).node()
        )
        self.assertAlmostEqual(solid.volume(), 48)
        self.assertEqual(tuple(solid.bounding_box()), (2, 3, 4, 6, 7, 8))

    def test_backend_rejects_unsupported_geometry(self):
        from mesh_backend import Parser, evaluate

        with self.assertRaises(RuntimeError):
            evaluate(Parser("sphere(r=1);").node())
