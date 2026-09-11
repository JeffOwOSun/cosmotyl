# Keywell Generator — Architecture & Design

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


A standalone Python → OpenSCAD procedural generator for the Cosmotyl split keyboard,
replacing Cosmos (whose rounded walls + wrist-rest solid are PRO-locked). Design follows
your 8-step pipeline, with every default traced to a source: **[C]** Cosmos internals
([cosmos_internals.md](research/cosmos_internals.md)),
**[M]** Dactyl Manuform, **[D]** Dometyl
([generator_patterns.md](research/generator_patterns.md)),
**[U]** our scan/collision-verified values
(gen_case.py (historical artifact, not included)).

## Core architectural decisions

1. **Stack**: Python emitting OpenSCAD (like your Clojure→scad experience; OpenSCAD is
   already installed and `gen_case.py` proves the workflow). Pure-functional style:
   placement math returns 4×4 matrices; solids are emitted separately.
2. **The one non-negotiable pattern — place/position duality [M]**: a single function
   `key_frame(col, row) -> Mat4` feeds BOTH solid placement and point queries
   (`key_position(col, row, local_pt) -> Vec3`). Thumb anchor, screw sites, wall starts,
   wrist footprint, USB port — all consume this one function, never re-derive. This is
   manuform's `apply-key-geometry` trick and the reason its thumb follows the well
   automatically.
3. **Coordinates [C]**: mm, degrees, **Z-up**, right-handed; key local frame +Z out of
   the cap; each key frame lands at **socket top center**. Right half canonical, left =
   mirror. (This drops gen_case.py's y-up design frame — one frame end to end, no
   rotate([90,0,0]) at the tail.)
4. **Hollow shell (Charybdis-style)**: NO vertical extrusion of the keywell perimeter.
   The case = thin web shell (thickness ≈ socket height) + swept perimeter walls only
   where structurally needed + interior pillars that double as heat-insert bosses.
5. **Rich intermediate results [D]**: each stage returns geometry + metadata (wall foot
   quads, continuous `outline`/`inline` ground paths). The bottom plate and wrist rest
   are then ~10-line consumers of the outline — never modeled independently.

## The 8-step pipeline, concretely

### 1. Ground the home row
World origin = home-row key of the **middle column**, socket top center, cap facing +Z.
Every other key is placed relative to this. (Cosmos centers on `centerRow = nRows-3`,
same idea [C§1]; manuform `centerrow = nrows-3` [M].)

### 2. Grow the fingers cluster
Per-column dataclass `Column{name, offset(x,y,z), splay, radius_or_travel, rows}` —
layout-as-data, dometyl `Lookups` style [D§7.2]. Placement for key (c, r):

```
key_frame(c,r) = Splay_c · T(offset_c) · ArcRow(r - home_row)
ArcRow(k):  R_c = clamp(1.4·travel_c, 55, 75)            [U, scan-derived]
            Δθ_c = max(18.5/R_c, 18.9/(R_c - 7))          [U, collision-verified]
            rotate -k·Δθ_c about X through [0, 0, R_cap], R_cap = R_c + cap_top
```

- Pivot about the **finger-contact sphere** (`+ cap_top` on the radius): cap_top = 6.2
  (MX unpressed) + 9.9 (XDA) ≈ 16.1 mm [C§2] (Clojure uses plate 4 + SA 12.7 = 16.7 [M]).
- **Splay rotates about the cluster origin** (cumulative γ), not the column's own axis
  [C§2] — this is what Cosmos does and what our `inject_splay.py` already encodes.
  Values: +10.7 / +4 / 0 / −1.5 / −11.4 / −11.4 (non-negotiable).
- Column staggers from your hand scan (gen_case.py L9-16 table, re-expressed in Z-up).
- Row curvature is per-column via `Δθ_c` (deeper bowl for longer fingers), replacing
  fixed α=15°; no cross-column arc — columns are placed by offset+splay like [U]/[D],
  not on a second sphere.

### 3. Grow the thumb cluster (pointing into the ground is fine)
Anchor **through the pipeline** [M§2.2], never absolute:

