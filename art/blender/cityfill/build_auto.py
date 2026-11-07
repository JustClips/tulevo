"""Delgado Auto Repair: a three-bay garage with a small office and a front apron (original
design, thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py auto
  blender --background --python build_auto.py -- OUT_DIR [--face S] [--no-render] [--samples N] [--res F]

Corrugated-steel garage: two bays open (roll-up doors up in their drums, lit work bays inside
with a two-post lift, tool chests, tyre rack), one bay shut. Sign board on the parapet, brick
office with a waiting-room window and a fascia sign, pole sign by the street, stalls, tyre
stacks, back yard with a dumpster and a fence.

Lot 40 x 28 m, origin = lot centre, z 0 = lot surface; place at y 0.3.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\auto")
NAME = model_name("AutoShop", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(3)

LX, LY0, LY1 = 20 * M, -14 * M, 14 * M
GX0, GX1, GY0, GY1, GH = -19 * M, 7 * M, -1 * M, 13 * M, 6 * M
WT = 0.3 * M
BAYS = [(-17.5 * M, -12.5 * M, True), (-11 * M, -6 * M, True), (-4.5 * M, 0.5 * M, False)]
DH = 4.6 * M
DRIVE = (GX0, GX1)

for name, sheet, tile in (("Metal", "GarageMetal", (2 * M, 2 * M)), ("RollDoor", "RollDoor", (2 * M, 2 * M)),
                          ("Brick", "KitchenBrick", (1.6 * M, 1.6 * M)), ("Roof", "RoofTar", (4 * M, 4 * M)),
                          ("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Trim", "MallTrim", (1 * M, 1 * M)), ("Steel", "FireSteel", (1 * M, 1 * M)),
                          ("Chest", "HydrantRed", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("AutoSigns", "StorefrontsD"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Dark", (0.05, 0.05, 0.055), 0.5, 0.3, 0), ("Tyre", (0.03, 0.03, 0.03), 0.9, 0, 0),
                                      ("Lift", (0.85, 0.65, 0.10), 0.5, 0.4, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Dumpster", (0.12, 0.30, 0.18), 0.6, 0.4, 0), ("Frame", (0.12, 0.12, 0.13), 0.4, 0.6, 0),
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


def tyre(x, y, z, axis="Z"):
    K.cyl("Tyre", (x, y, z), 0.34 * M, 0.22 * M, segs=12, axis=axis)


# ---------------------------------------------------------------- lot
K.boxr("Asphalt", -LX, LX, LY0, LY1, -0.5 * M, 0)
K.boxr("Pave", GX1, LX, LY0, LY0 + 0.3 * M, 0, 0.15 * M)                                 # kerb beside the drive
for sx in (-1, 1):
    a, b = sorted((sx * LX, sx * (LX - 0.3 * M)))
    K.boxr("Pave", a, b, LY0, LY1, 0, 0.15 * M)
for i in range(5):                                                                     # stalls in front of the office
    x = 8 * M + i * 2.7 * M
    K.boxr("LotLine", x - 0.06 * M, x + 0.06 * M, -7 * M, -1.5 * M, 0, 0.012 * M)
for i in range(4):
    x = 8 * M + (i + 0.5) * 2.7 * M
    K.boxr("Pave", x - 0.9 * M, x + 0.9 * M, -2.4 * M, -2.15 * M, 0, 0.14 * M)
for (x, y, n) in ((-18 * M, -10 * M, 5), (-16.9 * M, -10 * M, 4), (18.5 * M, -11 * M, 6)):      # tyre stacks
    for k in range(n):
        tyre(x, y, 0.11 * M + k * 0.23 * M)

# ---------------------------------------------------------------- garage
K.boxr("Pave", GX0, GX1, GY0, GY1, -0.3 * M, 0.08 * M)                                    # shop floor
K.boxr("Metal", GX0, GX1, GY1 - WT, GY1, 0, GH)                                          # back
K.boxr("Metal", GX0, GX0 + WT, GY0, GY1 - WT, 0, GH)                                     # sides
K.boxr("Metal", GX1 - WT, GX1, GY0, GY1 - WT, 0, GH)
xs = [GX0 + WT] + [v for b in BAYS for v in b[:2]] + [GX1 - WT]
for i in range(0, len(xs), 2):                                                         # front piers between the bays
    K.boxr("Metal", xs[i], xs[i + 1], GY0, GY0 + WT, 0, GH)
K.boxr("Metal", GX0 + WT, GX1 - WT, GY0, GY0 + WT, DH, GH)                               # over the doors
K.boxr("Roof", GX0, GX1, GY0, GY1, GH, GH + 0.25 * M)
K.boxr("Trim", GX0 - 0.05 * M, GX1 + 0.05 * M, GY0 - 0.12 * M, GY0 + 0.1 * M, GH, GH + 0.5 * M)
for (x0, x1, open_) in BAYS:
    K.boxr("Trim", x0 - 0.12 * M, x0, GY0 - 0.1 * M, GY0 + 0.05 * M, 0, DH)            # door jambs
    K.boxr("Trim", x1, x1 + 0.12 * M, GY0 - 0.1 * M, GY0 + 0.05 * M, 0, DH)
    K.boxr("Trim", x0 - 0.12 * M, x1 + 0.12 * M, GY0 - 0.1 * M, GY0 + 0.05 * M, DH, DH + 0.15 * M)
    if open_:
        K.cyl_along("RollDoor", (x0 + 0.05 * M, GY0 + 0.5 * M, DH - 0.35 * M), (x1 - 0.05 * M, GY0 + 0.5 * M, DH - 0.35 * M), 0.32 * M, segs=12)
        cx = (x0 + x1) / 2
        for sx in (-1, 1):                                                              # two-post lift
            K.boxr("Lift", cx + sx * 1.9 * M - 0.18 * M, cx + sx * 1.9 * M + 0.18 * M, 5.5 * M, 5.9 * M, 0.08 * M, 3.8 * M)
            K.boxr("Lift", cx + sx * 1.9 * M - 0.35 * M, cx + sx * 1.9 * M + 0.35 * M, 5.4 * M, 6.0 * M, 0.08 * M, 0.2 * M)
            for dy in (-1, 1):
                K.boxr("Lift", min(cx + sx * 1.9 * M, cx + sx * 0.6 * M), max(cx + sx * 1.9 * M, cx + sx * 0.6 * M),
                       5.7 * M + dy * 0.9 * M - 0.08 * M, 5.7 * M + dy * 0.9 * M + 0.08 * M, 0.6 * M, 0.7 * M)
        K.boxr("Lift", cx - 1.9 * M, cx + 1.9 * M, 5.55 * M, 5.85 * M, 3.8 * M, 3.95 * M)
        K.boxr("Chest", x1 - 1.4 * M, x1 - 0.3 * M, GY1 - 1.0 * M, GY1 - WT - 0.02 * M, 0.08 * M, 1.2 * M)   # tool chest
        for k in range(4):
            K.boxr("Steel", x1 - 1.38 * M, x1 - 0.32 * M, GY1 - 1.02 * M, GY1 - 1.0 * M, 0.25 * M + k * 0.25 * M, 0.28 * M + k * 0.25 * M)
        K.lamp((cx, 4 * M, GH - 0.05 * M), (0.5 * M, 3.0 * M, 0.06 * M))
    else:
        K.boxr("RollDoor", x0, x1, GY0 + 0.1 * M, GY0 + 0.16 * M, 0.08 * M, DH)
        K.boxr("Steel", x0, x1, GY0 + 0.04 * M, GY0 + 0.1 * M, 0.08 * M, 0.25 * M)
for k in range(6):                                                                     # tyre rack on the west wall
    tyre(GX0 + WT + 0.4 * M, 2 * M + k * 1.6 * M, 1.6 * M, axis="X")
    tyre(GX0 + WT + 0.4 * M, 2.8 * M + k * 1.6 * M, 3.1 * M, axis="X")
K.boxr("Steel", GX0 + WT, GX0 + WT + 0.8 * M, 1.5 * M, 11.8 * M, 1.2 * M, 1.26 * M)
K.boxr("Steel", GX0 + WT, GX0 + WT + 0.8 * M, 1.5 * M, 11.8 * M, 2.7 * M, 2.76 * M)
# sign board on the parapet
K.boxr("Steel", -12.2 * M, -1.8 * M, GY0 + 0.2 * M, GY0 + 0.35 * M, GH + 0.5 * M, GH + 3.2 * M)
panel_y("AutoSigns", -12.1 * M, -1.9 * M, GY0 + 0.18 * M, GH + 0.6 * M, GH + 3.1 * M, (0, 0.502, 1, 1))
for x in (-11 * M, -3 * M):
    K.cyl_along("Steel", (x, GY0 + 0.3 * M, GH + 2.5 * M), (x, GY0 + 2.5 * M, GH + 0.25 * M), 0.05 * M, segs=6)
for x in (-10 * M, -7 * M, -4 * M):
    K.cyl_along("Steel", (x, GY0 + 0.15 * M, GH + 3.3 * M), (x, GY0 - 0.6 * M, GH + 3.6 * M), 0.03 * M, segs=6)
    K.box("Sconce", (x, GY0 - 0.7 * M, GH + 3.5 * M), (0.3 * M, 0.25 * M, 0.08 * M))

# ---------------------------------------------------------------- office
OX0, OX1, OY0, OY1, OH = GX1, 18.5 * M, 3 * M, 13 * M, 4.6 * M
K.boxr("Brick", OX0, OX1, OY0 + 0.3 * M, OY1, -0.3 * M, OH)
K.boxr("Brick", OX0, OX0 + 0.5 * M, OY0, OY0 + 0.3 * M, -0.3 * M, OH)
K.boxr("Brick", OX1 - 0.5 * M, OX1, OY0, OY0 + 0.3 * M, -0.3 * M, OH)
gy = OY0 + 0.28 * M
panel_y("StorefrontsD", OX0 + 0.5 * M, OX1 - 0.5 * M, gy, 0.3 * M, 3.0 * M, (0.5, 0.5, 1.0, 1.0))
for fx in (OX0 + 0.55 * M, OX1 - 0.55 * M, OX1 - 0.5 * M - (OX1 - OX0 - 1 * M) * 0.22):
    K.boxr("Frame", fx - 0.05 * M, fx + 0.05 * M, gy - 0.08 * M, gy + 0.01 * M, 0.3 * M, 3.05 * M)
for z in (0.25 * M, 3.0 * M):
    K.boxr("Frame", OX0 + 0.5 * M, OX1 - 0.5 * M, gy - 0.08 * M, gy + 0.01 * M, z, z + 0.08 * M)
K.boxr("Brick", OX0 + 0.5 * M, OX1 - 0.5 * M, OY0 + 0.1 * M, gy - 0.08 * M, 3.1 * M, OH)
K.boxr("Trim", OX0 - 0.05 * M, OX1 + 0.05 * M, OY0 - 0.05 * M, OY0 + 0.1 * M, 3.15 * M, 4.45 * M)
panel_y("AutoSigns", OX0 + 0.6 * M, OX1 - 0.6 * M, OY0 - 0.07 * M, 3.2 * M, 4.4 * M, (0, 0, 1, 0.498))
K.boxr("Roof", OX0, OX1, OY0, OY1, OH, OH + 0.2 * M)
K.boxr("Trim", OX0 - 0.05 * M, OX1 + 0.05 * M, OY0 - 0.1 * M, OY1 + 0.05 * M, OH + 0.2 * M, OH + 0.45 * M)
K.boxr("Pave", OX0, OX1 + 1 * M, -1 * M, OY0, 0, 0.15 * M)                              # walk in front of the office

# ---------------------------------------------------------------- pole sign + back yard
PX, PY = 16 * M, LY0 + 1.2 * M
K.cyl("Steel", (PX, PY, 4 * M), 0.2 * M, 8 * M, segs=12)
K.cyl("Pave", (PX, PY, 0.3 * M), 0.45 * M, 0.6 * M, segs=12)
K.boxr("Dark", PX - 2.6 * M, PX + 2.6 * M, PY - 0.18 * M, PY + 0.18 * M, 5.4 * M, 8 * M)
panel_y("AutoSigns", PX - 2.55 * M, PX + 2.55 * M, PY - 0.2 * M, 5.45 * M, 7.95 * M, (0, 0.502, 1, 1), back=PY + 0.2 * M)
K.boxr("Steel", -LX + 0.3 * M, LX - 0.3 * M, LY1 - 0.3 * M, LY1 - 0.2 * M, 0, 1.8 * M)   # back fence panel
for i in range(14):
    x = -LX + 0.5 * M + i * (2 * LX - 1 * M) / 13
    K.boxr("Steel", x - 0.05 * M, x + 0.05 * M, LY1 - 0.35 * M, LY1 - 0.15 * M, 0, 1.9 * M)
K.downpipe(GX1 - 0.4 * M, GY1 + 0.1 * M, 0, GH + 0.2 * M)

K.finish(face=A["face"])
meta = K.export()
s = 1 if A["face"] == "N" else -1
meta["driveways"] = [[DRIVE[0] * s, DRIVE[1] * s, A["face"]]]
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    s = -1 if A["face"] == "N" else 1
    K.shot("front", (-14 * M, s * 34 * M, 8 * M), (0, 0, 3 * M), lens=26)
    K.shot("bay", (-6 * M, s * 9 * M, 1.7 * M), (-10 * M, 0, 2.2 * M), lens=24)
