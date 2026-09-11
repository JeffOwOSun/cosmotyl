#!/usr/bin/env python3
"""Build keywell_viewer.html: embeds the keywell generator's case STL
(right half + mirrored left) into a self-contained three.js artifact."""
import base64
import struct

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '..', 'output'))


def src_path(name):
    """Prefer a freshly generated STL next to the sources; fall back to the
    prebuilt copy in output/."""
    p = os.path.join(HERE, name)
    return p if '--prebuilt' not in sys.argv and os.path.exists(p) else os.path.join(OUT, name)


def parse_stl(path):
    """ASCII or binary STL -> (verts, tris) deduped; z-up -> three.js y-up."""
    data = open(path, 'rb').read()
    verts, vmap, tris = [], {}, []

    def add(p):
        p = (round(p[0], 3), round(p[2], 3), round(-p[1], 3))
        i = vmap.get(p)
        if i is None:
            i = len(verts)
            vmap[p] = i
            verts.append(p)
        return i

    if data[:5] == b'solid' and b'facet' in data[:300]:
        cur = []
        for line in data.decode('ascii', 'ignore').splitlines():
            parts = line.split()
            if parts[:1] == ['vertex']:
                cur.append(add(tuple(float(v) for v in parts[1:4])))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
    else:
        n = struct.unpack('<I', data[80:84])[0]
        off = 84
        for _ in range(n):
            tri = [add(struct.unpack_from('<3f', data, off + 12 + v * 12))
                   for v in range(3)]
            tris.append(tuple(tri))
            off += 50
    return verts, tris


def pack(verts, tris, dx, dy):
    pos = b''.join(struct.pack('<3f', v[0] - dx, v[1] - dy, v[2]) for v in verts)
    idx = b''.join(struct.pack('<3I', *t) for t in tris)
    return base64.b64encode(pos).decode(), base64.b64encode(idx).decode()


case_v, case_t = parse_stl(src_path('case_right.stl'))
case3_v, case3_t = parse_stl(src_path('case3_right.stl'))
uncut_v, uncut_t = parse_stl(src_path('uncut3_right.stl'))
plate_v, plate_t = parse_stl(src_path('bottom_right.stl'))
wrist_v, wrist_t = parse_stl(src_path('wrist_right.stl'))
dev_v, dev_t = parse_stl(src_path('devtool_right.stl'))
top4_v, top4_t = parse_stl(src_path('top4_right.stl'))
base4_v, base4_t = parse_stl(src_path('base4_right.stl'))
print(f'case: tris={len(case_t)} verts={len(case_v)}')
print(f'v4: top tris={len(top4_t)} base tris={len(base4_t)}')
print(f'case3: tris={len(case3_t)} verts={len(case3_v)}')
print(f'uncut: tris={len(uncut_t)} verts={len(uncut_v)}')
print(f'plate: tris={len(plate_t)} verts={len(plate_v)}')
print(f'wrist: tris={len(wrist_t)} verts={len(wrist_v)}')
print(f'devtool: tris={len(dev_t)} verts={len(dev_v)}')

allv = case_v + plate_v + wrist_v
minx = min(v[0] for v in allv)
miny = min(v[1] for v in allv)
maxx = max(v[0] for v in allv) - minx
maxy = max(v[1] for v in allv) - miny
minz = min(v[2] for v in allv)
maxz = max(v[2] for v in allv)
print(f'bbox: W={maxx:.1f} H={maxy:.1f} D={maxz - minz:.1f}')

case_pos, case_idx = pack(case_v, case_t, minx, miny)
case3_pos, case3_idx = pack(case3_v, case3_t, minx, miny)
uncut_pos, uncut_idx = pack(uncut_v, uncut_t, minx, miny)
plate_pos, plate_idx = pack(plate_v, plate_t, minx, miny)
wrist_pos, wrist_idx = pack(wrist_v, wrist_t, minx, miny)
dev_pos, dev_idx = pack(dev_v, dev_t, minx, miny)
top4_pos, top4_idx = pack(top4_v, top4_t, minx, miny)
base4_pos, base4_idx = pack(base4_v, base4_t, minx, miny)

import json, math
from config import CASE, COLUMNS, THUMB
from placement import _key_frame_raw, _orient, compute_lift, all_raw_frames, Layout
from transform import T, RX, RY, RZ, apply, compose, mat_mul

def to_three(pt):
    return [round(pt[0] - minx, 2), round(pt[2] - miny, 2), round(-pt[1], 2)]

