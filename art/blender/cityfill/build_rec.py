"""Eastside Rec Center on the paved lot behind the Calder building and Hotel Solana, south of the
Vipers houses (thread "Fill city with buildings and street props", 2026-11-07, Dev: "empty space here").

  python3 tools/cityfill_textures.py rec      (RecSigns, CourtBlue, CourtGreen, RecNavy, RecOrange)
  blender --background --python build_rec.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin). Roblox x/z:
  lot     x 463..640, z -359..-256, with two drives up to Vault Ave either side of the Calder building
          (x 463..485 and 615..640, z -256..-172)
  gym     x 467..527, z -352..-264: tall hall with a glass entry + sign facing the drives
  court   x 535..635, z -340..-286: full basketball court with hoops, bleachers and four light poles
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(44)
K = Kit("RecCenter", os.path.join(A["out"], "RecCenter"), BS.TEX)
for name, sheet, tile in (("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Block", "MallStucco", (3 * M, 3 * M)), ("Cap", "ParkCap", (3 * M, 3 * M)),
                          ("RoofTar", "RoofTar", (4 * M, 4 * M)), ("GlassBlock", "GlassBlock", (2 * M, 2 * M)),
                          ("CourtBlue", "CourtBlue", (4 * M, 4 * M)), ("CourtGreen", "CourtGreen", (4 * M, 4 * M)),
                          ("RecNavy", "RecNavy", (2 * M, 2 * M)), ("RecOrange", "RecOrange", (2 * M, 2 * M)),
                          ("Bench", "BenchWood", (1 * M, 1 * M)), ("AcBody", "HvacGrey", (1 * M, 1 * M)),
                          ("Bin", "BinGreen", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
K.mat("RecSigns", sheet="RecSigns", explicit=True)
K.facade_mats()
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0),
                                      ("Board", (0.95, 0.95, 0.95), 0.4, 0, 0), ("Rim", (0.95, 0.35, 0.08), 0.4, 0.6, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


def sign(cx, cz, h0, w, h, face, uv):
    (u0, v0), (u1, v1) = uv
    uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    if face in ("-x", "+x"):
        K.face_x("RecSigns", -cx, cz, Y0 + h0, w, h, facing=1 if face == "-x" else -1, uvs=uvs)
    else:
        K.face_y("RecSigns", -cx, cz, Y0 + h0, w, h, facing=-1 if face == "-z" else 1, uvs=uvs)


UV_BANNER, UV_OPEN, UV_PARK = ((0, 0.5), (1, 1)), ((0, 0), (0.5, 0.5)), ((0.5, 0), (1, 0.5))

# ---------------------------------------------------------------- lot + drives
B("Asphalt", 463.2, 639.8, -359.2, -256.0, -1.2, 0)
B("Asphalt", 463.2, 485.0, -256.0, -172.2, -1.2, 0)
B("Asphalt", 615.0, 639.8, -256.0, -172.2, -1.2, 0)
B("Pave", 463.2, 639.8, -359.2, -358.4, 0, 0.6)                     # kerb along the Vipers back fences
B("Pave", 639.0, 639.8, -358.4, -172.2, 0, 0.6)                     # kerb along the Bellmont grass
for x0, x1 in ((463.2, 485.0), (615.0, 639.0)):                     # PUBLIC PARKING signs at the drive mouths
    x = x0 + 1.4 if x0 < 500 else x1 - 1.4
    K.cyl("Steel", W(x, -175.0, 3.4), 0.15, 6.8, segs=8)
    B("Dark", x - 2.3, x + 2.3, -175.16, -175.0, 4.0, 6.8)
    sign(x, -175.2, 4.1, 4.4, 2.6, "-z", UV_PARK)

# ---------------------------------------------------------------- gym hall
GX0, GX1, GZ0, GZ1, GH = 467.0, 527.0, -352.0, -264.0, 24.0
B("Block", GX0, GX1, GZ0, GZ1, 0, GH)
B("RoofTar", GX0 + 0.4, GX1 - 0.4, GZ0 + 0.4, GZ1 - 0.4, GH, GH + 0.1)
for x0, x1, z0, z1 in ((GX0, GX1, GZ0, GZ0 + 0.7), (GX0, GX1, GZ1 - 0.7, GZ1), (GX0, GX0 + 0.7, GZ0 + 0.7, GZ1 - 0.7),
                       (GX1 - 0.7, GX1, GZ0 + 0.7, GZ1 - 0.7)):
    B("Block", x0, x1, z0, z1, GH, GH + 1.6)
B("Cap", GX0 - 0.2, GX1 + 0.2, GZ0 - 0.2, GZ1 + 0.2, GH + 1.6, GH + 2.0)
B("RecNavy", GX0 - 0.1, GX1 + 0.1, GZ0 - 0.1, GZ1 + 0.1, 0, 2.0)
B("RecOrange", GX0 - 0.1, GX1 + 0.1, GZ0 - 0.1, GZ1 + 0.1, 20.4, 21.4)
for x0, x1, z0, z1 in ((GX0 - 0.04, GX0, GZ0 + 6, GZ1 - 6), (GX1, GX1 + 0.04, GZ0 + 6, GZ1 - 6)):   # clerestory glass block
    B("GlassBlock", x0, x1, z0, z1, 13.0, 18.0)
B("GlassBlock", GX0 + 6, GX1 - 6, GZ0 - 0.04, GZ0, 13.0, 18.0)
# entry on the north face: glass wall, canopy, banner above
ex = (GX0 + GX1) / 2
for k in range(4):
    K.window3d("y", GZ1, 1, -(ex - 13.5 + k * 9.0), Y0 + 2.0, 7.4, 8.5, mull=1, depth=0.4)
B("RecNavy", ex - 20.0, ex + 20.0, GZ1, GZ1 + 5.0, 11.2, 12.0)
for x in (ex - 19.0, ex + 19.0):
    B("Steel", x - 0.25, x + 0.25, GZ1 + 4.3, GZ1 + 4.8, 0, 11.2)
for x in (ex - 10.0, ex + 10.0):
    K.lamp(W(x, GZ1 + 2.5, 11.15), (2.0, 1.0, 0.1))
B("RecNavy", ex - 22.0, ex + 22.0, GZ1, GZ1 + 0.3, 12.6, 20.0)
sign(ex, GZ1 + 0.34, 12.9, 43.0, 6.8, "+z", UV_BANNER)
sign(GX0 + 6.0, GZ1 + 0.04, 4.0, 5.0, 2.5, "+z", UV_OPEN)
for x in (480.0, 514.0):
    K.box("AcBody", W(x, -300.0, GH + 1.0), (5.0, 4.0, 1.8))

# ---------------------------------------------------------------- basketball court
CX0, CX1, CZ0, CZ1 = 535.0, 635.0, -340.0, -286.0
B("CourtGreen", CX0 - 4.0, CX1 + 4.0, CZ0 - 4.0, CZ1 + 4.0, 0, 0.25)
B("CourtBlue", CX0, CX1, CZ0, CZ1, 0.25, 0.3)
LW, Y = 0.45, 0.31
cz = (CZ0 + CZ1) / 2
for x0, x1, z0, z1 in ((CX0, CX1, CZ0, CZ0 + LW), (CX0, CX1, CZ1 - LW, CZ1), (CX0, CX0 + LW, CZ0, CZ1), (CX1 - LW, CX1, CZ0, CZ1),
                       ((CX0 + CX1) / 2 - LW / 2, (CX0 + CX1) / 2 + LW / 2, CZ0, CZ1)):
    B("LotLine", x0, x1, z0, z1, 0.3, Y)
for end in (0, 1):
    xb = CX0 if end == 0 else CX1
    s = 1 if end == 0 else -1
    # key (paint box) + free-throw line
    B("RecOrange", min(xb, xb + s * 19.0), max(xb, xb + s * 19.0), cz - 6.0, cz + 6.0, 0.3, 0.305)
    for z in (cz - 6.0, cz + 6.0):
        B("LotLine", min(xb, xb + s * 19.0), max(xb, xb + s * 19.0), z - LW / 2, z + LW / 2, 0.3, Y)
    B("LotLine", xb + s * 19.0 - LW / 2, xb + s * 19.0 + LW / 2, cz - 6.0, cz + 6.0, 0.3, Y)
    # three-point arc as segments
    import math
    for i in range(16):
        a0, a1 = -math.pi / 2 + i * math.pi / 16, -math.pi / 2 + (i + 1) * math.pi / 16
        p0 = (xb + s * (4.5 + 23.0 * math.cos(a0)), cz + 23.0 * math.sin(a0))
        p1 = (xb + s * (4.5 + 23.0 * math.cos(a1)), cz + 23.0 * math.sin(a1))
        K.cyl_along("LotLine", W(p0[0], p0[1], 0.3), W(p1[0], p1[1], 0.3), 0.22, segs=4)
    # hoop: pole behind the baseline, arm, backboard, rim
    xp = xb - s * 3.0
    K.cyl("Steel", W(xp, cz, 6.5), 0.4, 13.0, segs=10)
    B("Steel", min(xp, xb + s * 1.2), max(xp, xb + s * 1.2), cz - 0.3, cz + 0.3, 11.6, 12.2)
    B("Board", min(xb + s * 1.2, xb + s * 1.5), max(xb + s * 1.2, xb + s * 1.5), cz - 3.0, cz + 3.0, 10.0, 13.6)
    for i in range(10):
        a0, a1 = i * math.tau / 10, (i + 1) * math.tau / 10
        c = (xb + s * 2.5, cz)
        K.cyl_along("Rim", W(c[0] + math.cos(a0), c[1] + math.sin(a0), 10.0), W(c[0] + math.cos(a1), c[1] + math.sin(a1), 10.0), 0.08, segs=4)
    B("Rim", min(xb + s * 1.5, xb + s * 1.6), max(xb + s * 1.5, xb + s * 1.6), cz - 0.15, cz + 0.15, 9.9, 10.1)
# bleachers on the north side, light poles at the corners
for i in range(3):
    z0 = CZ1 + 5.0 + i * 2.2
    B("Cap", 560.0, 610.0, z0, z0 + 2.2, 0, 1.0 + i * 1.2)
    B("Bench", 560.2, 609.8, z0 + 0.3, z0 + 1.9, 1.0 + i * 1.2, 1.3 + i * 1.2)
for (x, z) in ((CX0 - 2.0, CZ0 - 2.5), (CX1 + 2.0, CZ0 - 2.5), (CX0 - 2.0, CZ1 + 2.5), (CX1 + 2.0, CZ1 + 2.5)):
    K.cyl("Steel", W(x, z, 12.5), 0.3, 25.0, segs=8)
    B("Dark", x - 1.6, x + 1.6, z - 0.6, z + 0.6, 25.0, 26.2)
    K.lamp(W(x, z, 24.95), (2.6, 0.9, 0.1))

# ---------------------------------------------------------------- parking + planters
for i in range(10):                                                 # stalls along the north edge of the lot
    x = 535.0 + i * 10.0
    B("LotLine", x - 0.2, x + 0.2, -273.0, -257.0, 0, 0.012)
for i in range(6):                                                  # and along the Vipers fences
    x = 540.0 + i * 9.0
    B("LotLine", x - 0.2, x + 0.2, -357.6, -346.0, 0, 0.012)
B("Pave", 463.6, 466.4, -352.0, -264.0, 0, 0.6)
B("Soil", 463.9, 466.1, -351.7, -264.3, 0, 0.65)
for k in range(5):
    K.shrub(-465.0, -346.0 + k * 19.0, Y0 + 0.65, rng.uniform(1.6, 2.1), rng)
for x in (530.0, 638.0):
    K.palm(-x, -262.0, Y0, rng.uniform(24, 28), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)), rng)
for (x, z) in ((530.0, -270.0), (531.0, -352.0)):
    K.cyl("Bin", W(x, z, 1.6), 1.0, 3.2, segs=12)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("rec", W(560.0, -200.0, 60.0), W(550.0, -310.0, 0.0), lens=26)
