"""Bellmont Hills: the rich suburb east of the city (original designs, thread "Build rich suburbs district").

  blender --background --python build_estate.py -- OUT_DIR --only Casa|Modern|Villa|Hacienda [--face S]
                                                    [--no-render] [--samples N] [--res F]

Every model is one 36 x 40 m lot (129.6 x 144 studs), origin = ground centre, front = -Y (street).
Casa      Spanish courtyard mansion: U plan, clay hip roofs, arched loggia with a balcony on top,
          three-tier fountain, garage wing, raised pool terrace.
Modern    charcoal render + glass villa: cantilevered upper floor, glass walls, roof terrace with
          topiary planters, cedar-clad garage, ivy wall, blossom trees, pool deck.
Villa     long two-floor house with a brown tile hip roof, two brick bays with covered balconies,
          garage wing, cypress row, pergola + pool.
Hacienda  single-storey ranch with a two-storey tower, barrel tile roofs, arcade porch,
          circular motor court round a fountain, garage, pool.
Textures: python3 tools/estate_textures.py first (CC0 ambientCG scans + PIL sheets in ./tex).
Walls take paint variants ("Walls@Ivory" etc., meta["variants"]); build_city_map picks one per lot.
Parts that must collide (Walls, HedgeBox, StoneWall, ...) are solid meshes; plants (Leaf*, Shrub,
Blossom, Ivy, Palm) never collide in game; ClearGlass* is see-through glass.
"""
import json, math, os, random, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402
from mathutils import Vector  # noqa: E402

A = args(r"C:\out\estate")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = argv[argv.index("--only") + 1]
NAME = model_name(ONLY, A)
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
K = Kit(NAME, A["out"], TEX)
rng = random.Random({"Casa": 11, "Modern": 12, "Villa": 13, "Hacienda": 14, "Police": 15}[ONLY])
LW, LD = 36.0, 40.0                     # lot, metres
PAINTS = ("Ivory", "Sand", "White", "Sage", "Stone", "Blush", "Slate", "Charcoal")
ROOF = {"Casa": "RoofClay", "Modern": "RoofFlat", "Villa": "RoofBrown", "Hacienda": "RoofBarrel", "Police": "RoofFlat"}[ONLY]
WALL = {"Casa": "WallIvory", "Modern": "WallWhite", "Villa": "WallSage", "Hacienda": "WallSand", "Police": "WallStone"}[ONLY]

# ---------------------------------------------------------------- materials (tile sizes in metres)
for name, sheet, tile in (("Walls", WALL, 3.0), ("Render", "Render", 3.0), ("Lawn", "Lawn", 3.0), ("Pavers", "Pavers", 1.6),
                          ("Travert", "Travert", 2.0), ("Patio", "Patio", 2.4), ("Brick", "Brick", 2.2), ("StoneWall", "StoneWall", 2.4),
                          ("Cladding", "Cladding", 2.0), ("Deck", "Deck", 1.8), ("PoolTile", "PoolTile", 1.6), ("Concrete", "Concrete", 3.0),
                          ("Gravel", "Gravel", 2.0), ("Marble", "Marble", 2.0), ("Stone", "Stone", 1.5), ("HedgeBox", "HedgeBox", 1.4),
                          ("Shrub", "HedgeBox", 1.0), ("Leaf", "Leaf", 1.4), ("LeafB", "LeafB", 1.4), ("Blossom", "Blossom", 1.4),
                          ("Trim", "Trim", 1.5), ("Iron", "Iron", 1.0), ("Bronze", "Bronze", 1.0), ("Steel", "Steel", 1.0),
                          ("Alu", "Alu", 1.0), ("Teak", "Teak", 1.0), ("Cushion", "Cushion", 1.0), ("Soil", "Soil", 1.0),
                          ("Bark", "Bark", 0.8), ("Pot", "Pot", 1.0), ("Rubber", "Rubber", 1.0), ("RoofFlat", "RoofFlat", 3.0), ("Asphalt", "Asphalt", 8 / 3.6)):
    K.mat(name, sheet=sheet, tile=(tile * M, tile * M), rough=0.7)
K.mat("Roof", sheet=ROOF, explicit=True)          # explicit UVs: tile rows run along each eave
for name in ("FrontDoor", "PivotDoor", "GarageWood", "GarageGlass", "GlassBigA", "GlassBigB", "GlassBigC", "HouseNumbers",
             "PoliceSign", "PoliceMonument", "PoliceBadge", "PoliceDoor", "RollDoor"):
    K.mat(name, sheet=name, explicit=True)
K.mat("Ivy", sheet="Ivy", explicit=True, alpha=True)
K.mat("FxPool", sheet="FxPool", explicit=True, rough=0.05)
K.mat("FxFall", sheet="FxFall", explicit=True, alpha=True, rough=0.05)
K.mat("FxRipple", sheet="FxRipple", explicit=True, alpha=True, rough=0.05)
K.mat("FxJet", color=(0.80, 0.90, 0.95), rough=0.05)
K.mat("ClearGlassRail", color=(0.62, 0.74, 0.76), rough=0.05, metal=0.2)
K.mat("Palm", color=(0.13, 0.29, 0.09), rough=0.7)
K.mat("Trunk", color=(0.40, 0.31, 0.22), rough=0.95)
for name, col, emit in (("Light", (1.0, 0.95, 0.85), 4.0), ("Sconce", (1.0, 0.90, 0.70), 3.0), ("Paint", (0.93, 0.93, 0.90), 0),
                        ("Flag", (0.10, 0.18, 0.40), 0), ("NeonRed", (1.0, 0.15, 0.12), 6.0), ("NeonCyan", (0.2, 0.5, 1.0), 6.0),
                        ("Yellow", (0.92, 0.70, 0.10), 0), ("Red", (0.75, 0.10, 0.10), 0)):
    K.mat(name, color=col, emit=emit)
K.facade_mats(frame=(0.95, 0.94, 0.91))
_g = K.mats["ClearGlassRail"]["mat"]
_g.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.25
_g.surface_render_method = 'DITHERED'


# ---------------------------------------------------------------- metre helpers
def B(part, x0, x1, y0, y1, z0, z1):
    K.boxr(part, x0 * M, x1 * M, y0 * M, y1 * M, z0 * M, z1 * M)


def C(part, x, y, z, r, h, segs=12, r2=None, axis='Z'):
    """Cylinder with its centre at z (metres)."""
    K.cyl(part, (x * M, y * M, z * M), r * M, h * M, segs=segs, r2=None if r2 is None else r2 * M, axis=axis)


def L(part, a, b, r, segs=6):
    K.cyl_along(part, tuple(v * M for v in a), tuple(v * M for v in b), r * M, segs=segs)