lay = Layout()
o = _orient()
pre = [(k, mat_mul(o, m)) for k, m in all_raw_frames()]
lift = compute_lift(pre)
world_from_raw = mat_mul(T(0, 0, lift), o)

col = THUMB.anchor_col
r = COLUMNS[col].rows - 1
anchor_m_w = lay.key_frame(col, r)
anchor_rect = [to_three(apply(anchor_m_w, p)) for p in [
    (-CASE.key_w/2, -CASE.key_d/2, 0), (CASE.key_w/2, -CASE.key_d/2, 0),
    (CASE.key_w/2, CASE.key_d/2, 0), (-CASE.key_w/2, CASE.key_d/2, 0),
    (-CASE.key_w/2, -CASE.key_d/2, 0)]]

corner_raw = apply(_key_frame_raw(col, r), (-CASE.key_w / 2, -CASE.key_d / 2, 0))
ox, oy, oz = THUMB.offset
offset_xy_raw = (corner_raw[0] + ox, corner_raw[1] + oy, corner_raw[2])
cluster_raw = compose(
    T(corner_raw[0] + ox, corner_raw[1] + oy, corner_raw[2] + oz),
    RZ(THUMB.yaw), RY(THUMB.roll), RX(THUMB.pitch),
)
cluster_w = mat_mul(world_from_raw, cluster_raw)

corner_3 = to_three(apply(world_from_raw, corner_raw))
offset_xy_3 = to_three(apply(world_from_raw, offset_xy_raw))
t_world = [apply(lay.thumb_frame(i), (0, 0, 0)) for i in range(THUMB.keys)]
t_centers_3 = [to_three(p) for p in t_world]
tz0, tz1, tz2 = (p[2] for p in t_world)
pivot_3 = to_three(apply(cluster_w, (0, -THUMB.arc_R, 0)))

arc_pts_3 = []
for k in range(65):
    deg = -8.0 + k * (46.0 / 64.0)
    rad = math.radians(deg)
    lx = -THUMB.arc_R * math.sin(rad)
    ly = THUMB.arc_R * (math.cos(rad) - 1.0)
    arc_pts_3.append(to_three(apply(cluster_w, (lx, ly, 0))))

math_json = json.dumps({
    'anchor_rect': anchor_rect,
    'corner': corner_3,
    'offset_xy': offset_xy_3,
    't_centers': t_centers_3,
    'pivot': pivot_3,
    'arc_pts': arc_pts_3,
})

three_src = '/*\n' + open(os.path.join(HERE, 'vendor', 'three.LICENSE.txt')).read() + '\n*/\n' + open(os.path.join(HERE, 'vendor', 'three.min.js')).read()
viewer_css = open(os.path.join(HERE, 'viewer.css')).read()

page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cosmotyl — keyboard viewer</title>
<style>
{viewer_css}
  :root {{
    --background: #0b1020;
    --foreground: #f8fafc;
    --card: rgba(15, 23, 42, 0.88);
    --border: rgba(148, 163, 184, 0.28);
    --muted-foreground: #cbd5e1;
    --primary: #38bdf8;
  }}
  html, body {{ font-family: system-ui, sans-serif; margin: 0; height: 100%; overflow: hidden; background: var(--background); color: var(--foreground); }}
  #c {{ display: block; width: 100%; height: 100%; touch-action: none; cursor: grab; }}
  #c:active {{ cursor: grabbing; }}
  .panel {{ backdrop-filter: blur(10px); background: var(--card); color: var(--foreground); }}
  input[type=range] {{ accent-color: var(--primary); }}
