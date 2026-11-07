"""Blue Comet Diner: a stainless-steel roadside diner on its own parking lot (original design,
thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py diner
  blender --background --python build_diner.py -- OUT_DIR [--face S] [--no-render] [--samples N] [--res F]

Diner car: blue tile plinth, fluted stainless skin, a ribbon of windows (printed booths, counter,
stools and pendant lamps behind glass), blue enamel band with chrome trim and a cyan neon strip,
rolled roof edge. Glass-block entrance vestibule with steps and a chrome double door. Roof sign
"BLUE COMET DINER" outlined in red neon. Pylon sign at the street with OPEN 24 HOURS.
Brick kitchen annex behind with exhaust hood, back door and a dumpster. Parking: a row of stalls
in front, a column on the east side, wheel stops, two lot lights, planters, a low kerb.

Lot 46 x 50 m, origin = lot centre, z 0 = lot surface; place it at y 0.3 (0.3 below the kerb).
The entrance drive (meta "driveways") is at the west end of the front edge.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\diner")
NAME = model_name("Diner", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(21)

LX, LY0, LY1 = 23 * M, -25 * M, 25 * M          # lot half width, front, back
DX0, DX1, DY0, DY1 = -14 * M, 8 * M, -8 * M, 2 * M   # diner car
FL = 0.9 * M                                     # diner floor height
DRIVE = (-22 * M, -15 * M)                       # entrance drive (x range at the front edge)

for name, sheet, tile in (("Steel", "DinerSteel", (1 * M, 1 * M)), ("Blue", "DinerBlue", (1 * M, 1 * M)),
                          ("Red", "DinerRed", (1 * M, 1 * M)), ("Tile", "DinerTile", (1 * M, 1 * M)),
                          ("Kitchen", "KitchenBrick", (1.6 * M, 1.6 * M)), ("Roof", "RoofTar", (4 * M, 4 * M)),
                          ("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("GlassBlock", "GlassBlock", (1 * M, 1 * M)), ("AcBody", "HvacGrey", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("DinerInterior", "DinerSigns", "DinerDoor"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Chrome", (0.80, 0.81, 0.83), 0.2, 1.0, 0), ("Dark", (0.05, 0.05, 0.055), 0.5, 0.3, 0),
                                      ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0), ("Dumpster", (0.12, 0.30, 0.18), 0.6, 0.4, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
                                      ("NeonRed", (1.0, 0.16, 0.12), 0.4, 0, 6.0), ("NeonCyan", (0.24, 0.92, 1.0), 0.4, 0, 6.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats(frame=(0.80, 0.81, 0.83), sill=(0.80, 0.77, 0.70))      # Pipe (downpipes)


def quad_uv(part, corners, box):
    u0, v0, u1, v1 = box
    K.quad(part, corners, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


def sign_y(part, x0, x1, y, z0, z1, box, both=True, gap=0.06 * M):
    """Printed panel facing -Y at y; the back face (+Y) sits gap behind it."""
    quad_uv(part, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], box)
    if both:
        quad_uv(part, [(x1, y + gap, z0), (x0, y + gap, z0), (x0, y + gap, z1), (x1, y + gap, z1)], box)


def neon_frame(part, x0, x1, y, z0, z1, t=0.06 * M):
    for (a0, a1, b0, b1) in ((x0, x1, z0, z0 + t), (x0, x1, z1 - t, z1), (x0, x0 + t, z0, z1), (x1 - t, x1, z0, z1)):
        K.boxr(part, a0, a1, y - t, y, b0, b1)


# ---------------------------------------------------------------- lot
K.boxr("Asphalt", -LX, LX, LY0, LY1, -0.5 * M, 0)
for (x0, x1) in ((-LX, DRIVE[0]), (DRIVE[1], LX)):                                     # low kerb on the front edge
    K.boxr("Pave", x0, x1, LY0, LY0 + 0.3 * M, 0, 0.15 * M)
for sx in (-1, 1):
    a, b = sorted((sx * LX, sx * (LX - 0.3 * M)))
    K.boxr("Pave", a, b, LY0 + 0.3 * M, LY1, 0, 0.15 * M)
K.boxr("Pave", -LX + 0.3 * M, LX - 0.3 * M, LY1 - 0.3 * M, LY1, 0, 0.15 * M)
# chain-link-free back fence: timber posts + rails along the back
for i in range(24):
    x = -LX + 1 * M + i * (2 * LX - 2 * M) / 23
    K.boxr("Dark", x - 0.06 * M, x + 0.06 * M, LY1 - 0.22 * M, LY1 - 0.1 * M, 0.15 * M, 1.6 * M)
for z in (0.6 * M, 1.4 * M):
    K.boxr("Dark", -LX + 1 * M, LX - 1 * M, LY1 - 0.25 * M, LY1 - 0.21 * M, z, z + 0.08 * M)


def stall_lines_x(x0, n, w, y0, y1):
    """n stalls side by side along x (lines run along y), wheel stops at y1 end."""
    for i in range(n + 1):
        x = x0 + i * w
        K.boxr("LotLine", x - 0.06 * M, x + 0.06 * M, y0, y1, 0, 0.012 * M)
    for i in range(n):
        x = x0 + (i + 0.5) * w
        K.boxr("Pave", x - 0.9 * M, x + 0.9 * M, y1 - 0.9 * M, y1 - 0.65 * M, 0, 0.14 * M)


def stall_lines_y(x0, x1, y0, n, w, stop_at_x):
    for i in range(n + 1):
        y = y0 + i * w
        K.boxr("LotLine", x0, x1, y - 0.06 * M, y + 0.06 * M, 0, 0.012 * M)
    for i in range(n):
        y = y0 + (i + 0.5) * w
        K.boxr("Pave", stop_at_x - 0.25 * M, stop_at_x, y - 0.9 * M, y + 0.9 * M, 0, 0.14 * M)


stall_lines_x(DX0, 3, 2.8 * M, -15 * M, -10.2 * M)        # west of the steps
stall_lines_x(1.4 * M, 2, 2.8 * M, -15 * M, -10.2 * M)     # east of the steps
stall_lines_y(14 * M, 19 * M, -8 * M, 7, 2.8 * M, 19 * M)  # east column, nose to the east kerb
stall_lines_x(-12 * M, 12, 2.8 * M, 18.4 * M, 23.6 * M)     # back row along the fence
for k in range(7):                                          # shade trees in a strip behind the annex
    K.shrub(-10 * M + k * 2.6 * M, 13.2 * M, 0.16 * M, rng.uniform(0.45, 0.6) * M, rng)
K.boxr("Pave", -11 * M, 6 * M, 12.6 * M, 13.8 * M, 0, 0.16 * M)
for i in range(18):
    x = -LX + 3 * M + i * 2.4 * M
    K.boxr("LotLine", x, x + 0.9 * M, -20.1 * M, -19.9 * M, 0, 0.012 * M)
# entry arrow at the drive
ax = (DRIVE[0] + DRIVE[1]) / 2
K.boxr("LotLine", ax - 0.12 * M, ax + 0.12 * M, -24 * M, -21.6 * M, 0, 0.012 * M)
K.quad("LotLine", [(ax - 0.7 * M, -21.6 * M, 0.012 * M), (ax + 0.7 * M, -21.6 * M, 0.012 * M), (ax, -20.6 * M, 0.012 * M)])

# ---------------------------------------------------------------- diner car
K.boxr("Tile", DX0, DX1, DY0, DY1, -0.3 * M, FL)                                    # plinth
K.boxr("Chrome", DX0 - 0.04 * M, DX1 + 0.04 * M, DY0 - 0.04 * M, DY1, FL - 0.06 * M, FL)
WZ0, WZ1 = 1.25 * M, 2.75 * M
# walls: steel below and around the window ribbon, glass recessed 0.12 m
K.boxr("Steel", DX0, DX1, DY0, DY1, FL, WZ0)
K.boxr("Steel", DX0 + 0.15 * M, DX1 - 0.15 * M, DY0 + 0.15 * M, DY1, WZ0, WZ1)        # body behind the glass
K.boxr("Blue", DX0, DX1, DY0, DY1, WZ1, 3.45 * M)                                      # enamel band
for z in (WZ1, 3.0 * M, 3.45 * M):
    K.boxr("Chrome", DX0 - 0.03 * M, DX1 + 0.03 * M, DY0 - 0.03 * M, DY1, z - 0.03 * M, z + 0.03 * M)
K.boxr("NeonCyan", DX0 + 0.2 * M, DX1 - 0.2 * M, DY0 - 0.08 * M, DY0 - 0.03 * M, 3.2 * M, 3.26 * M)
# window ribbon: front (split by the vestibule) and both ends, interior print + chrome mullions
VX0, VX1 = -3 * M, 1 * M


def ribbon_front(x0, x1, u0):
    y = DY0 + 0.15 * M - 0.02 * M
    span = (x1 - x0) / (22 * M)
    quad_uv("DinerInterior", [(x0, y, WZ0), (x1, y, WZ0), (x1, y, WZ1), (x0, y, WZ1)], (u0, 0, u0 + span, 1))
    n = max(1, round((x1 - x0) / (1.8 * M)))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        K.boxr("Chrome", x - 0.05 * M, x + 0.05 * M, DY0 - 0.02 * M, DY0 + 0.15 * M, WZ0, WZ1)
    K.boxr("Chrome", x0, x1, DY0 - 0.04 * M, DY0 + 0.15 * M, WZ0 - 0.06 * M, WZ0)        # sill


ribbon_front(DX0 + 0.15 * M, VX0, 0.0)
ribbon_front(VX1, DX1 - 0.15 * M, 0.55)
for sx, x in ((-1, DX0), (1, DX1)):                                                   # end windows
    xi = x - sx * 0.13 * M
    y0, y1 = DY0 + 1 * M, DY1 - 1.5 * M
    cs = ((xi, y1, WZ0), (xi, y0, WZ0), (xi, y0, WZ1), (xi, y1, WZ1)) if sx < 0 else \
         ((xi, y0, WZ0), (xi, y1, WZ0), (xi, y1, WZ1), (xi, y0, WZ1))
    quad_uv("DinerInterior", list(cs), (0.2, 0, 0.2 + (y1 - y0) / (22 * M), 1))
    for k in range(4):
        y = y0 + (y1 - y0) * k / 3
        K.boxr("Chrome", min(x, x - sx * 0.15 * M), max(x, x - sx * 0.15 * M) + 0.0, y - 0.05 * M, y + 0.05 * M, WZ0, WZ1)
    K.boxr("Steel", min(x, x - sx * 0.15 * M), max(x, x - sx * 0.15 * M), DY0 + 0.15 * M, y0 - 0.05 * M, WZ0, WZ1)
    K.boxr("Steel", min(x, x - sx * 0.15 * M), max(x, x - sx * 0.15 * M), y1 + 0.05 * M, DY1, WZ0, WZ1)
# front wall pieces between ribbon segments are the vestibule; front skin at the window band corners
for x0, x1 in ((DX0, DX0 + 0.15 * M), (DX1 - 0.15 * M, DX1)):
    K.boxr("Steel", x0, x1, DY0, DY0 + 0.15 * M, WZ0, WZ1)
# rolled roof edge + roof deck
K.boxr("Roof", DX0 + 0.1 * M, DX1 - 0.1 * M, DY0 + 0.1 * M, DY1 - 0.1 * M, 3.45 * M, 3.75 * M)
K.cyl_along("Steel", (DX0 - 0.1 * M, DY0 + 0.05 * M, 3.62 * M), (DX1 + 0.1 * M, DY0 + 0.05 * M, 3.62 * M), 0.22 * M, segs=12)
for x in (DX0 + 0.05 * M, DX1 - 0.05 * M):
    K.cyl_along("Steel", (x, DY0 + 0.05 * M, 3.62 * M), (x, DY1, 3.62 * M), 0.2 * M, segs=12)
for x in (DX0, DX1):                                                                  # rounded front corners
    K.cyl("Steel", (x, DY0, (FL + 3.45 * M) / 2), 0.2 * M, 3.45 * M - FL, segs=12)

# vestibule: glass-block sides, chrome door, canopy, steps
VY = DY0 - 2 * M
K.boxr("GlassBlock", VX0, VX0 + 0.3 * M, VY, DY0 + 0.2 * M, FL, 3.1 * M)
K.boxr("GlassBlock", VX1 - 0.3 * M, VX1, VY, DY0 + 0.2 * M, FL, 3.1 * M)
K.boxr("Steel", VX0 + 0.3 * M, VX1 - 0.3 * M, VY, VY + 0.25 * M, 2.95 * M, 3.1 * M)
K.boxr("Tile", VX0, VX1, VY, DY0, -0.3 * M, FL)
K.boxr("Dark", VX0 + 0.3 * M, VX1 - 0.3 * M, VY + 0.25 * M, DY0 + 0.2 * M, FL, 2.95 * M)       # dim lobby behind the door
quad_uv("DinerDoor", [(VX0 + 0.35 * M, VY - 0.02 * M, FL), (VX1 - 0.35 * M, VY - 0.02 * M, FL),
                      (VX1 - 0.35 * M, VY - 0.02 * M, 2.9 * M), (VX0 + 0.35 * M, VY - 0.02 * M, 2.9 * M)], (0, 0, 1, 1))
K.boxr("Blue", VX0 - 0.4 * M, VX1 + 0.4 * M, VY - 0.9 * M, DY0, 3.1 * M, 3.3 * M)                 # canopy
K.boxr("Chrome", VX0 - 0.42 * M, VX1 + 0.42 * M, VY - 0.92 * M, VY - 0.86 * M, 3.08 * M, 3.32 * M)
K.lamp(((VX0 + VX1) / 2, VY - 0.45 * M, 3.07 * M), (1.2 * M, 0.5 * M, 0.04 * M))
for k in range(3):                                                                   # steps down to the lot
    K.boxr("Pave", VX0 - 0.2 * M, VX1 + 0.2 * M, VY - (k + 1) * 0.35 * M, VY, 0, FL - (k + 1) * FL / 4 + 0.0)
for sx in (VX0 - 0.15 * M, VX1 + 0.15 * M):                                           # handrails
    K.cyl_along("Chrome", (sx, VY - 1.05 * M, 0.25 * M + 0.9 * M), (sx, VY - 0.05 * M, FL + 0.9 * M), 0.03 * M, segs=6)
    for yy, zz in ((VY - 1.0 * M, 0.25 * M), (VY - 0.1 * M, FL - 0.05 * M)):
        K.cyl("Chrome", (sx, yy, zz + 0.45 * M), 0.025 * M, 0.9 * M, segs=6)

# roof sign
RS = (-9 * M, 5 * M, DY0 + 1.2 * M, 4.0 * M, 5.6 * M)
for x in (RS[0] + 1 * M, (RS[0] + RS[1]) / 2, RS[1] - 1 * M):
    K.boxr("Steel", x - 0.06 * M, x + 0.06 * M, RS[2] + 0.1 * M, RS[2] + 0.2 * M, 3.75 * M, RS[3])
    K.cyl_along("Steel", (x, RS[2] + 0.15 * M, RS[3]), (x, RS[2] + 1.5 * M, 3.75 * M), 0.04 * M, segs=6)
K.boxr("Red", RS[0], RS[1], RS[2], RS[2] + 0.1 * M, RS[3], RS[4])
quad_uv("DinerSigns", [(RS[0] + 0.05 * M, RS[2] - 0.02 * M, RS[3] + 0.05 * M), (RS[1] - 0.05 * M, RS[2] - 0.02 * M, RS[3] + 0.05 * M),
                       (RS[1] - 0.05 * M, RS[2] - 0.02 * M, RS[4] - 0.05 * M), (RS[0] + 0.05 * M, RS[2] - 0.02 * M, RS[4] - 0.05 * M)],
        (0, 0, 1, 0.25))
neon_frame("NeonRed", RS[0] - 0.02 * M, RS[1] + 0.02 * M, RS[2] - 0.04 * M, RS[3] - 0.02 * M, RS[4] + 0.02 * M)

# rooftop units on the diner
for x in (-11 * M, 3 * M):
    K.boxr("AcBody", x, x + 2.2 * M, 0 * M, 1.6 * M, 3.75 * M, 4.8 * M)
    K.cyl("Dark", (x + 1.1 * M, 0.8 * M, 4.82 * M), 0.5 * M, 0.04 * M, segs=14)

# ---------------------------------------------------------------- kitchen annex + back yard
KX0, KX1, KY0, KY1 = -12 * M, 6 * M, DY1 - 0.3 * M, 10 * M      # starts inside the diner (no shared wall face)
K.boxr("Kitchen", KX0, KX1, KY0, KY1, -0.3 * M, 3.3 * M)
K.boxr("Pave", KX0 - 0.1 * M, KX1 + 0.1 * M, KY0, KY1 + 0.1 * M, 3.3 * M, 3.45 * M)          # coping
K.boxr("Roof", KX0 + 0.1 * M, KX1 - 0.1 * M, KY0 + 0.1 * M, KY1 - 0.1 * M, 3.3 * M, 3.38 * M)
K.boxr("Dark", -4 * M, -2.6 * M, KY1, KY1 + 0.06 * M, 0, 2.3 * M)                           # back door
K.boxr("Pave", -4.5 * M, -2.1 * M, KY1, KY1 + 1.4 * M, 0, 0.15 * M)
K.box("Sconce", (-3.3 * M, KY1 + 0.12 * M, 2.65 * M), (0.25 * M, 0.2 * M, 0.2 * M))
K.boxr("Steel", 1 * M, 3 * M, 4 * M, 6.5 * M, 3.38 * M, 4.2 * M)                            # exhaust hood
K.cyl("Steel", (2 * M, 5.25 * M, 4.9 * M), 0.35 * M, 1.4 * M, segs=12)
K.cyl("Steel", (2 * M, 5.25 * M, 5.7 * M), 0.6 * M, 0.2 * M, segs=12, r2=0.1 * M)
K.boxr("AcBody", -9 * M, -6.5 * M, 6 * M, 8 * M, 3.38 * M, 4.5 * M)
K.downpipe(KX1 - 0.3 * M, KY1 + 0.1 * M, 0, 3.4 * M)
# dumpster in a block enclosure
ex0, ex1, ey0, ey1 = -20 * M, -14 * M, 15 * M, 20 * M
for (a0, a1, b0, b1) in ((ex0, ex1, ey1 - 0.3 * M, ey1), (ex0, ex0 + 0.3 * M, ey0, ey1), (ex1 - 0.3 * M, ex1, ey0, ey1)):
    K.boxr("Pave", a0, a1, b0, b1, 0, 1.8 * M)
K.boxr("Dumpster", ex0 + 0.8 * M, ex1 - 0.8 * M, ey0 + 1.4 * M, ey1 - 0.6 * M, 0.15 * M, 1.4 * M)
K.boxr("Dark", ex0 + 0.75 * M, ex1 - 0.75 * M, ey0 + 1.35 * M, ey1 - 0.55 * M, 1.4 * M, 1.48 * M)
for x in (ex0 + 1.2 * M, ex1 - 1.2 * M):
    K.cyl("Dark", (x, ey0 + 1.5 * M, 0.1 * M), 0.1 * M, 0.2 * M, segs=8, axis='X')

# ---------------------------------------------------------------- pylon sign at the street
PX, PY = 18 * M, -23 * M
for x in (PX - 2.2 * M, PX + 2.2 * M):
    K.cyl("Steel", (x, PY, 4.6 * M), 0.18 * M, 9.2 * M, segs=12)
    K.cyl("Pave", (x, PY, 0.3 * M), 0.4 * M, 0.6 * M, segs=12)
K.boxr("Dark", PX - 3.2 * M, PX + 3.2 * M, PY - 0.2 * M, PY + 0.2 * M, 5.6 * M, 8.8 * M)
for s in (-1, 1):
    y = PY + s * 0.22 * M
    corners = [(PX - 3.1 * M, y, 5.7 * M), (PX + 3.1 * M, y, 5.7 * M), (PX + 3.1 * M, y, 8.7 * M), (PX - 3.1 * M, y, 8.7 * M)]
    if s > 0:
        corners = [corners[1], corners[0], corners[3], corners[2]]
    quad_uv("DinerSigns", corners, (0, 0.5, 1, 1))
    neon_frame("NeonCyan", PX - 3.25 * M, PX + 3.25 * M, y + (0.05 * M if s > 0 else 0), 5.55 * M, 8.85 * M)
K.boxr("Dark", PX - 2.4 * M, PX + 2.4 * M, PY - 0.15 * M, PY + 0.15 * M, 3.8 * M, 5.2 * M)
for s in (-1, 1):
    y = PY + s * 0.17 * M
    corners = [(PX - 2.3 * M, y, 3.9 * M), (PX + 2.3 * M, y, 3.9 * M), (PX + 2.3 * M, y, 5.1 * M), (PX - 2.3 * M, y, 5.1 * M)]
    if s > 0:
        corners = [corners[1], corners[0], corners[3], corners[2]]
    quad_uv("DinerSigns", corners, (0, 0.25, 1, 0.5))
K.boxr("Pave", PX - 3.2 * M, PX + 3.2 * M, PY - 0.8 * M, PY + 0.8 * M, 0, 0.2 * M)            # base with shrubs
for x in (PX - 1.2 * M, PX, PX + 1.2 * M):
    K.shrub(x, PY, 0.2 * M, 0.5 * M, rng)

# ---------------------------------------------------------------- lot lights + planters
for (x, y) in ((-6 * M, -20.5 * M), (10 * M, 8 * M)):
    K.cyl("Pave", (x, y, 0.35 * M), 0.35 * M, 0.7 * M, segs=12)
    K.cyl("Steel", (x, y, 4.2 * M), 0.1 * M, 7.0 * M, segs=10)
    K.cyl_along("Steel", (x, y, 7.6 * M), (x + 1.4 * M, y, 7.6 * M), 0.06 * M, segs=6)
    K.boxr("Steel", x + 1.0 * M, x + 2.2 * M, y - 0.3 * M, y + 0.3 * M, 7.45 * M, 7.7 * M)
    K.lamp((x + 1.6 * M, y, 7.43 * M), (1.0 * M, 0.45 * M, 0.04 * M))
for (cx, cy) in ((DX0 - 1.2 * M, DY0 + 2 * M), (DX1 + 1.2 * M, DY0 + 2 * M)):
    K.boxr("Pave", cx - 0.8 * M, cx + 0.8 * M, cy - 1.8 * M, cy + 1.8 * M, 0, 0.6 * M)
    K.boxr("Soil", cx - 0.68 * M, cx + 0.68 * M, cy - 1.68 * M, cy + 1.68 * M, 0.6 * M, 0.62 * M)
    for k in range(3):
        K.shrub(cx, cy - 1.1 * M + k * 1.1 * M, 0.6 * M, 0.55 * M, rng)
# a strip of grass + shrubs along the west edge, past the drive
K.boxr("Soil", -LX + 0.3 * M, -LX + 2.3 * M, -10 * M, 12 * M, 0, 0.16 * M)
for k in range(7):
    K.shrub(-LX + 1.3 * M, -9 * M + k * 3.4 * M, 0.16 * M, rng.uniform(0.5, 0.7) * M, rng)

K.finish(face=A["face"])
meta = K.export()
s = 1 if A["face"] == "N" else -1
meta["driveways"] = [[DRIVE[0] * s, DRIVE[1] * s, A["face"]]]
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    s = -1 if A["face"] == "N" else 1
    K.shot("front", (-20 * M, s * 52 * M, 12 * M), (0, 0, 2 * M), lens=26)
    K.shot("street", (6 * M, s * 26 * M, 1.7 * M), (-3 * M, s * 8 * M, 2.4 * M), lens=24)
    K.shot("back", (30 * M, -s * 45 * M, 18 * M), (0, 0, 2 * M), lens=28)
