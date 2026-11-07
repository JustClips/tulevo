"""Fort Halden: an original army base west of the city (gate, fence, barracks, tower, yard, pines).

  blender --background --python build_army.py -- OUT_DIR [--face E] [--no-render] [--samples N] [--res F]

Run tools/army_textures.py first (writes ./tex). One model, ArmyBase, origin = ground centre,
built in studs (M = 3.6 studs per metre), front (the gate) = -Y; --face E turns it so the gate
faces the city (Roblox +X).

Layout (metres, before turning):
  perimeter fence x -60..60, y -50..55: galvanised chain-link, Y-arm barbed strands, razor coil
  gate (y -50): concrete canopy with the FORT HALDEN sign, guard booth on the centre island,
      red/white boom barriers (in-lane up, out-lane down), STOP / ID CHECK sign, speed bumps,
      jersey barriers and a sandbag post outside
  control tower (40, -36): tapered concrete shaft, glass cab, catwalk, antennas, red beacon
  barracks 101/102 (east), 103/104 (north) and HQ: two storeys, ribbed steel siding, real
      windows, steel doors with canopies, outside stairs, roof HVAC, downpipes, number plates
  training yard (west front): dirt, pull-up rig, monkey bars, climbing wall, tyre run,
      balance logs, crawl frame, bleachers, its own low chain-link fence
  motor pool (west back): open olive steel shed with camo net, drums, crates
  watchtowers in the four corners, street lamps, flagpole, parking bays, pines all round.

Part names drive the game side (src/server/CityBuildings.server.luau): Lamp<n> lamps,
Light* glow, NeonRed beacon, Sconce door lights, ChainLink / RazorWire / CamoNet see-through,
Leaf* (pine foliage) never collides, Deco* thin dressing does not collide.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402
from mathutils import Vector  # noqa: E402

A = args(r"C:\out\army")
NAME = model_name("ArmyBase", A)
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")
K = Kit(NAME, A["out"], TEX)
rng = random.Random(1944)


def m(v):
    return v * M


# ---------------------------------------------------------------- materials
for name, sheet, tile in (("Grass", "Grass", 4), ("Asphalt", "Asphalt", 6), ("Dirt", "Dirt", 4), ("Gravel", "Gravel", 2.5),
                          ("Concrete", "Concrete", 3), ("ConcreteDark", "ConcreteDark", 3), ("Roof", "Roof", 4),
                          ("Siding", "Siding", 2), ("SidingOlive", "SidingOlive", 2), ("Bark", "Bark", 1.5),
                          ("Planks", "Planks", 2), ("Canvas", "Canvas", 1.5), ("Sandbag", "Sandbag", 0.8),
                          ("Steel", "Steel", 1.5), ("Tread", "Tread", 1), ("Needles", "Needles", 2.2)):
    K.mat(name, sheet=sheet, tile=(m(tile), m(tile)))
K.mat("Hvac", sheet="Hvac", tile=(m(1.0), m(1.0)))
for name in ("GateSign", "SignRestricted", "SignStop", "SignSpeed", "SignNoPhoto", "Flag", "Door", "RollDoor", "HvacTop",
             "Plate101", "Plate102", "Plate103", "Plate104", "PlateHQ", "PlateMotorpool", "PlateRangetower", "TowerGlassA"):
    K.mat(name, sheet=name, explicit=True)
for name in ("ChainLink", "RazorWire", "CamoNet"):
    K.mat(name, sheet=name, explicit=True, alpha=True, metal=0.5 if name != "CamoNet" else 0, rough=0.5)
for name in ("PaintYellow", "PaintWhite", "BoomRed", "BoomWhite", "Olive", "DarkSteel", "Rubber", "Tire", "Hesco"):
    K.mat(name, sheet=name, tile=None)
for name, col, rough, metal, emit in (("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
                                      ("NeonRed", (1.0, 0.12, 0.10), 0.5, 0, 6.0), ("Black", (0.03, 0.03, 0.035), 0.5, 0.3, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats(frame=(0.20, 0.21, 0.22), sill=(0.70, 0.70, 0.68))


# ---------------------------------------------------------------- helpers (metres in, studs out)
def box(part, x0, x1, y0, y1, z0, z1, mat=None):
    K.boxr(part, m(x0), m(x1), m(y0), m(y1), m(z0), m(z1), mat=mat)


COLS = []   # invisible box colliders (metres, unturned): the meshes themselves never collide in game


def col(name, x0, x1, y0, y1, z0, z1):
    COLS.append((name, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1))


def boxc(part, c, s, rz=0.0, mat=None):
    K.box(part, (m(c[0]), m(c[1]), m(c[2])), (m(s[0]), m(s[1]), m(s[2])), rz=rz, mat=mat)


def cyl(part, c, r, h, segs=10, r2=None, mat=None, axis='Z'):
    K.cyl(part, (m(c[0]), m(c[1]), m(c[2])), m(r), m(h), segs=segs, r2=None if r2 is None else m(r2), mat=mat, axis=axis)


def rod(part, a, b, r, segs=6, mat=None):
    K.cyl_along(part, tuple(m(v) for v in a), tuple(m(v) for v in b), m(r), segs=segs, mat=mat)


def panel(part, a, b, z0, z1, tile=1.2, both=True, mat=None):
    """Vertical textured quad from a to b (x, y metres), UVs tiled every `tile` metres. both = a
    second face pointing the other way (Roblox hides back faces)."""
    ax, ay = a
    bx, by = b
    L = math.hypot(bx - ax, by - ay)
    u, v0, v1 = L / tile, z0 / tile, z1 / tile
    c = [(m(ax), m(ay), m(z0)), (m(bx), m(by), m(z0)), (m(bx), m(by), m(z1)), (m(ax), m(ay), m(z1))]
    K.quad(part, c, ((0, v0), (u, v0), (u, v1), (0, v1)), mat=mat)
    if both:
        K.quad(part, c[::-1], ((0, v1), (u, v1), (u, v0), (0, v0)), mat=mat)


def sign(part, c, w, h, facing, z0, post=True, both_posts=False):
    """Printed sign board on a steel post; facing = -1 (seen from -Y) / +1 (+Y) / 'x+' 'x-'."""
    x, y = c
    if facing in (-1, 1):
        K.face_y(part, m(x), m(y + facing * 0.03), m(z0), m(w), m(h), facing=facing)
        box("DarkSteel", x - w / 2 - 0.03, x + w / 2 + 0.03, y - 0.02, y + 0.02, z0 - 0.03, z0 + h + 0.03)
        posts = (x - w / 2 + 0.1, x + w / 2 - 0.1) if both_posts else (x,)
        if post:
            for px in posts:
                box("Steel", px - 0.04, px + 0.04, y - facing * 0.02 - 0.04, y - facing * 0.02 + 0.04, 0, z0 + h - 0.05)
    else:
        f = 1 if facing == "x+" else -1
        K.face_x(part, m(x + f * 0.03), m(y), m(z0), m(w), m(h), facing=f)
        box("DarkSteel", x - 0.02, x + 0.02, y - w / 2 - 0.03, y + w / 2 + 0.03, z0 - 0.03, z0 + h + 0.03)
        if post:
            box("Steel", x - f * 0.02 - 0.04, x - f * 0.02 + 0.04, y - 0.04, y + 0.04, 0, z0 + h - 0.05)


def tube(part, a, b, r, segs=8, tile=1.0):
    """Open tube from a to b (metres) with explicit UVs: u along (every `tile` m), v around.
    Faces both ways so the see-through coil reads from inside too."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    t = d.normalized()
    n1 = t.cross(Vector((0, 0, 1)))
    if n1.length < 1e-4:
        n1 = t.cross(Vector((1, 0, 0)))
    n1.normalize()
    n2 = t.cross(n1)
    for i in range(segs):
        a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
        o0 = (n1 * math.cos(a0) + n2 * math.sin(a0)) * r
        o1 = (n1 * math.cos(a1) + n2 * math.sin(a1)) * r
        q = [a + o0, b + o0, b + o1, a + o1]
        q = [tuple(m(v) for v in p) for p in q]
        uv = ((0, i / segs), (L / tile, i / segs), (L / tile, (i + 1) / segs), (0, (i + 1) / segs))
        K.quad(part, q, uv)
        K.quad(part, q[::-1], uv[::-1])


