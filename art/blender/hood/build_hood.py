"""Neighborhood buildings for the tulevo gang hoods + the main spawn plaza (original designs).

  blender --background --python build_hood.py -- OUT_DIR --only HouseA|HouseB|Store|Court|SpawnPlaza [--face S]
                                                [--no-render] [--samples N] [--res F]

HouseA      one-floor stucco bungalow: hip shingle roof, porch, barred windows, security door,
            iron fence with gate, driveway, wall A/C, bins, mailbox, palm, dish, graffiti tag.
HouseB      two-floor flat-roof house with a garage, balcony on the garage roof, block + iron wall.
Store       corner market "Sunny's Market": printed sign, barred glass front, lot with stalls,
            ice box, payphone, news boxes, dumpster, lot lights, big side tag.
Court       fenced street basketball court (gang spawn): painted court, two hoops, chain-link fence,
            tagged block wall, benches, picnic table, lights.
SpawnPlaza  main spawn: paved plaza, fountain, benches ring, palms, bus shelter, WELCOME TO
            TULEVO monument, route map kiosk, flagpoles, bollards, lamps.

Gang looks are texture variants (tools/hood_textures.py): meta["variants"] lists the PNGs a
placed copy can swap in for a part ("Walls" paint, "Tag", "CourtPaint"); tools/build_city_map.py
picks them per building. Lot origin = ground centre, front = -Y (street), studs (M = 3.6).
"""
import json, math, os, random, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402
from mathutils import Vector  # noqa: E402

A = args(r"C:\out\hood")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = argv[argv.index("--only") + 1]
NAME = model_name(ONLY, A)
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
K = Kit(NAME, A["out"], TEX)
rng = random.Random({"HouseA": 1, "HouseB": 2, "Store": 3, "Court": 4, "SpawnPlaza": 5}[ONLY])

PALETTES = ("Cream", "Sand", "Sky", "Rose", "Brick", "Blush", "Butter", "Tan", "Peach", "Mint", "Sage", "Teal")
GANGS = ("RedCrowns", "Vipers", "GroveKings")   # original gang names, see tools/hood_textures.py
VARIANTS = {}

