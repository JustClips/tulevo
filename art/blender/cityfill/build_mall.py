"""Westgate Plaza: a one-storey strip mall with eight shops, a covered walkway and a parking lot
(original design, thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py mall
  blender --background --python build_mall.py -- OUT_DIR [--face S] [--no-render] [--samples N] [--res F]

Row of eight shops (printed interiors behind framed glass, door jambs, sign boards on the canopy
fascia: pizza, pet supply, arcade, nails, dentist, tax office, shoes, florist) under a
continuous canopy on square columns; stucco walls, maroon trim, stepped parapets and a centre
tower carrying the plaza name. Two rows of parking with wheel stops, lot lights, landscaped
front strip, tenant pylon sign. Back: service doors, dumpsters, rooftop units.

Lot 76 x 50 m, origin = lot centre, z 0 = lot surface; place at y 0.3. Drives at both ends of
the front edge (meta "driveways").
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\mall")
NAME = model_name("StripMall", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(5)

LX, LY0, LY1 = 38 * M, -25 * M, 25 * M
BX, BY0, BY1 = 35 * M, 8 * M, 22 * M          # building half width, front wall, back wall
CY = 3.6 * M                                  # canopy front edge
H, PH = 5.0 * M, 6.4 * M                      # roof height, parapet top
DRIVES = ((-35 * M, -28 * M), (28 * M, 35 * M))
NS = 8
SW = 2 * BX / NS

for name, sheet, tile in (("Stucco", "MallStucco", (2 * M, 2 * M)), ("Trim", "MallTrim", (1 * M, 1 * M)),
                          ("Roof", "RoofTar", (4 * M, 4 * M)), ("Asphalt", "LotAsphalt", (6 * M, 6 * M)),
                          ("Pave", "Plinth", (3 * M, 3 * M)), ("Pavers", "Pavers", (1.5 * M, 1.5 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Steel", "FireSteel", (1 * M, 1 * M)),
                          ("Soffit", "StoneTrim", (2 * M, 2 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("StorefrontsC", "StorefrontsD", "ShopSignsC", "ShopSignsD", "MallPylon"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Frame", (0.12, 0.12, 0.13), 0.4, 0.6, 0), ("Dark", (0.05, 0.05, 0.055), 0.5, 0.3, 0),
                                      ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0), ("Dumpster", (0.12, 0.30, 0.18), 0.6, 0.4, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats()


def quad_uv(part, corners, box):
    u0, v0, u1, v1 = box
    K.quad(part, corners, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


def panel_y(part, x0, x1, y, z0, z1, box, back=None):
    quad_uv(part, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], box)
    if back is not None:
        quad_uv(part, [(x1, back, z0), (x0, back, z0), (x0, back, z1), (x1, back, z1)], box)


# ---------------------------------------------------------------- lot
K.boxr("Asphalt", -LX, LX, LY0, LY1, -0.5 * M, 0)
K.boxr("Pave", DRIVES[0][1], DRIVES[1][0], LY0, LY0 + 0.3 * M, 0, 0.15 * M)            # front kerb + planting strip
K.boxr("Soil", DRIVES[0][1] + 0.3 * M, DRIVES[1][0] - 0.3 * M, LY0 + 0.3 * M, LY0 + 2.7 * M, 0, 0.14 * M)
K.boxr("Pave", DRIVES[0][1], DRIVES[1][0], LY0 + 2.7 * M, LY0 + 3.0 * M, 0, 0.15 * M)
for sx in (-1, 1):
    a, b = sorted((sx * DRIVES[0][1], sx * (DRIVES[0][1] + 0.3 * M)))
    K.boxr("Pave", a, b, LY0 + 0.3 * M, LY0 + 2.7 * M, 0, 0.15 * M)
for k in range(20):
    x = DRIVES[0][1] + 1.5 * M + k * (DRIVES[1][0] - DRIVES[0][1] - 3 * M) / 19
    if abs(x + 16 * M) < 3.5 * M:
        continue                                                                        # leave room for the pylon
    K.shrub(x, LY0 + 1.5 * M, 0.14 * M, rng.uniform(0.45, 0.6) * M, rng)
for sx in (-1, 1):                                                                       # side + back kerbs
    a, b = sorted((sx * LX, sx * (LX - 0.3 * M)))
    K.boxr("Pave", a, b, LY0, LY1, 0, 0.15 * M)
K.boxr("Pave", -LX + 0.3 * M, LX - 0.3 * M, LY1 - 0.3 * M, LY1, 0, 0.15 * M)


def stall_row(y_nose, y_tail, x0, x1, w=2.7 * M):
    n = int((x1 - x0) / w)
    for i in range(n + 1):
        x = x0 + i * w
        K.boxr("LotLine", x - 0.06 * M, x + 0.06 * M, min(y_nose, y_tail), max(y_nose, y_tail), 0, 0.012 * M)
    d = 1 if y_nose > y_tail else -1
    for i in range(n):
        x = x0 + (i + 0.5) * w
        a, b = sorted((y_nose - d * 0.9 * M, y_nose - d * 0.65 * M))
        K.boxr("Pave", x - 0.9 * M, x + 0.9 * M, a, b, 0, 0.14 * M)


stall_row(1.6 * M, -3.6 * M, -33 * M, 33 * M)                 # along the walkway, nose to the kerb
stall_row(-15.4 * M, -10.2 * M, -33 * M, 33 * M)              # back-to-back pair across the lot
stall_row(-15.8 * M, -21 * M, -26 * M, 26 * M)
K.boxr("Pave", -33 * M, 33 * M, -15.8 * M, -15.4 * M, 0, 0.15 * M)                       # median kerb between them
for (x, y) in ((-24 * M, -6.8 * M), (0, -6.8 * M), (24 * M, -6.8 * M), (-12 * M, -15.6 * M), (12 * M, -15.6 * M)):
    K.cyl("Pave", (x, y, 0.35 * M), 0.35 * M, 0.7 * M, segs=12)                        # lot lights
    K.cyl("Steel", (x, y, 4.6 * M), 0.11 * M, 7.8 * M, segs=10)
    for s in (-1, 1):
        K.cyl_along("Steel", (x, y, 8.3 * M), (x + s * 1.3 * M, y, 8.3 * M), 0.06 * M, segs=6)
        K.boxr("Steel", x + s * 0.9 * M - 0.6 * M, x + s * 0.9 * M + 0.6 * M, y - 0.3 * M, y + 0.3 * M, 8.15 * M, 8.45 * M)
        K.lamp((x + s * 0.9 * M, y, 8.13 * M), (1.0 * M, 0.45 * M, 0.04 * M))

# ---------------------------------------------------------------- building
K.boxr("Pavers", -BX - 1 * M, BX + 1 * M, CY - 1.6 * M, BY0, 0, 0.18 * M)               # walkway (raised kerb)
K.boxr("Pave", -BX - 1 * M, BX + 1 * M, CY - 1.7 * M, CY - 1.6 * M, 0, 0.18 * M)
K.boxr("Stucco", -BX, BX, BY0 + 0.3 * M, BY1, -0.3 * M, H)                                 # body (glass 0.3 m in)
for i in range(NS + 1):                                                                 # piers between the shops
    x = -BX + i * SW
    a0, a1 = max(-BX, x - 0.35 * M), min(BX, x + 0.35 * M)
    K.boxr("Stucco", a0, a1, BY0, BY0 + 0.3 * M, -0.3 * M, H)
for i in range(NS):
    x0, x1 = -BX + i * SW + 0.35 * M, -BX + (i + 1) * SW - 0.35 * M
    sheet = "StorefrontsC" if i < 4 else "StorefrontsD"
    c = i % 4
    u0, v0 = (c % 2) * 0.5, 0.5 - (c // 2) * 0.5
    gy = BY0 + 0.28 * M
    panel_y(sheet, x0, x1, gy, 0.3 * M, 3.4 * M, (u0, v0, u0 + 0.5, v0 + 0.5))
    for fx in (x0 + 0.04 * M, x1 - 0.04 * M, x1 - (x1 - x0) * 0.22):
        K.boxr("Frame", fx - 0.05 * M, fx + 0.05 * M, gy - 0.08 * M, gy + 0.01 * M, 0.3 * M, 3.45 * M)
    for z in (0.25 * M, 3.4 * M):
        K.boxr("Frame", x0, x1, gy - 0.08 * M, gy + 0.01 * M, z, z + 0.08 * M)
    K.boxr("Stucco", x0, x1, BY0 + 0.1 * M, gy - 0.08 * M, 3.5 * M, H)                    # wall over the glass
    K.boxr("Trim", x0, x1, BY0 + 0.05 * M, BY0 + 0.1 * M, 0.0, 0.3 * M)                    # base tile strip
# canopy: slab, fascia with the sign boards, columns, soffit lights
K.boxr("Soffit", -BX - 0.6 * M, BX + 0.6 * M, CY, BY0 + 0.1 * M, 3.9 * M, 4.1 * M)
K.boxr("Trim", -BX - 0.7 * M, BX + 0.7 * M, CY - 0.1 * M, CY + 0.25 * M, 3.8 * M, 5.0 * M)
for i in range(NS):
    x0, x1 = -BX + i * SW + 0.6 * M, -BX + (i + 1) * SW - 0.6 * M
    sheet = "ShopSignsC" if i < 4 else "ShopSignsD"
    c = i % 4
    panel_y(sheet, x0, x1, CY - 0.12 * M, 3.95 * M, 4.85 * M, (0, 1 - (c + 1) * 0.25, 1, 1 - c * 0.25))
    K.lamp((-BX + (i + 0.5) * SW, (CY + BY0) / 2, 3.88 * M), (1.4 * M, 0.5 * M, 0.04 * M))
for i in range(NS + 1):
    x = -BX + i * SW
    K.boxr("Stucco", x - 0.3 * M, x + 0.3 * M, CY + 0.05 * M, CY + 0.65 * M, 0.18 * M, 3.8 * M)
    K.boxr("Trim", x - 0.38 * M, x + 0.38 * M, CY - 0.03 * M, CY + 0.73 * M, 0.18 * M, 0.6 * M)
# parapets: stepped, higher over every other shop; centre tower with the plaza name
K.boxr("Roof", -BX + 0.3 * M, BX - 0.3 * M, BY0 + 0.3 * M, BY1 - 0.3 * M, H, H + 0.05 * M)
for i in range(NS):
    x0, x1 = -BX + i * SW, -BX + (i + 1) * SW
    top = PH if i % 2 == 0 else PH - 0.8 * M
    K.boxr("Stucco", x0, x1, BY0, BY0 + 0.3 * M, H, top)
    K.boxr("Trim", x0 - 0.02 * M, x1 + 0.02 * M, BY0 - 0.12 * M, BY0 + 0.32 * M, top, top + 0.25 * M)
for sx in (-1, 1):
    a, b = sorted((sx * BX, sx * (BX - 0.3 * M)))
    K.boxr("Stucco", a, b, BY0 + 0.3 * M, BY1, H, H + 1.0 * M)
K.boxr("Stucco", -BX, BX, BY1 - 0.3 * M, BY1, H, H + 1.0 * M)
TW = 4.6 * M
K.boxr("Stucco", -TW, TW, BY0 - 0.6 * M, BY0 + 3 * M, 4.1 * M, 9.5 * M)
K.boxr("Trim", -TW - 0.15 * M, TW + 0.15 * M, BY0 - 0.75 * M, BY0 + 3.15 * M, 9.5 * M, 9.8 * M)
K.quad("Roof", [(-TW - 0.4 * M, BY0 - 1.0 * M, 9.8 * M), (TW + 0.4 * M, BY0 - 1.0 * M, 9.8 * M), (0, BY0 + 1.2 * M, 11.6 * M)])
K.quad("Roof", [(TW + 0.4 * M, BY0 - 1.0 * M, 9.8 * M), (TW + 0.4 * M, BY0 + 3.4 * M, 9.8 * M), (0, BY0 + 1.2 * M, 11.6 * M)])
K.quad("Roof", [(TW + 0.4 * M, BY0 + 3.4 * M, 9.8 * M), (-TW - 0.4 * M, BY0 + 3.4 * M, 9.8 * M), (0, BY0 + 1.2 * M, 11.6 * M)])
K.quad("Roof", [(-TW - 0.4 * M, BY0 + 3.4 * M, 9.8 * M), (-TW - 0.4 * M, BY0 - 1.0 * M, 9.8 * M), (0, BY0 + 1.2 * M, 11.6 * M)])
panel_y("MallPylon", -TW + 0.3 * M, TW - 0.3 * M, BY0 - 0.62 * M, 6.0 * M, 8.9 * M, (0, 0.71, 1, 1))
for x in (-TW + 1.2 * M, TW - 1.2 * M):
    K.box("Sconce", (x, BY0 - 0.75 * M, 9.2 * M), (0.5 * M, 0.25 * M, 0.15 * M))

# ---------------------------------------------------------------- back + roof units
for i in range(NS):
    x = -BX + (i + 0.5) * SW
    K.boxr("Dark", x - 0.7 * M, x + 0.7 * M, BY1, BY1 + 0.06 * M, 0, 2.3 * M)
    K.box("Sconce", (x, BY1 + 0.12 * M, 2.7 * M), (0.25 * M, 0.2 * M, 0.2 * M))
    if i % 2 == 0:
        ax, ay = x + rng.uniform(-2, 2) * M, rng.uniform(12, 18) * M
        K.boxr("AcBody", ax - 1.0 * M, ax + 1.0 * M, ay - 0.7 * M, ay + 0.7 * M, H + 0.05 * M, H + 1.2 * M)
        K.cyl("Dark", (ax, ay, H + 1.22 * M), 0.5 * M, 0.04 * M, segs=14)
for x in (-20 * M, 6 * M):
    K.boxr("Dumpster", x, x + 3 * M, BY1 + 0.8 * M, BY1 + 2.6 * M, 0.15 * M, 1.4 * M)
    K.boxr("Dark", x - 0.05 * M, x + 3.05 * M, BY1 + 0.75 * M, BY1 + 2.65 * M, 1.4 * M, 1.48 * M)
for x in (-BX + 0.4 * M, 0, BX - 0.4 * M):
    K.downpipe(x, BY1 + 0.1 * M, 0, H + 0.6 * M)

# ---------------------------------------------------------------- pylon sign on the front strip
PX, PY = -16 * M, LY0 + 1.5 * M
for x in (PX - 2.2 * M, PX + 2.2 * M):
    K.boxr("Trim", x - 0.3 * M, x + 0.3 * M, PY - 0.3 * M, PY + 0.3 * M, 0, 7.6 * M)
K.boxr("Stucco", PX - 3.0 * M, PX + 3.0 * M, PY - 0.5 * M, PY + 0.5 * M, 0, 0.9 * M)
K.boxr("Dark", PX - 2.6 * M, PX + 2.6 * M, PY - 0.2 * M, PY + 0.2 * M, 2.4 * M, 7.6 * M)
panel_y("MallPylon", PX - 2.55 * M, PX + 2.55 * M, PY - 0.22 * M, 2.45 * M, 7.55 * M, (0, 0, 1, 1), back=PY + 0.22 * M)
K.boxr("Trim", PX - 2.8 * M, PX + 2.8 * M, PY - 0.35 * M, PY + 0.35 * M, 7.6 * M, 8.0 * M)

K.finish(face=A["face"])
meta = K.export()
s = 1 if A["face"] == "N" else -1
meta["driveways"] = [[a * s, b * s, A["face"]] for a, b in DRIVES]
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    s = -1 if A["face"] == "N" else 1
    K.shot("front", (-30 * M, s * 60 * M, 18 * M), (0, 0, 2 * M), lens=26)
    K.shot("street", (6 * M, s * 4 * M, 1.7 * M), (-8 * M, s * -8 * M, 2.6 * M), lens=24)
    K.shot("back", (40 * M, -s * 50 * M, 20 * M), (0, 0, 2 * M), lens=28)