# ---------------------------------------------------------------- site extents
FX0, FX1, FY0, FY1 = -60.0, 60.0, -50.0, 55.0          # perimeter fence
GX0, GX1, GY0, GY1 = -72.0, 72.0, -68.0, 66.0          # model ground
ROAD_HW = 6.1                                          # half width of the city road (44 studs)
GATE_HW = 10.0                                         # half width of the fence opening

# heights (metres) keep surfaces apart: no two coplanar faces anywhere
Z_GRASS, Z_DIRT, Z_ASPH, Z_PAINT, Z_WALK = 0.0, 0.03, 0.06, 0.075, 0.16

# ground: grass everywhere except the approach corridor in front of the gate (the city road runs there)
for gx0, gx1, gy0, gy1 in ((GX0, GX1, FY0 - 2, GY1), (GX0, -ROAD_HW, GY0, FY0 - 2), (ROAD_HW, GX1, GY0, FY0 - 2)):
    box("Grass", gx0, gx1, gy0, gy1, Z_GRASS - 0.3, Z_GRASS)
    col("Floor", gx0, gx1, gy0, gy1, Z_GRASS - 1.0, Z_GRASS)

# asphalt: gate apron + entry road, the main core, and the motor pool lot
ASPH = [(-ROAD_HW, ROAD_HW, FY0 - 2, -32), (-20, 52, -32, 8), (-56, 52, 8, 50), (-23.5, -20, -32, 8)]
for x0, x1, y0, y1 in ASPH:
    box("Asphalt", x0, x1, y0, y1, Z_ASPH - 0.3, Z_ASPH)
    col("Floor", x0, x1, y0, y1, Z_ASPH - 1.0, Z_ASPH)
# the gate lanes widen out under the canopy
for s_ in (-1, 1):
    box("Asphalt", min(s_ * ROAD_HW, s_ * (GATE_HW - 0.2)), max(s_ * ROAD_HW, s_ * (GATE_HW - 0.2)), FY0 - 6, FY0 + 6, Z_ASPH - 0.3, Z_ASPH)
    col("Floor", s_ * ROAD_HW, s_ * (GATE_HW - 0.2), FY0 - 6, FY0 + 6, Z_ASPH - 1.0, Z_ASPH)


# ---------------------------------------------------------------- perimeter fence
POST_H = 3.0


def fence_run(a, b, h=POST_H, step=3.0, wire=True, coil=True, gaps=()):
    """Chain-link fence from a to b (x, y): posts every `step` m, rails, mesh both sides,
    a Y-arm on each post with three barbed strands and a razor-wire coil along the top."""
    a, b = Vector((*a, 0)), Vector((*b, 0))
    L = (b - a).length
    d = (b - a) / L
    out = Vector((d.y, -d.x, 0))            # left-hand normal: outside of a clockwise loop
    n = max(1, round(L / step))
    pts = [a + d * (L * i / n) for i in range(n + 1)]
    inside = lambda p: any(g0 <= (p - a).dot(d) <= g1 for g0, g1 in gaps)
    for i, p in enumerate(pts):
        if inside(p) and not (i == 0 or i == n):
            continue
        end = i in (0, n)
        cyl("FenceSteel", (p.x, p.y, h / 2), 0.05 if not end else 0.07, h, segs=8, mat="Steel")
        cyl("ConcreteDark", (p.x, p.y, 0.08), 0.16, 0.16, segs=8)          # footing
        if wire:   # Y-arm outrigger
            for s_ in (-1, 1):
                tip = p + out * (0.32 * s_) + Vector((0, 0, h + 0.42))
                rod("FenceSteel", (p.x, p.y, h - 0.05), tuple(tip), 0.022, segs=4, mat="Steel")
    for i in range(n):
        p0, p1 = pts[i], pts[i + 1]
        if inside((p0 + p1) / 2):
            continue
        panel("ChainLink", (p0.x, p0.y), (p1.x, p1.y), 0.05, h - 0.05, tile=0.6)
        col("Fence", p0.x - 0.06, p1.x + 0.06, p0.y - 0.06, p1.y + 0.06, 0, h + (0.5 if wire else 0.1))
        for z in (h - 0.05, 0.12):
            rod("FenceSteel", (p0.x, p0.y, z), (p1.x, p1.y, z), 0.025, segs=5, mat="Steel")
        if wire:
            for s_ in (-1, 1):
                for k in (1, 2, 3):
                    o = out * (0.32 * s_ * k / 3)
                    zz = h - 0.05 + 0.42 * k / 3
                    rod("DecoWire", (p0.x + o.x, p0.y + o.y, zz), (p1.x + o.x, p1.y + o.y, zz), 0.006, segs=3, mat="DarkSteel")
        if coil:
            tube("RazorWire", (p0.x, p0.y, h + 0.25), (p1.x, p1.y, h + 0.25), 0.36, segs=8, tile=0.9)


# clockwise when seen from above with the outside on the left-hand normal
fence_run((FX0, FY0), (-GATE_HW - 1.0, FY0))
fence_run((GATE_HW + 1.0, FY0), (FX1, FY0))
fence_run((FX1, FY0), (FX1, FY1))
fence_run((FX1, FY1), (FX0, FY1))
fence_run((FX0, FY1), (FX0, FY0))
# sliding gate leaves (door system: Slide<N>, src door/gate system from the city thread): closed
# across the drive just behind the canopy side walls; each slides its own length toward its
# Slide<N>Pivot, out of the way behind the fence. Guards can lock them later (Lock_Slide<N>).
SLIDE_Y = FY0 + 9.6
for n, s_ in ((1, -1), (2, 1)):
    x_a, x_b = 0.0, s_ * (GATE_HW + 0.9)
    y = SLIDE_Y
    P = f"Slide{n}"
    for x in (x_a + s_ * 0.05, x_b - s_ * 0.05):
        cyl(P + "Leaf", (x, y, 1.25), 0.045, 2.3, segs=6, mat="Steel")
    for z in (0.18, 1.25, 2.35):
        rod(P + "Leaf", (x_a, y, z), (x_b, y, z), 0.035, segs=6, mat="Steel")
    rod(P + "Leaf", (x_a, y, 0.2), (x_b, y, 2.35), 0.025, segs=5, mat="Steel")       # diagonal brace
    panel(P + "Mesh", (x_a, y), (x_b, y), 0.18, 2.35, tile=0.6, mat="ChainLink")
    for x in (x_a + s_ * 0.5, x_b - s_ * 0.5):
        cyl(P + "Wheel", (x, y, 0.1), 0.1, 0.08, segs=10, axis='Y', mat="Rubber")
    # pivot = the gate's guide post beyond the leaf's far end (marks the slide direction)
    px = s_ * (GATE_HW + 1.25)
    box(P + "Pivot", px - 0.08, px + 0.08, y - 0.2, y + 0.2, Z_GRASS, 2.5, mat="DarkSteel")
    # the rail it rolls on, out to where it parks
    box("DarkSteel", min(0, s_ * 2 * (GATE_HW + 1.0)), max(0, s_ * 2 * (GATE_HW + 1.0)), y - 0.05, y + 0.05, Z_ASPH, Z_ASPH + 0.03)


# restricted-area signs on the fence every ~24 m, facing out
def fence_signs():
    for x in range(-48, 49, 24):
        if abs(x) < 14:
            continue
        K.face_y("SignRestricted", m(x), m(FY0 - 0.06), m(1.3), m(0.8), m(0.6), facing=-1)
        K.face_y("SignRestricted", m(x), m(FY1 + 0.06), m(1.3), m(0.8), m(0.6), facing=1)
    for y in range(-36, 50, 24):
        K.face_x("SignRestricted", m(FX0 - 0.06), m(y), m(1.3), m(0.8), m(0.6), facing=-1)
        K.face_x("SignRestricted", m(FX1 + 0.06), m(y), m(1.3), m(0.8), m(0.6), facing=1)


fence_signs()


