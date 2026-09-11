# Layout preset and measurement method

The default in [`src/config.py`](../src/config.py) is a scan-derived example
layout. Its design dimensions are retained so the included meshes can be
reproduced. Raw hand traces and personal comfort analysis are not distributed.

Each finger trace was approximated by a line to estimate column position,
splay, and comfortable travel. Those inputs were adjusted for keycap clearance
before becoming the column table. Travel controls the bounded bowl radius and
column height; it is not a guarantee of reach or comfort for another hand.

To customize the layout, edit `COLUMNS`, `THUMB`, and `CASE` in `config.py`,
run the geometry checks, and inspect the generated model. The thumb fan is a
manually tuned circular approximation. Physical fit and print quality still
need to be checked on a prototype.
