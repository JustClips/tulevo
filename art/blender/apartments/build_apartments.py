"""The Marlowe: a five-floor LA apartment block for the tulevo city (original name and design).

  blender --background --python build_apartments.py -- [OUT_DIR] [--no-render] [--samples N] [--res F]

Stucco block with white floor bands; ground floor = lobby with a canopy and the street number,
a coin laundry with a printed glass front, a garage with a roll-up gate. Upper floors: window
bays (curtains, blinds, some lit), projecting balconies with railings, chairs, plants and a
satellite dish or two, window A/C units. Steel fire escape down the east side with a drop
ladder; roof with parapet, stair house, A/C units, solar panels and vents. Front strip with
planters, palms, bins, a bike rack and a mailbox.
Textures: tools/apartment_textures.py -> tex/. Built in studs, -Y = street side.
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args  # noqa: E402

A = args(r"C:\out\apartments")
K = Kit("Apartments", A["out"], os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex"))
rng = random.Random(5)

W2, Y0, Y1 = 20 * M, -8 * M, 14 * M          # building x +-W2, front y=Y0, back y=Y1
GF, FL, NUP = 4.4 * M, 3.2 * M, 4            # ground floor, upper floor height, upper floors
TOPZ = GF + NUP * FL                          # roof deck
BAY = 5 * M

for name, sheet, tile in (("AptWall", "AptWall", (2 * M, 2 * M)), ("Concrete", None, None)):
    if sheet:
        K.mat(name, sheet=sheet, tile=tile)
for name in ("AptWindowA", "AptWindowB", "AptBalcony", "Laundromat", "LobbyGlass", "GarageGate", "AptSign", "AptBack", "Solar"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (
        ("Band", (0.93, 0.92, 0.88), 0.6, 0, 0), ("Pave", (0.62, 0.61, 0.58), 0.9, 0, 0), ("Roof", (0.36, 0.36, 0.35), 0.95, 0, 0),
        ("Rail", (0.08, 0.08, 0.09), 0.45, 0.6, 0), ("Steel", (0.10, 0.10, 0.11), 0.5, 0.6, 0), ("Units", (0.62, 0.63, 0.63), 0.5, 0.6, 0),
        ("AcBody", (0.85, 0.84, 0.80), 0.6, 0.2, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.2, 0), ("Trim", (0.20, 0.30, 0.34), 0.5, 0.3, 0),
        ("Chair", (0.90, 0.90, 0.88), 0.6, 0, 0), ("Pot", (0.62, 0.30, 0.20), 0.8, 0, 0), ("Dish", (0.85, 0.86, 0.86), 0.4, 0.4, 0),
        ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Bin", (0.10, 0.22, 0.12), 0.6, 0.1, 0), ("Mailbox", (0.10, 0.25, 0.55), 0.4, 0.3, 0),
        ("Shrub", (0.12, 0.30, 0.10), 0.85, 0, 0), ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
        ("Soil", (0.18, 0.12, 0.08), 1.0, 0, 0), ("Kerb", (0.62, 0.62, 0.60), 0.9, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)

# ---------------------------------------------------------------- site + block
K.boxr("Pave", -22 * M, 22 * M, -11 * M, 16 * M, -0.3, 0.0)
K.boxr("AptWall", -W2, W2, Y0, Y1, 0, TOPZ)
K.boxr("Roof", -W2 + 0.3 * M, W2 - 0.3 * M, Y0 + 0.3 * M, Y1 - 0.3 * M, TOPZ, TOPZ + 0.1)
for (x0, x1, y0, y1) in ((-W2, W2, Y0, Y0 + 0.3 * M), (-W2, W2, Y1 - 0.3 * M, Y1), (-W2, -W2 + 0.3 * M, Y0, Y1), (W2 - 0.3 * M, W2, Y0, Y1)):
    K.boxr("AptWall", x0, x1, y0, y1, TOPZ, TOPZ + 1.0 * M)                 # parapet
for (x0, x1, y0, y1) in ((-W2 - 0.1 * M, W2 + 0.1 * M, Y0 - 0.1 * M, Y0 + 0.3 * M), (-W2 - 0.1 * M, W2 + 0.1 * M, Y1 - 0.3 * M, Y1 + 0.1 * M),
                         (-W2 - 0.1 * M, -W2 + 0.3 * M, Y0, Y1), (W2 - 0.3 * M, W2 + 0.1 * M, Y0, Y1)):
    K.boxr("Band", x0, x1, y0, y1, TOPZ + 1.0 * M, TOPZ + 1.25 * M)       # parapet coping
for k in range(NUP + 1):                                                     # floor bands round three sides
    z = GF + k * FL
    K.boxr("Band", -W2 - 0.15 * M, W2 + 0.15 * M, Y0 - 0.2 * M, Y0, z - 0.15 * M, z + 0.15 * M)
    K.boxr("Band", -W2 - 0.2 * M, -W2, Y0 - 0.2 * M, Y1, z - 0.15 * M, z + 0.15 * M)
    K.boxr("Band", W2, W2 + 0.2 * M, Y0 - 0.2 * M, Y1, z - 0.15 * M, z + 0.15 * M)
for x in (-W2 + 10 * M, W2 - 10 * M):                                        # two vertical white fins
    K.boxr("Band", x - 0.25 * M, x + 0.25 * M, Y0 - 0.35 * M, Y0, GF, TOPZ + 1.6 * M)

# ---------------------------------------------------------------- ground floor: lobby, laundromat, garage
K.face_y("LobbyGlass", -16 * M, Y0 - 0.02, 0, 6 * M, GF * 0.98)
K.boxr("Trim", -20 * M, -12 * M, Y0 - 2.4 * M, Y0, GF - 0.9 * M, GF - 0.3 * M)            # canopy
K.face_y("AptSign", -16 * M, Y0 - 2.4 * M - 0.03, GF - 0.9 * M, 3.2 * M, 0.6 * M)
for sx in (-19.6 * M, -12.4 * M):
    K.cyl("Steel", (sx, Y0 - 2.2 * M, (GF - 0.9 * M) / 2), 0.08 * M, GF - 0.9 * M, segs=8)
K.lamp((-16 * M, Y0 - 1.2 * M, GF - 0.9 * M - 0.03), (2.4 * M, 0.5 * M, 0.04))
K.face_y("Laundromat", -2 * M, Y0 - 0.02, 0, 20 * M, GF * 0.98)
K.face_y("GarageGate", 14 * M, Y0 - 0.02, 0, 7 * M, 3.0 * M)
K.boxr("Dark", 10.4 * M, 17.6 * M, Y0 - 0.25 * M, Y0, 3.0 * M, 3.4 * M)                   # gate housing
for gx in (10.3 * M, 17.7 * M):
    K.box("Light", (gx, Y0 - 0.1 * M, 2.6 * M), (0.25 * M, 0.2 * M, 0.35 * M))
K.boxr("Concrete" if False else "Kerb", 10.4 * M, 17.6 * M, Y0 - 1.5 * M, Y0, -0.02, 0.02)  # driveway apron

# ---------------------------------------------------------------- upper floors: window bays, balconies, A/C units
BALC = {1, 2, 5, 6}
for f in range(NUP):
    z0 = GF + f * FL
    for b in range(8):
        cx = -W2 + (b + 0.5) * BAY
        if b in BALC:
            K.face_y("AptBalcony", cx, Y0 - 0.02, z0 + 0.15 * M, BAY, FL - 0.3 * M)
            bx0, bx1, by0 = cx - 2.3 * M, cx + 2.3 * M, Y0 - 1.5 * M
            K.boxr("Band", bx0, bx1, by0, Y0, z0 - 0.1 * M, z0 + 0.15 * M)
            for z in (z0 + 1.15 * M, z0 + 0.25 * M):
                K.boxr("Rail", bx0, bx1, by0, by0 + 0.06 * M, z - 0.03 * M, z + 0.03 * M)
                for x in (bx0, bx1 - 0.06 * M):
                    K.boxr("Rail", x, x + 0.06 * M, by0, Y0, z - 0.03 * M, z + 0.03 * M)
            n = 26
            for i in range(n + 1):
                x = bx0 + i * (bx1 - bx0) / n
                K.box("Rail", (x, by0 + 0.03 * M, z0 + 0.65 * M), (0.025 * M, 0.025 * M, 1.0 * M))
            # balcony life: a chair or two, a potted plant, now and then a satellite dish
            if rng.random() < 0.7:
                for c in range(rng.choice((1, 2))):
                    chx = bx0 + 0.8 * M + c * 0.8 * M
                    K.box("Chair", (chx, Y0 - 0.7 * M, z0 + 0.15 * M + 0.22 * M), (0.5 * M, 0.5 * M, 0.06 * M))
                    K.box("Chair", (chx, Y0 - 0.45 * M, z0 + 0.15 * M + 0.5 * M), (0.5 * M, 0.06 * M, 0.55 * M))
                    for sx in (-1, 1):
                        K.box("Chair", (chx + sx * 0.22 * M, Y0 - 0.7 * M, z0 + 0.15 * M + 0.11 * M), (0.05 * M, 0.45 * M, 0.22 * M))
            if rng.random() < 0.6:
                px = bx1 - 0.5 * M
                K.cyl("Pot", (px, Y0 - 0.5 * M, z0 + 0.15 * M + 0.22 * M), 0.22 * M, 0.44 * M, segs=10, r2=0.17 * M)
                K.shrub(px, Y0 - 0.5 * M, z0 + 0.15 * M + 0.4 * M, 0.35 * M, rng)
            if rng.random() < 0.25:
                dz = z0 + 1.6 * M
                K.cyl_along("Steel", (cx + 1.6 * M, Y0, dz), (cx + 1.6 * M, Y0 - 0.5 * M, dz), 0.03 * M, segs=6)
                K.cyl_along("Dish", (cx + 1.6 * M, Y0 - 0.5 * M, dz), (cx + 1.6 * M, Y0 - 0.62 * M, dz + 0.05 * M), 0.4 * M, segs=14)
        else:
            K.face_y("AptWindowA" if (b + f) % 2 else "AptWindowB", cx, Y0 - 0.02, z0 + 0.15 * M, BAY, FL - 0.3 * M)
            if rng.random() < 0.45:   # window A/C unit hanging out under one of the two windows
                ax = cx + rng.choice((-0.95, 0.95)) * M
                K.box("AcBody", (ax, Y0 - 0.3 * M, z0 + 0.15 * M + 1.15 * M), (0.75 * M, 0.6 * M, 0.45 * M))
                K.box("Dark", (ax, Y0 - 0.61 * M, z0 + 0.15 * M + 1.15 * M), (0.6 * M, 0.02 * M, 0.3 * M))
    # sides (4 bays of 5.5 m) and back
    for s in range(4):
        cy = Y0 + (s + 0.5) * 5.5 * M
        K.face_x("AptWindowA" if (s + f) % 2 else "AptWindowB", W2 + 0.02, cy, z0 + 0.15 * M, 5.5 * M, FL - 0.3 * M, facing=1)
        K.face_x("AptWindowB" if (s + f) % 2 else "AptWindowA", -W2 - 0.02, cy, z0 + 0.15 * M, 5.5 * M, FL - 0.3 * M, facing=-1)
    for b in range(8):
        K.face_y("AptBack", -W2 + (b + 0.5) * BAY, Y1 + 0.02, z0, BAY, FL, facing=1)
for b in range(8):
    K.face_y("AptBack", -W2 + (b + 0.5) * BAY, Y1 + 0.02, 0.3 * M, BAY, GF - 0.6 * M, facing=1)

# ---------------------------------------------------------------- fire escape on the east side
FX0, FX1 = W2 + 0.02, W2 + 1.4 * M
FY0, FY1 = Y0 + 5.5 * M, Y0 + 13 * M
for f in range(NUP):
    z = GF + f * FL - 0.05 * M
    K.boxr("Steel", FX0, FX1, FY0, FY1, z - 0.06 * M, z)
    for zz in (z + 1.0 * M, z + 0.5 * M):
        K.boxr("Rail", FX1 - 0.05 * M, FX1, FY0, FY1, zz - 0.03 * M, zz + 0.03 * M)
        for y in (FY0, FY1 - 0.05 * M):
            K.boxr("Rail", FX0, FX1, y, y + 0.05 * M, zz - 0.03 * M, zz + 0.03 * M)
    for i in range(16):
        K.box("Rail", (FX1 - 0.025 * M, FY0 + i * (FY1 - FY0) / 15, z + 0.5 * M), (0.03 * M, 0.03 * M, 1.0 * M))
    for i in range(8):   # grating slats
        K.box("Dark", ((FX0 + FX1) / 2, FY0 + (i + 0.5) * (FY1 - FY0) / 8, z + 0.005), (FX1 - FX0 - 0.1 * M, 0.05 * M, 0.01 * M))
    if f < NUP - 1:      # stair up to the next platform, alternating direction
        up = 1 if f % 2 == 0 else -1
        ya, yb = (FY0 + 0.4 * M, FY1 - 1.2 * M) if up > 0 else (FY1 - 0.4 * M, FY0 + 1.2 * M)
        n = 12
        for k in range(1, n):
            t = k / n
            K.box("Steel", ((FX0 + FX1) / 2, ya + (yb - ya) * t, z + FL * t), (FX1 - FX0 - 0.2 * M, 0.25 * M, 0.04 * M))
        for x in (FX0 + 0.1 * M, FX1 - 0.1 * M):
            K.cyl_along("Steel", (x, ya, z), (x, yb, z + FL), 0.05 * M, segs=4)
        K.cyl_along("Rail", (FX1 - 0.1 * M, ya, z + 0.9 * M), (FX1 - 0.1 * M, yb, z + FL + 0.9 * M), 0.03 * M, segs=6)
# drop ladder from the lowest platform (stops 2 m above the sidewalk)
lx = FX1 - 0.4 * M
for y in (FY0 + 0.3 * M, FY0 + 0.9 * M):
    K.box("Steel", (lx, y, GF - 1.0 * M), (0.05 * M, 0.05 * M, 2.4 * M))
for k in range(7):
    K.cyl_along("Steel", (lx, FY0 + 0.3 * M, GF - 2.1 * M + k * 0.32 * M), (lx, FY0 + 0.9 * M, GF - 2.1 * M + k * 0.32 * M), 0.02 * M, segs=6)

# ---------------------------------------------------------------- roof: stair house, units, solar, vents, dish
K.boxr("AptWall", -12 * M, -7 * M, 2 * M, 7 * M, TOPZ, TOPZ + 3.0 * M)
K.boxr("Band", -12.2 * M, -6.8 * M, 1.8 * M, 7.2 * M, TOPZ + 3.0 * M, TOPZ + 3.2 * M)
K.face_y("GarageGate", -9.5 * M, 1.98 * M, TOPZ, 1.0 * M, 2.1 * M)
for (cx, cy) in ((2 * M, 8 * M), (6 * M, 8 * M), (10 * M, 8 * M), (2 * M, -2 * M)):
    K.box("Units", (cx, cy, TOPZ + 0.6 * M), (2.0 * M, 1.6 * M, 1.2 * M))
    K.cyl("Dark", (cx, cy, TOPZ + 1.22 * M), 0.6 * M, 0.04, segs=14)
for row in range(3):
    for col in range(4):
        x, y = 4 * M + col * 3.6 * M, -5.5 * M + row * 2.4 * M
        K.quad("Solar", [(x - 1.6 * M, y - 0.8 * M, TOPZ + 0.5 * M), (x + 1.6 * M, y - 0.8 * M, TOPZ + 0.5 * M),
                         (x + 1.6 * M, y + 0.8 * M, TOPZ + 1.2 * M), (x - 1.6 * M, y + 0.8 * M, TOPZ + 1.2 * M)])
        for sx in (-1, 1):
            K.box("Steel", (x + sx * 1.4 * M, y + 0.6 * M, TOPZ + 0.6 * M), (0.08 * M, 0.08 * M, 1.2 * M))
            K.box("Steel", (x + sx * 1.4 * M, y - 0.6 * M, TOPZ + 0.3 * M), (0.08 * M, 0.08 * M, 0.6 * M))
for (vx, vy) in ((-16 * M, 0), (-3 * M, 10 * M), (15 * M, 2 * M), (-15 * M, 10 * M)):
    K.cyl("Units", (vx, vy, TOPZ + 0.5 * M), 0.1 * M, 1.0 * M, segs=8)
    K.cyl("Dark", (vx, vy, TOPZ + 1.05 * M), 0.18 * M, 0.12 * M, segs=8)
K.cyl("Steel", (-17 * M, 10 * M, TOPZ + 0.8 * M), 0.05 * M, 1.6 * M, segs=6)
K.cyl_along("Dish", (-17 * M, 10 * M, TOPZ + 1.6 * M), (-17 * M, 9.8 * M, TOPZ + 1.75 * M), 0.6 * M, segs=16)

# ---------------------------------------------------------------- front strip: planters, palms, bins, bike rack, mailbox
for (x0, x1) in ((-21.5 * M, -18.5 * M), (-11 * M, -8 * M), (4 * M, 7 * M)):
    K.boxr("Soil", x0, x1, -10.6 * M, -9.0 * M, 0.1 * M, 0.2 * M)
    for (a, b, c, d) in ((x0, x1, -10.6 * M - 0.15, -10.6 * M + 0.15), (x0, x1, -9.0 * M - 0.15, -9.0 * M + 0.15),
                         (x0 - 0.15, x0 + 0.15, -10.6 * M, -9.0 * M), (x1 - 0.15, x1 + 0.15, -10.6 * M, -9.0 * M)):
        K.boxr("Kerb", a, b, c, d, 0, 0.25 * M)
    K.palm((x0 + x1) / 2, -9.8 * M, 0.2 * M, rng.uniform(11, 13.5) * M, (rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.2)), rng)
    for k in range(3):
        K.shrub(x0 + 0.5 * M + k * 1.0 * M, -9.8 * M + (0.4 if k == 1 else -0.2) * M, 0.2 * M, 0.42 * M, rng)
for k, bx in enumerate((-13.5 * M, -12.6 * M)):
    K.box("Bin", (bx, -9.6 * M, 0.55 * M), (0.7 * M, 0.7 * M, 1.1 * M))
    K.box("Dark", (bx, -9.6 * M, 1.12 * M), (0.75 * M, 0.75 * M, 0.06 * M))
for k in range(4):                     # bike rack hoops
    x = -6 * M + k * 0.9 * M
    for sy in (-1, 1):
        K.box("Steel", (x, -9.8 * M + sy * 0.35 * M, 0.45 * M), (0.06 * M, 0.06 * M, 0.9 * M))
    K.box("Steel", (x, -9.8 * M, 0.9 * M), (0.06 * M, 0.76 * M, 0.06 * M))
K.box("Mailbox", (-7.5 * M, -10.2 * M, 0.75 * M), (0.55 * M, 0.5 * M, 0.9 * M))
K.cyl("Mailbox", (-7.5 * M, -10.2 * M, 1.2 * M), 0.25 * M, 0.55 * M, segs=12, axis='Y')
for sx in (-1, 1):
    for sy in (-1, 1):
        K.box("Dark", (-7.5 * M + sx * 0.22 * M, -10.2 * M + sy * 0.2 * M, 0.15 * M), (0.06 * M, 0.06 * M, 0.3 * M))

K.finish()
K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("01_street", (-34 * M, -48 * M, 6 * M), (0, 0, 9 * M), lens=24)
    K.shot("02_front", (2 * M, -34 * M, 2.2 * M), (-2 * M, -8 * M, 6 * M), lens=22)
    K.shot("03_fire_escape", (36 * M, -14 * M, 8 * M), (20 * M, 2 * M, 9 * M), lens=24)
    K.shot("04_aerial", (40 * M, -45 * M, 45 * M), (0, 2 * M, 8 * M), lens=30)
    K.shot("05_balconies", (-6 * M, -20 * M, 12 * M), (-8 * M, -8 * M, 13 * M), lens=22)
    print("done")
