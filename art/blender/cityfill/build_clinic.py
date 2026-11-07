"""Eastside Clinic on the empty lot on East Street between the Pike building, Hotel Solana and the Vipers
court (thread "Fill city with buildings and street props", 2026-11-07, Dev: "fix gap").

  python3 tools/cityfill_textures.py clinic      (ClinicSigns, ClinicTeal)
  blender --background --python build_clinic.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin). Roblox x/z:
  lot      x 160..297, z -347..-256: patient parking off East Street (one drive at z -340..-326),
           planted strip with a pylon sign along the sidewalk
  clinic   x 236..292, z -338..-266: two floors, glass entry + canopy, EMERGENCY drop-off canopy,
           rooftop helipad, stair bulkhead, AC units
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(55)
K = Kit("Clinic", os.path.join(A["out"], "Clinic"), BS.TEX)
for name, sheet, tile in (("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Block", "HotelStucco", (3 * M, 3 * M)), ("Cap", "ParkCap", (3 * M, 3 * M)),
                          ("RoofTar", "RoofTar", (4 * M, 4 * M)), ("ClinicTeal", "ClinicTeal", (2 * M, 2 * M)),
                          ("Lawn", "ParkLawn", (4 * M, 4 * M)), ("Bench", "BenchWood", (1 * M, 1 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Bin", "BinGreen", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
K.mat("ClinicSigns", sheet="ClinicSigns", explicit=True)
K.facade_mats()
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0),
                                      ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0), ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0),
                                      ("DoorGrey", (0.30, 0.33, 0.36), 0.5, 0.4, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


def sign(cx, cz, h0, w, h, face, uv):
    (u0, v0), (u1, v1) = uv
    uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    if face in ("-x", "+x"):
        K.face_x("ClinicSigns", -cx, cz, Y0 + h0, w, h, facing=1 if face == "-x" else -1, uvs=uvs)
    else:
        K.face_y("ClinicSigns", -cx, cz, Y0 + h0, w, h, facing=-1 if face == "-z" else 1, uvs=uvs)


UV_BANNER, UV_EMERG, UV_PYLON = ((0, 0.75), (1, 1)), ((0, 0.5), (0.5, 0.75)), ((0.5, 0.5), (1, 0.75))
UV_HELI, UV_PARK, UV_CROSS = ((0, 0), (0.5, 0.5)), ((0.5, 0.25), (1, 0.5)), ((0.625, 0), (0.875, 0.25))

LX0, LX1, LZ0, LZ1 = 160.2, 296.6, -346.6, -256.2
B("Asphalt", LX0, LX1, LZ0, LZ1, -1.2, 0)
# ---------------------------------------------------------------- building
CX0, CX1, CZ0, CZ1, CH = 236.0, 292.0, -338.0, -266.0, 24.0
B("Pave", 224.0, CX0 + 0.1, -342.0, -262.0, 0, 0.45)                      # front walk
B("Block", CX0, CX1, CZ0, CZ1, 0, CH)
B("RoofTar", CX0 + 0.4, CX1 - 0.4, CZ0 + 0.4, CZ1 - 0.4, CH, CH + 0.1)
for x0, x1, z0, z1 in ((CX0, CX1, CZ0, CZ0 + 0.7), (CX0, CX1, CZ1 - 0.7, CZ1), (CX0, CX0 + 0.7, CZ0 + 0.7, CZ1 - 0.7),
                       (CX1 - 0.7, CX1, CZ0 + 0.7, CZ1 - 0.7)):
    B("Block", x0, x1, z0, z1, CH, CH + 2.0)
B("Cap", CX0 - 0.2, CX1 + 0.2, CZ0 - 0.2, CZ1 + 0.2, CH + 2.0, CH + 2.4)
B("Cap", CX0 - 0.12, CX1 + 0.12, CZ0 - 0.12, CZ1 + 0.12, 0, 1.2)
B("ClinicTeal", CX0 - 0.1, CX1 + 0.1, CZ0 - 0.1, CZ1 + 0.1, 11.4, 12.0)
# west (street) face: windows, glass entry, EMERGENCY doors
for z in range(-332, -264, 8):
    if -316 < z < -288:
        continue
    if z > -286:
        K.window3d("x", -CX0, 1, z, Y0 + 14.4, 5.0, 6.0, mull=1, depth=0.4)
        continue
    for h in (2.8, 14.4):
        K.window3d("x", -CX0, 1, z, Y0 + h, 5.0, 6.0, mull=1, depth=0.4)
K.window3d("x", -CX0, 1, -302.0, Y0 + 1.2, 12.0, 8.4, mull=3, transom=True, sill=False, depth=0.4)
K.window3d("x", -CX0, 1, -276.0, Y0 + 1.2, 8.0, 8.4, mull=1, transom=True, sill=False, depth=0.4)
B("Cap", CX0 - 0.7, CX0, -314.0, -290.0, 13.4, 20.8)                        # banner board
sign(CX0 - 0.74, -302.0, 14.1, 23.0, 5.75, "-x", UV_BANNER)
B("ClinicTeal", 229.0, CX0, -312.0, -292.0, 10.2, 10.9)                     # entry canopy
for z in (-311.4, -292.6):
    B("Steel", 229.4, 229.8, z - 0.2, z + 0.2, 0.45, 10.2)
for z in (-306.0, -298.0):
    K.lamp(W(232.0, z, 10.15), (1.6, 1.6, 0.1))
# emergency drop-off canopy over the walk and the aisle
B("ClinicTeal", 212.0, CX0, -284.0, -268.0, 12.6, 13.6)
for x in (212.8, 222.0):
    for z in (-283.2, -268.8):
        B("Steel", x - 0.25, x + 0.25, z - 0.25, z + 0.25, 0 if x < 223 and x < 214 else 0.45, 12.6)
for x in (216.0, 222.0, 230.0):
    K.lamp(W(x, -276.0, 12.55), (2.0, 2.0, 0.1))
B("Cap", 212.2, 212.6, -280.4, -271.6, 13.6, 17.8)
sign(212.16, -276.0, 13.8, 8.0, 3.8, "-x", UV_EMERG)
for z0 in (-275.0,):
    B("Yellow", 213.0, 223.4, z0 - 0.2, z0 + 0.2, 0, 0.02)
# north / south faces
for x in range(242, 290, 8):
    for h in (2.8, 14.4):
        K.window3d("y", CZ1, 1, -x, Y0 + h, 4.6, 6.0, mull=1, depth=0.4)
        K.window3d("y", CZ0, -1, -x, Y0 + h, 4.6, 6.0, mull=1, depth=0.4)
# cross tiles on the north-west and south-west corners up high
B("Cap", CX0 - 0.4, CX0, -337.0, -331.0, 17.0, 23.0)
sign(CX0 - 0.44, -334.0, 17.2, 5.6, 5.6, "-x", UV_CROSS)
# east (service) face
for z in range(-330, -268, 10):
    K.window3d("x", -CX1, -1, z, Y0 + 14.4, 4.6, 6.0, mull=1, depth=0.3)
B("DoorGrey", CX1, CX1 + 0.12, -306.0, -301.0, 0, 8.6)
K.lamp(W(CX1 + 0.5, -303.5, 9.6), (0.8, 1.2, 0.1))
# roof: helipad with edge lights, stair bulkhead, AC units
PX0, PX1, PZ0, PZ1, PH = 254.0, 282.0, -316.0, -288.0, CH + 1.0
B("Cap", PX0, PX1, PZ0, PZ1, CH + 0.1, PH)
for x in (PX0 + 2, PX1 - 2):
    for z in (PZ0 + 2, PZ1 - 2):
        B("Steel", x - 0.5, x + 0.5, z - 0.5, z + 0.5, CH + 0.1, CH + 0.2)
uv = ((0, 0), (0, 0.5), (0.5, 0.5), (0.5, 0))
K.quad("ClinicSigns", [W(PX0 + 0.6, PZ0 + 0.6, PH + 0.04), W(PX0 + 0.6, PZ1 - 0.6, PH + 0.04),
                       W(PX1 - 0.6, PZ1 - 0.6, PH + 0.04), W(PX1 - 0.6, PZ0 + 0.6, PH + 0.04)], uv)
for i in range(4):
    for x, z in ((PX0 + 0.3 + i * 9.13, PZ0 + 0.3), (PX0 + 0.3 + i * 9.13, PZ1 - 0.3),
                 (PX0 + 0.3, PZ0 + 0.3 + i * 9.13), (PX1 - 0.3, PZ0 + 0.3 + i * 9.13)):
        K.boxr("LightPad", -(x + 0.25), -(x - 0.25), z - 0.25, z + 0.25, Y0 + PH, Y0 + PH + 0.35, mat="Light")
B("Block", 282.0, 290.0, -280.0, -270.0, CH, CH + 8.0)
B("Cap", 281.8, 290.2, -280.2, -269.8, CH + 8.0, CH + 8.4)
B("DoorGrey", 281.88, 282.0, -277.0, -273.0, CH + 0.1, CH + 7.0)
for x, z in ((246.0, -330.0), (246.0, -276.0), (268.0, -276.0)):
    K.box("AcBody", W(x, z, CH + 1.0), (5.0, 4.0, 1.8))
    K.cyl("Dark", W(x + 1.0, z, CH + 1.95), 1.4, 0.1, segs=16)
# ---------------------------------------------------------------- parking + planting
for k in range(8):                                                          # row A, noses to the planted strip
    z = -322.0 + k * 9.0
    B("LotLine", 165.6, 183.0, z - 0.2, z + 0.2, 0, 0.012)
    if k < 7:
        B("Pave", 166.4, 167.4, z + 1.5, z + 7.5, 0, 0.45)
for k in range(6):                                                          # row B, noses to the walk
    z = -338.0 + k * 9.0
    B("LotLine", 203.0, 221.0, z - 0.2, z + 0.2, 0, 0.012)
    if k < 5:
        B("Pave", 219.4, 220.4, z + 1.5, z + 7.5, 0, 0.45)
for z in (-312.0, -330.0):                                                  # aisle arrows (simple bars)
    B("LotLine", 191.6, 192.4, z - 3.0, z + 3.0, 0, 0.012)
B("Lawn", LX0, 164.6, LZ0 + 0.1, -341.0, -1.0, 0.45)                         # planted strip, gap for the drive
B("Lawn", LX0, 164.6, -325.0, LZ1 - 0.1, -1.0, 0.45)
B("Lawn", 164.6, 224.0, LZ0 + 0.1, -342.0, -1.0, 0.45)
B("Lawn", CX0 + 0.1, LX1 - 0.1, LZ0 + 0.1, CZ0 - 0.3, -1.0, 0.45)
B("Lawn", CX0 + 0.1, LX1 - 0.1, CZ1 + 0.3, LZ1 - 0.1, -1.0, 0.45)
for z in (-318.0, -300.0, -282.0, -264.0):
    K.shrub(-162.4, z + rng.uniform(-1, 1), Y0 + 0.45, rng.uniform(1.0, 1.4), rng)
for z in (-291.0, -273.0, -259.0):
    K.palm(-162.4, z, Y0 + 0.45, rng.uniform(22, 26), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)), rng)
for x in (175.0, 195.0, 215.0):
    K.shrub(-x, -344.3, Y0 + 0.45, rng.uniform(1.0, 1.3), rng)
for x in (246.0, 262.0, 278.0):
    K.shrub(-x, -342.3, Y0 + 0.45, rng.uniform(1.0, 1.3), rng)
    K.shrub(-x, -261.0, Y0 + 0.45, rng.uniform(1.0, 1.3), rng)
# pylon sign by the drive (both faces)
B("Cap", 161.6, 163.2, -310.6, -299.4, 0.45, 2.0)
B("Block", 162.0, 162.8, -310.0, -300.0, 2.0, 7.4)
sign(161.96, -305.0, 2.3, 9.6, 4.8, "-x", UV_PYLON)
sign(162.84, -305.0, 2.3, 9.6, 4.8, "+x", UV_PYLON)
B("Cap", 161.8, 163.0, -310.2, -299.8, 7.4, 7.8)
# patient parking signs at the row ends
for x, z in ((174.0, -323.4), (212.0, -339.4)):
    K.cyl("Steel", W(x, z, 3.0), 0.12, 6.0, segs=8)
    B("Dark", x - 1.9, x + 1.9, z - 0.16, z - 0.1, 3.6, 5.6)
    sign(x, z - 0.2, 3.7, 3.6, 1.8, "-z", UV_PARK)
# lot lights
for (x, z) in ((162.4, -334.0), (162.4, -268.0), (222.8, -341.0), (222.8, -263.0)):
    K.cyl("Steel", W(x, z, 12.6), 0.3, 25.0, segs=8)
    B("Pave", x - 0.9, x + 0.9, z - 0.9, z + 0.9, 0.45, 1.4)
    B("Dark", x + 0.2, x + 3.2, z - 0.25, z + 0.25, 25.1, 25.6)
    K.lamp(W(x + 2.6, z, 25.0), (2.0, 1.0, 0.15))
# benches, bins, bike rack on the front walk
for z in (-322.0, -284.0 - 8.0):
    for i in range(3):
        B("Bench", 225.6 + i * 0.5, 226.0 + i * 0.5, z - 3.0, z + 3.0, 1.95, 2.2)
    B("Bench", 227.2, 227.5, z - 3.0, z + 3.0, 2.3, 3.8)
    for dz in (-2.5, 2.5):
        B("Steel", 225.4, 227.2, z + dz - 0.15, z + dz + 0.15, 0.45, 1.95)
for z in (-317.0, -287.0):
    K.cyl("Bin", W(226.0, z, 2.05), 0.9, 3.2, segs=12)
for i in range(5):
    K.cyl_along("Steel", W(225.0, -334.0 + i * 1.6, 0.45), W(225.0, -334.0 + i * 1.6, 3.0), 0.1, segs=6)
    K.cyl_along("Steel", W(227.6, -334.0 + i * 1.6, 0.45), W(227.6, -334.0 + i * 1.6, 3.0), 0.1, segs=6)
    K.cyl_along("Steel", W(225.0, -334.0 + i * 1.6, 3.0), W(227.6, -334.0 + i * 1.6, 3.0), 0.1, segs=6)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("clinic", W(120.0, -230.0, 60.0), W(240.0, -300.0, 6.0), lens=26)
    K.shot("clinic_front", W(170.0, -300.0, 14.0), W(236.0, -296.0, 10.0), lens=30)
