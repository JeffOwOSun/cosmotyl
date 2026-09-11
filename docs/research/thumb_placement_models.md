# Thumb Cluster Placement Models — Dactyl, Manuform, Dometyl, Cosmos

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


All paths relative to `scratch/research/`. Every number below was re-verified against source this session.

## 1. Original Dactyl — mini spherical well + hand-tuned rigid mount

`dactyl-keyboard/src/dactyl_keyboard/dactyl.clj`, `thumb-place` (L239-262). The thumb is a second curved keywell with its OWN radii, then a rigid transform stack:

- α = π/12 (15°/key), β = π/36 (5°/key), cap-top-height = 4 + 12.7 = 16.7 (L120-122, L240-248).
- thumb row-radius = ((mount-height+1)/2)/sin(α/2) + 16.7 = (18.4/2)/sin 7.5° + 16.7 = 70.48 + 16.7 = **87.18 mm**; thumb column-radius = ((mount-width+2)/2)/sin(β/2) + 16.7 = 9.7/sin 2.5° + 16.7 = **239.08 mm** (mount-w = mount-h = 17.4).
- Per key (column,row), applied in order (L252-262):
  1. `T(0,0,−87.18)`, `Rx(α·row)`, `T(0,0,+87.18)`  ← rotation about the cap-top arc center ABOVE the key; note `α·row` (no center-row offset; rows are fractional: −1, −1/2, 0, 1)
  2. `T(0,0,−239.08)`, `Ry(β·column)`, `T(0,0,+239.08)`
  3. `T(17.4, 0, 0)`
  4. `Rz(π(1/4 − 3/16)) = Rz(π/16) = Rz(11.25°)`
  5. `R(π/12 = 15°, axis [1 1 0])` — 15° about the un-normalized diagonal
  6. `T(−52, −45, 40)` — ABSOLUTE anchor, hand-tuned, does not track the main well.
- Layout (L264-280): 2u keys at (0,−1/2), (1,−1/2); 1u at (1,1), (2,−1), (2,0), (2,1).

Model class: a true 2-axis arc grid (sphere-patch approximation, same math as the finger well) — keys DO lie on curves — but the cluster anchor is a magic constant.

## 2. Dactyl Manuform — pipeline-derived anchor + 6 free per-key poses (no curve)

`dactyl-manuform/src/dactyl_keyboard/dactyl.clj`:
- **Anchor** (L291-293): `thumborigin = key-position(1, cornerrow, [mount-width/2, −mount-height/2, 0]) + thumb-offsets`, with `thumb-offsets = [6 −3 7]` (L33), `cornerrow = nrows − 2` (L58-59: lastrow = nrows−1, cornerrow = lastrow−1). I.e. the BOTTOM-RIGHT CORNER of the index-adjacent column's corner key, computed through the full placement pipeline (`key-position` runs the same `apply-key-geometry` as solids, L191-212), so the cluster follows stagger/curvature/tenting changes automatically. This is the single most important pattern to copy.
- **Per-key** (L296-347), world = T(thumborigin + offset) · Rz · Ry · Rx (thread order: Rx first):
  | key | Rx | Ry | Rz | offset |
  |---|---|---|---|---|
  | tr | 10° | −23° | 10° | (−12, −16, 3) |
  | tl | 10° | −23° | 10° | (−32, −15, −2) |
  | mr | −6° | −34° | 48° | (−29, −40, −13) |
  | ml | 6° | −34° | 40° | (−51, −25, −12) |
  | br | −16° | −33° | 54° | (−37.8, −55.3, −25.3) |
  | bl | −4° | −35° | 52° | (−56.3, −43.3, −23.5) |
- No curve: 6 independent rigid poses. But note the regularity: Ry ≈ −23…−35° (roll toward thumb pad) and Rz grows 10→54° marching down the cluster — an implicit fan of ~11°/key in yaw.

## 3. Dometyl — the thumb IS a parametric curve (planar fan arc)

