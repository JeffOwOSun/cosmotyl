"""Electronics in the base: XIAO rails + battery pocket on the bottom plate,
USB-C slot cut through the back skirt. Positions derive from the layout/feet
so they track design changes [M place/position duality].
"""
from config import BATTERY, CASE


def usb_slot_cut(layout, feet):
    """Through-cut for the XIAO's USB-C, centered under the index column's
    back edge. Slot 10x3.8 with 1mm chamfer allowance, axis along +y."""
    kx, _, _ = layout.key_position(1, 0)
    back_y = max(y for _, y in feet)
    z0 = CASE.bottom_t + 2.0 + 1.6      # plate + rails + PCB: slot bottom at USB body
    return (f'translate([{kx - 5:.2f},{back_y - 6:.2f},{z0:.2f}]) '
            f'cube([10, 12, 3.8]);')


def plate_additions(layout, feet):
    """Rails/pockets to union onto the bottom plate (plate top = bottom_t)."""
    t = CASE.bottom_t
    kx, _, _ = layout.key_position(1, 0)
    back_y = max(y for _, y in feet)
    adds = []
    # XIAO cradle: two side rails + front stop; open toward the back skirt so
    # the board slides in USB-first. PCB 21 x 17.8.
    bx, by = kx - 21.2 / 2, back_y - 2.0 - 18.2   # 2mm gap to skirt
    for dx in (-2.0, 21.2):
        adds.append(f'translate([{bx + dx:.2f},{by:.2f},{t}]) cube([2, 18.2, 3.6]);')
    adds.append(f'translate([{bx - 2:.2f},{by - 2:.2f},{t}]) cube([25.2, 2, 3.6]);')
    # battery pocket under the middle/ring home region: frame walls around
    # BATTERY.l x BATTERY.w, 4mm tall, 2mm thick, opening on the -y side wall
    # (cable exit toward the XIAO).
    cx, cy, _ = layout.key_position(2, 2)
    px, py = cx - BATTERY.l / 2, cy - BATTERY.w / 2 - 8
    w, l = BATTERY.w, BATTERY.l
    adds.append(f'translate([{px - 2:.2f},{py - 2:.2f},{t}]) cube([2, {w + 4:.1f}, 4]);')
    adds.append(f'translate([{px + l:.2f},{py - 2:.2f},{t}]) cube([2, {w + 4:.1f}, 4]);')
    adds.append(f'translate([{px:.2f},{py + w:.2f},{t}]) cube([{l:.1f}, 2, 4]);')
    adds.append(f'translate([{px:.2f},{py - 2:.2f},{t}]) '
                f'cube([{l * 0.35:.1f}, 2, 4]);')   # partial front wall = cable gap
    return adds
