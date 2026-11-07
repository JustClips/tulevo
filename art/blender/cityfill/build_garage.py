"""Eastside Parking garage + Eastside Self Storage on the empty lot off East Street between Meridian
Plaza, The Marlowe and the Red Crowns store (thread "Fill city with buildings and street props",
2026-11-07, Dev: "empty space here too").

  python3 tools/cityfill_textures.py garage      (GarageSigns, StoreDoor, StoreOrange, GarageBlue)
  blender --background --python build_garage.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin, like the Park). Roblox x/z:
  garage   x 163..330, z 283..357: ground + level 2 + roof deck, stacked straight ramps along the
           north side, entrance from East Street, open spandrel facades with a blue band, stair tower
           with the blade sign on the East Street corner
  storage  x 330..523: the garage's ground aisle runs on through a sign gate into a lane between two
           rows of orange roll-up units; planted strip behind the north row (The Marlowe's side)
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(12)
K = Kit("EastsideGarage", os.path.join(A["out"], "EastsideGarage"), BS.TEX)
for name, sheet, tile in (("Deck", "ForeCrete", (4 * M, 4 * M)), ("Wall", "ParkWall", (3 * M, 3 * M)), ("Cap", "ParkCap", (3 * M, 3 * M)),
                          ("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Block", "MallStucco", (3 * M, 3 * M)), ("RoofTar", "RoofTar", (4 * M, 4 * M)),
                          ("StoreOrange", "StoreOrange", (2 * M, 2 * M)), ("GarageBlue", "GarageBlue", (2 * M, 2 * M)),
                          ("Hazard", "Hazard", (1 * M, 1 * M)), ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Bin", "BinGreen", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("GarageSigns", "StoreDoor"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0), ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0),
                                      ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0), ("DoorGrey", (0.30, 0.33, 0.36), 0.5, 0.4, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    """Roblox x/z ranges (studs), h above the lot surface."""
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


def prism(part, x0, x1, z0, z1, b0, b1, t0, t1):
    """A box along Roblox x whose bottom runs b0 -> b1 and top t0 -> t1 (ramps, sloped kerbs)."""
    bm = K.bm(part)
    v = [bm.verts.new(W(*p)) for p in ((x0, z0, b0), (x1, z0, b1), (x1, z1, b1), (x0, z1, b0),
                                        (x0, z0, t0), (x1, z0, t1), (x1, z1, t1), (x0, z1, t0))]
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[i] for i in f])


def sign(cx, cz, h0, w, h, face, uv):
    """Printed GarageSigns quad. face: '-x' (seen from East St, west), '+x', '-z' (north), '+z' (south)."""
    (u0, v0), (u1, v1) = uv
    uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
    if face in ("-x", "+x"):
        K.face_x("GarageSigns", -cx, cz, Y0 + h0, w, h, facing=1 if face == "-x" else -1, uvs=uvs)
    else:
        K.face_y("GarageSigns", -cx, cz, Y0 + h0, w, h, facing=-1 if face == "-z" else 1, uvs=uvs)


UV_BLADE, UV_FASCIA = ((0, 0), (0.25, 1)), ((0.25, 0.75), (1, 1))
UV_ENTER, UV_CLEAR = ((0.25, 0.5), (0.625, 0.75)), ((0.625, 0.5), (1, 0.75))
UV_LEVEL = [((0.25 + k * 0.25, 0.25), (0.5 + k * 0.25, 0.5)) for k in range(3)]
UV_STORE = ((0.25, 0), (1, 0.25))

# ---------------------------------------------------------------- lot slabs
GX0, GX1, GZ0, GZ1 = 163.0, 330.0, 283.0, 357.0
B("Deck", 160.2, GX1, 280.2, 359.2, -1.2, 0)
B("Asphalt", GX1, 523.0, 270.2, 359.2, -1.2, 0)

# ---------------------------------------------------------------- garage decks + ramps
L1, L2, T = 10.8, 21.6, 1.0
SZ0, SZ1 = 284.2, 297.4             # ramp strip along the north wall
RX0, RX1 = 197.0, 293.0             # ramps rise eastward over 96 studs (11 %)
AZ0, AZ1 = 316.5, 338.5             # drive aisle (runs on into the storage lane)
I0, I1, J0, J1 = GX0 + 0.5, GX1 - 0.5, GZ0 + 0.5, GZ1 - 0.5     # decks end inside the walls
for L in (L1, L2):
    B("Deck", I0, I1, SZ1, J1, L - T, L)
    B("Deck", I0, RX0, J0, SZ1, L - T, L)
    B("Deck", RX1, I1, J0, SZ1, L - T, L)
prism("Deck", RX0, RX1, SZ0, SZ1, 0, 0, 0.02, L1)                    # ramp 1: solid wedge from the ground
prism("Deck", RX0, RX1, SZ0, SZ1, L1 - T, L2 - T, L1, L2)            # ramp 2: slab, level 2 to the roof
for (b0, b1) in ((0.02, L1), (L1, L2)):                              # kerbs along both sides of each ramp
    for z0, z1 in ((SZ0, SZ0 + 0.7), (SZ1 - 0.7, SZ1)):
        prism("Cap", RX0 + 0.04, RX1, z0, z1, b0 + 0.04, b1 + 0.04, b0 + 1.2, b1 + 1.2)
for L in (L1, L2):                                                   # walls along the hole's deck edge
    B("Wall", RX0, RX1, SZ1 + 0.04, SZ1 + 0.84, L, L + 3.2)
    B("Cap", RX0 - 0.06, RX1 + 0.06, SZ1 + 0.02, SZ1 + 0.9, L + 3.2, L + 3.5)
B("Wall", RX0 - 0.8, RX0 - 0.04, SZ0, SZ1 + 0.04, L2, L2 + 3.2)     # roof: end of the hole over ramp 2's foot
B("Cap", RX0 - 0.86, RX0 + 0.02, SZ0, SZ1 + 0.1, L2 + 3.2, L2 + 3.55)
# hazard paint on the ramp feet
for h in (0.0, L1):
    B("Hazard", RX0 - 2.4, RX0 - 0.6, SZ0 + 0.8, SZ1 - 0.8, h, h + 0.02)

# ---------------------------------------------------------------- facades: spandrels, blue band, columns
def walls(h0, h1, gaps_w=(), gaps_e=()):
    """Perimeter wall band h0..h1 (outer faces on the garage edge), with gaps (z ranges) west / east."""
    B("Wall", GX0, GX1, GZ0, GZ0 + 0.9, h0, h1)
    B("Wall", GX0, GX1, GZ1 - 0.9, GZ1, h0, h1)
    for x0, x1, gaps in ((GX0, GX0 + 0.9, gaps_w), (GX1 - 0.9, GX1, gaps_e)):
        z = GZ0 + 0.9
        for g0, g1 in sorted(gaps) + [(GZ1 - 0.9, GZ1)]:
            if g0 - z > 0.5:
                B("Wall", x0, x1, z, g0, h0, h1)
            z = g1


walls(0, 3.0, gaps_w=[(AZ0, AZ1), (300.0, 305.0)], gaps_e=[(AZ0, AZ1)])                 # ground: low wall, drive gaps
for L in (L1, L2):
    walls(L - T - 0.1, L + 3.6)
    for (x0, x1, z0, z1) in ((GX0 - 0.08, GX1 + 0.08, GZ0 - 0.08, GZ0), (GX0 - 0.08, GX1 + 0.08, GZ1, GZ1 + 0.08),
                             (GX0 - 0.08, GX0, GZ0, GZ1), (GX1, GX1 + 0.08, GZ0, GZ1)):
        B("GarageBlue", x0, x1, z0, z1, L + 2.2, L + 3.0)
    B("Cap", GX0 - 0.1, GX1 + 0.1, GZ0 - 0.1, GZ0 + 1.0, L + 3.6, L + 3.9)
    B("Cap", GX0 - 0.1, GX1 + 0.1, GZ1 - 1.0, GZ1 + 0.1, L + 3.6, L + 3.9)
    B("Cap", GX0 - 0.1, GX0 + 1.0, GZ0 + 1.0, GZ1 - 1.0, L + 3.6, L + 3.85)
    B("Cap", GX1 - 1.0, GX1 + 0.1, GZ0 + 1.0, GZ1 - 1.0, L + 3.6, L + 3.85)
B("Cap", GX0 - 0.1, GX1 + 0.1, GZ0 - 0.1, GZ0 + 1.0, 3.0, 3.3)
B("Cap", GX0 - 0.1, GX1 + 0.1, GZ1 - 1.0, GZ1 + 0.1, 3.0, 3.3)
# perimeter columns (proud of the walls), interior columns clear of the drive turns
for k in range(7):
    x = GX0 + 1.0 + k * (GX1 - GX0 - 2.0) / 6
    for z in (GZ0, GZ1):
        B("Cap", x - 1.0 - (0.25 if k == 0 else 0), x + 1.0 + (0.25 if k == 6 else 0), z - 0.25 if z == GZ0 else z - 1.8, z + 1.8 if z == GZ0 else z + 0.25, 0, L2 + 3.6)
for z in (307.0, 345.0):
    for x in (GX0, GX1):
        B("Cap", x - 0.25 if x == GX0 else x - 1.8, x + 1.8 if x == GX0 else x + 0.25, z - 1.0, z + 1.0, 0, L2 + 3.6)
for (x, z) in ((226.0, 316.0), (262.0, 316.0), (208.0, 339.0), (244.0, 339.0), (280.0, 339.0)):
    B("Cap", x - 0.9, x + 0.9, z - 0.9, z + 0.9, 0, L2)

# ---------------------------------------------------------------- stalls (all three decks)
for L in (0.0, L1, L2):
    y = L + 0.012
    for i in range(11):                                              # row A between the drive turns
        x = 199.0 + i * 9.1
        B("LotLine", x - 0.2, x + 0.2, SZ1 + 1.0 if L else 298.3, AZ0 - 0.3, y - 0.012, y)
    for i in range(17):                                              # row B after the stair tower
        x = 182.0 + i * 9.1
        B("LotLine", x - 0.2, x + 0.2, AZ1 + 0.3, GZ1 - 1.2, y - 0.012, y)
    for k in range(int((I1 - 172) / 14)):                            # dashed aisle centre line
        x = 172 + k * 14
        B("LotLine", x, x + 7, (AZ0 + AZ1) / 2 - 0.2, (AZ0 + AZ1) / 2 + 0.2, y - 0.012, y)

# ---------------------------------------------------------------- lights
for L in (L1, L2):
    for x in (190.0, 230.0, 270.0, 310.0):
        K.lamp(W(x, (AZ0 + AZ1) / 2, L - T - 0.12), (6.0, 1.2, 0.15))
        B("Dark", x - 3.2, x + 3.2, (AZ0 + AZ1) / 2 - 0.75, (AZ0 + AZ1) / 2 + 0.75, L - T - 0.05, L - T - 0.01)
for (x, z) in ((222.0, 356.5), (300.0, 356.5)):                      # roof poles on the south parapet
    K.cyl("Steel", W(x, z, L2 + 3.9 + 7.0), 0.3, 14.0, segs=8)
    for s in (-1, 1):
        B("Dark", x + s * 0.2, x + s * 3.2, z - 0.25, z + 0.25, L2 + 17.9, L2 + 18.4)
        K.lamp(W(x + s * 2.6, z, L2 + 17.8), (2.0, 1.0, 0.15))

# ---------------------------------------------------------------- stair tower (East St corner) + signs
TX0, TX1, TZ0, TZ1 = 162.7, 181.0, 339.4, 357.3
TH = L2 + 3.6 + 7.2
B("Block", TX0, TX1, TZ0, TZ1, 0, TH)
B("StoreOrange", TX0 - 0.1, TX1 + 0.1, TZ0 - 0.1, TZ1 + 0.1, TH - 1.2, TH - 0.4)
B("Cap", TX0 - 0.2, TX1 + 0.2, TZ0 - 0.2, TZ1 + 0.2, TH, TH + 0.35)
for k, L in enumerate((0.0, L1, L2)):                                # doors onto each deck + level plates
    B("DoorGrey", 168.0, 172.0, TZ0 - 0.12, TZ0, L, L + 7.4)
    B("Dark", 168.3, 171.7, TZ0 - 0.14, TZ0 - 0.1, L + 0.1, L + 7.1)
    sign(176.0, TZ0 - 0.04, L + 3.0, 3.4, 3.4, "-z", UV_LEVEL[k])
for (x, z) in ((226.0, 316.0), (262.0, 316.0)):                      # level plates on the aisle columns
    for k, L in enumerate((0.0, L1)):
        sign(x, z + 0.94, L + 4.0, 1.7, 1.7, "+z", UV_LEVEL[k])
B("GarageBlue", TX0 - 0.35, TX0 - 0.05, (TZ0 + TZ1) / 2 - 3.6,       # tall P PARKING sign facing East St
 (TZ0 + TZ1) / 2 + 3.6, 5.6, 32.4)
sign(TX0 - 0.39, (TZ0 + TZ1) / 2, 6.0, 6.5, 26.0, "-x", UV_BLADE)
# fascia over the entrance, ENTER + clearance boards, hazard bar
fz = (AZ0 + AZ1) / 2
B("GarageBlue", GX0 - 0.6, GX0 - 0.1, fz - 11.0, fz + 11.0, L1 - 1.6, L1 + 5.8)
sign(GX0 - 0.64, fz, L1 - 1.4, 21.6, 7.0, "-x", UV_FASCIA)
B("Wall", GX0, GX0 + 0.9, 310.2, 314.8, 3.0, 7.2)
sign(GX0 - 0.04, 312.5, 4.0, 4.5, 3.0, "-x", UV_CLEAR)
B("Hazard", GX0 + 1.4, GX0 + 2.0, AZ0 + 0.5, AZ1 - 0.5, 7.4, 8.2)
for z in (AZ0 + 1.5, AZ1 - 1.5):
    K.cyl("Steel", W(GX0 + 1.7, z, (8.2 + L1 - T) / 2), 0.08, L1 - T - 8.2, segs=6)
K.cyl("Steel", W(161.4, AZ1 + 3.0, 3.0), 0.15, 6.0, segs=8)          # ENTER board on a post by the drive
B("Dark", 161.3, 161.5, AZ1 + 0.8, AZ1 + 5.2, 3.3, 6.3)
sign(161.26, AZ1 + 3.0, 3.4, 4.2, 2.8, "-x", UV_ENTER)
# pay station by the stair door
B("Dark", 164.4, 165.6, TZ0 - 0.9, TZ0 - 0.1, 0, 0.3)
B("AcBody", 164.5, 165.5, TZ0 - 0.8, TZ0 - 0.2, 0.3, 5.0)
B("Yellow", 164.48, 165.52, TZ0 - 0.82, TZ0 - 0.18, 5.0, 5.4)

# ---------------------------------------------------------------- self storage
SX0, SX1 = 340.0, 520.0
SH = 12.0
ROWS = ((340.5, 357.5, -1), (294.5, 314.5, 1))                      # (z0, z1, door side): south row, north row
for z0, z1, side in ROWS:
    B("Block", SX0, SX1, z0, z1, 0, SH)
    B("RoofTar", SX0 + 0.3, SX1 - 0.3, z0 + 0.3, z1 - 0.3, SH, SH + 0.1)
    for (x0, x1, a0, a1) in ((SX0, SX1, z0, z0 + 0.6), (SX0, SX1, z1 - 0.6, z1), (SX0, SX0 + 0.6, z0 + 0.6, z1 - 0.6),
                             (SX1 - 0.6, SX1, z0 + 0.6, z1 - 0.6)):
        B("Block", x0, x1, a0, a1, SH, SH + 1.2)
    B("StoreOrange", SX0 - 0.1, SX1 + 0.1, z0 - 0.1, z1 + 0.1, SH - 1.6, SH - 0.6)
    B("Cap", SX0 - 0.15, SX1 + 0.15, z0 - 0.15, z1 + 0.15, SH + 1.2, SH + 1.45)
    B("Pave", SX0 - 0.2, SX1 + 0.2, z0 - 0.2, z1 + 0.2, 0, 0.5)               # plinth
    face = z0 if side < 0 else z1
    for k in range(12):
        x = SX0 + (k + 0.5) * (SX1 - SX0) / 12
        out = face - 0.03 if side < 0 else face + 0.03
        K.face_y("StoreDoor", -x, out, Y0 + 0.5, 9.4, 8.6, facing=side, uvs=((0, 0), (1, 0), (1, 1), (0, 1)))
        for s in (-1, 1):                                                    # jambs + header
            B("StoreOrange", x + s * 4.7 - 0.35, x + s * 4.7 + 0.35, min(face, face + side * 0.35), max(face, face + side * 0.35), 0.5, 9.4)
        B("StoreOrange", x - 5.05, x + 5.05, min(face, face + side * 0.35), max(face, face + side * 0.35), 9.1, 9.8)
        B("Dark", x - 0.4, x + 0.4, min(face, face + side * 0.12), max(face, face + side * 0.12), 0.9, 1.3)    # handle/lock
    for k in (1, 4, 7, 10):                                                  # wall packs between doors
        x = SX0 + (k + 1) * (SX1 - SX0) / 12
        B("Dark", x - 0.6, x + 0.6, min(face, face + side * 0.5), max(face, face + side * 0.5), 10.0, 10.0 + 0.7)
        K.lamp(W(x, face + side * 0.3, 9.95), (1.0, 0.5, 0.08))
    for k in range(3):
        K.box("AcBody", W(SX0 + 30 + k * 60, (z0 + z1) / 2, SH + 1.0), (3.0, 3.0, 1.8))
# sign gate between the garage and the lane
for z in (AZ0 - 1.0, AZ1 + 1.0):
    B("Block", 333.0, 335.0, z - 1.0, z + 1.0, 0, 17.4)
    B("Cap", 332.8, 335.2, z - 1.2, z + 1.2, 17.4, 17.7)
B("StoreOrange", 333.3, 334.7, AZ0 - 0.1, AZ1 + 0.1, 9.8, 17.0)
sign(333.26, (AZ0 + AZ1) / 2, 9.9, 20.8, 6.9, "-x", UV_STORE)
sign(334.74, (AZ0 + AZ1) / 2, 9.9, 20.8, 6.9, "+x", UV_STORE)
B("Dark", 336.0, 336.8, AZ1 - 3.0, AZ1 - 2.2, 0, 4.2)                # keypad post
B("Yellow", 335.94, 336.86, AZ1 - 3.06, AZ1 - 2.14, 4.2, 4.5)
# boundary wall on the police side, bins
B("Block", 521.6, 522.6, 271.0, 358.6, 0, 7.0)
B("Cap", 521.4, 522.8, 270.8, 358.8, 7.0, 7.3)
for (x, z) in ((516.0, 337.0), (512.0, 337.0)):
    K.cyl("Bin", W(x, z, 1.6), 1.0, 3.2, segs=12)
# planted strip behind the north row (The Marlowe's side)
B("Pave", SX0, SX1, 272.0, 273.0, 0, 0.6)
B("Pave", SX0, SX1, 292.4, 293.4, 0, 0.6)
B("Pave", SX0, SX0 + 1.0, 273.0, 292.4, 0, 0.6)
B("Pave", SX1 - 1.0, SX1, 273.0, 292.4, 0, 0.6)
B("Soil", SX0 + 1.0, SX1 - 1.0, 273.0, 292.4, 0, 0.5)
for k in range(6):
    x = SX0 + 15 + k * 30
    K.palm(-x, 282.5 + rng.uniform(-2, 2), Y0 + 0.5, rng.uniform(26, 32), (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)), rng)
for k in range(17):
    K.shrub(-(SX0 + 6 + k * 10.5), 277.0 + (k % 2) * 10.0, Y0 + 0.5, rng.uniform(2.4, 3.2), rng)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("garage_street", W(105.0, 395.0, 45.0), W(230.0, 320.0, 8.0), lens=26)
    K.shot("garage_roof", W(150.0, 250.0, 70.0), W(260.0, 330.0, 10.0), lens=26)
    K.shot("storage", W(420.0, 250.0, 70.0), W(430.0, 330.0, 0.0), lens=26)