</style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased">
<div class="relative w-full h-full">
  <canvas id="c"></canvas>

  <div class="panel absolute top-3 left-3 bg-[var(--card)]/90 border border-[var(--border)] rounded-xl p-4 shadow-lg w-64 select-none">
    <h2 class="font-semibold text-sm mb-0.5">Cosmotyl — v4 floating plates</h2>
    <p class="text-[var(--muted-foreground)] text-xs mb-3">Curved keywell + thumb pod on a base with screw columns ({len(top4_t) + len(base4_t)} triangles/half)</p>

    <label class="text-xs flex justify-between mb-1"><span>Half separation</span><span id="gapVal" class="text-[var(--muted-foreground)]"></span></label>
    <input id="gap" type="range" min="30" max="240" step="2" value="100" class="w-full mb-3">

    <div class="flex flex-col gap-1.5 text-xs">
      <label class="flex items-center gap-2"><input id="wire" type="checkbox"> Wireframe</label>
      <label class="flex items-center gap-2"><input id="left" type="checkbox" checked> Show left hand</label>
      <label class="flex items-center gap-2"><input id="v4" type="checkbox" checked> v4 two-piece: top sheet + base</label>
      <label class="flex items-center gap-2"><input id="v3" type="checkbox"> v3 body + rods + shell</label>
      <label class="flex items-center gap-2"><input id="math" type="checkbox" checked> Thumb math constraint</label>
      <label class="flex items-center gap-2"><input id="uncut" type="checkbox"> Uncut loft (before holes)</label>
      <label class="flex items-center gap-2"><input id="v1" type="checkbox"> v1 shell body</label>
      <label class="flex items-center gap-2"><input id="plate" type="checkbox"> Show bottom plate (v1)</label>
      <label class="flex items-center gap-2"><input id="wrist" type="checkbox"> Show wrist rest (v1)</label>
      <label class="flex items-center gap-2"><input id="dev" type="checkbox" checked> Switches + caps (devtool)</label>
    </div>

    <div class="mt-3 pt-2.5 border-t border-[var(--border)] text-[11px] leading-4 space-y-1">
      <div class="font-medium text-[var(--foreground)]">Thumb placement geometry:</div>
      <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400 shrink-0"></span><span>Anchor: inner(0,3) corner (z=50.5)</span></div>
      <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-orange-500 shrink-0"></span><span>Offset L-drop: Δz = −20.8 mm → t0</span></div>
      <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-fuchsia-400 shrink-0"></span><span>CMC pivot (0,−85,0) wrist side & R=85 spokes</span></div>
      <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 shrink-0"></span><span>Tilted arc C(θ): roll −24.8°, pitch −11.9° drops t0({tz0:.1f})→t1({tz1:.1f})→t2({tz2:.1f})</span></div>
    </div>
  </div>

  <div class="panel absolute bottom-3 left-3 bg-[var(--card)]/90 border border-[var(--border)] rounded-lg px-3 py-2 text-[11px] text-[var(--muted-foreground)] shadow">
    drag to orbit · scroll to zoom · Cosmotyl · offline viewer
  </div>
