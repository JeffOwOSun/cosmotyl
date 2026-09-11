# Procedural Keyboard Generator Patterns: Dactyl, Dactyl Manuform, Dometyl

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


Sources (all paths relative to `scratch/research/`):
- `dactyl-keyboard/src/dactyl_keyboard/dactyl.clj` (adereth original, 1266 lines, scad-clj)
- `dactyl-manuform/src/dactyl_keyboard/dactyl.clj` (tshort fork, 761 lines)
- `dometyl/lib/*.ml` (OCaml, OCADml/OSCADml)

## 1. KEY PLACEMENT PIPELINE

### 1.1 Shared constants (identical in both Clojure projects)
From `dactyl.clj` L12-19 / manuform L66-73:
- `keyswitch-width = keyswitch-height = 14.4` ("Was 14.1, then 14.25")
- `plate-thickness = 4`
- `mount-width = mount-height = keyswitch + 3 = 17.4`
- `sa-profile-key-height = 12.7`
- `cap-top-height = plate-thickness + sa-profile-key-height = 16.7` (dactyl L122, manuform L147)

Curvature defaults: `α = π/12` (15°, column-direction/row curvature, rotation about X), `β = π/36` (5°, row-direction/column curvature, rotation about Y) — dactyl L120-121, manuform L19-20 (comments: "curvature of the columns" / "curvature of the rows").

### 1.2 Radius formulas (the core "curved well" math)
The key sits on a circle whose radius is chosen so adjacent keycap tops just clear each other. Half the key pitch subtends half the step angle:

original dactyl (L123-128):
```
row-radius    = ((mount-height + 0.5)/2) / sin(α/2) + cap-top-height
              = 8.95/sin(7.5°) + 16.7  ≈ 68.57 + 16.7 ≈ 85.27 mm
column-radius = ((mount-width + 2.0)/2) / sin(β/2) + cap-top-height
              = 9.7/sin(2.5°) + 16.7   ≈ 222.38 + 16.7 ≈ 239.08 mm
```
The `+0.5` / `+2.0` are inter-key gap allowances. Manuform parametrizes them as `extra-height = 1.0`, `extra-width = 2.5` (L37-38) giving `row-radius ≈ 87.18`, `column-radius ≈ 244.81` (L148-153). The radius is measured to the **keycap top** (hence `+ cap-top-height`); the shape is translated down by the radius, rotated, translated back up — so rotation is about the cap-top arc centre, not the plate.

### 1.3 `key-place` transform order — original dactyl (`defn key-place`, L130-147)
For key at (column, row), applied to shape in this exact order:
1. `translate [0 0 -row-radius]`
2. `rotate (α * (2 - row)) [1 0 0]`   ← centre row hardcoded = 2
3. `translate [0 0 row-radius]`
4. `translate [0 0 -column-radius]`
5. `rotate (β * (2 - column)) [0 1 0]`  ← centre column hardcoded = 2
6. `translate [0 0 column-radius]`
7. `translate column-offset` — stagger table (L135-138): col 2 → `[0 2.82 -3.0]` (comment "was moved -4.5"), col ≥ 4 → `[0 -5.8 5.64]`, else `[0 0 0]`
8. GLOBAL TENT: `rotate (π/12) [0 1 0]` then `translate [0 0 13]` (L145-147)

`case-place` (L149-163) is the same pipeline with a fixed `column-offset [0 -4.35 5.64]`, used to position wall spheres at *fractional* column/row coordinates.

