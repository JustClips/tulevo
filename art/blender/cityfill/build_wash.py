"""Bubble Bay Car Wash on the bare strip between the Kestrel gas station and Westgate Plaza, with a
free-vacuum lot behind the gas station (thread "Fill city with buildings and street props",
2026-11-07, Dev: "see gaps here").

  python3 tools/cityfill_textures.py wash      (WashSigns, WashTeal, WashNavy, BrushBlue, BrushRed)
  blender --background --python build_wash.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin). Roblox x/z:
  strip      x -358..-333, z 172..359: entry lane off Back Street with a pay island and menu
             board, a drive-through wash tunnel (brushes, top brush, dryer arch, conveyor)
  back lot   x -333..-160, z 316..359 (behind Kestrel): exit aisle to West Street, a row of
             vacuum stalls under a shade canopy
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(21)
K = Kit("CarWash", os.path.join(A["out"], "CarWash"), BS.TEX)
for name, sheet, tile in (("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Deck", "ForeCrete", (4 * M, 4 * M)), ("Block", "MallStucco", (3 * M, 3 * M)),
                          ("RoofTar", "RoofTar", (4 * M, 4 * M)), ("WashTeal", "WashTeal", (2 * M, 2 * M)),
                          ("WashNavy", "WashNavy", (2 * M, 2 * M)), ("BrushBlue", "BrushBlue", (1 * M, 1 * M)),
                          ("BrushRed", "BrushRed", (1 * M, 1 * M)), ("GlassBlock", "GlassBlock", (2 * M, 2 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Bin", "BinGreen", (1 * M, 1 * M)),
                          ("Hazard", "Hazard", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
K.mat("WashSigns", sheet="WashSigns", explicit=True)
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0), ("Hose", (0.10, 0.10, 0.11), 0.6, 0, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


def sign(cx, cz, h0, w, h, face, uv):
    """WashSigns quad. face '-x' (seen from the west), '+x', '-z' (seen from Back St, north), '+z'."""
    (u0, v0), (u1, v1) = uv
    uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    if face in ("-x", "+x"):
        K.face_x("WashSigns", -cx, cz, Y0 + h0, w, h, facing=1 if face == "-x" else -1, uvs=uvs)
    else:
        K.face_y("WashSigns", -cx, cz, Y0 + h0, w, h, facing=-1 if face == "-z" else 1, uvs=uvs)


UV_BANNER, UV_MENU, UV_ENTER = ((0, 0.75), (1, 1)), ((0, 0.25), (0.5, 0.75)), ((0.5, 0.5), (1, 0.75))
UV_VAC, UV_THANKS = ((0.5, 0.25), (1, 0.5)), ((0, 0), (1, 0.25))

# ---------------------------------------------------------------- lot
SX0, SX1 = -358.0, -333.0
B("Asphalt", SX0, SX1, 172.2, 359.2, -1.2, 0)
B("Asphalt", SX1, -160.2, 316.4, 359.2, -1.2, 0)
B("Pave", SX0, SX0 + 0.8, 172.2, 359.2, 0, 0.5)                    # kerb on the Westgate side
B("Pave", SX0 + 0.8, -160.2, 358.4, 359.2, 0, 0.5)                  # kerb along the houses

# ---------------------------------------------------------------- wash tunnel
TX0, TX1, TZ0, TZ1, TH = -356.0, -335.0, 214.0, 300.0, 16.0
for x0, x1 in ((TX0, TX0 + 1.2), (TX1 - 1.2, TX1)):
    B("Block", x0, x1, TZ0, TZ1, 0, TH)
    B("GlassBlock", x0 - 0.04, x1 + 0.04, TZ0 + 6, TZ1 - 6, 9.0, 12.0)
B("Block", TX0, TX1, TZ0, TZ1, TH - 1.4, TH)                        # roof slab
B("RoofTar", TX0 + 0.3, TX1 - 0.3, TZ0 + 0.3, TZ1 - 0.3, TH, TH + 0.1)
for x0, x1, z0, z1 in ((TX0, TX1, TZ0, TZ0 + 0.6), (TX0, TX1, TZ1 - 0.6, TZ1), (TX0, TX0 + 0.6, TZ0 + 0.6, TZ1 - 0.6),
                       (TX1 - 0.6, TX1, TZ0 + 0.6, TZ1 - 0.6)):
    B("Block", x0, x1, z0, z1, TH, TH + 1.6)
B("Deck", TX0 + 1.2, TX1 - 1.2, TZ0, TZ1, 0, 0.1)
for z, h0 in ((TZ0, 10.0), (TZ1, 10.0)):                            # fascia bands over the open ends
    B("Block", TX0, TX1, z - 0.4 if z == TZ0 else z, z if z == TZ0 else z + 0.4, h0, TH)
B("WashTeal", TX0 - 0.1, TX1 + 0.1, TZ0 - 0.5, TZ1 + 0.5, TH + 0.6, TH + 1.4)
B("WashNavy", TX0 - 0.08, TX0, TZ0, TZ1, 0, 1.2)                    # navy base band on the outer walls
B("WashNavy", TX1, TX1 + 0.08, TZ0, TZ1, 0, 1.2)
B("Block", TX0 - 0.15, TX1 + 0.15, TZ0 - 0.6, TZ1 + 0.6, TH + 1.6, TH + 1.85)   # coping
sign((TX0 + TX1) / 2, TZ0 - 0.44, 10.2, 20.4, 5.1, "-z", UV_BANNER)    # over the entrance (Back St side)
sign((TX0 + TX1) / 2, TZ1 + 0.44, 10.2, 20.4, 5.1, "+z", UV_THANKS)    # over the exit
B("WashNavy", TX0 - 0.6, TX0 - 0.15, 230.0, 284.0, 2.4, 15.6)       # big side sign toward Westgate Plaza
sign(TX0 - 0.64, 257.0, 2.6, 52.0, 13.0, "-x", UV_BANNER)
B("WashNavy", TX1 + 0.15, TX1 + 0.6, 230.0, 284.0, 2.4, 15.6)       # and toward the gas station
sign(TX1 + 0.64, 257.0, 2.6, 52.0, 13.0, "+x", UV_BANNER)
# conveyor track + guide rails, hazard paint at the mouth
for x in (-347.8, -343.2):
    B("Steel", x - 0.25, x + 0.25, TZ0 + 2, TZ1 - 2, 0.1, 0.35)
B("Dark", -347.4, -343.6, TZ0 + 2, TZ1 - 2, 0.1, 0.16)
B("Hazard", TX0 + 1.2, TX1 - 1.2, TZ0 - 4.0, TZ0 - 2.0, 0, 0.02)
# washing gear: gantry arches with side brushes, a top brush, a dryer
for k, z in enumerate((236.0, 252.0, 268.0)):
    for x in (TX0 + 1.6, TX1 - 1.6):
        B("Steel", x - 0.35, x + 0.35, z - 0.35, z + 0.35, 0.1, TH - 1.4)
    B("Steel", TX0 + 1.2, TX1 - 1.2, z - 0.35, z + 0.35, TH - 2.4, TH - 1.4)
    if k < 2:
        for x in (TX0 + 4.4, TX1 - 4.4):                              # side brushes (fat foam rolls)
            K.cyl("BrushBlue" if k == 0 else "BrushRed", W(x, z + 4.0, 5.6), 2.4, 9.0, segs=16)
            K.cyl("Steel", W(x, z + 4.0, 11.0), 0.25, 3.0, segs=6)
            B("Steel", min(x, TX0 + 1.6 if x < -345 else TX1 - 1.6), max(x, TX0 + 1.6 if x < -345 else TX1 - 1.6),
              z + 3.8, z + 4.2, 12.3, 12.7)
    else:
        K.cyl("BrushBlue", W((TX0 + TX1) / 2, z + 4.0, 9.5), 2.0, TX1 - TX0 - 7.0, segs=16, axis='X')
        for x in (TX0 + 3.2, TX1 - 3.2):
            B("Steel", x - 0.2, x + 0.2, z + 3.8, z + 4.2, 9.5, TH - 1.4)
B("WashNavy", TX0 + 1.6, TX1 - 1.6, 285.0, 287.0, 10.0, TH - 1.4)   # dryer arch with nozzles
for x in (TX0 + 1.6, TX1 - 1.6):
    B("WashNavy", x - 0.6, x + 0.6, 285.0, 287.0, 0.1, 10.0)
for i in range(6):
    x = TX0 + 4.0 + i * (TX1 - TX0 - 8.0) / 5
    K.cyl("Dark", W(x, 286.0, 9.6), 0.7, 0.8, segs=10)
for z in (230.0, 260.0, 290.0):
    K.lamp(W((TX0 + TX1) / 2, z, TH - 1.55), (6.0, 1.2, 0.15))
# roof units
for z in (232.0, 278.0):
    K.box("AcBody", W(-345.5, z, TH + 1.0), (4.0, 3.0, 1.8))

# ---------------------------------------------------------------- entry lane: pay island + menu board
B("Pave", -339.0, -335.4, 188.0, 206.0, 0, 0.6)                    # island (cars pass west of it)
for z in (188.6, 205.4):
    K.cyl("Yellow", W(-337.2, z, 2.2), 0.35, 3.2, segs=10)
B("Dark", -338.0, -336.4, 198.0, 199.6, 0.6, 0.9)                   # pay terminal
B("AcBody", -337.9, -336.5, 198.1, 199.5, 0.9, 5.6)
B("Dark", -338.0, -337.86, 198.4, 199.2, 3.6, 4.8)
B("WashTeal", -338.0, -336.4, 198.0, 199.6, 5.6, 6.0)
for x in (-338.6, -335.8):                                           # menu board on two posts, facing the cars
    K.cyl("Steel", W(x, 193.0, 3.6), 0.12, 6.0, segs=6)
B("Dark", -339.2, -335.2, 193.12, 193.3, 3.0, 7.0)
sign(-337.2, 193.06, 3.0, 4.0, 4.0, "-z", UV_MENU)
K.cyl("Steel", W(-353.6, 209.0, 3.4), 0.15, 6.8, segs=8)              # ENTER board on a post by the mouth
B("Dark", -356.0, -351.2, 208.8, 209.0, 3.6, 6.6)
sign(-353.6, 208.76, 3.7, 4.6, 2.3 * 4.6 / 4.6, "-z", UV_ENTER)
for k in range(4):                                                   # lane arrows
    z = 178.0 + k * 9.0
    B("LotLine", -346.1, -345.5, z, z + 4.0, 0, 0.02)
    K.quad("LotLine", [W(-347.6, z + 4.0, 0.02), W(-344.0, z + 4.0, 0.02), W(-345.8, z + 6.5, 0.02)])
# planter strip along the gas station side of the lane
B("Pave", -334.6, -333.2, 172.2, 212.0, 0, 0.6)
B("Soil", -335.4, -334.6, 172.2, 186.0, 0, 0.5)

# ---------------------------------------------------------------- back lot: vacuum stalls under a canopy
VZ0, VZ1 = 339.0, 357.6
N = 12
VX0, VX1 = -330.0, -166.0
w = (VX1 - VX0) / N
for i in range(N + 1):
    x = VX0 + i * w
    B("LotLine", x - 0.2, x + 0.2, VZ0 + 0.5, VZ1 - 0.6, 0, 0.012)
for i in range(N):
    x = VX0 + (i + 0.5) * w
    B("Pave", x - 3.0, x + 3.0, VZ1 - 2.4, VZ1 - 1.6, 0, 0.45)       # wheel stops
for i in range(N + 1):                                               # vacuum pedestals on the stall lines
    x = VX0 + i * w
    if i % 2:
        continue
    B("Pave", x - 0.9, x + 0.9, VZ1 - 1.3, VZ1 - 0.1, 0, 0.4)
    K.cyl("WashTeal", W(x, VZ1 - 0.7, 3.2), 0.55, 5.6, segs=12)
    K.cyl("WashNavy", W(x, VZ1 - 0.7, 6.1), 0.65, 0.2, segs=12)
    for s in (-1, 1):                                                # hoses arcing out over both stalls
        pts = [W(x + s * t * 3.2, VZ1 - 0.7 - t * 1.5, 5.6 + 2.0 * t - 3.6 * t * t) for t in (0, 0.33, 0.66, 1.0)]
        for a, b in zip(pts, pts[1:]):
            K.cyl_along("Hose", a, b, 0.14, segs=6)
# canopy: posts at the back, cantilever arms, a teal shade deck with a navy fascia
for i in range(0, N + 1, 2):
    x = VX0 + i * w
    B("Steel", x - 0.4, x + 0.4, VZ1 - 0.2, VZ1 + 0.6, 0, 12.6)
    B("Steel", x - 0.3, x + 0.3, VZ0 + 1.0, VZ1 + 0.6, 11.4, 12.0)
B("WashTeal", VX0 - 1.0, VX1 + 1.0, VZ0 + 1.0, VZ1 + 0.6, 12.0, 12.5)
B("WashNavy", VX0 - 1.1, VX1 + 1.1, VZ0 + 0.6, VZ0 + 1.0, 11.0, 13.2)
for k in range(4):
    x = VX0 + (k + 0.5) * (VX1 - VX0) / 4
    K.lamp(W(x, (VZ0 + VZ1) / 2, 11.85), (5.0, 1.0, 0.15))
    sign(x, VZ0 + 0.56, 11.0, 4.4, 2.2, "-z", UV_VAC)
# exit arrows toward West St, bins, a small planter at the corner
for k in range(5):
    x = -300.0 + k * 28.0
    B("LotLine", x, x + 4.0, 327.7, 328.3, 0, 0.02)
    K.quad("LotLine", [W(x + 4.0, 326.2, 0.02), W(x + 4.0, 329.8, 0.02), W(x + 6.5, 328.0, 0.02)][::-1])
for (x, z) in ((-331.2, 356.0), (-168.0, 336.0)):
    K.cyl("Bin", W(x, z, 1.6), 1.0, 3.2, segs=12)
B("Pave", -356.6, -335.6, 340.0, 358.4, 0, 0.6)                      # planter west of the vacuum row
B("Soil", -355.8, -336.4, 340.8, 357.6, 0, 0.62)
for k in range(5):
    K.shrub(-(-353.0 + k * 4.2), 345.0 + (k % 2) * 6.0, Y0 + 0.62, rng.uniform(2.2, 2.9), rng)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("wash_front", W(-300.0, 150.0, 40.0), W(-345.0, 230.0, 6.0), lens=26)
    K.shot("wash_back", W(-200.0, 300.0, 45.0), W(-280.0, 345.0, 4.0), lens=26)
    K.shot("wash_inside", W(-345.5, 206.0, 6.0), W(-345.5, 260.0, 5.0), lens=22)