# ---------------------------------------------------------------- gate: canopy, booth, barriers
def gate():
    y0, y1 = FY0 - 4.0, FY0 + 4.0         # canopy depth (8 m)
    z0, z1 = 5.4, 7.0
    # roof slab + fascia
    box("Concrete", -GATE_HW - 1.2, GATE_HW + 1.2, y0, y1, z0, z1)
    box("ConcreteDark", -GATE_HW - 1.3, GATE_HW + 1.3, y0 - 0.1, y1 + 0.1, z1, z1 + 0.12)
    # sign on both fascias
    K.face_y("GateSign", 0, m(y0 - 0.02), m(z0 + 0.06), m(6.0), m(1.5), facing=-1)
    K.face_y("GateSign", 0, m(y1 + 0.02), m(z0 + 0.06), m(6.0), m(1.5), facing=1)
    # columns (square concrete, two each side)
    for x in (-GATE_HW - 0.6, GATE_HW + 0.6):
        for y in (y0 + 0.6, y1 - 0.6):
            box("Concrete", x - 0.4, x + 0.4, y - 0.4, y + 0.4, Z_ASPH, z0)
            col("Column", x - 0.5, x + 0.5, y - 0.5, y + 0.5, 0, z0)
            box("ConcreteDark", x - 0.5, x + 0.5, y - 0.5, y + 0.5, Z_ASPH, 0.5)
    # under-canopy lights (two rows)
    for x in (-6.5, -2.5, 2.5, 6.5):
        for y in (y0 + 2, y1 - 2):
            K.lamp((m(x), m(y), m(z0 - 0.05)), (m(1.2), m(0.3), m(0.08)))
    # side walls joining the canopy to the fence (concrete, 2.4 m) with sandbag tops
    for s_ in (-1, 1):
        box("Concrete", min(s_ * (GATE_HW + 0.3), s_ * (GATE_HW + 0.9)), max(s_ * (GATE_HW + 0.3), s_ * (GATE_HW + 0.9)), y0 + 0.2, FY0 + 9, Z_GRASS, 2.4)
        col("Wall", s_ * (GATE_HW + 0.25), s_ * (GATE_HW + 0.95), y0 + 0.15, FY0 + 9.05, 0, 2.5)
        box("ConcreteDark", min(s_ * (GATE_HW + 0.25), s_ * (GATE_HW + 0.95)), max(s_ * (GATE_HW + 0.25), s_ * (GATE_HW + 0.95)), y0 + 0.15, FY0 + 9.05, 2.4, 2.5)
    # centre island + guard booth
    box("ConcreteDark", -1.3, 1.3, y0 - 3.0, y1 + 1.0, Z_ASPH - 0.05, Z_WALK + 0.06)
    box("PaintYellow", -1.32, 1.32, y0 - 3.02, y0 - 2.6, Z_ASPH, Z_WALK + 0.07)          # painted nose
    bx0, bx1, by0, by1, bz = -1.05, 1.05, FY0 - 1.6, FY0 + 1.6, Z_WALK + 0.06
    H = 2.7
    col("Island", -1.3, 1.3, y0 - 3.0, y1 + 1.0, 0, Z_WALK + 0.06)
    col("Booth", bx0 - 0.05, bx1 + 0.05, by0 - 0.05, by1 + 0.05, 0, bz + H + 0.22)
    box("Concrete", bx0, bx1, by0, by1, bz, bz + 0.9)                                    # solid lower wall
    for c in ((bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1)):                           # corner posts
        box("DarkSteel", c[0] - 0.06, c[0] + 0.06, c[1] - 0.06, c[1] + 0.06, bz + 0.9, bz + H)
    # glass band all round (the window sheets see into a lit booth)
    gz0, gz1 = bz + 0.95, bz + H - 0.15
    K.face_y("TowerGlassA", 0, m(by0 - 0.01), m(gz0), m(bx1 - bx0 - 0.12), m(gz1 - gz0), facing=-1)
    K.face_y("TowerGlassA", 0, m(by1 + 0.01), m(gz0), m(bx1 - bx0 - 0.12), m(gz1 - gz0), facing=1)
    K.face_x("TowerGlassA", m(bx0 - 0.01), m(by0 + 0.8), m(gz0), m(1.4), m(gz1 - gz0), facing=-1)
    K.face_x("TowerGlassA", m(bx1 + 0.01), m(by0 + 0.8), m(gz0), m(1.4), m(gz1 - gz0), facing=1)
    K.face_x("Door", m(bx1 + 0.01), m(by1 - 0.75), m(bz), m(0.85), m(2.1), facing=1,
             uvs=((0, 0), (1, 0), (1, 1), (0, 1)))
    K.face_x("Door", m(bx0 - 0.01), m(by1 - 0.75), m(bz), m(0.85), m(2.1), facing=-1)
    box("Concrete", bx0 + 0.02, bx1 - 0.02, by0 + 0.02, by1 - 0.02, bz + 0.9, gz0)       # wall top band
    box("Concrete", bx0 + 0.02, bx1 - 0.02, by0 + 0.02, by1 - 0.02, gz1, bz + H)
    box("Roof", bx0 - 0.35, bx1 + 0.35, by0 - 0.35, by1 + 0.35, bz + H, bz + H + 0.18)  # overhanging roof
    box("Black", bx0 - 0.36, bx1 + 0.36, by0 - 0.36, by1 + 0.36, bz + H + 0.18, bz + H + 0.22)
    K.lamp((0, m(by0 - 0.2), m(bz + H - 0.02)), (m(0.6), m(0.15), m(0.06)))
    # boom barriers (door system: Lift<N>): post on the island, arm down across each lane; the
    # system lifts the arm ~85 deg about Lift<N>Pivot (the pivot box on top of the post).
    for n, s_ in ((1, 1), (2, -1)):        # Lift1 = in lane (+x), Lift2 = out lane (-x)
        px, py = s_ * 1.0, FY0 - 2.8 * s_
        P = f"Lift{n}"
        box("BoomWhite", px - 0.22, px + 0.22, py - 0.22, py + 0.22, Z_WALK, Z_WALK + 0.85)
        col("Post", px - 0.24, px + 0.24, py - 0.24, py + 0.24, 0, Z_WALK + 0.9)
        box("BoomRed", px - 0.24, px + 0.24, py - 0.24, py + 0.24, Z_WALK + 0.85, Z_WALK + 0.9)
        hz = Z_WALK + 1.05
        box(P + "Pivot", px - 0.16, px + 0.16, py - 0.16, py + 0.16, hz - 0.15, hz + 0.15, mat="DarkSteel")
        L = GATE_HW - 1.6
        seg = L / 7
        for k in range(7):    # one connected arm: alternating red/white sleeves along it
            x_a, x_b = px + s_ * (0.16 + k * seg), px + s_ * (0.16 + (k + 1) * seg)
            box(P + ("Arm" if k % 2 == 0 else "Stripes"), min(x_a, x_b), max(x_a, x_b), py - 0.05, py + 0.05, hz - 0.05, hz + 0.05,
                mat="BoomRed" if k % 2 == 0 else "BoomWhite")
        x_end = px + s_ * (0.16 + L)
        box(P + "Arm", min(px, x_end) - 0.0, max(px, x_end), py - 0.03, py + 0.03, hz - 0.075, hz - 0.05, mat="BoomRed")  # under-rail ties the sleeves
        # rest post where the arm end sits
        box("BoomWhite", x_end - s_ * 0.3 - 0.1, x_end - s_ * 0.3 + 0.1, py - 0.1, py + 0.1, Z_ASPH, hz - 0.06)
        box("NeonRed", px - 0.06, px + 0.06, py - 0.25, py - 0.2, Z_WALK + 0.6, Z_WALK + 0.72)
    # stop lines, lane arrows, speed bumps, centre line on the approach
    for s_ in (-1, 1):
        box("PaintWhite", s_ * 1.5, s_ * (GATE_HW - 0.6), FY0 - 6.5 if s_ > 0 else FY0 + 6.0,
            FY0 - 6.1 if s_ > 0 else FY0 + 6.4, Z_ASPH, Z_PAINT)
        y = FY0 - 12
        for k in range(8):       # yellow/black speed bump
            mat = "PaintYellow" if k % 2 == 0 else "Rubber"
            x_a = s_ * (0.6 + k * (ROAD_HW - 0.8) / 8)
            x_b = s_ * (0.6 + (k + 1) * (ROAD_HW - 0.8) / 8)
            box(mat, min(x_a, x_b), max(x_a, x_b), y - 0.3, y + 0.3, Z_ASPH, Z_ASPH + 0.08)
    for y in range(int(FY0) + 8, -34, 4):
        for s_ in (-0.12, 0.12):
            box("PaintYellow", s_ - 0.06, s_ + 0.06, y, y + 2.4, Z_ASPH, Z_PAINT)
    # STOP / ID CHECK + speed signs on the approach shoulder, facing incoming traffic (-Y)
    sign("SignStop", (ROAD_HW + 2.2, FY0 - 9.0), 1.1, 0.82, -1, 1.4)
    sign("SignSpeed", (ROAD_HW + 2.2, FY0 - 22.0), 0.9, 0.68, -1, 1.5)
    sign("SignNoPhoto", (-ROAD_HW - 2.2, FY0 - 9.0), 1.1, 0.82, -1, 1.4)
    # jersey barriers + sandbag guard post outside the gate
    for s_ in (-1, 1):
        for k in range(4):
            jersey(s_ * (ROAD_HW + 0.7), FY0 - 3.5 - k * 3.2, math.pi / 2)
    sandbag_post(-GATE_HW - 6.0, FY0 - 4.5, 3.2, 2.4)
    for s_ in (-1, 1):
        col("Barrier", s_ * (ROAD_HW + 0.4), s_ * (ROAD_HW + 1.0), FY0 - 3.5 - 3 * 3.2 - 1.5, FY0 - 3.5 + 1.5, 0, Z_ASPH + 0.81)
        col("Hesco", s_ * (GATE_HW + 1.5), s_ * (GATE_HW + 2.0 + 4 * 1.1 + 0.5), FY0 - 1.5, FY0 - 0.5, 0, 1.24)
    # hesco barrier walls either side of the canopy, outside the fence
    for s_ in (-1, 1):
        for k in range(5):
            hesco(s_ * (GATE_HW + 2.0 + k * 1.1), FY0 - 1.0)


