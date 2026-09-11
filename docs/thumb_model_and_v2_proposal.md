# Thumb Placement Model + v2 Pipeline Proposal

> Historical design notes. Some experiments and referenced artifacts are not
> included in this repository; see the root README for the current build.


Deliverable for feedback items #4–#6 (2026-09-10). Sources: [thumb_placement_models.md](research/thumb_placement_models.md) (Dactyl/Manuform/Dometyl/Cosmos source analysis, file+line cited) and [thumb_kinematics_web.md](research/thumb_kinematics_web.md) (biomechanics + community literature).

## 1. The thumb placement model (#4)

**Recommendation: a planar circular fan arc about the CMC pivot, anchored through the finger pipeline.** This is simultaneously the biomechanically correct model and the one the best-engineered generator (dometyl) uses.

Why this is the right curve, not just a convenient one:

- With the palm planted, pure thumb flexion–extension is rotation about ONE fixed axis in the trapezium (Hollister et al. 1992), so the thumb tip traces a **circle** — the anatomically exact curve for a key row reached by the cheapest 1-DOF motion.
- The exact anatomical refinement (two skew axes, ~124° apart, ~9.2 mm offset) collapses to the same circle within <1.5 mm over a 3-key sweep, so nothing fancier is justified.
- Comfortable sweep radius from HCI research: **63–76 mm** (CHI 2014 thumb-area studies); dometyl ships R = 85; our scan's straight-looking 42 mm trace is consistent with any R ∈ [70, 100] (sagitta at R = 85 over 42 mm is only 2.6 mm — below trace noise).
- Every project that beats hand-tuned offsets uses exactly this: dometyl's fan (R = 85, 14.4°/key about a fixed center), Cosmos `placeOnSphere` (same thing plus dome curvature), Keyboardio's physical "thumb arc".

### The expression

**Anchor — derived through the pipeline, never absolute** (the Manuform/Cosmos pattern; this is what makes the cluster follow stagger/curvature/tent changes automatically):

$$A = M_{\text{index,bottom}} \cdot T(-29, -30, 0)$$

where \(M_{\text{index,bottom}}\) is the world frame of the index-column bottom key and (−29, −30) mm is **your measured thumb-rest offset** from the hand scan.

**Cluster frame** (heading measured, tilts converged from 3 projects):

$$F = A \cdot R_z(-37°) \cdot R_y(\beta_t) \cdot R_x(\alpha_t) \cdot T(0,0,z_t)$$

with your measured −37° arc heading; β_t = −25° roll toward the thumb pad (Manuform −23…−35°, Cosmos Curved −24.8°, dometyl −20° all converge here); α_t = +10° pitch; z_t = −7 mm drop.

**The curve** (in frame F, arc center on the palm side approximating the CMC pivot):

$$C(\theta) = \big(R\sin\theta,\; R(1-\cos\theta),\; 0\big), \qquad R = 85\text{ mm (tunable 70–100)}$$

**Moving frame + key poses**: tangent \(\hat T(\theta) = (\cos\theta, \sin\theta, 0)\), normal \(\hat N\) pointing at the arc center, binormal \(\hat B = \hat z_F\):

$$M_i = F \cdot [\hat T(\theta_i) \mid \hat N(\theta_i) \mid \hat B \mid C(\theta_i)] \cdot R_{\hat T}(\rho_i), \qquad \theta_i = (i - i_{\text{home}}) \cdot p / R$$

with key pitch p = 20 mm (current thumb pitch) → 13.5°/key, matching dometyl's 14.4° and the biomechanical 14.6° at R = 75. Optional cup roll ρ_i = −10°·(i − i_home) tilts outer keys toward the pad (upgrade path = Cosmos dome).

**Sanity checks built in**: 3-key span = 2p = 40 mm ≤ your measured 42 mm comfortable span; total sweep 27° ≤ 35° budget (⅔ of the 53° FE range of motion); home key at the rest pose θ₀, not mid-arc.

