# Cosmos Keyboard Generator — Internals Report

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


Distilled from the local clone at `research/cosmos-full/` (geometry engine is open source;
only `src/lib/worker/pro-patch/` stubs throw). Citations are file paths within
`cosmos-full/` unless noted. This seeds a clean-room reimplementation, so numbers and
transform order are authoritative.

## 1. Coordinate system & units

- Millimeters, degrees, **Z-up**, right-handed. Key local frame: **+Z out of the keycap**.
- A key's transform lands at the **socket top center** (`keyHoleTrsf`,
  `src/lib/worker/geometry.ts` L931-961).
- World origin ≈ the center of the fingers matrix: `centerCol = nCols/2`,
  `centerRow = nRows - 3`.
- The floor is found **post-hoc**: the model is raised by
  `additionalHeight = -minZ + verticalClearance + screw headroom`
  (`geometry.ts` L978-1029). Nothing is designed "from the floor up."
- **RIGHT hand is canonical**; the left half mirrors tuples as
  `pos(x→-x)`, `rot(α, -β, -γ)` plus a `trsf.mirror`
  (`src/lib/worker/config.cosmos.ts` L969-1008).
- Serialized units (proto/URL): lengths ×10 (0.1 mm), angles ×45 (1/45°). Tuple codec:
  per-component zigzag, 1 byte if `u < 128` else 2-byte 14-bit pack, LSB-first into an
  int64 (reimplemented in our `inject_splay.py` / `retent.py`).

## 2. Key placement math

Full composition:

```
M_world = ClusterTrsf · placeColumn(col) · ColumnTrsf · placeRow(row) · KeyLocal
```

- Each pose tuple decodes as `T(pos) · Rz(γ) · Ry(β) · Rx(α)` — **X rotation applied
  first**.
- `placeRow`: sphere-tangent placement. Radius
  `R = V_SPACE/2 / sin(colCurv/2) + capTop`; rotate `-colCurv · row` about X through
  `[0, 0, R]` (`src/lib/worker/modeling/transformation-ext.ts` L309-332).
- `capTop` = unpressed switch height above socket top (**MX: 6.2 mm**,
  `src/lib/geometry/switches.ts` L10-31).
- Defaults: `H_SPACE = 21.5`, `V_SPACE = 20.5`, `rowCurv = 5°`, `colCurv = 15°`
  (`src/lib/worker/config.serialize.ts` L217-220).
- **Splay** = cumulative γ in the column-cluster rotation, rotating about the **cluster
  origin** (`config.cosmos.ts` L1016-1024) — not about the column itself.
- Stock staggers: middle `(0, +2.8, -4.0)`, pinky/outer `(0, -13, +6)`.
- Keys/columns serialize **deltas from the parametric pose** (`toCosmosClusters`,
  `config.cosmos.ts` L215-221), so a "0" tuple means "exactly parametric".

## 3. Thumb cluster

- Thumb keys carry **absolute world poses**.
- `calcClusterTrsf = thumbPose · fingerPosInv(flat) · fingerPos(3D)` cancels in 3D
  (`config.cosmos.ts` L586-594) → **the tent slider never moves the thumbs**.
- Curved preset pose: `(-35.78, -25.67, -7.08)` mm /
  `(-11.889°, -24.800°, +34.444°)` — equal to legacy `curvedThumb` constants
  (`src/lib/worker/config.ts` L939-944).
- Per-key sculpt table for curved thumbs: `config.ts` L1209-1293
  (3-key = topLeft + topRight + middleLeft).

## 4. Tenting / orientation

- Tenting is a rotation baked into the fingers-cluster transform; Euler order as above
  (`Rz·Ry·Rx`, X first). Retenting a serialized design = decode cluster tuple, adjust β,
  re-encode (our `retent.py` operator).
- Because thumbs are absolute (see §3), retent operators must transform thumb poses
  explicitly if thumbs should follow.

## 5. Wrist rest

- **Footprint algorithm is OPEN** (`wristRestGeometry`, `geometry.ts` L1658-1740):
  - Case-side edge = the actual wall points → conformal **by construction**. This is why
    Cosmos cannot give clearance between pad and case.
  - Front edge = `minY - origin.y + extension`; taper clamps at `middle ± 10mm`.