</div>
<script>{three_src}</script>
<script>
(function () {{
  'use strict';
  const PARTS = {{
    case: {{ pos: '{case_pos}', idx: '{case_idx}' }},
    case3: {{ pos: '{case3_pos}', idx: '{case3_idx}' }},
    uncut: {{ pos: '{uncut_pos}', idx: '{uncut_idx}' }},
    plate: {{ pos: '{plate_pos}', idx: '{plate_idx}' }},
    wrist: {{ pos: '{wrist_pos}', idx: '{wrist_idx}' }},
    dev: {{ pos: '{dev_pos}', idx: '{dev_idx}' }},
    top4: {{ pos: '{top4_pos}', idx: '{top4_idx}' }},
    base4: {{ pos: '{base4_pos}', idx: '{base4_idx}' }},
  }};

  function b64ToArr(b64, T) {{
    const s = atob(b64);
    const u = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
    return new T(u.buffer);
  }}

  const canvas = document.getElementById('c');
  const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true }});
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  const scene = new THREE.Scene();
  const light = document.documentElement.classList.contains('light');
  scene.background = new THREE.Color(light ? 0xf1f5f9 : 0x0b1020);
  scene.fog = new THREE.Fog(scene.background, 500, 900);

  const camera = new THREE.PerspectiveCamera(45, 2, 1, 2000);
  scene.add(new THREE.HemisphereLight(0xffffff, light ? 0x94a3b8 : 0x1e293b, light ? 0.9 : 0.7));
  const dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(-120, 220, 160);
  scene.add(dir);
  const dir2 = new THREE.DirectionalLight(0xffffff, 0.25);
  dir2.position.set(150, 100, -100);
  scene.add(dir2);
  scene.add(new THREE.GridHelper(800, 40, light ? 0x94a3b8 : 0x334155, light ? 0xcbd5e1 : 0x1e293b));

  const isClose = window.location.hash === '#closeup';
  let theta = isClose ? -0.55 : -0.35, phi = isClose ? 1.15 : 1.02, radius = isClose ? 165 : 420;
  const target = isClose
    ? new THREE.Vector3(75, 25, 45)
    : new THREE.Vector3(0, {maxy / 3:.0f}, {(minz + maxz) / 2:.0f});
  function updateCam() {{
    camera.position.set(
      target.x + radius * Math.sin(phi) * Math.sin(theta),
      target.y + radius * Math.cos(phi),
      target.z + radius * Math.sin(phi) * Math.cos(theta));
    camera.lookAt(target);
  }}
  let dragging = false, px = 0, py = 0;
  canvas.addEventListener('pointerdown', e => {{ dragging = true; px = e.clientX; py = e.clientY; canvas.setPointerCapture(e.pointerId); }});
  canvas.addEventListener('pointermove', e => {{
    if (!dragging) return;
    theta -= (e.clientX - px) * 0.005;
    phi = Math.min(2.99, Math.max(0.15, phi - (e.clientY - py) * 0.005));
    px = e.clientX; py = e.clientY; updateCam();
  }});
  canvas.addEventListener('pointerup', () => dragging = false);
  canvas.addEventListener('wheel', e => {{
    e.preventDefault();
    radius = Math.min(800, Math.max(120, radius * (1 + e.deltaY * 0.001)));
    updateCam();
  }}, {{ passive: false }});

  function makeGeo(part) {{
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(b64ToArr(part.pos, Float32Array), 3));
    g.setIndex(new THREE.BufferAttribute(b64ToArr(part.idx, Uint32Array), 1));
    g.computeVertexNormals();
    return g;
  }}

  const caseMat = new THREE.MeshStandardMaterial({{
    color: light ? 0x64748b : 0x7dd3fc,
    roughness: 0.55, metalness: 0.15,
    flatShading: true, side: THREE.DoubleSide,
  }});
  const plateMat = new THREE.MeshStandardMaterial({{
    color: light ? 0x475569 : 0xf9a8d4,
    roughness: 0.7, metalness: 0.05,
    flatShading: true, side: THREE.DoubleSide,
  }});
  const wristMat = new THREE.MeshStandardMaterial({{
    color: light ? 0xb45309 : 0xfcd34d,
    roughness: 0.8, metalness: 0.0,
    side: THREE.DoubleSide,
  }});
  const case3Mat = new THREE.MeshStandardMaterial({{
    color: light ? 0x0f766e : 0x5eead4,
    roughness: 0.5, metalness: 0.1,
    flatShading: true, side: THREE.DoubleSide,
  }});
  const uncutMat = new THREE.MeshStandardMaterial({{
    color: light ? 0x7c3aed : 0xc4b5fd, transparent: true, opacity: 0.55,
    roughness: 0.5, metalness: 0.0, depthWrite: false,
    flatShading: true, side: THREE.DoubleSide,
  }});
  const devMat = new THREE.MeshStandardMaterial({{
    color: 0xef4444, transparent: true, opacity: 0.45,
    roughness: 0.6, metalness: 0.0, depthWrite: false,
    side: THREE.DoubleSide,
  }});

  const base4Mat = new THREE.MeshStandardMaterial({{
    color: light ? 0x92400e : 0xfbbf24,
    roughness: 0.6, metalness: 0.05,
    flatShading: true, side: THREE.DoubleSide,
  }});

  const caseGeo = makeGeo(PARTS.case);
  const case3Geo = makeGeo(PARTS.case3);
  const uncutGeo = makeGeo(PARTS.uncut);
  const plateGeo = makeGeo(PARTS.plate);
  const wristGeo = makeGeo(PARTS.wrist);
  const devGeo = makeGeo(PARTS.dev);
  const top4Geo = makeGeo(PARTS.top4);
  const base4Geo = makeGeo(PARTS.base4);

  const MATH_DATA = {math_json};
  function makeMathGroup() {{
    const g = new THREE.Group();
    const v3 = p => new THREE.Vector3(p[0], p[1], p[2]);
    const sph = (p, r, col) => {{
      const m = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 16),
        new THREE.MeshBasicMaterial({{ color: col }}));
      m.position.copy(v3(p));
      return m;
    }};
    const line = (pts, col) => {{
      const geom = new THREE.BufferGeometry().setFromPoints(pts.map(v3));
      return new THREE.Line(geom, new THREE.LineBasicMaterial({{ color: col }}));
    }};
    // 1. Gold anchor key outline + corner sphere
    g.add(line(MATH_DATA.anchor_rect, 0xfacc15));
    g.add(sph(MATH_DATA.corner, 2.2, 0xfacc15));
    // 2. Orange L-shaped offset vector (corner -> offset_xy -> t0)
    g.add(line([MATH_DATA.corner, MATH_DATA.offset_xy, MATH_DATA.t_centers[0]], 0xf97316));
    g.add(sph(MATH_DATA.offset_xy, 1.9, 0xf97316));
    // 3. Magenta CMC pivot + radial spokes to t0, t1, t2
    g.add(sph(MATH_DATA.pivot, 2.6, 0xe879f9));
    for (const tc of MATH_DATA.t_centers) {{
      g.add(line([MATH_DATA.pivot, tc], 0xe879f9));
      g.add(sph(tc, 2.0, 0x22d3ee));
    }}
    // 4. Cyan arc curve C(theta)
    g.add(line(MATH_DATA.arc_pts, 0x22d3ee));
    // 5. Translucent amber tilted cluster plane sector (pivot -> arc_pts)
    const fanPos = [];
    for (let i = 0; i < MATH_DATA.arc_pts.length - 1; i++) {{
      fanPos.push(...MATH_DATA.pivot, ...MATH_DATA.arc_pts[i], ...MATH_DATA.arc_pts[i + 1]);
    }}
    const fanGeo = new THREE.BufferGeometry();
    fanGeo.setAttribute('position', new THREE.Float32BufferAttribute(fanPos, 3));
    fanGeo.computeVertexNormals();
    g.add(new THREE.Mesh(fanGeo, new THREE.MeshBasicMaterial({{
      color: 0xf59e0b, transparent: true, opacity: 0.22,
      side: THREE.DoubleSide, depthWrite: false
    }})));
    return g;
  }}

  const rightGroup = new THREE.Group();
  const leftGroup = new THREE.Group();
  const rCase = new THREE.Mesh(caseGeo, caseMat), rPlate = new THREE.Mesh(plateGeo, plateMat);
  const lCase = new THREE.Mesh(caseGeo, caseMat), lPlate = new THREE.Mesh(plateGeo, plateMat);
  const rCase3 = new THREE.Mesh(case3Geo, case3Mat), lCase3 = new THREE.Mesh(case3Geo, case3Mat);
  const rUncut = new THREE.Mesh(uncutGeo, uncutMat), lUncut = new THREE.Mesh(uncutGeo, uncutMat);
  const rWrist = new THREE.Mesh(wristGeo, wristMat), lWrist = new THREE.Mesh(wristGeo, wristMat);
  const rDev = new THREE.Mesh(devGeo, devMat), lDev = new THREE.Mesh(devGeo, devMat);
  const rTop4 = new THREE.Mesh(top4Geo, case3Mat), lTop4 = new THREE.Mesh(top4Geo, case3Mat);
  const rBase4 = new THREE.Mesh(base4Geo, base4Mat), lBase4 = new THREE.Mesh(base4Geo, base4Mat);
  const rMath = makeMathGroup(), lMath = makeMathGroup();
  rightGroup.add(rCase, rCase3, rUncut, rPlate, rWrist, rDev, rTop4, rBase4, rMath);
  leftGroup.add(lCase, lCase3, lUncut, lPlate, lWrist, lDev, lTop4, lBase4, lMath);
  leftGroup.scale.set(-1, 1, 1);
  scene.add(rightGroup, leftGroup);

  function apply() {{
    const gap = +document.getElementById('gap').value;
    document.getElementById('gapVal').textContent = gap + ' mm';
    rightGroup.position.x = gap / 2;
    leftGroup.position.x = -gap / 2;
    leftGroup.visible = document.getElementById('left').checked;
    rCase.visible = lCase.visible = document.getElementById('v1').checked;
    rCase3.visible = lCase3.visible = document.getElementById('v3').checked;
    rTop4.visible = lTop4.visible = rBase4.visible = lBase4.visible = document.getElementById('v4').checked;
    rUncut.visible = lUncut.visible = document.getElementById('uncut').checked;
    rPlate.visible = lPlate.visible = document.getElementById('plate').checked;
    rWrist.visible = lWrist.visible = document.getElementById('wrist').checked;
    rDev.visible = lDev.visible = document.getElementById('dev').checked;
    rMath.visible = lMath.visible = document.getElementById('math').checked;
    caseMat.wireframe = case3Mat.wireframe = base4Mat.wireframe = uncutMat.wireframe = plateMat.wireframe = wristMat.wireframe = document.getElementById('wire').checked;
  }}
  for (const id of ['gap', 'wire', 'left', 'v1', 'v3', 'v4', 'math', 'uncut', 'plate', 'wrist', 'dev']) {{
    document.getElementById(id).addEventListener('input', apply);
  }}

  function resize() {{
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== w || canvas.height !== h) {{
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }}
  }}
  new ResizeObserver(resize).observe(canvas);

  apply();
  updateCam();
  (function loop() {{ resize(); renderer.render(scene, camera); requestAnimationFrame(loop); }})();
}})();
</script>
</body>
</html>
"""
out = os.path.join(OUT, 'keywell_viewer.html')
open(out, 'w').write(page)
print(f'wrote {out}: {len(page) // 1024}KB')
