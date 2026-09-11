"""OpenSCAD rendering helpers with fail-closed interference checks."""
import os
from pathlib import Path
import shutil
import subprocess


def openscad():
    configured = os.environ.get('OPENSCAD')
    if configured:
        return configured
    found = shutil.which('openscad')
    if found:
        return found
    mac_app = Path('/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD')
    if mac_app.is_file():
        return str(mac_app)
    raise RuntimeError('OpenSCAD not found. Install it or set OPENSCAD to its executable.')


def render(scad, stl, *, expect_empty=False):
    # Never inspect an output left behind by an earlier successful run.
    Path(stl).unlink(missing_ok=True)
    result = subprocess.run([openscad(), '-o', str(stl), str(scad)],
                            capture_output=True, text=True)
    message = (result.stdout or '') + (result.stderr or '')
    # A missing import can also produce an empty intersection; reject warnings.
    if 'ERROR:' in message or 'WARNING:' in message:
        raise RuntimeError(f'OpenSCAD diagnostic for {scad}:\n{message}')
    if expect_empty and 'top level object is empty' in message.lower():
        print(f'{scad}: CLEAN (empty intersection)')
        return
    if result.returncode:
        raise RuntimeError(f'OpenSCAD failed for {scad}:\n{message}')
    if expect_empty:
        raise RuntimeError(f'{scad}: INTERFERES; inspect {stl}')
    if not Path(stl).is_file() or not Path(stl).stat().st_size:
        raise RuntimeError(f'OpenSCAD produced no mesh for {scad}')