### 1.4 Manuform `apply-key-geometry` (L157-189) — the generalized version
```
column-angle = β * (centercol - column)          ; centercol = 3 (L22)
:standard  = translate(0,0,-row-radius) ∘ rotate-x(α*(centerrow-row)) ∘ translate(0,0,row-radius)
           ∘ translate(0,0,-column-radius) ∘ rotate-y(column-angle) ∘ translate(0,0,column-radius)
           ∘ translate(column-offset column)
then:      rotate-y(tenting-angle) ∘ translate(0,0,keyboard-z-offset)
```
Constants: `nrows=4, ncols=5` (L16-17), `centerrow = nrows - 3 = 1` ("controls front-back tilt", L21), `centercol = 3` ("controls left-right tilt / tenting", L22), `tenting-angle = π/12` (L23), `keyboard-z-offset = 9` ("original=9 with centercol=3; use 16 for centercol=2", L35). Column offsets (L28-31): col 2 → `[0 2.82 -4.5]`, col ≥ 4 → `[0 -12 5.64]` ("original [0 -5.8 5.64]"), else zero.

Two alternate column styles (L24-26, chosen `:orthographic` automatically when nrows > 5):
- `:orthographic` (L168-174): rotates by column-angle but *translates* columns instead of arcing them: x shift `-(column - centercol) * column-x-delta` where `column-x-delta = -1 - column-radius*sin(β) ≈ -22.34` (L154), z shift `column-z-delta = column-radius * (1 - cos(column-angle))` (L167). Avoids key collision for tall matrices.
- `:fixed` (L175-183): per-column absolute angle/x/z tables `fixed-angles = [10° 10° 0 0 0 -15° -15°]`, `fixed-x = [-41.5 -22.5 0 20.3 41.4 65.5 89.6]`, `fixed-z = [12.1 8.3 0 5 10.7 14.5 17.5]`, `fixed-tenting = 0°` (L49-52), "defaults roughly match Maltron". Comment admits: **"NOTE: THIS DOESN'T WORK QUITE LIKE I'D HOPED."** (L48).

### 1.5 `key-place` vs `key-position` — the key architectural trick
Manuform L191-212: `apply-key-geometry` is parametrized over `translate-fn`, `rotate-x-fn`, `rotate-y-fn`:
- `key-place` passes scad-clj's `translate`/`rotate` → returns a solid.
- `key-position` passes `(partial map +)` and pure 3×3 matrix functions `rotate-around-x` / `rotate-around-y` (core.matrix `mmul`, L197-209) → returns a coordinate vector.

Same layout code produces both geometry and raw points (used by `thumborigin`, `screw-insert`, `rj9-start`, `usb-holder-position`, `teensy-top-xy`). This is the single most reusable pattern for the Python port.

### 1.6 Dometyl placement (`lib/curvature.ml`, `lib/plate.ml`)
Curvature is a first-class value, not inline math. `Curvature.place` (curvature.ml L55-73):
- **well** (column curvature): `well_point = (0,0,radius)`; key i is rotated `angle * (i - centre_idx)` about X, `~about:well_point` (L43-47), after an optional per-key `tilt` about Y with `tilt_correction ~xrot ~tilt = xrot * tilt / -2.` (L32) to keep tilted columns (e.g. index) aligned.
- **fan** (row/thumb splay): `fan_point = (radius,0,0)`; rotate `-angle * (i - centre_idx)` about Z (L49-50).
- Combinators: `Curve`, `Custom (int -> Key.t -> Key.t)`, `PreTweak`, `PostTweak`, `Mix (int -> t)` (L25-30) — per-key escape hatches without abandoning the curve.

`Plate.make` (plate.ml L88-201): per-column `Lookups` record of functions `{offset; curve; swing; splay; rows; centre} : int -> _` (L5-64). Defaults: offsets col2 `(0,3.5,-6)` middle, col3 `(1,-2.5,0.5)` ring, col≥4 `(1,-22,9.5)` pinky, col0 `(-2,0,7)`; curvature ring `radius 37, angle π/4.5`, pinky `35, π/4.1`, col0 `45, π/6, tilt π/6.75`, else `46, π/6.3`; splay ring `-π/25`, pinky `-π/9`. Column x-spacing: `space = keyhole.outer_w + spacing` with `spacing = 1.` (L111-118). Column pipeline (L122-136): curve column → `yrot ~about:(centre_offset - off) tent` (tent about the centre column!) → rotate `(0, swing, splay)` about the column's centre-key origin → translate offset. Finally a global **lift** (L168-183): scan all key faces for the lowest z and translate everything up by `clearance - lowest_z` — replacing dactyl's magic `+13`/`+9` z offsets with a computed value.

