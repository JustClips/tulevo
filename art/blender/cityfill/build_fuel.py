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

for name, sheet, tile in (("Asphalt", "LotAsphalt", (6, 6)), ("Pave", "Plinth", (3, 3)),
                          ("Stucco", "FuelStucco", (3, 3)), ("Canopy", "FuelWhite", (2, 2)),
                          ("Orange", "FuelOrange", (1, 1)), ("PumpRed", "PumpRed", (1, 1)),
                          ("Roof", "RoofTar", (4, 4)), ("AcBody", "HvacGrey", (1, 1)), ("Bin", "BinGreen", (1, 1))):
    K.mat(name, sheet=sheet, tile=(tile[0] * M, tile[1] * M))
for name in ("FuelSigns", "MartInterior"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Chrome", (0.78, 0.79, 0.81), 0.25, 1.0, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0),
                                      ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0), ("Hose", (0.04, 0.04, 0.04), 0.7, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


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

# ---------------------------------------------------------------- lot
B("Asphalt", -LX, LX, -LY, LY, -0.5, 0)
for (y0, y1) in ((-LY, -LY + 0.3), (LY - 0.3, LY)):                                     # kerbs on both streets, gaps at the drives
    for (x0, x1) in ((-LX, DRIVE[0]), (DRIVE[1], LX)):
        B("Pave", x0, x1, y0, y1, 0, 0.15)
B("Pave", -LX, -LX + 0.3, -LY + 0.3, LY - 0.3, 0, 0.15)                                 # west kerb (city edge)
B("Pave", CX0 - 0.5, CX1 + 0.5, CY0 - 0.5, CY1 + 0.5, 0, 0.04)                          # concrete apron under the canopy
B("Pave", KX0 - 2.0, LX - 0.3, KY0 - 1.5, KY1 + 1.5, 0, 0.15)                            # mart sidewalk
for (y0, y1) in ((-LY + 0.3, KY0 - 1.5), (KY1 + 1.5, LY - 0.3)):                         # planted strip along the gun shop wall
    B("Soil", LX - 2.3, LX - 0.3, y0 + 1, y1 - 1, 0, 0.16)
    n = int((y1 - y0 - 2) / 3)
    for k in range(n):
        K.shrub(X(LX - 1.3), (y0 + 2 + k * 3) * M, 0.16 * M, rng.uniform(0.45, 0.6) * M, rng)
# parking stalls in front of the mart (nose to the sidewalk) + lane arrows
for i in range(7):
    y = KY0 + i * 3.0
    B("LotLine", KX0 - 7.0, KX0 - 2.0, y - 0.06, y + 0.06, 0, 0.012)
for i in range(6):
    y = KY0 + (i + 0.5) * 3.0
    B("Pave", KX0 - 2.9, KX0 - 2.6, y - 0.9, y + 0.9, 0, 0.14)                          # wheel stops
for (ay, d) in ((-LY + 4.5, 1), (LY - 4.5, -1)):
    ax = (DRIVE[0] + DRIVE[1]) / 2
    B("LotLine", ax - 0.12, ax + 0.12, ay - 1.2, ay + 1.2, 0, 0.012)
    K.quad("LotLine", [(X(ax - 0.7), (ay + d * 1.2) * M, 0.012 * M), (X(ax + 0.7), (ay + d * 1.2) * M, 0.012 * M),
                       (X(ax), (ay + d * 2.2) * M, 0.012 * M)][::-d])

# ---------------------------------------------------------------- canopy + pumps
for x in (CX0 + 1.2, CX1 - 1.2):
    for y in (CY0 + 1.5, CY1 - 1.5):
        B("Canopy", x - 0.3, x + 0.3, y - 0.3, y + 0.3, 0.04, CZ0)
        B("Orange", x - 0.32, x + 0.32, y - 0.32, y + 0.32, 1.0, 1.4)
B("Canopy", CX0, CX1, CY0, CY1, CZ0, CZ1)
B("Orange", CX0 - 0.05, CX1 + 0.05, CY0 - 0.05, CY1 + 0.05, CZ1, CZ1 + 0.12)                 # roof edge
for (x0, x1, y) in ((CX0, CX1, CY0 - E), (CX1, CX0, CY1 + E)):                              # brand fascia on all four sides
    L = abs(x1 - x0)
    Q("FuelSigns", [(x0, y, CZ0), (x1, y, CZ0), (x1, y, CZ1), (x0, y, CZ1)], REG_FASCIA, reps=round(L / 3.6))
for (y0, y1, x) in ((CY1, CY0, CX0 - E), (CY0, CY1, CX1 + E)):
    L = abs(y1 - y0)
    Q("FuelSigns", [(x, y0, CZ0), (x, y1, CZ0), (x, y1, CZ1), (x, y0, CZ1)], REG_FASCIA, reps=round(L / 3.6))
for x in (CX0 + 3.0, (CX0 + CX1) / 2, CX1 - 3.0):                                         # lights under the canopy
    for y in (-5.0, 0.0, 5.0):
        K.lamp((X(x), y * M, (CZ0 - 0.05) * M), (1.4 * M, 0.5 * M, 0.08 * M))
for ix in (-8.5, -2.5):                                                                  # two islands, two pumps each
    B("Pave", ix - 0.7, ix + 0.7, -5.2, 5.2, 0.04, 0.24)
    for y in (-5.5, 5.5):
        K.cyl("Yellow", (X(ix), y * M, 0.6 * M), 0.12 * M, 1.0 * M, segs=8)              # bollards
    for py in (-2.6, 2.6):
        B("PumpRed", ix - 0.3, ix + 0.3, py - 0.55, py + 0.55, 0.24, 2.0)
        B("Canopy", ix - 0.34, ix + 0.34, py - 0.6, py + 0.6, 2.0, 2.25)
        B("Dark", ix - 0.32, ix + 0.32, py - 0.57, py + 0.57, 0.24, 0.34)
        for sx in (-1, 1):                                                               # printed face on each side
            x = ix + sx * (0.3 + E)
            ys = (py + 0.5, py - 0.5) if sx < 0 else (py - 0.5, py + 0.5)
            Q("FuelSigns", [(x, ys[0], 0.9), (x, ys[1], 0.9), (x, ys[1], 1.95), (x, ys[0], 1.95)], REG_PUMP)
            for dy in (-0.32, 0.32):                                                     # nozzles in their holsters + hoses
                hx = ix + sx * 0.36
                B("Dark", min(hx, hx + sx * 0.12), max(hx, hx + sx * 0.12), py + dy - 0.06, py + dy + 0.06, 1.0, 1.25)
                K.cyl_along("Hose", (X(hx), (py + dy) * M, 1.0 * M), (X(hx + sx * 0.25), (py + dy) * M, 0.5 * M),
                            0.025 * M, segs=5)
                K.cyl_along("Hose", (X(hx + sx * 0.25), (py + dy) * M, 0.5 * M), (X(ix + sx * 0.3), (py + dy * 0.6) * M, 1.7 * M),
                            0.025 * M, segs=5)
    K.cyl("Bin", (X(ix), 0.0, 0.7 * M), 0.28 * M, 0.9 * M, segs=12)                        # bin mid-island
    K.cyl("Dark", (X(ix), 0.0, 1.17 * M), 0.3 * M, 0.04 * M, segs=12)

# ---------------------------------------------------------------- Sundial Mart (storefront faces west, toward the pumps)
B("Stucco", KX0, KX1, KY0, KY1, 0.15, KH)
B("Orange", KX0 - 0.05, KX1 + 0.05, KY0 - 0.05, KY1 + 0.05, KH, KH + 0.5)                   # parapet band
B("Roof", KX0 + 0.25, KX1 - 0.25, KY0 + 0.25, KY1 - 0.25, KH + 0.1, KH + 0.3)
B("AcBody", KX0 + 3, KX0 + 4.6, KY0 + 4, KY0 + 5.8, KH + 0.3, KH + 1.4)
B("AcBody", KX0 + 3, KX0 + 4.6, KY1 - 6, KY1 - 4.2, KH + 0.3, KH + 1.4)
GX = KX0 - E                                                                             # storefront: printed interior + chrome frame
GY0, GY1 = KY0 + 1.0, KY1 - 1.0
Q("MartInterior", [(GX, GY1, 0.5), (GX, GY0, 0.5), (GX, GY0, 3.0), (GX, GY1, 3.0)], (0, 0, 1, 1))
for y in [GY0 + (GY1 - GY0) * k / 6 for k in range(7)]:
    B("Chrome", KX0 - 0.08, KX0, y - 0.05, y + 0.05, 0.45, 3.05)
for z in (0.45, 3.0):
    B("Chrome", KX0 - 0.08, KX0, GY0, GY1, z, z + 0.06)
B("Orange", KX0 - 1.4, KX0, KY0 - 0.2, KY1 + 0.2, 3.3, 3.5)                                # entry canopy
B("Dark", KX0 - 1.4, KX0, KY0 - 0.2, KY1 + 0.2, 3.25, 3.3)
SX = KX0 - 1.4 - E                                                                       # SUNDIAL MART sign on the canopy front
Q("FuelSigns", [(SX, 5.0, 3.55), (SX, -3.0, 3.55), (SX, -3.0, 5.55), (SX, 5.0, 5.55)], REG_MART)
B("Stucco", KX0 - 1.4 + 0.05, KX0, -3.0, 5.0, 3.5, 5.6)                                  # sign backing
B("PumpRed", KX0 - 2.0 + 0.3, KX0 - 2.0 + 0.9, KY1 + 0.4, KY1 + 1.0, 0.15, 1.6)             # air machine
B("Dark", KX0 - 2.0 + 0.28, KX0 - 2.0 + 0.92, KY1 + 0.38, KY1 + 1.02, 1.6, 1.7)
K.cyl_along("Hose", (X(KX0 - 1.4), (KY1 + 0.7) * M, 1.2 * M), (X(KX0 - 2.6), (KY1 + 0.7) * M, 0.2 * M), 0.025 * M, segs=5)
K.cyl("Bin", (X(KX0 - 1.2), (KY0 - 0.6) * M, 0.6 * M), 0.28 * M, 0.9 * M, segs=12)
B("Dark", KX1 - 0.02, KX1 + 0.04, 1.0, 2.0, 0.15, 2.3)                                    # back door to the stock room

# ---------------------------------------------------------------- price pylon on the Vault corner + lot lights
PX, PY = -11.0, -LY + 2.2
for dx in (-1.0, 1.0):
    B("Dark", PX - 0.12, PX + 0.12, PY + dx - 0.12, PY + dx + 0.12, 0, 1.6)
B("Pave", PX - 0.6, PX + 0.6, PY - 1.6, PY + 1.6, 0, 0.5)
B("Dark", PX - 0.2, PX + 0.2, PY - 1.25, PY + 1.25, 1.6, 5.4)                               # sign cabinet
for sx in (-1, 1):
    x = PX + sx * (0.2 + E)
    ys = (PY + 1.2, PY - 1.2) if sx < 0 else (PY - 1.2, PY + 1.2)
    Q("FuelSigns", [(x, ys[0], 1.65), (x, ys[1], 1.65), (x, ys[1], 5.35), (x, ys[0], 5.35)], REG_PYLON)
for (lx, ly) in ((-LX + 1.2, 12.0), (-LX + 1.2, -14.0), (LX - 3.5, -20.0), (LX - 3.5, 20.0)):
    K.cyl("Dark", (X(lx), ly * M, 4.0 * M), 0.1 * M, 8.0 * M, segs=8)
    B("Dark", lx - 0.15, lx + 0.15, ly - 0.15, ly + 0.15, 0, 0.6)
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
