"""Halvorsen Building: a six-floor red brick walk-up with ground-floor shops (original design,
thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py
  blender --background --python build_brick.py -- OUT_DIR [--face S] [--no-render] [--samples N] [--res F]

Ground floor: four shops behind stone pilasters (printed interiors behind glass, painted sign
boards, striped canvas awnings, gooseneck lamps) and a recessed lobby with the street number.
Upper floors: double-hung windows with dark green frames, stone sills and keystone lintels,
window A/C units, two front fire escapes with stairs, railings and a drop ladder; stone belt
course and a deep cornice with dentils. Sides: windows, a faded painted furniture ad on the west
wall. Roof: tar deck, parapet with coping, stair bulkhead, a timber water tank on a steel stand,
A/C units, vents. Back: windows, a fire escape, a steel door, downpipes, concrete apron.

Variants (textures.json "<part>@<name>", picked per copy in tools/build_city_map.py):
  Brick: Red (default) | Brown | Tan      Storefronts + ShopSigns: A (default) | B
Built in studs (M = 3.6 per metre), front = -Y, ground-floor level z = 0 = sidewalk top, so the
model is placed with its origin at y 0.6. The walls run 0.7 m below that into the ground.
"""
import json, math, os, random, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402
from mathutils import Vector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\brick")
NAME = model_name("BrickBlock", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(14)

W2, Y0, Y1 = 15 * M, -10 * M, 10 * M
GF, FH, NF = 4.8 * M, 3.4 * M, 5
TOP = GF + NF * FH
BASE = -0.7 * M

for name, sheet, tile in (("Brick", "BrickRed", (1.6 * M, 1.6 * M)), ("Stone", "StoneTrim", (2 * M, 2 * M)),
                          ("Roof", "RoofTar", (4 * M, 4 * M)), ("Steel", "FireSteel", (1 * M, 1 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Wood", "TankWood", (1.2 * M, 1.2 * M)),
                          ("Pave", "Plinth", (3 * M, 3 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("Storefronts", "ShopSigns", "Awnings", "LobbyDoor"):
    K.mat(name, sheet=name + ("A" if name in ("Storefronts", "ShopSigns") else ""), explicit=True)
K.mat("GhostSign", sheet="GhostSign", explicit=True, alpha=True)
for name, col, rough, metal, emit in (("Dark", (0.05, 0.05, 0.055), 0.5, 0.3, 0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats(frame=(0.10, 0.20, 0.15), sill=(0.80, 0.77, 0.70))

SHOPS = [(-14.4 * M, -7.9 * M), (-7.3 * M, -2.2 * M), (2.2 * M, 7.3 * M), (7.9 * M, 14.4 * M)]
LOBBY = (-1.6 * M, 1.6 * M)
PILASTERS = [(-15 * M, -14.4 * M), (-7.9 * M, -7.3 * M), (-2.2 * M, -1.6 * M), (1.6 * M, 2.2 * M), (7.3 * M, 7.9 * M), (14.4 * M, 15 * M)]


def quad_uv(part, corners, box):
    """Quad with the atlas rectangle box = (u0, v0, u1, v1) (0..1, v up)."""
    u0, v0, u1, v1 = box
    K.quad(part, corners, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


# ---------------------------------------------------------------- masses
K.boxr("Brick", -W2, LOBBY[0], Y0 + 0.6 * M, Y1, BASE, GF)                 # ground floor, set back behind the pilasters
K.boxr("Brick", LOBBY[1], W2, Y0 + 0.6 * M, Y1, BASE, GF)
K.boxr("Brick", LOBBY[0], LOBBY[1], Y0 + 1.6 * M, Y1, BASE, GF)            # deeper at the lobby recess
K.boxr("Brick", -W2, W2, Y0, Y1, GF, TOP)                                  # upper floors
for (x0, x1, y0, y1) in ((-W2, W2, Y0, Y0 + 0.3 * M), (-W2, W2, Y1 - 0.3 * M, Y1),
                         (-W2, -W2 + 0.3 * M, Y0 + 0.3 * M, Y1 - 0.3 * M), (W2 - 0.3 * M, W2, Y0 + 0.3 * M, Y1 - 0.3 * M)):
    K.boxr("Brick", x0, x1, y0, y1, TOP, TOP + 1.2 * M)                     # parapet
    K.boxr("Stone", x0 - 0.08 * M, x1 + 0.08 * M, y0 - 0.08 * M, y1 + 0.08 * M, TOP + 1.2 * M, TOP + 1.36 * M) \
        if (x1 - x0) > (y1 - y0) else \
        K.boxr("Stone", x0 - 0.06 * M, x1 + 0.06 * M, y0, y1, TOP + 1.2 * M, TOP + 1.34 * M)
K.boxr("Roof", -W2 + 0.3 * M, W2 - 0.3 * M, Y0 + 0.3 * M, Y1 - 0.3 * M, TOP, TOP + 0.05 * M)

# stone belt course over the shops and a deep cornice under the parapet (front + both sides)
K.boxr("Stone", -W2 - 0.15 * M, W2 + 0.15 * M, Y0 - 0.15 * M, Y0, GF, GF + 0.32 * M)
for sx in (-1, 1):
    K.boxr("Stone", min(sx * W2, sx * (W2 + 0.13 * M)), max(sx * W2, sx * (W2 + 0.13 * M)), Y0, Y1, GF + 0.01 * M, GF + 0.3 * M)
K.boxr("Stone", -W2 - 0.2 * M, W2 + 0.2 * M, Y0 - 0.2 * M, Y0, TOP - 0.95 * M, TOP - 0.65 * M)
K.boxr("Stone", -W2 - 0.48 * M, W2 + 0.48 * M, Y0 - 0.48 * M, Y0, TOP - 0.6 * M, TOP)
for sx in (-1, 1):
    a, b = sorted((sx * W2, sx * (W2 + 0.18 * M)))
    K.boxr("Stone", a, b, Y0 + 0.02 * M, Y1, TOP - 0.93 * M, TOP - 0.67 * M)
    a, b = sorted((sx * W2, sx * (W2 + 0.45 * M)))
    K.boxr("Stone", a, b, Y0 + 0.02 * M, Y1, TOP - 0.58 * M, TOP - 0.02 * M)
x = -W2 + 0.2 * M
while x < W2 - 0.1 * M:                                                     # dentils
    K.boxr("Stone", x, x + 0.16 * M, Y0 - 0.34 * M, Y0 - 0.01 * M, TOP - 0.66 * M, TOP - 0.61 * M)
    x += 0.4 * M

# ---------------------------------------------------------------- ground floor front
for (x0, x1) in PILASTERS:
    K.boxr("Stone", x0, x1, Y0 - 0.1 * M, Y0 + 0.6 * M, BASE, GF)
    K.boxr("Stone", x0 - 0.05 * M, x1 + 0.05 * M, Y0 - 0.18 * M, Y0 + 0.6 * M, BASE, 0.6 * M)     # base block
fascia_z0, fascia_z1 = 3.6 * M, GF
for i, (x0, x1) in enumerate(SHOPS):
    K.boxr("Stone", x0, x1, Y0 + 0.4 * M, Y0 + 0.6 * M, BASE, 0.5 * M)                          # kick plate
    # glass: one shop of the 2x2 storefront atlas
    u0, v0 = (i % 2) * 0.5, 0.5 - (i // 2) * 0.5
    gy = Y0 + 0.57 * M
    quad_uv("Storefronts", [(x0, gy, 0.5 * M), (x1, gy, 0.5 * M), (x1, gy, 3.5 * M), (x0, gy, 3.5 * M)], (u0, v0, u0 + 0.5, v0 + 0.5))
    for fx in (x0 + 0.04 * M, x1 - 0.04 * M, x1 - (x1 - x0) * 0.22):                         # frame + door jamb
        K.boxr("Frame", fx - 0.05 * M, fx + 0.05 * M, gy - 0.08 * M, gy + 0.01 * M, 0.5 * M, 3.55 * M)
    K.boxr("Frame", x0, x1, gy - 0.08 * M, gy + 0.01 * M, 3.5 * M, 3.6 * M)
    K.boxr("Frame", x0, x1, gy - 0.08 * M, gy + 0.01 * M, 0.45 * M, 0.52 * M)
    # sign board on the fascia
    K.boxr("Stone", x0, x1, Y0 - 0.05 * M, Y0 + 0.6 * M, fascia_z0, fascia_z1)
    sy = Y0 - 0.07 * M
    quad_uv("ShopSigns", [(x0 + 0.15 * M, sy, fascia_z0 + 0.12 * M), (x1 - 0.15 * M, sy, fascia_z0 + 0.12 * M),
                          (x1 - 0.15 * M, sy, fascia_z1 - 0.12 * M), (x0 + 0.15 * M, sy, fascia_z1 - 0.12 * M)],
            (0, 1 - (i + 1) * 0.25, 1, 1 - i * 0.25))
    # gooseneck lamps over the sign
    for lx in (x0 + (x1 - x0) * 0.25, x1 - (x1 - x0) * 0.25):
        K.cyl_along("Steel", (lx, Y0 - 0.05 * M, GF - 0.05 * M), (lx, Y0 - 0.5 * M, GF + 0.15 * M), 0.025 * M, segs=6)
        K.box("Steel", (lx, Y0 - 0.55 * M, GF + 0.1 * M), (0.3 * M, 0.25 * M, 0.08 * M))
        K.box("Sconce", (lx, Y0 - 0.55 * M, GF + 0.05 * M), (0.24 * M, 0.2 * M, 0.02 * M))
    # canvas awning: sloped top, valance, closed sides (both faces so it reads from below too)
    ay0, ay1, az0, az1 = Y0 - 0.06 * M, Y0 - 1.5 * M, 3.5 * M, 2.85 * M
    ub = (i * 0.25, 0, i * 0.25 + 0.25, 1)
    top = [(x0, ay0, az0), (x0, ay1, az1), (x1, ay1, az1), (x1, ay0, az0)]
    # the inner faces sit 0.02 m inside the outer ones (opposite normals, no coplanar pair)
    e = 0.02 * M
    quad_uv("Awnings", [top[1], top[2], top[3], top[0]], ub)
    inner = [(x0 + e, ay0, az0 - e), (x1 - e, ay0, az0 - e), (x1 - e, ay1 + e, az1 - e), (x0 + e, ay1 + e, az1 - e)]
    quad_uv("Awnings", inner, ub)
    val = [(x0, ay1, az1 - 0.35 * M), (x1, ay1, az1 - 0.35 * M), (x1, ay1, az1), (x0, ay1, az1)]
    quad_uv("Awnings", val, (ub[0], 0, ub[2], 0.2))
    quad_uv("Awnings", [(x - e if x == x1 else x + e, y + e, z) for (x, y, z) in val[::-1]], (ub[0], 0, ub[2], 0.2))
    for sx_, si in ((x0, 1), (x1, -1)):
        tri = [(sx_, ay0, az0), (sx_, ay1, az1), (sx_, ay1, az1 - 0.35 * M), (sx_, ay0, az0 - 0.05 * M)]
        if si < 0:
            tri = tri[::-1]
        quad_uv("Awnings", tri, (ub[0], 0, ub[0] + 0.05, 1))
        quad_uv("Awnings", [(x + si * e, y, z) for (x, y, z) in tri[::-1]], (ub[0], 0, ub[0] + 0.05, 1))
    for sx_ in (x0 + 0.05 * M, x1 - 0.05 * M):                                                 # awning arms
        K.cyl_along("Steel", (sx_, Y0 - 0.02 * M, 2.6 * M), (sx_, ay1 + 0.05 * M, az1 - 0.05 * M), 0.025 * M, segs=6)

# lobby: recessed double door with the number transom, stone lining, wall lamps
ly = Y0 + 1.6 * M
K.boxr("Stone", LOBBY[0], LOBBY[1], Y0 - 0.12 * M, ly, BASE, 0.03 * M)                          # threshold slab
K.boxr("Stone", LOBBY[0], LOBBY[1], Y0 - 0.05 * M, ly, 3.55 * M, GF)                            # lintel over the recess
K.face_y("LobbyDoor", 0, ly - 0.02 * M, 0.03 * M, 2.6 * M, 3.5 * M)
for sx in (-1, 1):
    K.box("Steel", (sx * 1.35 * M, ly - 0.08 * M, 2.4 * M), (0.14 * M, 0.12 * M, 0.3 * M))
    K.box("Sconce", (sx * 1.35 * M, ly - 0.15 * M, 2.4 * M), (0.12 * M, 0.04 * M, 0.24 * M))

# ---------------------------------------------------------------- upper windows
WIN_W, WIN_H = 1.3 * M, 2.0 * M


def lintel(ax, plane, facing, a, ztop):
    """Stone lintel with a keystone over a window (wall plane ax/plane)."""
    K._wbox("Stone", ax, plane, facing, a, 0, 0.06 * M, ztop + 0.16 * M, WIN_W + 0.5 * M, 0.12 * M, 0.3 * M)
    K._wbox("Stone", ax, plane, facing, a, 0, 0.1 * M, ztop + 0.2 * M, 0.26 * M, 0.2 * M, 0.42 * M)


def ac_unit(ax, plane, facing, a, z0):
    K._wbox("AcBody", ax, plane, facing, a, 0, 0.25 * M, z0 + 0.45 * M, 0.7 * M, 0.5 * M, 0.42 * M)
    K._wbox("Dark", ax, plane, facing, a, 0, 0.505 * M, z0 + 0.45 * M, 0.56 * M, 0.02 * M, 0.3 * M)
    K._wbox("Steel", ax, plane, facing, a, 0, 0.2 * M, z0 + 0.2 * M, 0.6 * M, 0.4 * M, 0.04 * M)


def windows(ax, plane, facing, positions, floors, ac=0.12, bars_first=False):
    for k in floors:
        z0 = GF + k * FH + 0.9 * M
        for a in positions:
            K.window3d(ax, plane, facing, a, z0, WIN_W, WIN_H, mull=0, transom=True, head=False,
                       bars=bars_first and k == 0, depth=0.1 * M)
            lintel(ax, plane, facing, a, z0 + WIN_H + 0.07 * M)
            if rng.random() < ac:
                ac_unit(ax, plane, facing, a, z0)


bays = [-12.5 * M + i * 5 * M for i in range(6)]
front = [c + s * 1.2 * M for c in bays for s in (-1, 1)]
windows("y", Y0, -1, front, range(NF))
back = [c + s * 1.2 * M for c in bays for s in (-1, 1)]
windows("y", Y1, 1, back, range(NF), ac=0.2)
side = [-6 * M, -2 * M, 2 * M, 6 * M]
windows("x", W2, 1, side, range(NF))                       # east side
windows("x", -W2, -1, side, range(2))                      # west side: low floors only, painted ad above
K.face_x("GhostSign", -W2 - 0.02 * M, 0, GF + 2 * FH + 0.4 * M, 15 * M, 7.5 * M, facing=-1)
# west side shop window + a side door at street level
K.face_x("Storefronts", -W2 - 0.02 * M, -6 * M, 0.6 * M, 3 * M, 2.6 * M, facing=-1,
         uvs=((0.0, 0.5), (0.18, 0.5), (0.18, 1.0), (0.0, 1.0)))
K.boxr("Frame", -W2 - 0.1 * M, -W2, -7.6 * M, -4.4 * M, 3.2 * M, 3.3 * M)
K.boxr("Frame", -W2 - 0.1 * M, -W2, -7.6 * M, -4.4 * M, 0.5 * M, 0.6 * M)

# ---------------------------------------------------------------- fire escapes


def fire_escape(cx, plane, facing, floors, ladder=True, lx=None):
    """Platforms at each upper floor, railings, alternating stairs, brackets, drop ladder."""
    dep = 1.3 * M
    hw = 2.4 * M
    f = facing
    yi, yo = plane + f * 0.06 * M, plane + f * dep             # inner / outer edge
    lo_y, hi_y = sorted((yi, yo))
    for k in floors:
        z = GF + k * FH + 0.12 * M
        K.boxr("Steel", cx - hw, cx + hw, lo_y, hi_y, z - 0.06 * M, z)                                    # deck
        for x in (cx - hw, cx - hw / 2, cx, cx + hw / 2, cx + hw):                                       # posts
            K.boxr("Steel", x - 0.03 * M, x + 0.03 * M, yo - 0.03 * M if f < 0 else yo - 0.03 * M, yo + 0.03 * M, z, z + 1.0 * M)
        for x in (cx - hw, cx + hw):
            K.boxr("Steel", x - 0.03 * M, x + 0.03 * M, (yi + yo) / 2 - 0.03 * M, (yi + yo) / 2 + 0.03 * M, z, z + 1.0 * M)
        for zz in (z + 0.98 * M, z + 0.5 * M):                                                         # rails
            K.boxr("Steel", cx - hw, cx + hw, yo - 0.025 * M, yo + 0.025 * M, zz - 0.025 * M, zz + 0.025 * M)
            for x in (cx - hw, cx + hw):
                K.boxr("Steel", x - 0.025 * M, x + 0.025 * M, lo_y, hi_y, zz - 0.025 * M, zz + 0.025 * M)
        K.boxr("Steel", cx - hw, cx + hw, yo - 0.02 * M, yo + 0.02 * M, z, z + 0.12 * M)                  # toe kick
        for x in (cx - hw + 0.3 * M, cx + hw - 0.3 * M):                                                # brackets
            K.cyl_along("Steel", (x, plane + f * 0.02 * M, z - 1.1 * M), (x, yo - f * 0.08 * M, z - 0.07 * M), 0.035 * M, segs=6)
        if k + 1 in floors:                                                                             # stair up
            d = 1 if k % 2 == 0 else -1
            xa, xb = cx + d * (hw - 0.4 * M), cx - d * (hw - 1.2 * M)
            za, zb = z, z + FH
            ys = (yi + yo) / 2
            for s in (-1, 1):
                K.cyl_along("Steel", (xa, ys + s * 0.32 * M, za), (xb, ys + s * 0.32 * M, zb), 0.04 * M, segs=6)
            n = 13
            for t in range(1, n):
                u = t / n
                K.box("Steel", (xa + (xb - xa) * u, ys, za + (zb - za) * u), (0.22 * M, 0.6 * M, 0.03 * M))
            K.cyl_along("Steel", (xa, ys - f * 0.36 * M, za + 0.9 * M), (xb, ys - f * 0.36 * M, zb + 0.9 * M), 0.025 * M, segs=6)
    if ladder:                                                                                          # drop ladder
        z = GF + floors[0] * FH + 0.06 * M
        lx = cx + hw - 0.6 * M if lx is None else lx
        ly = yo - f * 0.25 * M
        for s in (-1, 1):
            K.boxr("Steel", lx + s * 0.25 * M - 0.025 * M, lx + s * 0.25 * M + 0.025 * M, ly - 0.025 * M, ly + 0.025 * M, 2.6 * M, z)
        zz = 2.75 * M
        while zz < z - 0.1 * M:
            K.boxr("Steel", lx - 0.25 * M, lx + 0.25 * M, ly - 0.015 * M, ly + 0.015 * M, zz - 0.015 * M, zz + 0.015 * M)
            zz += 0.3 * M


fire_escape(-7.5 * M, Y0, -1, list(range(NF)), lx=-7.6 * M)      # ladders drop in the pilaster gap, clear of the awnings
fire_escape(7.5 * M, Y0, -1, list(range(NF)), lx=7.6 * M)
fire_escape(2.5 * M, Y1, 1, list(range(NF)))

# ---------------------------------------------------------------- back + roof
K.boxr("Dark", -9 * M, -7.6 * M, Y1, Y1 + 0.06 * M, 0, 2.3 * M)                                    # back steel door
K.boxr("Stone", -9.3 * M, -7.3 * M, Y1, Y1 + 0.3 * M, 2.3 * M, 2.45 * M)
K.box("Sconce", (-8.3 * M, Y1 + 0.12 * M, 2.7 * M), (0.25 * M, 0.2 * M, 0.2 * M))
for x in (-W2 + 0.3 * M, W2 - 0.3 * M):
    K.downpipe(x, Y1 + 0.12 * M, 0, TOP + 0.6 * M)
K.boxr("Pave", -W2 - 3 * M, W2 + 3 * M, Y1, Y1 + 3 * M, BASE, -0.5 * M)                                # concrete apron (world 0.1)
K.boxr("Pave", -W2 - 3 * M, -W2, Y0 + 0.6 * M, Y1, BASE, -0.5 * M)
K.boxr("Pave", W2, W2 + 3 * M, Y0 + 0.6 * M, Y1, BASE, -0.5 * M)

# stair bulkhead
bx0, bx1, by0, by1 = -12 * M, -8.5 * M, 4 * M, 8 * M
K.boxr("Brick", bx0, bx1, by0, by1, TOP + 0.05 * M, TOP + 2.9 * M)
K.boxr("Stone", bx0 - 0.1 * M, bx1 + 0.1 * M, by0 - 0.1 * M, by1 + 0.1 * M, TOP + 2.9 * M, TOP + 3.05 * M)
K.boxr("Dark", -11 * M, -9.6 * M, by0 - 0.05 * M, by0, TOP + 0.05 * M, TOP + 2.2 * M)
# water tank on a steel stand
tx, ty, tz = 6 * M, 3 * M, TOP + 0.05 * M
for sx in (-1, 1):
    for sy in (-1, 1):
        K.cyl("Steel", (tx + sx * 1.2 * M, ty + sy * 1.2 * M, tz + 1.6 * M), 0.1 * M, 3.2 * M, segs=8)
for sx in (-1, 1):
    K.cyl_along("Steel", (tx + sx * 1.2 * M, ty - 1.2 * M, tz + 0.3 * M), (tx + sx * 1.2 * M, ty + 1.2 * M, tz + 2.9 * M), 0.04 * M, segs=6)
    K.cyl_along("Steel", (tx - 1.2 * M, ty + sx * 1.2 * M, tz + 0.3 * M), (tx + 1.2 * M, ty + sx * 1.2 * M, tz + 2.9 * M), 0.04 * M, segs=6)
K.boxr("Steel", tx - 1.75 * M, tx + 1.75 * M, ty - 1.75 * M, ty + 1.75 * M, tz + 3.2 * M, tz + 3.4 * M)
K.cyl("Wood", (tx, ty, tz + 3.4 * M + 1.7 * M), 1.6 * M, 3.4 * M, segs=20)
for z in (0.4, 1.3, 2.2, 3.0):
    K.cyl("Steel", (tx, ty, tz + 3.4 * M + z * M), 1.63 * M, 0.08 * M, segs=20)
K.cyl("Roof", (tx, ty, tz + 3.4 * M + 3.4 * M + 0.45 * M), 1.75 * M, 0.9 * M, segs=20, r2=0.15 * M)
K.cyl_along("Steel", (tx + 1.62 * M, ty, tz + 3.4 * M), (tx + 1.62 * M, ty, tz + 6.8 * M), 0.03 * M, segs=4)   # ladder rail
# A/C units, vents, skylight
for (x, y) in ((-3 * M, -4 * M), (1.5 * M, -4 * M)):
    K.boxr("AcBody", x - 1.2 * M, x + 1.2 * M, y - 0.8 * M, y + 0.8 * M, TOP + 0.05 * M, TOP + 1.3 * M)
    K.cyl("Dark", (x, y, TOP + 1.32 * M), 0.6 * M, 0.04 * M, segs=16)
for (x, y) in ((-5 * M, 6 * M), (11 * M, -6 * M), (12 * M, 7 * M)):
    K.cyl("Steel", (x, y, TOP + 0.6 * M), 0.12 * M, 1.1 * M, segs=8)
    K.cyl("Steel", (x, y, TOP + 1.2 * M), 0.22 * M, 0.12 * M, segs=8)
K.boxr("Stone", -2 * M, 2 * M, 3 * M, 7 * M, TOP + 0.05 * M, TOP + 0.5 * M)
K.boxr("ClearGlassSky", -1.8 * M, 1.8 * M, 3.2 * M, 6.8 * M, TOP + 0.5 * M, TOP + 0.56 * M, mat="GlassA")

K.finish(face=A["face"])
meta = K.export()
# variant sheets for other copies (tools/install_model.py copies meta["variants"])
meta["variants"] = {"Brick": {"Brown": "BrickBrown_Color.png", "Tan": "BrickTan_Color.png"},
                    "Storefronts": {"B": "StorefrontsB_Color.png"}, "ShopSigns": {"B": "ShopSignsB_Color.png"}}
for part, opts in meta["variants"].items():
    for fn in opts.values():
        shutil.copyfile(os.path.join(TEX, fn), os.path.join(K.tex, fn))
meta["driveways"] = []
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    s = -1 if A["face"] == "N" else 1
    K.shot("front", (-18 * M, s * 38 * M, 9 * M), (0, 0, 9 * M), lens=28)
    K.shot("street", (-9 * M, s * 17 * M, 1.7 * M), (2 * M, Y0 * -s * -1, 4 * M), lens=24)
    K.shot("back", (22 * M, -s * 40 * M, 16 * M), (0, 0, 10 * M), lens=30)