def jersey(x, y, rz, L=3.0):
    """Concrete jersey barrier: wide foot, sloped faces, narrow top."""
    prof = [(-0.30, 0.0), (0.30, 0.0), (0.30, 0.08), (0.16, 0.33), (0.08, 0.81), (-0.08, 0.81), (-0.16, 0.33), (-0.30, 0.08)]
    bm = K.bm("ConcreteDark")
    c, s = math.cos(rz), math.sin(rz)
    rings = []
    for e in (-L / 2, L / 2):
        ring = []
        for w, z in prof:
            lx, ly = e, w
            ring.append(bm.verts.new((m(x + lx * c - ly * s), m(y + lx * s + ly * c), m(Z_ASPH + z))))
        rings.append(ring)
    n = len(prof)
    for i in range(n):
        bm.faces.new([rings[0][i], rings[0][(i + 1) % n], rings[1][(i + 1) % n], rings[1][i]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])


def hesco(x, y, s=1.0):
    """Hesco-style gabion: mesh-sided box filled with earth."""
    box("Hesco", x - 0.5 * s, x + 0.5 * s, y - 0.5 * s, y + 0.5 * s, Z_GRASS, 1.2 * s)
    box("Dirt", x - 0.46 * s, x + 0.46 * s, y - 0.46 * s, y + 0.46 * s, 1.2 * s, 1.24 * s)
    for dx in (-0.5, 0.5):
        for dy in (-0.5, 0.5):
            box("Steel", x + dx * s - 0.02, x + dx * s + 0.02, y + dy * s - 0.02, y + dy * s + 0.02, Z_GRASS, 1.22 * s)


def sandbags(x0, y0, x1, y1, rows=4, z0=Z_GRASS):
    """Sandbag wall from (x0,y0) to (x1,y1): staggered pillow bags."""
    col("Sandbags", x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2, 0, z0 + rows * 0.152)
    a, b = Vector((x0, y0)), Vector((x1, y1))
    L = (b - a).length
    d = (b - a) / L
    rz = math.atan2(d.y, d.x)
    bl, bh = 0.6, 0.16
    for r_ in range(rows):
        off = (bl / 2) * (r_ % 2)
        n = int((L - off) / bl)
        for i in range(n):
            t = off + (i + 0.5) * bl
            p = a + d * t
            boxc("Sandbag", (p.x, p.y, z0 + bh / 2 + r_ * bh * 0.95), (bl * 0.96, 0.36, bh), rz=rz)


def sandbag_post(x, y, w, dpt):
    sandbags(x - w / 2, y - dpt / 2, x + w / 2, y - dpt / 2, rows=6)
    sandbags(x - w / 2, y - dpt / 2, x - w / 2, y + dpt / 2, rows=6)
    sandbags(x + w / 2, y - dpt / 2, x + w / 2, y + dpt / 2 - 0.9, rows=6)
    for c in ((x - w / 2, y + dpt / 2), (x + w / 2, y + dpt / 2), (x - w / 2, y - dpt / 2), (x + w / 2, y - dpt / 2)):
        box("Planks", c[0] - 0.06, c[0] + 0.06, c[1] - 0.06, c[1] + 0.06, Z_GRASS, 2.3)
    box("Canvas", x - w / 2 - 0.3, x + w / 2 + 0.3, y - dpt / 2 - 0.3, y + dpt / 2 + 0.3, 2.3, 2.38)


# ---------------------------------------------------------------- buildings
WINDOWS = ("GlassA", "GlassB", "GlassC", "GlassD")


