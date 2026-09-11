# Geometry validation

Validated with Python 3.14.7, Manifold 3.5.3, and independent OpenSCAD 2021.01
STL re-import checks on macOS. CI also runs the build on Python 3.10 and 3.14.

## Screw-cutout repair

The original vertical counterbores broke through several sloping webs, leaving
missing portions of the screw-head bearing surface. The repair adds explicit
flat pads (radius 3.3 mm, 3.4 mm thick) around the 3.4 mm shaft clearances,
while preserving the 6 mm counterbores. Heads sit 0.4 mm lower than before.
Matching base columns are revolved as single solids and stop 0.15 mm below
each pad underside, with blind
pilot bores leaving at least 1 mm of base material.

Plate/web joins are inset 0.1 mm from plate edges and 0.02 mm from their upper
and lower faces to avoid coincident face remnants. Clip relief cuts extend
below the plate instead of ending exactly on its lower face. A 0.05 mm
clearance envelope removes small intrusions into the modeled switch volume.

The v4 build uses Manifold on the same literal geometry that it writes to
SCAD, then validates the serialized binary STL files. This avoids the fragile
CGAL export path in OpenSCAD 2021.01; see the upstream
[quantization discussion](https://github.com/openscad/openscad/issues/4969).
OpenSCAD remains useful for viewing the generated SCAD and independently
checking the final STL geometry.

## Required checks

- No OBB collisions in the default 29-key layout.
- Every printed STL has two consistently oriented incident faces per edge,
  no degenerate triangles, and the expected component count: two for the
  assembled top, one each for the base and the individual print files.
- All seven screw shafts are open. At three radii and 64 angles per radius,
  each bearing ring has a flat upper seat and at least 1.5 mm of material.
- Column-top probes match each pad underside with a 0.15 mm gap.
- Top/switch, base/switch, top/base, and all seven screw-head/switch
  intersections are empty. These checks use the serialized meshes.
- The three print files rest at Z=0. The finger sheet and pod retain the
  selected −90° rotation about Y.
- The offline viewer rebuilds from the current example meshes and exposes
  the top and base independently. Five obsolete v1/v3 STL files were removed.

## Remaining limitations

The print-orientation heuristic reports one unresolved finger-sheet patch
(approximately 810 mm²). These geometric checks do not establish physical
print quality, comfort, strength, or assembly fit with real hardware.
Electronics mounting and the v4 wrist rest remain unfinished.

Personal hand analysis remains excluded, and the release retains the
three.js license notice and fully offline viewer resources.
