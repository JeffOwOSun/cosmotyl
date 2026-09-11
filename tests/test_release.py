"""Regressions for build failures and STL parsing found during release review."""
import contextlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from render import render
from stl_components import read_stl
from placement import Layout
from verify import report


class ReleaseTests(unittest.TestCase):
    def test_binary_stl_vertices_and_last_record(self):
        # Binary headers may begin with 'solid'; the final record has no padding.
        data = b'solid binary'.ljust(80, b'\0') + struct.pack('<I', 1)
        data += struct.pack('<12fH', 0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'part.stl'
            p.write_bytes(data)
            self.assertEqual(read_stl(p), [[(1, 2, 3), (4, 5, 6), (7, 8, 9)]])

    def check_intersection(self, code, message, fails):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'old.stl'
            output.write_text('stale mesh')
            result = subprocess.CompletedProcess([], code, '', message)
            with patch('render.openscad', return_value='openscad'), \
                 patch('render.subprocess.run', return_value=result), \
                 contextlib.redirect_stdout(io.StringIO()):
                if fails:
                    with self.assertRaises(RuntimeError):
                        render('test.scad', output, expect_empty=True)
                else:
                    render('test.scad', output, expect_empty=True)
            self.assertFalse(output.exists())

    def test_empty_intersection_passes(self):
        self.check_intersection(1, 'Current top level object is empty.', False)

    def test_missing_import_does_not_pass_as_empty(self):
        self.check_intersection(1, 'WARNING: Cannot open import file\n'
                                'Current top level object is empty.', True)

    def test_renderer_failure_fails(self):
        self.check_intersection(1, 'render crashed', True)

    def test_nonempty_intersection_fails(self):
        self.check_intersection(0, 'Facets: 12', True)

    def test_default_layout(self):
        layout = Layout()
        self.assertEqual(len(list(layout.items())), 29)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(report(layout), 0)

    def test_inadequate_headroom_fails(self):
        with patch('verify.min_web_height', return_value=0), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertGreater(report(Layout()), 0)


if __name__ == '__main__':
    unittest.main()