def building(cx, cy, w, d, plate, floors=2, front=-1, stairs=True, porch=True, part="Siding"):
    """Two-storey barracks block centred at (cx, cy), w along x, d along y, front facing -Y (front=-1)
    or +Y. Ribbed steel siding on a concrete plinth, floor band, real windows, steel doors with
    canopies and lamps, outside steel stair to the upper floor, flat roof with parapet + HVAC."""
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    fh = 3.4
    top = floors * fh + 0.4
    # footpath round the building (raised concrete), then the plinth and walls
    box("Concrete", x0 - 1.6, x1 + 1.6, y0 - 1.6, y1 + 1.6, Z_ASPH - 0.1, Z_WALK)
    box("ConcreteDark", x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, Z_WALK, 0.6)
    box(part, x0, x1, y0, y1, 0.6, top)
    col("Building", x0 - 0.06, x1 + 0.06, y0 - 0.06, y1 + 0.06, 0, top + 0.55)
    for f in range(1, floors):                                       # floor band
        box("DarkSteel", x0 - 0.06, x1 + 0.06, y0 - 0.06, y1 + 0.06, f * fh + 0.25, f * fh + 0.45)
    # roof: slab, parapet coping, HVAC units, hatch, vent stacks, antenna
    box("Roof", x0 + 0.25, x1 - 0.25, y0 + 0.25, y1 - 0.25, top - 0.01, top + 0.1)
    for (a0, a1, b0, b1) in ((x0 - 0.08, x1 + 0.08, y0 - 0.08, y0 + 0.25), (x0 - 0.08, x1 + 0.08, y1 - 0.25, y1 + 0.08),
                             (x0 - 0.08, x0 + 0.25, y0 + 0.25, y1 - 0.25), (x1 - 0.25, x1 + 0.08, y0 + 0.25, y1 - 0.25)):
        box("Steel", a0, a1, b0, b1, top, top + 0.55)
    n_hvac = max(2, int(w / 8))
    for i in range(n_hvac):
        hx = x0 + (i + 0.6) * w / n_hvac
        hy = cy + (d / 4 if i % 2 else -d / 6)
        hvac(hx, hy, top + 0.1)
    box("DarkSteel", cx - 0.5, cx + 0.5, y1 - 2.2, y1 - 1.2, top + 0.1, top + 0.55)        # roof hatch
    for i in range(3):
        cyl("Steel", (x0 + 2 + i * 3.1, cy + d / 2 - 0.9, top + 0.5), 0.1, 0.8, segs=8)
    rod("DarkSteel", (x1 - 1.0, y1 - 1.0, top + 0.1), (x1 - 1.0, y1 - 1.0, top + 3.5), 0.03, segs=5)
    # windows: both long sides, every ~3 m, both floors; short sides: 2 per floor
    per = max(3, int(w / 3.0))
    for f in range(floors):
        z = f * fh + 1.5 if f == 0 else f * fh + 1.2
        for i in range(per):
            a = x0 + (i + 0.5) * w / per
            if f == 0 and abs(a - cx) < 1.6:
                continue     # front door
            for plane, facing in ((y0, -1), (y1, 1)):
                K.window3d("y", m(plane), facing, m(a), m(z), m(1.25), m(1.35), glass=WINDOWS[(i + f + facing) % 4],
                           depth=m(0.1), fw=m(0.06), mull=1, sill=True, head=False)
        for j in (-1, 1):
            K.window3d("x", m(x0), -1, m(cy + j * d / 4), m(z), m(1.0), m(1.35), glass=WINDOWS[(f + j) % 4],
                       depth=m(0.1), fw=m(0.06), mull=0, head=False)
            if not (stairs and f >= 1):
                K.window3d("x", m(x1), 1, m(cy + j * d / 4), m(z), m(1.0), m(1.35), glass=WINDOWS[(f - j) % 4],
                           depth=m(0.1), fw=m(0.06), mull=0, head=False)
    # front + back doors (double steel doors), canopy, lamp, steps
    for plane, facing in ((y0, -1), (y1, 1)):
        for k in (-0.46, 0.46):
            K.face_y("Door", m(cx + k), m(plane + facing * 0.02), m(0.6), m(0.9), m(2.15), facing=facing)
        box("Frame", cx - 1.0, cx + 1.0, plane + facing * 0.0 - 0.06, plane + facing * 0.0 + 0.06, 2.75, 2.85)
        y_a, y_b = sorted((plane, plane + facing * 1.4))
        box("DarkSteel", cx - 1.5, cx + 1.5, y_a, y_b, 3.0, 3.12)            # door canopy
        for k in (-1.4, 1.4):
            rod("Steel", (cx + k, plane + facing * 1.3, 3.0), (cx + k, plane, 3.5), 0.025, segs=4)
        box("Sconce", cx - 0.12, cx + 0.12, plane + facing * 0.05 - 0.05, plane + facing * 0.05 + 0.05, 2.9, 2.98)
        ys = sorted((plane, plane + facing * 1.2))
        box("Concrete", cx - 1.3, cx + 1.3, ys[0], ys[1], Z_WALK, 0.45)
        if plate and facing == front:
            K.face_y(plate, m(cx + 2.4), m(plane + facing * 0.03), m(2.0), m(1.6), m(0.5), facing=facing)
    # wall lamps on the long sides (shine onto the path)
    for i in range(3):
        a = x0 + (i + 0.5) * w / 3
        for plane, facing in ((y0, -1), (y1, 1)):
            if abs(a - cx) < 2.5:
                continue
            ya, yb = sorted((plane, plane + facing * 0.35))
            box("DarkSteel", a - 0.2, a + 0.2, ya, yb, 6.1, 6.25)
            box("LightWall", a - 0.15, a + 0.15, min(plane, plane + facing * 0.31), max(plane, plane + facing * 0.31), 6.04, 6.1, mat="Light")
    # downpipes at the corners, wall A/C units on the back
    for x, y in ((x0 + 0.2, y0 - 0.12), (x1 - 0.2, y0 - 0.12), (x0 + 0.2, y1 + 0.12), (x1 - 0.2, y1 + 0.12)):
        K.downpipe(m(x), m(y), m(0.2), m(top + 0.3))
    for i in range(2):
        a = x0 + w * (0.3 + 0.4 * i)
        box("Hvac", a - 0.5, a + 0.5, y1 + 0.05, y1 + 0.65, 0.65, 1.45)
    # outside steel stair to the upper floor door on the +x end
    if stairs and floors > 1:
        sx = x1 + 0.1
        z_land = fh + 0.45
        land_y0, land_y1 = y1 - 3.0, y1 - 0.4
        box("Tread", sx, sx + 1.4, land_y0, land_y1, z_land - 0.1, z_land)                  # landing
        K.face_x("Door", m(x1 + 0.02), m(land_y0 + 1.2), m(z_land), m(0.95), m(2.15), facing=1)
        steps = 13
        for i in range(steps):
            t = (i + 1) / (steps + 1)
            yy = land_y0 - (steps - i) * 0.28
            box("Tread", sx + 0.05, sx + 1.35, yy - 0.14, yy + 0.14, z_land * t - 0.04, z_land * t)
        for k in (sx + 0.05, sx + 1.35):                                                   # stringers + rail
            rod("Steel", (k, land_y0 - steps * 0.28 - 0.2, 0.2), (k, land_y0, z_land), 0.05, segs=5)
            rod("Steel", (k, land_y0 - steps * 0.28 - 0.2, 1.1), (k, land_y0, z_land + 1.0), 0.025, segs=5)
        rod("Steel", (sx + 1.35, land_y0, z_land + 1.0), (sx + 1.35, land_y1, z_land + 1.0), 0.025, segs=5)
        for yy in (land_y0, land_y1):
            rod("Steel", (sx + 1.35, yy, 0.6), (sx + 1.35, yy, z_land + 1.0), 0.04, segs=6)


def hvac(x, y, z):
    box("Hvac", x - 0.8, x + 0.8, y - 0.6, y + 0.6, z, z + 1.0)
    K.quad("HvacTop", [(m(x - 0.78), m(y - 0.58), m(z + 1.01)), (m(x + 0.78), m(y - 0.58), m(z + 1.01)),
                       (m(x + 0.78), m(y + 0.58), m(z + 1.01)), (m(x - 0.78), m(y + 0.58), m(z + 1.01))])
    box("DarkSteel", x - 0.85, x + 0.85, y - 0.65, y + 0.65, z - 0.08, z)


# ---------------------------------------------------------------- control tower
def tower(cx, cy):
    """Tapered octagonal concrete shaft with a glass cab, catwalk, roof antennas and a red beacon,
    and a one-storey annex at its foot."""
    import bmesh
    shaft_h, r0, r1 = 26.0, 3.4, 2.5
    col("Tower", cx - 2.9, cx + 2.9, cy - 2.9, cy + 2.9, 0, shaft_h + 5.5)
    cyl("Concrete", (cx, cy, shaft_h / 2), r0, shaft_h, segs=8, r2=r1)
    # vertical pilasters (the ribbed look of the reference tower)
    for i in range(8):
        a = (i + 0.5) / 8 * math.tau
        p0 = (cx + math.cos(a) * (r0 * 0.93 + 0.12), cy + math.sin(a) * (r0 * 0.93 + 0.12), 0.0)
        p1 = (cx + math.cos(a) * (r1 * 0.93 + 0.12), cy + math.sin(a) * (r1 * 0.93 + 0.12), shaft_h)
        rod("ConcreteDark", p0, p1, 0.22, segs=4)
    # cab: wider octagon, outward-slanted glass, catwalk, roof
    z0 = shaft_h
    cyl("ConcreteDark", (cx, cy, z0 + 0.3), 3.2, 0.6, segs=8, r2=4.6)                   # corbel
    cyl("Concrete", (cx, cy, z0 + 0.8), 4.9, 0.4, segs=8)                               # catwalk floor
    bm = K.bm("TowerGlassA")
    uv = bm.loops.layers.uv.active
    ra, rb, za, zb = 4.0, 4.5, z0 + 1.6, z0 + 4.4
    for i in range(8):
        a0, a1 = i / 8 * math.tau + math.pi / 8, (i + 1) / 8 * math.tau + math.pi / 8
        q = [(cx + math.cos(a0) * ra, cy + math.sin(a0) * ra, za), (cx + math.cos(a1) * ra, cy + math.sin(a1) * ra, za),
             (cx + math.cos(a1) * rb, cy + math.sin(a1) * rb, zb), (cx + math.cos(a0) * rb, cy + math.sin(a0) * rb, zb)]
        f = bm.faces.new([bm.verts.new(tuple(m(v) for v in p)) for p in q])
        for l, t in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l[uv].uv = t
    cyl("Concrete", (cx, cy, z0 + 1.3), 4.05, 0.6, segs=8)                               # cab sill wall
    for i in range(8):                                                                   # mullions
        a = i / 8 * math.tau + math.pi / 8
        rod("Black", (cx + math.cos(a) * ra, cy + math.sin(a) * ra, za), (cx + math.cos(a) * rb, cy + math.sin(a) * rb, zb), 0.07, segs=4)
    cyl("DarkSteel", (cx, cy, zb + 0.25), 5.0, 0.5, segs=8, r2=4.7)                      # roof
    cyl("Roof", (cx, cy, zb + 0.55), 4.6, 0.1, segs=8)
    for i in range(16):                                                                  # catwalk railing
        a0, a1 = i / 16 * math.tau, (i + 1) / 16 * math.tau
        p0 = (cx + math.cos(a0) * 4.8, cy + math.sin(a0) * 4.8)
        p1 = (cx + math.cos(a1) * 4.8, cy + math.sin(a1) * 4.8)
        rod("Steel", (*p0, z0 + 1.0), (*p0, z0 + 2.1), 0.03, segs=4)
        rod("Steel", (*p0, z0 + 2.1), (*p1, z0 + 2.1), 0.03, segs=4)
        rod("Steel", (*p0, z0 + 1.55), (*p1, z0 + 1.55), 0.02, segs=4)
    # antennas, radar dish, beacon
    rod("Steel", (cx, cy, zb + 0.6), (cx, cy, zb + 6.5), 0.08, segs=6)
    for k in range(4):
        rod("Steel", (cx, cy, zb + 1.5 + k * 1.2), (cx + 0.8, cy, zb + 1.5 + k * 1.2), 0.02, segs=4)
    cyl("NeonRed", (cx, cy, zb + 6.65), 0.16, 0.3, segs=8)
    cyl("Steel", (cx + 2.2, cy + 1.0, zb + 1.2), 0.06, 1.2, segs=6)
    cyl("PaintWhite", (cx + 2.2, cy + 1.0, zb + 2.0), 0.75, 0.25, segs=12, r2=0.3)
    for a in (0.5, 2.3, 4.1):
        cyl("Light", (cx + math.cos(a) * 4.9, cy + math.sin(a) * 4.9, zb + 0.2), 0.14, 0.14, segs=8)
    # annex at the foot (door, plate)
    ax0, ax1, ay0, ay1 = cx - 4.5, cx + 4.5, cy - r0 - 4.2, cy - r0 + 0.5
    box("Concrete", ax0 - 1.2, ax1 + 1.2, ay0 - 1.4, ay1 + 1.2, Z_GRASS - 0.1, Z_WALK)
    box("Concrete", ax0, ax1, ay0, ay1, Z_WALK, 3.6)
    col("Building", ax0, ax1, ay0, ay1, 0, 3.75)
    box("Roof", ax0 - 0.2, ax1 + 0.2, ay0 - 0.2, ay1 + 0.2, 3.6, 3.75)
    for k in (-0.46, 0.46):
        K.face_y("Door", m(cx + k), m(ay0 - 0.02), m(Z_WALK), m(0.9), m(2.15), facing=-1)
    K.face_y("PlateRangetower", m(cx + 2.6), m(ay0 - 0.03), m(2.1), m(2.0), m(0.62), facing=-1)
    for a in (cx - 3.2, cx + 3.2):
        K.window3d("y", m(ay0), -1, m(a), m(1.3), m(1.2), m(1.2), glass="GlassA", depth=m(0.1), fw=m(0.06), mull=1, head=False)
    box("Sconce", cx - 0.12, cx + 0.12, ay0 - 0.1, ay0, 2.6, 2.7)
    hvac(cx + 3.2, ay0 + 2.0, 3.75)