def FY(part, cx, y, z0, w, h, facing=-1, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
    K.face_y(part, cx * M, y * M + facing * 0.012 * M, z0 * M, w * M, h * M, facing=facing, uvs=uvs)


def FX(part, x, cy, z0, w, h, facing=1, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
    K.face_x(part, x * M + facing * 0.012 * M, cy * M, z0 * M, w * M, h * M, facing=facing, uvs=uvs)


def win(ax, plane, facing, a, z0, w=1.4, h=1.8, mull=1, transom=True, glass=None):
    K.window3d(ax, plane * M, facing, a * M, z0 * M, w * M, h * M, mull=mull, transom=transom, glass=glass, depth=0.14 * M)


def win_row(ax, plane, facing, a0, a1, z0, n, w=1.3, h=1.8, **kw):
    for i in range(n):
        win(ax, plane, facing, a0 + (i + 0.5) * (a1 - a0) / n, z0, w, h, **kw)


def roof_face(pts, edir):
    """One explicit-UV roof face: u along the eave (edir), v up the slope; 1 uv = 2.5 m."""
    pv = [Vector(p) for p in pts]
    n = (pv[1] - pv[0]).cross(pv[2] - pv[0]).normalized()
    e = Vector(edir).normalized()
    s = n.cross(e).normalized()
    if s.z < 0:
        s = -s
    T = 2.5 * M
    K.quad("Roof", [tuple(p) for p in pv], [((p - pv[0]).dot(e) / T, (p - pv[0]).dot(s) / T) for p in pv])


def hip(x0, x1, y0, y1, z, slope=0.42, over=0.6, gutter=True):
    """Hip roof over the box x0..x1, y0..y1 (metres) from wall top z; soffit, fascia, gutters."""
    rx0, rx1, ry0, ry1 = (v * M for v in (x0 - over, x1 + over, y0 - over, y1 + over))
    zb = (z + 0.01) * M
    wx, wy = rx1 - rx0, ry1 - ry0
    h = slope * min(wx, wy) / 2
    if wx >= wy:
        cy, i = (ry0 + ry1) / 2, wy / 2
        r0, r1 = (rx0 + i, cy, zb + h), (rx1 - i, cy, zb + h)
        roof_face([(rx0, ry0, zb), (rx1, ry0, zb), r1, r0], (1, 0, 0))
        roof_face([(rx1, ry1, zb), (rx0, ry1, zb), r0, r1], (-1, 0, 0))
        roof_face([(rx1, ry0, zb), (rx1, ry1, zb), r1], (0, 1, 0))
        roof_face([(rx0, ry1, zb), (rx0, ry0, zb), r0], (0, -1, 0))
    else:
        cx, i = (rx0 + rx1) / 2, wx / 2
        r0, r1 = (cx, ry0 + i, zb + h), (cx, ry1 - i, zb + h)
        roof_face([(rx1, ry0, zb), (rx1, ry1, zb), r1, r0], (0, 1, 0))
        roof_face([(rx0, ry1, zb), (rx0, ry0, zb), r0, r1], (0, -1, 0))
        roof_face([(rx0, ry0, zb), (rx1, ry0, zb), r0], (1, 0, 0))
        roof_face([(rx1, ry1, zb), (rx0, ry1, zb), r1], (-1, 0, 0))
    K.quad("Trim", [(rx0, ry0, zb - 0.01), (rx0, ry1, zb - 0.01), (rx1, ry1, zb - 0.01), (rx1, ry0, zb - 0.01)])   # soffit
    f = 0.06
    for (a0, a1, b0, b1) in ((x0 - over, x1 + over, y0 - over - f, y0 - over), (x0 - over, x1 + over, y1 + over, y1 + over + f),
                             (x0 - over - f, x0 - over, y0 - over - f, y1 + over + f), (x1 + over, x1 + over + f, y0 - over - f, y1 + over + f)):
        B("Trim", a0, a1, b0, b1, z - 0.2, z + 0.06)                                   # fascia
    if gutter:
        for (a0, a1, b0, b1) in ((x0 - over, x1 + over, y0 - over - 0.2, y0 - over - f), (x0 - over, x1 + over, y1 + over + f, y1 + over + 0.2)):
            B("Alu", a0, a1, b0, b1, z - 0.18, z - 0.04)
    return h / M


def shed(x0, x1, y0, y1, z_low, z_high):
    """Mono-pitch tile roof (porches): high edge at y1, low at y0."""
    a, b = (x0 * M, y0 * M, z_low * M), (x1 * M, y0 * M, z_low * M)
    c, d = (x1 * M, y1 * M, z_high * M), (x0 * M, y1 * M, z_high * M)
    roof_face([a, b, c, d], (1, 0, 0))
    K.quad("Trim", [a, d, c, b])
    B("Trim", x0, x1, y0 - 0.06, y0, z_low - 0.18, z_low + 0.04)


def rail(x0, y0, x1, y1, z, h=1.05, step=0.12, part="Iron"):
    """Iron balcony railing: balusters + top and bottom rails (metres)."""
    a, b = Vector((x0, y0, z)), Vector((x1, y1, z))
    Lr = (b - a).length
    d = (b - a) / Lr
    rz = math.atan2(d.y, d.x)
    n = max(1, int(Lr / step))
    for i in range(n + 1):
        p = a + d * (Lr * i / n)
        K.box(part, (p.x * M, p.y * M, (z + h / 2) * M), (0.025 * M, 0.025 * M, h * M), rz=rz)
    c = (a + b) / 2
    for zz, t in ((z + h, 0.06), (z + 0.1, 0.035)):
        K.box(part, (c.x * M, c.y * M, zz * M), (Lr * M + 0.05 * M, 0.06 * M, t * M), rz=rz)


def glass_rail(x0, y0, x1, y1, z, h=1.05):
    a, b = Vector((x0, y0, z)), Vector((x1, y1, z))
    Lr = (b - a).length
    d = (b - a) / Lr
    rz = math.atan2(d.y, d.x)
    c = (a + b) / 2
    K.box("ClearGlassRail", (c.x * M, c.y * M, (z + h / 2) * M), (Lr * M, 0.03 * M, h * M), rz=rz)
    K.box("Steel", (c.x * M, c.y * M, (z + h + 0.03) * M), (Lr * M + 0.04 * M, 0.07 * M, 0.06 * M), rz=rz)
    for i in range(int(Lr / 1.5) + 1):
        p = a + d * min(Lr, i * 1.5)
        K.box("Steel", (p.x * M, p.y * M, (z + 0.06) * M), (0.12 * M, 0.12 * M, 0.12 * M), rz=rz)


def hedge(x0, x1, y0, y1, h=1.2):
    """Clipped box hedge (collides): body + a slightly narrower rounded-off top layer."""
    B("HedgeBox", x0, x1, y0, y1, 0, h - 0.12)
    B("HedgeBox", x0 + 0.06, x1 - 0.06, y0 + 0.06, y1 - 0.06, h - 0.12, h)


def topiary(x, y, z=0.0, pot=True, h=1.0, s=0.45):
    if pot:
        C("Pot", x, y, z + 0.3, 0.32, 0.6, segs=12, r2=0.42)
        C("Soil", x, y, z + 0.58, 0.36, 0.03, segs=10)
        z += 0.6
    C("Bark", x, y, z + h / 2, 0.04, h, segs=6)
    K.shrub(x * M, y * M, (z + h - s * 0.5) * M, s * M, rng, part="Shrub", subdiv=2)


def cypress(x, y, h=7.0, r=0.75):
    C("Bark", x, y, 0.4, 0.12, 0.8, segs=6)
    rings = 6
    for k in range(rings):
        z0 = 0.5 + k * (h - 0.5) / rings
        z1 = z0 + (h - 0.5) / rings * 1.35
        r0 = r * (1.0 - 0.15 * k / rings) * (0.9 if k == 0 else 1.0)
        r1 = r * max(0.05, 1.0 - (k + 1.2) / rings) if k == rings - 1 else r * (1.0 - 0.15 * (k + 1) / rings)
        K.cyl("Leaf", (x * M, y * M, (z0 + z1) / 2 * M), r0 * M, (z1 - z0) * M, segs=9, r2=(r1 if k == rings - 1 else r0 * 0.92) * M)


def tree(x, y, h=8.0, spread=4.5, part="Leaf"):
    """Shade tree: tapered trunk, limbs, clumped canopy (part Leaf/LeafB/Blossom)."""
    C("Bark", x, y, h * 0.22, 0.22, h * 0.44, segs=8, r2=0.15)
    top = Vector((x, y, h * 0.44))
    for i in range(4):
        a = i / 4 * math.tau + rng.uniform(-0.4, 0.4)
        end = top + Vector((math.cos(a) * spread * 0.35, math.sin(a) * spread * 0.35, h * 0.22))
        L("Bark", top, end, 0.08)
    for i in range(14):
        a = rng.uniform(0, math.tau)
        r_ = rng.uniform(0, spread * 0.42)
        p = part if part == "Blossom" else ("Leaf" if i % 3 else "LeafB")
        K.shrub((x + math.cos(a) * r_) * M, (y + math.sin(a) * r_) * M, (h * rng.uniform(0.58, 0.82) - spread * 0.2) * M,
                rng.uniform(0.24, 0.34) * spread * M, rng, part=p, subdiv=2)


def palm(x, y, h=8.0):
    K.palm(x * M, y * M, 0, h * M, (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4)), rng)


def flower_bed(x0, x1, y0, y1, n=None):
    e = 0.12
    B("Soil", x0 + e, x1 - e, y0 + e, y1 - e, -0.02, 0.06)
    for (a0, a1, b0, b1) in ((x0, x1, y0, y0 + e), (x0, x1, y1 - e, y1), (x0, x0 + e, y0 + e, y1 - e), (x1 - e, x1, y0 + e, y1 - e)):
        B("Stone", a0, a1, b0, b1, 0, 0.16)
    n = n or max(2, int(max(x1 - x0, y1 - y0) / 0.8))
    for i in range(n):
        t = (i + 0.5) / n
        px, py = (x0 + (x1 - x0) * t, (y0 + y1) / 2) if x1 - x0 > y1 - y0 else ((x0 + x1) / 2, y0 + (y1 - y0) * t)
        K.shrub(px * M, py * M, 0.06 * M, rng.uniform(0.22, 0.32) * M, rng, part="Shrub" if i % 2 else "LeafB")


def lantern(x, y, z, wall_axis=None):
    """Bronze carriage lantern (lit at night) on a pier top or a wall."""
    B("Bronze", x - 0.14, x + 0.14, y - 0.14, y + 0.14, z, z + 0.05)
    B("Sconce", x - 0.1, x + 0.1, y - 0.1, y + 0.1, z + 0.05, z + 0.36)
    for sx in (-1, 1):
        for sy in (-1, 1):
            B("Bronze", x + sx * 0.11 - 0.015, x + sx * 0.11 + 0.015, y + sy * 0.11 - 0.015, y + sy * 0.11 + 0.015, z + 0.05, z + 0.38)
    C("Bronze", x, y, z + 0.42, 0.17, 0.08, segs=8, r2=0.05)


def bollard(x, y):
    C("Alu", x, y, 0.3, 0.07, 0.6, segs=8)
    C("Light", x, y, 0.55, 0.075, 0.08, segs=8)


def lathe(part, cx, cy, prof, segs=32):
    """Surface of revolution round (cx, cy): prof = [(r, z), ...] metres, from the axis to the axis."""
    bm = K.bm(part)
    rings = []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([bm.verts.new((cx * M, cy * M, z * M))])
        else:
            rings.append([bm.verts.new(((cx + r * math.cos(i / segs * math.tau)) * M, (cy + r * math.sin(i / segs * math.tau)) * M, z * M))
                          for i in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1:
                bm.faces.new([a[0], b[i], b[j]])
            elif len(b) == 1:
                bm.faces.new([a[i], b[0], a[j]])
            else:
                bm.faces.new([a[i], b[i], b[j], a[j]])


def disc(part, cx, cy, r, z, segs=32, scale=1.0):
    bm = K.bm(part)
    uvl = bm.loops.layers.uv.active
    for i in range(segs):
        a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
        p = [(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)), (cx + r * math.cos(a1), cy + r * math.sin(a1))]
        f = bm.faces.new([bm.verts.new((q[0] * M, q[1] * M, z * M)) for q in p])
        for l, q in zip(f.loops, p):
            l[uvl].uv = ((q[0] - cx) / scale, (q[1] - cy) / scale)


def sheet_rev(part, cx, cy, r0, z0, r1, z1, segs=32, urep=6, vrep=1.0, both=True):
    for side in ((1, -1) if both else (1,)):
        for i in range(segs):
            a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
            p = [((cx + r0 * math.cos(a0)) * M, (cy + r0 * math.sin(a0)) * M, z0 * M), ((cx + r0 * math.cos(a1)) * M, (cy + r0 * math.sin(a1)) * M, z0 * M),
                 ((cx + r1 * math.cos(a1)) * M, (cy + r1 * math.sin(a1)) * M, z1 * M), ((cx + r1 * math.cos(a0)) * M, (cy + r1 * math.sin(a0)) * M, z1 * M)]
            uv = [(i / segs * urep, 0), ((i + 1) / segs * urep, 0), ((i + 1) / segs * urep, vrep), (i / segs * urep, vrep)]
            if side < 0:
                p, uv = p[::-1], uv[::-1]
            K.quad(part, p, uv)


def fountain(cx, cy, R=2.4, tiers=3):
    """Carved travertine tiered fountain: round basin, bowls on a column, animated water (FxPool/FxFall/FxRipple)."""
    lathe("Stone", cx, cy, [(0, 0.02), (R + 0.2, 0.02), (R + 0.2, 0.5), (R + 0.3, 0.52), (R + 0.3, 0.64), (R + 0.24, 0.68),
                            (R - 0.12, 0.68), (R - 0.16, 0.64), (R - 0.16, 0.15), (0, 0.15)], segs=40)
    disc("FxPool", cx, cy, R - 0.17, 0.52, segs=40, scale=2.0)
    prof = [(0, 0.15), (0.4, 0.15), (0.4, 0.3), (0.3, 0.42), (0.24, 1.0), (0.3, 1.15), (0.5, 1.25), (1.0, 1.4), (1.3, 1.5),
            (1.36, 1.6), (1.3, 1.64), (1.0, 1.55), (0.3, 1.5), (0.2, 1.7), (0.17, 2.2), (0.24, 2.36), (0.6, 2.46), (0.78, 2.54),
            (0.8, 2.6), (0.74, 2.62), (0.25, 2.58)]
    if tiers >= 3:
        prof += [(0.13, 2.75), (0.11, 3.05), (0.16, 3.15), (0.36, 3.22), (0.4, 3.28), (0.33, 3.3), (0.12, 3.3), (0.1, 3.5), (0.05, 3.6), (0, 3.62)]
    else:
        prof += [(0.15, 2.8), (0.06, 3.0), (0, 3.02)]
    lathe("Stone", cx, cy, prof, segs=32)
    disc("FxPool", cx, cy, 1.28, 1.6, segs=32, scale=1.2)
    disc("FxPool", cx, cy, 0.74, 2.59, segs=24, scale=0.8)
    sheet_rev("FxFall", cx, cy, 1.36, 1.6, 1.5, 0.53, segs=32, urep=8, vrep=2.0)
    sheet_rev("FxFall", cx, cy, 0.8, 2.6, 0.9, 1.61, segs=24, urep=6, vrep=1.5)
    if tiers >= 3:
        disc("FxPool", cx, cy, 0.34, 3.27, segs=16, scale=0.6)
        sheet_rev("FxFall", cx, cy, 0.4, 3.28, 0.45, 2.6, segs=16, urep=4, vrep=1.2)
        sheet_rev("FxFall", cx, cy, 0.03, 3.6, 0.015, 4.1, segs=6, urep=1, vrep=0.8)
    sheet_rev("FxRipple", cx, cy, 1.48, 0.525, 2.1, 0.525, segs=40, urep=8, vrep=1.0, both=False)
    sheet_rev("FxRipple", cx, cy, 0.88, 1.605, 1.2, 1.605, segs=24, urep=5, vrep=1.0, both=False)
    for i in range(6):
        a = i / 6 * math.tau
        C("Light", cx + math.cos(a) * (R - 0.6), cy + math.sin(a) * (R - 0.6), 0.16, 0.08, 0.02, segs=8)


def pool(x0, x1, y0, y1, terrace, zt=0.9, steps_y=None):
    """Raised pool terrace (Patio top at zt) with a pool (x0..x1, y0..y1) cut in it: tiled shell,
    travertine coping, animated water a little below the coping, steps down to the lawn at the front."""
    tx0, tx1, ty0, ty1 = terrace
    B("StoneWall", tx0, x0, ty0, ty1, 0, zt - 0.05)
    B("StoneWall", x1, tx1, ty0, ty1, 0, zt - 0.05)
    B("StoneWall", x0, x1, ty0, y0, 0, zt - 0.05)
    B("StoneWall", x0, x1, y1, ty1, 0, zt - 0.05)
    for (a0, a1, b0, b1) in ((tx0, x0 - 0.4, ty0, ty1), (x1 + 0.4, tx1, ty0, ty1), (x0 - 0.4, x1 + 0.4, ty0, y0 - 0.4), (x0 - 0.4, x1 + 0.4, y1 + 0.4, ty1)):
        B("Patio", a0, a1, b0, b1, zt - 0.05, zt)
    for (a0, a1, b0, b1) in ((x0 - 0.4, x0, y0 - 0.4, y1 + 0.4), (x1, x1 + 0.4, y0 - 0.4, y1 + 0.4), (x0, x1, y0 - 0.4, y0), (x0, x1, y1, y1 + 0.4)):
        B("Stone", a0, a1, b0, b1, zt - 0.05, zt + 0.04)                              # coping, 4 cm proud
    # shell: tile walls inside the cut, floor; water surface 15 cm below the coping
    B("PoolTile", x0, x0 + 0.05, y0, y1, 0.05, zt - 0.05)
    B("PoolTile", x1 - 0.05, x1, y0, y1, 0.05, zt - 0.05)
    B("PoolTile", x0 + 0.05, x1 - 0.05, y0, y0 + 0.05, 0.05, zt - 0.05)
    B("PoolTile", x0 + 0.05, x1 - 0.05, y1 - 0.05, y1, 0.05, zt - 0.05)
    B("PoolTile", x0, x1, y0, y1, 0.0, 0.05)
    K.quad("FxPool", [(x0 * M, y0 * M, (zt - 0.15) * M), (x1 * M, y0 * M, (zt - 0.15) * M), (x1 * M, y1 * M, (zt - 0.15) * M), (x0 * M, y1 * M, (zt - 0.15) * M)],
           uvs=((0, 0), ((x1 - x0) / 2.5, 0), ((x1 - x0) / 2.5, (y1 - y0) / 2.5), (0, (y1 - y0) / 2.5)))
    for i in range(3):
        C("Light", x0 + 0.06, y0 + (i + 1) * (y1 - y0) / 4, zt - 0.4, 0.1, 0.02, segs=8, axis='X')
    # steps down to the lawn (front edge of the terrace)
    sx = steps_y if steps_y is not None else (tx0 + tx1) / 2
    for k in range(3):
        h = zt * (3 - k) / 4
        B("Stone", sx - 1.2, sx + 1.2, ty0 - 0.35 * (k + 1), ty0 - 0.35 * k, 0, h)
    # pool ladder
    for dx in (-0.25, 0.25):
        L("Steel", (x1 - 1.0 + dx, y1 - 0.08, zt + 0.7), (x1 - 1.0 + dx, y1 - 0.08, 0.3), 0.025)
        L("Steel", (x1 - 1.0 + dx, y1 - 0.08, zt + 0.7), (x1 - 1.0 + dx, y1 + 0.25, zt + 0.7), 0.025)


def lounger(x, y, z, rz=0.0):
    c, s = math.cos(rz), math.sin(rz)
    def P(dx, dy):
        return x + dx * c - dy * s, y + dx * s + dy * c
    for t in (-0.7, 0.7):
        px, py = P(0.0, t)
        K.box("Teak", (px * M, py * M, (z + 0.2) * M), (0.7 * M, 0.06 * M, 0.06 * M), rz=rz)
    px, py = P(0, -0.2)
    K.box("Teak", (px * M, py * M, (z + 0.3) * M), (0.7 * M, 1.4 * M, 0.08 * M), rz=rz)
    K.box("Cushion", (px * M, py * M, (z + 0.38) * M), (0.64 * M, 1.34 * M, 0.08 * M), rz=rz)
    for dx in (-0.3, 0.3):
        for dy in (-0.85, 0.45):
            qx, qy = P(dx, dy)
            K.box("Teak", (qx * M, qy * M, (z + 0.13) * M), (0.06 * M, 0.06 * M, 0.26 * M), rz=rz)
    qx, qy = P(0, 0.75)
    K.box("Teak", (qx * M, qy * M, (z + 0.6) * M), (0.7 * M, 0.08 * M, 0.6 * M), rz=rz + 0.0)


def umbrella(x, y, z, r=1.4):
    C("Steel", x, y, z + 1.2, 0.03, 2.4, segs=6)
    C("Alu", x, y, z + 0.05, 0.3, 0.1, segs=10)
    C("Cushion", x, y, z + 2.25, r, 0.35, segs=10, r2=0.06)


def table_set(x, y, z):
    C("Teak", x, y, z + 0.72, 0.6, 0.05, segs=14)
    C("Steel", x, y, z + 0.36, 0.05, 0.72, segs=6)
    for i in range(4):
        a = i / 4 * math.tau + 0.4
        cx, cy = x + math.cos(a) * 0.95, y + math.sin(a) * 0.95
        B("Teak", cx - 0.23, cx + 0.23, cy - 0.23, cy + 0.23, z + 0.42, z + 0.47)
        B("Cushion", cx - 0.21, cx + 0.21, cy - 0.21, cy + 0.21, z + 0.47, z + 0.52)
        for sx in (-0.18, 0.18):
            for sy in (-0.18, 0.18):
                B("Teak", cx + sx - 0.02, cx + sx + 0.02, cy + sy - 0.02, cy + sy + 0.02, z, z + 0.42)


def ivy(ax, plane, facing, a0, a1, z0, z1):
    """Climbing ivy sheet (alpha leaves) just off a wall, with a few clumps standing out."""
    w, h = a1 - a0, z1 - z0
    uv = ((0, 0), (w / 2.2, 0), (w / 2.2, h / 2.2), (0, h / 2.2))
    if ax == "y":
        FY("Ivy", (a0 + a1) / 2, plane + facing * 0.03, z0, w, h, facing=facing, uvs=uv)
    else:
        FX("Ivy", plane + facing * 0.03, (a0 + a1) / 2, z0, w, h, facing=facing, uvs=uv)
    for i in range(int(w * h / 3) + 2):
        a, z = rng.uniform(a0 + 0.3, a1 - 0.3), rng.uniform(z0 + 0.2, z1 - 0.3)
        p = (a, plane + facing * 0.12) if ax == "y" else (plane + facing * 0.12, a)
        K.shrub(p[0] * M, p[1] * M, z * M, rng.uniform(0.15, 0.3) * M, rng, part="Shrub")


def house_number(x, y, z, k, facing=-1):
    """Brass number plate (atlas cell k of 12)."""
    u0, v0 = (k % 4) / 4, 1 - (k // 4 + 1) / 3
    FY("HouseNumbers", x, y, z, 0.42, 0.42, facing=facing, uvs=((u0, v0), (u0 + 0.25, v0), (u0 + 0.25, v0 + 1 / 3), (u0, v0 + 1 / 3)))


def front_wall(y, gaps, h=0.9, part="Walls", cap="Stone", piers=True):
    """Low garden wall along the street at y with gaps [(x0, x1)]; piers with lanterns at the gaps."""
    x = -LW / 2 + 0.3
    edges = sorted(gaps)
    for g0, g1 in edges + [(LW / 2 - 0.3, LW / 2 - 0.3)]:
        if g0 - x > 0.2:
            B(part, x, g0, y - 0.15, y + 0.15, 0, h)
            B(cap, x - 0.03, g0 + 0.03, y - 0.2, y + 0.2, h, h + 0.08)
        x = g1
    if piers:
        for g0, g1 in edges:
            for px in (g0, g1):
                B(part, px - 0.3, px + 0.3, y - 0.3, y + 0.3, 0, h + 0.5)
                B(cap, px - 0.36, px + 0.36, y - 0.36, y + 0.36, h + 0.5, h + 0.6)
                lantern(px, y, h + 0.6)


GATES = [0]


def swing_leaf(x0, x1, y, h, hinge):
    """One openable iron gate leaf (metres) across x0..x1 at y, hinged at x0 ("left") or x1 ("right").
    In game Client/CityDoors swings Swing<n>* round Swing<n>Pivot when a body walks into it."""
    GATES[0] += 1
    n = GATES[0]
    leaf = f"Swing{n}Leaf"
    hx = x1 - 0.05 if hinge == "right" else x0 + 0.05
    far = x0 + 0.02 if hinge == "right" else x1 - 0.02
    lo, hi = min(hx, far), max(hx, far)
    z0, z1 = 0.06, h
    def bx(a0, a1, b0, b1, c0, c1):
        K.boxr(leaf, a0 * M, a1 * M, b0 * M, b1 * M, c0 * M, c1 * M, mat="Iron")
    for xs in (lo, hi - 0.06):                                       # stiles
        bx(xs, xs + 0.06, y - 0.03, y + 0.03, z0, z1)
    for z in (z0, z0 + 0.3, (z0 + z1) * 0.55, z1 - 0.06):             # rails
        bx(lo + 0.06, hi - 0.06, y - 0.025, y + 0.025, z, z + 0.06)
    nb = max(2, int((hi - lo) / 0.12))
    for k in range(1, nb):                                           # bars with spear tips
        x = lo + k * (hi - lo) / nb
        bx(x - 0.013, x + 0.013, y - 0.013, y + 0.013, z0 + 0.06, z1 + 0.1)
        K.cyl(leaf, (x * M, y * M, (z1 + 0.14) * M), 0.03 * M, 0.09 * M, segs=4, r2=0.002 * M, mat="Iron")
    lx = far + (0.07 if hinge == "right" else -0.07)
    K.boxr(f"Swing{n}Latch", (lx - 0.03) * M, (lx + 0.03) * M, (y - 0.06) * M, (y + 0.06) * M, 0.95 * M, 1.05 * M, mat="Bronze")
    for z in (0.3, z1 - 0.3):
        K.cyl(f"Swing{n}Pivot", (hx * M, y * M, z * M), 0.03 * M, 0.18 * M, segs=8, mat="Iron")


def iron_gate(x0, x1, y, h=1.4, open_=0.0):
    """Closed pair of openable iron gate leaves between the pier faces x0..x1 (push to open)."""
    mid = (x0 + x1) / 2
    swing_leaf(x0, mid - 0.02, y, h, "left")
    swing_leaf(mid + 0.02, x1, y, h, "right")


def lot_edges(back="StoneWall", side_h=2.0, front_y=-19.7, side_from=-19.2):
    """Lawn, tall clipped side hedges, and a stone back wall."""
    B("Lawn", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.083, 0)
    hedge(-LW / 2 + 0.1, -LW / 2 + 1.1, side_from, LD / 2 - 0.5, side_h)
    hedge(LW / 2 - 1.1, LW / 2 - 0.1, side_from, LD / 2 - 0.5, side_h)
    B(back, -LW / 2 + 0.1, LW / 2 - 0.1, LD / 2 - 0.5, LD / 2 - 0.1, 0, 2.2)
    B("Stone", -LW / 2 + 0.05, LW / 2 - 0.05, LD / 2 - 0.55, LD / 2 - 0.05, 2.2, 2.3)


def pave(part, x0, x1, y0, y1):
    """Paving laid into the lawn (top 5 cm above the grass, never coplanar)."""
    B(part, x0, x1, y0, y1, -0.05, 0.05)


def chimney(x, y, z0, z1):
    B("Walls", x - 0.5, x + 0.5, y - 0.4, y + 0.4, z0, z1)
    B("Stone", x - 0.6, x + 0.6, y - 0.5, y + 0.5, z1, z1 + 0.12)
    B("Stone", x - 0.3, x + 0.3, y - 0.2, y + 0.2, z1 + 0.12, z1 + 0.45)


def arcade(x0, x1, y, z0, z1, n, t=0.45, pier=0.55, part="Walls", band=0.45):
    """Row of round arches facing -Y on the plane y (front face) .. y + t: piers + arched spandrels."""
    bay = (x1 - x0) / n
    r = (bay - pier) / 2
    zs = z1 - band - r
    for i in range(n + 1):
        px = x0 + i * bay
        B(part, px - pier / 2, px + pier / 2, y, y + t, z0, z1)
        B("Stone", px - pier / 2 - 0.05, px + pier / 2 + 0.05, y - 0.05, y + t + 0.05, zs - 0.12, zs)    # impost
        B("Stone", px - pier / 2 - 0.06, px + pier / 2 + 0.06, y - 0.06, y + t + 0.06, z0, z0 + 0.25)    # base
    bm = K.bm(part)
    segs = 10
    for i in range(n):
        cx = x0 + (i + 0.5) * bay
        arc = [(cx - r * math.cos(k / segs * math.pi), zs + r * math.sin(k / segs * math.pi)) for k in range(segs + 1)]
        def V(x_, yy, z_):
            return bm.verts.new((x_ * M, yy * M, z_ * M))
        fr = [V(ax_, y, az) for ax_, az in arc]
        bk = [V(ax_, y + t, az) for ax_, az in arc]
        tf = [V(ax_, y, z1) for ax_, _ in arc]
        tb = [V(ax_, y + t, z1) for ax_, _ in arc]
        for k in range(segs):
            bm.faces.new([fr[k], fr[k + 1], tf[k + 1], tf[k]])
            bm.faces.new([bk[k + 1], bk[k], tb[k], tb[k + 1]])
            bm.faces.new([fr[k + 1], fr[k], bk[k], bk[k + 1]])              # soffit
            bm.faces.new([tf[k], tf[k + 1], tb[k + 1], tb[k]])
        bm.faces.new([fr[0], tf[0], tb[0], bk[0]])
        bm.faces.new([fr[-1], bk[-1], tb[-1], tf[-1]])
    B("Stone", x0 - pier / 2 - 0.05, x1 + pier / 2 + 0.05, y - 0.08, y + t + 0.08, z1 - 0.18, z1)      # cornice band


VARIANTS = {}


# ================================================================ Casa: Spanish courtyard mansion
def casa():
    lot_edges()
    F1, F2, TOP = 0.4, 3.7, 7.0                # floor 1, floor 2, wall top
    # blocks: main (back of the court), west wing, east wing (garage at the front of the ground floor)
    B("Stone", -8.0, 8.0, 1.95, 11.1, 0, F1)                                     # plinths under each block only
    B("Stone", -14.1, -8.0, -9.6, 11.1, 0, F1)                                     # (the court and loggia stay open)
    B("Stone", 8.0, 14.1, -9.6, 11.1, 0, F1)
    for (x0, x1, y0, y1) in ((-8, 8, 2, 11), (-14, -8, -9.5, 11), (8, 14, -9.5, 11)):
        B("Walls", x0, x1, y0, y1, F1, TOP)
        B("Stone", x0 - 0.04, x1 + 0.04, y0 - 0.04, y1 + 0.04, F2 - 0.12, F2)      # floor band (outside the wall)
    hip(-8, 8, 2, 11, TOP, slope=0.42, over=0.6)
    hip(-14, -8, -9.5, 11, TOP, slope=0.42, over=0.6)
    hip(8, 14, -9.5, 11, TOP, slope=0.42, over=0.6)
    chimney(-11, 6, TOP, TOP + 3.2)
    # loggia: 4 arches across the court front of the main block, balcony on top
    arcade(-7.6, 7.6, -1.6, F1, F2 - 0.15, 4)
    B("Travert", -7.6, 7.6, -1.6, 1.95, 0.0, F1 - 0.02)                            # loggia floor
    B("Deck", -8, 8, -1.8, 2, F2 - 0.15, F2 + 0.05)                                # balcony floor
    rail(-7.9, -1.75, 7.9, -1.75, F2 + 0.05)
    for x in (-7.9, 7.9):
        rail(x, -1.75, x, 1.95, F2 + 0.05)
    for x in (-6.2, -2.1, 2.1, 6.2):
        topiary(x, -1.2, F2 + 0.05, h=0.7, s=0.38)
    FY("FrontDoor", 0, 2, F1, 2.0, 2.6)                                             # front doors in the loggia
    B("Stone", -1.25, 1.25, 1.9, 2.05, F1 + 2.6, F1 + 2.85)
    for x in (-4.6, 4.6):
        win("y", 2, -1, x, F1 + 0.5, 1.6, 2.2)
        K.box("Sconce", (x * M + 1.3 * M, 1.9 * M, (F1 + 2.4) * M), (0.18 * M, 0.16 * M, 0.3 * M))
    for x in (-4.5, 0, 4.5):                                                         # balcony French doors
        win("y", 2, -1, x, F2 + 0.06, 1.5, 2.4, mull=1, transom=True)
    # court: travertine pavers, fountain, hedge borders, pots
    pave("Travert", -7.95, 7.95, -9.5, -1.6)
    fountain(0, -5.6, R=2.2)
    for sx in (-1, 1):
        hedge(sx * 7.6 - 0.35, sx * 7.6 + 0.35, -9.2, -2.4, 0.7)
        flower_bed(sx * 4.8 - 1.2, sx * 4.8 + 1.2, -9.3, -8.3)
        topiary(sx * 6.8, -2.3, 0.05)
    # west wing front: tall windows + a juliet balcony
    for x in (-12.6, -9.4):
        win("y", -9.5, -1, x, F1 + 0.5, 1.3, 2.1)
    B("Deck", -12.6, -9.4, -10.4, -9.5, F2 - 0.1, F2 + 0.05)
    for k in range(3):                                                               # corbels
        B("Stone", -12.4 + k * 1.4 - 0.12, -12.4 + k * 1.4 + 0.12, -10.2, -9.5, F2 - 0.5, F2 - 0.1)
    rail(-12.6, -10.35, -9.4, -10.35, F2 + 0.05)
    rail(-12.6, -10.35, -12.6, -9.55, F2 + 0.05)
    rail(-9.4, -10.35, -9.4, -9.55, F2 + 0.05)
    win("y", -9.5, -1, -11.0, F2 + 0.06, 1.6, 2.4)
    # east wing front: garage door + window above + lanterns
    FY("GarageWood", 11, -9.5, 0.02, 4.6, 2.5)
    B("Stone", 8.55, 13.45, -9.6, -9.5, 2.52, 2.7)
    for x in (8.4, 13.6):
        K.box("Sconce", (x * M, -9.58 * M, 2.2 * M), (0.18 * M, 0.16 * M, 0.3 * M))
    win_row("y", -9.5, -1, 8, 14, F2 + 0.4, 2, 1.3, 1.8)
    # courtyard-facing wing walls + side + back windows
    for x, fc in ((-8, 1), (8, -1)):
        win_row("x", x, fc, -9.0, -2.4, F1 + 0.5, 2, 1.2, 2.0)
        win_row("x", x, fc, -9.0, -2.4, F2 + 0.4, 2, 1.2, 1.8)
    for x, fc in ((-14, -1), (14, 1)):
        win_row("x", x, fc, -9, 11, F1 + 0.5, 5, 1.2, 2.0)
        win_row("x", x, fc, -9, 11, F2 + 0.4, 5, 1.2, 1.8)
    win_row("y", 11, 1, -14, 14, F1 + 0.5, 7, 1.3, 2.1)
    win_row("y", 11, 1, -14, 14, F2 + 0.4, 7, 1.3, 1.8)
    ivy("x", -14, -1, 1.0, 6.0, 0.1, 5.5)
    for (x, y) in ((-14.1, -9.6), (14.1, -9.6), (-14.1, 11.1), (14.1, 11.1)):
        K.downpipe(x * M, y * M, 0, TOP * M)
    # front garden: low wall with an iron gate + driveway gap, hedges, palms, cypresses, trees
    front_wall(-19.6, [(-2.0, 2.0), (8.6, 13.4)])
    iron_gate(-2.0 + 0.3, 2.0 - 0.3, -19.6)
    house_number(-2.0, -19.9, 0.9, 0)
    pave("Pavers", -1.6, 1.6, -19.7, -9.5)
    pave("Pavers", 8.6, 13.4, -20, -9.5)
    hedge(-16.6, -2.5, -18.9, -18.2, 0.9)
    hedge(2.5, 8.2, -18.9, -18.2, 0.9)
    for x in (-2.6, 2.6):
        cypress(x, -16.8, h=6.5)
    palm(-15.8, -14.5, 9.0)
    palm(15.5, -12.0, 8.0)
    tree(-8.5, -14.0, h=7.5, spread=4.5)
    tree(5.0, -14.5, h=6.5, spread=3.8, part="Blossom")
    flower_bed(-16.4, -10.5, -10.6, -9.8)
    for x in (-16.4, -15.6):
        topiary(x, 6.0)
    # back: raised pool terrace, loungers, umbrella, table
    pool(-9, 3, 13.4, 17.2, (-12, 6, 12.0, 19.3))
    for x in (-8.0, -6.2, -4.4):
        lounger(x, 18.6, 0.9, rz=math.pi)
    umbrella(-2.6, 18.6, 0.9)
    table_set(4.5, 15.0, 0.9)
    tree(10.0, 16.0, h=8.0, spread=5.0)
    tree(-15.2, 17.0, h=7.0, spread=4.0)
    bollard(-1.2, -12.5); bollard(1.2, -12.5); bollard(-1.2, -16.0); bollard(1.2, -16.0)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PAINTS if p != "Charcoal"}
    return [("01_front", (14, -46, 9), (0, -2, 3), 26), ("02_aerial", (30, -38, 30), (0, 0, 0), 26),
            ("03_court", (-4.5, -16, 2.0), (1, -4, 2.8), 24), ("04_pool", (-16, 26, 6), (-3, 15, 1), 26)]


# ================================================================ Modern: charcoal + glass villa
def modern():
    lot_edges(back="Render")
    F1, F2, TOP = 0.3, 3.7, 7.2
    # ground volume (charcoal render) with a glass living room at the front left
    B("Concrete", -11.3, 7.3, -4.3, 10.3, 0, F1)
    B("Render", -11, 7, 2, 10, F1, F2)                                          # back half solid
    B("Render", -2.6, 7, -4, 2, F1, F2)                                         # front right: entry + study
    B("Render", -11, -10.6, -4, 2, F1, F2)                                      # glass room end wall
    for k in range(5):                                                           # glass room: big panes, slim frames
        x0 = -10.6 + k * (8.0 / 5)
        FY("GlassBig" + "ABCBA"[k], x0 + 0.8, -4, F1, 1.6, F2 - F1)
        B("Alu", x0 - 0.04, x0 + 0.04, -4.1, -3.95, F1, F2)
    B("Render", -10.6, -2.6, -3.9, 2, F1, F2)                                  # room behind the glass (no hollow box)
    B("Alu", -10.64, -2.56, -4.1, -3.95, F2 - 0.08, F2)
    B("Alu", -10.64, -2.56, -4.1, -3.95, F1, F1 + 0.06)
    # entry: tall pivot door under a concrete canopy, white frame grid on the study front
    FY("PivotDoor", -1.4, -4, F1, 1.3, 3.0)
    B("Concrete", -3.2, 1.2, -6.0, -4, F2 - 0.25, F2)                           # canopy
    for x in (-2.8, 0.8):
        K.box("Light", (x * M, -5.0 * M, (F2 - 0.27) * M), (0.25 * M, 0.25 * M, 0.04 * M))
    for k in range(4):                                                           # study: white frame grid over dark glass
        x0 = 1.0 + k * 1.5
        FY("GlassBig" + "BCAB"[k], x0 + 0.75, -4, F1 + 0.1, 1.5, F2 - F1 - 0.2)
    for x in (1.0, 2.5, 4.0, 5.5, 7.0):
        B("Trim", x - 0.12, x + 0.12, -4.25, -3.95, F1, F2)
    for z in (F1, F2 - 0.24, (F1 + F2) / 2):                                     # rails a touch behind the posts
        B("Trim", 0.88, 7.12, -4.21, -3.95, z, z + 0.24)
    # upper volume: cantilevers forward over the glass room, ribbon windows
    B("Render", -11, 1.0, -5.5, 11, F2, TOP)
    B("Concrete", -11.4, 1.4, -5.9, 11.4, F2 - 0.3, F2)                          # cantilever slab
    B("Concrete", -11.5, 1.5, -6.0, 11.5, TOP, TOP + 0.35)                        # roof slab, overhang
    B("RoofFlat", -11.2, 1.2, -5.7, 11.2, TOP + 0.35, TOP + 0.4)
    for k in range(4):
        FY("GlassBig" + "ACBA"[k], -9.6 + k * 2.6 + 1.2, -5.5, F2 + 0.6, 2.4, 2.3)
        B("Alu", -9.6 + k * 2.6 - 0.05, -9.6 + k * 2.6 + 0.05, -5.62, -5.48, F2 + 0.6, F2 + 2.9)
    B("Alu", -9.65, 0.85, -5.62, -5.48, F2 + 2.85, F2 + 2.95)
    B("Alu", -9.65, 0.85, -5.62, -5.48, F2 + 0.55, F2 + 0.65)
    win_row("x", -11, -1, -5, 10, F2 + 0.8, 4, 1.4, 2.2, mull=0, transom=False)
    win_row("x", 1.0, 1, 2, 10, F2 + 0.8, 3, 1.4, 2.2, mull=0, transom=False)
    win_row("y", 11, 1, -11, 1, F2 + 0.8, 4, 1.8, 2.2, mull=1, transom=False)
    ivy("x", -11, -1, -3.0, 9.0, 0.3, 6.6)
    # roof terrace over the ground floor's right half: deck, glass rail, topiary planters, AC
    B("Concrete", 1.0, 7.3, -4.3, 10.3, F2, F2 + 0.15)
    B("Deck", 1.05, 7.0, -4.0, 10.0, F2 + 0.15, F2 + 0.2)
    glass_rail(1.1, -4.1, 7.1, -4.1, F2 + 0.2)
    glass_rail(7.1, -4.1, 7.1, 10.1, F2 + 0.2)
    for k in range(3):
        x = 2.2 + k * 2.1
        B("Render", x - 0.5, x + 0.5, -3.4, -2.4, F2 + 0.2, F2 + 0.9)
        topiary(x, -2.9, F2 + 0.9, pot=False, h=0.9, s=0.42)
    lounger(4.0, 4.0, F2 + 0.2, rz=0.0)
    lounger(5.6, 4.0, F2 + 0.2, rz=0.0)
    umbrella(2.4, 5.5, F2 + 0.2)
    # side + back ground floor
    win_row("x", 7, 1, 3, 10, F1 + 0.4, 3, 1.4, 2.4, mull=0, transom=False)
    for k in range(6):                                                           # back: full glass to the pool
        FY("GlassBig" + "ABCACB"[k], -10.0 + k * 2.4 + 1.2, 10, F1, 2.4, F2 - F1 - 0.1, facing=1)
        B("Alu", -10.0 + k * 2.4 - 0.05, -10.0 + k * 2.4 + 0.05, 9.98, 10.12, F1, F2 - 0.1)
    # cedar-clad garage with a frosted glass door + flat roof
    B("Concrete", 7.3, 15.3, -2.3, 9.3, 0, 0.15)
    B("Cladding", 7.5, 15.0, -2.0, 9.0, 0.15, 3.3)
    B("Concrete", 7.3, 15.4, -2.6, 9.3, 3.3, 3.55)
    FY("GarageGlass", 11.25, -2.0, 0.15, 5.8, 2.6)
    for x in (8.0, 14.5):
        K.box("Light", (x * M, -2.5 * M, 3.27 * M), (0.25 * M, 0.25 * M, 0.04 * M))
    # forecourt: travertine + paver drive, low white wall, hedges, blossom trees, bollards
    pave("Travert", -3.4, 1.2, -19.6, -4.3)
    pave("Pavers", 8.4, 14.6, -20, -2.3)
    pave("Travert", -11.3, -3.4, -6.4, -4.3)
    front_wall(-19.6, [(-3.4, 1.2), (8.4, 14.6)], h=0.8, part="Concrete", cap="Concrete", piers=False)
    hedge(-16.6, -3.9, -19.15, -18.5, 1.0)
    hedge(1.7, 7.9, -19.15, -18.5, 1.0)
    for y in (-16.0, -12.5, -9.0):
        bollard(-3.9, y)
        bollard(1.7, y)
    tree(-13.5, -13.0, h=6.5, spread=4.2, part="Blossom")
    tree(-7.0, -15.5, h=6.0, spread=3.8, part="Blossom")
    tree(4.8, -12.5, h=5.5, spread=3.4, part="Blossom")
    for x in (-15.5, -12.0, -8.5):
        hedge(x - 1.4, x + 1.4, -9.3, -8.5, 0.8)
    flower_bed(-11.0, -4.0, -8.0, -7.0)
    house_number(-3.5, -20.0, 0.25, 4)
    # back: pool deck + raised pool, loungers
    B("Deck", -11.3, 7.3, 10.3, 12.4, 0, F1)
    pool(-8, 6, 13.6, 17.6, (-11, 9, 12.4, 19.3), zt=F1 + 0.6, steps_y=-10.0)
    for k, x in enumerate((-6.0, -4.2, -2.4)):
        lounger(x, 18.65, F1 + 0.6, rz=math.pi)
    umbrella(0.0, 18.65, F1 + 0.6)
    table_set(12.5, 15.0, 0)
    pave("Patio", 10.2, 15.0, 13.0, 17.0)
    palm(15.5, 18.0, 7.5)
    tree(-15.0, 16.0, h=8.0, spread=4.5)
    VARIANTS["Render"] = {p: f"Wall{p}_Color.png" for p in ("Charcoal", "Slate", "White", "Stone")}
    return [("01_front", (16, -44, 10), (-2, -2, 3), 26), ("02_aerial", (30, -38, 30), (0, 0, 0), 26),
            ("03_entry", (-1, -15, 2.0), (-3, -4, 3.0), 24), ("04_pool", (16, 28, 7), (-1, 14, 1), 26)]


# ================================================================ Villa: two brick balcony bays, brown hip roof
def villa():
    lot_edges()
    F1, F2, TOP = 0.4, 3.7, 7.0
    B("Stone", -15.1, 9.1, -2.1, 9.1, 0, F1)
    B("Walls", -15, 9, -2, 9, F1, TOP)
    B("Stone", -15.04, 9.04, -2.04, 9.04, F2 - 0.12, F2)
    hip(-15, 9, -2, 9, TOP, slope=0.4, over=0.7)
    chimney(4.5, 5.5, TOP, TOP + 3.0)
    # two brick bays: ground floor rooms, balcony on top with a lean-to roof on slim posts
    for bx in (-8.5, 0.5):
        x0, x1 = bx - 2.6, bx + 2.6
        B("Brick", x0, x1, -6.0, -2, 0, F2 - 0.05)
        B("Stone", x0 - 0.08, x1 + 0.08, -6.08, -2, F2 - 0.05, F2 + 0.12)       # balcony slab edge
        B("Deck", x0 + 0.02, x1 - 0.02, -5.98, -2.02, F2 + 0.12, F2 + 0.17)
        win_row("y", -6.0, -1, x0, x1, F1 + 0.6, 2, 1.6, 2.0)
        for xx, fc in ((x0, -1), (x1, 1)):
            win("x", xx, fc, -4.0, F1 + 0.6, 1.3, 2.0)
        rail(x0 + 0.08, -5.9, x1 - 0.08, -5.9, F2 + 0.17)
        rail(x0 + 0.08, -5.9, x0 + 0.08, -2.1, F2 + 0.17)
        rail(x1 - 0.08, -5.9, x1 - 0.08, -2.1, F2 + 0.17)
        for xx in (x0 + 0.1, x1 - 0.1):
            B("Trim", xx - 0.07, xx + 0.07, -5.98, -5.84, F2 + 0.17, F2 + 2.65)
        shed(x0 - 0.2, x1 + 0.2, -6.3, -2, F2 + 2.6, F2 + 3.2)
        for xx in (bx - 1.2, bx + 1.2):
            win("y", -2, -1, xx, F2 + 0.2, 1.3, 2.4, transom=True)                # balcony doors
        topiary(x0 + 0.6, -5.4, F2 + 0.17, h=0.5, s=0.3)
        topiary(x1 - 0.6, -5.4, F2 + 0.17, h=0.5, s=0.3)
    # front door with a small portico, windows on the rest of the front
    FY("FrontDoor", -4.0, -2, F1, 1.9, 2.5)
    B("Stone", -5.4, -2.6, -3.6, -2, 0, F1)
    for x in (-5.2, -2.8):
        C("Trim", x, -3.3, (F1 + 3.1) / 2, 0.14, 3.1 - F1, segs=12)
    B("Trim", -5.5, -2.5, -3.7, -2, 3.1, 3.35)
    shed(-5.6, -2.4, -3.85, -2, 3.35, 3.8)
    K.box("Sconce", (-5.6 * M, -2.08 * M, 2.4 * M), (0.18 * M, 0.16 * M, 0.3 * M))
    win_row("y", -2, -1, 3.4, 9, F1 + 0.5, 2, 1.4, 2.0)
    win_row("y", -2, -1, 3.4, 9, F2 + 0.4, 2, 1.4, 1.8)
    win_row("y", -2, -1, -15, -11.1, F1 + 0.5, 1, 1.4, 2.0)
    win_row("y", -2, -1, -15, -11.1, F2 + 0.4, 1, 1.4, 1.8)
    win("y", -2, -1, -4.0, F2 + 0.4, 1.4, 1.8)
    for x, fc in ((-15, -1), (9, 1)):
        win_row("x", x, fc, -2, 9, F1 + 0.5, 3, 1.3, 2.0)
        win_row("x", x, fc, -2, 9, F2 + 0.4, 3, 1.3, 1.8)
    win_row("y", 9, 1, -15, 9, F1 + 0.5, 6, 1.4, 2.2)
    win_row("y", 9, 1, -15, 9, F2 + 0.4, 6, 1.4, 1.8)
    ivy("y", -2, -1, -15.0, -13.4, 0.4, 6.4)
    ivy("x", 9, 1, 6.0, 8.6, 0.4, 5.0)
    for (x, y) in ((-15.1, -2.1), (9.1, -2.1), (-15.1, 9.1), (9.1, 9.1)):
        K.downpipe(x * M, y * M, 0, TOP * M)
    # garage wing (one floor, hip roof) on the east side
    B("Stone", 9.0, 16.1, -1.1, 9.1, 0, 0.2)
    B("Walls", 9.0, 16, -1, 9, 0.2, 3.4)
    hip(9.0, 16, -1, 9, 3.4, slope=0.4, over=0.5)
    FY("GarageWood", 12.5, -1, 0.2, 5.4, 2.6)
    for x in (9.6, 15.4):
        K.box("Sconce", (x * M, -1.08 * M, 2.4 * M), (0.18 * M, 0.16 * M, 0.3 * M))
    # front garden: low brick wall + hedges, paver drive, path, cypress row, trees
    front_wall(-19.6, [(-5.2, -2.8), (9.6, 15.4)], h=0.7, part="Brick", cap="Stone")
    pave("Pavers", 9.6, 15.4, -20, -1)
    pave("Travert", -4.8, -3.2, -19.7, -3.6)
    pave("Travert", -11.2, 6.6, -7.2, -6.1)
    hedge(-16.6, -5.6, -18.9, -18.2, 1.0)
    hedge(-2.4, 9.1, -18.9, -18.2, 1.0)
    for y in (-16.5, -12.5, -8.5):
        cypress(-16.4, y, h=7.0)
    tree(-10.5, -13.5, h=7.5, spread=4.6)
    tree(4.0, -14.0, h=6.5, spread=4.0)
    flower_bed(-11.0, -6.2, -7.8, -7.3)
    flower_bed(3.2, 6.4, -7.8, -7.3)
    house_number(-5.2, -19.95, 1.0, 8)
    for k in range(3):
        bollard(-5.4, -17 + k * 4)
        bollard(-2.6, -17 + k * 4)
    # back: pergola over a patio, raised pool, loungers
    pave("Patio", -14, 8, 9.2, 12.4)
    for x in (-13.6, -9.6, -5.6):
        for y in (9.6, 12.0):
            B("Teak", x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0.05, 2.8)
    for y in (9.6, 12.0):
        B("Teak", -14.0, -5.2, y - 0.08, y + 0.08, 2.8, 3.05)
    for k in range(12):
        x = -13.8 + k * 0.75
        B("Teak", x - 0.05, x + 0.05, 9.2, 12.4, 3.05, 3.2)
    table_set(-9.6, 10.8, 0.05)
    pool(-4, 8, 13.8, 17.4, (-6, 11, 12.4, 19.3))
    for x in (-3.0, -1.2, 0.6):
        lounger(x, 18.6, 0.9, rz=math.pi)
    umbrella(2.6, 18.6, 0.9)
    tree(-14.0, 16.5, h=8.0, spread=4.8)
    palm(14.5, 15.0, 8.5)
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PAINTS if p != "Charcoal"}
    return [("01_front", (12, -46, 9), (-3, -2, 3), 26), ("02_aerial", (30, -38, 30), (0, 0, 0), 26),
            ("03_balcony", (7, -11, 2.4), (-2, -4, 4.4), 22), ("04_pool", (-18, 26, 6), (-4, 13, 1), 26)]


# ================================================================ Hacienda: arcade ranch, tower, motor court
def hacienda():
    lot_edges()
    F1, TOP, T2 = 0.35, 3.8, 7.3
    B("Stone", -15.1, 15.1, -0.1, 10.1, 0, F1)
    B("Walls", -15, 15, 0, 10, F1, TOP)
    B("Walls", -4, 4, -1.5, 10.25, F1, T2)                                      # tower (proud of the wings, no shared faces)
    hip(-15, -4, 0, 10, TOP, slope=0.38, over=0.6)
    hip(4, 15, 0, 10, TOP, slope=0.38, over=0.6)
    hip(-4, 4, -1.5, 10.25, T2, slope=0.45, over=0.6)
    chimney(-12.0, 7.0, TOP, TOP + 2.6)
    # arcade porches either side of the tower
    for (x0, x1) in ((-14.4, -4.4), (4.4, 10.4)):
        arcade(x0, x1, -3.0, F1, 3.3, 4, t=0.4, pier=0.5)
        B("Travert", x0 - 0.3, x1 + 0.3, -3.0, 0, 0, F1)
        shed(x0 - 0.5, x1 + 0.5, -3.5, 0, 3.4, 3.8)
    # tower front: entry doors, balcony with railing, tall window
    FY("FrontDoor", 0, -1.5, F1, 2.2, 2.8)
    B("Stone", -1.4, 1.4, -1.65, -1.5, F1 + 2.8, F1 + 3.05)
    for x in (-1.6, 1.6):
        K.box("Sconce", (x * M, -1.6 * M, 2.6 * M), (0.18 * M, 0.16 * M, 0.3 * M))
    B("Deck", -2.0, 2.0, -2.6, -1.5, 3.9, 4.05)
    for k in range(3):
        B("Stone", -1.6 + k * 1.6 - 0.12, -1.6 + k * 1.6 + 0.12, -2.4, -1.5, 3.45, 3.9)
    rail(-2.0, -2.55, 2.0, -2.55, 4.05)
    rail(-2.0, -2.55, -2.0, -1.55, 4.05)
    rail(2.0, -2.55, 2.0, -1.55, 4.05)
    win("y", -1.5, -1, 0, 4.06, 1.6, 2.4)
    for x, fc in ((-4, -1), (4, 1)):
        win("x", x, fc, 4.0, 4.4, 1.2, 1.8)
    win_row("y", 10, 1, -4, 4, 4.4, 2, 1.2, 1.8)
    # porch walls: windows + doors behind the arches
    for x in (-12.5, -9.2, -6.0, 6.0, 8.8):
        win("y", 0, -1, x, F1 + 0.5, 1.3, 2.1)
    for x, fc in ((-15, -1), (15, 1)):
        win_row("x", x, fc, 0, 10, F1 + 0.5, 3, 1.2, 2.0)
    win_row("y", 10, 1, -15, -4, F1 + 0.5, 3, 1.4, 2.2)
    win_row("y", 10, 1, 4, 15, F1 + 0.5, 3, 1.4, 2.2)
    ivy("y", -1.5, -1, 2.6, 4.0, 3.0, 7.0)
    # garage behind the east end of the porch line, with its own apron to the east gate
    FY("GarageWood", 12.7, 0, F1, 3.6, 2.4)
    pave("Travert", 10.8, 14.8, -3.0, 0.0)
    # motor court: gravel loop round a fountain, two gates, travertine apron to the porches
    pave("Gravel", -11.0, 11.0, -16.5, -5.0)
    pave("Travert", -14.6, 14.6, -5.0, -3.0)
    B("Lawn", -6.0, 6.0, -13.6, -7.6, -0.05, 0.1)                                 # island lawn (raised a touch)
    B("Stone", -6.1, 6.1, -13.7, -13.6, 0, 0.18); B("Stone", -6.1, 6.1, -7.6, -7.5, 0, 0.18)
    B("Stone", -6.1, -6.0, -13.6, -7.6, 0, 0.18); B("Stone", 6.0, 6.1, -13.6, -7.6, 0, 0.18)
    fountain(0, -10.6, R=2.0, tiers=2)
    for sx in (-1, 1):
        topiary(sx * 4.6, -9.0, 0.1, pot=True)
        topiary(sx * 4.6, -12.2, 0.1, pot=True)
        pave("Gravel", sx * 9.5 - 1.5, sx * 9.5 + 1.5, -20, -16.5)
    front_wall(-19.6, [(-11.0, -8.0), (8.0, 11.0)], h=1.1, part="Walls", cap="Stone")
    for gx in ((-11.0, -8.0), (8.0, 11.0)):
        iron_gate(gx[0] + 0.3, gx[1] - 0.3, -19.6, h=1.5)
    house_number(-8.0, -19.95, 1.2, 1)
    hedge(-7.6, 7.6, -19.0, -18.3, 1.1)
    for x in (-16.0, 16.0):
        palm(x, -14.0, 9.0)
        palm(x * 0.8, -17.5, 7.5)
    for x in (-14.5, 14.5):
        cypress(x, -6.0, h=6.0, r=0.6)
    flower_bed(-14.4, -11.6, -6.2, -5.2)
    flower_bed(11.6, 14.4, -6.2, -5.2)
    # back: pool terrace, loungers, olive trees
    pool(-7, 7, 13.5, 17.3, (-10, 10, 11.5, 19.3))
    for x in (-5.5, -3.7, -1.9):
        lounger(x, 18.6, 0.9, rz=math.pi)
    umbrella(1.2, 18.6, 0.9)
    table_set(13.0, 14.5, 0)
    pave("Patio", 11.0, 15.0, 12.5, 16.5)
    tree(-14.0, 15.5, h=7.0, spread=4.5)
    tree(14.0, 18.0, h=6.0, spread=3.5, part="Blossom")
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in PAINTS if p != "Charcoal"}
    return [("01_front", (16, -46, 9), (0, -3, 3), 26), ("02_aerial", (30, -38, 30), (0, 0, 0), 26),
            ("03_court", (-9, -20, 2.4), (0, -9, 2.2), 26), ("04_pool", (-16, 26, 6), (0, 14, 1), 26)]



