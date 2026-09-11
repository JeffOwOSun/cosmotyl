# UI reconstruction notes — "from scratch via Advanced menu" (2026-09-07)

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


## Goal
Rebuild Cosmotyl by driving Cosmos's real UI from the default keyboard, so all
pose relationships (esp. tent ↔ thumb cluster) are UI-owned and every slider
keeps working. Minimum deviation from stock.

## Why
User set Tenting 25°→12° in our encoded design and the thumb cluster
disconnected: our `thumbs_cluster()` bakes Ry(25°) into the thumb's absolute
pose, the UI only re-poses the fingers cluster.

## Target deltas from stock (everything else stays default)
1. 6 columns × 4 rows fingers; extra bottom-row key on middle+ring only
2. Thumb: builtin Curved preset, Number of Keys = 3
3. Part: MX + Skree flex PCB; XIAO nRF52840 (wireless); usb connector default
4. Tenting 25° (via the UI field so it stays live-editable)
5. Wrist rest on, widened (130mm max width, 5° taper)
6. Splay: inner +10.7, index +4.0, middle 0, ring −1.5, pinky −11.4, outer −11.4
   — via Advanced per-column splay if exposed, else Expert menu (user's ask).
   NOTE upstream bug: expert-mode PASTE crashes; small in-editor edits untested.
7. (Dropped for min-deviation: per-column custom stagger/curvature from scan)

## Facts learned
- (fill in as we go)

## State
- Step 1: inventory Advanced-mode controls on the DEFAULT keyboard.

## Session: keycap-wall issue hunt (2026-09-07 evening)

**Offender identified**: the 2 "keycap intersects walls at 3.6mm press" issues are a
THUMB keycap (per hand). Clicked the red cap → Edit Key shows fractional Row -0.06 /
Col 1.43, custom pose (-15.2, -9.9, 5) rot (10.5, -18.2, 2.2) = Curved-preset thumb key.

**Rejected levers** (issue count unchanged or worse):
- KeyboardExtra.web_min_thickness_factor 0.8→0.5 (field 1, float): no change, +2 benign; filament 192.5→188.9.
- Wall Z Offset 15→18 (kbd field 18=180): BREAKS wrist-rest wall locator (same failure wallXY-5 had).
- Wall XY 7→9 (field 17=90): generates fine, no issue change, +6m filament.
- Thumb H/V spacing 20→22 via UI inputs: WORSE (4 keycap-wall + 2 keycap-keycap).

**Root cause found by diffing old (cosmos_cm_url.txt, 229.5m, CLEAN: only 2 benign) vs new
(noprof, 192.5m)**: thumb KEYS byte-identical; cluster-level differs:
- field 4 block: OLD (1:220, 2:185, 3:1349, 4:0) = H 22 / V 18.5 / f3 1349(-15°?); NEW (200,200,0,0,+f6/f7=0)
- field 8 position: OLD 6236506098339 vs NEW 1705169061323
- field 9 rotation: OLD 25151491212243 vs NEW 27058591172781

**Fix strategy**: transplant old field 4 only (keep UI pose → tent-slider safe). If dirty,
transplant 4+8+9 (full old thumb) and re-run tent 25→12 acceptance test.

**ui_step.js gained `click x y`** (Input.dispatchMouseEvent). Banner must be COLLAPSED
before canvas clicks (expanded banner eats clicks). Edit Key tab at ~(1435,646).

## Session: thumb-doesn't-follow-tenting (2026-09-09)

User: "change tent to 12 → thumb clusters remain in place. Not what I wanted."

**Root cause is UPSTREAM Cosmos behavior, not our transplant:**
- Experiment: noprof (pure UI-built) tent 25→12 via UI → fingers rot 1165824→571392, thumb pose
  bytes UNCHANGED (8:1705169061323, 9:27058591172781).
- Stock keyboard (no #cm), tent 0→20 via UI → same: thumb pose identical to preset default;
  screenshot stock_tent20_clear.png (local capture, not included) shows stock thumb visibly staying flat.
- Source: config.cosmos.ts calcClusterTrsf = thumbPose ∘ fingerPosInv(inFlat=T) ∘ fingerPos(inFlat=F);
  the inv/fwd pair cancels in 3D ⇒ serialized thumb poses are ABSOLUTE world-space.
  Tenting Angle input rewrites ONLY fingers rotation [0, deg*45, 0].

**Fix: scratch/retent.py <url|file> <tent_deg> [wr_tent_deg]**
- Rewrites fingers rot; rotates thumb pose by Ry(Δ) about fingers position (pos AND rot,
  Euler order R = Rz(g)·Ry(b)·Rx(a), X applied first); sets KeyboardExtra field 14 (WR tenting ×45).
- Validation: retent 25→25 reproduces canonical URL byte-identical.
- retent 25→12: thumb VISIBLY follows tent (looks right), 2 benign notices only, filament 164.2m.

**Wrist-rest tenting fragility (OpenCascade error 24454592 "During processing of Wrist Rest"):**
- board 12 / WR 12: FAILS (reproducible, 2 gens)
- board 12 / WR 15: FAILS
- board 12 / WR 25: WORKS (164.2m)
- board 25 / WR 25: works (canonical)
- Guidance: keep WR tenting high (≈25°) or adjust via UI input after loading; if wrist gen
  fails, raise the 3rd retent arg.

---

## Session: stock thumb swap → FINAL design (tent 12/WR 12, USB-only)

**Thumb cluster replaced with stock "Curved, 3 keys" preset + nudge.**
- Byte-diff vs noprof: canonical differed ONLY in thumb fields 4 (spacing 22/18.5 vs 20/20) and 8/9 (pose).
- Stock preset as-is: 1 real keycap-wall error/hand. Nudge via scratch/move_thumb.py:
  (-2,-3,0) cleared reals; **(-4,-6,0) = zero errors zero warnings** (locked).

**WR fragility note above is OBSOLETE:** board 12 / WR 12 now WORKS — the OpenCascade
crash was tied to the OLD custom thumb geometry, not the WR angle itself. With the stock
thumb, retent.py 12/12 renders clean (149.7m pre-pad-fix).

**Wrist pad (field 15) empirical map:**
- position moves the pad body; Z honored. maxWidth (extra f11/f17) trims OUTER/pinky edge
  only; extension (extra f9/f16) is the FRONT edge; the case-side edge is ALWAYS conformal
  (generator is PRO/closed-source) — cannot be detached.
- Interference fixes that FAILED: thumb +6Y (4 real errors), pad -8Y, maxWidth cut, ext=0.
- Fix that WORKED: pad (+52, 0, -18) mm — +52 X ends pad at middle-column line (user spec:
  support only to the index-column trace), -18 Z clears thumb keycaps. move_wrist.py.

**Connectors (keyboard field 16):** 0402 (trrs+usb-average) → 02 (usb-average only).
Verified single slot per half in back-wall render. MCU holder unaffected (sized by MCU=74).

**Promotion (this date):** final URL → cosmos_cm_url{,_final,_t12}.txt; 25° twin via
retent.py 25/25 → cosmos_cm_url_t25.txt (198.8m, clean). Filament: 149.8m @ 12°.
Both bookmarks updated; 6 STLs re-exported; viewer rebuilt.

**Wrist-rest mesh extraction (viewer request):** the print STL is PRO-gated, but the
preview geometry lives in the page's three.js scene. Technique (scratch/extract_wrist.js):
inject `window.__THREE_DEVTOOLS__ = new EventTarget()` via Page.addScriptToEvaluateOnNewDocument
(captures 'observe' events -> renderer), wrap renderer.render to harvest the scene, traverse
meshes. Cosmos scene: ~190 meshes; keycaps 2380/932 tris; per-half hidden source group holds
case(3640t)/web(6080t)/plate-ish(1100t)/WRIST(528t)/floor(1122t)/holder(11512t); display
copies are parented under matrixWorld scale ±0.00322 (x negated = left mirror).
KEY FACT: raw geometry buffers are in mm in the EXACT same frame as the STL exports
(case raw bbox == caseright.stl bbox in x/y; z shifted +44.02 because export re-floors z=0).
So: grab buffers (base64 via CDP), apply z+=44.02, write binary STL -> cosmotyl-wristright.stl
(85.2 x 109.8 x 38.1 mm). Embedded in viewer with "Show wrist rests" toggle; left = x-mirror.
mesh_json_to_stl.py converts grabbed JSON generically (matrixWorld path also available).