# ---------------------------------------------------------------- training yard
def training_yard(x0, x1, y0, y1):
    box("Dirt", x0, x1, y0, y1, Z_DIRT - 0.2, Z_DIRT)
    col("Floor", x0, x1, y0, y1, Z_DIRT - 1.0, Z_DIRT)
    # low chain-link fence round it with a gap on the +x side (door to the core)
    gap = ((y0 + y1) / 2 - 2.5 - y0, (y0 + y1) / 2 + 2.5 - y0)
    fence_run((x0, y0), (x1, y0), h=2.2, step=3.0, wire=False, coil=False)
    fence_run((x1, y0), (x1, y1), h=2.2, step=3.0, wire=False, coil=False, gaps=(gap,))
    fence_run((x1, y1), (x0, y1), h=2.2, step=3.0, wire=False, coil=False)
    fence_run((x0, y1), (x0, y0), h=2.2, step=3.0, wire=False, coil=False)
    # pull-up rig: 4 bars at stepped heights
    px, py = x0 + 5, y1 - 5
    for i in range(5):
        cyl("Steel", (px + i * 1.4, py, 1.4), 0.06, 2.8, segs=8)
        cyl("ConcreteDark", (px + i * 1.4, py, Z_DIRT + 0.05), 0.15, 0.1, segs=8)
    for i in range(4):
        rod("Steel", (px + i * 1.4, py, 2.1 + 0.2 * i), (px + (i + 1) * 1.4, py, 2.1 + 0.2 * i), 0.025, segs=6)
    # monkey bars
    mx, my = x0 + 5, y1 - 11
    for dy in (-0.5, 0.5):
        for k in range(2):
            cyl("Steel", (mx + k * 6, my + dy, 1.2), 0.06, 2.4, segs=8)
        rod("Steel", (mx, my + dy, 2.35), (mx + 6, my + dy, 2.35), 0.05, segs=6)
    for k in range(13):
        rod("Steel", (mx + k * 0.5, my - 0.5, 2.35), (mx + k * 0.5, my + 0.5, 2.35), 0.025, segs=5)
    # climbing wall (planks on a frame) with a back platform
    wx, wy = x0 + 18, y1 - 6
    box("Planks", wx - 2, wx + 2, wy - 0.1, wy + 0.1, Z_DIRT, 2.6)
    col("Wall", wx - 2.1, wx + 2.1, wy - 0.1, wy + 1.4, 0, 2.6)
    for k in (-2, 2):
        box("Planks", wx + k - 0.08, wx + k + 0.08, wy - 0.1, wy + 1.4, Z_DIRT, 2.6)
    box("Planks", wx - 2, wx + 2, wy + 0.1, wy + 1.4, 1.4, 1.5)
    for k in range(5):
        rod("DarkSteel", (wx - 1.6 + k * 0.8, wy - 0.1, 2.6), (wx - 1.6 + k * 0.8 + 0.1, wy - 0.12, 0.3), 0.02, segs=4)
    # tyre run: 2 x 8 tyres lying flat
    tx, ty = x0 + 16, y0 + 6
    for i in range(8):
        for j in range(2):
            c = (tx + i * 0.95 + j * 0.45, ty + j * 0.95)
            cyl("Tire", (*c, Z_DIRT + 0.11), 0.42, 0.22, segs=12)
            cyl("Rubber", (*c, Z_DIRT + 0.12), 0.24, 0.22, segs=10)
    # balance logs on stumps
    for k in range(3):
        bx_, by_ = x0 + 4 + k * 4.5, y0 + 13 + (k % 2) * 1.2
        rod("Bark", (bx_, by_, 0.55 + k * 0.15), (bx_ + 4, by_, 0.55 + k * 0.15), 0.14, segs=8)
        for e in (bx_ + 0.3, bx_ + 3.7):
            cyl("Bark", (e, by_, (0.55 + k * 0.15) / 2), 0.16, 0.55 + k * 0.15, segs=8)
    # crawl frame: low posts with barbed strands
    cx_, cy_ = x0 + 4, y0 + 4
    for i in range(5):
        for j in (0, 3):
            cyl("Planks", (cx_ + i * 2, cy_ + j, 0.35), 0.06, 0.7, segs=6)
    for i in range(4):
        for j in (0, 3):
            rod("DecoWire", (cx_ + i * 2, cy_ + j, 0.6), (cx_ + (i + 1) * 2, cy_ + j, 0.6), 0.008, segs=3, mat="DarkSteel")
        for t in (0.5, 1.5, 2.5):
            rod("DecoWire", (cx_ + i * 2, cy_ + t, 0.62), (cx_ + (i + 1) * 2, cy_ + t, 0.62), 0.008, segs=3, mat="DarkSteel")
    for i in range(5):
        rod("DecoWire", (cx_ + i * 2, cy_, 0.6), (cx_ + i * 2, cy_ + 3, 0.6), 0.008, segs=3, mat="DarkSteel")
    # bleachers (4 tiers of planks on a steel frame) facing the yard
    bx0, by0 = x1 - 3.2, y1 - 14
    col("Bleachers", bx0, bx0 + 2.8, by0, by0 + 9, 0, 1.0)
    for t in range(4):
        z = 0.45 + t * 0.45
        box("Planks", bx0 + t * 0.7, bx0 + t * 0.7 + 0.55, by0, by0 + 9, z - 0.06, z)
        box("Planks", bx0 + t * 0.7 - 0.05, bx0 + t * 0.7 + 0.02, by0, by0 + 9, z - 0.45, z - 0.1)
    for k in range(4):
        y = by0 + 0.3 + k * 2.8
        rod("Steel", (bx0 - 0.05, y, Z_DIRT), (bx0 + 2.7, y, 2.0), 0.04, segs=5)
        rod("Steel", (bx0 + 2.7, y, Z_DIRT), (bx0 + 2.7, y, 2.0), 0.04, segs=5)
    # instructor hut (olive siding) + sandbag wall
    hx, hy = x1 - 4, y0 + 4
    box("SidingOlive", hx - 2.2, hx + 2.2, hy - 1.8, hy + 1.8, Z_DIRT, 2.8)
    col("Building", hx - 2.2, hx + 2.2, hy - 1.8, hy + 1.8, 0, 2.95)
    box("DarkSteel", hx - 2.5, hx + 2.5, hy - 2.1, hy + 2.1, 2.8, 2.95)
    K.face_x("Door", m(hx - 2.22), m(hy), m(Z_DIRT), m(0.9), m(2.1), facing=-1)
    K.window3d("y", m(hy - 1.8), -1, m(hx), m(1.1), m(1.2), m(1.0), glass="GlassB", depth=m(0.08), fw=m(0.05), mull=1, head=False)
    sandbags(x0 + 22, y0 + 2, x0 + 22, y0 + 9, rows=5, z0=Z_DIRT)


