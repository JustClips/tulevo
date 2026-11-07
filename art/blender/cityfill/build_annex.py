"""Palmview Motel annex: a second room wing on the strip between the motel's back wall and the
Back Street sidewalk (thread "Fill city with buildings and street props", 2026-11-07, Dev: "expand
motel so it takes this entire area"). The Palmview Motel model itself belongs to another thread, so
this is its own model in the motel's look (the motel's stucco, room fronts, mansard tiles).

  blender --background --python build_annex.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin, like the Park). Two floors of rooms facing Back
Street off a ground walkway and an upper walkway with a stucco balustrade under a tiled mansard,
stair at the west end, office + ice/soda alcove at the West Street end.
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(4)
K = Kit("MotelAnnex", os.path.join(A["out"], "MotelAnnex"), BS.TEX)
MOTEL_TEX = os.path.join(HERE, "..", "motel", "tex")

# the motel's own sheets (same images, so they share the motel's uploaded textures)
K.texdir = MOTEL_TEX
for name, tile in (("Stucco", (3.5 * M, 3.5 * M)), ("Concrete", (3 * M, 3 * M))):
    K.mat(name, sheet=name, tile=tile)
for name in ("RoomFront", "BackWall", "RoofTile", "OfficeGlass", "OfficeSign", "IceSign", "Soda", "IceMachine", "AcUnit"):
    K.mat(name, sheet=name, explicit=True)
K.facade_mats()
K.texdir = BS.TEX
for name, col, rough, metal, emit in (
        ("Roof", (0.33, 0.33, 0.32), 0.95, 0, 0), ("Post", (0.95, 0.93, 0.88), 0.7, 0, 0), ("Trim", (0.85, 0.40, 0.32), 0.6, 0, 0),
        ("Coping", (0.94, 0.93, 0.90), 0.6, 0, 0), ("Units", (0.62, 0.63, 0.63), 0.5, 0.6, 0), ("AcBody", (0.80, 0.79, 0.75), 0.6, 0.2, 0),
        ("Dark", (0.06, 0.06, 0.07), 0.5, 0.2, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
        ("Steel", (0.08, 0.36, 0.37), 0.45, 0.5, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    """Roblox x/z ranges (studs), h above the lot surface."""
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


BAY, FH = 4.0 * M, 3.2 * M
TOP = 2 * FH + 1.5 * M
RZ = TOP - 0.6 * M
XW = -367.0                         # west end of the block (LotParking's kerb ends at -369.5)
XE = XW + 14 * BAY                  # -165.4 (West St sidewalk starts at -160)
ZB, FZ, WZ = 70.0, 85.6, 91.4       # back wall, room fronts, walkway edge (sidewalk line z 92)
XS = XW + 2 * BAY                   # stair top: upper walkway runs XS..XE


def bay_left(k):
    """Blender x of the viewer's left edge of bay k (seen from Back St, i.e. from +y)."""
    return -(XW + k * BAY)


# ---------------------------------------------------------------- slab, block, roof, parapets, stripes
B("Concrete", -369.3, -160.4, 67.3, 92.0, -1.2, 0)
B("Stucco", XW, XE, ZB, FZ, 0, RZ)
B("Roof", XW + 0.3, XE - 0.3, ZB + 0.3, FZ - 0.3, RZ, RZ + 0.1)
for (x0, x1, z0, z1) in ((XW, XE, ZB, ZB + 0.3 * M), (XW, XW + 0.3 * M, ZB, FZ), (XE - 0.3 * M, XE, ZB, FZ), (XW, XE, FZ - 0.3 * M, FZ)):
    B("Stucco", x0, x1, z0, z1, RZ, TOP)
for i, (x0, x1, z0, z1) in enumerate(((XW, XE, ZB - 0.12 * M, ZB), (XW - 0.12 * M, XW, ZB - 0.12 * M, FZ),
                                      (XE, XE + 0.12 * M, ZB - 0.12 * M, FZ))):
    e = 0.06 * i                     # the end pieces sit a hair higher, so no top faces meet at the corners
    B("Concrete", x0 - 0.02, x1 + 0.02, z0 - 0.02, z1 + 0.02, 0, 0.45 * M + e)                         # plinth
    B("Coping", x0 - 0.04, x1 + 0.04, z0 - 0.04, z1 + 0.04, FH - 0.08 * M - e, FH + 0.08 * M + e)     # floor band
    B("Trim", x0 - 0.03, x1 + 0.03, z0 - 0.03, z1 + 0.03, TOP - 0.95 * M - e, TOP - 0.7 * M + e)      # coral stripe
    B("Coping", x0 - 0.05, x1 + 0.05, z0 - 0.05, z1 + 0.05, TOP - 0.08 * M - e, TOP + 0.04 * M + e)   # cap
