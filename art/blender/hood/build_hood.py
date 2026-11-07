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
rng = random.Random({"HouseA": 1, "HouseB": 2, "Store": 3, "Court": 4, "SpawnPlaza": 5, "HouseC": 6, "HouseD": 7, "SideYard": 8}[ONLY])

PALETTES = ("Cream", "Sand", "Sky", "Rose", "Brick", "Blush", "Butter", "Tan", "Peach", "Mint", "Sage", "Teal")
GANGS = ("RedCrowns", "Vipers", "GroveKings")   # original gang names, see tools/hood_textures.py
VARIANTS = {}

# ---------------------------------------------------------------- materials
K.mat("Walls", sheet="WallCream" if ONLY != "Store" else "WallSand", tile=(3.5 * M, 3.5 * M))
for name, sheet, tile in (("Lawn", "Lawn", (3 * M, 3 * M)), ("Concrete", "Concrete", (3 * M, 3 * M)),
                          ("Asphalt", "Asphalt", (8 * M, 8 * M)), ("Roof", "Shingles", (2.5 * M, 2.5 * M)),
                          ("Pave", "PlazaPave", (4 * M, 4 * M)), ("ShopFloor", "ShopFloor", (2.4 * M, 2.4 * M)),
                          ("Ceiling", "Ceiling", (2.4 * M, 2.4 * M)), ("Water", "Water", (3 * M, 3 * M)),
                          ("Tiles", "ClayTile", (2 * M, 2 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("BusSign", "Timetable", "BusDisplay", "BusFascia", "BinLabel", "MeterFace", "FridgeDoors", "ShelfGoodsA", "ShelfGoodsB", "CandyRack", "IceFront", "Register", "Coffee", "AtmFace", "FreezerTop",
             "PosterSoda", "PosterSnack", "PosterCoffee", "PosterOpen", "AcGrille", "NewsFace", "BarWindow", "SecurityDoor", "GarageDoor", "StoreFront", "StoreSign", "StoreDoor", "Backboard",
             "WelcomeSign", "ShelterAd", "RouteMap"):
    K.mat(name, sheet=name, explicit=True)
K.mat("CourtPaint", sheet="CourtPaint", explicit=True)
K.mat("Tag", sheet="Tag", explicit=True, alpha=True)
K.mat("ChainLink", sheet="ChainLink", explicit=True, alpha=True, metal=0.6, rough=0.4)
# fountain water: flipbook-animated in game (Client/FountainFx swaps the TextureID frames)
K.mat("FxPool", sheet="FxPool", explicit=True, rough=0.05)
K.mat("FxFall", sheet="FxFall", explicit=True, alpha=True, rough=0.05)
K.mat("FxRipple", sheet="FxRipple", explicit=True, alpha=True, rough=0.05)
K.mat("FxJet", color=(0.80, 0.90, 0.95), rough=0.05)
for name, col, rough, metal, emit in (
        ("Trim", (0.93, 0.92, 0.88), 0.6, 0, 0), ("Iron", (0.03, 0.03, 0.035), 0.45, 0.6, 0), ("Foundation", (0.55, 0.54, 0.51), 0.9, 0, 0),
        ("Flat", (0.30, 0.30, 0.29), 0.95, 0, 0), ("AcBody", (0.80, 0.79, 0.75), 0.6, 0.2, 0), ("Dark", (0.06, 0.06, 0.07), 0.5, 0.2, 0),
        ("BinGreen", (0.10, 0.26, 0.14), 0.6, 0, 0), ("BinGrey", (0.22, 0.23, 0.24), 0.6, 0, 0), ("BinBlue", (0.10, 0.22, 0.48), 0.6, 0, 0),
        ("Mailbox", (0.85, 0.85, 0.82), 0.4, 0.5, 0), ("Pole", (0.55, 0.56, 0.57), 0.4, 0.9, 0), ("Wood", (0.42, 0.28, 0.17), 0.85, 0, 0),
        ("Paint", (0.94, 0.94, 0.90), 0.7, 0, 0), ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("WheelStop", (0.75, 0.74, 0.70), 0.9, 0, 0),
        ("Rim", (0.95, 0.35, 0.05), 0.4, 0.6, 0), ("Net", (0.95, 0.95, 0.95), 0.8, 0, 0), ("Block", (0.62, 0.61, 0.58), 0.95, 0, 0),
        ("Stone", (0.80, 0.77, 0.70), 0.8, 0, 0), ("Glass", (0.45, 0.58, 0.62), 0.1, 0.3, 0), ("IceBox", (0.94, 0.95, 0.97), 0.4, 0.2, 0),
        ("IceBlue", (0.10, 0.40, 0.80), 0.5, 0, 0), ("Red", (0.70, 0.08, 0.08), 0.5, 0.1, 0), ("Dumpster", (0.10, 0.30, 0.16), 0.6, 0.3, 0),
        ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("NeonRed", (1.0, 0.15, 0.12), 0.5, 0, 6.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0), ("NeonCyan", (0.2, 0.95, 1.0), 0.5, 0, 6.0),
        ("Shrub", (0.12, 0.29, 0.10), 0.85, 0, 0), ("Palm", (0.13, 0.29, 0.09), 0.7, 0, 0), ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0),
        ("Soil", (0.18, 0.12, 0.08), 1.0, 0, 0), ("Kerb", (0.62, 0.62, 0.60), 0.9, 0, 0), ("Flag", (0.85, 0.85, 0.82), 0.8, 0, 0),
        ("Tile", (0.16, 0.42, 0.55), 0.3, 0, 0), ("Plastic", (0.92, 0.92, 0.90), 0.5, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
for name, col in (("Agave", (0.32, 0.45, 0.38)), ("Grass", (0.36, 0.42, 0.20)), ("Shutter", (0.16, 0.24, 0.22)), ("Leaf", (0.11, 0.24, 0.08)), ("LeafB", (0.17, 0.30, 0.10)),
                  ("Bark", (0.25, 0.19, 0.14)), ("FlowerR", (0.75, 0.10, 0.15)), ("FlowerY", (0.95, 0.75, 0.15)),
                  ("FlowerW", (0.92, 0.90, 0.88)), ("Picket", (0.92, 0.91, 0.87)), ("Hedge", (0.09, 0.20, 0.07))):
    K.mat(name, color=col, rough=0.8)
K.mat("DecoPaint", color=(0.90, 0.88, 0.80), rough=0.8)
K.mat("DecoSkirt", color=(0.22, 0.20, 0.19), rough=0.6)
K.mat("Counter", color=(0.55, 0.36, 0.23), rough=0.4)
# realistic surface sheets (tools/hood_textures.py SURF: Mat<Name>) replace the flat colours
SURF_TILE = {"Foundation": (1.6 * M, 0.8 * M), "Block": (0.8 * M, 0.4 * M), "Flat": (2 * M, 2 * M), "Stone": (1.5 * M, 1.5 * M),
             "Wood": (1.2 * M, 1.2 * M), "Picket": (0.6 * M, 0.6 * M), "Bark": (0.6 * M, 0.6 * M), "Soil": (1 * M, 1 * M),
             "DecoPaint": (2.5 * M, 2.5 * M), "Counter": (1.2 * M, 1.2 * M)}
for _name in list(K.mats):
    if os.path.exists(os.path.join(TEX, f"Mat{_name}_Color.png")):
        K.mat(_name, sheet=f"Mat{_name}", tile=SURF_TILE.get(_name, (1.5 * M, 1.5 * M)), rough=0.6)
K.facade_mats()
_g = K.mats["Glass"]["mat"]          # see-through shop glass in the renders (in game: ClearGlass* parts, CityBuildings)
_g.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.18
_g.surface_render_method = 'DITHERED'


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


def frustum(part, cx, cy, z0, z1, w0, d0, w1, d1, mat=None):
    """Box that tapers from w0 x d0 at z0 to w1 x d1 at z1 (closed)."""
    bm = K.bm(part, mat)
    lo = [bm.verts.new((cx + sx * w0 / 2, cy + sy * d0 / 2, z0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    hi = [bm.verts.new((cx + sx * w1 / 2, cy + sy * d1 / 2, z1)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])


def bins(x, y, n=2):
    """Wheelie bins facing the street (-Y): tapered body, ribs, overhanging lid with hinge and
    handle at the back, axle + two wheels, city sticker on the front."""
    for i in range(n):
        bx = x + i * 0.8 * M
        part = ("BinGreen", "BinGrey", "BinBlue")[i % 3]
        frustum(part, bx, y, 0.12 * M, 1.0 * M, 0.56 * M, 0.6 * M, 0.64 * M, 0.72 * M)
        for k in (-1, 1):                                            # corner ribs
            K.boxr(part, bx + k * 0.3 * M - 0.02 * M, bx + k * 0.3 * M + 0.02 * M, y - 0.37 * M, y - 0.31 * M, 0.2 * M, 0.98 * M)
        K.boxr(part, bx - 0.33 * M, bx + 0.33 * M, y - 0.38 * M, y - 0.34 * M, 0.9 * M, 0.97 * M)   # top rim
        K.boxr(part, bx - 0.34 * M, bx + 0.34 * M, y - 0.42 * M, y + 0.36 * M, 1.0 * M, 1.06 * M)  # lid
        K.boxr(part, bx - 0.3 * M, bx + 0.3 * M, y - 0.44 * M, y - 0.4 * M, 0.96 * M, 1.06 * M)   # lid lip
        K.cyl("Dark", (bx, y + 0.37 * M, 1.02 * M), 0.03 * M, 0.6 * M, segs=6, axis='X')          # hinge
        K.cyl("Dark", (bx, y + 0.42 * M, 0.92 * M), 0.025 * M, 0.5 * M, segs=6, axis='X')         # handle
        K.cyl("Iron", (bx, y + 0.3 * M, 0.12 * M), 0.02 * M, 0.66 * M, segs=6, axis='X')          # axle
        for wx in (-0.31 * M, 0.31 * M):
            K.cyl("Dark", (bx + wx, y + 0.3 * M, 0.12 * M), 0.12 * M, 0.06 * M, segs=12, axis='X')
            K.cyl("Plastic", (bx + wx * 1.12, y + 0.3 * M, 0.12 * M), 0.05 * M, 0.01 * M, segs=8, axis='X')
        K.face_y("BinLabel", bx, y - 0.335 * M - 0.035 * M, 0.55 * M, 0.34 * M, 0.21 * M)


def meter(ax, plane, facing, a, z):
    """Electric meter cabinet with a printed dial face, conduit down into the ground."""
    K._wbox("Meter", ax, plane, facing, a, 0, 0.08 * M, z, 0.42 * M, 0.16 * M, 0.58 * M)
    if ax == "y":
        K.face_y("MeterFace", a, plane + facing * 0.161 * M, z - 0.28 * M, 0.4 * M, 0.55 * M, facing=facing)
    else:
        K.face_x("MeterFace", plane + facing * 0.161 * M, a, z - 0.28 * M, 0.4 * M, 0.55 * M, facing=facing)
    K._wbox("Pipe", ax, plane, facing, a, 0, 0.06 * M, (z - 0.29 * M) / 2, 0.06 * M, 0.06 * M, z - 0.29 * M)


def ac_unit_x(x, y, z, facing):
    """Through-wall A/C: cabinet, printed grille front, side louvres, brackets, drip line."""
    K.box("AcBody", (x + facing * 0.32 * M, y, z), (0.62 * M, 0.75 * M, 0.5 * M))
    K.face_x("AcGrille", x + facing * 0.632 * M, y, z - 0.23 * M, 0.72 * M, 0.46 * M, facing=facing)
    for k in range(5):
        for sy in (-1, 1):
            K.box("Iron", (x + facing * (0.2 + k * 0.08) * M, y + sy * 0.378 * M, z + 0.05 * M), (0.04 * M, 0.01 * M, 0.3 * M))
    for sy in (-0.28, 0.28):
        K.cyl_along("Iron", (x, y + sy * M, z - 0.55 * M), (x + facing * 0.55 * M, y + sy * M, z - 0.26 * M), 0.02 * M, segs=4)
    K.cyl_along("Pipe", (x + facing * 0.5 * M, y + 0.3 * M, z - 0.25 * M), (x + facing * 0.5 * M, y + 0.3 * M, 0.02), 0.012 * M, segs=4)


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


def tree(x, y, h=7.5 * M, spread=3.2 * M):
    """Leafy shade tree: tapered trunk, three limbs, clumped canopy in two greens."""
    K.cyl("Bark", (x, y, h * 0.25), 0.22 * M, h * 0.5, segs=8, r2=0.16 * M)
    top = Vector((x, y, h * 0.5))
    for i in range(3):
        a = i / 3 * math.tau + rng.uniform(-0.4, 0.4)
        end = top + Vector((math.cos(a) * spread * 0.45, math.sin(a) * spread * 0.45, h * 0.25))
        K.cyl_along("Bark", top, end, 0.09 * M, segs=6)
    for i in range(14):
        a = rng.uniform(0, math.tau)
        r_ = rng.uniform(0, spread * 0.6)
        c = (x + math.cos(a) * r_, y + math.sin(a) * r_, h * rng.uniform(0.62, 0.9))
        K.shrub(c[0], c[1], c[2] - spread * 0.3, rng.uniform(0.26, 0.38) * spread, rng, part="Leaf" if i % 3 else "LeafB", subdiv=2)


def shutters(face, a, z0, w, h):
    """A pair of louvred shutters either side of a window (face as in window())."""
    ax, pos, facing = face
    for side in (-1, 1):
        c = a + side * (w / 2 + 0.3 * M)
        for k in range(5):                       # louvre slats
            z = z0 + (k + 0.5) * h / 5
            if ax == "y":
                K.box("Shutter", (c, pos + facing * 0.05 * M, z), (0.5 * M, 0.06 * M, h / 5 - 0.03 * M))
            else:
                K.box("Shutter", (pos + facing * 0.05 * M, c, z), (0.06 * M, 0.5 * M, h / 5 - 0.03 * M))


def flower_bed(x0, x1, y0, y1):
    """Edged soil bed with low shrubs and red/yellow/white flowers."""
    e = 0.08 * M                                 # soil sits inside the edging (no shared faces -> no flicker)
    K.boxr("Soil", x0 + e, x1 - e, y0 + e, y1 - e, 0.005 * M, 0.06 * M)
    for (a0, a1, b0, b1) in ((x0, x1, y0, y0 + e), (x0, x1, y1 - e, y1), (x0, x0 + e, y0 + e, y1 - e), (x1 - e, x1, y0 + e, y1 - e)):
        K.boxr("Stone", a0, a1, b0, b1, 0, 0.15 * M)
    n = max(2, int((x1 - x0) / (0.9 * M)))
    for i in range(n):
        sx = x0 + (i + 0.5) * (x1 - x0) / n
        if i % 2 == 0:
            K.shrub(sx, (y0 + y1) / 2, 0.04 * M, 0.32 * M, rng, part="Hedge")
        else:
            for k in range(5):
                fx, fy = sx + rng.uniform(-0.3, 0.3) * M, (y0 + y1) / 2 + rng.uniform(-0.2, 0.2) * M
                K.cyl("Shrub", (fx, fy, 0.15 * M), 0.01 * M, 0.25 * M, segs=3)
                K.shrub(fx, fy, 0.22 * M, 0.07 * M, rng, part=("FlowerR", "FlowerY", "FlowerW")[(i + k) % 3])


def picket_fence(x0, y0, x1, y1, h=1.0 * M, gaps=()):
    """White wooden picket fence along x or y with gate gaps (fractions)."""
    a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
    L = (b - a).length
    d = (b - a) / L
    rz = math.atan2(d.y, d.x)
    n = int(L / (0.14 * M))
    for i in range(n + 1):
        t = i / n
        if any(g0 <= t <= g1 for g0, g1 in gaps):
            continue
        p = a + d * (L * t)
        K.box("Picket", (p.x, p.y, h / 2), (0.09 * M, 0.03 * M, h), rz=rz)
        K.box("Picket", (p.x, p.y, h + 0.03 * M), (0.06 * M, 0.03 * M, 0.06 * M), rz=rz + 0.0)
    cuts = [0.0] + [v for g in gaps for v in g] + [1.0]
    for t0, t1 in zip(cuts[::2], cuts[1::2]):
        pa, pb = a + d * (L * t0), a + d * (L * t1)
        c = (pa + pb) / 2
        for z in (0.25 * M, h - 0.2 * M):
            K.box("Picket", (c.x, c.y, z), ((pb - pa).length, 0.04 * M, 0.08 * M), rz=rz)
        for t in (t0, t1):
            p = a + d * (L * t)
            K.box("Picket", (p.x, p.y, h / 2 + 0.05 * M), (0.12 * M, 0.12 * M, h + 0.1 * M), rz=rz)


def wood_fence(x0, y0, x1, y1, h=1.8 * M):
    """Tall board fence (back and side yards)."""
    a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
    L = (b - a).length
    d = (b - a) / L
    rz = math.atan2(d.y, d.x)
    n = int(L / (0.15 * M))
    for i in range(n):
        p = a + d * (L * (i + 0.5) / n)
        K.box("Wood", (p.x, p.y, h / 2), (0.14 * M, 0.025 * M, h - rng.uniform(0, 0.04) * M), rz=rz)
    for i in range(int(L / (2.4 * M)) + 1):
        p = a + d * min(L, i * 2.4 * M)
        K.box("Wood", (p.x, p.y, h / 2), (0.1 * M, 0.1 * M, h + 0.05 * M), rz=rz)
    for z in (0.3 * M, h - 0.3 * M):
        c = (a + b) / 2
        K.box("Wood", (c.x - d.y * 0.05 * M, c.y + d.x * 0.05 * M, z), (L, 0.04 * M, 0.1 * M), rz=rz)


def gutter(x0, x1, y, z, ax="x"):
    """Eave gutter along x (at y) or along y (at x = y arg)."""
    if ax == "x":
        K.boxr("Trim", x0, x1, y - 0.08 * M, y + 0.08 * M, z - 0.12 * M, z)
    else:
        K.boxr("Trim", y - 0.08 * M, y + 0.08 * M, x0, x1, z - 0.12 * M, z)


def gable(part, x0, x1, y0, y1, z, rh, over=0.45 * M, wall="Walls"):
    """Gable roof with the ridge along X; gable triangles (walls) close both ends."""
    bm = K.bm(part)
    rx0, rx1, ry0, ry1 = x0 - over, x1 + over, y0 - over, y1 + over
    cy = (y0 + y1) / 2
    slope = rh / ((y1 - y0) / 2)
    zl = z - over * slope
    v = [bm.verts.new(p) for p in ((rx0, ry0, zl), (rx1, ry0, zl), (rx1, cy, z + rh), (rx0, cy, z + rh),
                                    (rx1, ry1, zl), (rx0, ry1, zl))]
    bm.faces.new([v[0], v[1], v[2], v[3]]); bm.faces.new([v[3], v[2], v[4], v[5]])
    t = 0.12 * M                              # thickness: underside sheet
    w = [bm.verts.new((p.co.x, p.co.y, p.co.z - t)) for p in v]
    bm.faces.new([w[3], w[2], w[1], w[0]]); bm.faces.new([w[5], w[4], w[2], w[3]])
    for a_, b_ in ((0, 1), (1, 2), (2, 4), (4, 5), (5, 3), (3, 0)):
        bm.faces.new([v[a_], v[b_], w[b_], w[a_]])
    wb = K.bm(wall)
    for x, inw in ((x0, 1), (x1, -1)):           # solid triangular prisms (closed, so normals recalc cleanly)
        xi = x + inw * 0.25 * M
        o = [wb.verts.new(p) for p in ((x, y0, z), (x, y1, z), (x, cy, z + rh - 0.02))]
        i_ = [wb.verts.new(p) for p in ((xi, y0, z), (xi, y1, z), (xi, cy, z + rh - 0.02))]
        wb.faces.new(o); wb.faces.new(i_[::-1])
        for a_, b_ in ((0, 1), (1, 2), (2, 0)):
            wb.faces.new([o[a_], o[b_], i_[b_], i_[a_]])
    for (a0, a1, b0, b1) in ((rx0, rx1, ry0 - 0.03 * M, ry0 + 0.05 * M), (rx0, rx1, ry1 - 0.05 * M, ry1 + 0.03 * M)):
        K.boxr("Trim", a0, a1, b0, b1, zl - 0.25 * M, zl)                          # fascia boards
    K.boxr("Trim", rx0, rx1, cy - 0.1 * M, cy + 0.1 * M, z + rh - 0.02 * M, z + rh + 0.08 * M)   # ridge cap


def lathe(part, prof, segs=32, mat=None):
    """Surface of revolution round the Z axis at (0, 0): prof = [(r, z), ...] from the axis to the axis."""
    bm = K.bm(part, mat)
    rings = []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(i / segs * math.tau), r * math.sin(i / segs * math.tau), z)) for i in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1:
                bm.faces.new([a[0], b[i], b[j]])
            elif len(b) == 1:
                bm.faces.new([a[i], b[0], a[j]])
            else:
                bm.faces.new([a[i], b[i], b[j], a[j]])


def sheet_rev(part, cx, cy, r0, z0, r1, z1, segs=32, urep=6, vrep=1.0, both=True):
    """Open cone/annulus sheet (explicit UVs: u round, v from edge 0 to edge 1) for water FX."""
    for side in ((1, -1) if both else (1,)):
        for i in range(segs):
            a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
            p = [(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0), (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0),
                 (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1), (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)]
            uv = [(i / segs * urep, 0), ((i + 1) / segs * urep, 0), ((i + 1) / segs * urep, vrep), (i / segs * urep, vrep)]
            if side < 0:
                p, uv = p[::-1], uv[::-1]
            K.quad(part, p, uv)


def disc(part, cx, cy, r, z, segs=32, scale=1.0):
    """Flat explicit-UV disc facing up (water surfaces); UVs tile every `scale` studs... in metres."""
    for i in range(segs):
        a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
        p = [(cx, cy, z), (cx + r * math.cos(a0), cy + r * math.sin(a0), z), (cx + r * math.cos(a1), cy + r * math.sin(a1), z)]
        uv = [((q[0] - cx) / (scale * M), (q[1] - cy) / (scale * M)) for q in p]
        bm = K.bm(part)
        uvl = bm.loops.layers.uv.active
        f = bm.faces.new([bm.verts.new(q) for q in p])
        for l, t in zip(f.loops, uv):
            l[uvl].uv = t


def agave(x, y, z, s=0.6 * M, n=14):
    """Spiky succulent rosette."""
    for i in range(n):
        a = i / n * math.tau + rng.uniform(-0.2, 0.2)
        tilt = rng.uniform(0.35, 1.0)
        tip = (x + math.cos(a) * s * tilt, y + math.sin(a) * s * tilt, z + s * (1.1 - tilt * 0.6))
        K.cyl_along("Agave", (x, y, z + 0.02 * M), tip, 0.035 * M * (1.2 - tilt * 0.4), segs=3)


def grass_clump(x, y, z, h=0.7 * M, n=26):
    for i in range(n):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.05, 0.35) * h
        K.cyl_along("Grass", (x + math.cos(a) * 0.04 * M, y + math.sin(a) * 0.04 * M, z),
                    (x + math.cos(a) * r, y + math.sin(a) * r, z + h * rng.uniform(0.6, 1.0)), 0.008 * M, segs=3)


def plaza_planter(x, y, w, d, h=0.65 * M, palm=True):
    """Granite-clad raised planter with an overhanging coping, mulch, and layered planting."""
    K.boxr("Stone", x - w / 2, x + w / 2, y - d / 2, y + d / 2, 0, h - 0.08 * M)
    c = 0.06 * M
    for (a0, a1, b0, b1) in ((x - w / 2 - c, x + w / 2 + c, y - d / 2 - c, y - d / 2 + 0.22 * M),
                             (x - w / 2 - c, x + w / 2 + c, y + d / 2 - 0.22 * M, y + d / 2 + c),
                             (x - w / 2 - c, x - w / 2 + 0.22 * M, y - d / 2 + 0.22 * M, y + d / 2 - 0.22 * M),
                             (x + w / 2 - 0.22 * M, x + w / 2 + c, y - d / 2 + 0.22 * M, y + d / 2 - 0.22 * M)):
        K.boxr("Kerb", a0, a1, b0, b1, h - 0.08 * M, h + 0.02 * M)           # coping (seat height)
    K.boxr("Soil", x - w / 2 + 0.22 * M, x + w / 2 - 0.22 * M, y - d / 2 + 0.22 * M, y + d / 2 - 0.22 * M, h - 0.08 * M, h - 0.04 * M)
    top = h - 0.04 * M
    if palm:
        K.palm(x, y, top, rng.uniform(6.5, 8.5) * M, (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)), rng)
    nx, ny = max(1, int(w / (1.1 * M))), max(1, int(d / (1.1 * M)))
    for i in range(nx):
        for j in range(ny):
            px = x - w / 2 + 0.5 * M + (i + 0.5) * (w - 1.0 * M) / nx
            py = y - d / 2 + 0.5 * M + (j + 0.5) * (d - 1.0 * M) / ny
            if palm and abs(px - x) < 0.6 * M and abs(py - y) < 0.6 * M:
                continue
            k = (i + j) % 3
            if k == 0:
                agave(px, py, top, s=0.45 * M)
            elif k == 1:
                grass_clump(px, py, top)
            else:
                K.shrub(px, py, top, 0.32 * M, rng, part="Leaf", subdiv=2)


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
    for sx in (-5.8, -4.8):
        K.shrub(sx * M, Y0 - 0.9 * M, 0, 0.45 * M, rng)
    flower_bed(-0.6 * M, 3.3 * M, Y0 - 1.3 * M, Y0 - 0.4 * M)
    shutters(front, -1.6 * M, 1.2 * M, 1.4 * M, 1.4 * M)
    shutters(front, 1.6 * M, 1.2 * M, 1.8 * M, 1.4 * M)
    gutter(rx0, rx1, ry0 + 0.05 * M, rz)
    gutter(rx0, rx1, ry1 - 0.05 * M, rz)
    meter("x", X1, 1, 1.0 * M, 1.3 * M)
    K.downpipe(X1 + 0.1 * M, Y0 + 0.1 * M, 0, TOP)
    tree(1.5 * M, -9.0 * M, h=7.0 * M)
    K.boxr("Wood", -7.6 * M, -6.8 * M, 9.5 * M, 12.6 * M, 0, 2.0 * M)                 # back yard tool shed
    gable("Roof", -7.6 * M, -6.8 * M, 9.5 * M, 12.6 * M, 2.0 * M, 0.5 * M, over=0.15 * M, wall="Wood")
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
    tree(-5.0 * M, -8.0 * M, h=8.0 * M, spread=3.6 * M)
    flower_bed(-6.3 * M, -4.2 * M, Y0 - 1.1 * M, Y0 - 0.3 * M)
    flower_bed(-1.8 * M, 1.3 * M, Y0 - 1.1 * M, Y0 - 0.3 * M)
    for a in (-4.8 * M, -1.5 * M):
        shutters(f, a, FZ + FH + 0.8 * M, 1.5 * M, 1.3 * M)
    meter("x", X0, -1, 0.5 * M, 1.3 * M)
    K.downpipe(X0 + 0.12 * M, Y0 - 0.1 * M, 0, TOP)
    for (a0, a1) in ((X1 + 0.1, GX1 - 0.1),):
        gutter(a0, a1, Y0 - 0.05 * M, GH + 0.05 * M)
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


# ---------------------------------------------------------------- HouseC: ranch house, gable roof, carport (20 m lot)
def house_c():
    LW, LD = 20 * M, 26 * M
    X0, X1, Y0, Y1 = -9 * M, 2.5 * M, -5 * M, 4.5 * M
    FZ, TOP = 0.35 * M, 3.1 * M
    K.boxr("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Foundation", X0 - 0.1, X1 + 0.1, Y0 - 0.1, Y1 + 0.1, 0, FZ)
    K.boxr("Walls", X0, X1, Y0, Y1, FZ, TOP)
    K.boxr("Stone", X0 - 0.06 * M, X1 + 0.06 * M, Y0 - 0.06 * M, Y0 + 0.2 * M, FZ, FZ + 0.8 * M)   # stone wainscot (front)
    K.boxr("Stone", X0 - 0.08 * M, X1 + 0.08 * M, Y0 - 0.08 * M, Y0 + 0.2 * M, FZ + 0.8 * M, FZ + 0.88 * M)
    gable("Roof", X0, X1, Y0, Y1, TOP, 1.9 * M)
    # chimney on the west gable end
    K.boxr("Block", X0 - 0.9 * M, X0 + 0.1, -1.2 * M, 0.2 * M, 0, TOP + 2.4 * M)
    K.boxr("Stone", X0 - 1.0 * M, X0 + 0.2 * M, -1.3 * M, 0.3 * M, TOP + 2.4 * M, TOP + 2.55 * M)
    K.boxr("Dark", X0 - 0.6 * M, X0 - 0.2 * M, -0.7 * M, -0.3 * M, TOP + 2.55 * M, TOP + 2.6 * M)
    # entry: door, stoop, little gable canopy on posts
    front = ("y", Y0, -1)
    K.face_y("SecurityDoor", -1.5 * M, Y0 - 0.04, FZ, 1.05 * M, 2.15 * M)
    K.boxr("Concrete", -2.6 * M, -0.4 * M, Y0 - 1.6 * M, Y0, 0, FZ - 0.05)
    K.boxr("Concrete", -2.2 * M, -0.8 * M, Y0 - 2.0 * M, Y0 - 1.6 * M, 0, FZ / 2)
    for px in (-2.5 * M, -0.5 * M):
        K.boxr("Trim", px - 0.08 * M, px + 0.08 * M, Y0 - 1.55 * M, Y0 - 1.4 * M, FZ - 0.05, 2.75 * M)
    K.boxr("Trim", -2.7 * M, -0.3 * M, Y0 - 1.65 * M, Y0, 2.75 * M, 2.9 * M)
    K.boxr("Roof", -2.8 * M, -0.2 * M, Y0 - 1.75 * M, Y0, 2.9 * M, 3.0 * M)
    K.box("Sconce", (-0.7 * M, Y0 - 0.08 * M, 2.4 * M), (0.18 * M, 0.16 * M, 0.26 * M))
    K.box("Meter", (-2.25 * M, Y0 - 0.03 * M, 2.35 * M), (0.4 * M, 0.04 * M, 0.15 * M))   # house number plate
    # windows: picture window with shutters, kitchen window with a flower box
    window(front, -5.2 * M, 1.3 * M, w=2.4 * M, h=1.5 * M)
    shutters(front, -5.2 * M, 1.3 * M, 2.4 * M, 1.5 * M)
    window(front, 0.9 * M, 1.4 * M, w=1.2 * M, h=1.2 * M)
    shutters(front, 0.9 * M, 1.4 * M, 1.2 * M, 1.2 * M)
    K.boxr("Wood", 0.2 * M, 1.6 * M, Y0 - 0.45 * M, Y0 - 0.05, 1.05 * M, 1.3 * M)
    for i in range(4):
        K.shrub(0.35 * M + i * 0.37 * M, Y0 - 0.25 * M, 1.25 * M, 0.14 * M, rng, part=("FlowerR", "Hedge", "FlowerY", "Hedge")[i])
    for a in (-3.5 * M, 2.2 * M):
        window(("x", X0, -1), a, 1.4 * M, w=1.2 * M, h=1.2 * M)
    window(("x", X1, 1), 1.0 * M, 1.4 * M, w=1.2 * M, h=1.2 * M)
    for a in (-6.5 * M, -3.5 * M, 0.5 * M):
        window(("y", Y1, 1), a, 1.3 * M, w=1.3 * M, h=1.3 * M)
    K.face_y("SecurityDoor", -1.8 * M, Y1 + 0.04, FZ, 1.0 * M, 2.1 * M, facing=1)
    gutter(X0 - 0.45 * M, X1 + 0.45 * M, Y0 - 0.45 * M, TOP - 0.45 * M * 1.9 / 4.75)
    gutter(X0 - 0.45 * M, X1 + 0.45 * M, Y1 + 0.45 * M, TOP - 0.45 * M * 1.9 / 4.75)
    for (gx, gy) in ((X0 - 0.4 * M, Y0 - 0.4 * M), (X1 + 0.4 * M, Y1 + 0.4 * M)):
        K.downpipe(gx, gy, 0, TOP - 0.2 * M)
    ac_unit_x(X0, 3.0 * M, 0.4 * M, -1)
    meter("x", X1, 1, -3.5 * M, 1.3 * M)
    tag(X0, "x", -4.6 * M, 1.4 * M, 1.6 * M, 0.8 * M, -1)
    # carport: posts, flat roof, oil-stained pad, bins, workbench
    CX0, CX1, CY0, CY1 = X1, X1 + 5.6 * M, Y0 - 0.4 * M, Y1 - 1.0 * M
    K.boxr("Concrete", CX0, CX1, -LD / 2, CY1, 0, 0.04)
    for (px, py) in ((CX1 - 0.2 * M, CY0 + 0.2 * M), (CX1 - 0.2 * M, CY1 - 0.2 * M), (CX1 - 0.2 * M, (CY0 + CY1) / 2)):
        K.boxr("Trim", px - 0.1 * M, px + 0.1 * M, py - 0.1 * M, py + 0.1 * M, 0, 2.8 * M)
        K.boxr("Stone", px - 0.18 * M, px + 0.18 * M, py - 0.18 * M, py + 0.18 * M, 0, 0.3 * M)
    K.boxr("Flat", CX0, CX1, CY0, CY1, 2.8 * M, 2.95 * M)
    K.boxr("Trim", CX0, CX1 + 0.05 * M, CY0 - 0.05 * M, CY0 + 0.05 * M, 2.7 * M, 3.0 * M)
    K.boxr("Trim", CX1 - 0.05 * M, CX1 + 0.05 * M, CY0, CY1, 2.7 * M, 3.0 * M)
    K.box("Sconce", ((CX0 + CX1) / 2, (CY0 + CY1) / 2, 2.78 * M), (0.6 * M, 0.3 * M, 0.04 * M))
    K.box("Dark", ((CX0 + CX1) / 2, -1.0 * M, 0.045), (1.2 * M, 1.6 * M, 0.01))
    bins(CX0 + 0.6 * M, CY1 - 0.6 * M, 2)
    K.boxr("Wood", CX1 - 2.6 * M, CX1 - 0.6 * M, CY1 - 0.7 * M, CY1 - 0.1 * M, 0.85 * M, 0.95 * M)
    for lx in (CX1 - 2.5 * M, CX1 - 0.7 * M):
        K.boxr("Wood", lx - 0.05 * M, lx + 0.05 * M, CY1 - 0.6 * M, CY1 - 0.2 * M, 0, 0.85 * M)
    # front yard: walk, picket fence with gates, beds, shade tree, mailbox
    K.boxr("Concrete", -2.1 * M, -0.9 * M, -12.6 * M, Y0 - 2.0 * M, 0, 0.04)
    picket_fence(-LW / 2 + 0.1, -12.6 * M, X1 - 0.1 * M, -12.6 * M, gaps=((0.6, 0.72),))
    flower_bed(-8.6 * M, -3.0 * M, Y0 - 1.3 * M, Y0 - 0.4 * M)
    tree(-6.0 * M, -9.4 * M, h=8.5 * M, spread=3.8 * M)
    mailbox(-3.0 * M, -12.2 * M)
    for sx in (-9.3, 1.8):
        K.shrub(sx * M, -11.8 * M, 0, 0.55 * M, rng, part="Hedge")
    # back yard: board fences, patio with table + umbrella, swing set
    wood_fence(-LW / 2 + 0.1, Y0, -LW / 2 + 0.1, LD / 2 - 0.1)
    wood_fence(-LW / 2 + 0.1, LD / 2 - 0.1, LW / 2 - 0.1, LD / 2 - 0.1)
    wood_fence(LW / 2 - 0.1, CY1, LW / 2 - 0.1, LD / 2 - 0.1)
    K.boxr("Concrete", -5 * M, 0 * M, Y1, Y1 + 3.2 * M, 0, 0.05)
    K.cyl("Plastic", (-2.5 * M, Y1 + 1.7 * M, 0.72 * M), 0.55 * M, 0.05 * M, segs=16)
    K.cyl("Pole", (-2.5 * M, Y1 + 1.7 * M, 1.1 * M), 0.025 * M, 2.2 * M, segs=6)
    K.cyl("Red", (-2.5 * M, Y1 + 1.7 * M, 2.1 * M), 1.2 * M, 0.35 * M, segs=8, r2=0.05 * M)
    for k in range(4):
        a = k * math.pi / 2
        K.box("Plastic", (-2.5 * M + math.cos(a) * 0.9 * M, Y1 + 1.7 * M + math.sin(a) * 0.9 * M, 0.42 * M), (0.45 * M, 0.45 * M, 0.06 * M))
    sx, sy = -6.5 * M, 10.5 * M
    for dx in (-1.2 * M, 1.2 * M):
        K.cyl_along("Pole", (sx + dx, sy - 0.7 * M, 0), (sx + dx, sy, 2.2 * M), 0.04 * M, segs=6)
        K.cyl_along("Pole", (sx + dx, sy + 0.7 * M, 0), (sx + dx, sy, 2.2 * M), 0.04 * M, segs=6)
    K.cyl_along("Pole", (sx - 1.2 * M, sy, 2.2 * M), (sx + 1.2 * M, sy, 2.2 * M), 0.045 * M, segs=6)
    for dx in (-0.5 * M, 0.5 * M):
        for ddx in (-0.2 * M, 0.2 * M):
            K.cyl_along("Iron", (sx + dx + ddx, sy, 2.2 * M), (sx + dx + ddx, sy, 0.5 * M), 0.01 * M, segs=4)
        K.box("Dark", (sx + dx, sy, 0.48 * M), (0.5 * M, 0.2 * M, 0.04 * M))
    tree(5.5 * M, 9.5 * M, h=7.5 * M)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (12 * M, -32 * M, 6 * M), (0, -2 * M, 2 * M), 26), ("02_aerial", (26 * M, -28 * M, 24 * M), (0, 0, 0), 28),
            ("03_carport", (14 * M, -14 * M, 3 * M), (5 * M, -1 * M, 1.8 * M), 24)]


# ---------------------------------------------------------------- HouseD: Spanish courtyard house, clay tile roof
def house_d():
    LW, LD = 16 * M, 26 * M
    X0, X1, Y0, Y1 = -6.5 * M, 5 * M, -4 * M, 6.5 * M
    FZ, TOP = 0.3 * M, 3.4 * M
    K.boxr("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Foundation", X0 - 0.1, X1 + 0.1, Y0 - 0.1, Y1 + 0.1, 0, FZ)
    K.boxr("Walls", X0, X1, Y0, Y1, FZ, TOP)
    gable("Tiles", X0, X1, Y0, Y1, TOP, 1.3 * M, over=0.4 * M)
    # porch: three stucco piers, beam, tiled shed roof, tile floor
    K.boxr("Stone", -6.3 * M, -0.8 * M, Y0 - 2.4 * M, Y0, 0, FZ)
    for px in (-6.0 * M, -3.55 * M, -1.1 * M):
        K.boxr("Walls", px - 0.22 * M, px + 0.22 * M, Y0 - 2.3 * M, Y0 - 1.86 * M, FZ, 2.75 * M)
        K.boxr("Trim", px - 0.28 * M, px + 0.28 * M, Y0 - 2.36 * M, Y0 - 1.8 * M, 2.55 * M, 2.65 * M)
    K.boxr("Walls", -6.3 * M, -0.8 * M, Y0 - 2.35 * M, Y0, 2.75 * M, 3.05 * M)
    K.boxr("Tiles", -6.45 * M, -0.65 * M, Y0 - 2.55 * M, Y0, 3.05 * M, 3.17 * M)
    K.box("Sconce", (-2.6 * M, Y0 - 0.08 * M, 2.3 * M), (0.18 * M, 0.16 * M, 0.26 * M))
    K.box("Sconce", (-4.5 * M, Y0 - 0.08 * M, 2.3 * M), (0.18 * M, 0.16 * M, 0.26 * M))
    front = ("y", Y0, -1)
    K.face_y("SecurityDoor", -3.55 * M, Y0 - 0.04, FZ, 1.1 * M, 2.2 * M)
    window(front, -5.4 * M, 1.2 * M, w=1.0 * M, h=1.3 * M)
    window(front, -1.7 * M, 1.2 * M, w=1.0 * M, h=1.3 * M)
    window(front, 2.4 * M, 1.1 * M, w=2.0 * M, h=1.5 * M)
    shutters(front, 2.4 * M, 1.1 * M, 2.0 * M, 1.5 * M)
    for a in (-1.5 * M, 3.0 * M):
        window(("x", X0, -1), a, 1.2 * M, w=1.1 * M, h=1.3 * M)
        window(("x", X1, 1), a, 1.2 * M, w=1.1 * M, h=1.3 * M)
    for a in (-4 * M, 0 * M, 3 * M):
        window(("y", Y1, 1), a, 1.2 * M, w=1.2 * M, h=1.3 * M)
    for k in range(3):                                               # clay vent pipes in the gable ends
        for x, fc in ((X0, -1), (X1, 1)):
            K.cyl("Tiles", (x + fc * 0.02, 0.6 * M + (k - 1) * 0.35 * M, TOP + 0.5 * M), 0.08 * M, 0.3 * M, segs=8, axis='X')
    ac_unit_x(X1, -2.0 * M, 2.4 * M, 1)
    meter("x", X1, 1, 1.0 * M, 1.3 * M)
    K.downpipe(X0 - 0.3 * M, Y0 - 0.3 * M, 0, TOP - 0.1 * M)
    # front courtyard wall (stucco, tile cap) with an iron gate, fountain, pots, palms
    WY = -11.5 * M
    G0, G1 = -3.9 * M, -1.5 * M                      # gate piers (centres): wide, open entrance
    for (a0, a1) in ((-LW / 2 + 0.1, G0), (G1, 1.58 * M)):
        K.boxr("Walls", a0, a1, WY - 0.15 * M, WY + 0.15 * M, 0, 1.15 * M)
        K.boxr("Tiles", a0 - 0.05 * M, a1 + 0.05 * M, WY - 0.22 * M, WY + 0.22 * M, 1.15 * M, 1.27 * M)
    for gx in (G0, G1):                               # piers a bit proud of the wall + cap (no shared faces)
        K.boxr("Walls", gx - 0.28 * M, gx + 0.28 * M, WY - 0.28 * M, WY + 0.28 * M, 0, 1.6 * M)
        K.boxr("Tiles", gx - 0.34 * M, gx + 0.34 * M, WY - 0.34 * M, WY + 0.34 * M, 1.6 * M, 1.72 * M)
    # iron gate leaf standing open inward against the right pier
    hx = G1 - 0.3 * M
    for k in range(9):
        K.box("Iron", (hx - 0.03 * M, WY + 0.35 * M + k * 0.13 * M, 0.65 * M), (0.04 * M, 0.04 * M, 1.1 * M))
    for z in (0.15 * M, 0.65 * M, 1.15 * M):
        K.boxr("Iron", hx - 0.06 * M, hx, WY + 0.3 * M, WY + 1.4 * M, z - 0.03 * M, z + 0.03 * M)
    K.boxr("Walls", -LW / 2 + 0.12, -LW / 2 + 0.42 * M, WY + 0.15 * M + 0.01, Y0, 0, 1.12 * M)
    K.boxr("Walls", 1.26 * M, 1.56 * M, WY + 0.15 * M + 0.01, Y0 - 2.6 * M, 0, 1.12 * M)
    tag(WY - 0.15 * M, "y", -5.8 * M, 0.15 * M, 2.2 * M, 0.85 * M, -1)
    K.boxr("Stone", -3.3 * M, -2.1 * M, WY - 0.3 * M, Y0 - 2.4 * M, 0, 0.05)          # path
    K.cyl("Stone", (-4.8 * M, -8.0 * M, 0.3 * M), 0.9 * M, 0.6 * M, segs=16)          # little fountain
    K.cyl("Water", (-4.8 * M, -8.0 * M, 0.615 * M), 0.78 * M, 0.02 * M, segs=16)    # just above the rim top
    K.cyl("Stone", (-4.8 * M, -8.0 * M, 0.9 * M), 0.12 * M, 0.7 * M, segs=8)
    K.cyl("Stone", (-4.8 * M, -8.0 * M, 1.25 * M), 0.35 * M, 0.1 * M, segs=12)
    for (px, py) in ((-0.2 * M, -7.0 * M), (0.6 * M, -9.5 * M), (-6.8 * M, -5.6 * M)):
        K.cyl("Tiles", (px, py, 0.3 * M), 0.3 * M, 0.6 * M, segs=10, r2=0.38 * M)
        K.shrub(px, py, 0.55 * M, 0.35 * M, rng)
    planter(-0.3 * M, -10.4 * M, 1.0 * M, 1.0 * M, h=0.4 * M, palm=False)
    planter(-7.0 * M, -10.6 * M, 1.0 * M, 1.0 * M, h=0.4 * M)
    # driveway along the east side to a wooden double gate
    K.boxr("Concrete", 2.2 * M, 7.6 * M, -LD / 2, Y0 + 1.0 * M, 0, 0.04)
    for gx in (X1 + 0.1 * M, LW / 2 - 0.35 * M):
        K.boxr("Walls", gx, gx + 0.35 * M, Y0 + 1.0 * M, Y0 + 1.35 * M, 0, 2.0 * M)
    gx0, gx1 = X1 + 0.45 * M, LW / 2 - 0.35 * M
    for k in range(int((gx1 - gx0) / (0.16 * M))):
        x = gx0 + (k + 0.5) * 0.16 * M
        K.box("Wood", (x, Y0 + 1.17 * M, 0.95 * M), (0.14 * M, 0.05 * M, 1.7 * M))
    K.boxr("Iron", gx0, gx1, Y0 + 1.1 * M, Y0 + 1.14 * M, 1.5 * M, 1.58 * M)
    mailbox(1.9 * M, -12.2 * M)
    # back yard: block walls, string lights posts, grill, lounge chairs
    K.boxr("Block", -LW / 2, -LW / 2 + 0.2 * M, Y0, LD / 2, 0, 1.8 * M)
    K.boxr("Block", -LW / 2, LW / 2, LD / 2 - 0.2 * M, LD / 2, 0, 1.8 * M)
    K.boxr("Block", LW / 2 - 0.2 * M, LW / 2, Y0 + 1.35 * M, LD / 2, 0, 1.8 * M)
    K.boxr("Stone", -5 * M, 3 * M, Y1, Y1 + 3.5 * M, 0, 0.05)
    for cx in (-3.5 * M, -1.8 * M):
        K.boxr("Wood", cx - 0.35 * M, cx + 0.35 * M, Y1 + 1.0 * M, Y1 + 2.8 * M, 0.25 * M, 0.35 * M)
        K.boxr("Wood", cx - 0.35 * M, cx + 0.35 * M, Y1 + 0.9 * M, Y1 + 1.1 * M, 0.35 * M, 0.85 * M)
    K.box("Dark", (1.8 * M, Y1 + 2.2 * M, 0.85 * M), (1.0 * M, 0.55 * M, 0.3 * M))
    for lx in (1.4 * M, 2.2 * M):
        K.boxr("Iron", lx - 0.03 * M, lx + 0.03 * M, Y1 + 2.1 * M, Y1 + 2.3 * M, 0, 0.7 * M)
    tree(4.5 * M, 10.5 * M, h=7.0 * M)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (-12 * M, -32 * M, 6 * M), (0, -3 * M, 2 * M), 26), ("02_aerial", (22 * M, -26 * M, 22 * M), (0, 0, 0), 28),
            ("03_court", (4 * M, -17 * M, 2.2 * M), (-3.5 * M, -6 * M, 1.4 * M), 26)]