# ---------------------------------------------------------------- materials
K.mat("Walls", sheet="WallCream" if ONLY != "Store" else "WallSand", tile=(3.5 * M, 3.5 * M))
for name, sheet, tile in (("Lawn", "Lawn", (3 * M, 3 * M)), ("Concrete", "Concrete", (3 * M, 3 * M)),
                          ("Asphalt", "Asphalt", (8 * M, 8 * M)), ("Roof", "Shingles", (2.5 * M, 2.5 * M)),
                          ("Pave", "PlazaPave", (4 * M, 4 * M)), ("Water", "Water", (3 * M, 3 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("BarWindow", "SecurityDoor", "GarageDoor", "StoreFront", "StoreSign", "StoreDoor", "Backboard",
             "WelcomeSign", "ShelterAd", "RouteMap"):
    K.mat(name, sheet=name, explicit=True)
K.mat("CourtPaint", sheet="CourtPaint", explicit=True)
K.mat("Tag", sheet="Tag", explicit=True, alpha=True)
K.mat("ChainLink", sheet="ChainLink", explicit=True, alpha=True, metal=0.6, rough=0.4)
for name, col, rough, metal, emit in (
        ("Trim", (0.93, 0.92, 0.88), 0.6, 0, 0), ("Iron", (0.03, 0.03, 0.035), 0.45, 0.6, 0), ("Foundation", (0.55, 0.54, 0.51), 0.9, 0, 0),
        ("Flat", (0.30, 0.30, 0.29), 0.95, 0, 0), ("AcBody", (0.80, 0.79, 0.75), 0.6, 0.2, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.2, 0),
        ("BinGreen", (0.10, 0.26, 0.14), 0.6, 0, 0), ("BinGrey", (0.22, 0.23, 0.24), 0.6, 0, 0), ("BinBlue", (0.10, 0.22, 0.48), 0.6, 0, 0),
        ("Mailbox", (0.85, 0.85, 0.82), 0.4, 0.5, 0), ("Pole", (0.55, 0.56, 0.57), 0.4, 0.9, 0), ("Wood", (0.42, 0.28, 0.17), 0.85, 0, 0),
        ("Paint", (0.94, 0.94, 0.90), 0.7, 0, 0), ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("WheelStop", (0.75, 0.74, 0.70), 0.9, 0, 0),
        ("Rim", (0.95, 0.35, 0.05), 0.4, 0.6, 0), ("Net", (0.95, 0.95, 0.95), 0.8, 0, 0), ("Block", (0.62, 0.61, 0.58), 0.95, 0, 0),
        ("Stone", (0.80, 0.77, 0.70), 0.8, 0, 0), ("Glass", (0.45, 0.58, 0.62), 0.1, 0.3, 0), ("IceBox", (0.94, 0.95, 0.97), 0.4, 0.2, 0),
        ("IceBlue", (0.10, 0.40, 0.80), 0.5, 0, 0), ("Red", (0.70, 0.08, 0.08), 0.5, 0.1, 0), ("Dumpster", (0.10, 0.30, 0.16), 0.6, 0.3, 0),
        ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0), ("NeonCyan", (0.2, 0.95, 1.0), 0.5, 0, 6.0),
        ("Shrub", (0.12, 0.30, 0.10), 0.85, 0, 0), ("Palm", (0.20, 0.42, 0.14), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
        ("Soil", (0.18, 0.12, 0.08), 1.0, 0, 0), ("Kerb", (0.62, 0.62, 0.60), 0.9, 0, 0), ("Flag", (0.85, 0.85, 0.82), 0.8, 0, 0),
        ("Tile", (0.16, 0.42, 0.55), 0.3, 0, 0), ("Plastic", (0.92, 0.92, 0.90), 0.5, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats()


# ---------------------------------------------------------------- helpers
def rot(dx, dy, rz):
    c, s = math.cos(rz), math.sin(rz)
    return dx * c - dy * s, dx * s + dy * c


def piece(part, x, y, rz, dx, dy, z, size):
    ox, oy = rot(dx, dy, rz)
    K.box(part, (x + ox, y + oy, z), size, rz=rz)


def window(face, a, z0, w=1.4 * M, h=1.4 * M, bars=True):
    """Real 3D window on a wall plane: face = ('y', y, facing) or ('x', x, facing); a = centre along
    the wall. Ground-floor windows get iron security bars, LA style."""
    ax, pos, facing = face
    K.window3d(ax, pos, facing, a, z0, w, h, mull=1, bars=bars and z0 < 2.5 * M, depth=0.1 * M)


def iron_fence(x0, y0, x1, y1, h=1.4 * M, gaps=(), step=0.16 * M, z0=0.0):
    """Black picket fence along a straight line; gaps = list of (t0, t1) fractions left open."""
    a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
    L = (b - a).length
    d = (b - a) / L
    rz = math.atan2(d.y, d.x)
    open_ = lambda t: any(g0 <= t <= g1 for g0, g1 in gaps)
    runs, cur = [], None
    n = int(L / step)
    for i in range(n + 1):
        t = i / n
        if open_(t):
            if cur is not None:
                runs.append((cur, (i - 1) / n)); cur = None
            continue
        if cur is None:
            cur = t
        p = a + d * (L * t)
        K.box("Iron", (p.x, p.y, z0 + h / 2), (0.1, 0.1, h), rz=rz)
    if cur is not None:
        runs.append((cur, 1.0))
    for t0, t1 in runs:
        pa, pb = a + d * (L * t0), a + d * (L * t1)
        c, ln = (pa + pb) / 2, (pb - pa).length + 0.1
        for z in (0.2 * M, h - 0.12 * M):
            K.box("Iron", (c.x, c.y, z0 + z), (ln, 0.14, 0.14), rz=rz)
        for t in (t0, t1):
            p = a + d * (L * t)
            K.box("Iron", (p.x, p.y, z0 + h / 2 + 0.1 * M), (0.3, 0.3, h + 0.2 * M), rz=rz)


def chain_fence(x0, y0, x1, y1, h=3.6 * M, post=3 * M):
    """Galvanised posts + top rail + see-through chain-link mesh (both sides)."""
    a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
    L = (b - a).length
    d = (b - a) / L
    n = max(1, round(L / post))
    for i in range(n + 1):
        p = a + d * (L * i / n)
        K.cyl("Pole", (p.x, p.y, h / 2), 0.07 * M, h, segs=8)
    K.cyl_along("Pole", (a.x, a.y, h - 0.05 * M), (b.x, b.y, h - 0.05 * M), 0.04 * M, segs=6)
    t = 0.9 * M
    uvs = ((0, 0), (L / t, 0), (L / t, h / t), (0, h / t))
    nrm = Vector((-d.y, d.x, 0)) * 0.03
    for s in (1, -1):
        o = nrm * s
        pa, pb = a + o, b + o
        corners = [(pa.x, pa.y, 0.05), (pb.x, pb.y, 0.05), (pb.x, pb.y, h - 0.1 * M), (pa.x, pa.y, h - 0.1 * M)]
        if s < 0:
            corners = corners[::-1]
            uvs_ = uvs[::-1]
        else:
            uvs_ = uvs
        K.quad("ChainLink", corners, uvs_)


def bench(x, y, rz, w=1.8 * M):
    piece("Wood", x, y, rz, 0, 0, 0.45 * M, (w, 0.45 * M, 0.06 * M))
    piece("Wood", x, y, rz, 0, 0.24 * M, 0.75 * M, (w, 0.06 * M, 0.35 * M))
    for dx in (-w / 2 + 0.15 * M, w / 2 - 0.15 * M):
        piece("Iron", x, y, rz, dx, 0, 0.22 * M, (0.08 * M, 0.45 * M, 0.44 * M))
        piece("Iron", x, y, rz, dx, 0.24 * M, 0.6 * M, (0.08 * M, 0.06 * M, 0.75 * M))


def lamp_post(x, y, h=6.5 * M, arm=(0, 1)):
    K.cyl("Pole", (x, y, h / 2), 0.1 * M, h, segs=10, r2=0.07 * M)
    K.box("Pole", (x, y, 0.3 * M), (0.35 * M, 0.35 * M, 0.6 * M))
    ex, ey = x + arm[0] * 1.3 * M, y + arm[1] * 1.3 * M
    K.cyl_along("Pole", (x, y, h - 0.1 * M), (ex, ey, h - 0.1 * M), 0.05 * M, segs=6)
    K.box("Dark", (ex, ey, h - 0.1 * M), (0.6 * M, 0.6 * M, 0.2 * M))
    K.lamp((ex, ey, h - 0.24 * M), (0.48 * M, 0.48 * M, 0.08 * M))


def bins(x, y, n=2):
    for i in range(n):
        bx = x + i * 0.8 * M
        part = ("BinGreen", "BinGrey", "BinBlue")[i % 3]
        K.box(part, (bx, y, 0.5 * M), (0.65 * M, 0.7 * M, 1.0 * M))
        K.box(part, (bx, y + 0.02 * M, 1.04 * M), (0.7 * M, 0.78 * M, 0.08 * M))
        K.cyl("Dark", (bx - 0.3 * M, y + 0.32 * M, 0.1 * M), 0.1 * M, 0.08 * M, segs=8, axis='X')
        K.cyl("Dark", (bx + 0.3 * M, y + 0.32 * M, 0.1 * M), 0.1 * M, 0.08 * M, segs=8, axis='X')


def ac_unit_x(x, y, z, facing):
    K.box("AcBody", (x + facing * 0.32 * M, y, z), (0.62 * M, 0.75 * M, 0.5 * M))
    K.box("Dark", (x + facing * 0.635 * M, y, z), (0.02, 0.6 * M, 0.36 * M))
    K.box("Iron", (x + facing * 0.3 * M, y, z - 0.3 * M), (0.55 * M, 0.06 * M, 0.06 * M))


def dish(x, y, z, facing=-1):
    K.cyl("Pole", (x, y, z + 0.25 * M), 0.03 * M, 0.5 * M, segs=6)
    K.cyl("Plastic", (x, y + facing * 0.12 * M, z + 0.6 * M), 0.4 * M, 0.08 * M, segs=16, axis='Y', r2=0.3 * M)
    K.cyl_along("Pole", (x, y + facing * 0.15 * M, z + 0.6 * M), (x, y + facing * 0.55 * M, z + 0.62 * M), 0.015 * M, segs=4)


def tag(x_or_y, ax, a, z0, w, h, facing):
    if ax == "x":
        K.face_x("Tag", x_or_y + 0.05 * facing, a, z0, w, h, facing=facing)
    else:
        K.face_y("Tag", a, x_or_y + 0.05 * facing, z0, w, h, facing=facing)


def mailbox(x, y):
    K.box("Wood", (x, y, 0.5 * M), (0.1 * M, 0.1 * M, 1.0 * M))
    K.box("Mailbox", (x, y, 1.08 * M), (0.25 * M, 0.5 * M, 0.25 * M))
    K.box("Red", (x + 0.14 * M, y + 0.1 * M, 1.2 * M), (0.02, 0.05 * M, 0.2 * M))


def planter(x, y, w, d, h=0.6 * M, palm=True):
    K.box("Stone", (x, y, h / 2), (w, d, h))
    K.box("Soil", (x, y, h + 0.01), (w - 0.3 * M, d - 0.3 * M, 0.04))
    if palm:
        K.palm(x, y, h, rng.uniform(6.5, 8.5) * M, (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)), rng)
    else:
        for i in range(3):
            K.shrub(x + (i - 1) * w / 3.5, y, h, 0.5 * M, rng)


# ---------------------------------------------------------------- HouseA: bungalow
def house_a():
    LW, LD = 16 * M, 26 * M
    X0, X1, Y0, Y1 = -6 * M, 3.5 * M, -2 * M, 8 * M
    FZ, TOP = 0.4 * M, 3.2 * M
    K.boxr("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Concrete", 4.3 * M, 7.7 * M, -LD / 2, Y1, 0, 0.04)                       # driveway
    K.boxr("Concrete", -4.0 * M, -3.0 * M, -12.6 * M, -4 * M, 0, 0.04)               # front walk
    K.boxr("Concrete", -2 * M, 2 * M, Y1, Y1 + 3 * M, 0, 0.04)                      # back patio
    K.boxr("Foundation", X0 - 0.1, X1 + 0.1, Y0 - 0.1, Y1 + 0.1, 0, FZ)
    K.boxr("Walls", X0, X1, Y0, Y1, FZ, TOP)
    # hip roof
    bm = K.bm("Roof")
    o = 0.5 * M
    rx0, rx1, ry0, ry1, rz, rh = X0 - o, X1 + o, Y0 - o, Y1 + o, TOP, 1.7 * M
    inset = (rx1 - rx0) / 2
    base = [bm.verts.new(p) for p in ((rx0, ry0, rz), (rx1, ry0, rz), (rx1, ry1, rz), (rx0, ry1, rz))]
    cx = (rx0 + rx1) / 2
    r0, r1 = bm.verts.new((cx, ry0 + inset, rz + rh)), bm.verts.new((cx, ry1 - inset, rz + rh))
    bm.faces.new([base[0], base[1], r0]); bm.faces.new([base[1], base[2], r1, r0])
    bm.faces.new([base[2], base[3], r1]); bm.faces.new([base[3], base[0], r0, r1])
    bm.faces.new(base[::-1])
    for (a0, a1, b0, b1) in ((rx0, rx1, ry0, ry0 + 0.06 * M), (rx0, rx1, ry1 - 0.06 * M, ry1), (rx0, rx0 + 0.06 * M, ry0, ry1),
                             (rx1 - 0.06 * M, rx1, ry0, ry1)):
        K.boxr("Trim", a0, a1, b0, b1, rz - 0.25 * M, rz + 0.02)                    # fascia
    K.boxr("Trim", X0, X1, Y0, Y1, TOP - 0.05, TOP)
    # porch
    K.boxr("Concrete", -5.2 * M, -0.8 * M, -4.2 * M, Y0, 0, FZ - 0.05)
    K.boxr("Concrete", -4.2 * M, -2.8 * M, -4.7 * M, -4.2 * M, 0, FZ / 2)           # step
    for px in (-5.0 * M, -1.0 * M):
        K.boxr("Trim", px - 0.09 * M, px + 0.09 * M, -4.1 * M, -3.92 * M, FZ - 0.05, 2.75 * M)
    K.boxr("Roof", -5.4 * M, -0.6 * M, -4.4 * M, Y0 - 0.05, 2.75 * M, 2.92 * M)
    K.boxr("Trim", -5.4 * M, -0.6 * M, -4.45 * M, -4.4 * M, 2.7 * M, 2.92 * M)
    iron_fence(-5.0 * M, -4.0 * M, -4.3 * M, -4.0 * M, h=0.9 * M)
    iron_fence(-2.7 * M, -4.0 * M, -1.0 * M, -4.0 * M, h=0.9 * M)
    # door, windows
    K.face_y("SecurityDoor", -3.5 * M, Y0 - 0.04, FZ, 1.05 * M, 2.15 * M)
    K.box("Sconce", (-2.7 * M, Y0 - 0.08 * M, 2.4 * M), (0.18 * M, 0.16 * M, 0.26 * M))
    front = ("y", Y0, -1)
    window(front, -1.6 * M, 1.2 * M)
    window(front, 1.6 * M, 1.2 * M, w=1.8 * M)
    for a in (0.5 * M, 4.8 * M):
        window(("x", X0, -1), a, 1.2 * M)
    for a in (-0.3 * M, 5.6 * M):
        window(("x", X1, 1), a, 1.2 * M)
    for a in (-3.8 * M, 1.6 * M):
        window(("y", Y1, 1), a, 1.4 * M, w=1.2 * M, h=1.2 * M)
    K.face_y("SecurityDoor", -1.2 * M, Y1 + 0.04, FZ, 1.0 * M, 2.1 * M, facing=1)
    ac_unit_x(X1, 3.0 * M, 1.9 * M, 1)
    tag(X0, "x", 2.65 * M, 1.85 * M, 2.7 * M, 1.0 * M, -1)
    dish(X1 - 0.6 * M, Y1 - 1.2 * M, TOP + 0.4 * M)
    K.cyl("Pole", (X0 + 1.5 * M, 5 * M, TOP + 1.4 * M), 0.06 * M, 0.8 * M, segs=6)   # vent pipe
    # gutters + downpipes
    for (gx, gy) in ((rx0 + 0.1 * M, ry0 + 0.1 * M), (rx1 - 0.1 * M, ry1 - 0.1 * M)):
        K.cyl("Trim", (gx, gy, rz / 2), 0.05 * M, rz, segs=6)
    # fences, gate gaps for the walk and the driveway
    iron_fence(-LW / 2 + 0.1, -12.6 * M, LW / 2 - 0.1, -12.6 * M, gaps=((0.24, 0.32), (0.76, 0.99)))
    iron_fence(-LW / 2 + 0.15, -12.6 * M, -LW / 2 + 0.15, Y0, h=1.2 * M)
    K.boxr("Block", -LW / 2, -LW / 2 + 0.2 * M, Y0, LD / 2, 0, 1.8 * M)              # block wall round the back yard
    K.boxr("Block", -LW / 2, LW / 2, LD / 2 - 0.2 * M, LD / 2, 0, 1.8 * M)
    K.boxr("Block", LW / 2 - 0.2 * M, LW / 2, Y1 + 0.5 * M, LD / 2, 0, 1.8 * M)
    mailbox(-2.2 * M, -12.2 * M)
    bins(4.6 * M, -11.0 * M, 3)
    K.palm(-6.2 * M, -9.0 * M, 0, 7.5 * M, (0.4, -0.3), rng)
    for sx in (-5.8, -4.8, -1.8, -0.9, 0.1, 1.1, 2.2):
        K.shrub(sx * M, Y0 - 0.9 * M, 0, 0.45 * M, rng)
    # back yard: plastic chairs, bbq, clothesline
    for cx in (-0.8 * M, 0.8 * M):
        K.box("Plastic", (cx, Y1 + 1.8 * M, 0.4 * M), (0.5 * M, 0.5 * M, 0.06 * M))
        K.box("Plastic", (cx, Y1 + 2.05 * M, 0.7 * M), (0.5 * M, 0.06 * M, 0.6 * M))
        for lx in (-0.22, 0.22):
            for ly in (-0.22, 0.22):
                K.box("Plastic", (cx + lx * M, Y1 + 1.8 * M + ly * M, 0.2 * M), (0.05 * M, 0.05 * M, 0.4 * M))
    K.cyl("Dark", (3 * M, Y1 + 2 * M, 0.85 * M), 0.35 * M, 0.3 * M, segs=12)
    for lx in (-0.25, 0.25):
        K.cyl_along("Iron", (3 * M + lx * M, Y1 + 2 * M, 0), (3 * M + lx * 0.5 * M, Y1 + 2 * M, 0.75 * M), 0.025 * M, segs=4)
    for py in (Y1 + 4.5 * M, LD / 2 - 1.5 * M):
        K.cyl("Pole", (-4 * M, py, 1.0 * M), 0.04 * M, 2.0 * M, segs=6)
    K.cyl_along("Net", (-4 * M, Y1 + 4.5 * M, 1.95 * M), (-4 * M, LD / 2 - 1.5 * M, 1.95 * M), 0.01 * M, segs=4)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (14 * M, -30 * M, 6 * M), (0, 0, 2 * M), 26), ("02_aerial", (22 * M, -26 * M, 22 * M), (0, 0, 0), 28),
            ("03_side", (-20 * M, -8 * M, 3 * M), (-4 * M, 3 * M, 2 * M), 26)]


# ---------------------------------------------------------------- HouseB: two floors + garage
def house_b():
    LW, LD = 16 * M, 26 * M
    X0, X1, Y0, Y1 = -6.5 * M, 1.5 * M, -1 * M, 8 * M
    FZ, FH = 0.4 * M, 2.9 * M
    TOP = FZ + 2 * FH
    GX1, GY1, GH = 7.3 * M, 7 * M, 3.1 * M
    K.boxr("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Concrete", 2.0 * M, 7.0 * M, -LD / 2, Y0, 0, 0.04)                       # driveway
    K.boxr("Concrete", -3.6 * M, -2.6 * M, -11.6 * M, -2.2 * M, 0, 0.04)
    K.boxr("Foundation", X0 - 0.1, X1, Y0 - 0.1, Y1 + 0.1, 0, FZ)
    K.boxr("Walls", X0, X1, Y0, Y1, FZ, TOP - 0.05)
    K.boxr("Walls", X1, GX1, Y0, GY1, 0, GH)
    K.boxr("Flat", X0 + 0.3, X1 - 0.3, Y0 + 0.3, Y1 - 0.3, TOP - 0.05, TOP + 0.03)
    for (a0, a1, b0, b1) in ((X0, X1, Y0, Y0 + 0.25 * M), (X0, X1, Y1 - 0.25 * M, Y1), (X0, X0 + 0.25 * M, Y0, Y1), (X1 - 0.25 * M, X1, Y0, Y1)):
        K.boxr("Walls", a0, a1, b0, b1, TOP - 0.05, TOP + 0.7 * M)                  # parapet
        K.boxr("Trim", a0 - 0.05, a1 + 0.05, b0 - 0.05, b1 + 0.05, TOP + 0.7 * M, TOP + 0.8 * M)
    K.boxr("Trim", X0 - 0.06, X1 + 0.06, Y0 - 0.12 * M, Y0, FZ + FH - 0.1 * M, FZ + FH + 0.1 * M)   # floor band
    K.boxr("Flat", X1 + 0.05, GX1 - 0.2, Y0 + 0.2, GY1 - 0.2, GH, GH + 0.06)
    # garage roof balcony: iron railing round the edge
    iron_fence(X1 + 0.1, Y0 + 0.15, GX1 - 0.15, Y0 + 0.15, h=1.0 * M, z0=GH)
    iron_fence(GX1 - 0.15, Y0 + 0.15, GX1 - 0.15, GY1 - 0.15, h=1.0 * M, z0=GH)
    K.face_x("SecurityDoor", X1 + 0.04, 2.5 * M, FZ + FH, 1.0 * M, 2.1 * M, facing=1)   # balcony door
    K.box("Sconce", (X1 + 0.08 * M, 3.4 * M, FZ + FH + 2.0 * M), (0.16 * M, 0.18 * M, 0.26 * M))
    # garage door + light
    K.face_y("GarageDoor", 4.5 * M, Y0 - 0.04, 0, 4.0 * M, 2.6 * M)
    K.boxr("Trim", 2.35 * M, 6.65 * M, Y0 - 0.12 * M, Y0, 2.6 * M, 2.75 * M)
    K.box("Sconce", (4.5 * M, Y0 - 0.08 * M, 2.9 * M), (0.3 * M, 0.16 * M, 0.18 * M))
    # entrance: door with a small canopy
    K.face_y("SecurityDoor", -3.1 * M, Y0 - 0.04, FZ, 1.05 * M, 2.15 * M)
    K.boxr("Concrete", -4.0 * M, -2.2 * M, Y0 - 1.2 * M, Y0, 0, FZ - 0.05)
    K.boxr("Trim", -4.2 * M, -2.0 * M, Y0 - 1.2 * M, Y0, 2.75 * M, 2.88 * M)
    for bx in (-4.1 * M, -2.1 * M):
        K.cyl_along("Iron", (bx, Y0 - 1.15 * M, 2.75 * M), (bx, Y0, 3.5 * M), 0.025 * M, segs=4)
    K.box("Sconce", (-2.3 * M, Y0 - 0.08 * M, 2.4 * M), (0.18 * M, 0.16 * M, 0.26 * M))
    f = ("y", Y0, -1)
    window(f, -5.3 * M, 1.2 * M, w=1.4 * M)
    window(f, -0.8 * M, 1.2 * M, w=1.4 * M)
    for a in (-4.8 * M, -1.5 * M):
        window(f, a, FZ + FH + 0.8 * M, w=1.5 * M, h=1.3 * M)
    for a in (1.5 * M, 5.5 * M):
        for z in (1.2 * M, FZ + FH + 0.8 * M):
            window(("x", X0, -1), a, z, w=1.2 * M, h=1.3 * M)
    for a in (-4 * M, -0.5 * M):
        for z in (1.2 * M, FZ + FH + 0.8 * M):
            window(("y", Y1, 1), a, z, w=1.3 * M, h=1.3 * M)
    window(("x", X1, 1), 6.0 * M, FZ + FH + 0.8 * M, w=1.2 * M, h=1.3 * M)
    K.face_x("SecurityDoor", GX1 + 0.04, 5.5 * M, 0, 0.95 * M, 2.1 * M, facing=1)    # garage side door
    ac_unit_x(X0, 3.4 * M, FZ + FH + 1.5 * M, -1)
    for (cx, cy) in ((-4 * M, 5 * M), (-1 * M, 2 * M)):
        K.box("AcBody", (cx, cy, TOP + 0.4 * M), (1.2 * M, 1.0 * M, 0.8 * M))
        K.cyl("Dark", (cx, cy, TOP + 0.81 * M), 0.4 * M, 0.03, segs=12)
    dish(-5.6 * M, 0.2 * M, TOP + 0.75 * M)
    tag(X0, "x", 6.0 * M, 0.5 * M, 3.6 * M, 1.35 * M, -1)
    K.cyl("Trim", (X1 - 0.12 * M, Y0 - 0.1 * M, TOP / 2), 0.05 * M, TOP, segs=6)    # downpipe
    # front wall: block base, iron on top, gaps for walk and driveway
    for (wx0, wx1) in ((-LW / 2 + 0.1, -3.9 * M), (-2.3 * M, 1.6 * M)):
        K.boxr("Block", wx0, wx1, -12.75 * M, -12.45 * M, 0, 0.8 * M)
        K.boxr("Stone", wx0 - 0.03, wx1 + 0.03, -12.8 * M, -12.4 * M, 0.8 * M, 0.9 * M)
        iron_fence(wx0 + 0.2, -12.6 * M, wx1 - 0.2, -12.6 * M, h=1.0 * M)
        for px in (wx0 + 0.25 * M, wx1 - 0.25 * M):
            K.box("Block", (px, -12.6 * M, 0.75 * M), (0.5 * M, 0.5 * M, 1.5 * M))
            K.box("Stone", (px, -12.6 * M, 1.53 * M), (0.6 * M, 0.6 * M, 0.08 * M))
    K.boxr("Block", -LW / 2, -LW / 2 + 0.2 * M, -12.4 * M, LD / 2, 0, 1.8 * M)
    K.boxr("Block", -LW / 2, LW / 2, LD / 2 - 0.2 * M, LD / 2, 0, 1.8 * M)
    K.boxr("Block", LW / 2 - 0.2 * M, LW / 2, GY1, LD / 2, 0, 1.8 * M)
    mailbox(-1.9 * M, -12.1 * M)
    bins(2.3 * M, -10.5 * M, 2)
    K.palm(5.0 * M, 10.5 * M, 0, 8.5 * M, (-0.4, 0.3), rng)
    K.shrub(-6.5 * M, -8 * M, 0, 0.9 * M, rng)
    for sx in (-6.0, -5.0, -1.4, -0.4, 0.6):
        K.shrub(sx * M, Y0 - 0.8 * M, 0, 0.42 * M, rng)
    # parked old sedan stand-in? no: a basketball hoop over the garage door, a kid bike in the yard
    K.cyl("Pole", (7.5 * M, -6 * M, 1.6 * M), 0.06 * M, 3.2 * M, segs=8)
    K.face_x("Backboard", 7.45 * M, -6 * M, 2.8 * M, 1.4 * M, 0.88 * M, facing=-1)
    K.face_x("Backboard", 7.55 * M, -6 * M, 2.8 * M, 1.4 * M, 0.88 * M, facing=1)
    for i in range(12):
        a0, a1 = i / 12 * math.tau, (i + 1) / 12 * math.tau
        c = Vector((7.2 * M, -6 * M, 3.05 * M))
        K.cyl_along("Rim", c + Vector((math.cos(a0), math.sin(a0), 0)) * 0.22 * M, c + Vector((math.cos(a1), math.sin(a1), 0)) * 0.22 * M, 0.015 * M, segs=4)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (-14 * M, -30 * M, 7 * M), (0, 0, 3 * M), 26), ("02_aerial", (22 * M, -26 * M, 24 * M), (0, 0, 0), 28),
            ("03_garage", (12 * M, -16 * M, 4 * M), (3 * M, 0, 2.5 * M), 24)]