for k in range(4):
    cx = XW + (1.5 + k * 3.6) * BAY
    K.box("Units", (-cx, (ZB + FZ) / 2, Y0 + RZ + 0.5 * M), (1.8 * M, 1.4 * M, 1.0 * M))
    K.cyl("Dark", (-cx, (ZB + FZ) / 2, Y0 + RZ + 1.02 * M), 0.5 * M, 0.04, segs=14)

# ---------------------------------------------------------------- walkways, posts, balustrade, mansard
B("Concrete", XS, XE, FZ, WZ, 0, 0.15 * M)                        # ground walkway
B("Concrete", XS, XE, FZ, WZ, FH - 0.25 * M, FH)                  # upper walkway
B("Stucco", XS + 0.3 * M, XE, WZ - 0.9, WZ - 0.08, FH, FH + 1.0 * M)          # solid balustrade (no thin rails)
B("Coping", XS + 0.3 * M - 0.06, XE + 0.06, WZ - 1.0, WZ + 0.12, FH + 1.0 * M, FH + 1.0 * M + 0.25)
B("Coping", XW - 0.06, XE + 0.06, FZ, WZ + 0.3 * M, 2 * FH, 2 * FH + 0.3 * M)  # roof overhang
zb, zt = Y0 + 2 * FH + 0.3 * M, Y0 + TOP
sl = ((WZ + 0.3 * M - FZ) ** 2 + (zt - zb) ** 2) ** 0.5
L = XE - XW
K.quad("RoofTile", [(-XW, WZ + 0.3 * M, zb), (-XE, WZ + 0.3 * M, zb), (-XE, FZ, zt), (-XW, FZ, zt)],
       ((0, 0), (L / (2 * M), 0), (L / (2 * M), sl / (1.2 * M)), (0, sl / (1.2 * M))))
bm = K.bm("Stucco")                                               # close the mansard's ends
for tri in (((-XW, WZ + 0.3 * M, zb), (-XW, FZ, zt), (-XW, FZ, zb)), ((-XE, WZ + 0.3 * M, zb), (-XE, FZ, zb), (-XE, FZ, zt))):
    bm.faces.new([bm.verts.new(p) for p in tri])
for k in range(13):
    x = XS + 0.54 + k * (XE - XS - 1.08) / 12
    B("Post", x - 0.54, x + 0.54, WZ - 1.08, WZ + 0.06, 0, 2 * FH)
B("Post", XW + 0.04, XW + 1.12, WZ - 1.08, WZ + 0.06, 0, 2 * FH)         # west corner post, standing on the stair landing

# ---------------------------------------------------------------- stair (west end, rising east to the upper walkway)
n = 18
run, rise = (XS - XW - 1.2) / n, FH / n
for k in range(n):
    B("Concrete", XW + 1.2 + k * run, XW + 1.2 + (k + 1) * run + (0.02 if k < n - 1 else 0), FZ + 1.0, WZ - 0.1, 0,
      (k + 1) * rise)
# stair side wall toward the street (a stucco wedge) with a coping on its slope
bm = K.bm("Stucco")
x0b, x1b = -(XW + 1.2), -XS
zf, zk = WZ - 0.1, WZ + 0.4
pts = [(x0b, zf, Y0), (x1b, zf, Y0), (x1b, zf, Y0 + FH + 1.0 * M), (x0b, zf, Y0 + 1.0 * M),
       (x0b, zk, Y0), (x1b, zk, Y0), (x1b, zk, Y0 + FH + 1.0 * M), (x0b, zk, Y0 + 1.0 * M)]
v = [bm.verts.new(p) for p in pts]
for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
    bm.faces.new([v[i] for i in f])
# stair landing: the ground walkway runs on under the stair's west end to the parking lot
B("Concrete", XW - 2.2, XW + 1.2, FZ, WZ, 0, 0.15 * M)

# ---------------------------------------------------------------- room bays on the street side
FRONT = FZ + 0.03


def room(floor, k):
    z0 = Y0 + floor * FH
    bl = bay_left(k)
    K.face_y("RoomFront", bl - BAY / 2, FRONT, z0, BAY, FH, facing=1)
    K.window3d("y", FRONT, 1, bl - 0.695 * BAY, z0 + 1.14 * M, 0.453 * BAY, 1.31 * M, mull=1, depth=0.1 * M)
    dc, dw, dt = bl - 0.227 * BAY, 0.234 * BAY, z0 + 0.863 * FH
    for s_ in (-1, 1):
        K._wbox("Frame", "y", FRONT, 1, dc, s_ * (dw / 2 + 0.05 * M), 0.05 * M, (z0 + dt) / 2, 0.1 * M, 0.1 * M, dt - z0)
    K._wbox("Frame", "y", FRONT, 1, dc, 0, 0.05 * M, dt + 0.05 * M, dw + 0.2 * M, 0.1 * M, 0.1 * M)
    K.box("Sconce", (bl - 0.06 * BAY, FRONT + 0.06 * M, z0 + 2.25 * M), (0.18 * M, 0.12 * M, 0.3 * M))
    K.box("AcBody", (bl - 0.72 * BAY, FRONT + 0.15 * M, z0 + 0.62 * M), (1.0 * M, 0.3 * M, 0.42 * M))
    K.face_y("AcUnit", bl - 0.72 * BAY, FRONT + 0.3 * M + 0.01, z0 + 0.42 * M, 0.96 * M, 0.4 * M, facing=1)