## 2. THUMB CLUSTER

### 2.1 Original dactyl (`defn thumb-place`, L239-262)
Mini curved well with its own radii (`row-radius = ((mount-height+1)/2)/sin(α/2)+16.7 ≈ 87.18`, `column-radius = ((mount-width+2)/2)/sin(β/2)+16.7 ≈ 239.08`), then a hand-tuned rigid transform:
1. row arc about X (`rotate (α*row)`, no centre offset), 2. column arc about Y (`rotate (column*β)`), 3. `translate [mount-width 0 0]`, 4. `rotate (π*(1/4 - 3/16)) [0 0 1]` = π/16 = 11.25° yaw, 5. `rotate (π/12) [1 1 0]` — 15° about the *diagonal* [1 1 0] axis, 6. `translate [-52 -45 40]`.
Layout uses fractional grid coords: 2×2u keys at `(0,-1/2)`, `(1,-1/2)`; 1u at `(1,1)`, `(2,-1)`, `(2,0)`, `(2,1)` (`thumb-layout` L276-280). Anchor is absolute — if the main well moves, `[-52 -45 40]` must be re-tuned by hand.

### 2.2 Manuform (`thumborigin`, L291-293)
```
thumborigin = key-position(1, cornerrow, [mount-width/2, -mount-height/2, 0]) + thumb-offsets
thumb-offsets = [6 -3 7]  (L33)
```
i.e. the bottom-right corner of key (col 1, cornerrow) computed **through the full placement pipeline** — the cluster follows the well automatically. Six named per-key place fns (L296-347), each `rotate-x(deg) ∘ rotate-y(deg) ∘ rotate-z(deg) ∘ translate(thumborigin) ∘ translate(per-key offset)`:
- `thumb-tr-place`: (10°, -23°, 10°), `[-12 -16 3]`
- `thumb-tl-place`: (10°, -23°, 10°), `[-32 -15 -2]`
- `thumb-mr-place`: (-6°, -34°, 48°), `[-29 -40 -13]`
- `thumb-ml-place`: (6°, -34°, 40°), `[-51 -25 -12]`
- `thumb-br-place`: (-16°, -33°, 54°), `[-37.8 -55.3 -25.3]`
- `thumb-bl-place`: (-4°, -35°, 52°), `[-56.3 -43.3 -23.5]`
Top two use `larger-plate` (1.5u) and dedicated `thumb-post-*` at `±mount-height/1.15` (L382-385).

### 2.3 Dometyl (plate.ml L138-166)
Thumb is just another `Column` with fan curvature (default `radius 85, angle π/12.5`, Lookups.thumb L54-63), then: `Columns.zrot (-π/2)` ("orient along x-axis") → `Columns.rotate thumb_angle` (default `(π/20, -π/9, π/12)`) → `Columns.translate thumb_offset` (default `(-14, -42, 13.5)`) → tent `yrot ~about:(centre_offset - thumb_origin) tent` so the thumb tents around the same pivot as the body. Reuses all column machinery (curvature, joins, walls).

## 3. WEB / CONNECTORS

Identical technique in both Clojure projects (dactyl L187-233, manuform L240-285):
- `web-thickness = 3.5`, `post-size = 0.1`, `post-adj = post-size/2 = 0.05`
- `web-post` = 0.1×0.1×3.5 cube translated `[0 0 plate-thickness - web-thickness/2]` so its **top face is flush with the plate top** (z=4) and it hangs 3.5 down.
- Corner posts inset by `post-adj`: `web-post-tr = translate [mount-width/2 - 0.05, mount-height/2 - 0.05, 0]`, and `-tl/-bl/-br` mirrored (dactyl L194-197).
- `triangle-hulls` (manuform L252-255): `(apply union (map (partial apply hull) (partition 3 1 shapes)))` — hull every consecutive **triple** of posts, producing a triangle strip.

