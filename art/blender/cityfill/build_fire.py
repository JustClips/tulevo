"""Tulevo Fire Dept Station 3 on the lot behind the Halvorsen building (by the Lindell skatepark wall)
and a community garden behind the main spawn plaza (thread "Fill city with buildings and street props",
2026-11-07, Dev: "two empty spaces").

  python3 tools/cityfill_textures.py fire      (FireSigns, FireDoor, FireRed, TruckRed, FireBrick, FireDecals)
  blender --background --python build_fire.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin). Roblox x/z:
  station  x -296..-160, z -359..-256: red brick firehouse with three bay doors (pilasters, panel rails,
           ENGINE / LADDER / RESCUE plates, gooseneck lights) onto a concrete apron on West Street, Engine 3
           parked out front, two-floor crew wing, hose tower with antenna + beacon, flag, memorial bell,
           hydrant, hose rack, staff parking behind, drive along the north
  garden   x -80..80, z -359..-316: lawn, centre path, raised beds, palms, benches, tool shed, signs
"""
import math, os, random, sys
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
                          ("Deck", "ForeCrete", (4 * M, 4 * M)), ("Brick", "FireBrick", (2 * M, 2 * M)),
                          ("Cap", "ParkCap", (3 * M, 3 * M)), ("RoofTar", "RoofTar", (4 * M, 4 * M)),
                          ("FireRed", "FireRed", (2 * M, 2 * M)), ("Lawn", "ParkLawn", (4 * M, 4 * M)),
                          ("Path", "ParkPavers", (2 * M, 2 * M)), ("Wood", "TankWood", (1.5 * M, 1.5 * M)),
                          ("Bench", "BenchWood", (1 * M, 1 * M)), ("Mulch", "ParkMulch", (2 * M, 2 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Bin", "BinGreen", (1 * M, 1 * M)),
                          ("TruckRed", "TruckRed", (2 * M, 2 * M)), ("Dumpster", "BinGreen", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("FireSigns", "FireDoor", "FireDecals"):
    K.mat(name, sheet=name, explicit=True)
K.facade_mats()
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Crop", (0.30, 0.52, 0.18), 0.85, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
                                      ("Roof", (0.30, 0.31, 0.32), 0.9, 0, 0), ("DoorGrey", (0.30, 0.33, 0.36), 0.5, 0.4, 0),
                                      ("TruckWhite", (0.92, 0.92, 0.90), 0.4, 0, 0), ("Locker", (0.70, 0.71, 0.73), 0.3, 1.0, 0),
                                      ("CabGlass", (0.05, 0.07, 0.09), 0.08, 0.6, 0), ("LightHead", (1.0, 0.97, 0.9), 0.3, 0, 5.0),
                                      ("LightBar", (1.0, 1.0, 1.0), 0.3, 0, 5.0), ("NeonRed", (1.0, 0.12, 0.10), 0.4, 0, 6.0),
                                      ("Brass", (0.78, 0.60, 0.25), 0.3, 1.0, 0), ("Hose", (0.86, 0.80, 0.64), 0.8, 0, 0),
                                      ("DoorRail", (0.50, 0.08, 0.08), 0.5, 0.3, 0)):
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
B("Brick", FX0 - 0.25, FX1 + 0.25, FZ0 - 0.25, FZ1 + 0.25, 23.6, 24.2)      # corbel courses under the parapet
B("Brick", FX0 - 0.5, FX1 + 0.5, FZ0 - 0.5, FZ1 + 0.5, 24.2, 24.9)
B("Cap", FX0 - 0.56, FX1 + 0.56, FZ0 - 0.56, FZ1 + 0.56, 24.9, 25.2)
# three apparatus bays facing West St (+x): brick pilasters, door heads, sectional door rails, name plates
BZ0, BW, PW = FZ0 + 1.5, 16.0, 1.5
BAYS = [BZ0 + k * (BW + PW) + BW / 2 for k in range(3)]
UV_PLATES = (((0, 1 - 480 / 1024), (0.5, 1 - 352 / 1024)), ((0.5, 1 - 480 / 1024), (1, 1 - 352 / 1024)),
             ((0, 1 - 608 / 1024), (0.5, 1 - 480 / 1024)))
PIERS = [(FZ0 - 0.3, BZ0 + 0.45, FH + 2.0)] + [(zc + BW / 2 - 0.45, zc + BW / 2 + PW + 0.45, 17.6) for zc in BAYS[:2]] \
    + [(BAYS[2] + BW / 2 - 0.45, BAYS[2] + BW / 2 + PW + 0.45, FH + 2.0)]
for z0, z1, top in PIERS:
    B("Brick", FX1, FX1 + 1.0, z0, z1, 1.2, top)                           # pilaster
    B("Cap", FX1, FX1 + 1.15, z0 - 0.15, z1 + 0.15, 0, 1.6)                 # plinth
    B("Cap", FX1, FX1 + 1.25, z0 - 0.25, z1 + 0.25, 15.5, 16.1)             # capital at the band
    if top < FH:
        B("Cap", FX1, FX1 + 1.25, z0 - 0.25, z1 + 0.25, top, top + 0.45)
    zm = (z0 + z1) / 2                                                       # gooseneck barn light
    K.cyl_along("Dark", W(FX1 + 1.0, zm, 12.4), W(FX1 + 2.0, zm, 13.2), 0.1, segs=6)
    K.cyl_along("Dark", W(FX1 + 1.95, zm, 13.2), W(FX1 + 2.55, zm, 13.05), 0.1, segs=6)
    K.cyl("Dark", W(FX1 + 2.6, zm, 12.8), 0.75, 0.6, segs=14, r2=0.22)
    K.lamp(W(FX1 + 2.6, zm, 12.46), (0.9, 0.9, 0.08))
for k, zc in enumerate(BAYS):
    sign(FX1 + 0.04, zc, 1.2, BW, 13.0, "+x", ((0, 0), (1, 1)), part="FireDoor")
    B("Cap", FX1, FX1 + 0.5, zc - BW / 2 - 0.4, zc + BW / 2 + 0.4, 14.2, 14.6)   # head
    for h in (4.45, 7.7, 10.95):                                              # sectional panel joints
        B("DoorRail", FX1 + 0.04, FX1 + 0.16, zc - BW / 2 + 0.3, zc + BW / 2 - 0.3, h - 0.07, h + 0.07)
    B("Dark", FX1 + 0.04, FX1 + 0.2, zc - BW / 2 + 0.3, zc + BW / 2 - 0.3, 1.2, 1.45)      # rubber seal
    for dz in (-2.0, 2.0):
        B("Steel", FX1 + 0.04, FX1 + 0.26, zc + dz - 0.5, zc + dz + 0.5, 2.0, 2.25)      # lift handles
    B("Dark", FX1, FX1 + 0.3, zc - 3.9, zc + 3.9, 15.6, 17.6)
    sign(FX1 + 0.34, zc, 15.7, 7.4, 1.85, "+x", UV_PLATES[k], part="FireDecals")
    K.cyl("FireRed", W(FX1 + 1.8, zc - BW / 2 + 0.8, 1.6), 0.4, 3.2, segs=10)   # bollards
    K.cyl("FireRed", W(FX1 + 1.8, zc + BW / 2 - 0.8, 1.6), 0.4, 3.2, segs=10)
    for z in (zc - 3.2, zc + 3.2):                                           # red lane edges on the apron
        B("FireRed", FX1 + 1.0, -162.0, z - 0.2, z + 0.2, 0, 0.02)
# banner over the bays, clear of the corbels
bz = BAYS[1]
B("Cap", FX1, FX1 + 0.7, bz - 17.0, bz + 17.0, 18.2, 26.6)
sign(FX1 + 0.74, bz, 18.4, 32.0, 8.0, "+x", UV_BANNER)
# crew wing (FZ0+56..FZ1): two floors of windows, glass entry, station plaque, planters, bench
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
B("Steel", FX1 + 0.16, FX1 + 0.3, zd + 1.4, zd + 1.6, 4.0, 6.4)              # push bar
B("FireRed", FX1, FX1 + 3.2, zd - 4.0, zd + 4.0, 10.4, 11.0)                # entry canopy
for z in (zd - 3.6, zd + 3.6):
    B("Steel", FX1 + 2.7, FX1 + 3.1, z - 0.2, z + 0.2, 0, 10.4)
K.lamp(W(FX1 + 1.6, zd, 10.35), (1.6, 1.2, 0.1))
B("Cap", FX1, FX1 + 0.2, zd - 3.4, zd + 3.4, 11.4, 13.8)                     # plaque over the canopy
sign(FX1 + 0.24, zd, 11.5, 6.6, 2.2, "+x", ((0.25, 1 - 352 / 1024), (1, 1 - 96 / 1024)), part="FireDecals")
for s in (-1, 1):                                                           # planters by the door
    z0, z1 = sorted((zd + s * 4.4, zd + s * 7.6))
    B("Cap", FX1 + 0.3, FX1 + 2.9, z0, z1, 0, 2.0)
    B("Soil", FX1 + 0.6, FX1 + 2.6, z0 + 0.3, z1 - 0.3, 2.0, 2.06)
    for j in range(2):
        K.shrub(-(FX1 + 1.6), z0 + 0.9 + j * 1.4, Y0 + 1.9, 0.9, rng)
for i in range(3):                                                          # bench under the north window
    B("Bench", FX1 + 0.6 + i * 0.5, FX1 + 1.0 + i * 0.5, -272.5, -266.5, 1.5, 1.75)
B("Bench", FX1 + 0.3, FX1 + 0.6, -272.5, -266.5, 1.9, 3.4)
for dz in (-2.5, 2.5):
    B("Steel", FX1 + 0.5, FX1 + 2.1, -269.5 + dz - 0.15, -269.5 + dz + 0.15, 0, 1.5)
# back side: two doors to the staff lot
for z in (FZ0 + 20.0, FZ0 + 60.0):
    B("DoorGrey", FX0 - 0.12, FX0, z - 2.2, z + 2.2, 1.2, 9.2)
    K.lamp(W(FX0 - 0.5, z, 10.2), (0.8, 1.2, 0.1))
    B("Dark", FX0 - 0.9, FX0, z - 0.8, z + 0.8, 10.25, 10.7)
# hose tower at the back corner, antenna + red beacon, siren
TX0, TX1, TZ0, TZ1, TT = -252.0, -240.0, -346.0, -334.0, 46.0
B("Brick", TX0, TX1 + 0.6, TZ0, TZ1, 0, TT)
B("Cap", TX0 - 0.3, TX1 + 0.9, TZ0 - 0.3, TZ1 + 0.3, TT, TT + 0.6)
B("FireRed", TX0 - 0.1, TX1 + 0.7, TZ0 - 0.1, TZ1 + 0.1, TT - 3.0, TT - 2.2)
B("Brick", TX0 - 0.35, TX1 + 0.6, TZ0 - 0.35, TZ1 + 0.35, TT - 5.0, TT - 4.2)
for h in (12.0, 22.0, 32.0):
    K.window3d("x", -TX0, 1, (TZ0 + TZ1) / 2, Y0 + h, 1.4, 4.0, mull=0, depth=0.3)
K.cyl("Steel", W(-249.0, -343.0, TT + 6.0), 0.15, 10.8, segs=8)
for h in (TT + 4.0, TT + 7.5):
    B("Steel", -249.9, -248.1, -343.06, -342.94, h, h + 0.12)
K.cyl("NeonRed", W(-249.0, -343.0, TT + 11.65), 0.35, 0.5, segs=10)
K.cyl("Steel", W(-244.0, -337.0, TT + 1.6), 0.18, 2.0, segs=8)
K.cyl("Dark", W(-244.0, -337.0, TT + 3.0), 0.7, 1.0, segs=12, r2=0.5)
K.cyl("Steel", W(-244.0, -337.0, TT + 3.7), 0.3, 0.4, segs=8, r2=0.1)
# roof: AC units with fan discs, vent stacks, hatch
for z in (-330.0, -300.0, -276.0):
    K.box("AcBody", W(-220.0, z, FH + 1.0), (5.0, 4.0, 1.8))
    K.cyl("Dark", W(-219.0, z, FH + 1.95), 1.4, 0.1, segs=16)
    K.cyl("Steel", W(-219.0, z, FH + 2.03), 0.25, 0.08, segs=8)
for x, z in ((-232.0, -320.0), (-232.0, -290.0), (-210.0, -285.0), (-228.0, -270.0)):
    K.cyl("Steel", W(x, z, FH + 1.5), 0.35, 3.0, segs=10)
    K.cyl("Steel", W(x, z, FH + 3.15), 0.6, 0.3, segs=10, r2=0.3)
B("Cap", -236.0, -232.0, -306.0, -302.0, FH, FH + 1.2)
B("DoorGrey", -235.7, -232.3, -305.7, -302.3, FH + 1.2, FH + 1.3)
# flag pole + flag, fire lane / keep clear signs, hydrant
K.cyl("Steel", W(-165.0, -264.0, 15.0), 0.25, 30.0, segs=10)
K.cyl("Steel", W(-165.0, -264.0, 30.2), 0.45, 0.4, segs=10)
B("Pave", -166.2, -163.8, -265.2, -262.8, 0, 0.5)
FLAG = ((0, 1 - 864 / 1024), (0.5, 1 - 608 / 1024))
(fu0, fv0), (fu1, fv1) = FLAG
N, FL, FTOP, FHT = 8, 8.0, 29.6, 4.0
for i in range(N):
    for side in (0, 1):
        za, zb = -264.3 - i * FL / N, -264.3 - (i + 1) * FL / N
        xa = -165.0 + 0.45 * math.sin(i * 0.9) * (i / N) + (0.03 if side else 0)
        xb = -165.0 + 0.45 * math.sin((i + 1) * 0.9) * ((i + 1) / N) + (0.03 if side else 0)
        ua, ub = fu0 + (fu1 - fu0) * i / N, fu0 + (fu1 - fu0) * (i + 1) / N
        c = [W(xa, za, FTOP - FHT), W(xb, zb, FTOP - FHT), W(xb, zb, FTOP), W(xa, za, FTOP)]
        uv = ((ua, fv0), (ub, fv0), (ub, fv1), (ua, fv1))
        if side:
            K.quad("Flag", c[::-1], uv[::-1], mat="FireDecals")
        else:
            K.quad("Flag", c, uv, mat="FireDecals")
for zz, uv in ((-352.0, UV_LANE), (-286.0, ((0.5, 1 - 608 / 1024), (1, 1 - 480 / 1024)))):
    K.cyl("Steel", W(-163.0, zz, 3.2), 0.15, 6.4, segs=8)
for (zz, uv, ww, hh) in ((-352.0, UV_LANE, 4.2, 2.6), (-286.0, ((0.5, 1 - 608 / 1024), (1, 1 - 480 / 1024)), 5.2, 1.3)):
    B("Dark", -163.08, -162.92, zz - ww / 2 - 0.1, zz + ww / 2 + 0.1, 3.6, 3.8 + hh)
    sign(-162.88, zz, 3.7, ww, hh, "+x", uv, part="FireSigns" if uv is UV_LANE else "FireDecals")
HX, HZ = -163.0, -327.75                                                    # hydrant
K.cyl("Hydrant", W(HX, HZ, 0.15), 0.62, 0.3, segs=12, mat="Yellow")
K.cyl("Hydrant", W(HX, HZ, 1.3), 0.45, 2.0, segs=12, mat="Yellow")
K.cyl("Hydrant", W(HX, HZ, 2.35), 0.56, 0.2, segs=12, mat="Yellow")
K.cyl("Hydrant", W(HX, HZ, 2.7), 0.5, 0.5, segs=12, r2=0.18, mat="Yellow")
K.cyl("Steel", W(HX, HZ, 3.05), 0.12, 0.25, segs=6)
K.cyl("Steel", W(HX, HZ, 1.65), 0.22, 1.5, segs=8, axis='Y')
K.cyl("Steel", W(HX + 0.55, HZ, 1.55), 0.3, 0.5, segs=8, axis='X')
# ---------------------------------------------------------------- Engine 3 parked on the apron in front of bay 2
TZ = BAYS[1]
R = 2.0
B("Dark", -195.0, -165.0, TZ - 2.4, TZ + 2.4, 1.8, 4.7)                     # chassis
for x in (-190.5, -186.0, -167.0):
    for s in (-1, 1):
        K.cyl("Tire", W(x, TZ + s * 3.6, R), R, 1.4, segs=18, axis='Y', mat="Dark")
        K.cyl("Steel", W(x, TZ + s * 3.6, R), 1.15, 1.52, segs=12, axis='Y')
        K.cyl("Steel", W(x, TZ + s * 3.6, R), 0.4, 1.7, segs=8, axis='Y')
WELLS = ((-193.2, -183.3), (-169.4, -164.6))
# body (lockers) and cab, wheel wells cut out of the lower skirt
B("TruckRed", -196.5, -176.5, TZ - 4.2, TZ + 4.2, 4.6, 12.0)
B("TruckRed", -173.7, -164.0, TZ - 4.2, TZ + 4.2, 4.6, 12.4)
for x0, x1 in ((-196.5, -193.2), (-183.3, -176.5), (-176.5, -173.7), (-173.7, -169.4)):
    B("TruckRed", x0, x1, TZ - 4.2, TZ + 4.2, 2.3, 4.6)
B("TruckRed", -176.5, -173.7, TZ - 3.6, TZ + 3.6, 4.6, 11.4)                # pump house between body and cab
for x0, x1 in ((-196.56, -176.5), (-173.7, -163.94)):
    B("TruckWhite", x0, x1, TZ - 4.26, TZ + 4.26, 6.1, 6.6)
for s in (-1, 1):
    zo = TZ + s * 4.2
    zp = lambda d: sorted((zo, zo + s * d))
    # upper locker row, roll-up doors with handles
    for i in range(4):
        x0 = -196.0 + i * 4.85
        a, b = zp(0.08)
        B("Locker", x0, x0 + 4.6, a, b, 7.0, 10.0)
        a, b = zp(0.16)
        B("Dark", x0 + 1.6, x0 + 3.0, a, b, 7.25, 7.45)
    for x0, x1 in ((-196.0, -193.5), (-183.0, -180.1), (-179.9, -177.0)):
        a, b = zp(0.08)
        B("Locker", x0, x1, a, b, 2.6, 5.8)
        a, b = zp(0.16)
        B("Dark", (x0 + x1) / 2 - 0.6, (x0 + x1) / 2 + 0.6, a, b, 5.3, 5.5)
    # livery band above the lockers
    sign(-186.0, zo + s * 0.06, 10.2, 18.6, 1.74, "+z" if s > 0 else "-z", ((0, 1 - 96 / 1024), (1, 1)), part="FireDecals")
    # pump panel: brushed plate, gauges, discharge outlets
    pz = TZ + s * 3.6
    a, b = sorted((pz, pz + s * 0.12))
    B("Steel", -176.3, -173.9, a, b, 2.8, 11.0)
    for gx, gh in ((-175.6, 9.2), (-174.6, 9.2), (-175.1, 8.0)):
        sign(gx, pz + s * 0.14, gh, 0.7, 0.7, "+z" if s > 0 else "-z", ((0, 0), (160 / 1024, 160 / 1024)), part="FireDecals")
    for gx in (-175.6, -174.6):
        K.cyl("Brass", W(gx, pz + s * 0.4, 4.6), 0.35, 0.6, segs=10, axis='Y')
        K.cyl("Brass", W(gx, pz + s * 0.75, 4.6), 0.45, 0.12, segs=10, axis='Y')
    # cab door with emblem, windows, step, handle, mirror
    sign(-171.4, zo + s * 0.06, 3.2, 3.2, 3.2, "+z" if s > 0 else "-z", ((0, 1 - 352 / 1024), (0.25, 1 - 96 / 1024)),
         part="FireDecals")
    for x0, x1 in ((-173.3, -169.9), (-169.3, -165.2)):
        a, b = zp(0.08)
        B("CabGlass", x0, x1, a, b, 7.6, 11.4)
    a, b = zp(0.1)
    B("Dark", -173.75, -173.55, a, b, 2.4, 11.6)                               # door seam
    B("Dark", -169.75, -169.55, a, b, 4.6, 11.6)
    a, b = zp(0.2)
    B("Steel", -170.6, -170.0, a, b, 7.0, 7.2)
    a, b = zp(0.7)
    B("Steel", -173.4, -169.9, a, b, 2.2, 2.45)
    a, b = zp(1.2)
    B("Dark", -165.4, -165.2, a, b, 9.0, 9.2)                                  # mirror arm
    B("Dark", -165.6, -165.0, sorted((zo + s * 0.9, zo + s * 1.4))[0], sorted((zo + s * 0.9, zo + s * 1.4))[1], 7.6, 10.4)
# front: windscreen, grille, headlights, bumper; rear: tail lights, step
B("CabGlass", -164.0, -163.88, TZ - 3.7, TZ + 3.7, 7.6, 11.6)
B("Steel", -164.0, -163.84, TZ - 2.2, TZ + 2.2, 3.4, 5.9)
for i in range(5):
    h = 3.7 + i * 0.48
    B("Dark", -163.84, -163.8, TZ - 2.0, TZ + 2.0, h, h + 0.18)
for s in (-1, 1):
    B("LightHead", -164.0, -163.86, TZ + s * 3.3 - 0.6, TZ + s * 3.3 + 0.6, 4.6, 5.6)
    B("NeonRed", -164.0, -163.86, TZ + s * 3.3 - 0.4, TZ + s * 3.3 + 0.4, 6.8, 7.3)
    B("NeonRed", -196.64, -196.5, TZ + s * 3.4 - 0.4, TZ + s * 3.4 + 0.4, 3.0, 4.4)
    B("NeonRed", -196.64, -196.5, TZ + s * 3.4 - 0.4, TZ + s * 3.4 + 0.4, 10.6, 11.6)
B("Steel", -164.0, -162.7, TZ - 4.3, TZ + 4.3, 2.0, 3.3)
B("Steel", -197.4, -196.5, TZ - 3.8, TZ + 3.8, 2.2, 2.8)
B("Locker", -196.58, -196.5, TZ - 3.0, TZ + 3.0, 4.8, 10.4)
# roof: light bar, ladder on brackets, hose bed rail
B("Dark", -167.4, -165.6, TZ - 3.9, TZ + 3.9, 12.4, 12.6)
B("NeonRed", -167.3, -165.7, TZ - 3.8, TZ - 0.7, 12.6, 13.2)
B("NeonRed", -167.3, -165.7, TZ + 0.7, TZ + 3.8, 12.6, 13.2)
B("LightBar", -167.3, -165.7, TZ - 0.6, TZ + 0.6, 12.6, 13.2)
for x in (-194.5, -181.0):
    B("Steel", x - 0.3, x + 0.3, TZ - 2.0, TZ + 2.0, 12.0, 12.7)
B("Steel", -170.6, -170.0, TZ - 2.0, TZ + 2.0, 12.4, 12.7)
for s in (-1, 1):
    B("Steel", -197.2, -168.6, TZ + s * 1.7 - 0.15, TZ + s * 1.7 + 0.15, 12.7, 13.3)
x = -196.6
while x < -168.8:
    K.cyl_along("Steel", W(x, TZ - 1.55, 13.0), W(x, TZ + 1.55, 13.0), 0.1, segs=6)
    x += 1.4
for s in (-1, 1):
    B("Steel", -196.4, -177.0, TZ + s * 3.9 - 0.1, TZ + s * 3.9 + 0.1, 12.0, 12.8)   # roof rails
# ---------------------------------------------------------------- back lot: hose rack, memorial bell, dumpster
for h in (1.6, 5.2):
    B("Steel", FX0 - 1.8, FX0 - 0.1, -316.2, -306.8, h - 0.15, h)
    for i in range(4):
        K.cyl("Hose", W(FX0 - 0.95, -315.0 + i * 2.4, h + 1.05), 1.0, 0.8, segs=14, axis='X')
        K.cyl("Brass", W(FX0 - 0.95, -315.0 + i * 2.4, h + 1.05), 0.3, 0.86, segs=8, axis='X')
for z in (-316.2, -306.8):
    for xo in (FX0 - 1.8, FX0 - 0.4):
        B("Steel", xo, xo + 0.3, z - 0.15 if z > -310 else z, z if z > -310 else z + 0.15, 0, 8.4)
BX, BZb = -178.0, -270.0                                                   # memorial bell by the flag
B("Brick", BX - 1.6, BX + 1.6, BZb - 1.6, BZb + 1.6, 0, 3.6)
B("Cap", BX - 1.8, BX + 1.8, BZb - 1.8, BZb + 1.8, 3.6, 3.9)
sign(BX + 1.64, BZb, 1.1, 2.6, 1.3, "+x", ((0.5, 1 - 864 / 1024), (1, 1 - 608 / 1024)), part="FireDecals")
for dz in (-1.3, 1.3):
    B("Dark", BX - 0.15, BX + 0.15, BZb + dz - 0.15, BZb + dz + 0.15, 3.9, 8.0)
B("Dark", BX - 0.2, BX + 0.2, BZb - 1.5, BZb + 1.5, 7.6, 8.0)
K.cyl("Brass", W(BX, BZb, 6.6), 0.9, 1.6, segs=16, r2=0.45)
K.cyl("Brass", W(BX, BZb, 5.75), 1.0, 0.14, segs=16)
K.cyl("Brass", W(BX, BZb, 7.5), 0.2, 0.2, segs=8)
DX0, DX1, DZ0, DZ1 = -262.0, -255.0, -259.6, -256.4                        # dumpster by the bins
B("Dumpster", DX0, DX1, DZ0, DZ1, 0.5, 4.4)
K.quad("Dumpster", [W(DX0 - 0.1, DZ0 - 0.2, 4.4), W(DX1 + 0.1, DZ0 - 0.2, 4.4), W(DX1 + 0.1, DZ1 + 0.1, 4.9), W(DX0 - 0.1, DZ1 + 0.1, 4.9)])
for x in (DX0 + 0.6, DX1 - 0.6):
    for z in (DZ0 + 0.5, DZ1 - 0.5):
        K.cyl("Dark", W(x, z, 0.25), 0.25, 0.5, segs=8, axis='X')

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
    K.shot("fire_truck", W(-150.0, -300.0, 12.0), W(-180.0, -319.0, 6.0), lens=30)
    K.shot("fire_bays", W(-170.0, -345.0, 14.0), W(-200.0, -315.0, 10.0), lens=28)
    K.shot("fire_back", W(-300.0, -240.0, 50.0), W(-240.0, -320.0, 0.0), lens=26)
    K.shot("garden", W(0.0, -290.0, 45.0), W(0.0, -340.0, 0.0), lens=26)