```
thumb_origin = key_position(inner_col, bottom_row, [+w/2, -h/2, 0]) + tuned_offset
thumb_frame(i) = T(thumb_origin) · Rz(yaw) · Ry(roll) · Rx(pitch) · T(key_i_offset)
```

Seed pose = the Cosmos Curved-3 pose we already ship, converted into this anchored form
(Cosmos values: (−35.78, −25.67, −7.08) mm / (−11.9°, −24.8°, 34.4°) [C§3], plus our
(−4, −6, 0) nudge). 2 keys initially (matching the accepted design), sculpt table
available for more.

### 4. Orient: tenting + backward rotation — applied ONCE
`Orient = T(0,0,lift) · Ry(-tent) · Rx(-slope)` applied at the single tail of
`key_frame` [M§6], so every point query inherits it. `tent = 12°` canonical.
`lift` is **computed**: scan all socket/cap corner points, `lift = clearance − min_z`
[D§6] — no magic z constants. Unlike Cosmos, the thumb is anchored (step 3), so
re-tenting moves it correctly for free — fixing Cosmos's tent-slider-ignores-thumb wart.

### 5. Thin shell: curved plate + minimal lofted skirt (NO walls) — per your call
- **Web (the case itself)**: 0.1 mm corner posts + triangle-hulls between
  row/col/diagonal neighbors [M§3] (gen_case.py already does this); thickness = socket
  height 4.7 mm [C§7], top flush with socket top. The doubly-curved 4.7 mm plate is the
  structural shell — no perimeter walls, no vertical extrusion of the keywell.
- **Support skirt**: a thin ruled loft from the plate's boundary edge straight down to
  the z=0 construction plane — each boundary edge segment hulled with its own floor
  projection (this degenerates dometyl's bezier sweep to d1=d2=0; the foot outline
  falls out for free). Thickness 2 mm; its only jobs are (a) a flat printable rim,
  (b) carrying the USB-C slot, (c) hosting the insert bosses, (d) hiding electronics.
  Boundary detection: flat-project socket corners → concave hull [C§6], or directly the
  known edge list from the grid (gen_case.py `boundary_edges`).
- **Pillars**: vertical struts from web underside to floor at the heat-insert sites
  (step 6) + under the thumb pod — pillars ARE the bosses, no separate ribs.
- **Rounded top edge**: with no wall band, this reduces to rounding the plate's exposed
  boundary edge — chamfer/roundover ring swept along the boundary loop (cheap,
  printable, no minkowski of the whole solid).
- **Thumb↔body seam**: explicit configurable link (universal hard part [D§7-pitfalls]);
  v1 = triangle-hull bridge like gen_case.py L169-174, kept as its own module; the
  thumb pod gets its own skirt loft to the same plane.

### 6. Bottom plate — a projection, aligned by construction
`plate = linear_extrude(2.5) polygon(outline_2d)` where `outline_2d` = the skirt's foot
outline recorded in step 5 (dometyl `Connect.outline` [D§5.3]; equivalently manuform's
`cut` at z≈0 [M§5.2]). Heat-insert bosses (M3: bore Ø4.0 for insert, boss Ø8, h 6)
placed along the skirt's inner foot path; the plate's screw holes reuse the **same site
list** — alignment is guaranteed because both consume one data structure. 5 sites:
back-left, back-right, front-right, front-middle, thumb-side. (Resolved: 5× M3 heat
inserts, per your OK.)

### 7. Electronics in the BASE, not the shell
- **XIAO nRF52840** bay: PCB 21×17.8×3.4 (+USB-C overhang ≈1.3); printed rails on the
  bottom plate hold it; USB-C slot (9.5×3.6, chamfered) cut through the back skirt at a
  height computed from `key_position` of the back boundary edge — one port per half,
  no TRRS (your accepted design).
- **Battery** pocket sized for your actual cells (screenshots): **EEMB LP603449
  49×34×6.0 mm 1100 mAh** (design driver) and **522332 32×22×5.2 mm 400 mAh** (fits the
  same pocket). Pocket 50×35×6.5 with a strap bar + JST-PH 2.0 pigtail channel,
  positioned under the middle-column web where step-2 clearance analysis
  (gen_case.py L108-132 shows ≥ bay height) says it fits.
