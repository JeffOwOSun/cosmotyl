# Dactyl Build Plan — Cosmos case + column flex PCBs + XIAO nRF52840

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


Companion to the 3D case viewer (historical artifact, not included) and [hand geometry report](hand_geometry_report.md).

> [!IMPORTANT]
> **Update 2026-09-10 — own generator (keywell v1) supersedes the Cosmos path.** The new procedural generator in `scratch/keywell/` builds the whole right half from the hand scan: home-row sockets land exactly on scan targets, 0 keycap collisions (OBB-verified), no-wall shell (curved web plate + 2 mm skirt lofted to a flat z=0 rim), 5× M3 heat-insert bosses aligned to a countersunk bottom plate by construction, XIAO cradle + USB slot at the index column, 50×35×6.5 battery pocket (LP603449 / 522332), and a conformal wrist pad with a **verified ≥1.0 mm gap** ending at the middle-column line. Printables: keywell-caseright.stl (legacy mesh; regenerate from the historical source), keywell-plateright.stl (legacy mesh; regenerate from the historical source), keywell-wristright.stl (legacy mesh; regenerate from the historical source) (left half = slicer mirror); explore in the [keywell viewer](../output/keywell_viewer.html). The Cosmos design below remains the printable fallback.




## Layout (per hand, 29 keys)

- 4 rows × 6 columns (num / top / home / bottom)
- +2 keys in a 5th row under **middle, ring** only (the index one was traded for a thumb key)
- +3 thumb keys on your measured 37° arc, centered on the anchor

## Cosmos settings (transcribe into Advanced mode at [ryanis.cool/cosmos](https://ryanis.cool/cosmos/))

> [!IMPORTANT]
> **Update — FINAL design: tent 12°, stock thumb + nudge, fully clean.** The design is UI-rebuilt from stock Cosmos (Out column toggle, MX+Skree switches, XIAO BT MCU, wrist-rest widths 130/taper 5°) with the scanned per-column geometry (splay, stagger, curvature) injected at column level, plus a 7 mm wall offset. The thumb cluster is now the **stock "Curved, 3 keys" preset nudged (−4, −6, 0) mm** — the earlier byte-transplanted custom thumb is retired, because the stock pose plus that small nudge renders with **zero errors and zero warnings** while staying a factory preset. **Tenting caveat (upstream Cosmos behavior)**: the UI's Tenting Angle field rotates *only the keywell* — thumb clusters are serialized as absolute world poses (`calcClusterTrsf` cancels the finger transform), so they never follow the slider. To retent the *whole board* (thumb + wrist rest included), run retent.py (historical artifact, not included): `python3 retent.py <url-file> <tent°> [wrist-rest-tent°]`. With the stock thumb geometry the old OpenCascade crash at wrist-rest angles < 20° is gone — the canonical design runs **tent 12° / wrist 12°**. Bookmarks: **"Cosmos Cosmotyl — FINAL (tent 12°)"** (canonical) and **"Cosmos Cosmotyl — tent 25° twin"** (same design retented). Expert-mode paste remains broken upstream (crashes on any config, still worth reporting at [github.com/rianadon/Cosmos-Keyboards](https://github.com/rianadon/Cosmos-Keyboards)).
>
> Collision status: **zero errors, zero warnings** at both 12° and 25°. The wrist pad is moved (+52, 0, −18) mm from Cosmos's default: +52 mm X ends the pad at the middle-finger column line (support only needs to reach the index-column trace, per hand-fit review) which also clears the thumb cluster, and −18 mm Z keeps it from burying the thumb keycaps. The connector cutout is **USB only** (`usb-average`) — the default TRRS jack was removed since the ZMK/BT build needs no interconnect cable.

The viewer artifact shows the target geometry; these are the numbers it encodes, converted to Cosmos's units. Curvature is derived from each finger's measured comfortable travel (tighter arc for shorter travel):


| Column | Stagger vs middle (mm) | Splay | Row curvature |
|---|---|---|---|
| inner (index-far) | +9.8 | +10.7° | ~21°/key |
| index | +4.3 | +4.0° | ~23°/key |
| middle | 0 | 0° | ~15°/key |
| ring | +2.4 | −1.5° | ~16°/key |
| pinky | +15.2 | −11.4° | ~18°/key |
| outer | +15.2 | −11.4° | ~18°/key |

Column spread: index→middle 17.9, middle→ring 20.4, ring→pinky 21.2 mm. Tenting **12°** (canonical; a 25° twin is bookmarked if you want more tent). Enable Cosmos's **wrist rest** generation — it produces a separate STL sized to the case front. Export **STL** (print) + **STEP** (backup for CAD tweaks).

> [!IMPORTANT]
> In Cosmos, delete the extra bottom-row key from all columns except index/middle/ring — click keys to remove them in Advanced mode. The thumb cluster needs no edits: it is the stock **Curved, 3 keys** preset. Key count drives everything downstream (flex PCB lengths, ZMK matrix).