def window_bay(floor, k):
    """Bays behind the stair: windows only."""
    z0 = Y0 + floor * FH
    bl = bay_left(k)
    K.window3d("y", FZ, 1, bl - 0.5 * BAY, z0 + 1.2 * M, 1.5 * M, 1.3 * M, mull=1, bars=(floor == 0), depth=0.1 * M)


for k in range(14):
    for floor in (0, 1):
        if k < 2:
            if floor == 1:
                window_bay(floor, k)
        elif floor == 0 and k >= 11:
            continue                         # ice alcove + office below
        else:
            room(floor, k)

# ice + soda alcove (bay 11)
bl = bay_left(11)
K.face_y("BackWall", bl - BAY / 2, FRONT, Y0, BAY, FH, facing=1)
K.face_y("IceSign", bl - BAY / 2, FRONT + 0.03, Y0 + 2.3 * M, 2.4 * M, 0.6 * M, facing=1)
for u, part in ((0.3, "Soda"), (0.7, "IceMachine")):
    x = bl - u * BAY
    K.box("Dark", (x, FRONT + 0.4 * M, Y0 + 0.95 * M), (1.0 * M, 0.8 * M, 1.9 * M))
    K.face_y(part, x, FRONT + 0.8 * M + 0.01, Y0 + 0.02 * M, 0.96 * M, 1.84 * M, facing=1)

# office (bays 12-13, West St end): glass front, sign on the balustrade above, lamp under the walkway
ocx = bay_left(12) - BAY
K.face_y("OfficeGlass", ocx, FRONT, Y0, 2 * BAY - 1.6 * M, 3.0 * M, facing=1)
for s_ in (-1, 1):
    K.box("Stucco", (ocx + s_ * (BAY - 0.4 * M), FZ + 0.15, Y0 + FH / 2), (0.8 * M, 0.3, FH))
B("Trim", XE - 2 * BAY + 0.2, XE - 0.2, WZ + 0.18, WZ + 0.46, FH - 0.9, FH + 1.0 * M + 0.25)
K.face_y("OfficeSign", ocx, WZ + 0.49, Y0 + FH - 0.9, 2 * BAY - 0.6, 1.0 * M + 1.15, facing=1)
for k in range(5):
    x = XS + (k + 0.5) * (XE - XS) / 5
    K.lamp((-x, (FZ + WZ) / 2, Y0 + FH - 0.25 * M - 0.07), (2.4 * M, 0.4 * M, 0.04))

# ---------------------------------------------------------------- backs (alley) and ends: windows, vents, pipes
for k in range(14):
    a = -(XW + (k + 0.5) * BAY)
    for floor in (0, 1):
        z0 = Y0 + floor * FH
        K.window3d("y", ZB, -1, a + 0.24 * BAY, z0 + 1.75 * M, 0.75 * M, 0.6 * M, glass="GlassFrost", mull=0, depth=0.08 * M)
        K.window3d("y", ZB, -1, a - 0.18 * BAY, z0 + 1.0 * M, 1.4 * M, 1.3 * M, mull=1, bars=(floor == 0), depth=0.1 * M)
    if k % 3 == 0:
        K.downpipe(a - BAY / 2, ZB - 0.08 * M, Y0, Y0 + TOP)
for x, facing in ((XE, -1), (XW, 1)):          # blender x plane = -x; East end faces West St (blender -x)
    for floor in (0, 1):
        for zc in ((ZB + FZ) / 2 - 2.0 * M, (ZB + FZ) / 2 + 1.2 * M):
            K.window3d("x", -x, facing, zc, Y0 + floor * FH + 1.0 * M, 1.4 * M, 1.3 * M, mull=1, bars=(floor == 0), depth=0.1 * M)
K.meter_box("y", ZB, -1, -(XW + 6.5 * BAY), Y0 + 1.2 * M)

K.finish()
meta = K.export()
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("annex_street", (-(-230.0), 150.0, 40.0), (-(-270.0), 80.0, 10.0), lens=28)
    K.shot("annex_corner", (-(-130.0), 120.0, 30.0), (-(-200.0), 80.0, 10.0), lens=30)
    K.shot("annex_stair", (-(-385.0), 115.0, 22.0), (-(-345.0), 85.0, 8.0), lens=30)
