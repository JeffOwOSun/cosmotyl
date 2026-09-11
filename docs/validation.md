# Public release validation

Reviewed on 2026-09-10 with Python 3.14.7 and OpenSCAD 2021.01 on macOS.

## Passed

- Seven regression tests: binary STL vertex parsing, the default 29-key
  layout, sampled headroom rejection, and interference-check failure cases.
- SCAD generation for v1, v3, and v4 without requiring a renderer (`--fast`).
- Default keycap OBB check: zero collisions. Sampled bay heights: battery
  20.2 mm and controller 25.9 mm, compared with a 9.0 mm battery/base envelope.
- Offline viewer rebuilt and visually inspected; left-half toggle and
  separation slider exercised in a browser.
- Public file set scanned with Gitleaks 8.30.1: no secrets detected.
  Personal workstation links and personal hand analysis were removed.
  Included screenshots have no text or EXIF metadata chunks.
- Vendored three.js matched upstream r147 after removing surrounding
  whitespace; the repository now includes the exact upstream build and MIT
  notice. The generated viewer has no remote script dependency.

## Failed: v4 top sheet is not accepted as a closed STL solid

The full v4 build renders its top, base, and switch envelope, then OpenSCAD
reports this during the STL-based interference check:

```text
ERROR: The given mesh is not closed! Unable to convert to CGAL_Nef_Polyhedron.
Current top level object is empty.
```

An isolated re-import check identifies `top4_right.stl` as the affected mesh.
The switch-envelope STL converts successfully. The exact defect in the upper
sheet geometry has not yet been repaired. An empty intersection following a
conversion error provides no evidence of switch clearance.

The old gate accepted the “empty” message even after this error. The release
fix rejects warnings/errors before considering an empty intersection valid,
and exits nonzero instead of exporting new print parts after a failed check.
The prebuilt meshes in `output/` are retained from the earlier prototype;
they have not passed this corrected gate. The published viewer uses those
prebuilt meshes consistently.

## Remaining design work

Repair the top-sheet mesh and rerun the full interference and topology
checks. Then evaluate the two reported overhang patches, real hardware fit,
physical assembly, and printed parts. Electronics mounting and v4 wrist-rest
integration are also unfinished. CI checks Python behavior and SCAD/viewer
generation; it does not claim a successful full OpenSCAD render.
