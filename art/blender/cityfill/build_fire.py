"""Tulevo Fire Dept Station 3 on the lot behind the Halvorsen building (by the Lindell skatepark wall)
and a community garden behind the main spawn plaza (thread "Fill city with buildings and street props",
2026-11-07, Dev: "two empty spaces").

  python3 tools/cityfill_textures.py fire      (FireSigns, FireDoor, FireRed)
  blender --background --python build_fire.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin). Roblox x/z:
  station  x -294..-160, z -359..-256: red brick firehouse with three bay doors onto a concrete apron
           on West Street, two-floor crew wing, hose tower, staff parking behind, drive along the north
  garden   x -80..80, z -359..-316: lawn, centre path, raised beds, palms, benches, tool shed, signs
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(33)
K = Kit("FireStation", os.path.join(A["out"], "FireStation"), BS.TEX)
for name, sheet, tile in (("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Deck", "ForeCrete", (4 * M, 4 * M)), ("Brick", "BrickRed", (2 * M, 2 * M)),
                          ("Cap", "ParkCap", (3 * M, 3 * M)), ("RoofTar", "RoofTar", (4 * M, 4 * M)),
                          ("FireRed", "FireRed", (2 * M, 2 * M)), ("Lawn", "ParkLawn", (4 * M, 4 * M)),
                          ("Path", "ParkPavers", (2 * M, 2 * M)), ("Wood", "TankWood", (1.5 * M, 1.5 * M)),
                          ("Bench", "BenchWood", (1 * M, 1 * M)), ("Mulch", "ParkMulch", (2 * M, 2 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Bin", "BinGreen", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("FireSigns", "FireDoor"):
    K.mat(name, sheet=name, explicit=True)
K.facade_mats()
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Crop", (0.30, 0.52, 0.18), 0.85, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
                                      ("Roof", (0.30, 0.31, 0.32), 0.9, 0, 0), ("DoorGrey", (0.30, 0.33, 0.36), 0.5, 0.4, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


def sign(cx, cz, h0, w, h, face, uv, part="FireSigns"):
    (u0, v0), (u1, v1) = uv
    uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    if face in ("-x", "+x"):
        K.face_x(part, -cx, cz, Y0 + h0, w, h, facing=1 if face == "-x" else -1, uvs=uvs)
    else:
        K.face_y(part, -cx, cz, Y0 + h0, w, h, facing=-1 if face == "-z" else 1, uvs=uvs)


UV_BANNER, UV_LANE, UV_GARDEN = ((0, 0.5), (1, 1)), ((0, 0), (0.5, 0.5)), ((0.5, 0), (1, 0.5))

# ================================================================ fire station
FX0, FX1, FZ0, FZ1, FH = -240.0, -200.0, -346.0, -262.0, 26.0
B("Asphalt", -296.0, -200.0, -359.2, -256.0, -1.2, 0)
B("Deck", -200.0, -160.2, -359.2, -256.0, -1.2, 0)
B("Brick", FX0, FX1, FZ0, FZ1, 0, FH)
B("RoofTar", FX0 + 0.4, FX1 - 0.4, FZ0 + 0.4, FZ1 - 0.4, FH, FH + 0.1)
for x0, x1, z0, z1 in ((FX0, FX1, FZ0, FZ0 + 0.7), (FX0, FX1, FZ1 - 0.7, FZ1), (FX0, FX0 + 0.7, FZ0 + 0.7, FZ1 - 0.7),
                       (FX1 - 0.7, FX1, FZ0 + 0.7, FZ1 - 0.7)):
    B("Brick", x0, x1, z0, z1, FH, FH + 2.0)
B("Cap", FX0 - 0.2, FX1 + 0.2, FZ0 - 0.2, FZ1 + 0.2, FH + 2.0, FH + 2.4)
B("Cap", FX0 - 0.12, FX1 + 0.12, FZ0 - 0.12, FZ1 + 0.12, 0, 1.2)            # stone base
B("FireRed", FX0 - 0.1, FX1 + 0.1, FZ0 - 0.1, FZ1 + 0.1, 14.6, 15.4)        # red band between the floors
# three apparatus bays facing West St (+x), piers between them
BZ0, BW, PW = FZ0 + 1.5, 16.0, 1.5
for k in range(3):
    zc = BZ0 + k * (BW + PW) + BW / 2
    sign(FX1 + 0.04, zc, 1.2, BW, 13.0, "+x", ((0, 0), (1, 1)), part="FireDoor")
    B("Cap", FX1, FX1 + 0.5, zc - BW / 2 - 0.4, zc + BW / 2 + 0.4, 14.2, 14.6)   # head
    for s in (-1, 1):
        B("Cap", FX1, FX1 + 0.4, zc + s * (BW / 2 + 0.2) - 0.2, zc + s * (BW / 2 + 0.2) + 0.2, 1.2, 14.2)
        K.cyl("FireRed", W(FX1 + 1.4, zc + s * (BW / 2 + 0.8), 1.6), 0.4, 3.2, segs=10)   # bollards
    K.lamp(W(FX1 + 0.6, zc, 15.2), (1.6, 0.6, 0.12))
    B("Dark", FX1 + 0.12, FX1 + 1.0, zc - 1.0, zc + 1.0, 15.26, 15.7)
    for z in (zc - 3.2, zc + 3.2):                                           # red lane edges on the apron
        B("FireRed", FX1 + 1.0, -162.0, z - 0.2, z + 0.2, 0, 0.02)
# banner over the bays
bz = BZ0 + 1.5 * BW + PW
B("Cap", FX1, FX1 + 0.3, bz - 19.0, bz + 19.0, 16.2, 25.0)
sign(FX1 + 0.34, bz, 16.6, 37.0, 8.0, "+x", UV_BANNER)
# crew wing (FZ0+56..FZ1): two floors of windows, glass entry, both street and back sides
WZ0 = BZ0 + 3 * (BW + PW)
for floor, h in ((0, 3.6), (1, 17.0)):
    for k in range(3):
        zc = WZ0 + 4.5 + k * 9.0
        if floor == 0 and k == 1:
            continue
        K.window3d("x", -FX1, -1, zc, Y0 + h, 4.6, 6.0, mull=1, depth=0.4)
for k in range(9):
    zc = FZ0 + 6 + k * 9.6
    K.window3d("x", -FX0, 1, zc, Y0 + 17.0, 4.6, 6.0, mull=1, depth=0.4)
zd = WZ0 + 13.5
B("DoorGrey", FX1, FX1 + 0.12, zd - 2.6, zd + 2.6, 1.2, 9.6)
B("Dark", FX1 + 0.12, FX1 + 0.16, zd - 2.2, zd + 2.2, 1.6, 9.2)
B("FireRed", FX1, FX1 + 3.2, zd - 4.0, zd + 4.0, 10.4, 11.0)                # entry canopy
for z in (zd - 3.6, zd + 3.6):
    B("Steel", FX1 + 2.7, FX1 + 3.1, z - 0.2, z + 0.2, 0, 10.4)
K.lamp(W(FX1 + 1.6, zd, 10.35), (1.6, 1.2, 0.1))
# back side: two doors to the staff lot
for z in (FZ0 + 20.0, FZ0 + 60.0):
    B("DoorGrey", FX0 - 0.12, FX0, z - 2.2, z + 2.2, 1.2, 9.2)
    K.lamp(W(FX0 - 0.5, z, 10.2), (0.8, 1.2, 0.1))
    B("Dark", FX0 - 0.9, FX0, z - 0.8, z + 0.8, 10.25, 10.7)
# hose tower at the back corner
TX0, TX1, TZ0, TZ1, TT = -252.0, -240.0, -346.0, -334.0, 46.0
B("Brick", TX0, TX1 + 0.6, TZ0, TZ1, 0, TT)
B("Cap", TX0 - 0.3, TX1 + 0.9, TZ0 - 0.3, TZ1 + 0.3, TT, TT + 0.6)
B("FireRed", TX0 - 0.1, TX1 + 0.7, TZ0 - 0.1, TZ1 + 0.1, TT - 3.0, TT - 2.2)
for h in (12.0, 22.0, 32.0):
    K.window3d("x", -TX0, 1, (TZ0 + TZ1) / 2, Y0 + h, 1.4, 4.0, mull=0, depth=0.3)
# roof units
for z in (-330.0, -300.0, -276.0):
    K.box("AcBody", W(-220.0, z, FH + 1.0), (5.0, 4.0, 1.8))
# flag pole + fire lane sign on the apron, hydrant-red posts
K.cyl("Steel", W(-165.0, -264.0, 15.0), 0.25, 30.0, segs=10)
K.cyl("Steel", W(-165.0, -264.0, 30.2), 0.45, 0.4, segs=10)
B("Pave", -166.2, -163.8, -265.2, -262.8, 0, 0.5)
K.cyl("Steel", W(-163.0, -352.0, 3.2), 0.15, 6.4, segs=8)
B("Dark", -163.08, -162.92, -354.2, -349.8, 3.6, 6.4)
sign(-162.88, -352.0, 3.7, 4.2, 2.6, "+x", UV_LANE)
# staff parking behind (stalls nose to the park wall), drive round the north end
for i in range(10):
    z = -350.0 + i * 9.0
    B("LotLine", -292.0, -274.0, z - 0.2, z + 0.2, 0, 0.012)
for i in range(9):
    z = -345.5 + i * 9.0
    B("Pave", -291.0, -290.0, z - 3.0, z + 3.0, 0, 0.45)
B("Pave", -296.0, -295.2, -359.2, -256.0, 0, 0.6)                          # kerb by the park wall
B("Pave", -293.2, -160.6, -359.2, -358.4, 0, 0.6)                          # kerb along the house fences
for (x, z) in ((-262.0, -352.0), (-262.0, -300.0)):
    K.cyl("Steel", W(x, z, 12.6), 0.3, 25.0, segs=8)
    B("Pave", x - 1.0, x + 1.0, z - 1.0, z + 1.0, 0, 1.4)
    for s in (-1, 1):
        B("Dark", x + s * 0.2, x + s * 3.2, z - 0.25, z + 0.25, 25.1, 25.6)
        K.lamp(W(x + s * 2.6, z, 25.0), (2.0, 1.0, 0.15))
for (x, z) in ((-244.0, -258.0), (-248.0, -258.0)):
    K.cyl("Bin", W(x, z, 1.6), 1.0, 3.2, segs=12)

# ================================================================ community garden
GX0, GX1, GZ0, GZ1 = -79.6, 79.6, -359.2, -316.4
B("Lawn", GX0, GX1, GZ0, GZ1, -1.0, 0.35)
for x0, x1, z0, z1 in ((GX0, GX1, GZ0, GZ0 + 0.8), (GX0, GX1, GZ1 - 0.8, GZ1), (GX0, GX0 + 0.8, GZ0 + 0.8, -342.0),
                       (GX0, GX0 + 0.8, -333.6, GZ1 - 0.8), (GX1 - 0.8, GX1, GZ0 + 0.8, -342.0), (GX1 - 0.8, GX1, -333.6, GZ1 - 0.8)):
    B("Cap", x0, x1, z0, z1, 0, 1.4)                                         # low wall, gaps for the path at both ends
PZ0, PZ1 = -342.0, -333.6
B("Path", GX0, GX1, PZ0, PZ1, 0, 0.45)
B("Path", -4.0, 4.0, GZ0 + 0.8, PZ0, 0, 0.45)
B("Path", -4.0, 4.0, PZ1, GZ1 - 0.8, 0, 0.45)
# raised beds with crops
for zc in (-350.4, -324.8):
    for k in range(6):
        xc = -70.0 + k * 13.2 + (8.4 if k >= 3 else 0)
        B("Wood", xc - 5.0, xc + 5.0, zc - 2.4, zc + 2.4, 0, 1.9)
        B("Soil", xc - 4.6, xc + 4.6, zc - 2.0, zc + 2.0, 1.9, 2.0)
        for j in range(4):
            K.shrub(-(xc - 3.5 + j * 2.33), zc + rng.uniform(-0.6, 0.6), Y0 + 1.95, rng.uniform(0.7, 1.0), rng, part="Crop")
# palms, benches along the path, tool shed, signs, bins
for x in (-60.0, -20.0, 20.0, 60.0):
    K.palm(-x, -337.8 + (5.6 if x < 0 else -5.6), Y0 + 0.35, rng.uniform(22, 27), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)), rng)
for x in (-44.0, 44.0):
    for z, s in ((PZ0 - 1.6, -1), (PZ1 + 1.6, 1)):
        for i in range(3):
            B("Bench", x - 3.0, x + 3.0, z - 0.75 + i * 0.5, z - 0.35 + i * 0.5, 1.5, 1.75)
        B("Bench", x - 3.0, x + 3.0, z + s * 0.9 - 0.15, z + s * 0.9 + 0.15, 1.9, 3.4)
        for dx in (-2.5, 2.5):
            B("Steel", x + dx - 0.15, x + dx + 0.15, z - 0.9, z + 0.9, 0.35, 1.5)
SX0, SX1, SZ0, SZ1 = 64.0, 76.0, -357.0, -347.0
B("Wood", SX0, SX1, SZ0, SZ1, 0.35, 8.5)
K.quad("Roof", [W(SX0 - 0.6, SZ0 - 0.6, 8.3), W(SX1 + 0.6, SZ0 - 0.6, 8.3), W(SX1 + 0.6, SZ1 + 0.6, 10.2), W(SX0 - 0.6, SZ1 + 0.6, 10.2)])
K.quad("Roof", [W(SX0 - 0.6, SZ1 + 0.6, 10.2), W(SX1 + 0.6, SZ1 + 0.6, 10.2), W(SX1 + 0.6, SZ0 - 0.6, 8.3), W(SX0 - 0.6, SZ0 - 0.6, 8.3)])
B("Wood", SX0, SX1, SZ1 - 0.01, SZ1, 8.5, 10.2)
B("DoorGrey", SX0 + 3.0, SX0 + 7.0, SZ1, SZ1 + 0.12, 0.35, 7.4)
for x, face in ((GX0 + 2.5, "-x"), (GX1 - 2.5, "+x")):
    for z in (PZ0 - 5.8, PZ0 - 1.4):
        K.cyl("Steel", W(x, z, 3.2), 0.12, 6.4, segs=6)
    B("Dark", x - 0.08, x + 0.08, PZ0 - 6.0, PZ0 - 1.2, 3.6, 6.4)
    sign(x - 0.12 if face == "-x" else x + 0.12, PZ0 - 3.6, 3.7, 4.6, 2.6, face, UV_GARDEN)
for (x, z) in ((-8.0, PZ0 - 1.4), (8.0, PZ1 + 1.4)):
    K.cyl("Bin", W(x, z, 1.95), 0.9, 3.2, segs=12)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("fire_front", W(-120.0, -250.0, 40.0), W(-215.0, -310.0, 8.0), lens=26)
    K.shot("fire_back", W(-300.0, -240.0, 50.0), W(-240.0, -320.0, 0.0), lens=26)
    K.shot("garden", W(0.0, -290.0, 45.0), W(0.0, -340.0, 0.0), lens=26)
