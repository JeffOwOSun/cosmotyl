"""Build the right half: emit SCAD, render STL + preview PNGs.

Usage: python3 main.py [--fast]   (--fast skips the STL render)
"""
import subprocess
import sys
import os
from pathlib import Path

from render import render, openscad

from bottom import bottom_plate_scad, case_bosses, screw_sites
from config import CASE
from devtool import devtool_scad, interference_scad
from electronics import plate_additions, usb_slot_cut
from placement import Layout
from skirt import skirt
from verify import report
from web import plates_and_holes, webs
from wrist import footprint, verify_clearance, wrist_scad

OUT_SCAD = 'case_right.scad'
OUT_STL = 'case_right.stl'
OUT_PLATE_SCAD = 'bottom_right.scad'
OUT_PLATE_STL = 'bottom_right.stl'
OUT_WRIST_SCAD = 'wrist_right.scad'
OUT_WRIST_STL = 'wrist_right.stl'
OUT_DEV_SCAD = 'devtool_right.scad'
OUT_DEV_STL = 'devtool_right.stl'


def build_scad(layout):
    plates, holes = plates_and_holes(layout)
    web_solids = webs(layout)
    skirt_solids, feet = skirt(layout)
    sites = screw_sites(feet)
    boss_solids, boss_cuts = case_bosses(sites)
    usb = usb_slot_cut(layout, feet)
    scad = f'''// Auto-generated Cosmotyl right half (Z-up, floor at z=0).
$fn = 24;
difference() {{
  union() {{
    {' '.join(plates)}
    {' '.join(web_solids)}
    {' '.join(skirt_solids)}
    {' '.join(boss_solids)}
  }}
  {' '.join(holes)}
  {' '.join(boss_cuts)}
  {usb}
  translate([-200,-300,-50]) cube([600,600,50]);  // floor clip
}}
'''
    open(OUT_SCAD, 'w').write(scad)
    open(OUT_PLATE_SCAD, 'w').write(
        bottom_plate_scad(feet, sites, plate_additions(layout, feet)))
    open(OUT_WRIST_SCAD, 'w').write(wrist_scad(layout, feet))
    open(OUT_DEV_SCAD, 'w').write(devtool_scad(layout))
    _, back = footprint(layout, feet)
    gap = verify_clearance(feet, back)
    print(f'wrist<->case min gap: {gap:.2f} mm (need >= 1.0)')
    if gap < 0.99:
        sys.exit('wrist clearance violated')
    return feet


def render_previews():
    views = {
        'iso':   '--camera=45,-90,20,55,0,25,420',
        'top':   '--camera=45,-45,0,0,0,0,500',
        'front': '--camera=45,-45,20,90,0,0,420',
        'side':  '--camera=45,-45,20,90,0,90,420',
    }
    for name, cam in views.items():
        import shutil
        prefix = ['xvfb-run', '-a'] if shutil.which('xvfb-run') else []
        subprocess.run(prefix + [openscad(), '-o', f'preview_{name}.png',
                        cam, '--imgsize=1100,800', '--colorscheme=Tomorrow Night',
                        OUT_SCAD], check=True, capture_output=True)
        print(f'preview_{name}.png')


def main():
    layout = Layout()
    bad = report(layout)
    if bad:
        sys.exit('verification failed; not rendering')
    build_scad(layout)
    print(f'\nwrote {OUT_SCAD}')
    if '--preview' in sys.argv:
        render_previews()
    if '--fast' not in sys.argv:
        render(OUT_SCAD, OUT_STL)
        print(f'wrote {OUT_STL}')
        render(OUT_PLATE_SCAD, OUT_PLATE_STL)
        print(f'wrote {OUT_PLATE_STL}')
        render(OUT_WRIST_SCAD, OUT_WRIST_STL)
        print(f'wrote {OUT_WRIST_STL}')
        render(OUT_DEV_SCAD, OUT_DEV_STL)
        print(f'wrote {OUT_DEV_STL}')
        layout = Layout()
        open('interference.scad', 'w').write(interference_scad(layout))
        render('interference.scad', 'interference.stl', expect_empty=True)


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    main()