# ---------------------------------------------------------------- motor pool
def motor_pool(x0, x1, y0, y1):
    h = 5.2
    n = int((x1 - x0) / 5)
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        for y in (y0, y1):
            box("DarkSteel", x - 0.15, x + 0.15, y - 0.15, y + 0.15, Z_ASPH, h)
            col("Column", x - 0.15, x + 0.15, y - 0.15, y + 0.15, 0, h)
        rod("DarkSteel", (x, y0, h), (x, y1, h + 0.6), 0.12, segs=6)
    # pitched corrugated roof (one slope, a bit of fall to the front)
    q = [(x0 - 0.6, y0 - 0.8, h + 0.08), (x1 + 0.6, y0 - 0.8, h + 0.08), (x1 + 0.6, y1 + 0.8, h + 0.7), (x0 - 0.6, y1 + 0.8, h + 0.7)]
    K.quad("ShedRoof", [tuple(m(v) for v in p) for p in q], mat="SidingOlive")
    K.quad("ShedRoof", [tuple(m(v) for v in p) for p in q[::-1]], mat="SidingOlive")
    # back wall + roll doors in a side store
    box("SidingOlive", x0, x1, y1 - 0.1, y1 + 0.1, Z_ASPH, h)
    col("Wall", x0, x1, y1 - 0.1, y1 + 0.1, 0, h)
    col("Drums", x0 + 0.7, x0 + 1.3 + 9 * 0.75, y1 - 1.1, y1 - 0.5, 0, Z_ASPH + 0.92)
    col("Crates", x1 - 2 - 5 * 1.4 - 0.6, x1 - 1.4, y1 - 1.6, y1 - 0.4, 0, Z_ASPH + 1.5)
    K.face_y("PlateMotorpool", m((x0 + x1) / 2), m(y0 - 0.9), m(h - 0.85), m(3.2), m(0.7), facing=-1)
    for i in range(n):
        x = x0 + (i + 0.5) * (x1 - x0) / n
        box("LightShed", x - 0.6, x + 0.6, (y0 + y1) / 2 - 0.12, (y0 + y1) / 2 + 0.12, h - 0.1, h - 0.02, mat="Light")
    # camo net draped off the front edge
    for i in range(n):
        xa, xb = x0 + i * (x1 - x0) / n, x0 + (i + 1) * (x1 - x0) / n
        q = [(xa, y0 - 0.9, h + 0.1), (xb, y0 - 0.9, h + 0.1), (xb, y0 - 2.6, 2.6 + (i % 2) * 0.6), (xa, y0 - 2.6, 2.4 + ((i + 1) % 2) * 0.6)]
        uvs = ((0, 0), (2.5, 0), (2.5, 1.2), (0, 1.2))
        K.quad("CamoNet", [tuple(m(v) for v in p) for p in q], uvs)
        K.quad("CamoNet", [tuple(m(v) for v in p) for p in q[::-1]], uvs[::-1])
    # drums, jerry cans, crates, pallets along the back wall
    for i in range(10):
        x = x0 + 1 + i * 0.75
        cyl("Olive", (x, y1 - 0.8, Z_ASPH + 0.45), 0.29, 0.9, segs=12)
        cyl("DarkSteel", (x, y1 - 0.8, Z_ASPH + 0.91), 0.27, 0.02, segs=12)
    for i in range(6):
        x = x1 - 2 - i * 1.4
        box("Planks", x - 0.6, x + 0.6, y1 - 1.6, y1 - 0.4, Z_ASPH, Z_ASPH + 0.15)
        box("Olive", x - 0.55, x + 0.55, y1 - 1.5, y1 - 0.5, Z_ASPH + 0.15, Z_ASPH + 0.9 + (i % 2) * 0.6)
    # parking bays under the shed
    for i in range(n + 1):
        x = x0 + i * (x1 - x0) / n
        box("PaintYellow", x - 0.06, x + 0.06, y0 + 0.5, y1 - 2.0, Z_ASPH, Z_PAINT)


# ---------------------------------------------------------------- watchtowers, lamps, flag, pines
def watchtower(x, y):
    h = 6.0
    for dx in (-1.2, 1.2):
        for dy in (-1.2, 1.2):
            rod("DarkSteel", (x + dx * 1.15, y + dy * 1.15, Z_GRASS), (x + dx, y + dy, h), 0.08, segs=6)
            col("Leg", x + dx * 1.1 - 0.15, x + dx * 1.1 + 0.15, y + dy * 1.1 - 0.15, y + dy * 1.1 + 0.15, 0, h)
            cyl("ConcreteDark", (x + dx * 1.15, y + dy * 1.15, 0.12), 0.25, 0.24, segs=8)
    for z in (2.0, 4.0):
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            rod("DarkSteel", (x + a[0] * 1.2, y + a[1] * 1.2, z - 1.0), (x + b[0] * 1.2, y + b[1] * 1.2, z), 0.03, segs=4)
    box("Tread", x - 1.6, x + 1.6, y - 1.6, y + 1.6, h, h + 0.15)
    box("Planks", x - 1.6, x + 1.6, y - 1.6, y - 1.45, h + 0.15, h + 1.15)
    box("Planks", x - 1.6, x + 1.6, y + 1.45, y + 1.6, h + 0.15, h + 1.15)
    box("Planks", x - 1.6, x - 1.45, y - 1.45, y + 1.45, h + 0.15, h + 1.15)
    box("Planks", x + 1.45, x + 1.6, y - 1.45, y + 0.5, h + 0.15, h + 1.15)
    for dx in (-1.5, 1.5):
        for dy in (-1.5, 1.5):
            box("DarkSteel", x + dx - 0.05, x + dx + 0.05, y + dy - 0.05, y + dy + 0.05, h + 0.15, h + 2.6)
    box("SidingOlive", x - 1.9, x + 1.9, y - 1.9, y + 1.9, h + 2.6, h + 2.75)
    box("DarkSteel", x + 1.3, x + 1.6, y - 1.6, y - 1.3, h + 1.15, h + 1.45)
    K.lamp((m(x + 1.45), m(y - 1.45), m(h + 1.12)), (m(0.3), m(0.3), m(0.06)))
    # ladder on the +x side
    for dy in (0.6, 1.1):
        rod("Steel", (x + 1.65, y + dy, Z_GRASS), (x + 1.65, y + dy, h + 1.0), 0.03, segs=4)
    for k in range(int(h / 0.3)):
        rod("Steel", (x + 1.65, y + 0.6, 0.3 + k * 0.3), (x + 1.65, y + 1.1, 0.3 + k * 0.3), 0.02, segs=4)


def street_lamp(x, y, rz):
    cyl("Steel", (x, y, 3.8), 0.09, 7.6, segs=8, r2=None)
    col("Pole", x - 0.15, x + 0.15, y - 0.15, y + 0.15, 0, 7.6)
    cyl("ConcreteDark", (x, y, 0.2), 0.3, 0.4, segs=8)
    dx, dy = math.cos(rz), math.sin(rz)
    rod("Steel", (x, y, 7.4), (x + dx * 1.6, y + dy * 1.6, 7.6), 0.05, segs=6)
    boxc("DarkSteel", (x + dx * 1.8, y + dy * 1.8, 7.6), (0.8, 0.35, 0.16), rz=rz)
    K.lamp((m(x + dx * 1.8), m(y + dy * 1.8), m(7.51)), (m(0.6), m(0.24), m(0.03)))