## Corrected keywell geometry (collision-verified)

Naive spacing collides on a concave MX keywell, so these constraints are baked into the generated case and the viewer, and verified by a 3D OBB separating-axis check over every keycap pair (frustum cap model: 18.3 mm base, 13 mm top) — **0 collisions**:

- **Row angular pitch is clearance-derived**: `Δθ = 18.9 mm / (R − 7 mm)`, because cap bases converge by factor (R−7)/R on a bowl of plate-radius R. This is why real Dactyls show gaps between rows.
- **Plate radii clamped to 55–75 mm** (per-finger from travel: index 55, middle 74, ring 67, pinky 60); anything tighter physically cannot clear MX caps.
- **Spreads widened over the raw scan** (index→middle 20.9, middle→ring 20.4, ring→pinky 22.7, pinky→outer 19 mm) so splay-converging near rows keep ≥1.7 mm cap clearance.
- **Thumb anchor at (−14, 57) mm** from the inner column origin, clearing the inner-bottom and index-extra keys.
- The outer column rides 3.6 mm forward of the pinky column — intentional, from cumulative splay (the pinky sweeps an arc to reach it).

## Final print files (Cosmos-generated) — print these

Exported straight from the final Cosmos session (open the **"Cosmos Cosmotyl — FINAL (tent 12°)"** bookmark to re-download or tweak; **"Cosmos Cosmotyl — tent 25° twin"** is the same design at 25°):

| File | Part |
|---|---|
| cosmotyl-caseright.stl (historical artifact, not included) / left (historical artifact, not included) | Main case (57k tris each) |
| cosmotyl-plateright.stl (historical artifact, not included) / left (historical artifact, not included) | Screw-on bottom plate |
| cosmotyl-holderright.stl (historical artifact, not included) / left (historical artifact, not included) | XIAO microcontroller holder |

- View them in cosmotyl_viewer.html (historical artifact, not included) — the exact meshes, both hands, orbit/zoom, now **including the wrist rests** (toggleable). The pad mesh (cosmotyl-wristright.stl (historical artifact, not included), 528 tris) was extracted from Cosmos's own three.js preview scene since the print-grade wrist STL is PRO-gated — its frame matches the case export exactly (x/y bboxes align to 0.01 mm), so it's positionally exact, just coarser than a print mesh.
- Hardware per Cosmos: **14× M3×6 mm countersunk screws + 14 heat-set inserts** (both hands total) fasten the plates.
- The **wrist rest** STL is PRO-gated in Cosmos — open the bookmark and export it there if you have PRO, or print without it first (the case stands on its walls). It's **130 mm max width with a 5° taper**, shifted **(+52, 0, −18) mm** from Cosmos's default: the +52 mm X retreat ends the pad at the middle-finger column line — palm support only needs to reach the index-column trace, and this also keeps it clear of the thumb cluster — while −18 mm Z stops it from crowding the thumb keycaps.
- The back wall has a **single USB cutout per half** (`usb-average`, fits most USB-C overmolds; `usb-slim` is snugger if you prefer). No TRRS — the BT build needs no interconnect.
- Total ≈ **149.8 m of filament** (~450 g) for everything at tent 12°; the 25° twin is 198.8 m (~590 g) because taller walls.

## Generated case files (SCAD fallback draft)

- dactyl_case.scad (historical artifact, not included) — parametric source (right half). Regenerate via gen_case.py (historical artifact, not included), which re-runs the collision check on every change.
- dactyl_case_right.stl (historical artifact, not included) — rendered mesh, verified **manifold and single-connected** (4322 triangles, one component).
- dactyl_case_left.stl (historical artifact, not included) — left hand, an exact X-mirror of the right (rendered via OpenSCAD `mirror()`, same 4322 facets), valid because the layout was derived from your right-hand scan and mirrored symmetrically.
- dactyl_stl_viewer.html (historical artifact, not included) — interactive three.js viewer of the **actual STL meshes** (both hands, orbit/zoom, gap slider, wireframe) — the exact geometry your slicer will see, embedded so it works offline.
- Features: 4 mm plates with **14.15 mm MX cutouts + 1.5 mm clip undercuts**, hulled web, world-vertical walls to the floor at 25° tent (stands on its own), USB-C and power-switch cutouts in the back wall, and a `fit_test()` coupon module — **print the coupon first** (2 min) and adjust `MX_HOLE` for your printer's shrink before committing to the full case.

````carousel

<!-- slide -->

<!-- slide -->

````

> [!NOTE]
> This SCAD case is a functional draft — correct geometry, cutouts, and stands at tent angle — but Cosmos still produces a more refined production case (rounded walls, screw bosses, bottom plate with feet). Recommended path: print the SCAD draft to validate reach/comfort cheaply, then transcribe the same numbers into Cosmos for the final.