# ---------------------------------------------------------------- SideYard: 6 m gap lot between houses
def side_yard():
    LW, LD = 6 * M, 26 * M
    K.boxr("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    for i in range(7):                                               # hedge along the sidewalk
        K.shrub(-LW / 2 + 0.45 * M + i * 0.85 * M, -12.4 * M, 0, 0.5 * M, rng, part="Hedge")
    tree(0.2 * M, -6.5 * M, h=9.0 * M, spread=4.0 * M)
    K.boxr("Stone", -1.6 * M, -0.8 * M, -11.8 * M, 1.0 * M, 0, 0.05)              # stepping path
    wood_fence(-LW / 2 + 0.1, 1.0 * M, -1.9 * M, 1.0 * M)
    wood_fence(-0.5 * M, 1.0 * M, LW / 2 - 0.1, 1.0 * M)
    for k in range(9):                                               # side gate (ajar)
        K.box("Wood", (-1.85 * M + 0.07 * M, 1.05 * M + k * 0.15 * M, 0.9 * M), (0.025 * M, 0.14 * M, 1.7 * M))
    wood_fence(-LW / 2 + 0.1, LD / 2 - 0.1, LW / 2 - 0.1, LD / 2 - 0.1)
    # small garden shed + compost bin + flowers in the back
    K.boxr("Wood", -2.4 * M, 1.4 * M, 8.5 * M, 11.5 * M, 0, 2.1 * M)
    gable("Roof", -2.4 * M, 1.4 * M, 8.5 * M, 11.5 * M, 2.1 * M, 0.7 * M, over=0.2 * M, wall="Wood")
    K.face_y("SecurityDoor", -0.5 * M, 8.46 * M, 0, 0.9 * M, 1.9 * M)
    K.box("Dark", (2.0 * M, 10.0 * M, 0.5 * M), (0.9 * M, 0.9 * M, 1.0 * M))
    flower_bed(-2.6 * M, 2.6 * M, 4.5 * M, 5.5 * M)
    for (sx, sy) in ((2.0 * M, -2.0 * M), (-2.2 * M, -3.5 * M), (2.1 * M, 3.0 * M)):
        K.shrub(sx, sy, 0, 0.6 * M, rng)
    return [("01_front", (8 * M, -26 * M, 5 * M), (0, -2 * M, 3 * M), 26), ("02_aerial", (14 * M, -20 * M, 18 * M), (0, 0, 0), 28)]


# ---------------------------------------------------------------- Store
def store():
    """Walk-in corner market. Every wall piece, shelf and counter is its own part (own convex
    collision), so the open door, aisles and counter gaps stay walkable in Roblox."""
    LW, LD = 26 * M, 26 * M
    X0, X1, Y0, Y1, H = -11 * M, 11 * M, 1 * M, 13 * M, 4.6 * M
    T = 0.3 * M                       # wall thickness
    PT = 6.0 * M
    YI = Y0 + T                       # inside face of the front wall
    WALLS = []

    def wall(name, x0, x1, y0, y1, z0, z1):
        K.boxr(name, x0, x1, y0, y1, z0, z1, mat="Walls")
        WALLS.append(name)

    K.boxr("Asphalt", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.3, 0)
    K.boxr("Concrete", X0 - 0.5 * M, X1 + 0.5 * M, Y0 - 2.2 * M, Y0, 0, 0.18 * M)    # walk in front
    K.boxr("KerbEdge", X0 - 0.5 * M, X1 + 0.5 * M, Y0 - 2.25 * M, Y0 - 2.1 * M, 0, 0.2 * M, mat="Paint")
    # ---- shell: front wall pieces round two shop windows, the door and a side window
    WIN = (-7.2 * M, 2.0 * M, 0.6 * M, 3.2 * M)       # x0, x1, z0, z1
    DOOR = (3.8 * M, 5.4 * M, 2.6 * M)
    SWIN = (6.7 * M, 8.9 * M, 1.0 * M, 3.0 * M)
    wall("WallF1", X0, WIN[0], Y0, YI, 0, H)
    wall("WallF2", WIN[0], WIN[1], Y0, YI, 0, WIN[2])
    wall("WallF3", WIN[0], WIN[1], Y0, YI, WIN[3], H)
    wall("WallF4", WIN[1], DOOR[0], Y0, YI, 0, H)
    wall("WallF5", DOOR[0], DOOR[1], Y0, YI, DOOR[2], H)
    wall("WallF6", DOOR[1], SWIN[0], Y0, YI, 0, H)
    wall("WallF7", SWIN[0], SWIN[1], Y0, YI, 0, SWIN[2])
    wall("WallF8", SWIN[0], SWIN[1], Y0, YI, SWIN[3], H)
    wall("WallF9", SWIN[1], X1, Y0, YI, 0, H)
    wall("WallL", X0, X0 + T, YI, Y1, 0, H)
    wall("WallR", X1 - T, X1, YI, Y1, 0, H)
    wall("WallB", X0 + T, X1 - T, Y1 - T, Y1, 0, H)
    wall("ParapetF", X0, X1, Y0, Y0 + 0.35 * M, H, PT)
    wall("ParapetL", X0, X0 + T, Y0 + 0.35 * M, Y1, H, H + 0.6 * M)
    wall("ParapetR", X1 - T, X1, Y0 + 0.35 * M, Y1, H, H + 0.6 * M)
    wall("ParapetB", X0 + T, X1 - T, Y1 - T, Y1, H, H + 0.6 * M)
    K.boxr("Trim", X0 - 0.05, X1 + 0.05, Y0 - 0.05, Y0 + 0.4 * M, PT, PT + 0.12 * M)
    K.boxr("Flat", X0 + T, X1 - T, YI, Y1 - T, H - 0.05, H + 0.06)                     # roof deck
    K.boxr("Ceiling", X0 + T, X1 - T, YI, Y1 - T, H - 0.55 * M, H - 0.45 * M)          # drop ceiling
    K.boxr("ShopFloor", X0 + T, X1 - T, YI - T, Y1 - T, 0, 0.04)
    for (a0, a1, b0, b1) in ((X0 - 0.05, X1 + 0.05, Y0 - 0.05, Y0), (X0 - 0.05, X1 + 0.05, Y1, Y1 + 0.05),
                             (X0 - 0.05, X0, Y0, Y1), (X1, X1 + 0.05, Y0, Y1)):
        K.boxr("Foundation", a0, a1, b0, b1, 0, 0.35 * M)                           # plinth band, outside only
    # ---- sign + lights
    K.face_y("StoreSign", 0, Y0 - 0.05, 3.5 * M, 19.2 * M, 2.4 * M)
    K.boxr("Dark", -9.8 * M, 9.8 * M, Y0 - 0.35 * M, Y0 - 0.05, 3.4 * M, 3.48 * M)
    for lx in (-7, -2.4, 2.4, 7):
        K.box("Sconce", (lx * M, Y0 - 0.55 * M, 6.05 * M), (0.6 * M, 0.25 * M, 0.12 * M))
        K.cyl_along("Iron", (lx * M, Y0 - 0.02, 5.95 * M), (lx * M, Y0 - 0.55 * M, 6.05 * M), 0.02 * M, segs=4)
    # ---- shop windows: real glass (ClearGlass* -> see-through in game), aluminium mullions, iron bars
    for gi, (x0, x1, z0, z1, n) in enumerate(((*WIN, 3), (*SWIN, 1))):
        K.boxr(f"ClearGlass{gi + 1}", x0, x1, Y0 + 0.14 * M, Y0 + 0.16 * M, z0, z1, mat="Glass")
        for k in range(n + 1):
            x = x0 + k * (x1 - x0) / n
            K.boxr("Frame", x - 0.06 * M, x + 0.06 * M, Y0 + 0.05 * M, Y0 + 0.25 * M, z0, z1)
        for z in (z0, z1):
            K.boxr("Frame", x0, x1, Y0 + 0.05 * M, Y0 + 0.25 * M, z - 0.06 * M, z + 0.06 * M)
        K.boxr("Sill", x0 - 0.1 * M, x1 + 0.1 * M, Y0 - 0.12 * M, Y0 + 0.05 * M, z0 - 0.1 * M, z0)
        nb = int((x1 - x0) / (0.16 * M))
        for k in range(nb + 1):
            K.boxr("WinIron", x0 + k * (x1 - x0) / nb - 0.015 * M, x0 + k * (x1 - x0) / nb + 0.015 * M, Y0 - 0.1 * M, Y0 - 0.07 * M, z0, z1)
        for z in (z0 + 0.3 * M, (z0 + z1) / 2, z1 - 0.3 * M):
            K.boxr("WinIron", x0, x1, Y0 - 0.11 * M, Y0 - 0.06 * M, z - 0.025 * M, z + 0.025 * M)
        K.boxr("Pole", x0 - 0.05 * M, x1 + 0.05 * M, Y0 - 0.32 * M, Y0, z1 + 0.02 * M, z1 + 0.32 * M)   # rolled shutter box
    # posters inside the glass + neon OPEN outline
    for px, name in ((-6.3 * M, "PosterSoda"), (-3.0 * M, "PosterSnack"), (0.6 * M, "PosterCoffee"), (7.8 * M, "PosterOpen")):
        K.face_y(name, px, Y0 + 0.17 * M, 1.6 * M, 0.8 * M, 1.0 * M, facing=-1)
    for (cx, cz, w, h) in ((7.8 * M, 2.65 * M, 1.0 * M, 0.05 * M), (7.8 * M, 1.55 * M, 1.0 * M, 0.05 * M),
                           (7.3 * M, 2.1 * M, 0.05 * M, 1.1 * M), (8.3 * M, 2.1 * M, 0.05 * M, 1.1 * M)):
        K.box("NeonRed", (cx, Y0 + 0.22 * M, cz), (w, 0.04 * M, h))
    # ---- door: aluminium frame, glass door swung open inward, push bar, threshold, mat
    for x in (DOOR[0], DOOR[1]):
        K.boxr("Frame", x - 0.08 * M, x + 0.08 * M, Y0 - 0.02, YI + 0.02, 0, DOOR[2])
    K.boxr("Frame", DOOR[0] - 0.08 * M, DOOR[1] + 0.08 * M, Y0 - 0.02, YI + 0.02, DOOR[2], DOOR[2] + 0.15 * M)
    K.boxr("Meter", DOOR[0], DOOR[1], Y0, YI, 0, 0.03)
    dx, dy = DOOR[1] - 0.08 * M, YI + 0.05 * M                     # hinge on the right, door open 90 deg
    K.boxr("Frame", dx - 0.08 * M, dx, dy, dy + 0.12 * M, 0.02, DOOR[2] - 0.05 * M)        # hinge stile
    K.boxr("ClearGlass3", dx - 0.06 * M, dx - 0.02 * M, dy + 0.1 * M, dy + 1.4 * M, 0.3 * M, DOOR[2] - 0.2 * M, mat="Glass")
    for z in (0.08 * M, DOOR[2] - 0.12 * M):
        K.boxr("Frame", dx - 0.08 * M, dx, dy, dy + 1.5 * M, z - 0.06 * M, z + 0.06 * M)
    K.boxr("Frame", dx - 0.08 * M, dx, dy + 1.38 * M, dy + 1.5 * M, 0.02, DOOR[2] - 0.05 * M)
    K.boxr("Pole", dx - 0.2 * M, dx - 0.08 * M, dy + 0.3 * M, dy + 1.2 * M, 1.0 * M, 1.06 * M)  # push bar
    K.box("Dark", (DOOR[0] + 0.8 * M, YI + 0.8 * M, 0.05), (1.3 * M, 0.9 * M, 0.02))            # door mat
    K.box("Dark", (DOOR[0] + 0.8 * M, Y0 - 0.6 * M, 0.2 * M), (1.3 * M, 0.9 * M, 0.02))
    K.box("Sconce", (DOOR[0] + 0.8 * M, Y0 - 0.12 * M, DOOR[2] + 0.4 * M), (0.5 * M, 0.2 * M, 0.15 * M))
    # ======================================================== interior
    # light painted lining just inside the shell (no collision in game), with a dark skirting
    IN, CZ = 0.02, H - 0.55 * M
    for (x0, x1, y0, y1) in ((X0 + T, X1 - T, YI, YI + IN), (X0 + T, X0 + T + IN, YI, Y1 - T),
                             (X1 - T - IN, X1 - T, YI, Y1 - T), (X0 + T, X1 - T, Y1 - T - IN, Y1 - T)):
        if y0 == YI:               # front wall: keep the window and door openings clear
            for (a, b, z0, z1) in ((x0, WIN[0], 0, CZ), (WIN[0], WIN[1], 0, WIN[2]), (WIN[0], WIN[1], WIN[3], CZ),
                                   (WIN[1], DOOR[0], 0, CZ), (DOOR[0], DOOR[1], DOOR[2], CZ), (DOOR[1], SWIN[0], 0, CZ),
                                   (SWIN[0], SWIN[1], 0, SWIN[2]), (SWIN[0], SWIN[1], SWIN[3], CZ), (SWIN[1], x1, 0, CZ)):
                K.boxr("DecoPaint", a, b, y1, y1 + IN, z0, z1)
        else:
            K.boxr("DecoPaint", x0, x1, y0, y1, 0, CZ)
    for (x0, x1, y0, y1) in ((X0 + T, X0 + T + 0.05 * M, YI, Y1 - T), (X1 - T - 0.05 * M, X1 - T, YI, Y1 - T),
                             (X0 + T, X1 - T, Y1 - T - 0.05 * M, Y1 - T)):
        K.boxr("DecoSkirt", x0, x1, y0, y1, 0.04, 0.3 * M)
    # drink coolers along the back wall
    for i in range(3):
        cx = -8.6 * M + i * 3.1 * M
        K.boxr(f"Cooler{i + 1}", cx - 1.55 * M, cx + 1.55 * M, Y1 - T - 0.9 * M, Y1 - T, 0, 2.5 * M, mat="Pole")
        K.face_y("FridgeDoors", cx, Y1 - T - 0.92 * M, 0.15 * M, 3.0 * M, 2.2 * M)
        K.box("Light", (cx, Y1 - T - 0.93 * M, 2.42 * M), (3.0 * M, 0.04 * M, 0.08 * M))
    # three gondola aisles (front-back), goods on both long sides, end caps
    for g, gx in enumerate((-8.0 * M, -4.6 * M, -1.2 * M)):
        y0, y1, gh = 3.6 * M, 9.6 * M, 1.7 * M
        K.boxr(f"Gondola{g + 1}", gx - 0.5 * M, gx + 0.5 * M, y0, y1, 0, gh, mat="Plastic")
        K.boxr("Pole", gx - 0.55 * M, gx + 0.55 * M, y0 - 0.05, y1 + 0.05, 0, 0.15 * M)
        for side in (-1, 1):
            for k in range(2):
                K.face_x("ShelfGoodsA" if (g + k + (side > 0)) % 2 else "ShelfGoodsB", gx + side * 0.52 * M,
                         y0 + (k + 0.5) * 3.0 * M, 0.15 * M, 3.0 * M, 1.55 * M, facing=side)
        for (ey, fc) in ((y0, -1), (y1, 1)):                              # end caps with candy
            K.face_y("CandyRack", gx, ey + fc * 0.02, 0.2 * M, 0.95 * M, 1.4 * M, facing=fc)
        K.box("Yellow", (gx, y0 - 0.03, gh + 0.2 * M), (0.9 * M, 0.04 * M, 0.3 * M))       # aisle sign
    # counter (L shape) with register, candy rack behind, cig-free back wall shelves with snacks
    K.boxr("Counter1", 6.4 * M, 10.0 * M, 3.4 * M, 4.2 * M, 0, 1.05 * M, mat="Counter")
    K.boxr("Counter2", 6.4 * M, 7.2 * M, 4.2 * M, 6.4 * M, 0, 1.05 * M, mat="Counter")
    K.boxr("Stone", 6.35 * M, 10.05 * M, 3.35 * M, 4.25 * M, 1.05 * M, 1.1 * M)
    K.boxr("Stone", 6.35 * M, 7.25 * M, 4.25 * M, 6.45 * M, 1.05 * M, 1.1 * M)
    K.box("Dark", (8.6 * M, 3.8 * M, 1.25 * M), (0.6 * M, 0.45 * M, 0.3 * M))                    # register
    K.face_y("Register", 8.6 * M, 3.8 * M - 0.23 * M - 0.01, 1.1 * M, 0.45 * M, 0.45 * M, facing=-1)
    K.box("Dark", (7.9 * M, 3.8 * M, 1.2 * M), (0.35 * M, 0.3 * M, 0.2 * M))                     # card reader
    K.face_x("CandyRack", X1 - T - 0.02, 5.0 * M, 1.1 * M, 3.0 * M, 2.4 * M, facing=-1)
    K.boxr("Wood", 9.6 * M, X1 - T, 3.5 * M, 6.5 * M, 0, 1.0 * M)
    K.box("Dark", (10.2 * M, 6.0 * M, 2.9 * M), (0.6 * M, 0.9 * M, 0.55 * M))                    # CCTV monitor
    K.face_x("Register", 9.88 * M, 6.0 * M, 2.7 * M, 0.7 * M, 0.42 * M, facing=-1)
    # coffee station + freezer chest + ATM + trash + mop bucket + wet floor sign
    K.boxr("Counter3", X1 - T - 0.8 * M, X1 - T, 7.6 * M, 10.6 * M, 0, 0.95 * M, mat="Counter")
    K.face_x("Coffee", X1 - T - 0.85 * M, 9.1 * M, 0.95 * M, 1.0 * M, 1.5 * M, facing=-1)
    K.box("Dark", (X1 - T - 0.4 * M, 9.1 * M, 1.7 * M), (0.8 * M, 1.0 * M, 1.5 * M))
    for i in range(3):
        K.cyl("Plastic", (X1 - T - 0.4 * M, 8.0 * M + i * 0.12 * M, 1.1 * M), 0.05 * M, 0.3 * M, segs=8)
    K.boxr("Freezer", 2.0 * M, 4.6 * M, 8.0 * M, 9.0 * M, 0, 0.85 * M, mat="Plastic")
    K.quad("FreezerTop", [(2.05 * M, 8.05 * M, 0.86 * M), (4.55 * M, 8.05 * M, 0.86 * M), (4.55 * M, 8.95 * M, 0.86 * M), (2.05 * M, 8.95 * M, 0.86 * M)])
    K.boxr("Atm", 2.3 * M, 3.2 * M, YI, YI + 0.7 * M, 0, 1.8 * M, mat="Dark")
    K.face_y("AtmFace", 2.75 * M, YI + 0.72 * M, 0.5 * M, 0.85 * M, 1.25 * M, facing=1)
    K.cyl("BinGrey", (6.0 * M, YI + 0.4 * M, 0.45 * M), 0.3 * M, 0.9 * M, segs=12)
    K.cyl("Yellow", (0.5 * M, 11.0 * M, 0.2 * M), 0.25 * M, 0.4 * M, segs=10)                 # mop bucket
    K.cyl_along("Wood", (0.5 * M, 11.0 * M, 0.3 * M), (0.6 * M, 11.1 * M, 1.5 * M), 0.02 * M, segs=4)
    for s_ in (-1, 1):                                                                            # wet floor sign
        K.box("Yellow", (2.2 * M, 6.8 * M + s_ * 0.12 * M, 0.35 * M), (0.35 * M, 0.03 * M, 0.7 * M))
    # back room door, ceiling lights, a dome camera and a mirror
    K.face_y("SecurityDoor", 6 * M, Y1 - T - 0.02, 0, 1.0 * M, 2.1 * M, facing=-1)
    K.face_y("SecurityDoor", 6 * M, Y1 + 0.04, 0, 1.05 * M, 2.2 * M, facing=1)
    for lx in (-8 * M, -4.6 * M, -1.2 * M, 2.5 * M, 7.5 * M):
        for ly in (4.0 * M, 7.0 * M, 10.0 * M):
            K.box("LightCeil", (lx, ly, H - 0.57 * M), (1.2 * M, 0.5 * M, 0.04 * M), mat="Light")
    K.cyl("Dark", (-3 * M, 6 * M, H - 0.62 * M), 0.12 * M, 0.12 * M, segs=10)
    K.cyl("Glass", (-10.4 * M, YI + 0.3 * M, 3.4 * M), 0.3 * M, 0.05 * M, segs=14, axis='Y')
    # ======================================================== outside details
    # bollards with caps + reflective band
    for bx in (-6.5, -4, -1.5, 1, 6.5, 9):
        K.cyl("Yellow", (bx * M, Y0 - 1.6 * M, 0.6 * M), 0.12 * M, 1.2 * M, segs=12)
        K.cyl("Yellow", (bx * M, Y0 - 1.6 * M, 1.22 * M), 0.1 * M, 0.06 * M, segs=12)
        K.cyl("Paint", (bx * M, Y0 - 1.6 * M, 0.95 * M), 0.125 * M, 0.08 * M, segs=12)
    # ice box: body, lid, ICE front, handles, compressor grille, feet
    ix0, ix1 = X0 + 0.4 * M, X0 + 2.6 * M
    K.boxr("IceBody", ix0, ix1, Y0 - 1.1 * M, Y0 - 0.05, 0.12 * M, 1.85 * M, mat="IceBox")
    K.face_y("IceFront", (ix0 + ix1) / 2, Y0 - 1.12 * M, 0.5 * M, ix1 - ix0 - 0.1 * M, 1.25 * M)
    for hx in (ix0 + 0.6 * M, ix1 - 0.6 * M):
        K.boxr("Pole", hx - 0.2 * M, hx + 0.2 * M, Y0 - 1.18 * M, Y0 - 1.12 * M, 1.05 * M, 1.1 * M)
    K.face_x("AcGrille", ix1 + 0.01, Y0 - 0.6 * M, 0.25 * M, 0.8 * M, 0.5 * M, facing=1)
    for fx in (ix0 + 0.1 * M, ix1 - 0.1 * M):
        for fy in (Y0 - 1.0 * M, Y0 - 0.15 * M):
            K.boxr("Dark", fx - 0.06 * M, fx + 0.06 * M, fy - 0.06 * M, fy + 0.06 * M, 0, 0.12 * M)
    # payphone: post, housing, keypad, handset + cord, little hood
    px = X0 + 3.5 * M
    K.box("Pole", (px, Y0 - 0.12 * M, 0.9 * M), (0.12 * M, 0.12 * M, 1.8 * M))
    K.box("Pole", (px, Y0 - 0.25 * M, 1.45 * M), (0.55 * M, 0.3 * M, 0.75 * M))
    K.box("Pole", (px, Y0 - 0.32 * M, 1.95 * M), (0.7 * M, 0.45 * M, 0.06 * M))
    K.face_y("Register", px + 0.08 * M, Y0 - 0.41 * M, 1.25 * M, 0.25 * M, 0.25 * M)
    K.box("Dark", (px - 0.18 * M, Y0 - 0.42 * M, 1.5 * M), (0.1 * M, 0.06 * M, 0.42 * M))
    K.cyl_along("Dark", (px - 0.18 * M, Y0 - 0.44 * M, 1.3 * M), (px - 0.05 * M, Y0 - 0.45 * M, 1.12 * M), 0.012 * M, segs=4)
    # newspaper boxes on legs with a coin box
    for i, part in enumerate(("BinBlue", "Red", "Yellow")):
        nx = X1 - 1.2 * M - i * 0.7 * M
        K.box(part, (nx, Y0 - 0.5 * M, 0.85 * M), (0.55 * M, 0.45 * M, 0.75 * M))
        K.face_y("NewsFace", nx, Y0 - 0.73 * M, 0.55 * M, 0.5 * M, 0.6 * M)
        K.box(part, (nx, Y0 - 0.5 * M, 1.25 * M), (0.6 * M, 0.5 * M, 0.06 * M))
        for lx in (-0.2, 0.2):
            K.box("Pole", (nx + lx * M, Y0 - 0.5 * M, 0.24 * M), (0.05 * M, 0.4 * M, 0.48 * M))
    # cameras + wall lights
    for cx in (X0 + 0.4 * M, X1 - 0.4 * M):
        K.box("Plastic", (cx, Y0 - 0.3 * M, 3.2 * M), (0.18 * M, 0.4 * M, 0.18 * M))
        K.box("Dark", (cx, Y0 - 0.51 * M, 3.2 * M), (0.1 * M, 0.02, 0.1 * M))
    for sy in (4 * M, 10 * M):
        K.box("Sconce", (X1 + 0.1 * M, sy, 3.6 * M), (0.16 * M, 0.3 * M, 0.2 * M))
        K.box("Sconce", (X0 - 0.1 * M, sy, 3.6 * M), (0.16 * M, 0.3 * M, 0.2 * M))
    # big side tag, a real barred side window, downpipes, meters, roof ladder
    tag(X1, "x", 7.6 * M, 0.6 * M, 8.0 * M, 3.0 * M, 1)
    K.window3d("x", X0, -1, 4.5 * M, 1.6 * M, 1.6 * M, 1.2 * M, bars=True)
    for (dx_, dy_) in ((X0 - 0.12 * M, Y1 - 0.4 * M), (X1 + 0.12 * M, Y1 - 0.4 * M)):
        K.downpipe(dx_, dy_, 0, H + 0.6 * M)
    meter("y", Y1, 1, -6 * M, 1.4 * M)
    meter("y", Y1, 1, -5.2 * M, 1.4 * M)
    for k in range(10):                                                                          # roof ladder at the back
        K.boxr("Pole", -2.4 * M, -1.6 * M, Y1 + 0.15 * M, Y1 + 0.2 * M, 0.6 * M + k * 0.42 * M, 0.64 * M + k * 0.42 * M)
    for lx in (-2.4 * M, -1.6 * M):
        K.boxr("Pole", lx - 0.03 * M, lx + 0.03 * M, Y1 + 0.12 * M, Y1 + 0.22 * M, 0.5 * M, H + 1.2 * M)
    K.box("Sconce", (7.2 * M, Y1 + 0.08 * M, 2.6 * M), (0.25 * M, 0.16 * M, 0.2 * M))
    # roof units: casing, grille faces, fan disc, ducts
    for (cx, cy) in ((-6 * M, 8 * M), (2 * M, 9 * M), (7 * M, 6 * M)):
        K.box("AcBody", (cx, cy, H + 0.55 * M), (1.6 * M, 1.3 * M, 1.0 * M))
        K.face_y("AcGrille", cx, cy - 0.66 * M, H + 0.15 * M, 1.4 * M, 0.75 * M)
        K.cyl("Dark", (cx, cy, H + 1.06 * M), 0.5 * M, 0.03, segs=14)
        K.cyl("Pole", (cx, cy, H + 1.09 * M), 0.12 * M, 0.04, segs=8)
        K.boxr("Pole", cx + 0.5 * M, cx + 0.8 * M, cy - 0.3 * M, cy + 0.3 * M, H, H + 0.25 * M)
    # parking: stalls, wheel stops, an accessible-free plain lot
    for i in range(7):
        sx = -8.4 * M + i * 2.8 * M
        K.boxr("Paint", sx - 0.06 * M, sx + 0.06 * M, -4.5 * M, Y0 - 2.4 * M, 0, 0.03)
    for i in range(6):
        sx = -7.0 * M + i * 2.8 * M
        K.box("WheelStop", (sx, Y0 - 2.9 * M, 0.08 * M), (1.8 * M, 0.25 * M, 0.16 * M))
    # dumpster with lids, side pockets, wheels
    d0, d1, e0, e1 = X1 + 0.4 * M, X1 + 1.8 * M, Y1 - 3.4 * M, Y1 - 1.2 * M
    K.boxr("Dumpster", d0, d1, e0, e1, 0.15 * M, 1.4 * M)
    for (a0, a1) in ((e0, (e0 + e1) / 2), ((e0 + e1) / 2, e1)):
        K.boxr("Dark", d0 - 0.05 * M, d1 + 0.05 * M, a0 + 0.02, a1 - 0.02, 1.4 * M, 1.47 * M)
    for (a0, a1) in ((e0 - 0.1 * M, e0), (e1, e1 + 0.1 * M)):
        K.boxr("Dumpster", d0 + 0.3 * M, d1 - 0.3 * M, a0, a1, 0.7 * M, 0.9 * M)
    for dy in (e0 + 0.2 * M, e1 - 0.2 * M):
        for dx in (d0 + 0.1 * M, d1 - 0.1 * M):
            K.cyl("Dark", (dx, dy, 0.08 * M), 0.08 * M, 0.1 * M, segs=8, axis='Y')
    bins(X0 - 1.5 * M, Y1 - 1.0 * M, 2)
    lamp_post(-12 * M, -12 * M, arm=(1, 0))
    lamp_post(12 * M, -12 * M, arm=(-1, 0))
    planter(-12 * M, -1 * M, 1.6 * M, 3 * M, palm=True)
    planter(12 * M, -1 * M, 1.6 * M, 3 * M, palm=True)
    for wn in WALLS:
        VARIANTS[wn] = {p: f"Wall{p}_Color.png" for p in PALETTES}
    VARIANTS["Tag"] = {g: f"Tag{g}_Color.png" for g in GANGS}
    return [("01_front", (12 * M, -34 * M, 6 * M), (0, 2 * M, 3 * M), 26), ("02_aerial", (30 * M, -30 * M, 26 * M), (0, 0, 0), 28),
            ("03_inside", (9 * M, 2.2 * M, 1.7 * M), (-6 * M, 9 * M, 1.2 * M), 18),
            ("04_inside2", (-10 * M, 2.4 * M, 1.8 * M), (3 * M, 10 * M, 1.0 * M), 18),
            ("05_door", (6 * M, -6 * M, 1.8 * M), (3.5 * M, 4 * M, 1.4 * M), 24)]


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
    # fountain: granite basin (lathed: floor, inner wall, wide coping, outer wall), mosaic floor,
    # two-tier bowl column. Water = FxPool surfaces + FxFall sheets + FxRipple rings (animated in game)
    R0 = 4.2 * M
    lathe("Stone", [(0, 0), (R0 + 0.35 * M, 0), (R0 + 0.35 * M, 0.78 * M), (R0 + 0.48 * M, 0.8 * M), (R0 + 0.48 * M, 0.95 * M),
                    (R0 + 0.42 * M, 1.0 * M), (R0 - 0.2 * M, 1.0 * M), (R0 - 0.26 * M, 0.95 * M), (R0 - 0.26 * M, 0.26 * M), (0, 0.26 * M)], segs=48)
    lathe("Tile", [(0, 0.262 * M), (R0 - 0.27 * M, 0.262 * M), (R0 - 0.27 * M, 0.3 * M), (0, 0.3 * M)][::-1], segs=48)
    m = M
    prof = [(0, 0.3), (0.62, 0.3), (0.62, 0.45), (0.5, 0.55), (0.42, 0.7), (0.38, 1.2), (0.42, 1.45), (0.55, 1.62), (0.7, 1.75),
            (1.2, 1.93), (1.7, 2.08), (1.95, 2.2), (2.02, 2.3), (1.98, 2.36), (1.88, 2.36), (1.65, 2.22), (1.1, 2.12), (0.4, 2.08),
            (0.3, 2.25), (0.25, 2.7), (0.3, 3.0), (0.42, 3.12), (0.8, 3.26), (1.05, 3.36), (1.08, 3.42), (1.0, 3.46), (0.75, 3.38),
            (0.3, 3.32), (0.2, 3.5), (0.16, 3.72), (0.09, 3.8), (0, 3.82)]
    lathe("Stone", [(r * m, z * m) for r, z in prof], segs=40)
    for zz, rr in ((0.3, 0.64), (1.75, 0.72)):                       # carved bands
        lathe("Kerb", [(0, zz * m), (rr * m, zz * m), (rr * m, zz * m + 0.06 * m), (0, zz * m + 0.06 * m)][::-1], segs=40)
    # water surfaces (just below each rim, inside the stone, never coplanar)
    disc("FxPool", 0, 0, R0 - 0.27 * M, 0.8 * M, segs=48, scale=2.0)
    disc("FxPool", 0, 0, 1.78 * M, 2.3 * M, segs=40, scale=1.2)
    disc("FxPool", 0, 0, 0.9 * M, 3.4 * M, segs=32, scale=0.8)
    # falling sheets off each lip + a crown jet at the top
    sheet_rev("FxFall", 0, 0, 2.03 * M, 2.3 * M, 2.25 * M, 0.81 * M, segs=40, urep=10, vrep=2.0)
    sheet_rev("FxFall", 0, 0, 1.09 * M, 3.4 * M, 1.22 * M, 2.31 * M, segs=32, urep=6, vrep=1.5)
    sheet_rev("FxFall", 0, 0, 0.05 * M, 3.82 * M, 0.025 * M, 4.7 * M, segs=8, urep=1, vrep=0.8)       # thin jet up
    for i in range(6):                                                                                # arcing spouts
        a = i / 6 * math.tau
        pts = [(math.cos(a) * (0.1 + 0.55 * t) * M, math.sin(a) * (0.1 + 0.55 * t) * M, (3.75 + 0.5 * t - 0.85 * t * t) * M) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        for p0, p1 in zip(pts, pts[1:]):
            K.cyl_along("FxJet", p0, p1, 0.02 * M, segs=5)
    # impact ripples where the sheets land
    sheet_rev("FxRipple", 0, 0, 2.2 * M, 0.805 * M, 3.3 * M, 0.805 * M, segs=48, urep=8, vrep=1.0, both=False)
    sheet_rev("FxRipple", 0, 0, 1.18 * M, 2.305 * M, 1.7 * M, 2.305 * M, segs=40, urep=6, vrep=1.0, both=False)
    sheet_rev("FxRipple", 0, 0, 0.6 * M, 3.405 * M, 0.88 * M, 3.405 * M, segs=32, urep=4, vrep=1.0, both=False)
    for i in range(8):                                                 # underwater uplights in the basin floor
        a = i / 8 * math.tau
        K.cyl("Light", (math.cos(a) * 3.2 * M, math.sin(a) * 3.2 * M, 0.31 * M), 0.12 * M, 0.02 * M, segs=10)
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
            plaza_planter(sx * 16 * M, sy * 14 * M, 3.2 * M, 3.2 * M, palm=True)
        plaza_planter(sx * 16 * M, 0, 2.4 * M, 6 * M, palm=False)
    for sx in (-1, 1):
        plaza_planter(sx * 8 * M, 16.5 * M, 6 * M, 2 * M, palm=False)
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
    # bus shelter (right of centre on the kerb): pad + tactile strip, steel frame, glass back and
    # end, lit ad box, glass roof with printed fascia, perforated bench with dividers, lean rail,
    # LED arrivals board, stop flag with timetable, litter bin
    sx0, sy0 = 11 * M, -18.3 * M
    K.boxr("Concrete", sx0 - 3.6 * M, sx0 + 3.6 * M, sy0 - 0.1 * M, sy0 + 2.4 * M, 0, 0.03 * M)
    for k in range(18):
        K.boxr("Yellow", sx0 - 3.4 * M + k * 0.38 * M, sx0 - 3.1 * M + k * 0.38 * M, sy0 - 0.05 * M, sy0 + 0.5 * M, 0.03 * M, 0.045 * M)
    BY = sy0 + 1.8 * M                                                   # back plane
    for px in (sx0 - 3 * M, sx0 - 0.9 * M, sx0 + 1.4 * M, sx0 + 3 * M):
        K.boxr("Pole", px - 0.06 * M, px + 0.06 * M, BY - 0.06 * M, BY + 0.06 * M, 0.03 * M, 2.75 * M)
    for px in (sx0 - 3 * M, sx0 + 3 * M):                                 # roof arms, sloping to the kerb
        K.cyl_along("Pole", (px, BY, 2.75 * M), (px, sy0 + 0.1 * M, 2.6 * M), 0.05 * M, segs=6)
    for yy, zz in ((BY, 2.75 * M), (sy0 + 0.1 * M, 2.6 * M), ((BY + sy0 + 0.1 * M) / 2, 2.675 * M)):
        K.cyl_along("Pole", (sx0 - 3.05 * M, yy, zz), (sx0 + 3.05 * M, yy, zz), 0.04 * M, segs=6)
    K.quad("ClearGlassRoof", [(sx0 - 3 * M, sy0 + 0.1 * M, 2.65 * M), (sx0 + 3 * M, sy0 + 0.1 * M, 2.65 * M),
                              (sx0 + 3 * M, BY, 2.8 * M), (sx0 - 3 * M, BY, 2.8 * M)], mat="Glass")
    K.quad("ClearGlassRoof", [(sx0 - 3 * M, BY, 2.78 * M), (sx0 + 3 * M, BY, 2.78 * M),
                              (sx0 + 3 * M, sy0 + 0.1 * M, 2.63 * M), (sx0 - 3 * M, sy0 + 0.1 * M, 2.63 * M)], mat="Glass")
    K.face_y("BusFascia", sx0, sy0 + 0.04 * M, 2.42 * M, 6.1 * M, 0.3 * M)
    K.boxr("Dark", sx0 - 3.05 * M, sx0 + 3.05 * M, sy0 + 0.05 * M, sy0 + 0.1 * M, 2.4 * M, 2.74 * M)
    for (a0, a1) in ((sx0 - 2.94 * M, sx0 - 0.96 * M), (sx0 - 0.84 * M, sx0 + 1.34 * M)):
        K.boxr("ClearGlassBus", a0, a1, BY - 0.01 * M, BY + 0.01 * M, 0.25 * M, 2.6 * M, mat="Glass")
        K.boxr("Pole", a0, a1, BY - 0.04 * M, BY + 0.04 * M, 0.2 * M, 0.26 * M)
        K.boxr("Pole", a0, a1, BY - 0.04 * M, BY + 0.04 * M, 2.6 * M, 2.66 * M)
        for k in range(1, 4):                                          # frosted dot band at eye level
            K.boxr("Paint", a0 + 0.05 * M, a1 - 0.05 * M, BY - 0.015 * M, BY - 0.012 * M, 1.3 * M + k * 0.06 * M, 1.32 * M + k * 0.06 * M)
    K.boxr("ClearGlassBus", sx0 - 3.01 * M, sx0 - 2.99 * M, sy0 + 0.6 * M, BY - 0.06 * M, 0.25 * M, 2.6 * M, mat="Glass")
    K.boxr("Pole", sx0 - 3.04 * M, sx0 - 2.96 * M, sy0 + 0.55 * M, sy0 + 0.6 * M, 0.03 * M, 2.7 * M)
    # ad box at the right end, lit both sides
    K.boxr("Dark", sx0 + 1.45 * M, sx0 + 2.95 * M, BY - 0.12 * M, BY + 0.12 * M, 0.2 * M, 2.5 * M)
    K.face_y("ShelterAd", sx0 + 2.2 * M, BY - 0.125 * M, 0.35 * M, 1.3 * M, 2.0 * M)
    K.face_y("ShelterAd", sx0 + 2.2 * M, BY + 0.125 * M, 0.35 * M, 1.3 * M, 2.0 * M, facing=1)
    for zz in (0.27 * M, 2.43 * M):
        K.box("Light", (sx0 + 2.2 * M, BY, zz), (1.4 * M, 0.26 * M, 0.04 * M))
    # bench: perforated steel seat, three armrests, legs; lean rail
    K.boxr("Pole", sx0 - 2.7 * M, sx0 + 1.1 * M, BY - 0.5 * M, BY - 0.1 * M, 0.44 * M, 0.48 * M)
    for k in range(40):
        K.boxr("Dark", sx0 - 2.65 * M + k * 0.094 * M, sx0 - 2.63 * M + k * 0.094 * M, BY - 0.46 * M, BY - 0.14 * M, 0.481 * M, 0.483 * M)
    for ax_ in (sx0 - 2.6 * M, sx0 - 0.8 * M, sx0 + 1.0 * M):
        K.boxr("Pole", ax_ - 0.03 * M, ax_ + 0.03 * M, BY - 0.45 * M, BY - 0.12 * M, 0.48 * M, 0.7 * M)
        K.boxr("Pole", ax_ - 0.03 * M, ax_ + 0.03 * M, BY - 0.4 * M, BY - 0.2 * M, 0.03 * M, 0.44 * M)
    K.cyl_along("Pole", (sx0 - 0.9 * M, BY - 0.08 * M, 0.9 * M), (sx0 + 1.4 * M, BY - 0.08 * M, 0.9 * M), 0.04 * M, segs=8)
    # LED arrivals board hanging under the roof
    K.boxr("Dark", sx0 - 1.0 * M, sx0 + 0.6 * M, sy0 + 0.9 * M, sy0 + 1.0 * M, 2.15 * M, 2.45 * M)
    K.face_y("BusDisplay", sx0 - 0.2 * M, sy0 + 0.895 * M, 2.17 * M, 1.5 * M, 0.26 * M)
    for hx in (sx0 - 0.9 * M, sx0 + 0.5 * M):
        K.cyl("Pole", (hx, sy0 + 0.95 * M, 2.56 * M), 0.015 * M, 0.22 * M, segs=4)
    # stop flag + timetable
    fx_ = sx0 - 4.1 * M
    K.cyl("Pole", (fx_, sy0 + 0.25 * M, 1.6 * M), 0.05 * M, 3.2 * M, segs=8)
    K.boxr("Pole", fx_ - 0.42 * M, fx_ + 0.42 * M, sy0 + 0.2 * M, sy0 + 0.3 * M, 2.0 * M, 3.05 * M)
    K.face_y("BusSign", fx_, sy0 + 0.195 * M, 2.02 * M, 0.8 * M, 1.0 * M)
    K.face_y("BusSign", fx_, sy0 + 0.305 * M, 2.02 * M, 0.8 * M, 1.0 * M, facing=1)
    K.boxr("Dark", fx_ - 0.3 * M, fx_ + 0.3 * M, sy0 + 0.19 * M, sy0 + 0.3 * M, 0.95 * M, 1.85 * M)
    K.face_y("Timetable", fx_, sy0 + 0.185 * M, 1.0 * M, 0.55 * M, 0.8 * M)
    # round litter bin
    K.cyl("Dark", (sx0 + 3.5 * M, sy0 + 1.3 * M, 0.45 * M), 0.28 * M, 0.9 * M, segs=16)
    K.cyl("Pole", (sx0 + 3.5 * M, sy0 + 1.3 * M, 0.93 * M), 0.31 * M, 0.08 * M, segs=16)
    K.cyl("Dark", (sx0 + 3.5 * M, sy0 + 1.3 * M, 0.98 * M), 0.18 * M, 0.04 * M, segs=12)
    # route map kiosk
    kx, ky = 4.5 * M, -14 * M
    K.box("Dark", (kx, ky, 1.1 * M), (1.5 * M, 0.35 * M, 2.2 * M))
    K.face_y("RouteMap", kx, ky - 0.2 * M, 0.7 * M, 1.25 * M, 1.25 * M)
    K.face_y("RouteMap", kx, ky + 0.2 * M, 0.7 * M, 1.25 * M, 1.25 * M, facing=1)
    K.box("Light", (kx, ky, 2.25 * M), (1.5 * M, 0.35 * M, 0.1 * M))
    # bollards along the kerb, lamps, flagpoles at the back, bins
    for i in range(-10, 11):
        bx = i * 2 * M
        if abs(bx - sx0) < 4.8 * M or abs(bx - mx) < 5.2 * M:
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
    return [("04_fountain", (9 * M, -11 * M, 3.2 * M), (0, 0, 2.0 * M), 30), ("05_bus", (17 * M, -26 * M, 2.4 * M), (11 * M, -17 * M, 1.4 * M), 26),
            ("01_front", (0, -46 * M, 10 * M), (0, 0, 2 * M), 24), ("02_aerial", (30 * M, -36 * M, 34 * M), (0, 0, 0), 26),
            ("03_monument", (-6 * M, -28 * M, 2.5 * M), (-11 * M, -16.5 * M, 1.6 * M), 26)]


shots = {"HouseA": house_a, "HouseB": house_b, "HouseC": house_c, "HouseD": house_d, "SideYard": side_yard, "Store": store, "Court": court, "SpawnPlaza": spawn_plaza}[ONLY]()

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