# ---------------------------------------------------------------- Store
def store():
    LW, LD = 26 * M, 26 * M
    X0, X1, Y0, Y1, H = -11 * M, 11 * M, 1 * M, 13 * M, 4.6 * M
    PT = 6.0 * M
    K.boxr("Asphalt", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Concrete", X0 - 0.5 * M, X1 + 0.5 * M, Y0 - 2.2 * M, Y0, 0, 0.18 * M)    # walk in front
    K.boxr("Walls", X0, X1, Y0, Y1, 0, H)
    K.boxr("Walls", X0, X1, Y0, Y0 + 0.35 * M, H, PT)                                 # tall front parapet
    for (a0, a1, b0, b1) in ((X0, X0 + 0.3 * M, Y0, Y1), (X1 - 0.3 * M, X1, Y0, Y1), (X0, X1, Y1 - 0.3 * M, Y1)):
        K.boxr("Walls", a0, a1, b0, b1, H, H + 0.6 * M)
    K.boxr("Trim", X0 - 0.05, X1 + 0.05, Y0 - 0.05, Y0 + 0.4 * M, PT, PT + 0.12 * M)
    K.boxr("Flat", X0 + 0.3, X1 - 0.3, Y0 + 0.3, Y1 - 0.3, H, H + 0.06)
    K.face_y("StoreSign", 0, Y0 - 0.05, 3.5 * M, 19.2 * M, 2.4 * M)
    K.boxr("Dark", -9.8 * M, 9.8 * M, Y0 - 0.35 * M, Y0 - 0.05, 3.4 * M, 3.48 * M)  # sign ledge
    for lx in (-7, -2.4, 2.4, 7):
        K.box("Sconce", (lx * M, Y0 - 0.55 * M, 6.05 * M), (0.6 * M, 0.25 * M, 0.12 * M))   # sign lights
        K.cyl_along("Iron", (lx * M, Y0 - 0.02, 5.95 * M), (lx * M, Y0 - 0.55 * M, 6.05 * M), 0.02 * M, segs=4)
    K.face_y("StoreFront", -2.5 * M, Y0 - 0.04, 0.18 * M, 9.0 * M, 3.2 * M)
    K.face_y("StoreDoor", 4.6 * M, Y0 - 0.04, 0.18 * M, 1.6 * M, 2.6 * M)
    K.boxr("Dark", 3.7 * M, 5.5 * M, Y0 - 0.1 * M, Y0, 2.78 * M, 2.9 * M)
    K.face_y("BarWindow", 7.8 * M, Y0 - 0.04, 1.0 * M, 2.2 * M, 2.0 * M)
    K.box("NeonCyan", (7.8 * M, Y0 - 0.07 * M, 2.55 * M), (1.4 * M, 0.04 * M, 0.08 * M))
    K.box("NeonCyan", (7.8 * M, Y0 - 0.07 * M, 2.05 * M), (1.4 * M, 0.04 * M, 0.08 * M))
    # rolled shutter boxes over the glass
    K.boxr("Pole", -7.1 * M, 2.1 * M, Y0 - 0.3 * M, Y0, 3.0 * M, 3.38 * M)
    # bollards in front of the glass
    for bx in (-6.5, -4, -1.5, 1, 6.5, 9):
        K.cyl("Yellow", (bx * M, Y0 - 1.6 * M, 0.6 * M), 0.12 * M, 1.2 * M, segs=10)
    # ice box, payphone, news boxes
    K.boxr("IceBox", X0 + 0.4 * M, X0 + 2.6 * M, Y0 - 1.1 * M, Y0 - 0.05, 0.18 * M, 1.9 * M)
    K.boxr("IceBlue", X0 + 0.4 * M, X0 + 2.6 * M, Y0 - 1.12 * M, Y0 - 1.08 * M, 1.3 * M, 1.7 * M)
    K.boxr("Dark", X0 + 0.5 * M, X0 + 2.5 * M, Y0 - 1.13 * M, Y0 - 1.1 * M, 0.4 * M, 1.15 * M)
    K.box("Pole", (X0 + 3.4 * M, Y0 - 0.25 * M, 1.4 * M), (0.6 * M, 0.4 * M, 0.9 * M))
    K.box("Dark", (X0 + 3.4 * M, Y0 - 0.46 * M, 1.4 * M), (0.4 * M, 0.04 * M, 0.6 * M))
    K.box("Pole", (X0 + 3.4 * M, Y0 - 0.15 * M, 0.5 * M), (0.12 * M, 0.12 * M, 1.0 * M))
    for i, part in enumerate(("BinBlue", "Red", "Yellow")):
        nx = X1 - 1.2 * M - i * 0.65 * M
        K.box(part, (nx, Y0 - 0.5 * M, 0.75 * M), (0.5 * M, 0.45 * M, 0.7 * M))
        K.box("Dark", (nx, Y0 - 0.73 * M, 0.85 * M), (0.38 * M, 0.02, 0.3 * M))
        K.box("Pole", (nx, Y0 - 0.5 * M, 0.3 * M), (0.08 * M, 0.08 * M, 0.3 * M))
    # cameras + wall lights
    for cx in (X0 + 0.4 * M, X1 - 0.4 * M):
        K.box("Plastic", (cx, Y0 - 0.3 * M, 3.2 * M), (0.18 * M, 0.4 * M, 0.18 * M))
        K.box("Dark", (cx, Y0 - 0.51 * M, 3.2 * M), (0.1 * M, 0.02, 0.1 * M))
    for sy in (4 * M, 10 * M):
        K.box("Sconce", (X1 + 0.1 * M, sy, 3.6 * M), (0.16 * M, 0.3 * M, 0.2 * M))
        K.box("Sconce", (X0 - 0.1 * M, sy, 3.6 * M), (0.16 * M, 0.3 * M, 0.2 * M))
    # big side tag + barred side windows
    tag(X1, "x", 7.6 * M, 0.6 * M, 8.0 * M, 3.0 * M, 1)
    window(("x", X0, -1), 4.5 * M, 1.6 * M, w=1.6 * M, h=1.2 * M)
    K.face_y("SecurityDoor", 6 * M, Y1 + 0.04, 0, 1.05 * M, 2.2 * M, facing=1)
    K.box("Sconce", (7.2 * M, Y1 + 0.08 * M, 2.6 * M), (0.25 * M, 0.16 * M, 0.2 * M))
    # roof units
    for (cx, cy) in ((-6 * M, 8 * M), (2 * M, 9 * M), (7 * M, 6 * M)):
        K.box("AcBody", (cx, cy, H + 0.5 * M), (1.6 * M, 1.3 * M, 1.0 * M))
        K.cyl("Dark", (cx, cy, H + 1.01 * M), 0.5 * M, 0.03, segs=12)
    # parking: 6 stalls in front, wheel stops, a handicap-free plain lot
    for i in range(7):
        sx = -8.4 * M + i * 2.8 * M
        K.boxr("Paint", sx - 0.06 * M, sx + 0.06 * M, -4.5 * M, Y0 - 2.4 * M, 0, 0.03)
    for i in range(6):
        sx = -7.0 * M + i * 2.8 * M
        K.box("WheelStop", (sx, Y0 - 2.9 * M, 0.08 * M), (1.8 * M, 0.25 * M, 0.16 * M))
    # dumpster + side alley
    K.boxr("Dumpster", X1 + 0.4 * M, X1 + 1.8 * M, Y1 - 3.4 * M, Y1 - 1.2 * M, 0.15 * M, 1.4 * M)
    K.boxr("Dark", X1 + 0.38 * M, X1 + 1.82 * M, Y1 - 3.45 * M, Y1 - 1.15 * M, 1.4 * M, 1.48 * M)
    for dy in (Y1 - 3.2 * M, Y1 - 1.4 * M):
        for dx in (X1 + 0.5 * M, X1 + 1.7 * M):
            K.cyl("Dark", (dx, dy, 0.08 * M), 0.08 * M, 0.1 * M, segs=6, axis='Y')
    bins(X0 - 1.5 * M, Y1 - 1.0 * M, 2)
    lamp_post(-12 * M, -12 * M, arm=(1, 0))
    lamp_post(12 * M, -12 * M, arm=(-1, 0))
    planter(-12 * M, -1 * M, 1.6 * M, 3 * M, palm=True)
    planter(12 * M, -1 * M, 1.6 * M, 3 * M, palm=True)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (12 * M, -34 * M, 6 * M), (0, 2 * M, 3 * M), 26), ("02_aerial", (30 * M, -30 * M, 26 * M), (0, 0, 0), 28),
            ("03_side", (28 * M, 4 * M, 4 * M), (10 * M, 6 * M, 2 * M), 24)]