## Electronics space (measured at 25° tent)

The web underside sits **~39 mm above the floor at the battery bay** (under the middle num row) and **~66 mm at the XIAO bay** (back wall, index side) on the 25° twin; at the canonical 12° tent the case is lower, but clearance still dwarfs the parts — the tallest component stack is the 5.6 mm LiPo, and even the shallow thumb-side walls exceed that. Mount the battery on the floor with VHB tape near the tall inner side; mount the XIAO against the back wall aligned to the USB-C cutout.


## Electronics: the pin budget is a perfect fit

The **XIAO nRF52840 exposes exactly 11 GPIOs (D0–D10)**, and your matrix needs exactly **6 columns + 5 rows = 11 pins** — zero pins wasted, no expander needed. The 3 thumb keys wire into the unused row-5 positions of the inner, index, and pinky columns, so 29 keys fit a 5×6 matrix with one hole.

| XIAO pin | Function |
|---|---|
| D0–D5 | col0–col5 (inner→outer) |
| D6–D10 | row0–row4 (num→extra/thumb) |
| BAT+/BAT− pads (underside) | LiPo — charger is built in |

Battery sensing uses the XIAO's internal divider (no GPIO cost); ZMK supports it out of the box. You have 8 XIAOs = 2 per keyboard + 6 spares/prototypes.

## Column flex PCBs — two real options

Per-column flexible strips with hotswap sockets + per-key diodes pre-soldered; you bend them into the keywell curvature, so soldering shrinks to ~11 wires per half:

1. **Pumpkin Patch PCBs** (Cosmos-native, from the Cosmos/Lemon store): fully interconnected flex columns with FPC ribbon tails and RGB. Designed for zero-solder use with the **Lemon** microcontroller's FPC connectors. With a XIAO instead, you either solder the tail pads directly or add a **Skree translator** board (FPC connector → plain pads). Cosmos generates matching PCB cutouts in the case when you select them.
2. **Skree flex PCBs** ([skree.us](https://skree.us)): column strips with plain solder pads — 1 column wire per strip + daisy-chained row wires across strips. No adapter needed for the XIAO; slightly more soldering (~17 joints/half), which is still trivial next to handwiring 58 diodes.

**Decision (made): Skree strips + XIAO, MX switches.** This skips the Lemon/translator dependency, your soldering background makes 17 joints a non-issue, and every part is orderable today.

> [!WARNING]
> Column flex PCBs are overwhelmingly **MX hotswap**. The choc-spacing argument from the flat-PCB plan no longer applies — the keywell curvature is what solves your index finger's short 33.8 mm travel — so build MX and pick from the whole switch market.

## ZMK config sketch

Board is upstream in ZMK as `seeeduino_xiao_ble`; you write a shield:

```
# build.yaml
include:
  - board: seeeduino_xiao_ble
    shield: yushi_dactyl_left
  - board: seeeduino_xiao_ble
    shield: yushi_dactyl_right
```

```dts
/* yushi_dactyl.dtsi — kscan + matrix transform */
kscan0: kscan {
    compatible = "zmk,kscan-gpio-matrix";
    diode-direction = "col2row";   /* verify against strip silkscreen */
    col-gpios = <&xiao_d 0 GPIO_ACTIVE_HIGH>, ...;  /* D0-D5 */
    row-gpios = <&xiao_d 6 (GPIO_ACTIVE_HIGH | GPIO_PULL_DOWN)>, ...;  /* D6-D10 */
};
```

Left half = central (`zmk,split-role = central` via shield defconfig), right = peripheral. Adapt an existing keymap to the final matrix.

## BOM (both hands)

| Part | Qty | Est. cost |
|---|---|---|
| Cosmos case + wrist rest prints (PETG, ~450 g) | 2+2 | ~\$15 filament |
| Seeed XIAO nRF52840 | 2 | already owned (×8) |
| Column flex PCB strips (4-key ×8, 5-key ×4) + 6 single thumb sockets | 12+6 | \$35–60 |
| MX hotswap switches | 58 | \$25–45 |
| LiPo 601230–502030 (250–400 mAh), JST or direct-solder | 2 | \$10–14 |
| Power slide switch + M3 heat-set inserts + screws | 2 sets | ~\$8 |
| Keycaps (MT3/DSA blank recommended for keywells) | 58 | \$30–60 |

## Build order

1. Print **one right-half case in PLA** at the 12° tent; dry-fit switches in the well, live-test reach on all 5 index/middle/ring rows for a few days.
2. Iterate curvature/stagger in Cosmos if any column feels off (each reprint ≈ \$2, overnight).
3. When the shape is right: print both halves + wrist rests in PETG, install flex strips + XIAOs + batteries, flash ZMK.
4. Keep a familiar keyboard available while evaluating the prototype.
