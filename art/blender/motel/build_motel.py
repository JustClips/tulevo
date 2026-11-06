"""Palmview Motel for the tulevo city (original name and design): a classic two-floor LA motel.

  blender --background --python build_motel.py -- [OUT_DIR] [--no-render] [--samples N] [--res F]

L-shaped room wings round a parking court: rooms open onto an outside walkway (upper walkway
with white railings on posts, steel stairs at the ends), shingle mansard band on top, room
number plates, wall A/C units and porch lights. Office with a glass front at the street
corner, a tall neon pylon sign, a fenced pool with loungers and an umbrella, ice + soda
machines, palms, planters, wheel stops and two lot lights.
Textures: tools/motel_textures.py -> tex/. Built in studs, -Y = street side.
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args  # noqa: E402

A = args(r"C:\out\motel")
K = Kit("Motel", A["out"], os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex"))
rng = random.Random(3)

BAY, FH, RD, WK = 4.0 * M, 3.2 * M, 7.2 * M, 1.8 * M
TOP = 2 * FH + 1.5 * M                      # parapet top
LOT_W, LOT_D = 56 * M, 44 * M

# ---------------------------------------------------------------- materials
for name, sheet, tile, explicit in (("Stucco", "Stucco", (2 * M, 2 * M), False), ("Asphalt", "Asphalt", (8 * M, 8 * M), False),
                                    ("Concrete", "Concrete", (3 * M, 3 * M), False), ("PoolWater", "PoolWater", (3 * M, 3 * M), False)):
    K.mat(name, sheet=sheet, tile=tile, explicit=explicit)
for name in ("RoomFront", "RoomNumbers", "BackWall", "RoofTile", "MotelSign", "OfficeGlass", "OfficeSign", "IceSign", "Soda",
             "IceMachine", "AcUnit"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (
        ("Roof", (0.33, 0.33, 0.32), 0.95, 0, 0), ("Rail", (0.93, 0.93, 0.90), 0.4, 0.3, 0), ("Post", (0.95, 0.93, 0.88), 0.7, 0, 0),
        ("Steel", (0.08, 0.36, 0.37), 0.45, 0.5, 0), ("Trim", (0.85, 0.40, 0.32), 0.6, 0, 0), ("SignBox", (0.10, 0.50, 0.50), 0.5, 0.2, 0),
        ("SignPole", (0.45, 0.46, 0.47), 0.4, 0.9, 0), ("Paint", (0.92, 0.92, 0.88), 0.7, 0, 0), ("WheelStop", (0.75, 0.74, 0.70), 0.9, 0, 0),
        ("Coping", (0.94, 0.93, 0.90), 0.6, 0, 0), ("Lounger", (0.96, 0.96, 0.95), 0.5, 0, 0), ("Canvas", (0.85, 0.36, 0.30), 0.8, 0, 0),
        ("Units", (0.62, 0.63, 0.63), 0.5, 0.6, 0), ("AcBody", (0.80, 0.79, 0.75), 0.6, 0.2, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.2, 0),
        ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("NeonPink", (1.0, 0.25, 0.65), 0.5, 0, 6.0), ("NeonCyan", (0.2, 0.95, 1.0), 0.5, 0, 6.0),
        ("Shrub", (0.12, 0.30, 0.10), 0.85, 0, 0), ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
        ("Soil", (0.18, 0.12, 0.08), 1.0, 0, 0), ("Kerb", (0.62, 0.62, 0.60), 0.9, 0, 0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)

# ---------------------------------------------------------------- lot
K.boxr("Asphalt", -LOT_W / 2, LOT_W / 2, -LOT_D / 2, LOT_D / 2, -0.3, 0.0)

# ---------------------------------------------------------------- room wings
MX0, MX1 = -18.8 * M, 13.2 * M              # main wing bays (8), rooms face -Y
MY0, MY1 = 13.8 * M, 21.0 * M               # main room block front / back
SY0, SY1 = -10.2 * M, 13.8 * M              # side wing bays (6), rooms face +X
SX0, SX1 = -26.0 * M, -18.8 * M             # side room block back / front
RZ = TOP - 0.6 * M                         # flat roof deck inside the parapet
K.boxr("Stucco", -26.0 * M, MX1, MY0, MY1, 0, RZ)
K.boxr("Stucco", SX0, SX1, SY0, SY1, 0, RZ)
K.boxr("Roof", -26.0 * M + 0.3, MX1 - 0.3, MY0 + 0.3, MY1 - 0.3, RZ, RZ + 0.1)
K.boxr("Roof", SX0 + 0.3, SX1 - 0.3, SY0 + 0.3, SY1 - 0.3, RZ, RZ + 0.1)
for (x0, x1, y0, y1) in ((-26.0 * M, MX1, MY1 - 0.3 * M, MY1), (MX1 - 0.3 * M, MX1, MY0, MY1), (SX0, SX0 + 0.3 * M, SY0, MY1),
                         (SX0, SX1, SY0, SY0 + 0.3 * M)):
    K.boxr("Stucco", x0, x1, y0, y1, RZ, TOP)                                # parapet (the mansard closes the front)
K.boxr("Stucco", SX1 - 0.3 * M, SX1, SY0, MY0, RZ, TOP)
K.boxr("Stucco", SX1, MX1, MY0, MY0 + 0.3 * M, RZ, TOP)
for (cx, cy) in ((-10 * M, 17.5 * M), (2 * M, 17 * M), (-22.5 * M, 2 * M)):
    K.box("Units", (cx, cy, TOP - 0.6 * M + 0.5 * M), (1.8 * M, 1.4 * M, 1.0 * M))
    K.cyl("Dark", (cx, cy, TOP - 0.6 * M + 1.02 * M), 0.5 * M, 0.04, segs=14)


def numbers_uv(floor, i):
    row, col = floor * 2 + i // 8, i % 8
    u0, vt = col / 8, 1 - row / 4
    return ((u0, vt - 0.25), (u0 + 0.125, vt - 0.25), (u0 + 0.125, vt), (u0, vt))


def room(face, floor, i, a0, ice=False):
    """One room bay. face 'main' (front at y=MY0, facing -Y, bay from x=a0) or 'side' (front at x=SX1, +X, bay from y=a0)."""
    z0 = floor * FH
    c = a0 + BAY / 2
    if face == "main":
        f = lambda part, u, z, w, h, dz=0.0, **kw: K.face_y(part, a0 + u * BAY, MY0 - 0.03 - dz, z0 + z, w, h, **kw)
        bx = lambda part, u, z, size, out: K.box(part, (a0 + u * BAY, MY0 - out / 2, z0 + z), (size[0], out, size[1]))
    else:
        f = lambda part, u, z, w, h, dz=0.0, **kw: K.face_x(part, SX1 + 0.03 + dz, a0 + u * BAY, z0 + z, w, h, **kw)
        bx = lambda part, u, z, size, out: K.box(part, (SX1 + out / 2, a0 + u * BAY, z0 + z), (out, size[0], size[1]))
    if ice:
        f("BackWall", 0.5, 0, BAY, FH)
        f("IceSign", 0.5, 2.3 * M, 2.4 * M, 0.6 * M)
        for u, part in ((0.3, "Soda"), (0.7, "IceMachine")):
            bx("Dark", u, 0.95 * M, (1.0 * M, 1.9 * M), 0.8 * M)
            f(part, u, 0.02 * M, 0.96 * M, 1.84 * M, dz=0.8 * M)
        return
    f("RoomFront", 0.5, 0, BAY, FH)
    n = numbers_uv(floor, room.counter[floor])
    room.counter[floor] += 1
    f("RoomNumbers", 0.42, 1.65 * M, 0.26 * M, 0.26 * M, dz=0.01, uvs=n)
    # porch light by the door, A/C unit under the window
    bx("Sconce", 0.06, 2.25 * M, (0.18 * M, 0.3 * M), 0.12 * M)
    bx("AcBody", 0.72, 0.62 * M, (1.0 * M, 0.42 * M), 0.3 * M)
    f("AcUnit", 0.72, 0.42 * M, 0.96 * M, 0.4 * M, dz=0.3 * M)


room.counter = [0, 0]
for floor in (0, 1):
    for k in range(6):
        room("side", floor, k, SY0 + k * BAY)
    for k in range(8):
        room("main", floor, k, MX0 + k * BAY, ice=(floor == 0 and k == 7))
# backs of the rooms
for floor in (0, 1):
    for k in range(10):
        K.face_y("BackWall", -26.0 * M + (k + 0.5) * BAY * 39.2 / 40, MY1 + 0.03, floor * FH, BAY * 39.2 / 40, FH, facing=1)
    for k in range(6):
        K.face_x("BackWall", SX0 - 0.03, SY0 + (k + 0.5) * BAY, floor * FH, BAY, FH, facing=-1)

# ---------------------------------------------------------------- walkways, posts, railings, roof overhang + mansard
WX = SX1 + WK        # side walkway outer edge (x)
WY = MY0 - WK        # main walkway outer edge (y)
K.boxr("Concrete", WX, MX1, WY, MY0, 0, 0.15 * M)                           # ground walkways
K.boxr("Concrete", SX1, WX, SY0, MY0, 0, 0.15 * M)
K.boxr("Concrete", WX, MX1, WY, MY0, FH - 0.25 * M, FH)                     # upper walkways
K.boxr("Concrete", SX1, WX, SY0, MY0, FH - 0.25 * M, FH)
K.boxr("Coping", WX, MX1, WY - 0.3 * M, MY0, 2 * FH, 2 * FH + 0.3 * M)       # roof overhang
K.boxr("Coping", SX1, WX + 0.3 * M, SY0, MY0, 2 * FH, 2 * FH + 0.3 * M)
zb, zt = 2 * FH + 0.3 * M, TOP


def slope_uv(length, slope):
    return ((0, 0), (length / (2 * M), 0), (length / (2 * M), slope / (1.2 * M)), (0, slope / (1.2 * M)))


sl = math.hypot(WK + 0.3 * M, zt - zb)
K.quad("RoofTile", [(WX, WY - 0.3 * M, zb), (MX1, WY - 0.3 * M, zb), (MX1, MY0, zt), (WX, MY0, zt)], slope_uv(MX1 - WX, sl))
K.quad("RoofTile", [(WX + 0.3 * M, SY0, zb), (WX + 0.3 * M, MY0, zb), (SX1, MY0, zt), (SX1, SY0, zt)], slope_uv(MY0 - SY0, sl))
bm = K.bm("Stucco")       # close the triangular ends of the mansard
for tri in (((MX1, WY - 0.3 * M, zb), (MX1, MY0, zb), (MX1, MY0, zt)), ((WX + 0.3 * M, SY0, zb), (SX1, SY0, zt), (SX1, SY0, zb))):
    bm.faces.new([bm.verts.new(p) for p in tri])
# posts at the walkway edge, every bay
for k in range(9):
    x = min(WX + k * BAY, MX1 - 0.15 * M)
    K.box("Post", (x, WY + 0.15 * M, FH), (0.3 * M, 0.3 * M, 2 * FH))
for k in range(7):
    y = SY0 + 0.15 * M + k * BAY
    K.box("Post", (WX - 0.15 * M, min(y, MY0 - 0.15 * M), FH), (0.3 * M, 0.3 * M, 2 * FH))


def railing(a, b, axis):
    """Upper walkway railing from a to b along 'x' (at y=WY) or 'y' (at x=WX)."""
    L = b - a
    for z in (FH + 1.0 * M, FH + 0.12 * M):
        if axis == 'x':
            K.box("Rail", ((a + b) / 2, WY + 0.05 * M, z), (L, 0.08 * M, 0.08 * M))
        else:
            K.box("Rail", (WX - 0.05 * M, (a + b) / 2, z), (0.08 * M, L, 0.08 * M))
    n = int(L / (0.16 * M))
    for i in range(1, n):
        t = a + i * L / n
        if axis == 'x':
            K.box("Rail", (t, WY + 0.05 * M, FH + 0.56 * M), (0.035 * M, 0.035 * M, 0.88 * M))
        else:
            K.box("Rail", (WX - 0.05 * M, t, FH + 0.56 * M), (0.035 * M, 0.035 * M, 0.88 * M))


railing(WX, MX1, 'x')
railing(SY0 + 1.7 * M, MY0 - WK, 'y')                 # opening at the south end for the stair
K.box("Rail", ((SX1 + WX) / 2, SY0 + 0.05 * M, FH + 1.0 * M), (WK, 0.08 * M, 0.08 * M))


def stair(x_top, y0, y1):
    """Steel stair down along +X from the walkway edge at x_top, between y0 and y1."""
    n, rise, run = 18, FH / 18, 0.28 * M
    for k in range(1, n):
        K.box("Steel", (x_top + (k - 0.5) * run, (y0 + y1) / 2, FH - k * rise), (run * 0.95, (y1 - y0) - 0.2 * M, 0.05 * M))
    for y in (y0 + 0.08 * M, y1 - 0.08 * M):
        K.cyl_along("Steel", (x_top, y, FH - 0.1 * M), (x_top + n * run, y, -0.05 * M), 0.1 * M, segs=4)
        K.cyl_along("Rail", (x_top, y, FH + 1.0 * M), (x_top + n * run, y, 1.0 * M), 0.04 * M, segs=6)
        K.box("Rail", (x_top + n * run, y, 0.5 * M), (0.06 * M, 0.06 * M, 1.0 * M))
        for k in range(1, 6):
            t = k / 6
            K.box("Rail", (x_top + t * n * run, y, FH * (1 - t) + 0.5 * M), (0.035 * M, 0.035 * M, 1.0 * M))


stair(MX1, WY, MY0)
stair(WX, SY0, SY0 + 1.7 * M)

# ---------------------------------------------------------------- parking: stalls, wheel stops, lot lights
for k in range(9):
    x = -10 * M + k * 2.7 * M
    K.box("Paint", (x, WY - 0.3 * M - 2.75 * M, 0.01), (0.12 * M, 5.5 * M, 0.02))
    if k < 8:
        K.box("WheelStop", (x + 1.35 * M, WY - 0.3 * M - 0.6 * M, 0.08 * M), (1.8 * M, 0.25 * M, 0.16 * M))
for k in range(7):
    y = -6 * M + k * 2.7 * M
    K.box("Paint", (WX + 0.3 * M + 2.75 * M, y, 0.01), (5.5 * M, 0.12 * M, 0.02))
    if k < 6:
        K.box("WheelStop", (WX + 0.3 * M + 0.6 * M, y + 1.35 * M, 0.08 * M), (0.25 * M, 1.8 * M, 0.16 * M))
for (lx, ly) in ((4 * M, -4 * M), (22 * M, 6 * M)):
    K.cyl("SignPole", (lx, ly, 0.6 * M + 4.0 * M), 0.12 * M, 8.0 * M, segs=10, r2=0.09 * M)
    K.cyl("Kerb", (lx, ly, 0.3 * M), 0.3 * M, 0.6 * M, segs=12)
    for d in (-1, 1):
        K.box("SignPole", (lx + d * 0.8 * M, ly, 8.5 * M), (1.6 * M, 0.12 * M, 0.12 * M))
        K.box("Dark", (lx + d * 1.7 * M, ly, 8.5 * M), (1.0 * M, 0.5 * M, 0.22 * M))
        K.lamp((lx + d * 1.7 * M, ly, 8.5 * M - 0.12 * M), (0.8 * M, 0.38 * M, 0.04))

# ---------------------------------------------------------------- office (street corner) with glass front + sign band
OX0, OX1, OY0, OY1, OH = 16 * M, 26 * M, -18 * M, -8 * M, 4.2 * M
K.boxr("Stucco", OX0, OX1, OY0 + 0.6 * M, OY1, 0, OH)
K.boxr("Stucco", OX0, OX0 + 0.8 * M, OY0, OY0 + 0.6 * M, 0, OH)
K.boxr("Stucco", OX1 - 0.8 * M, OX1, OY0, OY0 + 0.6 * M, 0, OH)
K.face_y("OfficeGlass", (OX0 + OX1) / 2, OY0 + 0.6 * M - 0.02, 0.0, OX1 - OX0 - 1.6 * M, 3.0 * M)
K.boxr("Trim", OX0 - 0.2 * M, OX1 + 0.2 * M, OY0 - 1.6 * M, OY0 + 0.6 * M, 3.1 * M, OH + 0.2 * M)     # sign band + porch roof
K.face_y("OfficeSign", (OX0 + OX1) / 2, OY0 - 1.6 * M - 0.03, 3.15 * M, OX1 - OX0, OH - 3.1 * M)
for sx in (OX0 + 0.3 * M, OX1 - 0.3 * M):
    K.box("Post", (sx, OY0 - 1.3 * M, 1.55 * M), (0.3 * M, 0.3 * M, 3.1 * M))
K.lamp(((OX0 + OX1) / 2, OY0 - 0.6 * M, 3.1 * M - 0.03), (3.0 * M, 0.5 * M, 0.04))
K.boxr("Roof", OX0 + 0.2, OX1 - 0.2, OY0 + 0.8, OY1 - 0.2, OH - 0.1, OH + 0.05)
K.boxr("Concrete", OX0 - 0.2 * M, OX1 + 0.2 * M, OY0 - 1.6 * M, OY0, 0, 0.15 * M)
K.box("Units", ((OX0 + OX1) / 2, (OY0 + OY1) / 2 + 1 * M, OH + 0.5 * M), (1.6 * M, 1.4 * M, 1.0 * M))

# ---------------------------------------------------------------- neon pylon sign
PX, PY = -9 * M, -20.4 * M
sw, sh, ph = 3.6 * M, 7.2 * M, 11.0 * M
z0 = ph - sh
for sx in (-1, 1):
    K.box("SignPole", (PX + sx * 1.1 * M, PY, z0 / 2), (0.35 * M, 0.35 * M, z0))
K.box("SignBox", (PX, PY, z0 + sh / 2), (sw + 0.5 * M, 0.6 * M, sh + 0.5 * M))
for face in (-1, 1):
    y = PY + face * (0.3 * M + 0.03)
    K.face_y("MotelSign", PX, y, z0, sw, sh, facing=face)
    yn = PY + face * (0.3 * M + 0.12 * M)
    for (cx, cz, w, h) in ((PX, z0 + sh + 0.12 * M, sw + 0.4 * M, 0.1 * M), (PX, z0 - 0.12 * M, sw + 0.4 * M, 0.1 * M),
                           (PX - sw / 2 - 0.15 * M, z0 + sh / 2, 0.1 * M, sh + 0.3 * M), (PX + sw / 2 + 0.15 * M, z0 + sh / 2, 0.1 * M, sh + 0.3 * M)):
        K.box("NeonPink", (cx, yn, cz), (w, 0.1 * M, h))
# neon arrow on top pointing down at the office side
for k in range(6):
    K.box("NeonCyan", (PX - sw / 2 + k * 0.75 * M, PY, ph + 0.6 * M + (0.25 * M if k % 2 else 0)), (0.5 * M, 0.25 * M, 0.12 * M))
K.box("SignBox", (PX, PY, ph + 0.35 * M), (sw + 0.6 * M, 0.4 * M, 0.2 * M))
K.cyl("Kerb", (PX, PY, 0.25 * M), 1.6 * M, 0.5 * M, segs=16)

# ---------------------------------------------------------------- pool
DX0, DX1, DY0, DY1 = -27 * M, -13 * M, -21.2 * M, -11.8 * M
K.boxr("Concrete", DX0, DX1, DY0, DY1, 0, 0.15 * M)
PX0, PX1, PY0, PY1 = -24.5 * M, -15.5 * M, -19.2 * M, -14 * M
K.boxr("PoolWater", PX0, PX1, PY0, PY1, 0.15 * M, 0.2 * M)
for (x0, x1, y0, y1) in ((PX0 - 0.4 * M, PX1 + 0.4 * M, PY0 - 0.4 * M, PY0), (PX0 - 0.4 * M, PX1 + 0.4 * M, PY1, PY1 + 0.4 * M),
                         (PX0 - 0.4 * M, PX0, PY0, PY1), (PX1, PX1 + 0.4 * M, PY0, PY1)):
    K.boxr("Coping", x0, x1, y0, y1, 0.15 * M, 0.3 * M)
for k in range(2):  # ladder rails
    for s in (-1, 1):
        x = PX1 - 1.0 * M + s * 0.3 * M
        K.cyl_along("Rail", (x, PY1 - 0.2 * M, 0.2 * M), (x, PY1 + 0.15 * M, 1.2 * M), 0.04 * M, segs=6)
for k in range(4):
    lx = PX0 + 1.0 * M + k * 1.6 * M
    K.box("Lounger", (lx, DY0 + 1.1 * M, 0.45 * M), (0.7 * M, 1.6 * M, 0.12 * M))
    K.box("Lounger", (lx, DY0 + 0.45 * M, 0.75 * M), (0.7 * M, 0.12 * M, 0.6 * M))
    for sx in (-1, 1):
        for sy in (0.4, 1.8):
            K.box("Lounger", (lx + sx * 0.3 * M, DY0 + sy * M, 0.2 * M), (0.06 * M, 0.06 * M, 0.4 * M))
UX, UY = PX1 + 1.2 * M, DY1 - 1.4 * M
K.cyl("Rail", (UX, UY, 1.4 * M), 0.04 * M, 2.8 * M, segs=6)
K.cyl("Canvas", (UX, UY, 2.6 * M), 1.4 * M, 0.5 * M, segs=12, r2=0.05 * M)
K.cyl("Lounger", (UX, UY, 0.75 * M), 0.5 * M, 0.06 * M, segs=12)
# fence round the deck (open gate toward the rooms)
fence = [((DX0, DY0), (DX1, DY0)), ((DX1, DY0), (DX1, DY1 - 1.5 * M)), ((DX0, DY1), (DX1 - 2.5 * M, DY1)), ((DX0, DY0), (DX0, DY1))]
for (ax_, ay_), (bx_, by_) in fence:
    L = math.hypot(bx_ - ax_, by_ - ay_)
    cx, cy = (ax_ + bx_) / 2, (ay_ + by_) / 2
    along_x = abs(bx_ - ax_) > abs(by_ - ay_)
    for z in (1.2 * M, 0.25 * M):
        K.box("Rail", (cx, cy, z), (L, 0.05 * M, 0.05 * M) if along_x else (0.05 * M, L, 0.05 * M))
    n = int(L / (0.3 * M))
    for i in range(n + 1):
        t = i / n
        K.box("Rail", (ax_ + (bx_ - ax_) * t, ay_ + (by_ - ay_) * t, 0.65 * M), (0.03 * M, 0.03 * M, 1.1 * M))

# ---------------------------------------------------------------- planters, shrubs, palms
def planter(x0, x1, y0, y1):
    K.boxr("Soil", x0, x1, y0, y1, 0.15 * M, 0.25 * M)
    for (a, b, c, d) in ((x0, x1, y0 - 0.15, y0 + 0.15), (x0, x1, y1 - 0.15, y1 + 0.15), (x0 - 0.15, x0 + 0.15, y0, y1), (x1 - 0.15, x1 + 0.15, y0, y1)):
        K.boxr("Kerb", a, b, c, d, 0, 0.3 * M)


planter(OX0, OX1, -21.4 * M, -20.0 * M)
planter(OX1 + 0.3 * M, LOT_W / 2 - 0.3 * M, -21.4 * M, -2 * M)
planter(-6.5 * M, -2 * M, -21.4 * M, -19.8 * M)
for k in range(8):
    K.shrub(OX0 + 0.8 * M + k * 1.25 * M, -20.7 * M, 0.25 * M, rng.uniform(0.45, 0.6) * M, rng)
for k in range(5):
    K.shrub(OX1 + 1.0 * M, -19.5 * M + k * 3.5 * M, 0.25 * M, rng.uniform(0.55, 0.75) * M, rng)
for k in range(3):
    K.shrub(-5.8 * M + k * 1.6 * M, -20.6 * M, 0.25 * M, 0.5 * M, rng)
K.palm(OX1 + 1.0 * M, -17.5 * M, 0.25 * M, 11.5 * M, (-0.5, 0.3), rng)
K.palm(OX1 + 1.0 * M, -6.0 * M, 0.25 * M, 10.0 * M, (-0.6, -0.2), rng)
K.palm(-4.2 * M, -20.6 * M, 0.25 * M, 12.5 * M, (0.4, 0.2), rng)
K.palm(DX0 + 0.5 * M, DY1 - 0.6 * M, 0.15 * M, 10.5 * M, (0.3, 0.5), rng)

# ---------------------------------------------------------------- finish
K.finish()
K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("01_street", (40 * M, -62 * M, 9 * M), (-2 * M, 2 * M, 4 * M), lens=24)
    K.shot("02_court", (8 * M, -12 * M, 2.2 * M), (-10 * M, 14 * M, 3.5 * M), lens=20)
    K.shot("03_sign", (2 * M, -40 * M, 3 * M), (-9 * M, -20 * M, 8 * M), lens=24)
    K.shot("06_office", (14 * M, -32 * M, 2.5 * M), (21 * M, -16 * M, 2.5 * M), lens=24)
    K.shot("04_aerial", (45 * M, -55 * M, 40 * M), (-2 * M, 0, 0), lens=30)
    K.shot("05_pool", (-11 * M, -24 * M, 4 * M), (-20 * M, -15 * M, 0.5 * M), lens=24)
    print("done")