**Free parameters and their status**: measured — anchor (−29,−30), heading −37°, span budget 42; defaulted-but-bounded — R = 85 ∈ [70,100], β_t = −25°, α_t = +10°, z_t = −7, ρ = 0. The devtool collision gate + your visual review tune the last four.

## 2. Connector generation by sweep (#5)

Exactly your procedure, expressed against C(θ). Right-half frame (mirror of your left-hand description — the innermost thumb key's inner face points toward **+x**/the main board):

1. Place thumb keys on C(θ), loft adjacent keys into a single row (pairwise hulls along \(\hat T\)).
2. Take the **inner side face** of the innermost key t0: the rectangle at local +HW spanning the socket depth and plate thickness.
3. **Sweep** that profile along C(θ) extended past θ₀ (toward the board): sample θ at 2–3° steps, place the profile with the moving frame at each sample, hull consecutive profiles.
4. Stop when the swept profile is fully inside the main body; **cut** the overlap (boolean subtract body), keeping the sweep watertight against it.
5. Loft/fillet the seam ring where the sweep meets the body.

Because the sweep follows the same curve the keys sit on, the connector is tangent-continuous with the thumb row by construction — no more misaligned loft between unrelated frames (the current index→pod hulls).

## 3. v2 pipeline (#6) — Bezier-surface body

Restating your algorithm with implementation specifics:

| Step | What | Implementation notes |
|---|---|---|
| A | Solid (hole-less) socket blocks at every key pose (fingers + thumb on C(θ)) | trivial change: today's plates without the hole cut |
| B | Loft into a continuous reference solid | today's hull machinery, but between full blocks → every face continuous; this reference defines the **bottom** and the minimum top |
| C | Bezier control net: one control curve per column (control points at that column's socket centers + normal offset), rows roughly x-aligned; tensor-product patch evaluated on a dense grid → polyhedron | pure Python; no CGAL needed for surface eval |
| D | Thumb cluster columns join the net as additional control columns (via C(θ) frames) | the surface flows over the connector region — this is what makes the seam smooth |
| E | Verify surface ≥ reference top everywhere (sample reference top corners against patch; push control points up where violated); body = volume between patch and B's bottom | iterate until zero violations |
| F | Cuts in order: (1) flat mount pocket per key (key_w × key_d, normal to key frame, down to socket-top plane — restores the flat seat + the ~1.5 mm clip thickness MX needs), (2) 14.15 through-hole + clip undercut, (3) bottom hollow | pocket before hole, exactly as you specified |
| G | Gate: `intersection(body, devtool) = ∅` where devtool = switches + XDA caps + 4 mm travel envelopes + underside housings/pins | already built and running — today's build reports **CLEAN** |

**No walls at all** (#2): the v2 body is a thick curved slab — the skirt disappears. Consequences to sign off on: M3 bosses become pillars hanging from the slab underside to the bottom-plate plane; the XIAO + USB port mount moves to the **bottom plate** (cradle already lives there; the slot becomes a notch in the slab's back edge or a bottom-plate-mounted port); the bottom plate keeps the current foot-polygon outline.

## 4. Already done this session (items #1–#3)

- **3-key thumb**: config + web + skirt generalized; build is green with 0 keycap collisions.
- **Devtool**: switches + caps + travel envelopes render as a translucent red toggle in the [viewer](../output/keywell_viewer.html), and the build now runs the intersection gate — currently **CLEAN** (even the ugly seam doesn't invade any switch/cap volume; it's an aesthetic/printability problem, which v2's surface fixes properly).

## Decision requested

1. **Thumb model**: planar fan arc as specced (R=85 default, pipeline anchor, your scan's −29/−30/−37°) — OK to implement?
2. **v2 pipeline**: proceed with A–G as tabled, replacing the current web+skirt entirely?
3. **Electronics relocation** (consequence of no-wall): XIAO/USB on the bottom plate, bosses as underside pillars — OK?