Three enumeration loops in `connectors` (manuform L257-285):
1. **Row connections** (col c ↔ c+1): `[(c+1,r).tl, (c,r).tr, (c+1,r).bl, (c,r).br]`
2. **Column connections** (row r ↔ r+1): `[(c,r).bl, (c,r).br, (c,r+1).tl, (c,r+1).tr]`
3. **Diagonal**: `[(c,r).br, (c,r+1).tr, (c+1,r).bl, (c+1,r+1).tl]` — one quad per 4-key intersection.
Because posts are ~0-size, hulls produce clean skirts whose top surface interpolates plate tops. Thumb connectors are the same posts hulled in hand-written sequences (dactyl `thumb-connectors` L303-380, manuform L387-458, incl. the thumb↔body seam via long triangle-hulls chains).

Dometyl replaces posts with **face hulls**: `Column.make` (column.ml L65-111) hulls the actual north/south face paths of adjacent keys (`Mesh.hull (face1.path @ face2.path)`, with ±0.01 "fudge faces in for union" translations, L58-63) and stores each join's west/east side sheets in `Join.t` for later reuse. Cross-column gaps use `Bridge.keys`/`Bridge.cols` (bridge.ml L22-125): each face is slid outward along its normal by `d1 = 0.5`, `d2 = 1.0` (`slide`, L6-9) and inward by `in_d = 0.2`, then hulled — the code comments explain d1/d2 exist for switch clearance ("If it is too large, it will interfere with needed switch clearance (like amoeba, hotswap)", L11-15) and TODO suggests replacing them with an automatic angle-sharpness check (L17-21).

## 4. WALLS (most important section)

### 4.1 Original dactyl: sphere-skinning (L405-743)
No generic wall function. Walls are built by placing 1mm spheres (`wall-sphere-at`, L408-411; `wall-sphere-bottom`/`-top` parameterized 0..1 front↔back, L416-430) at **fractional** (column,row) coords via `case-place`/`thumb-place`, then hulling consecutive pairs while marching in steps `wall-step = 0.2` (front-wall L449-493, back-wall L495-542, right-wall L544-574 — which marches 0.01 steps and hulls `partition 2 1` pairs — left-wall L576-609, plus three thumb walls L611-734). Wall↔plate gaps are patched by hulling spheres against `web-post` corners. Full of magic coordinates (`1.6666`, `0.7`, `right-wall-column = last col + 0.55`, `thumb-back-y = 0.93`, L394-400). Verdict: precise-looking but unmaintainable; this is exactly what manuform and dometyl each replaced.

### 4.2 Manuform: `wall-brace` (L482-506) — the classic pattern
Constants (L40-42): `wall-z-offset = -15` ("length of the first downward-sloping part of the wall"), `wall-xy-offset = 5`, `wall-thickness = 2` ("originally 5").
```clojure
(wall-locate1 dx dy) = [dx*wall-thickness,            dy*wall-thickness,            -1]
(wall-locate2 dx dy) = [dx*wall-xy-offset,            dy*wall-xy-offset,            wall-z-offset]
(wall-locate3 dx dy) = [dx*(wall-xy-offset+wall-thickness), dy*(...),               wall-z-offset]
```
(dx,dy) is the outward unit direction of that wall segment (e.g. back wall `0 1`, right wall `1 0`, corners get two braces with the two directions). `wall-brace place1 dx1 dy1 post1 place2 dx2 dy2 post2` =
1. `hull` of 8 shapes: each post + its locate1/2/3 offsets under both places → the sloping top wall band;
2. `bottom-hull` of the locate2 + locate3 shapes → drop to ground. `bottom` (L464-467) = `project` (2D projection) → `extrude-linear height` → translate to `z = height/2 - 10`; `bottom-hull` hulls the shapes with their 0.001-thick ground projections. locate2 vs locate3 differ by wall-thickness in xy, giving the vertical lower wall its thickness.
`key-wall-brace` (L504-506) just partials `key-place` for two key corners. `case-walls` (L508-583) enumerates: per-column back braces + between-column "tweener" braces, per-row right braces, left wall via `left-key-place` (key-position of col-0 left edge minus `[left-wall-x-offset=10, 0, left-wall-z-offset=3]`, L472-479), front wall, 7 thumb braces + 2 corner braces + 4 tweeners. The thumb↔body seam is hand-patched, flagged by the comment **"clunky bit on the top left thumb connection (normal connectors don't work well)"** (L553-582).
Ground trueing: final `model-right` subtracts `(translate [0 0 -20] (cube 350 350 40))` (L713) to shave anything below z=0.

