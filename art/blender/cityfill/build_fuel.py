"""Sundial Fuel: a corner gas station with a pump canopy and a small mart (original design,
thread "Fill city with buildings and street props", 2026-11-07; Dev: "add gas station").

  python3 tools/cityfill_textures.py fuel
  blender --background --python build_fuel.py -- OUT_DIR [--no-render] [--samples N] [--res F]

Runs the full depth of the block between Vault Ave (front, -Y) and Back St (back, +Y), with a
drive on each street. Canopy over two pump islands (four pumps), Sundial Mart along the east side
(storefront facing the pumps), price pylon on the Vault corner, air machine, bins, lot lights.

Lot 30.3 x 51 m, origin = lot centre, z 0 = lot surface; place it at y 0.3 (0.3 below the kerb).
"""
import json, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\fuel")
NAME = model_name("FuelStation", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(5)

LX, LY = 15.15, 25.5                               # lot half width / half depth (m)
DRIVE = (-13.0, -3.5)                             # drive x range (m) on both streets
CX0, CX1, CY0, CY1 = -12.5, 1.5, -9.0, 9.0        # canopy
CZ0, CZ1 = 5.0, 5.9
KX0, KX1, KY0, KY1 = 5.5, 14.2, -8.0, 10.0       # mart
KH = 4.4
GDY0, GDY1 = 0.0, 2.0                             # mart door opening (y)

for name, sheet, tile in (("Asphalt", "LotAsphalt", (6, 6)), ("Pave", "Plinth", (3, 3)), ("Fore", "ForeCrete", (4, 4)),
                          ("Stucco", "MartStucco", (3, 3)), ("Brick", "MartBrick", (3, 3)), ("Canopy", "FuelWhite", (2, 2)),
                          ("Soffit", "Soffit", (2, 2)), ("Brushed", "Brushed", (1, 1)), ("Hazard", "Hazard", (1, 1)),
                          ("Orange", "FuelOrange", (1, 1)), ("PumpRed", "PumpRed", (1, 1)),
                          ("Roof", "RoofTar", (4, 4)), ("AcBody", "HvacGrey", (1, 1)), ("Bin", "BinGreen", (1, 1))):
    K.mat(name, sheet=sheet, tile=(tile[0] * M, tile[1] * M))
for name in ("FuelSigns", "MartInterior", "MartPosters", "MartDoor"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Chrome", (0.78, 0.79, 0.81), 0.25, 1.0, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0),
                                      ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0), ("Hose", (0.04, 0.04, 0.04), 0.7, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Screen", (0.05, 0.12, 0.08), 0.2, 0, 0.6), ("BlueStall", (0.12, 0.32, 0.72), 0.8, 0, 0),
                                      ("Green", (0.10, 0.30, 0.18), 0.6, 0.3, 0), ("Glass", (0.22, 0.28, 0.32), 0.1, 0.2, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats()                                                                   # Pipe / Meter


# Layout below is written with +x = east (the gun shop side). Blender +x is Roblox west, so every
# coordinate goes through X() (mirror), and printed quads swap corner pairs to stay readable.
def X(x):
    return -x * M


def B(part, x0, x1, y0, y1, z0, z1):
    K.boxr(part, X(x1), X(x0), y0 * M, y1 * M, z0 * M, z1 * M)


def Q(part, pts, box, reps=1.0):
    """Quad (corners in m, counter-clockwise seen from the front) printed with an atlas region."""
    u0, v0, u1, v1 = box
    du = (u1 - u0) * reps
    c = [(X(x), y * M, z * M) for x, y, z in pts]
    K.quad(part, [c[1], c[0], c[3], c[2]], ((u0, v0), (u0 + du, v0), (u0 + du, v1), (u0, v1)))


REG_FASCIA = (0, 0.75, 1, 1)
REG_PYLON = (0, 0, 0.5, 0.75)
REG_MART = (0.5, 0.5, 1, 0.75)
REG_PUMP = (0.5, 0, 1, 0.5)
E = 0.02                                          # printed faces sit 2 cm off the surface they cover

def C(part, x, y, z, r, h, segs=12, r2=None):
    K.cyl(part, (X(x), y * M, z * M), r * M, h * M, segs=segs, r2=r2 * M if r2 else None)


def R(part, a, b, r, segs=6):
    K.cyl_along(part, (X(a[0]), a[1] * M, a[2] * M), (X(b[0]), b[1] * M, b[2] * M), r * M, segs=segs)


def poster(x, y0, y1, z0, z1, cell, facing=-1):
    """Printed poster on a wall plane at x (faces -x when facing=-1), cell 0..7 of MartPosters."""
    u0, v0 = (cell % 4) * 0.25, 0.5 - (cell // 4) * 0.5
    box = (u0, v0, u0 + 0.25, v0 + 0.5)
    ys = (y1, y0) if facing < 0 else (y0, y1)
    Q("MartPosters", [(x, ys[0], z0), (x, ys[1], z0), (x, ys[1], z1), (x, ys[0], z1)], box)


# ---------------------------------------------------------------- lot
B("Asphalt", -LX, LX, -LY, LY, -0.5, 0)
for (y0, y1) in ((-LY, -LY + 0.3), (LY - 0.3, LY)):                                     # kerbs on both streets, gaps at the drives
    for (x0, x1) in ((-LX, DRIVE[0]), (DRIVE[1], LX)):
        B("Pave", x0, x1, y0, y1, 0, 0.15)
B("Pave", -LX, -LX + 0.3, -LY + 0.3, LY - 0.3, 0, 0.15)                                 # west kerb (city edge)
B("Fore", CX0 - 1.5, CX1 + 1.0, CY0 - 2.0, CY1 + 2.0, 0, 0.04)                          # stained concrete forecourt
for (fx, fy, ring) in ((-14.0 + 1.6, -1.0, "Yellow"), (-14.0 + 1.6, 1.0, "PumpRed"), (-14.0 + 1.6, 3.0, "Green")):
    C("Brushed", fx, fy, 0.05, 0.32, 0.03, segs=14)                                     # underground tank fill caps
    C(ring, fx, fy, 0.045, 0.4, 0.03, segs=14)
B("Pave", KX0 - 2.0, LX - 0.3, KY0 - 1.5, KY1 + 1.5, 0, 0.15)                            # mart sidewalk
for y in [KY0 - 1.0 + k * 2.4 for k in range(9)]:                                       # steel bollards along the storefront edge
    if KY0 - 1.2 < y < KY1 + 1.2 and not (GDY0 - 0.4 < y < GDY1 + 0.4):
        C("Yellow", KX0 - 1.7, y, 0.15 + 0.5, 0.11, 1.0, segs=10)
        C("Dark", KX0 - 1.7, y, 1.17, 0.115, 0.04, segs=10)
for (y0, y1) in ((-LY + 0.3, KY0 - 1.5), (KY1 + 1.5, LY - 0.3)):                         # planted strip along the gun shop wall
    B("Pave", LX - 2.5, LX - 2.3, y0 + 0.8, y1 - 0.8, 0, 0.35)
    B("Soil", LX - 2.3, LX - 0.3, y0 + 1, y1 - 1, 0, 0.3)
    n = int((y1 - y0 - 2) / 2.2)
    for k in range(n):
        K.shrub(X(LX - 1.3), (y0 + 2 + k * 2.2) * M, 0.3 * M, rng.uniform(0.5, 0.7) * M, rng)
# parking stalls in front of the mart (nose to the sidewalk), the end one blue (accessible) + lane arrows
for i in range(7):
    y = KY0 + i * 3.0
    B("BlueStall" if i < 2 else "LotLine", KX0 - 7.0, KX0 - 2.0, y - 0.06, y + 0.06, 0, 0.012)
for i in range(6):
    y = KY0 + (i + 0.5) * 3.0
    B("Pave", KX0 - 2.9, KX0 - 2.6, y - 0.9, y + 0.9, 0, 0.14)                          # wheel stops
    B("Yellow", KX0 - 2.9, KX0 - 2.6, y - 0.9, y - 0.75, 0.14, 0.142)
for (ay, d) in ((-LY + 4.5, 1), (LY - 4.5, -1)):
    ax = (DRIVE[0] + DRIVE[1]) / 2
    B("LotLine", ax - 0.12, ax + 0.12, ay - 1.2, ay + 1.2, 0, 0.012)
    K.quad("LotLine", [(X(ax - 0.7), (ay + d * 1.2) * M, 0.012 * M), (X(ax + 0.7), (ay + d * 1.2) * M, 0.012 * M),
                       (X(ax), (ay + d * 2.2) * M, 0.012 * M)][::-d])
    B("LotLine", DRIVE[0] + 0.3, DRIVE[1] - 0.3, ay - d * 2.6 - 0.2, ay - d * 2.6 + 0.2, 0, 0.012)   # stop bar
# dumpster enclosure at the back corner of the mart (block walls, steel gates)
DX, DY = KX0 + 1.0, KY1 + 4.5
for (x0, x1, y0, y1) in ((DX, DX + 4.2, DY + 2.6, DY + 2.8), (DX, DX + 0.2, DY, DY + 2.6), (DX + 4.0, DX + 4.2, DY, DY + 2.6)):
    B("Brick", x0, x1, y0, y1, 0, 1.9)
    B("Pave", x0 - 0.03, x1 + 0.03, y0 - 0.03, y1 + 0.03, 1.9, 2.0)
for gx in (DX + 0.25, DX + 2.12):                                                      # gates (slatted steel)
    B("Green", gx, gx + 1.85, DY - 0.06, DY, 0.15, 1.8)
B("Green", DX + 0.6, DX + 3.6, DY + 0.6, DY + 2.3, 0.0, 1.25)                            # the dumpster
B("Dark", DX + 0.55, DX + 3.65, DY + 0.55, DY + 2.35, 1.25, 1.35)

# ---------------------------------------------------------------- canopy
for x in (CX0 + 1.2, CX1 - 1.2):
    for y in (CY0 + 1.5, CY1 - 1.5):
        B("Pave", x - 0.45, x + 0.45, y - 0.45, y + 0.45, 0.04, 0.9)                     # concrete pedestal
        B("Brushed", x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0.9, CZ0)                       # stainless cladding
        B("Orange", x - 0.32, x + 0.32, y - 0.32, y + 0.32, 2.6, 2.9)
        K.downpipe(X(x + 0.36), y * M, 0.9 * M, CZ0 * M)                                 # roof drain down the column
B("Canopy", CX0, CX1, CY0, CY1, CZ0, CZ1)
B("Orange", CX0 - 0.05, CX1 + 0.05, CY0 - 0.05, CY1 + 0.05, CZ1, CZ1 + 0.12)                 # roof edge
B("Canopy", CX0 + 0.3, CX1 - 0.3, CY0 + 0.3, CY1 - 0.3, CZ1 + 0.12, CZ1 + 0.18)              # roof deck
K.quad("Soffit", [(X(CX0 + 0.05), (CY0 + 0.05) * M, (CZ0 - E) * M), (X(CX1 - 0.05), (CY0 + 0.05) * M, (CZ0 - E) * M),
                  (X(CX1 - 0.05), (CY1 - 0.05) * M, (CZ0 - E) * M), (X(CX0 + 0.05), (CY1 - 0.05) * M, (CZ0 - E) * M)])
for (x0, x1, y) in ((CX0, CX1, CY0 - E), (CX1, CX0, CY1 + E)):                              # brand fascia on all four sides
    L = abs(x1 - x0)
    Q("FuelSigns", [(x0, y, CZ0), (x1, y, CZ0), (x1, y, CZ1), (x0, y, CZ1)], REG_FASCIA, reps=round(L / 3.6))
for (y0, y1, x) in ((CY1, CY0, CX0 - E), (CY0, CY1, CX1 + E)):
    L = abs(y1 - y0)
    Q("FuelSigns", [(x, y0, CZ0), (x, y1, CZ0), (x, y1, CZ1), (x, y0, CZ1)], REG_FASCIA, reps=round(L / 3.6))
for x in (CX0 + 3.0, (CX0 + CX1) / 2, CX1 - 3.0):                                         # recessed lights in the ceiling
    for y in (-5.5, -1.8, 1.8, 5.5):
        B("Dark", x - 0.75, x + 0.75, y - 0.3, y + 0.3, CZ0 - 0.06, CZ0 - E - 0.005)
        K.lamp((X(x), y * M, (CZ0 - 0.08) * M), (1.3 * M, 0.42 * M, 0.04 * M))

# ---------------------------------------------------------------- pump islands
for ix in (-8.5, -2.5):
    B("Pave", ix - 0.75, ix + 0.75, -5.6, 5.6, 0.04, 0.24)                                # island
    for (y0, y1) in ((-5.6, -4.9), (4.9, 5.6)):                                          # hazard-painted noses
        B("Hazard", ix - 0.77, ix + 0.77, y0 - 0.02 if y0 < 0 else y0, y1 + 0.02 if y1 > 0 else y1, 0.04, 0.26)
    for y in (-6.2, 6.2):                                                                # crash posts with black bands
        C("Yellow", ix, y, 0.04 + 0.55, 0.14, 1.1, segs=10)
        for zb in (0.5, 0.9):
            C("Dark", ix, y, zb, 0.145, 0.12, segs=10)
        C("Dark", ix, y, 1.16, 0.15, 0.04, segs=10)
    for py in (-2.6, 2.6):
        B("Brushed", ix - 0.36, ix + 0.36, py - 0.62, py + 0.62, 0.24, 0.42)              # plinth
        B("PumpRed", ix - 0.3, ix + 0.3, py - 0.55, py + 0.55, 0.42, 1.95)                # cabinet
        B("Chrome", ix - 0.31, ix + 0.31, py - 0.56, py + 0.56, 0.86, 0.9)                # trim line
        B("Canopy", ix - 0.25, ix + 0.25, py - 0.5, py + 0.5, 1.95, 2.55)                 # header with the brand
        B("Orange", ix - 0.26, ix + 0.26, py - 0.51, py + 0.51, 2.55, 2.62)
        B("Brushed", ix - 0.06, ix + 0.06, py - 0.06, py + 0.06, 2.62, 3.1)              # hose retractor mast
        B("Brushed", ix - 0.05, ix + 0.05, py - 0.5, py + 0.5, 3.1, 3.18)                # boom
        for sx in (-1, 1):
            x = ix + sx * (0.3 + E)
            ys = (py + 0.5, py - 0.5) if sx < 0 else (py - 0.5, py + 0.5)
            Q("FuelSigns", [(x, ys[0], 0.92), (x, ys[1], 0.92), (x, ys[1], 1.92), (x, ys[0], 1.92)], REG_PUMP)
            xh = ix + sx * (0.25 + E)                                                    # header: fascia print (brand)
            yh = (py + 0.48, py - 0.48) if sx < 0 else (py - 0.48, py + 0.48)
            Q("FuelSigns", [(xh, yh[0], 2.0), (xh, yh[1], 2.0), (xh, yh[1], 2.5), (xh, yh[0], 2.5)], REG_FASCIA)
            B("Dark", min(ix + sx * 0.3, ix + sx * 0.36), max(ix + sx * 0.3, ix + sx * 0.36), py - 0.42, py + 0.42, 0.55, 0.8)   # card/keypad ledge
            for dy in (-0.32, 0.32):                                                     # nozzles in holsters, hoses from the boom
                hx = ix + sx * 0.36
                B("Dark", min(hx, hx + sx * 0.12), max(hx, hx + sx * 0.12), py + dy - 0.07, py + dy + 0.07, 1.05, 1.3)
                R("Chrome", (hx + sx * 0.1, py + dy, 1.28), (hx + sx * 0.18, py + dy, 1.12), 0.02, segs=5)
                top = (ix + sx * 0.05, py + dy * 1.4, 3.1)
                mid = (ix + sx * 0.5, py + dy * 1.15, 0.9)
                R("Hose", top, mid, 0.03)
                R("Hose", mid, (hx + sx * 0.12, py + dy, 1.12), 0.03)
    C("Bin", ix, 0.0, 0.24 + 0.45, 0.28, 0.9, segs=12)                                   # bin + windscreen bucket
    C("Dark", ix, 0.0, 1.16, 0.3, 0.04, segs=12)
    B("Brushed", ix - 0.04, ix + 0.04, 0.7, 0.78, 0.24, 1.4)
    C("Green", ix, 0.74, 1.55, 0.2, 0.35, segs=10)                                      # squeegee bucket
    R("Dark", (ix, 0.74, 1.6), (ix + 0.1, 0.74, 2.1), 0.02)
    B("Brushed", ix - 0.12, ix + 0.12, -0.9, -0.7, 0.9, 1.5)                             # paper towel box on a post
    B("Brushed", ix - 0.03, ix + 0.03, -0.83, -0.77, 0.24, 0.9)

# ---------------------------------------------------------------- Sundial Mart (storefront faces west, toward the pumps)
B("Brick", KX0, KX1, KY0, KY1, 0.15, 1.1)                                                 # brick wainscot
B("Pave", KX0 - 0.06, KX1 + 0.06, KY0 - 0.06, KY1 + 0.06, 1.1, 1.18)                      # its cap
B("Stucco", KX0 + 0.04, KX1 - 0.04, KY0 + 0.04, KY1 - 0.04, 1.18, KH)
B("Orange", KX0 - 0.05, KX1 + 0.05, KY0 - 0.05, KY1 + 0.05, KH, KH + 0.5)                   # parapet band
B("Brushed", KX0 - 0.1, KX1 + 0.1, KY0 - 0.1, KY1 + 0.1, KH + 0.5, KH + 0.58)              # coping
B("Roof", KX0 + 0.25, KX1 - 0.25, KY0 + 0.25, KY1 - 0.25, KH + 0.1, KH + 0.3)
for (ax, ay) in ((KX0 + 3, KY0 + 4), (KX0 + 3, KY1 - 6)):                                  # rooftop units: body, fan, curb
    B("Pave", ax - 0.1, ax + 1.7, ay - 0.1, ay + 1.9, KH + 0.3, KH + 0.45)
    B("AcBody", ax, ax + 1.6, ay, ay + 1.8, KH + 0.45, KH + 1.5)
    C("Dark", ax + 0.8, ay + 0.9, KH + 1.53, 0.55, 0.06, segs=16)
    C("Brushed", ax + 0.8, ay + 0.9, KH + 1.57, 0.12, 0.04, segs=8)
for (vx, vy) in ((KX1 - 2.0, KY0 + 2.0), (KX1 - 2.0, KY1 - 2.5), (KX0 + 6.5, 1.0)):       # vent stacks
    C("Brushed", vx, vy, KH + 0.6, 0.1, 0.6, segs=8)
    C("Brushed", vx, vy, KH + 0.95, 0.16, 0.1, segs=8)
# storefront: glazing either side of a glass double door
GX = KX0 - E
GY0, GY1 = KY0 + 1.0, KY1 - 1.0
Q("MartInterior", [(GX, GY1, 1.18), (GX, GDY1, 1.18), (GX, GDY1, 3.0), (GX, GY1, 3.0)], (0, 0, 0.42, 1))
Q("MartInterior", [(GX, GDY0, 1.18), (GX, GY0, 1.18), (GX, GY0, 3.0), (GX, GDY0, 3.0)], (0.58, 0, 1, 1))
DGX = KX0 - 0.03 - E                                                                      # door leaves (printed glass door)
Q("MartDoor", [(DGX, GDY1, 0.15), (DGX, (GDY0 + GDY1) / 2 + 0.02, 0.15), (DGX, (GDY0 + GDY1) / 2 + 0.02, 2.4), (DGX, GDY1, 2.4)], (0, 0, 1, 1))
Q("MartDoor", [(DGX, (GDY0 + GDY1) / 2 - 0.02, 0.15), (DGX, GDY0, 0.15), (DGX, GDY0, 2.4), (DGX, (GDY0 + GDY1) / 2 - 0.02, 2.4)], (0, 0, 1, 1))
B("Glass", KX0 - 0.02, KX0, GDY0, GDY1, 2.45, 3.0)                                         # transom
for y in [GY0, GY0 + (GDY0 - GY0) / 2, GDY0, (GDY0 + GDY1) / 2, GDY1, GDY1 + (GY1 - GDY1) / 2, GY1]:
    B("Chrome", KX0 - 0.1, KX0, y - 0.05, y + 0.05, 0.15 if GDY0 - 0.01 <= y <= GDY1 + 0.01 else 1.12, 3.06)
for z in (1.12, 3.0):
    for (y0, y1) in ((GY0, GDY0), (GDY1, GY1)):
        B("Chrome", KX0 - 0.1, KX0, y0, y1, z, z + 0.06)
B("Chrome", KX0 - 0.1, KX0, GDY0, GDY1, 2.4, 2.46)
for (k, (y0, y1)) in enumerate(((GY0 + 0.3, GY0 + 1.2), (GY0 + 1.6, GY0 + 2.5), (GDY1 + 0.5, GDY1 + 1.4), (GY1 - 1.2, GY1 - 0.3))):
    poster(KX0 - 2 * E - 0.01, y0, y1, 1.5, 2.9, (0, 1, 2, 3)[k])                        # window posters (inside the glass)
B("Orange", KX0 - 1.4, KX0, KY0 - 0.2, KY1 + 0.2, 3.3, 3.5)                                # entry canopy
B("Soffit", KX0 - 1.38, KX0, KY0 - 0.18, KY1 + 0.18, 3.25, 3.3)
for y in (KY0 + 1.5, (GDY0 + GDY1) / 2, KY1 - 1.5):
    K.lamp((X(KX0 - 0.7), y * M, 3.22 * M), (0.4 * M, 0.4 * M, 0.04 * M))
SX = KX0 - 1.4 - E                                                                       # SUNDIAL MART sign on the canopy front
Q("FuelSigns", [(SX, 5.0, 3.55), (SX, -3.0, 3.55), (SX, -3.0, 5.55), (SX, 5.0, 5.55)], REG_MART)
B("Stucco", KX0 - 1.4 + 0.05, KX0, -3.0, 5.0, 3.5, 5.6)                                  # sign backing
# side + back walls: wall packs, downpipes, meter, back door with a light, ATM/AIR/PROPANE
for (y, face) in ((KY0, -1), (KY1, 1)):
    for x in (KX0 + 2.0, KX1 - 2.0):
        B("Dark", x - 0.18, x + 0.18, min(y, y + face * 0.14), max(y, y + face * 0.14), 3.3, 3.6)          # wall pack
        K.lamp((X(x), (y + face * 0.15) * M, 3.25 * M), (0.3 * M, 0.1 * M, 0.04 * M))
    K.downpipe(X(KX1 - 0.4), (y + face * 0.1) * M, 0.15 * M, KH * M)
B("Dark", KX1 + 0.0, KX1 + 0.06, 0.6, 1.6, 0.15, 2.3)                                      # back door + its light
B("Brushed", KX1 + 0.06, KX1 + 0.08, 0.7, 0.8, 1.0, 1.2)
K.lamp((X(KX1 + 0.2), 1.1 * M, 2.6 * M), (0.3 * M, 0.3 * M, 0.04 * M))
B("AcBody", KX1, KX1 + 0.2, -3.0, -2.4, 1.0, 1.8)                                          # electric meter box
# propane exchange cage by the south end of the storefront
PCX, PCY = KX0 - 1.5, KY0 - 1.3
B("Green", PCX - 0.4, PCX + 0.4, PCY - 1.0, PCY + 1.0, 0.15, 0.25)
for (a, b2) in ((PCX - 0.4, PCY - 1.0), (PCX + 0.4, PCY - 1.0), (PCX - 0.4, PCY + 1.0), (PCX + 0.4, PCY + 1.0)):
    B("Green", a - 0.03, a + 0.03, b2 - 0.03, b2 + 0.03, 0.25, 1.7)
for z in (0.8, 1.25, 1.7):
    B("Green", PCX - 0.42, PCX + 0.42, PCY - 1.02, PCY + 1.02, z, z + 0.04)
for k in range(3):
    C("Brushed", PCX, PCY - 0.6 + k * 0.6, 0.55, 0.15, 0.6, segs=10)
poster(PCX - 0.43, PCY - 0.5, PCY + 0.5, 1.75, 2.35, 7)
B("Green", PCX - 0.42, PCX - 0.41, PCY - 0.5, PCY + 0.5, 1.74, 2.36)
# air machine by the north end
AMX, AMY = KX0 - 1.6, KY1 + 0.8
B("Yellow", AMX - 0.3, AMX + 0.3, AMY - 0.3, AMY + 0.3, 0.15, 1.6)
B("Dark", AMX - 0.32, AMX + 0.32, AMY - 0.32, AMY + 0.32, 1.6, 1.7)
poster(AMX - 0.3 - E, AMY - 0.25, AMY + 0.25, 0.9, 1.5, 5)
R("Hose", (AMX - 0.3, AMY, 1.1), (AMX - 0.7, AMY + 0.3, 0.2), 0.025)
R("Hose", (AMX - 0.7, AMY + 0.3, 0.2), (AMX - 0.35, AMY + 0.25, 1.3), 0.025)
C("Bin", KX0 - 1.2, KY0 + 0.2, 0.15 + 0.45, 0.28, 0.9, segs=12)

# ---------------------------------------------------------------- price pylon on the Vault corner + lot lights
PX, PY = -11.0, -LY + 2.6
B("Soil", PX - 1.2, PX + 1.2, PY - 2.2, PY + 2.2, 0, 0.35)                                # planter round its base
B("Brick", PX - 1.3, PX + 1.3, PY - 2.3, PY - 2.2, 0, 0.45)
B("Brick", PX - 1.3, PX + 1.3, PY + 2.2, PY + 2.3, 0, 0.45)
B("Brick", PX - 1.3, PX - 1.2, PY - 2.2, PY + 2.2, 0, 0.45)
B("Brick", PX + 1.2, PX + 1.3, PY - 2.2, PY + 2.2, 0, 0.45)
for k in range(4):
    K.shrub(X(PX + (-0.6 if k % 2 else 0.6)), (PY - 1.5 + k * 1.0) * M, 0.35 * M, 0.42 * M, rng)
B("Brick", PX - 0.35, PX + 0.35, PY - 1.4, PY + 1.4, 0.35, 1.6)                             # brick base
B("Pave", PX - 0.4, PX + 0.4, PY - 1.45, PY + 1.45, 1.6, 1.68)
B("Dark", PX - 0.2, PX + 0.2, PY - 1.25, PY + 1.25, 1.68, 5.4)                              # sign cabinet
B("Orange", PX - 0.22, PX + 0.22, PY - 1.27, PY + 1.27, 5.4, 5.6)
for sx in (-1, 1):
    x = PX + sx * (0.2 + E)
    ys = (PY + 1.2, PY - 1.2) if sx < 0 else (PY - 1.2, PY + 1.2)
    Q("FuelSigns", [(x, ys[0], 1.72), (x, ys[1], 1.72), (x, ys[1], 5.35), (x, ys[0], 5.35)], REG_PYLON)
for (lx, ly) in ((-LX + 1.2, 12.0), (-LX + 1.2, -14.0), (LX - 3.5, -20.0), (LX - 3.5, 20.0)):
    C("Dark", lx, ly, 4.0, 0.1, 8.0, segs=8)
    B("Pave", lx - 0.3, lx + 0.3, ly - 0.3, ly + 0.3, 0, 0.6)
    B("Dark", lx - 0.4, lx + 0.4, ly - 0.25, ly + 0.25, 8.0, 8.2)
    K.lamp((X(lx), ly * M, 7.95 * M), (0.7 * M, 0.4 * M, 0.08 * M))

K.finish()
meta = K.export()
meta["driveways"] = [[X(DRIVE[0]), X(DRIVE[1]), "N"], [X(DRIVE[0]), X(DRIVE[1]), "S"]]
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("front", (X(-34), -40 * M, 14 * M), (0, -2 * M, 2 * M), lens=26)
    K.shot("pumps", (X(-20), -14 * M, 2.5 * M), (X(-5), 0, 2.5 * M), lens=26)
    K.shot("mart", (X(-6), 14 * M, 3 * M), (X(KX0), 0, 2.5 * M), lens=26)