`dometyl/lib/curvature.ml` + `lib/plate.ml`:
- Thumb = one `Column` with **fan** curvature: default `radius = 85., angle = π/12.5 = 14.4°/key, centre = 1, 3 keys` (plate.ml L54-63).
- Fan math (curvature.ml L44, L49-50, L63-64): key i is rotated about the point `fan_point = (radius, 0, 0)` by `θ_i = −angle·(i − centre_idx)` about **Z** (plus optional per-key `yrot tilt`, default 0). Explicitly: `p_i = c + Rz(θ_i)(p − c)` with c = (85,0,0). For the default 3 keys: θ = {+14.4°, 0, −14.4°} → key origins (2.67, ∓21.14, 0) — a planar arc of radius 85 mm, chord pitch 21.1 mm.
- Cluster pose (plate.ml L138-166): fanned column → `Columns.zrot(−π/2)` ("orient along x-axis") → `Columns.rotate(thumb_angle)` with default `(π/20, −π/9, π/12) = (9°, −20°, 15°)` XYZ → `Columns.translate(thumb_offset)` default `(−14, −42, 13.5)` → tent `yrot ~about:(centre_offset − thumb_origin) tent` (same pivot as the body, so tenting carries the thumb consistently, L166).
- Curve parameterization: C(θ) = fan center + R·(direction), keys at equal Δθ; key +Z stays the fan-plane normal (fan rotates about Z only) — a **planar circular arc with keys normal to the plane**, the cleanest curve model of the four projects.

## 4. Cosmos — anchor derived through pipeline + 4 cluster generators (2 are curves)

`cosmos-full/src/lib/worker/config.ts`:
- **Anchor** `thumbOrigin(c)` (L900-958): `origin = [preset pose] · translateBy( placeOnMatrix(row = cornerRow−centerRow, column = 1−centerCol, merged finger curvature) transformed by upperKeysPlane(c) then translate(17.5/2, −17.5/2, 0) ) · Rz(staggerThumb.a) · T(staggerThumb.xyz)`; cornerRow = rows−2, centerRow = rows−3 (2.5/2 for 3/2-row boards), centerCol = cols/2 (L901-906). Same manuform idea: the anchor is the bottom-right quarter-key corner of column 1's corner key, run through the finger placement math incl. tenting plane (upperKeysPlane, L869-874). `approximateCosmosThumbOrigin` (L876-898) is the flat 21-mm-spacing version used by the editor.
- **Preset poses** prepended to that anchor (order = Rz·Ry·Rx world composition since ETrsf ops chain):
  - defaultThumb (manuform port, L933-938): Rx 28.868°, Ry 12.366°, Rz −47.284°, T(−42,−43,−8)+T(5,10,0) = T(−37,−33,−8)
  - curvedThumb (L939-944): Rx −11.890°, Ry −24.801°, Rz +34.450°, T(−35.783, −25.667, −7.083)
  - carbonfet (L911-915): Rx −9°, Ry 32°, Rz −160°, T(−26.2, −28.5, −8.9)
  - orbyl (L916-921): T(0,0,−8), Rx 10°, Ry −15°, Rz 5°, T(−57.75, −18.75, −2)