- Both live on the bottom plate → swap/repair without reprinting the shell.

### 8. Wrist rests — with real clearance
Port Cosmos's OPEN footprint algorithm [C§5]: case-side edge from actual wall outline
points, front edge = `min_y + extension (80 mm)`, taper 10°, maxWidth 100. Then the two
things Cosmos can't do:
- **`clearance` parameter = 1.0 mm**: offset the case-side edge away from the case along
  the local outline normal before building the solid — pad drops in/out freely.
- Solid generation ourselves (PRO in Cosmos): extrude footprint, apply slope 5° + WR
  tent 6° [C§5 defaults], `minkowski` a small sphere on the top face for the rounded
  comfortable edge, flat bottom.
- Pad ends at the **middle-column line** (your earlier requirement), position seeded
  from the accepted (+52, 0, −18) offset.

## Defaults table (provenance-tagged)

| Parameter | Value | Src |
|---|---|---|
| Key pitch (row, arc chord) | 18.5 mm | U |
| Cap-base clearance rule | Δθ = max(18.5/R, 18.9/(R−7)) | U |
| Column radius | clamp(1.4·travel, 55, 75) | U |
| cap_top (MX + XDA) | 6.2 + 9.9 = 16.1 mm | C |
| Splay (inner→outer) | +10.7, +4, 0, −1.5, −11.4, −11.4 | U |
| Tent / lift clearance | 12° / computed, ≥ 8 mm interior | U |
| MX cutout | 14.15 mm (print shrink) + 1.4 mm clip undercut | U |
| Socket (plate) size | 18×18, height 4.7 mm | C |
| Web thickness | = socket height (4.7) | C |
| Skirt thickness | 2 mm (ruled loft, boundary → z=0) | you |
| Boundary edge roundover | r 1.5 mm ring along boundary loop | D (adapted) |
| Bottom plate | 2.5 mm | D (1.65) → thicker for bays |
| Heat inserts | M3, bore Ø4.0, boss Ø8×6; 5 sites | M/C, OK'd |
| Battery pocket | 50×35×6.5 (LP603449; 522332 fits) | you |
| Wrist ext / taper / maxW / slope / WR tent | 80 mm / 10° / 100 mm / 5° / 6° | C |
| **Wrist↔case clearance** | **1.0 mm** | **you** |

## Module layout (`scratch/keywell/`)

```
config.py      # dataclasses: Column, Thumb, Case, Wrist — the whole design as data
transform.py   # Mat4 helpers (from gen_case.py), frame composition
placement.py   # key_frame / key_position / thumb_frame + lift computation
verify.py      # OBB keycap collision (ported), bay clearance, skirt-foot sanity
web.py         # posts + triangle-hulls
skirt.py       # ruled loft boundary→plane, foot outline, edge roundover
bottom.py      # plate from outline, bosses, screw holes
electronics.py # XIAO rails + USB slot + battery pocket
wrist.py       # footprint + clearance offset + solid
emit.py        # SCAD emission; scene = union of parts
main.py        # build right half, mirror left, render STLs, run verify
```

## Verification plan (each iteration)

1. `verify.py` gates: 0 keycap OBB collisions; bay clearances ≥ spec; every skirt foot
   lands at z=0; outline is simple (no self-intersections).
2. `openscad -o` renders both halves + plate + wrist → STLs into the working directory.
3. Rebuild the three.js viewer from the new STLs (existing `gen_cosmos_viewer.py`
   pipeline) → visual check with screenshots, including the 1 mm wrist gap measured on
   a cross-section (existing junction-section tool).

## Resolved decisions (2026-09-10)

1. **Shell style**: NO walls — curved plate + minimal 2 mm skirt lofted to the z=0
   construction plane, purely for a flat printable bottom (your call).
2. **Fastening**: 5× M3 heat inserts, OK'd.
3. **Battery**: EEMB LP603449 (49×34×6.0, 1100 mAh) drives the pocket; 522332
   (32×22×5.2, 400 mAh) fits the same pocket (your screenshots).