- Solid generation (slope/tenting application, `WR_TOLERANCE = 0.25`) is PRO-stubbed.
- Proto fields: f15 = position tuple (0.1 mm, default `(10, -110, 0)`); f9/f16 extension
  ×10 (default 80 = 8 mm... stored 80→8.0mm); f10 taper ×45 (450 = 10°); f11/f17 maxWidth
  ×10 (1000 = 100 mm); f12 angle ×45; f13 slope ×45 (225 = 5°); f14 WR tenting ×45
  (270 = 6°).

## 6. Wall / web algorithms (OPEN — steal wholesale)

- **Boundary**: flat-project socket corners → `cdt2d` Delaunay → `concaveman` concave
  hull with concavity 1.5 (`geometry.ts` L1061-1181).
- **Wall cross-section**: 7 points ti/to/mi/mo/ki/bi/bo with exact-thickness corrections;
  offsets `xOut = wallXYOffset`, `zOut = wallZOffset`, then vertical drop to floor
  (`wallCriticalPoints`, `geometry.ts` L198-344).
- **Web**: same triangulation as boundary; thickness = socketHeight
  (`src/lib/worker/model.ts` L215-290).
- PRO-stubbed (throw): rounded walls, wrist solid, stilts, plate art.

## 7. Constants worth keeping

| Constant | Value | Source |
|---|---|---|
| wallThickness | 4 mm | config defaults |
| wallXYOffset | 5 mm (ours: 7) | config defaults |
| wallZOffset | 15 mm | config defaults |
| plateThickness | 3 mm | config defaults |
| verticalClearance | 0.1 mm | config defaults |
| webMinThicknessFactor | 0.8 | model.ts |
| keyBase (xda) | 15.11 mm = 6.2 + 0.9·9.9 | switches/keycaps |
| mx-skree socket | 18×18×4.7; partBottom 18.7×18.7×7.5 | socketsParts.ts |
| keycap depths | xda 9.9 / dsa 7.9 / mt3-r3 10.7 | keycaps.ts |
| DISPARITY_MAGIC | 5.95545213 | geometry.ts |
| arc magic | 28.636 | geometry.ts |
| foot | Ø10 × 2.5, inset 6 | model.ts |
| screws | 7× M3 heat-insert, countersunk | config defaults |

**Ours** (collision-verified, `gen_case.py` L25-49): row pitch
`Δθ = max(18.5/R, 18.9/(R-7))`, R clamped 55–75; `base_y = -(travel - 34)·0.3`;
MX cutout **14.15 mm** (print-shrink compensated).

## 8. PRO gaps (what we must build ourselves)

- Rounded top/side walls (bezier or fillet sweep — the trigger for this pivot).
- Wrist-rest solid generation (footprint is open, §5).
- Stilts, plate art — not needed.

## 9. Serialization quick-reference

- Lengths ×10 (0.1 mm), angles ×45.
- Tuple: per-component zigzag; 1 byte if `u < 128` else 2-byte 14-bit pack; components
  packed LSB-first into int64.
- Keyboard field 12 = `rounded_flags` (`RoundedFlags{side: bit0, top: bit1}`,
  `cosmosStructs.ts`).
- Working codecs: our `inject_splay.py`, `retent.py`, `decode_cm.py`.

## 10. Recommended steals for the new generator

1. Sphere-tangent key placement with the `capTop` offset (§2) — pivot about the *finger
   contact sphere*, not the socket plane.
2. 7-point wall cross-section (§6) for exact wall thickness on slanted walls.
3. Flat-projection + cdt2d + concave-hull boundary detection (§6).
4. Explicit absolute thumb frames + a retent operator (§3/§4).
5. Wrist-rest footprint algorithm (§5) **with a new clearance parameter** — offset the
   case-side edge outward by `clearance` (user requires 1 mm). Cosmos cannot do this.
6. 0.1 mm / (1/45)° tuple codec only if URL parity with Cosmos is ever wanted.