def flagpole(x, y):
    cyl("Steel", (x, y, 6.0), 0.07, 12.0, segs=8, r2=None)
    col("Pole", x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0, 12.0)
    cyl("Steel", (x, y, 12.05), 0.12, 0.1, segs=8)
    box("Concrete", x - 1.2, x + 1.2, y - 1.2, y + 1.2, Z_ASPH, Z_WALK + 0.15)
    # flag waving in +x
    bm = K.bm("Flag")
    uv = bm.loops.layers.uv.active
    cols, W, H = 8, 2.6, 1.6
    for face in (0, 1):
        for i in range(cols):
            u0, u1 = i / cols, (i + 1) / cols
            xa, xb = x + 0.08 + u0 * W, x + 0.08 + u1 * W
            ya, yb = y + 0.18 * math.sin(u0 * 5) * u0, y + 0.18 * math.sin(u1 * 5) * u1
            q = [(xa, ya, 10.2), (xb, yb, 10.2 - 0.05 * u1), (xb, yb, 10.2 + H - 0.05 * u1), (xa, ya, 10.2 + H)]
            uvs = [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
            if face:
                q, uvs = q[::-1], uvs[::-1]
            f = bm.faces.new([bm.verts.new(tuple(m(v) for v in p)) for p in q])
            for l, t in zip(f.loops, uvs):
                l[uv].uv = t


PINE_N = [0]


def pine(x, y, h, rng_):
    """Realistic conifer: tapering trunk + 6-8 drooping, ragged needle tiers (both faces)."""
    PINE_N[0] += 1
    leaf = ("Leaf", "LeafB", "LeafC", "LeafD", "LeafE", "LeafF")[PINE_N[0] % 6]
    cyl("Trunk", (x, y, h * 0.32), 0.09 * h / 4 + 0.12, h * 0.64, segs=7, r2=0.06, mat="Bark")
    tr = 0.09 * h / 4 + 0.08
    col("Trunk", x - tr, x + tr, y - tr, y + tr, 0, h * 0.5)
    tiers = rng_.randint(9, 12)
    bm = K.bm(leaf, "Needles")
    base_r = h * rng_.uniform(0.19, 0.24)
    for t in range(tiers):
        f = t / tiers
        zc = h * (0.22 + 0.74 * f)
        r = base_r * (1 - f * 0.85) * rng_.uniform(0.92, 1.08) + 0.25
        tall = h * 0.16 * (1 - f * 0.4)
        apex = bm.verts.new((m(x), m(y), m(zc + tall)))
        n = 13
        ring = []
        for k in range(n * 2):
            a = k / (n * 2) * math.tau + rng_.uniform(-0.08, 0.08) + t
            rr2 = r * (1.0 if k % 2 == 0 else 0.72) * rng_.uniform(0.88, 1.1)
            droop = -0.25 * r if k % 2 == 0 else -0.05 * r
            ring.append(bm.verts.new((m(x + math.cos(a) * rr2), m(y + math.sin(a) * rr2), m(zc + droop))))
        inner = bm.verts.new((m(x), m(y), m(zc + 0.08 * tall)))
        for k in range(n * 2):
            a_, b_ = ring[k], ring[(k + 1) % (n * 2)]
            bm.faces.new([apex, a_, b_])
            bm.faces.new([inner, b_, a_])


def street_furniture():
    for x, y, rz in ((-ROAD_HW - 1.2, -46, 0), (ROAD_HW + 1.2, -40, math.pi), (-ROAD_HW - 1.2, -34, 0), (8, -30, math.pi / 2),
                     (30, -27, math.pi / 2), (48, -10, math.pi), (48, 12, math.pi), (10, 22, -math.pi / 2), (-18, 22, -math.pi / 2),
                     (-40, 6, math.pi / 2), (30, 46, -math.pi / 2), (-10, 46, -math.pi / 2)):
        street_lamp(x, y, rz)
    flagpole(-4, -6)


def parking():
    # bays in front of barracks 101 / 102 (west side of them, along x = 10)
    for y0 in (-22, -2):
        for k in range(5):
            y = y0 + k * 2.7
            box("PaintWhite", 4.0, 9.5, y - 0.06, y + 0.06, Z_ASPH, Z_PAINT)
    for x0 in (-16, 18):
        for k in range(10):
            x = x0 + k * 2.7
            box("PaintWhite", x - 0.06, x + 0.06, 18.5, 24.0, Z_ASPH, Z_PAINT)


# ---------------------------------------------------------------- build
gate()
tower(40, -36)
building(26, -16, 24, 11, "Plate101")
building(26, 4, 24, 11, "Plate102")
building(-4, 33, 24, 11, "Plate103", front=-1)
building(28, 33, 24, 11, "Plate104", front=-1)
building(-4, 8, 18, 11, "PlateHQ", front=-1, stairs=False)
training_yard(-57, -24, -46, -10)
motor_pool(-54, -26, 30, 44)
for x, y in ((FX0 + 3, FY0 + 3), (FX1 - 3, FY0 + 3), (FX0 + 3, FY1 - 3), (FX1 - 3, FY1 - 3)):
    watchtower(x, y)
street_furniture()
parking()
# grass verge kerbs along the core asphalt edge facing the gate road
for y in (-32,):
    box("ConcreteDark", -20, -ROAD_HW, y - 0.15, y + 0.15, Z_ASPH - 0.05, Z_WALK)
    box("ConcreteDark", ROAD_HW, 52, y - 0.15, y + 0.15, Z_ASPH - 0.05, Z_WALK)

# pines: a dense belt outside the fence (sides + back), a few clumps inside on the grass
PINES = []
for _ in range(900):
    x, y = rng.uniform(GX0 + 2, GX1 - 2), rng.uniform(GY0 + 2, GY1 - 2)
    outside = not (FX0 - 3 < x < FX1 + 3 and FY0 - 3 < y < FY1 + 3)
    corridor = abs(x) < ROAD_HW + 4 and y < FY0 + 2
    front_clear = y < FY0 - 3 and abs(x) < GATE_HW + 12
    if not outside or corridor or front_clear:
        continue
    if any((x - a) ** 2 + (y - b) ** 2 < 4.2 ** 2 for a, b, _ in PINES):
        continue
    PINES.append((x, y, rng.uniform(11, 17)))
for x, y in ((-15, -44), (-18, -39), (-16, -34), (48, -16), (56, 2), (56, 20), (-40, -4), (-48, 0), (14, -44), (24, -44)):
    PINES.append((x, y, rng.uniform(9, 13)))
for x, y, h in PINES:
    pine(x, y, h, rng)
print("pines", len(PINES))

K.finish(keep_normals=("Leaf", "LeafB", "LeafC", "LeafD", "LeafE", "LeafF", "ChainLink", "RazorWire", "CamoNet", "Flag", "ShedRoof", "TowerGlassA"), face=A["face"])
meta = K.export()


def roblox_box(c):
    """Blender metres (unturned) -> Roblox studs offset from the model origin, for the --face turn."""
    name, x0, x1, y0, y1, z0, z1 = c
    turn = {"N": 0, "S": math.pi, "E": -math.pi / 2, "W": math.pi / 2}[A["face"]]
    cs, sn = round(math.cos(turn)), round(math.sin(turn))
    xs, ys = [], []
    for x, y in ((x0, y0), (x1, y1)):
        tx, ty = x * cs - y * sn, x * sn + y * cs
        xs.append(-tx * M)          # Blender (x, y, z) -> Roblox (-x, z, y)
        ys.append(ty * M)
    return {"name": name, "pos": [round((xs[0] + xs[1]) / 2, 3), round((z0 + z1) / 2 * M, 3), round((ys[0] + ys[1]) / 2, 3)],
            "size": [round(abs(xs[1] - xs[0]), 3), round((z1 - z0) * M, 3), round(abs(ys[1] - ys[0]), 3)]}


meta["colliders"] = [roblox_box(c) for c in COLS]
json.dump(meta, open(os.path.join(A["out"], "meta.json"), "w"), indent=1)
print("colliders", len(COLS))

# ---------------------------------------------------------------- renders
if A["render"]:
    K.render_setup(A["samples"], A["res"], ground=6000)
    turn = {"N": 0, "S": math.pi, "E": -math.pi / 2, "W": math.pi / 2}[A["face"]]
    def T(p):
        c, s = math.cos(turn), math.sin(turn)
        return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])
    K.shot("gate", T((m(26), m(-92), m(26))), T((m(0), m(-44), m(4))), lens=32)
    K.shot("overview", T((m(-110), m(-120), m(95))), T((m(0), m(0), m(0))), lens=28)
    K.shot("barracks", T((m(2), m(-30), m(7))), T((m(26), m(-8), m(4))), lens=26)
    K.shot("tower", T((m(10), m(-62), m(10))), T((m(40), m(-36), m(18))), lens=28)
    K.shot("yard", T((m(-20), m(-56), m(14))), T((m(-40), m(-28), m(0))), lens=26)