- **Per-key generators**:
  - `manuformThumbs` (L1077-1192): 6 free poses, e.g. topLeft Ry −3°, Rz 66°, T(−13.4, 17, −0.1); bottomRight Rx −21°, Ry −2°, Rz 106°, T(18.4,−18.5,−0.6). Ad-hoc offsets (Cosmos's re-tuned manuform).
  - `defaultThumbs` = curvedThumb (L1194-1325): each key = small trim rotation (e.g. topLeft Rx 17.8°, Ry 3.3°, Rz −8.2°) · `placeOnMatrix(fractional coords)` · z-trim. Fractional (column,row): topLeft (0.4,−0.34), topRight (1.43,−0.06), middleLeft (−0.72,−0.42), middleRight (0.29,0.67), bottomLeft (−0.64,−0.44), bottomRight (−0.75,0.58); curvature/spacing from user params (`thumbCurvature` L1340-1346, proto angles ×45, spacings ×10). So curved thumbs are keys on a 2-axis arc surface + per-key sculpt deltas.
  - `carbonfetThumbs` (L1356-1408): pure `placeOnMatrix` 3×2 grid, columns {−1,0,1}, rows {0.7,−0.3}, {0.575,−0.675}, {0.45,−0.8} — clean torus-patch placement, no per-key fudge.
  - `orbylThumbs` (L1410-1473): **keys on a sphere**: `placeOnSphere({angle, row})` at azimuth angles {80°, 130°, 180°, 230°}, row 1.85/2/2/2, spacing 18.75; plus trackball at center (Rz 30°, T(0,0,8)).
- **The curve/surface math** (`modeling/transformation-ext.ts`):
  - `placeOnMatrix` (L309-353): rowRadius = spacingOfRows/2/sin(curv_col/2) + capTop (MX capTop = 6.2); `t.rotate(−curv_col·row, about [0,0,+rowRadius], X)`; then columnRadius likewise and `t.rotate(−curv_row·column, about [0,0,+columnRadius], Y)`. Center ABOVE key plane → concave well.
  - `placeOnSphere` (L355-371): `R = spacing/2/sin(curv/2) + capTop`; `t.rotate(−curv·row, about [0,0,−R], X)` — center BELOW → **convex dome** — then `t.rotate(−angle)` about Z. Parameterization: polar angle φ = curv·row from the dome pole, azimuth ψ = angle. i.e. key(ψ,row) = Rz(−ψ)·RotX@(0,0,−R)(−curv·row). This is the most explicit "keys on a curved surface with a moving frame" of any generator.
- Thumb keys carry ABSOLUTE world poses after this; `calcClusterTrsf = thumbPose · fingerPosInv(flat) · fingerPos(3D)` cancels in 3D so the tent slider deliberately never moves thumbs (config.cosmos.ts L586-594, per our prior notes §3).

## 5. Cosmos hand-scan fitting — VERDICT: it does NOT place the thumb cluster

Dug hard; the premise "hand scan positions clusters from thumb metrics" is FALSE in the current code:
- The scan (`routes/scan`, `routes/scan2`, MediaPipe 21 landmarks) produces per-finger 4-bone kinematic chains: `calculateJoints` (`src/lib/hand.ts` L417-438) fixes the metacarpal (degree 0, `averageNorms` L194-205) and fits the phalange rotation axes by SVD/PCA of normalized bone vectors (`fitNorms` L215-243). Thumb DOF exception: 2nd joint 1-DOF, 3rd joint 2-DOF (header L19, L430-432).
- `HandFitView.svelte` — the only place scan data changes the CONFIG — computes **finger column staggers only**: FK with fixed curl angles [5°, 4°, 9°] accumulated over the 3 phalanges, `x = Σ lᵢ·cos(Σaⱼ)`, `y = −Σ lᵢ·sin(Σaⱼ)` (L20-36), staggers relative to index (L49-54), written into the fingers cluster (L72-77). The UI states verbatim (L122-126): "This does **not change** … anything about the **thumb cluster** (placement or spacing). You should tune those yourself using the Hand 3D model."
- What the scan DOES do for thumbs: the 3D preview solves the **inverse** problem — given the keyboard, pose the hand. `theBigFit` (`Viewer3D.svelte` L537-551) targets the 5 home keys (incl. `home: 'thumb'`); the wrist pose starts at the wrist-rest matrix (L489-510) and `refine()` (`handoptim.ts` L108-163) runs 300 iterations of gradient descent over the wrist **Euler angles only** (position stays fixed), minimizing per finger `E = (|R·x − t| − 0.99·(l₁+l₂+l₃))²` (linear branch when inside reach, L91-98) plus a joint-limit penalty on the MCP direction (L80-82); per-finger joint angles then come from the closed-form cyclic-quadrilateral IK `SolvedHand.ik` (`hand.ts` L263-308, `cyclicQuadAngle` L248-250 = law-of-cosines on the max-area inscribed quadrilateral).
- Takeaway: Cosmos's principled piece is the scanned thumb chain (CMC-anchored 4-bone chain with measured lengths + fitted axes) + an optimizer that can score reachability of any candidate cluster pose. Nothing maps scan → cluster pose in closed form.

## 6. Does anyone model the thumb as a curve?

| Project | Curve? | Parameterization |
|---|---|---|
| Dactyl | yes (2-axis arc grid) | Rx@(0,0,87.18)·(15°·row), Ry@(0,0,239.08)·(5°·col), fractional (col,row) |
| Manuform | no | 6 free rigid poses off a pipeline-derived anchor |
| Dometyl | **yes — planar fan arc** | rotate about (85,0,0) by −14.4°·(i−1) about Z |
| Cosmos manuform/default | no | free poses off pipeline anchor |
| Cosmos curved/carbonfet | yes (torus patch) | placeOnMatrix arcs, R = s/2/sin(κ/2)+6.2 |
| Cosmos orbyl | **yes — sphere/dome** | Rz(−ψ)·RotX@(0,0,−R)(−κ·row), ψ ∈ {80,130,180,230}° |

## 7. Our scan data (verified, hand_geometry_report.md)

- Thumb: "natural arc centered ~29 mm inward and ~30 mm below your index bottom row, running at ~37° from horizontal with ~42 mm of comfortable span (≈2–3 keys of arc)" (L15); Ergogen config uses `ref: matrix_index_bottom, shift: [−29, −30], rotate: −37` (L63-67).
- **No radius was measured**: `scratch/ergopad_analysis.py` L52 fits a LINE (slope → 37°), not a circle. A radius must therefore be assumed/inferred. Cross-check: at R = 85 mm (dometyl default), the sagitta over the 42 mm span is 85 − √(85² − 21²) = 2.63 mm — below trace noise, which is exactly why a line fit looked straight. So R ∈ [70, 100] is consistent with our data.

## 8. Recommended parametric model (synthesis)

**Anchor (verified inputs)**: derive through the finger pipeline, never absolute — `A = M_indexBottomKey · T(−29, −30, 0)` where M_indexBottomKey is the world 4×4 of the index-column bottom-row key from our generator (manuform/Cosmos pattern, §2/§4).

**Cluster frame (verified heading + inferred tilts)**: `F = A · Rz(−37°) · Ry(β_t) · Rx(α_t)` with β_t ≈ −25° (INFERRED: manuform −23…−35°, Cosmos curved −24.8°, dometyl −20° — all three converge on rolling the thumb plane ~20-35° so caps face the thumb pad) and α_t ≈ +10° pitch (manuform +10°, dometyl +9°). Drop z by ~−5…−8 mm relative to the corner key (manuform +7 on thumb-offsets but −13…−25 per key; Cosmos −7…−9; start at −7 and tune).

**Curve** — planar fan arc in the F frame (dometyl model, radius justified by our flat trace):
- C(θ) = (R·sin θ, R·(1 − cos θ)·σ, 0), θ ∈ [θ_min, θ_max], with R = 85 mm default (tunable 70–100), σ = +1 placing the arc center at (0, +R, 0) — on the palm side, approximating the CMC pivot, so the arc bows away from the palm like a real thumb sweep.
- Moving frame: T̂(θ) = (cos θ, σ·sin θ, 0); N̂(θ) = σ·(−sin θ, σ·cos θ, 0) (points at the arc center); B̂ = (0,0,1) = ẑ_F.
- Key i pose: `M_i = F · [T̂(θᵢ) | N̂(θᵢ) | B̂ | C(θᵢ)] · R_T(ρᵢ)` where θᵢ = (i − i_home)·p/R with pitch p and optional cup roll ρᵢ about the tangent (orbyl-style dome cupping; start ρ = 0, or ρᵢ = −10°·(i − i_home) to face keys toward the thumb pad — INFERRED, no project measured this).
- Constraint from scan: total span (n−1)·p ≤ 42 mm → 3 keys max — matches the report's "2–3 keys of arc" exactly.
- With curvature wanted later, swap B̂-constant for the Cosmos sphere: R_s = p/2/sin(κ/2) + capTop and rotate each key −κ·row about the local X through (0,0,−R_s) for a convex dome (κ ≈ 10°/key is Cosmos's orbyl example, model_gen/keyboards.ts L70).

**Validation loop (steal from Cosmos)**: implement the 4-bone thumb chain from hand.ts with OUR measured metrics and score each candidate (R, β_t, α_t, z) by reach error to the 3 key tops via the cyclic-quadrilateral IK — that turns Cosmos's visualization into the closed-loop cluster-placement optimizer they never built.

**Verified vs inferred summary**: verified — all formulas/numbers in §1-§6 (file+line cited), anchor (−29,−30), heading −37°, span 42 mm, 3-key budget; inferred — R = 85 (bounded 70–100 by sagitta argument), β_t = −25°, α_t = +10°, z = −7, cup roll ρ.

---
NOTE (parent): key correction to the task premise — Cosmos's hand scan feeds finger-column staggers and a hand-on-keyboard IK visualizer only; it does not position the thumb cluster (HandFitView.svelte L122-126 says so explicitly).