# ---------------------------------------------------------------- Court
def court():
    LW, LD = 32 * M, 26 * M
    FX, FY = 15.5 * M, 12.5 * M
    K.boxr("Asphalt", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.quad("CourtPaint", [(-14 * M, -7.5 * M, 0.03), (14 * M, -7.5 * M, 0.03), (14 * M, 7.5 * M, 0.03), (-14 * M, 7.5 * M, 0.03)])
    for sx in (-1, 1):
        bx = sx * 12.8 * M
        K.cyl("Pole", (sx * 14.9 * M, 0, 1.8 * M), 0.12 * M, 3.6 * M, segs=12)
        K.box("Pole", (sx * 14.9 * M, 0, 0.12 * M), (0.6 * M, 0.6 * M, 0.24 * M))
        K.cyl_along("Pole", (sx * 14.9 * M, 0, 3.4 * M), (bx + sx * 0.08 * M, 0, 3.4 * M), 0.07 * M, segs=8)
        K.cyl_along("Pole", (sx * 14.9 * M, 0, 2.6 * M), (bx + sx * 0.08 * M, 0, 3.2 * M), 0.05 * M, segs=6)
        K.face_x("Backboard", bx - sx * 0.03, 0, 2.9 * M, 1.8 * M, 1.1 * M, facing=-sx)
        K.face_x("Backboard", bx + sx * 0.03, 0, 2.9 * M, 1.8 * M, 1.1 * M, facing=sx)
        c = Vector((bx - sx * 0.42 * M, 0, 3.05 * M))
        for i in range(14):
            a0, a1 = i / 14 * math.tau, (i + 1) / 14 * math.tau
            K.cyl_along("Rim", c + Vector((math.cos(a0), math.sin(a0), 0)) * 0.23 * M,
                        c + Vector((math.cos(a1), math.sin(a1), 0)) * 0.23 * M, 0.018 * M, segs=4)
        K.box("Rim", (bx - sx * 0.12 * M, 0, 3.05 * M), (0.2 * M, 0.2 * M, 0.04 * M))
        for i in range(8):     # chain net
            a = i / 8 * math.tau
            K.cyl_along("Net", c + Vector((math.cos(a), math.sin(a), 0)) * 0.23 * M,
                        c + Vector((math.cos(a + 0.5) * 0.13 * M, math.sin(a + 0.5) * 0.13 * M, -0.45 * M)), 0.008 * M, segs=3)
    # fence: chain link front + sides (gate in the middle of the front), block wall at the back
    chain_fence(-FX, -FY, -2 * M, -FY)
    chain_fence(2 * M, -FY, FX, -FY)
    chain_fence(-FX, -FY, -FX, FY)
    chain_fence(FX, -FY, FX, FY)
    for gx in (-2 * M, 2 * M):
        K.cyl("Pole", (gx, -FY, 1.9 * M), 0.09 * M, 3.8 * M, segs=8)
    K.cyl_along("Pole", (-2 * M, -FY, 3.55 * M), (2 * M, -FY, 3.55 * M), 0.05 * M, segs=6)
    K.boxr("Block", -FX - 0.1 * M, FX + 0.1 * M, FY - 0.2 * M, FY + 0.2 * M, 0, 2.6 * M)
    K.boxr("Stone", -FX - 0.15 * M, FX + 0.15 * M, FY - 0.25 * M, FY + 0.25 * M, 2.6 * M, 2.72 * M)
    for i in range(-5, 6):
        K.box("Block", (i * 3 * M, FY - 0.3 * M, 1.3 * M), (0.5 * M, 0.25 * M, 2.6 * M))
    tag(FY - 0.42 * M, "y", -8 * M, 0.4 * M, 6.4 * M, 2.4 * M, -1)
    tag(FY - 0.42 * M, "y", 7 * M, 0.4 * M, 6.4 * M, 2.4 * M, -1)
    tag(FY + 0.2 * M, "y", 0, 0.3 * M, 7.0 * M, 2.6 * M, 1)
    # benches along the sides, picnic table, lights, bins
    for sy in (-4 * M, 4 * M):
        bench(-14.6 * M, sy, -math.pi / 2)
        bench(14.6 * M, sy, math.pi / 2)
    tx, ty = -10 * M, -10.2 * M
    K.box("Wood", (tx, ty, 0.75 * M), (2.0 * M, 0.8 * M, 0.06 * M))
    for oy in (-0.7 * M, 0.7 * M):
        K.box("Wood", (tx, ty + oy, 0.45 * M), (2.0 * M, 0.3 * M, 0.05 * M))
    for ox in (-0.8 * M, 0.8 * M):
        K.box("Iron", (tx + ox, ty, 0.38 * M), (0.08 * M, 1.6 * M, 0.06 * M))
        K.box("Iron", (tx + ox, ty, 0.4 * M), (0.08 * M, 0.08 * M, 0.75 * M))
    bins(9.0 * M, -11.2 * M, 2)
    lamp_post(-FX + 0.6 * M, -9.5 * M, h=7 * M, arm=(1, 0))
    lamp_post(FX - 0.6 * M, 9.5 * M, h=7 * M, arm=(-1, 0))
    lamp_post(-FX + 0.6 * M, 9.5 * M, h=7 * M, arm=(1, 0))
    lamp_post(FX - 0.6 * M, -9.5 * M, h=7 * M, arm=(-1, 0))
    # a couple of old tyres + a boombox crate by the wall
    for (tx, ty) in ((-13 * M, 10.8 * M), (-12.2 * M, 11.1 * M)):
        K.cyl("Dark", (tx, ty, 0.12 * M), 0.35 * M, 0.24 * M, segs=12)
    K.box("Wood", (12.5 * M, 11 * M, 0.3 * M), (0.8 * M, 0.6 * M, 0.6 * M))
    K.palm(-LW / 2 + 0.2 * M, -LD / 2 + 0.6 * M, 0, 9 * M, (0.3, 0.2), rng)
    K.palm(LW / 2 - 0.2 * M, LD / 2 - 0.4 * M, 0, 10 * M, (-0.3, -0.1), rng)
    VARIANTS["CourtPaint"] = {g: f"CourtPaint{g}_Color.png" for g in GANGS}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (10 * M, -32 * M, 8 * M), (0, 0, 1 * M), 26), ("02_aerial", (0, -28 * M, 34 * M), (0, 0, 0), 30),
            ("03_hoop", (-4 * M, -5 * M, 2 * M), (-12.8 * M, 0, 3 * M), 24)]