### 4.3 Dometyl `lib/wall.ml` — bezier-swept walls from keyhole faces
A wall is generated from an actual key face (`Key.Face.t` = rounded path + corner `Points` + normal, key.ml L4-15), per side `` `North|`East|`South|`West ``. `Wall.make` (wall.ml L104-247), defaults `?(clearance=0.) ?(n_steps=`Flat 4) ?(min_step_dist=0.02) ?(d1=`Abs 14.) ?(d2=10.) ?(end_z=0.1)`:
1. **`swing_face`** (L90-102): quaternion-rotate the face about its bottom (or top, by normal z sign) edge so it becomes vertical — walls always start plumb regardless of key tilt.
2. **Clearance**: translate the swung face `clearance` along its normal (`cleared_face`, L119) — pushes wall start off the switch for cap/hotswap clearance; the gap is skinned back to the true face with 5 slices (L186-187).
3. **Quadratic bezier spine** (`bz`, L128-133): with `xy` = normalized horizontal projection of the face ortho:
   - `p1 = centre - 0.01*ortho` ("fudge for union")
   - `p2 = centre + xy * d1`  — d1 (`` `Abs mm `` or `` `Rel fraction`` of face height, L123-126) controls how far the wall shoots outward at start height;
   - `p3 = (centre.x, centre.y, end_z) + xy * d2` — d2 controls the ground landing offset.
4. **Steps**: `Steps.t = `Flat n | `PerZ mm` (L5-15) — `PerZ` gives one step per mm of face height (min 2), so short walls get few slices. `Util.prune_transforms ~min_dist:min_step_dist` drops profiles closer than 0.02 to the previous — the anti-self-intersection guard; if <2 remain: `failwith "Insufficient valid wall sweep transformations, consider tweaking d parameters."` (L177-180).
5. **Counter-rotation** (L134-141): a slerp'd quaternion, eased with cubic-bezier Easing (0.42,0)→(1,1), progressively cancels the face's z-tilt so the wall's angle matches the xy heading of its face.
6. **Scaling** (L145-163): optional `V2 (width, thickness)` taper along the sweep with optional easing (used for skeleton-style thinning walls).
7. **Two-pass end_z fix** (L164-172): sweep once with `end_z=0`, measure the min z of the last profile, re-run with `end_z` raised so the profile never dips underground; final mesh = clearing profiles + swept rows + `final` profiles skinned from the last row to its flat `V3.projection` (z=0) copy (L189-194) → the foot lands exactly on the ground plane.
8. **Rich return value** (L239-247): `{scad; key; side; start; cleared; foot; drawer; bounds_drawer}` — `foot : Points.t` is the ground-contact quad; `drawer : loc -> Path3.t` (L200-237) replays the wall's transform stack from any point on the start face (`` `TL|`BR|`T x|`XY (x,y)`` …) down to ground. Connect uses drawers to stitch neighbouring walls without re-deriving geometry.

Wall selection: `Walls.Sides.auto` (walls.ml L65-140) instantiates walls per side from lookup predicates (`north_lookup = const true`, `south_lookup i = i > 1`, `west_lookup i = i = 0`, `east_lookup = const false` defaults; thumb variants at L195-228), with per-side clearance overrides and separate index-column scaling. Manual mode takes explicit `int -> Wall.config option` maps.

Wall-to-wall gaps: `lib/connect.ml(i)` — `full_join` (morph start wall face into destination over `slices=12`, projecting pre-rotated faces when heading difference > `max_angle=1.4` rad) and `spline` (ground-level connector swept along a bezier spline of the walls' feet, with z-fillets, corner roundovers, `end_shrink=0.025`, and `tight_threshold`/`tight_d` fallback for sharp angles) (connect.mli L35-93). `skeleton`/`closed` presets assemble a full perimeter; the result `Connect.t = {scad; outline; inline}` (L6-11) records the continuous outer/inner ground outlines — consumed by bottom plate, eyelets, and tent. Doc comment: thumb links deliberately not auto-closed because sealing logic is "prone to breaking, which goes against dometyls philosophy of allowing easy repositioning/re-orienting of the thumb cluster" (connect.mli L160-164).

## 5. SCREW / INSERT MOUNTS & BOTTOM PLATES

### 5.1 Original dactyl
- `screw-hole` = cylinder r=1.5, h=60 (L1051-1053), subtracted at `key-place(4.5, 0.5)`, `key-place(4.5, 3.5)`, `thumb-place(2, -0.5)` (L1055-1059) — fractional grid coords again; same holes cut from both top and bottom parts so they align.
- Bottom is a *printed second shell*, not a flat plate: `bottom-plate` (L755-1049) re-runs the whole layout with `bottom-key-guard` cubes (mount-w × mount-h × 3.5 at z≈-4.5, L750-753), re-hulls all connections with posts shifted down `[0 0 -web-thickness-5]` (L772-776), re-hulls all wall spheres at `translate [0 ±1 1]`, and adds `stands` (L1018-1036): integrated feet = sphere r=(9.6+2)/2 hulled to ground (`bottom-hull`), minus a cube and a bumper-recess sphere (bumper Ø9.6, cut 1.5 above ground) at 4 key positions. Final parts are `difference`d with `(cube 1000 1000 10)` at z=-5 to flatten (L1207, L1221).

### 5.2 Manuform
`screw-insert-shape` (L640-642) = `cylinder [bottom-radius top-radius] height` + sphere cap at top — a heat-set insert boss. `screw-insert` (L644-656) computes xy via `key-position` + `wall-locate2/3` shifts so bosses embed in the wall band: `shift-up` rows use `wall-locate2(0,1) + [0 mount-height/2 0]`, `shift-down` `wall-locate2(0,-1) - ...`, `shift-left` `left-key-position + wall-locate3(-1,0)`, else right `wall-locate2(1,0) + [mount-width/2 0 0]`. Five sites (L658-664): `(0,0), (0,lastrow), (2,lastrow+0.3), (3,0), (lastcol,1)`. Constants (L665-670): height 3.8, insert bore Ø5.31→5.1 (tapered), boss = radii +1.6, height +1.5; through-plate screw holes r=1.7, length 350.
Bottom plate (L745-754): `(cut (translate [0 0 -0.1] (difference (union case-walls teensy-holder screw-insert-outers) screw-insert-screw-holes)))` — OpenSCAD `cut` takes the 2D cross-section at z≈0 of the wall bottoms → a laser-cuttable/printable flat plate that exactly matches the case footprint, with screw holes already in place. Zero extra bookkeeping — clever and worth stealing.

### 5.3 Dometyl
`lib/eyelet.ml`: `config = {outer_rad; inner_rad; thickness; hole}`, `hole = Through | Inset {depth; punch}`; presets `m4_config` (outer 5, inner 2.7, t 4, Through), `bumpon_config` (5.8/5/2.4, inset 0.6), `magnet_6x3_config` (4.4/3.15/4.6, inset 3.2 with `` `Rel 0.5`` punch) (L71-80). `Eyelet.make` (L84-159) builds the boss as a 2D outline: arc around the hole + two bezier "swoops" filleting into a run of wall points, extruded `thickness`; raises `failwith "Outline of eyelet ... contains intersections"` advising narrower feet or deeper bury. `Eyelet.place` (L161-199) positions it along the case's continuous `inline`/`outline` foot paths (closest-point or parameter `u`), `bury = 0.5` into the wall. `default_wall_locs` (L201-208): body W-first, N-2, N-last, S-3, thumb W-last. `Case.make` places eyelets after connections and `Eyelet.apply` adds boss + subtracts cut (case.ml L49-70).
`Bottom.make` (bottom.ml L43-113): plate = `Scad.polygon (Connect.outline_2d case.connections)` extruded `thickness = 1.65`, minus fastener holes at each eyelet centre — `Screw` counter-sunk via cone-scaled extrude (`scale = shaft_rad/head_rad`) or `Pan depth`, or magnet pockets — minus bump-on insets (rad 5.5, inset 0.8) located by key references `default_bumps = [thumb Last First; thumb Last Last; body First Last; body (Idx 3) Last; body Last Last; body Last First]` (L34-41), located via each key's actual face normals (L14-21). Bottom plate outline comes free from `Connect.t` — no re-derivation.

## 6. TENTING / ROTATION

- **Original dactyl**: tent = final `rotate (π/12) [0 1 0]` + `translate [0 0 13]` embedded (duplicated!) inside `key-place`, `case-place` (L145-147, L161-163), and differently inside `thumb-place` (`rotate π/12 [1 1 0]` + `[-52 -45 40]`). Flat bottom by boolean cut with a giant cube at z<0 (L1207/1221) — walls are simply built long enough to reach through the floor.
- **Manuform**: tent = `rotate-y tenting-angle` + `translate [0 0 keyboard-z-offset]` at the single tail of `apply-key-geometry` (L188-189), so key-place, key-position, thumborigin, screw positions, everything inherits it consistently. Ground: walls end via `bottom-hull` projections (already flat), plus the safety cut `translate [0 0 -20] (cube 350 350 40)` (L713).
- **Dometyl**: tent is a `Plate.make` parameter (`tent = π/12` default) applied per column as `yrot ~about:(centre_offset - column_offset)` (plate.ml L124-129) and to the thumb about the same pivot (L166) — i.e. rotation about the centre column so stagger tables stay meaningful; then the computed `lift` normalizes height to `keyhole clearance` (L168-183). Walls don't need a floor cut: the bezier sweep terminates at `end_z` and is skinned to its own z=0 projection (wall.ml L189-194). Additionally `lib/tent.ml` generates a **separate tenting base**: `Tent.make ?(degrees=20.)` rotates the case's `Connect` outline about the pinky-side bounding-box edge (auto-detected by comparing pinky home key to bbox edges, L228-244), builds a `Solid` shell or `Prison` of swept pillars between the flat and tilted outlines, re-drills fastener holes aligned to the case eyelets, and adds bump-on feet.

## 7. ARCHITECTURE LESSONS FOR THE PYTHON GENERATOR

**Worth copying:**
1. **Placement math separated from solid generation** (manuform `apply-key-geometry` L157-212). In Python: make the canonical placement a function `(col, row) -> 4×4 matrix`; apply it to solids *or* points. Every downstream feature (thumb anchor, screw sites, connector ports, wall starts) should consume matrices/points, never re-derive.
2. **Layout as data**: dometyl's `Lookups` (`int -> offset/curve/splay/rows`, plate.ml L5-64) and `Walls.Sides.auto` predicates (walls.ml L77-80) beat manuform's `cond` tables and beat dactyl's hardcoded loops. In Python: dataclasses of per-column config with callable or dict lookups + defaults.
3. **Rich intermediate results**: dometyl's `Wall.t` keeps `start/cleared/foot` points and a `drawer` closure; `Connect.t` keeps `outline/inline`; `Case.make` is literally `plate_builder → plate_welder → wall_builder → base_connector → ports_cutter` as injected functions (case.ml L33-78). The bottom plate is a 10-line function because the outline already exists. Design every stage to return geometry + queryable metadata, not just a mesh.
4. **Radius-from-pitch formula** `r = (pitch/2)/sin(θ/2) + cap_top_height` — keep it, it's the correct arc math; parametrize gap (`extra-width/height`) like manuform.
5. **Anchor derived positions through the pipeline** (manuform `thumborigin = key-position(1, cornerrow, corner) + offsets`), never absolute coords (dactyl `[-52 -45 40]`).
6. **Tiny-post + hull ("triangle-hulls")** is a robust, dumb, always-manifold gap filler (`partition 3 1` + hull). Good v1 strategy; dometyl-style face-path hulls with 0.5/1.0 mm slide-out clearance (bridge.ml `slide`) are the upgrade when you have real face paths.
7. **Wall recipe to adopt**: dometyl's — swing face vertical → clearance offset → quadratic bezier `(face centre) → (+d1·xy at start height) → (+d2·xy at end_z)` → sweep profiles with step pruning → skin last profile to its z=0 projection → record foot quad. `d1=14 abs / rel-to-height`, `d2=10`, `steps = PerZ(1mm)` are proven defaults. Manuform's locate1/2/3 (thickness 2, xy 5, z -15) is the simpler fallback and is fine for closed cases.
8. **Bottom plate via 2D projection/section of the walls at z≈0** (manuform `cut`, dometyl outline polygon) — never model it independently.
9. **Single tenting application point** and computed z-lift (dometyl's lowest-face scan) instead of magic z constants.

**Pitfalls the code itself admits:**
- Manuform L48: fixed column style "DOESN'T WORK QUITE LIKE I'D HOPED" — don't bother with absolute per-column pose tables; keep arc+offset.
- Manuform L553: "clunky bit on the top left thumb connection (normal connectors don't work well)" — the thumb↔body seam is *the* hard part in every generator; plan an explicit, configurable link (dometyl's `west_link`/`east_link` configs, and its stated philosophy of not auto-sealing thumb links, connect.mli L160-164).
- wall.mli L88-97: too many sweep steps → points bunch → self-intersecting mesh → CGAL failure; mitigations = `PerZ` steps, `min_step_dist` pruning, larger d1. Bake a min-profile-distance guard into any swept-wall implementation.
- connect.mli L67-77: high outline resolution + fillets → "bunching up of points" → self-intersection; sharp inter-wall angles need a reduced outward step (`tight_threshold`/`tight_d`).
- bridge.ml L11-21: clearance offsets (in_d/out_d) must be user-tunable because hotswap sockets/amoebas need room; TODO: derive from angle sharpness automatically.
- eyelet.ml L152-157: boss outlines can self-intersect on concave wall runs — validate and report with actionable messages like dometyl does.
- Original dactyl overall: fractional-coordinate sphere walls (L394-743) show what happens without a wall abstraction — hundreds of magic numbers; also global tent duplicated in 3 place functions drifted apart (`case-place` has different column-offset than `key-place`).

---
Key file citations recap: dactyl.clj L120-163 (placement), L187-233 (web), L239-262 (thumb), L405-743 (walls), L1051-1059 (screws); manuform L157-212 (apply-key-geometry/key-position), L291-347 (thumb), L482-583 (wall-brace/case-walls), L640-670 (screw inserts), L745-754 (plate via cut); dometyl wall.ml L90-247, curvature.ml L32-73, plate.ml L88-201, walls.ml L65-140, connect.mli, bridge.ml L6-125, column.ml L41-120, eyelet.ml L84-222, bottom.ml L43-113, tent.ml L215-346, case.ml L33-78.