# ================================================================ Police: Tulevo Police Department
def police():
    """32 x 50 m lot south of Back Street: two-floor civic block (brick base, stone panels, glass atrium),
    front plaza with flags + monument, side drive with a boom barrier to the secure back car park."""
    W2, D2 = 16.0, 25.4
    F1, F2, TOP = 0.6, 4.6, 8.6
    B("Concrete", -W2, W2, -D2, D2, -0.083, 0)                                     # lot slab
    # ---- building
    X0, X1, Y0, Y1 = -15.0, 8.6, -12.0, 4.0
    B("Stone", X0 - 0.15, X1 + 0.15, Y0 - 0.15, Y1 + 0.15, 0, F1)
    B("Brick", X0, X1, Y0, Y1, F1, F2)
    B("Walls", X0, X1, Y0, Y1, F2, TOP)
    B("Stone", X0 - 0.08, X1 + 0.08, Y0 - 0.08, Y1 + 0.08, F2 - 0.2, F2 + 0.1)        # floor band
    B("Walls", X0 - 0.1, X1 + 0.1, Y0 - 0.1, Y1 + 0.1, TOP, TOP + 0.9)                # parapet
    B("Stone", X0 - 0.16, X1 + 0.16, Y0 - 0.16, Y1 + 0.16, TOP + 0.9, TOP + 1.05)
    B("RoofFlat", X0 + 0.2, X1 - 0.2, Y0 + 0.2, Y1 - 0.2, TOP + 0.1, TOP + 0.15)
    # glass entry atrium (taller, proud of the front), canopy, doors, fascia sign
    AX0, AX1 = -5.0, 2.0
    B("Walls", AX0, AX0 + 0.5, Y0 - 2.0, Y0, F1, TOP - 0.2)                       # piers stop under the head
    B("Walls", AX1 - 0.5, AX1, Y0 - 2.0, Y0, F1, TOP - 0.2)
    B("Walls", AX0, AX1, Y0 - 2.0, Y0, TOP - 0.2, TOP + 1.8)
    B("Stone", AX0 - 0.1, AX1 + 0.1, Y0 - 2.1, Y0 + 0.1, TOP + 1.8, TOP + 1.95)
    for k in range(4):
        FY("GlassBig" + "BCAB"[k], AX0 + 0.5 + (k + 0.5) * 1.5, Y0 - 1.6, F2 + 0.2, 1.5, TOP - F2 - 0.5)
    for k in range(5):
        B("Alu", AX0 + 0.5 + k * 1.5 - 0.05, AX0 + 0.5 + k * 1.5 + 0.05, Y0 - 1.7, Y0 - 1.55, F1, TOP - 0.2)
    B("Walls", AX0 + 0.5, AX1 - 0.5, Y0 - 1.55, Y0, F1, TOP - 0.2)                   # body behind the glass
    FY("PoliceDoor", -1.5, Y0 - 1.6, F1, 2.4, 2.9)
    FY("GlassBigA", -3.75, Y0 - 1.6, F1, 1.5, 2.9)
    FY("GlassBigC", 0.75, Y0 - 1.6, F1, 1.5, 2.9)
    B("Alu", AX0 + 0.5, AX1 - 0.5, Y0 - 1.7, Y0 - 1.55, F1 + 2.9, F1 + 3.1)
    FY("PoliceBadge", -1.5, Y0 - 1.6, F1 + 3.3, 0.85, 0.85)
    B("Concrete", AX0 - 1.0, AX1 + 1.0, Y0 - 5.0, Y0 - 2.0, F1 + 3.6, F1 + 3.9)        # canopy
    for x in (AX0 - 0.6, AX1 + 0.6):
        C("Steel", x, Y0 - 4.6, (F1 + 3.6) / 2 + 0.3, 0.16, F1 + 3.6 - 0.6, segs=12)
    for x in (-4.0, -1.5, 1.0):
        K.box("Light", (x * M, (Y0 - 3.5) * M, (F1 + 3.57) * M), (0.5 * M, 0.5 * M, 0.04 * M))
    FY("PoliceSign", -1.5, Y0 - 2.0, TOP + 0.2, 6.6, 1.1)
    # windows: ribbon of tall windows on both floors (barred low windows on the cell side)
    for a0, a1 in ((X0, AX0), (AX1, X1)):
        win_row("y", Y0, -1, a0 + 0.4, a1 - 0.4, F1 + 0.8, max(1, int((a1 - a0) / 2.3)), 1.5, 2.2, mull=1, transom=True)
        win_row("y", Y0, -1, a0 + 0.4, a1 - 0.4, F2 + 0.7, max(1, int((a1 - a0) / 2.3)), 1.5, 2.2, mull=1, transom=True)
    for x, fc in ((X0, -1), (X1, 1)):
        win_row("x", x, fc, Y0 + 0.5, Y1 - 0.5, F2 + 0.7, 5, 1.4, 2.2, mull=1)
        win_row("x", x, fc, Y0 + 0.5, Y1 - 0.5, F1 + 1.6, 5, 1.0, 1.0, mull=0, transom=False)
    win_row("y", Y1, 1, X0, -2, F2 + 0.7, 5, 1.5, 2.2, mull=1)
    # back: sally port roll door + staff door + lamp
    FY("RollDoor", 3.5, Y1, 0.02, 4.4, 3.4, facing=1)
    B("Concrete", 1.0, 6.0, Y1, Y1 + 1.4, F1 + 3.5, F1 + 3.7)
    FY("PoliceDoor", -6.0, Y1, F1, 1.4, 2.4, facing=1)
    B("Stone", -7.0, -5.0, Y1, Y1 + 1.0, 0, F1)
    for x in (1.2, 5.8, -7.4):
        K.box("Sconce", (x * M, (Y1 + 0.1) * M, 3.4 * M), (0.25 * M, 0.2 * M, 0.35 * M))
    # roof: AC units, comms mast with a red beacon, stair hut
    for (x, y) in ((-11, -6), (-11, -1), (-7, -6), (4, 0)):
        B("Steel", x - 0.9, x + 0.9, y - 0.7, y + 0.7, TOP + 0.15, TOP + 1.3)
        C("Rubber", x, y, TOP + 1.33, 0.5, 0.06, segs=12)
    B("Walls", -1.0, 2.5, -2.0, 2.0, TOP + 0.15, TOP + 2.8)
    B("Stone", -1.1, 2.6, -2.1, 2.1, TOP + 2.8, TOP + 2.95)
    L("Steel", (6.0, -8.0, TOP + 0.15), (6.0, -8.0, TOP + 9.0), 0.08)
    for k in range(6):
        z = TOP + 1.0 + k * 1.3
        L("Steel", (5.6, -8.0, z), (6.4, -8.0, z + 0.6), 0.03)
        L("Steel", (6.0, -8.4, z + 0.6), (6.0, -7.6, z + 1.2), 0.03)
    for k in range(3):
        L("Steel", (6.0, -8.0, TOP + 8.0 - k * 1.5), (6.0 + 0.8, -8.0, TOP + 8.0 - k * 1.5), 0.04)
    C("NeonRed", 6.0, -8.0, TOP + 9.1, 0.12, 0.2, segs=8)
    for k in range(3):
        L("Steel", (6.0, -8.0, TOP + 5), (6.0 + 1.6 * math.cos(k * 2.1), -8.0 + 1.6 * math.sin(k * 2.1), TOP + 0.15), 0.02)
    for (x, y) in ((X0 - 0.2, Y0 - 0.2), (X1 + 0.2, Y0 - 0.2), (X0 - 0.2, Y1 + 0.2), (X1 + 0.2, Y1 + 0.2)):
        K.downpipe(x * M, y * M, 0, TOP * M)
    # ---- front plaza: pavers, steps + ramp, flags, monument, planters, bollards
    pave("Travert", -W2 + 0.3, 9.4, -D2, Y0)
    for k in range(3):
        B("Stone", AX0 - 1.0, AX1 + 1.0, Y0 - 2.0 - 0.45 * (k + 1), Y0 - 2.0 - 0.45 * k, 0, F1 * (3 - k) / 3)
    B("Stone", AX0 - 1.0, AX1 + 1.0, Y0 - 2.0, Y0, 0, F1)
    for k in range(10):                                                              # ramp (sloped, built from thin steps)
        B("Stone", AX1 + 1.0, AX1 + 2.6, Y0 - 2.0 - (k + 1) * 0.6, Y0 - 2.0 - k * 0.6, 0, F1 * (10 - k) / 10)
    rail(AX1 + 2.6, Y0 - 8.0, AX1 + 2.6, Y0 - 2.0, 0.0, h=1.0, step=2.0, part="Steel")
    for i, x in enumerate((-12.5, -10.5, -8.5)):
        C("Steel", x, -20.5, 5.0, 0.07, 10.0, segs=8)
        C("Steel", x, -20.5, 10.05, 0.12, 0.12, segs=8)
        B("Flag", x + 0.07, x + 2.0, -20.52, -20.48, 8.6, 9.8)
    B("Stone", -13.5, -7.5, -21.5, -19.5, 0, 0.3)
    B("Stone", -15.4, -9.2, -24.2, -23.4, 0, 0.3)
    B("Stone", -15.2, -9.4, -24.0, -23.6, 0.3, 1.9)
    FY("PoliceMonument", -12.3, -24.0, 0.45, 4.2, 1.4)
    for x in (-14.8, -9.8):
        C("Light", x, -24.6, 0.08, 0.15, 0.06, segs=8)
    for (x, y) in ((-13.0, -15.5), (6.0, -15.5), (6.0, -20.5)):
        B("Stone", x - 1.4, x + 1.4, y - 1.4, y + 1.4, 0, 0.6)
        B("Soil", x - 1.25, x + 1.25, y - 1.25, y + 1.25, 0.6, 0.62)
        tree(x, y, h=7.0, spread=3.8) if (x, y) != (6.0, -20.5) else palm(x, y, 8.0)
    for x in range(-14, 9, 2):
        if AX0 - 1.4 < x < AX1 + 3.0:
            continue
        C("Steel", x, -24.9, 0.45, 0.13, 0.9, segs=10)
    for x in (AX0 - 0.6, AX1 + 0.6, -6.2, 3.8):
        C("Steel", x, -24.9, 0.45, 0.13, 0.9, segs=10)
    # ---- east drive + boom barrier, back car park, fences
    pave("Asphalt", 9.6, W2 - 0.3, -D2, Y1)
    B("Asphalt", -W2 + 0.3, W2 - 0.3, Y1, D2 - 0.4, -0.05, 0.05)
    for k in range(9):                                                               # stalls along the back wall
        x = -14.5 + k * 2.8
        B("Paint", x - 0.06, x + 0.06, 19.6, D2 - 0.6, 0.05, 0.06)
    for k in range(4):                                                               # stalls along the west wall
        y = 7.0 + k * 2.8
        B("Paint", -W2 + 0.5, -W2 + 5.6, y - 0.06, y + 0.06, 0.05, 0.06)
    for k in range(8):
        x = -12.0 + k * 2.8
        B("Rubber", x - 0.9, x + 0.9, 23.6, 23.9, 0.05, 0.2)                          # wheel stops
    B("Yellow", 0.5, 7.0, 5.6, 5.75, 0.05, 0.06)                                     # sally port keep-clear box
    B("Yellow", 0.5, 7.0, 10.4, 10.55, 0.05, 0.06)
    # boom barrier across the drive at y = 6 (Lift1: arm lifts 85 deg when someone comes near)
    BY = 6.5
    B("Concrete", 14.5, 15.6, BY - 0.6, BY + 0.6, 0, 0.12)
    B("Steel", 14.7, 15.4, BY - 0.35, BY + 0.35, 0.12, 1.1)
    B("Yellow", 14.75, 15.35, BY - 0.36, BY + 0.36, 0.95, 1.0)
    K.cyl("Lift1Pivot", (15.05 * M, (BY - 0.38) * M, 1.0 * M), 0.12 * M, 0.08 * M, segs=10, axis='Y', mat="Steel")
    for k in range(10):
        x0 = 14.9 - (k + 1) * 0.55
        K.boxr("Lift1Arm", x0 * M, (x0 + 0.55) * M, (BY - 0.47) * M, (BY - 0.41) * M, 0.95 * M, 1.07 * M, mat="Red" if k % 2 else "Paint")
    B("Steel", 9.8, 10.0, BY - 0.6, BY - 0.4, 0, 0.95)                               # arm rest post
    # perimeter: tall stone wall west + back, iron fence on the east edge, gatehouse lamp posts
    B("StoneWall", -W2, -W2 + 0.4, Y0, D2, 0, 2.4)
    B("StoneWall", -W2, W2, D2 - 0.4, D2, 0, 2.4)
    for (a0, a1, b0, b1) in ((-W2 - 0.05, -W2 + 0.45, Y0, D2), (-W2 - 0.05, W2 + 0.05, D2 - 0.45, D2 + 0.05)):
        B("Stone", a0, a1, b0, b1, 2.4, 2.5)
    rail(W2 - 0.15, Y1 + 2.5, W2 - 0.15, D2 - 0.45, 0.0, h=2.2, step=0.15)
    rail(X1 + 0.2, Y1 + 2.5, 9.6, Y1 + 2.5, 0.0, h=2.2, step=0.15)
    for (x, y) in ((-12.0, 13.0), (0.0, 13.0), (12.0, 15.0), (13.0, -8.0)):
        C("Steel", x, y, 3.5, 0.1, 7.0, segs=8)
        L("Steel", (x, y, 7.0), (x + 0.0, y - 1.2, 7.0), 0.06)
        K.lamp((x * M, (y - 1.2) * M, 6.92 * M), (0.6 * M, 0.35 * M, 0.12 * M))
    # hedges along the sidewalk either side of the plaza
    VARIANTS["Walls"] = {p: f"Wall{p}_Color.png" for p in ("Stone", "White", "Sand", "Slate")}
    return [("01_front", (14, -48, 8), (-3, -6, 5), 26), ("02_aerial", (34, -40, 34), (0, 0, 0), 26),
            ("03_entry", (5, -24, 2.0), (-1.5, -12, 4.0), 24), ("04_back", (-14, 30, 10), (2, 8, 1), 26)]

shots = {"Police": police, "Casa": casa, "Modern": modern, "Villa": villa, "Hacienda": hacienda}[ONLY]()

K.finish(keep_normals=("Palm", "Ivy"), face=A["face"])
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
        K.shot(name, tuple(v * M for v in loc), tuple(v * M for v in target), lens=lens)