# ---------------------------------------------------------------- SpawnPlaza
def spawn_plaza():
    W, D = 44 * M, 40 * M
    K.boxr("Pave", -W / 2, W / 2, -D / 2, D / 2, -0.6, 0)
    K.boxr("Kerb", -W / 2, W / 2, -D / 2, -D / 2 + 0.3 * M, 0, 0.03)
    # fountain: ring wall, floor, water, tiered column
    R0 = 4.2 * M
    K.cyl("Stone", (0, 0, 0.1 * M), R0 + 0.3 * M, 0.2 * M, segs=32)
    seg = 28
    for i in range(seg):
        a = (i + 0.5) / seg * math.tau
        K.box("Stone", (math.cos(a) * R0, math.sin(a) * R0, 0.45 * M), (0.55 * M, 2 * math.pi * R0 / seg + 0.05 * M, 0.9 * M), rz=a)
        K.box("Stone", (math.cos(a) * R0, math.sin(a) * R0, 0.93 * M), (0.75 * M, 2 * math.pi * R0 / seg + 0.08 * M, 0.08 * M), rz=a)
    K.cyl("Tile", (0, 0, 0.25 * M), R0 - 0.2 * M, 0.1 * M, segs=32)
    K.cyl("Water", (0, 0, 0.7 * M), R0 - 0.26 * M, 0.04, segs=32)
    K.cyl("Stone", (0, 0, 1.5 * M), 0.45 * M, 2.0 * M, segs=16)
    K.cyl("Stone", (0, 0, 2.2 * M), 1.8 * M, 0.35 * M, segs=24, r2=0.6 * M)
    K.cyl("Water", (0, 0, 2.39 * M), 1.6 * M, 0.04, segs=24)
    K.cyl("Stone", (0, 0, 2.9 * M), 0.25 * M, 1.0 * M, segs=12)
    K.cyl("Stone", (0, 0, 3.45 * M), 0.9 * M, 0.25 * M, segs=20, r2=0.3 * M)
    K.cyl("Water", (0, 0, 3.6 * M), 0.8 * M, 0.04, segs=20)
    K.cyl("Stone", (0, 0, 3.85 * M), 0.12 * M, 0.5 * M, segs=8)
    # benches ring
    for i in range(10):
        a = i / 10 * math.tau + math.pi / 10
        if abs(math.sin(a)) > 0.95:
            continue
        rr = 7.2 * M
        bench(math.cos(a) * rr, math.sin(a) * rr, a + math.pi / 2)
    # paving ring + paths
    K.cyl("Stone", (0, 0, 0.005), 8.6 * M, 0.02, segs=40)
    # planters with palms in the corners + shrub beds
    for sx in (-1, 1):
        for sy in (-1, 1):
            planter(sx * 16 * M, sy * 14 * M, 3.2 * M, 3.2 * M, palm=True)
        planter(sx * 16 * M, 0, 2.4 * M, 6 * M, palm=False)
    for sx in (-1, 1):
        planter(sx * 8 * M, 16.5 * M, 6 * M, 2 * M, palm=False)
    # WELCOME monument (left of centre, faces the avenue) + uplights
    mx, my = -11 * M, -16.5 * M
    K.boxr("Stone", mx - 4.6 * M, mx + 4.6 * M, my - 0.4 * M, my + 0.4 * M, 0, 2.7 * M)
    K.boxr("Trim", mx - 4.75 * M, mx + 4.75 * M, my - 0.5 * M, my + 0.5 * M, 2.7 * M, 2.85 * M)
    K.face_y("WelcomeSign", mx, my - 0.43 * M, 0.45 * M, 8.0 * M, 2.0 * M)
    K.face_y("WelcomeSign", mx, my + 0.43 * M, 0.45 * M, 8.0 * M, 2.0 * M, facing=1)
    for lx in (-3, -1, 1, 3):
        K.box("Light", (mx + lx * M, my - 1.2 * M, 0.08 * M), (0.4 * M, 0.25 * M, 0.16 * M))
    K.boxr("Soil", mx - 4.6 * M, mx + 4.6 * M, my - 1.5 * M, my - 0.4 * M, 0, 0.06 * M)
    for i in range(6):
        K.shrub(mx + (i - 2.5) * 1.5 * M, my - 0.9 * M, 0, 0.35 * M, rng)
    # bus shelter (right of centre on the kerb)
    sx0, sy0 = 11 * M, -18.3 * M
    K.boxr("Pole", sx0 - 3 * M, sx0 + 3 * M, sy0 + 0.3 * M, sy0 + 1.9 * M, 2.6 * M, 2.72 * M)
    for px in (sx0 - 2.9 * M, sx0 + 2.9 * M):
        K.boxr("Pole", px - 0.06 * M, px + 0.06 * M, sy0 + 1.7 * M, sy0 + 1.82 * M, 0, 2.6 * M)
        K.boxr("Pole", px - 0.06 * M, px + 0.06 * M, sy0 + 0.4 * M, sy0 + 0.52 * M, 0, 2.6 * M)
    K.boxr("Glass", sx0 - 2.9 * M, sx0 + 1.6 * M, sy0 + 1.74 * M, sy0 + 1.78 * M, 0.3 * M, 2.5 * M)
    K.boxr("Pole", sx0 + 1.6 * M, sx0 + 2.9 * M, sy0 + 1.7 * M, sy0 + 1.82 * M, 0.2 * M, 2.4 * M)
    K.face_y("ShelterAd", sx0 + 2.25 * M, sy0 + 1.68 * M, 0.35 * M, 1.2 * M, 2.0 * M)
    K.face_y("ShelterAd", sx0 + 2.25 * M, sy0 + 1.84 * M, 0.35 * M, 1.2 * M, 2.0 * M, facing=1)
    K.boxr("Wood", sx0 - 2.4 * M, sx0 + 1.2 * M, sy0 + 1.2 * M, sy0 + 1.6 * M, 0.45 * M, 0.52 * M)
    for bx in (sx0 - 2.2 * M, sx0 + 1.0 * M):
        K.box("Iron", (bx, sy0 + 1.4 * M, 0.22 * M), (0.08 * M, 0.35 * M, 0.45 * M))
    K.box("Light", (sx0, sy0 + 1.1 * M, 2.58 * M), (4.5 * M, 0.15 * M, 0.04 * M))
    K.cyl("Pole", (sx0 - 4 * M, sy0 + 0.2 * M, 1.5 * M), 0.05 * M, 3.0 * M, segs=6)       # bus stop sign
    K.box("BinBlue", (sx0 - 4 * M, sy0 + 0.17 * M, 2.7 * M), (0.6 * M, 0.04 * M, 0.6 * M))
    # route map kiosk
    kx, ky = 4.5 * M, -14 * M
    K.box("Dark", (kx, ky, 1.1 * M), (1.5 * M, 0.35 * M, 2.2 * M))
    K.face_y("RouteMap", kx, ky - 0.2 * M, 0.7 * M, 1.25 * M, 1.25 * M)
    K.face_y("RouteMap", kx, ky + 0.2 * M, 0.7 * M, 1.25 * M, 1.25 * M, facing=1)
    K.box("Light", (kx, ky, 2.25 * M), (1.5 * M, 0.35 * M, 0.1 * M))
    # bollards along the kerb, lamps, flagpoles at the back, bins
    for i in range(-10, 11):
        bx = i * 2 * M
        if abs(bx - sx0) < 3.5 * M or abs(bx - mx) < 5.2 * M:
            continue
        K.cyl("Pole", (bx, -D / 2 + 0.8 * M, 0.5 * M), 0.12 * M, 1.0 * M, segs=10)
        K.cyl("Trim", (bx, -D / 2 + 0.8 * M, 0.85 * M), 0.13 * M, 0.08 * M, segs=10)
    for (lx, ly) in ((-20 * M, -8 * M), (20 * M, -8 * M), (-20 * M, 8 * M), (20 * M, 8 * M), (-5 * M, -12 * M), (5 * M, 12 * M)):
        lamp_post(lx, ly, arm=(0, -1) if ly > 0 else (0, 1))
    for i, fx in enumerate((-3 * M, 0, 3 * M)):
        K.cyl("Pole", (fx, 18.5 * M, 5 * M), 0.07 * M, 10 * M, segs=8)
        K.cyl("Trim", (fx, 18.5 * M, 10.05 * M), 0.12 * M, 0.12 * M, segs=8)
        part = ("Flag", "IceBlue", "Red")[i]
        K.box(part, (fx + 1.1 * M, 18.5 * M, 9.0 * M), (2.1 * M, 0.04 * M, 1.3 * M))
    K.boxr("Stone", -4 * M, 4 * M, 17.8 * M, 19.2 * M, 0, 0.3 * M)
    for (bx, by) in ((-8 * M, -10 * M), (8 * M, 10 * M), (-8 * M, 10 * M)):
        K.cyl("BinGrey", (bx, by, 0.5 * M), 0.3 * M, 1.0 * M, segs=12)
    # compass inlay where players spawn (between the fountain and the avenue)
    K.cyl("Paint", (0, -11 * M, 0.01), 2.2 * M, 0.02, segs=32)
    K.cyl("Stone", (0, -11 * M, 0.02), 1.9 * M, 0.02, segs=32)
    for i in range(8):
        a = i / 8 * math.tau
        ln = (1.7 if i % 2 == 0 else 1.0) * M
        K.box("Yellow", (math.cos(a) * ln / 2, -11 * M + math.sin(a) * ln / 2, 0.04), (ln, 0.22 * M, 0.03), rz=a)
    return [("01_front", (0, -46 * M, 10 * M), (0, 0, 2 * M), 24), ("02_aerial", (30 * M, -36 * M, 34 * M), (0, 0, 0), 26),
            ("03_monument", (-6 * M, -28 * M, 2.5 * M), (-11 * M, -16.5 * M, 1.6 * M), 26)]


shots = {"HouseA": house_a, "HouseB": house_b, "Store": store, "Court": court, "SpawnPlaza": spawn_plaza}[ONLY]()

K.finish(face=A["face"])
meta = K.export()
if VARIANTS:
    meta["variants"] = VARIANTS
    for part, opts in VARIANTS.items():
        for fn in opts.values():
            shutil.copyfile(os.path.join(TEX, fn), os.path.join(K.tex, fn))
    json.dump(meta, open(os.path.join(A["out"], "meta.json"), "w"), indent=1)
if A["render"] and A["face"] == "N":
    K.render_setup(A["samples"], A["res"])
    for name, loc, target, lens in shots:
        K.shot(name, loc, target, lens=lens)
