"""Ironwood Arms: a walk-in gun shop with an indoor range (original design in the style of a GTA
gun store; thread "Build GTA-style gun shop", 2026-11-07).

  python3 tools/gunshop_textures.py
  blender --background --python build_gunshop.py -- OUT_DIR [--no-render] [--samples N] [--res F]

Lot 28 x 26 m, front = -Y (street), origin = ground centre, studs (1 m = M = 3.6 studs).
  Front     stucco shop with a dark plinth, IRONWOOD ARMS sign on the parapet, blade sign, barred
            display windows with posters, glass door (Swing1, Client/CityDoors), canopy, cameras,
            parking stalls, bollards.
  Store     glass display counter across the room (pistols on felt, price cards), POS, clerk
            spot behind it; slatwall of rifles, shotguns and SMGs behind the counter; tall glass
            rifle cabinets on the left wall; ammo shelving + armor display on the right wall;
            centre glass case; posters, CCTV, drop ceiling with light panels.
  Range     steel door (Swing2) + viewing window in the partition; 5 lanes with booths, shelves,
            lane numbers, target carriers on ceiling rails, overhead baffles, sloped backstop.

Marker parts Spot* (tiny, invisible in game) tell Server/GunShop where things are:
  SpotBuy    where the customer stands at the till (the buy prompt)
  SpotClerk  where the clerk stands, facing the customer
  SpotCam    shop camera while the buy menu is open, looking at SpotCamLook
Deco* parts (guns, linings, small dressing) never collide. Guns are original low-poly models;
the rack carbines reuse our own CarbineRifle mesh (decimated, flat colours).
"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy, bmesh  # noqa: E402
from kit import Kit, M, args  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\gunshop")
K = Kit("GunShop", A["out"], TEX)
rng = random.Random(21)

# ---------------------------------------------------------------- materials
for name, tile in (("ExtWall", 3.5), ("ExtBand", 2.0), ("InWall", 3.0), ("ShopFloor", 1.2), ("RangeFloor", 3.0),
                   ("Asphalt", 6.0), ("Walk", 3.0), ("WoodTop", 1.5), ("Ceiling", 1.2), ("Pegboard", 1.2),
                   ("Slatwall", 1.2), ("Acoustic", 1.2), ("Backstop", 2.0), ("GunMetal", 1.0), ("Polymer", 1.0),
                   ("Tan", 1.0), ("Steel", 1.0), ("CaseMetal", 1.0), ("Shutter", 1.0), ("Stock", 0.8), ("Cardboard", 1.0)):
    K.mat(name, sheet=name, tile=(tile * M, tile * M))
K.mat("Block", sheet="Block", tile=(1.6 * M, 0.8 * M))
for name in ("ShopSign", "BladeSign", "Target", "AmmoWall", "CaseFelt", "LaneNumbers", "RangeSign", "RulesBoard",
             "Swing1Sign", "Register", "Cctv", "PosterSafety", "PosterStock", "PosterArmor", "PosterRange"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (
        ("Glass", (0.42, 0.52, 0.55), 0.08, 0.3, 0), ("Frame", (0.62, 0.63, 0.64), 0.35, 0.8, 0), ("Dark", (0.05, 0.05, 0.055), 0.5, 0.2, 0),
        ("Light", (1.0, 0.96, 0.88), 0.5, 0, 4.0), ("NeonRed", (1.0, 0.15, 0.12), 0.5, 0, 6.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
        ("Paint", (0.92, 0.92, 0.88), 0.7, 0, 0), ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Rubber", (0.08, 0.08, 0.085), 0.9, 0, 0),
        ("Red", (0.62, 0.07, 0.06), 0.5, 0.1, 0), ("Olive", (0.24, 0.26, 0.18), 0.85, 0, 0), ("Skin", (0.55, 0.52, 0.48), 0.6, 0, 0),
        ("AcBody", (0.78, 0.77, 0.73), 0.6, 0.2, 0), ("Spot", (1.0, 0.0, 1.0), 0.5, 0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats()
_g = K.mats["Glass"]["mat"]                 # see-through in the renders (in game: ClearGlass*, CityBuildings)
_g.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.16
_g.surface_render_method = 'DITHERED'


# ---------------------------------------------------------------- helpers (metres in, studs out)
def _m(part, mat):
    if mat or part in K.mats:
        return mat
    if part.startswith(("Light", "ShopLamp")):
        return "Light"
    raise KeyError(f"part {part} needs mat=")


def b(part, x0, x1, y0, y1, z0, z1, mat=None):
    mat = _m(part, mat)
    K.boxr(part, x0 * M, x1 * M, y0 * M, y1 * M, z0 * M, z1 * M, mat=mat)


def c(part, x, y, z, r, d, segs=12, axis='Z', mat=None, r2=None):
    mat = _m(part, mat)
    K.cyl(part, (x * M, y * M, z * M), r * M, d * M, segs=segs, axis=axis, mat=mat, r2=None if r2 is None else r2 * M)


def ca(part, a, bb, r, segs=8, mat=None):
    K.cyl_along(part, tuple(v * M for v in a), tuple(v * M for v in bb), r * M, segs=segs, mat=mat)


def fy(part, x, y, z0, w, h, facing=-1, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), mat=None):
    K.face_y(part, x * M, y * M, z0 * M, w * M, h * M, facing=facing, uvs=uvs, mat=mat)


def fx(part, x, y, z0, w, h, facing=1, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), mat=None):
    K.face_x(part, x * M, y * M, z0 * M, w * M, h * M, facing=facing, uvs=uvs, mat=mat)


def split(a0, a1, z0, z1, holes):
    """Rectangle a0..a1 x z0..z1 minus rectangular holes (ha0, ha1, hz0, hz1) -> pieces."""
    cuts = sorted({a0, a1, *[h[0] for h in holes], *[h[1] for h in holes]})
    out = []
    for p, q in zip(cuts, cuts[1:]):
        hs = sorted((h for h in holes if h[0] <= p and h[1] >= q), key=lambda h: h[2])
        z = z0
        for h in hs:
            if h[2] > z:
                out.append((p, q, z, h[2]))
            z = max(z, h[3])
        if z < z1:
            out.append((p, q, z, z1))
    return out


def spot(name, x, y, z):
    b(name, x - 0.02, x + 0.02, y - 0.02, y + 0.02, z - 0.02, z + 0.02, mat="Spot")


# ---------------------------------------------------------------- guns (local frame: muzzle +X, top +Z, side faces +-Y)
GS = 1.4          # guns a little larger than life so they read in game


def gbox(part, R, o, cx, cy, cz, sx, sy, sz, mat=None, ry=0.0):
    bm = K.bm(part, mat)
    r = bmesh.ops.create_cube(bm, size=1.0)
    loc = Matrix.Translation(Vector((cx, cy, cz)) * GS * M) @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Diagonal((sx * GS * M, sy * GS * M, sz * GS * M, 1))
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(o) * M) @ R @ loc, verts=r["verts"])


def gcyl(part, R, o, cx, cy, cz, r, length, mat=None, segs=8):
    """Cylinder along the gun's X axis."""
    bm = K.bm(part, mat)
    mx = Matrix.Translation(Vector(o) * M) @ R @ Matrix.Translation(Vector((cx, cy, cz)) * GS * M) @ Matrix.Rotation(math.pi / 2, 4, 'Y')
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r * GS * M, radius2=r * GS * M, depth=length * GS * M, matrix=mx)


def pistol(R, o, metal="DecoGunMetal", frame="DecoPolymer"):
    gbox(metal, R, o, 0.0, 0, 0.030, 0.19, 0.028, 0.034, mat="GunMetal")                 # slide
    gbox(metal, R, o, 0.096, 0, 0.034, 0.012, 0.012, 0.012, mat="GunMetal")              # muzzle
    gbox(metal, R, o, 0.08, 0, 0.050, 0.006, 0.006, 0.008, mat="GunMetal")               # front sight
    gbox(metal, R, o, -0.085, 0, 0.050, 0.008, 0.02, 0.008, mat="GunMetal")              # rear sight
    gbox(frame, R, o, 0.008, 0, 0.004, 0.17, 0.024, 0.02, mat="Polymer")                 # frame / dust cover
    gbox(frame, R, o, -0.062, 0, -0.045, 0.036, 0.026, 0.11, mat="Polymer", ry=-0.28)    # grip
    gbox(frame, R, o, -0.012, 0, -0.026, 0.05, 0.016, 0.006, mat="Polymer")              # trigger guard bottom
    gbox(frame, R, o, 0.012, 0, -0.016, 0.006, 0.016, 0.022, mat="Polymer")              # guard front
    gbox(metal, R, o, -0.02, 0, -0.012, 0.006, 0.006, 0.016, mat="GunMetal")             # trigger


def shotgun(R, o, wood="DecoGunWood", metal="DecoGunMetal"):
    gcyl(metal, R, o, 0.32, 0, 0.03, 0.011, 0.52, mat="GunMetal")                        # barrel
    gcyl(metal, R, o, 0.24, 0, 0.005, 0.010, 0.36, mat="GunMetal")                       # magazine tube
    gbox(wood, R, o, 0.20, 0, 0.012, 0.16, 0.034, 0.032, mat="Stock")                    # pump
    gbox(metal, R, o, -0.02, 0, 0.02, 0.2, 0.034, 0.058, mat="GunMetal")                 # receiver
    gbox(metal, R, o, -0.02, 0, -0.02, 0.05, 0.012, 0.024, mat="GunMetal")               # guard
    gbox(wood, R, o, -0.19, 0, -0.005, 0.16, 0.034, 0.05, mat="Stock", ry=0.18)          # wrist
    gbox(wood, R, o, -0.33, 0, -0.03, 0.17, 0.038, 0.11, mat="Stock", ry=0.10)           # butt
    gbox("DecoRubber", R, o, -0.42, 0, -0.035, 0.02, 0.04, 0.115, mat="Rubber", ry=0.10)


def smg(R, o, metal="DecoGunMetal", frame="DecoPolymer"):
    gbox(metal, R, o, 0.02, 0, 0.03, 0.26, 0.036, 0.05, mat="GunMetal")                  # receiver
    gcyl(metal, R, o, 0.19, 0, 0.034, 0.016, 0.1, mat="GunMetal")                        # shroud
    gcyl(metal, R, o, 0.25, 0, 0.034, 0.008, 0.05, mat="GunMetal")                       # muzzle
    gbox(frame, R, o, 0.02, 0, -0.06, 0.03, 0.022, 0.13, mat="Polymer", ry=0.12)         # magazine
    gbox(frame, R, o, -0.07, 0, -0.03, 0.035, 0.03, 0.08, mat="Polymer", ry=-0.25)       # grip
    gbox(frame, R, o, 0.11, 0, -0.01, 0.06, 0.03, 0.03, mat="Polymer")                   # handguard
    gbox(metal, R, o, 0.0, 0, 0.064, 0.18, 0.012, 0.014, mat="GunMetal")                 # top rail
    for z in (0.045, 0.0):                                                               # folding wire stock
        gbox(metal, R, o, -0.2, 0, z, 0.2, 0.008, 0.008, mat="GunMetal")
    gbox(metal, R, o, -0.3, 0, 0.02, 0.012, 0.03, 0.08, mat="GunMetal")


def hunting(R, o, wood="DecoGunWood", metal="DecoGunMetal"):
    gcyl(metal, R, o, 0.33, 0, 0.035, 0.010, 0.56, mat="GunMetal")                       # barrel
    gbox(wood, R, o, 0.12, 0, 0.012, 0.32, 0.034, 0.04, mat="Stock")                     # forend
    gbox(metal, R, o, -0.05, 0, 0.035, 0.16, 0.03, 0.04, mat="GunMetal")                 # action
    gcyl(metal, R, o, -0.04, 0, 0.1, 0.016, 0.3, mat="GunMetal")                         # scope tube
    gcyl(metal, R, o, 0.12, 0, 0.1, 0.024, 0.07, mat="GunMetal")                         # objective bell
    gcyl(metal, R, o, -0.19, 0, 0.1, 0.02, 0.05, mat="GunMetal")                         # eyepiece
    for x in (0.03, -0.1):
        gbox(metal, R, o, x, 0, 0.068, 0.02, 0.02, 0.03, mat="GunMetal")                 # rings
    gbox(metal, R, o, -0.1, 0.03, 0.03, 0.012, 0.04, 0.012, mat="GunMetal")              # bolt handle
    gbox(wood, R, o, -0.2, 0, -0.005, 0.16, 0.034, 0.055, mat="Stock", ry=0.22)          # wrist
    gbox(wood, R, o, -0.35, 0, -0.03, 0.18, 0.038, 0.12, mat="Stock", ry=0.08)           # butt
    gbox(metal, R, o, -0.06, 0, -0.022, 0.05, 0.01, 0.022, mat="GunMetal")               # guard


# our own CarbineRifle mesh, decimated, for the rack carbines (flat colours, no textures)
_carbine = None


def carbine_mesh():
    global _carbine
    if _carbine is None:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "art", "models", "CarbineRifle", "CarbineRifle.glb"))
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == 'MESH']
        bm = bmesh.new()
        for o in meshes:
            me = o.data.copy()
            me.transform(o.matrix_world)
            dec = bpy.data.objects.new("tmp", me)
            bpy.context.scene.collection.objects.link(dec)
            mod = dec.modifiers.new("d", 'DECIMATE')
            mod.ratio = 850 / max(1, len(me.polygons)) if o.name.startswith("Body") else 0.25
            dg = bpy.context.evaluated_depsgraph_get()
            ev = dec.evaluated_get(dg)
            tmp = bmesh.new()
            tmp.from_mesh(ev.to_mesh())
            ev.to_mesh_clear()
            copy_bm(tmp, bm, Matrix.Identity(4))
            tmp.free()
            bpy.data.objects.remove(dec)
        for o in new:
            bpy.data.objects.remove(o)
        lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
        hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
        length = hi.y - lo.y
        # muzzle -Y -> +X, centred, scaled to 0.86 m (times GS)
        mx = Matrix.Rotation(math.pi / 2, 4, 'Z') @ Matrix.Scale(0.86 / length, 4) @ Matrix.Translation(-(lo + hi) / 2)
        bmesh.ops.transform(bm, matrix=mx, verts=bm.verts)
        _carbine = bm
    return _carbine


def copy_bm(src, dst, mx):
    vm = {}
    for v in src.verts:
        vm[v] = dst.verts.new(mx @ v.co)
    for f in src.faces:
        try:
            dst.faces.new([vm[v] for v in f.verts])
        except ValueError:
            pass


def carbine(R, o, part="DecoRifle", mat="Polymer"):
    src = carbine_mesh()
    copy_bm(src, K.bm(part, mat), Matrix.Translation(Vector(o) * M) @ R @ Matrix.Scale(GS * M, 4))


ROT_FLAT = Matrix.Identity(4)                                                  # lying in the x-z plane, side to -Y
ROT_UP = Matrix.Rotation(math.pi / 2, 4, 'X') @ Matrix.Rotation(math.pi / 2, 4, 'Z')   # muzzle up, side to +X
ROT_DOWN = Matrix.Rotation(math.pi / 2, 4, 'X')                                # lying on its side (side up), muzzle +X


def ry_(a):
    return Matrix.Rotation(a, 4, 'Z')


# ================================================================ layout (metres)
LW, LD = 28.0, 26.0
X0, X1, Y0, Y1 = -12.0, 12.0, -6.0, 12.0          # building outer faces
H, T, F = 5.0, 0.3, 0.15                          # roof height, wall thickness, floor top
YI = Y0 + T                                        # front wall inside face
YP = 3.0                                           # partition (store | range), store side face
TP = 0.25
CZ = 4.3                                           # drop ceiling
DOOR = (-0.8, 0.8, F + 2.55)
WL, WR = (-10.2, -2.6, F + 0.9, F + 3.0), (2.6, 10.2, F + 0.9, F + 3.0)
RDOOR = (-11.0, -9.6, F + 2.3)                     # range door in the partition
RWIN = (-8.6, -5.6, F + 1.0, F + 2.3)              # range viewing window

# ---------------------------------------------------------------- ground
b("Asphalt", -LW / 2, LW / 2, -LD / 2, LD / 2, -0.08, 0.0)
b("Walk", X0 - 0.6, X1 + 0.6, Y0 - 3.0, Y0, 0.0, F)                               # shop front walk
b("Walk", -1.4, 1.4, -LD / 2, Y0 - 3.0, 0.0, F)                                   # path to the sidewalk
b("Paint", X0 - 0.6, X1 + 0.6, Y0 - 3.04, Y0 - 2.96, F, F + 0.004)
for i in range(4):                                                                # 4 stalls each side of the path
    for s_ in (-1, 1):
        x = s_ * (2.4 + i * 2.7)
        b("Paint", x - 0.05, x + 0.05, -LD / 2 + 0.6, Y0 - 3.3, 0.0, 0.004)
        if i < 3:
            xc = s_ * (2.4 + (i + 0.5) * 2.7)
            b("WheelStop", xc - 0.9, xc + 0.9, Y0 - 3.75, Y0 - 3.5, 0.0, 0.14, mat="Walk")
for bx in (-1.9, 1.9):                                                            # steel bollards by the path
    for by in (-9.4, -7.6):
        c("Bollard", bx, by, F + 0.5, 0.12, 1.0, segs=14, mat="Yellow")
        c("Bollard", bx, by, F + 1.02, 0.1, 0.05, segs=14, mat="Yellow")
for k in range(9):                                                                # bollards along the shop front walk
    bx = -11 + k * 2.75
    if abs(bx) < 2.2:
        continue
    c("Bollard", bx, Y0 - 2.6, F + 0.45, 0.11, 0.9, segs=12, mat="Steel")

# ---------------------------------------------------------------- shell
WALLS = []


def wall(name, x0, x1, y0, y1, z0, z1, mat="ExtWall"):
    b(name, x0, x1, y0, y1, z0, z1, mat=mat)
    WALLS.append(name)


front = split(X0, X1, 0.0, H, [(WL[0], WL[1], WL[2], WL[3]), (DOOR[0], DOOR[1], 0.0, DOOR[2]), (WR[0], WR[1], WR[2], WR[3])])
for i, (a0, a1, z0, z1) in enumerate(front):
    wall(f"WallF{i + 1}", a0, a1, Y0, YI, z0, z1)
wall("WallL", X0, X0 + T, YI, Y1, 0.0, H)
wall("WallR", X1 - T, X1, YI, Y1, 0.0, H)
back = split(X0 + T, X1 - T, 0.0, H, [(8.5, 9.6, 0.0, F + 2.2)])                    # back fire door opening
for i, (a0, a1, z0, z1) in enumerate(back):
    wall(f"WallB{i + 1}", a0, a1, Y1 - T, Y1, z0, z1)
part_ = split(X0 + T, X1 - T, 0.0, H, [(RDOOR[0], RDOOR[1], 0.0, RDOOR[2]), (RWIN[0], RWIN[1], RWIN[2], RWIN[3])])
for i, (a0, a1, z0, z1) in enumerate(part_):
    wall(f"WallP{i + 1}", a0, a1, YP, YP + TP, z0, z1, mat="InWall")
# parapets + roof
wall("ParapetF", X0, X1, Y0, Y0 + 0.4, H, 6.7)
wall("ParapetL", X0, X0 + T, Y0 + 0.4, Y1, H, H + 0.7)
wall("ParapetR", X1 - T, X1, Y0 + 0.4, Y1, H, H + 0.7)
wall("ParapetB", X0 + T, X1 - T, Y1 - T, Y1, H, H + 0.7)
b("Coping", X0 - 0.06, X1 + 0.06, Y0 - 0.06, Y0 + 0.46, 6.7, 6.8, mat="ExtBand")
for (x0, x1, y0, y1) in ((X0 - 0.04, X0 + T + 0.04, Y0 + 0.46, Y1 + 0.04), (X1 - T - 0.04, X1 + 0.04, Y0 + 0.46, Y1 + 0.04),
                         (X0 + T + 0.04, X1 - T - 0.04, Y1 - T - 0.04, Y1 + 0.04)):
    b("Coping", x0, x1, y0, y1, H + 0.7, H + 0.78, mat="ExtBand")
b("Roof", X0 + T, X1 - T, YI, Y1 - T, H - 0.12, H - 0.02, mat="ExtBand")
# dark plinth band round the outside (stands 0.04 m proud of the stucco)
for (x0, x1, y0, y1) in ((X0 - 0.04, X1 + 0.04, Y0 - 0.04, Y0), (X0 - 0.04, X1 + 0.04, Y1, Y1 + 0.04),
                         (X0 - 0.04, X0, Y0, Y1), (X1, X1 + 0.04, Y0, Y1)):
    for (a0, a1, z0, z1) in split(x0 if y1 - y0 < 0.1 else y0, x1 if y1 - y0 < 0.1 else y1, 0.0, F + 0.75,
                                  [(DOOR[0], DOOR[1], 0.0, DOOR[2])] if y1 == Y0 else
                                  ([(8.5, 9.6, 0.0, F + 2.2)] if y0 == Y1 else [])):
        if y1 - y0 < 0.1:
            b("Plinth", a0, a1, y0, y1, z0, z1, mat="ExtBand")
        else:
            b("Plinth", x0, x1, a0, a1, z0, z1, mat="ExtBand")
# dark fascia band at the top of the shop front, under the sign
b("Fascia", X0 - 0.05, X1 + 0.05, Y0 - 0.05, Y0, F + 3.55, F + 4.1, mat="ExtBand")
# floors + ceilings
b("ShopFloor", X0 + T, X1 - T, YI, YP, 0.0, F)
b("RangeFloor", X0 + T, X1 - T, YP, Y1 - T, 0.0, F)
b("Ceiling", X0 + T, X1 - T, YI, YP, CZ, CZ + 0.06)
b("RangeCeiling", X0 + T, X1 - T, YP + TP, Y1 - T, CZ, CZ + 0.06, mat="Acoustic")

# ---------------------------------------------------------------- sign, canopy, lights (front)
fy("ShopSign", 0, Y0 - 0.06, 4.55, 15.2, 1.9)
b("SignBox", -7.75, 7.75, Y0 - 0.05, Y0 - 0.01, 4.47, 6.53, mat="Dark")          # sign tray (behind the printed face)
b("NeonRed", -7.5, 7.5, Y0 - 0.14, Y0 - 0.08, 4.36, 4.42)                         # red neon line under the sign
for nx in (-7.0, -2.4, 2.4, 7.0):
    b("Steel", nx - 0.02, nx + 0.02, Y0 - 0.14, Y0 - 0.06, 4.36, 4.47)
for lx in (-6, -2, 2, 6):                                                         # gooseneck sign lights
    ca("Steel", (lx, Y0 - 0.02, 6.75), (lx, Y0 - 0.7, 7.0), 0.025)
    b("Sconce", lx - 0.22, lx + 0.22, Y0 - 0.86, Y0 - 0.6, 6.9, 7.0)
# canopy over the door
b("Canopy", -2.1, 2.1, Y0 - 1.3, Y0 - 0.02, F + 2.95, F + 3.1, mat="CaseMetal")
for sx in (-1.95, 1.95):
    ca("Steel", (sx, Y0 - 1.25, F + 3.08), (sx, Y0 - 0.03, F + 3.7), 0.02)
b("ShopLamp", -1.6, 1.6, Y0 - 1.0, Y0 - 0.6, F + 2.93, F + 2.95)
# blade sign at the right corner
bx_ = X1 - 1.0
b("BladeBox", bx_ - 0.06, bx_ + 0.06, Y0 - 1.3, Y0 - 0.25, F + 3.0, F + 6.1, mat="Dark")
fx("BladeSign", bx_ + 0.065, Y0 - 0.775, F + 3.05, 1.0, 3.0, facing=1)
fx("BladeSign", bx_ - 0.065, Y0 - 0.775, F + 3.05, 1.0, 3.0, facing=-1)
for z in (F + 3.4, F + 5.7):
    b("Steel", bx_ - 0.03, bx_ + 0.03, Y0 - 0.25, Y0 - 0.01, z - 0.04, z + 0.04)
# security cameras + wall lights
for cx in (X0 + 0.5, X1 - 0.5):
    b("Cam", cx - 0.1, cx + 0.1, Y0 - 0.45, Y0 - 0.05, F + 3.3, F + 3.48, mat="Paint")
    b("Dark", cx - 0.06, cx + 0.06, Y0 - 0.47, Y0 - 0.45, F + 3.34, F + 3.44)
for sy in (-2.0, 4.0, 10.0):
    for (sx, s) in ((X0 - 0.12, 1), (X1 + 0.12, -1)):
        b("Sconce", sx - 0.08, sx + 0.08, sy - 0.15, sy + 0.15, F + 3.0, F + 3.2)

# ---------------------------------------------------------------- display windows: glass, frames, bars, shutter boxes, posters
for gi, (x0, x1, z0, z1) in enumerate((WL, WR)):
    b(f"ClearGlass{gi + 1}", x0, x1, Y0 + 0.14, Y0 + 0.16, z0, z1, mat="Glass")
    n = 3
    for k in range(n + 1):
        x = x0 + k * (x1 - x0) / n
        b("Frame", x - 0.05, x + 0.05, Y0 + 0.08, Y0 + 0.22, z0, z1)
    for z in (z0, z1):
        b("Frame", x0, x1, Y0 + 0.08, Y0 + 0.22, z - 0.05, z + 0.05)
    b("Sill", x0 - 0.08, x1 + 0.08, Y0 - 0.12, Y0 + 0.05, z0 - 0.08, z0, mat="ExtBand")
    nb = int((x1 - x0) / 0.15)
    for k in range(nb + 1):                                                       # security bars
        bx = x0 + 0.04 + k * (x1 - x0 - 0.08) / nb
        b("WinIron", bx - 0.012, bx + 0.012, Y0 - 0.09, Y0 - 0.066, z0, z1, mat="Dark")
    for z in (z0 + 0.25, (z0 + z1) / 2, z1 - 0.25):
        b("WinIron", x0, x1, Y0 - 0.1, Y0 - 0.06, z - 0.02, z + 0.02, mat="Dark")
    b("ShutterBox", x0 - 0.05, x1 + 0.05, Y0 - 0.32, Y0 - 0.01, z1 + 0.03, z1 + 0.33, mat="Shutter")
    for sx in (x0 - 0.03, x1 + 0.03):                                             # shutter guide rails
        b("Shutter", sx - 0.03, sx + 0.03, Y0 - 0.08, Y0 - 0.01, 0.0 + F, z1 + 0.03)
for (px, name) in ((-8.6, "PosterStock"), (-4.2, "PosterSafety"), (4.2, "PosterArmor"), (8.6, "PosterRange")):
    fy(name, px, Y0 + 0.17, F + 1.2, 1.1, 1.65)                                   # stuck inside the glass, facing out
    b("PosterBack", px - 0.55, px + 0.55, Y0 + 0.175, Y0 + 0.185, F + 1.2, F + 2.85, mat="Cardboard")

# ---------------------------------------------------------------- front door (Swing1, glass, push bars both sides)
DY = Y0 + T / 2
for x in (DOOR[0], DOOR[1]):
    b("Frame", x - 0.08, x + 0.08, Y0 - 0.01, YI + 0.01, 0.0 + F, DOOR[2])
b("Frame", DOOR[0] - 0.08, DOOR[1] + 0.08, Y0 - 0.01, YI + 0.01, DOOR[2], DOOR[2] + 0.15)
b("Threshold", DOOR[0], DOOR[1], Y0 - 0.02, YI + 0.02, F - 0.02, F + 0.01, mat="Steel")
hx = DOOR[1] - 0.15
lx0, lx1, lz0, lz1, t2 = DOOR[0] + 0.1, hx + 0.05, F + 0.02, DOOR[2] - 0.04, 0.025
for (a, bb) in ((lx0, lx0 + 0.1), (lx1 - 0.1, lx1)):
    b("Swing1Frame", a, bb, DY - t2, DY + t2, lz0, lz1, mat="Frame")
b("Swing1Frame", lx0 + 0.1, lx1 - 0.1, DY - t2, DY + t2, lz1 - 0.12, lz1, mat="Frame")
b("Swing1Frame", lx0 + 0.1, lx1 - 0.1, DY - t2, DY + t2, lz0, lz0 + 0.26, mat="Frame")
b("Swing1Glass", lx0 + 0.09, lx1 - 0.09, DY - 0.006, DY + 0.006, lz0 + 0.25, lz1 - 0.11, mat="Glass")
for sgn in (-1, 1):
    by = DY + sgn * (t2 + 0.07)
    ca("Swing1Bar", (lx0 + 0.18, by, F + 1.0), (lx1 - 0.18, by, F + 1.0), 0.02, mat="Steel")
    for bx in (lx0 + 0.25, lx1 - 0.25):
        b("Swing1Bar", bx - 0.02, bx + 0.02, min(by, DY + sgn * t2), max(by, DY + sgn * t2), F + 0.98, F + 1.02, mat="Steel")
fy("Swing1Sign", (lx0 + lx1) / 2, DY - t2 - 0.003, F + 1.4, 0.55, 0.34)
for z in (F, lz1 + 0.005):
    c("Swing1Pivot", hx, DY, z + 0.01, 0.03, 0.02, segs=8, mat="Steel")
b("Frame", DOOR[0], DOOR[1], YI + 0.02, YI + 0.1, DOOR[2] - 0.12, DOOR[2] - 0.02)     # closer
b("DecoMat", -0.75, 0.75, YI + 0.25, YI + 1.15, F, F + 0.012, mat="Rubber")
b("DecoMat", -0.75, 0.75, Y0 - 1.0, Y0 - 0.1, F, F + 0.012, mat="Rubber")

# ================================================================ store interior
IN = 0.02
for (x0, x1, y0, y1, holes) in (
        (X0 + T + IN, X0 + T + 2 * IN, YI, YP, []), (X1 - T - 2 * IN, X1 - T - IN, YI, YP, [])):
    b("DecoWall", x0, x1, y0, y1, F, CZ, mat="InWall")
for (a0, a1, z0, z1) in split(X0 + T, X1 - T, F, CZ, [(WL[0], WL[1], WL[2], WL[3]), (DOOR[0] - 0.1, DOOR[1] + 0.1, 0.0, DOOR[2] + 0.15), (WR[0], WR[1], WR[2], WR[3])]):
    b("DecoWall", a0, a1, YI + IN, YI + 2 * IN, z0, z1, mat="InWall")
# skirting
for (x0, x1, y0, y1) in ((X0 + T, X0 + T + 0.06, YI, YP), (X1 - T - 0.06, X1 - T, YI, YP)):
    b("DecoSkirt", x0, x1, y0, y1, F, F + 0.12, mat="Dark")

# ---- glass display counter across the room (customer side y < -0.45)
CX0, CX1, CY0, CY1 = -5.0, X1 - T, -0.45, 0.45
RET = (-5.0, -4.1)                                                               # return to the partition (closes the clerk side)


def glass_case(name, x0, x1, y0, y1, z_top=1.0, felt=True, front_glass=True):
    """Counter case: dark metal base, felt floor with guns, glass front + top, metal frame."""
    zb = F + 0.35
    zt = F + z_top
    b(name, x0, x1, y0, y1, F, zb, mat="CaseMetal")
    b("DecoKick", x0 + 0.03, x1 - 0.03, y0 - 0.02, y0, F, F + 0.1, mat="Dark")
    if felt:
        fy_ = (y0 + y1) / 2
        K.quad("CaseFelt", [(x0 * M, y0 * M, (zb + 0.004) * M), (x1 * M, y0 * M, (zb + 0.004) * M),
                            (x1 * M, y1 * M, (zb + 0.004) * M), (x0 * M, y1 * M, (zb + 0.004) * M)],
               uvs=((0, 0), ((x1 - x0) / 7.5, 0), ((x1 - x0) / 7.5, 1), (0, 1)))
    b(f"ClearGlass{name}", x0 + 0.03, x1 - 0.03, y0, y0 + 0.012, zb, zt, mat="Glass")     # front glass
    b(f"ClearGlass{name}", x0, x1, y0, y1, zt, zt + 0.012, mat="Glass")                   # top glass
    b(f"{name}Back", x0 + 0.03, x1 - 0.03, y1 - 0.03, y1, zb, zt, mat="CaseMetal")      # staff side panel
    for x in (x0, x1):
        b(f"{name}End", x - 0.0 if x == x0 else x - 0.03, x + 0.03 if x == x0 else x, y0, y1, zb, zt, mat="CaseMetal")
    for (a0, a1) in ((y0 - 0.01, y0 + 0.02), (y1 - 0.02, y1 + 0.01)):
        b("CaseTrim", x0, x1, a0, a1, zt - 0.02, zt + 0.02, mat="Frame")
    b("CaseTrim", x0, x1, y0 - 0.01, y0 + 0.02, zb - 0.02, zb + 0.02, mat="Frame")
    b("LightCase", x0 + 0.1, x1 - 0.1, y1 - 0.1, y1 - 0.06, zt - 0.04, zt - 0.02)       # LED strip inside


# counter in three cases with seams so it reads as units
for (x0, x1) in ((CX0, -0.5), (-0.5, 4.0), (4.0, CX1)):
    glass_case("Counter", x0 + 0.01, x1 - 0.01, CY0, CY1)
glass_case("Counter", RET[0], RET[1], CY1 + 0.01, YP - 0.01, felt=False)
# pistols on the felt, angled like a real case
for i in range(15):
    x = CX0 + 0.5 + i * 0.95
    if x > CX1 - 0.4:
        break
    if 2.6 < x < 3.6:       # till area: no guns under the register
        continue
    R = ry_(rng.uniform(-0.25, 0.25) + 0.4) @ ROT_DOWN
    pistol(R, (x, rng.uniform(-0.15, 0.05), F + 0.39), metal="DecoGunMetal" if i % 3 else "DecoSteel")
# till: register, screen, card reader, receipt printer
b("Till", 2.65, 3.45, -0.05, 0.4, F + 1.012, F + 1.1, mat="Dark")
b("Till", 2.95, 3.15, 0.15, 0.25, F + 1.1, F + 1.35, mat="Dark")
K.box("Dark", (3.05 * M, 0.17 * M, (F + 1.5) * M), (0.55 * M, 0.04 * M, 0.38 * M), rz=0)
fy("Register", 3.05, 0.145, F + 1.32, 0.5, 0.36)
b("Till", 2.2, 2.45, -0.3, -0.1, F + 1.012, F + 1.06, mat="Dark")                # card reader
b("Paint", 2.24, 2.41, -0.28, -0.13, F + 1.06, F + 1.062)
b("Till", 3.6, 3.85, 0.0, 0.25, F + 1.012, F + 1.14, mat="Paint")                # receipt printer
# small sign on the counter: no loaded guns (bent card)
b("DecoCard", -3.0, -2.6, -0.1, -0.08, F + 1.012, F + 1.2, mat="Paint")

# ---- slatwall behind the counter with racks of guns
SW0, SW1 = -3.9, X1 - T - 0.1
b("Slatwall", SW0, SW1, YP - 0.04, YP - 0.005, F + 0.9, F + 3.9)
b("SlatTrim", SW0 - 0.04, SW1 + 0.04, YP - 0.06, YP - 0.005, F + 3.9, F + 3.98, mat="Frame")
b("SlatTrim", SW0 - 0.04, SW1 + 0.04, YP - 0.06, YP - 0.005, F + 0.85, F + 0.9, mat="Frame")
b("BackCounter", SW0, SW1, YP - 0.6, YP - 0.05, F, F + 0.85, mat="CaseMetal")    # low cabinet under the racks
b("BackCounterTop", SW0 - 0.02, SW1 + 0.02, YP - 0.62, YP - 0.04, F + 0.85, F + 0.89, mat="WoodTop")
cols = [SW0 + 0.8 + k * 1.35 for k in range(int((SW1 - SW0 - 1.2) / 1.35) + 1)]
for k, x in enumerate(cols):
    # top row: shotguns + hunting rifles, middle: carbines, bottom: SMGs
    (shotgun if k % 2 else hunting)(ROT_FLAT, (x + 0.05, YP - 0.1, F + 3.4))
    carbine(ROT_FLAT, (x, YP - 0.11, F + 2.55), part="DecoRifle" if k % 3 else "DecoRifleT", mat="Polymer" if k % 3 else "Tan")
    smg(ROT_FLAT, (x - 0.1, YP - 0.1, F + 1.55))
    for row_z, half in ((F + 3.4, 0.45), (F + 2.55, 0.38), (F + 1.55, 0.22)):     # rack hooks
        for hxx in (x - half, x + half):
            b("DecoHook", hxx - 0.015, hxx + 0.015, YP - 0.16, YP - 0.04, row_z - 0.09, row_z - 0.06, mat="Steel")
# CCTV monitor + clock behind the counter
b("Monitor", 10.4, 11.4, YP - 0.5, YP - 0.3, F + 0.89, F + 0.93, mat="Dark")
K.box("Dark", (10.9 * M, (YP - 0.35) * M, (F + 1.3) * M), (0.9 * M, 0.08 * M, 0.55 * M))
fy("Cctv", 10.9, YP - 0.395, F + 1.06, 0.82, 0.48)
c("DecoClock", 7.6, YP - 0.02, F + 4.05, 0.18, 0.04, segs=20, axis='Y', mat="Paint")
c("DecoClock", 7.6, YP - 0.035, F + 4.05, 0.2, 0.02, segs=20, axis='Y', mat="Dark")

# ---- tall glass rifle cabinets along the left wall
LX = X0 + T + 0.04
for k, (y0, y1) in enumerate(((-5.2, -2.9), (-2.7, -0.4), (-0.2, 2.1))):
    xF = LX + 0.6
    b(f"Cabinet{k + 1}", LX, xF, y0, y1, F, F + 0.4, mat="CaseMetal")                   # base drawer
    b(f"Cabinet{k + 1}", LX, xF, y0, y1, F + 2.6, F + 2.75, mat="CaseMetal")           # top
    b(f"Cabinet{k + 1}", LX, LX + 0.04, y0, y1, F + 0.4, F + 2.6, mat="Pegboard")      # back board
    for yy in (y0, y1 - 0.04):
        b(f"Cabinet{k + 1}", LX, xF, yy, yy + 0.04, F + 0.4, F + 2.6, mat="CaseMetal")
    b(f"ClearGlassCab{k + 1}", xF - 0.012, xF, y0 + 0.04, y1 - 0.04, F + 0.4, F + 2.6, mat="Glass")
    b("CaseTrim", xF - 0.02, xF + 0.01, y0, y1, F + 0.4, F + 0.43, mat="Frame")
    b("CaseTrim", xF - 0.02, xF + 0.01, (y0 + y1) / 2 - 0.015, (y0 + y1) / 2 + 0.015, F + 0.43, F + 2.6, mat="Frame")
    b("LightCab", LX + 0.1, xF - 0.1, y0 + 0.1, y1 - 0.1, F + 2.58, F + 2.6)
    b("DecoRest", LX + 0.05, xF - 0.08, y0 + 0.05, y1 - 0.05, F + 0.4, F + 0.48, mat="Rubber")      # butt rest
    b("DecoRest", LX + 0.04, LX + 0.18, y0 + 0.05, y1 - 0.05, F + 1.9, F + 1.95, mat="Rubber")      # barrel rest
    for j in range(5):
        yy = y0 + 0.28 + j * (y1 - y0 - 0.56) / 4
        kind = (k + j) % 3
        o = (LX + 0.28, yy, F + 1.0 + (0.05 if kind == 1 else 0.0))
        R = ROT_UP
        if kind == 0:
            hunting(R, o)
        elif kind == 1:
            shotgun(R, o)
        else:
            carbine(R, o, part="DecoRifleCT" if j % 2 else "DecoRifleC", mat="Tan" if j % 2 else "Polymer")
# wall posters above the cabinets
fx("PosterStock", LX + 0.02, -4.0, F + 2.95, 0.8, 1.2, facing=1)
fx("PosterRange", LX + 0.02, 0.9, F + 2.95, 0.8, 1.2, facing=1)

# ---- right wall: ammo shelving + armor display
RX = X1 - T - 0.04
for k, (y0, y1) in enumerate(((-5.4, -3.2), (-3.0, -0.8))):
    xF = RX - 0.5
    b(f"AmmoShelf{k + 1}", xF, RX, y0, y1, F, F + 0.25, mat="CaseMetal")
    b(f"AmmoShelf{k + 1}", RX - 0.04, RX, y0, y1, F, F + 2.4, mat="Pegboard")
    for yy in (y0, y1 - 0.04):
        b(f"AmmoShelf{k + 1}", xF, RX, yy, yy + 0.04, F, F + 2.4, mat="CaseMetal")
    for z in (F + 0.25, F + 0.78, F + 1.31, F + 1.84, F + 2.37):
        b(f"AmmoShelf{k + 1}", xF, RX - 0.04, y0 + 0.04, y1 - 0.04, z - 0.03, z, mat="Steel")
    fx("AmmoWall", RX - 0.3, (y0 + y1) / 2, F + 0.27, y1 - y0 - 0.1, 2.08, facing=-1,
       uvs=((0, 0), (1, 0), (1, 1), (0, 1)) if k == 0 else ((0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1)))
    # loose boxes on the shelves (real 3D, a few)
    for z in (F + 0.25, F + 1.31):
        for j in range(4):
            yy = y0 + 0.3 + j * 0.45
            b("DecoAmmoBox", RX - 0.48, RX - 0.32, yy - 0.08, yy + 0.08, z, z + 0.1, mat="Red" if j % 2 else "Olive")
    fx("PosterArmor", RX - 0.01, (y0 + y1) / 2, F + 2.7, 0.8, 1.2, facing=-1) if k == 1 else None
# armor display: torso form on a stand wearing a plate carrier
ax, ay = RX - 0.6, 1.0
c("Stand", ax, ay, F + 0.03, 0.3, 0.06, segs=16, mat="Steel")
c("Stand", ax, ay, F + 0.6, 0.025, 1.1, segs=8, mat="Steel")
b("DecoForm", ax - 0.16, ax + 0.16, ay - 0.24, ay + 0.24, F + 1.15, F + 1.75, mat="Skin")
c("DecoForm", ax, ay, F + 1.8, 0.07, 0.1, segs=10, mat="Skin")
for s_ in (-1, 1):                                                                    # front + back plates
    b("DecoVest", ax + s_ * 0.17, ax + s_ * 0.24, ay - 0.22, ay + 0.22, F + 1.2, F + 1.66, mat="Olive")
    for j in range(3):                                                                # mag pouches on the front
        if s_ < 0:
            yy = ay - 0.14 + j * 0.14
            b("DecoVest", ax - 0.31, ax - 0.24, yy - 0.06, yy + 0.06, F + 1.22, F + 1.4, mat="Olive")
b("DecoVest", ax - 0.2, ax + 0.2, ay - 0.27, ay - 0.22, F + 1.22, F + 1.45, mat="Olive")    # cummerbund
b("DecoVest", ax - 0.2, ax + 0.2, ay + 0.22, ay + 0.27, F + 1.22, F + 1.45, mat="Olive")
for s_ in (-1, 1):
    b("DecoVest", ax - 0.2, ax + 0.2, ay + s_ * 0.1 - 0.03, ay + s_ * 0.1 + 0.03, F + 1.66, F + 1.76, mat="Olive")  # straps
# centre glass case (optics, knives) on the shop floor
glass_case("Island", -10.2, -7.2, -3.6, -2.4, z_top=0.95)
for j in range(3):
    pistol(ry_(0.3 + j * 0.2) @ ROT_DOWN, (-9.6 + j * 1.0, -3.0, F + 0.39), metal="DecoSteel")
# freestanding round rifle rack in the middle of the shop floor + a stack of ammo cases
rx, ry = -5.4, -3.2
c("RackBase", rx, ry, F + 0.06, 0.55, 0.12, segs=20, mat="CaseMetal")
c("RackBase", rx, ry, F + 0.9, 0.06, 1.6, segs=10, mat="CaseMetal")
c("RackBase", rx, ry, F + 1.5, 0.45, 0.04, segs=20, mat="CaseMetal")
for j in range(6):
    a = j / 6 * math.tau
    o = (rx + math.cos(a) * 0.38, ry + math.sin(a) * 0.38, F + 0.62)
    R = ry_(a) @ Matrix.Rotation(math.pi / 2, 4, 'Y') @ Matrix.Rotation(math.pi, 4, 'Z')   # muzzle up, top facing out
    if j % 3 == 0:
        carbine(R, (o[0], o[1], o[2] + 0.1), part="DecoRifleC", mat="Polymer")
    elif j % 3 == 1:
        shotgun(R, o)
    else:
        hunting(R, o)
for j in range(3):
    for kk in range(2 - (j == 2)):
        bx0 = 7.0 + kk * 0.62
        b("AmmoCase", bx0, bx0 + 0.58, -4.6, -4.2, F + j * 0.3, F + j * 0.3 + 0.28, mat="Olive")
        b("DecoLatch", bx0 + 0.12, bx0 + 0.46, -4.62, -4.6, F + j * 0.3 + 0.17, F + j * 0.3 + 0.22, mat="Steel")
# bench + bin + plant by the window
b("Bench", 4.6, 7.0, YI + 0.3, YI + 0.75, F + 0.42, F + 0.47, mat="WoodTop")
for bx in (4.8, 6.8):
    b("Bench", bx - 0.04, bx + 0.04, YI + 0.35, YI + 0.7, F, F + 0.42, mat="Steel")
c("Bin", 7.6, YI + 0.45, F + 0.38, 0.22, 0.76, segs=14, mat="Dark")
# ceiling lights + dome cameras
for lx in (-9.5, -6.0, -2.5, 1.0, 4.5, 8.0, 10.6):
    for ly in (-4.4, -2.2, 0.0, 1.9):
        K.box("LightCeil", (lx * M, ly * M, (CZ - 0.015) * M), (1.1 * M, 0.5 * M, 0.03 * M), mat="Light")
for (dx, dy) in ((-8.0, -1.0), (6.0, -3.5), (1.0, 1.5)):
    c("Dome", dx, dy, CZ - 0.06, 0.12, 0.12, segs=12, mat="Dark")
# range sign + viewing window frame (store side)
fy("RangeSign", (RDOOR[0] + RWIN[1]) / 2, YP - 0.02, F + 2.7, 3.6, 0.68)
b(f"ClearGlassRange", RWIN[0], RWIN[1], YP + 0.11, YP + 0.14, RWIN[2], RWIN[3], mat="Glass")
for (a0, a1, z0, z1) in ((RWIN[0] - 0.06, RWIN[0], RWIN[2], RWIN[3]), (RWIN[1], RWIN[1] + 0.06, RWIN[2], RWIN[3]),
                         (RWIN[0] - 0.06, RWIN[1] + 0.06, RWIN[2] - 0.06, RWIN[2]), (RWIN[0] - 0.06, RWIN[1] + 0.06, RWIN[3], RWIN[3] + 0.06)):
    b("Frame", a0, a1, YP - 0.03, YP + TP + 0.03, z0, z1)
# ear protection rack by the range door
b("Rack", -9.4, -8.7, YP - 0.06, YP - 0.01, F + 1.2, F + 1.9, mat="Pegboard")
for j in range(2):
    for kk in range(2):
        mx_ = -9.25 + kk * 0.4
        mz = F + 1.75 - j * 0.35
        ca("DecoMuffs", (mx_ - 0.1, YP - 0.12, mz - 0.1), (mx_ + 0.1, YP - 0.12, mz - 0.1), 0.06, segs=8, mat="Red")
        ca("DecoMuffs", (mx_ - 0.1, YP - 0.12, mz - 0.1), (mx_ - 0.1, YP - 0.08, mz + 0.02), 0.012, segs=4, mat="Dark")

# ---- range door (Swing2): steel door with a small window, push plate, closer
RY = YP + TP / 2
for x in (RDOOR[0], RDOOR[1]):
    b("Frame", x - 0.06, x + 0.06, YP - 0.01, YP + TP + 0.01, F, RDOOR[2])
b("Frame", RDOOR[0] - 0.06, RDOOR[1] + 0.06, YP - 0.01, YP + TP + 0.01, RDOOR[2], RDOOR[2] + 0.1)
hx2 = RDOOR[0] + 0.12                                                             # hinge on the left jamb
l0, l1 = hx2 - 0.05, RDOOR[1] - 0.1
b("Swing2Leaf", l0, l0 + 0.1, RY - 0.03, RY + 0.03, F + 0.02, RDOOR[2] - 0.03, mat="Steel")
b("Swing2Leaf", l1 - 0.1, l1, RY - 0.03, RY + 0.03, F + 0.02, RDOOR[2] - 0.03, mat="Steel")
b("Swing2Leaf", l0 + 0.1, l1 - 0.1, RY - 0.03, RY + 0.03, F + 0.02, F + 1.4, mat="Steel")
b("Swing2Leaf", l0 + 0.1, l1 - 0.1, RY - 0.03, RY + 0.03, F + 1.8, RDOOR[2] - 0.03, mat="Steel")
b("Swing2Leaf", l0 + 0.1, (l0 + l1) / 2 - 0.15, RY - 0.03, RY + 0.03, F + 1.4, F + 1.8, mat="Steel")
b("Swing2Leaf", (l0 + l1) / 2 + 0.15, l1 - 0.1, RY - 0.03, RY + 0.03, F + 1.4, F + 1.8, mat="Steel")
b("Swing2Glass", (l0 + l1) / 2 - 0.15, (l0 + l1) / 2 + 0.15, RY - 0.006, RY + 0.006, F + 1.4, F + 1.8, mat="Glass")
for sgn in (-1, 1):
    b("Swing2Plate", l1 - 0.35, l1 - 0.15, RY + sgn * 0.03 - (0.01 if sgn < 0 else 0), RY + sgn * 0.03 + (0.01 if sgn > 0 else 0),
      F + 1.0, F + 1.3, mat="Frame")
for z in (F, RDOOR[2] - 0.025):
    c("Swing2Pivot", hx2, RY, z + 0.01, 0.03, 0.02, segs=8, mat="Steel")

# ================================================================ range
RY0, RY1 = YP + TP, Y1 - T
FL = 5.6                                                                          # firing line (shelf front edge)
LANES = 5
lw = (X1 - X0 - 2 * T) / LANES
for (x0, x1) in ((X0 + T + IN, X0 + T + 2 * IN), (X1 - T - 2 * IN, X1 - T - IN)):
    b("DecoAcoustic", x0, x1, RY0, RY1, F, CZ, mat="Acoustic")
for (a0, a1, z0, z1) in split(X0 + T, X1 - T, F, CZ, [(RDOOR[0] - 0.1, RDOOR[1] + 0.1, 0.0, RDOOR[2] + 0.1), (RWIN[0] - 0.1, RWIN[1] + 0.1, RWIN[2] - 0.1, RWIN[3] + 0.1)]):
    b("DecoAcoustic", a0, a1, RY0 + IN, RY0 + 2 * IN, z0, z1, mat="Acoustic")
fy("RulesBoard", -2.5, RY0 + 0.05, F + 1.3, 0.9, 1.12, facing=1, uvs=((1, 0), (0, 0), (0, 1), (1, 1)))
fy("RulesBoard", 6.0, RY0 + 0.05, F + 1.3, 0.9, 1.12, facing=1, uvs=((1, 0), (0, 0), (0, 1), (1, 1)))
b("DecoStripe", X0 + T, X1 - T, FL + 0.6, FL + 0.7, F, F + 0.005, mat="Yellow")     # do-not-cross line
b("DecoStripe", X0 + T, X1 - T, FL - 1.2, FL - 1.1, F, F + 0.005, mat="Red")        # wait line
for k in range(LANES):
    xa = X0 + T + k * lw
    xm = xa + lw / 2
    # booth divider (bullet-stop panel on a steel frame), shelf, lane number, target carrier
    if k > 0:
        b(f"Booth{k}", xa - 0.06, xa + 0.06, FL - 1.0, FL + 0.6, F, F + 2.3, mat="Acoustic")
        b("BoothTrim", xa - 0.08, xa + 0.08, FL - 1.02, FL + 0.62, F + 2.3, F + 2.36, mat="CaseMetal")
        b("BoothTrim", xa - 0.08, xa + 0.08, FL - 1.02, FL - 0.98, F, F + 2.3, mat="CaseMetal")
    b(f"Shelf{k + 1}", xa + 0.12, xa + lw - 0.12, FL, FL + 0.5, F + 0.95, F + 1.0, mat="WoodTop")
    b("ShelfBracket", xa + 0.12, xa + lw - 0.12, FL + 0.44, FL + 0.5, F, F + 0.95, mat="CaseMetal")
    u0, u1 = k / LANES, (k + 1) / LANES
    fy("LaneNumbers", xm, FL - 0.62, CZ - 0.75, 0.5, 0.5, uvs=((u0, 0), (u1, 0), (u1, 1), (u0, 1)))
    b("LaneSign", xm - 0.27, xm + 0.27, FL - 0.6, FL - 0.56, CZ - 0.77, CZ - 0.23, mat="Dark")
    ca("Steel", (xm, FL - 0.58, CZ - 0.23), (xm, FL - 0.58, CZ), 0.012, segs=4)
    # target rail on the ceiling, carrier + paper target down range
    b("Rail", xm - 0.05, xm + 0.05, FL + 0.2, RY1 - 1.6, CZ - 0.1, CZ - 0.02, mat="Steel")
    ty = FL + 1.8 + (k % 3) * 1.2
    b("Carrier", xm - 0.12, xm + 0.12, ty - 0.12, ty + 0.12, CZ - 0.28, CZ - 0.1, mat="CaseMetal")
    ca("DecoWire", (xm - 0.3, ty, CZ - 0.28), (xm - 0.3, ty, F + 2.35), 0.006, segs=4, mat="Dark")
    ca("DecoWire", (xm + 0.3, ty, CZ - 0.28), (xm + 0.3, ty, F + 2.35), 0.006, segs=4, mat="Dark")
    b("DecoClip", xm - 0.35, xm + 0.35, ty - 0.015, ty + 0.015, F + 2.3, F + 2.38, mat="Dark")
    fy("Target", xm, ty, F + 1.25, 0.7, 1.05)
    fy("Target", xm, ty + 0.004, F + 1.25, 0.7, 1.05, facing=1, uvs=((1, 0), (0, 0), (0, 1), (1, 1)))
    # range lights: bright over the booths, softer down range
    K.box("LightCeil", (xm * M, (FL - 1.3) * M, (CZ - 0.015) * M), (1.4 * M, 0.5 * M, 0.03 * M), mat="Light")
    b("LightRange", xm - 0.6, xm + 0.6, RY1 - 1.9, RY1 - 1.75, CZ - 0.06, CZ - 0.03)
    # ear muffs + a box of ammo on each shelf
    ca("DecoMuffs", (xa + 0.4, FL + 0.25, F + 1.06), (xa + 0.6, FL + 0.25, F + 1.06), 0.06, segs=8, mat="Red")
    b("DecoAmmoBox", xa + lw - 0.6, xa + lw - 0.4, FL + 0.1, FL + 0.3, F + 1.0, F + 1.1, mat="Olive")
    if k % 2 == 0:
        pistol(ry_(0.3) @ ROT_DOWN, (xm, FL + 0.25, F + 1.03))
# overhead baffles (angled steel + acoustic face) and a sloped backstop
for by in (FL + 1.6, FL + 3.0, FL + 4.4):
    ang = math.radians(35)
    K.box("Baffle", (0, by * M, (CZ - 0.45) * M), ((X1 - X0 - 2 * T - 0.1) * M, 0.04 * M, 0.75 * M), rz=0, mat="CaseMetal")
    obj_bm = K.bm("Baffle", "CaseMetal")
    obj_bm.verts.ensure_lookup_table()
    vs = obj_bm.verts[-8:]
    piv = Vector((0, by * M, (CZ - 0.45) * M))
    bmesh.ops.rotate(obj_bm, cent=piv, matrix=Matrix.Rotation(-ang, 3, 'X'), verts=vs)
# backstop: steel plate slope from the floor up to the ceiling, rubber face, sand trap
bs0 = RY1 - 1.5
K.quad("Backstop", [((X0 + T) * M, bs0 * M, F * M), ((X1 - T) * M, bs0 * M, F * M),
                    ((X1 - T) * M, (RY1 - 0.1) * M, CZ * M), ((X0 + T) * M, (RY1 - 0.1) * M, CZ * M)],
       uvs=((0, 0), (12, 0), (12, 2.4), (0, 2.4)))
b("BackstopFrame", X0 + T, X1 - T, bs0 - 0.2, bs0, F, F + 0.3, mat="CaseMetal")
b("BackstopWall", X0 + T, X1 - T, RY1 - 0.1, RY1, F, CZ, mat="CaseMetal")
# a fill below the slope so it is solid (collision height field)
for j in range(6):
    yy0 = bs0 + j * 1.4 / 6
    zt = F + (j + 0.5) / 6 * (CZ - F)
    b("BackstopFill", X0 + T + 0.02, X1 - T - 0.02, yy0 + 0.02, yy0 + 1.4 / 6, F, zt - 0.1, mat="CaseMetal")
# vents + exit sign
for vx in (-7.0, 0.0, 7.0):
    b("Vent", vx - 0.4, vx + 0.4, RY0 + 0.6, RY0 + 1.0, CZ - 0.04, CZ, mat="Steel")
b("ExitSign", RDOOR[0] - 0.05, RDOOR[1] + 0.05, RY0 + 0.04, RY0 + 0.1, RDOOR[2] + 0.2, RDOOR[2] + 0.45, mat="Red")

# ================================================================ outside back + roof
b("BackDoor", 8.55, 9.55, Y1 + 0.0, Y1 + 0.04, F, F + 2.15, mat="Steel")          # closed steel fire door (printed panel)
b("BackDoorFrame", 8.45, 9.65, Y1 + 0.0, Y1 + 0.06, F + 2.15, F + 2.25, mat="Frame")
b("BackStep", 8.2, 9.9, Y1, Y1 + 1.0, 0.0, F, mat="Walk")
b("Sconce", 8.9, 9.2, Y1 + 0.06, Y1 + 0.2, F + 2.5, F + 2.65)
# dumpster at the back right
d0, d1, e0, e1 = 3.5, 5.7, Y1 + 0.15, Y1 + 0.95
b("Dumpster", d0, d1, e0, e1, 0.15, 1.4, mat="Olive")
b("DumpsterLid", d0 - 0.05, d1 + 0.05, e0 - 0.05, e1 + 0.05, 1.4, 1.46, mat="Dark")
for dy in (e0 + 0.2, e1 - 0.2):
    for dx in (d0 + 0.15, d1 - 0.15):
        c("Wheel", dx, dy, 0.08, 0.08, 0.1, segs=8, axis='Y', mat="Rubber")
# downpipes on the sides
for (dx, dy) in ((X0 - 0.12, Y1 - 0.5), (X1 + 0.12, Y1 - 0.5), (X0 - 0.12, Y0 + 1.0), (X1 + 0.12, Y0 + 1.0)):
    K.downpipe(dx * M, dy * M, 0, (H + 0.7) * M)
# roof: AC units, vent stacks, hatch
for (ux, uy) in ((-6.0, 7.0), (0.0, 8.5), (6.0, 6.5)):
    b("AcBody", ux - 0.9, ux + 0.9, uy - 0.7, uy + 0.7, H - 0.02, H + 1.0)
    c("Dark", ux, uy, H + 1.01, 0.5, 0.02, segs=16)
    c("Steel", ux, uy, H + 1.03, 0.12, 0.03, segs=8)
for (vx, vy) in ((-9.0, 2.0), (9.0, 1.0)):
    c("Steel", vx, vy, H + 0.4, 0.12, 0.8, segs=10)
    c("Steel", vx, vy, H + 0.85, 0.2, 0.1, segs=10)
b("Hatch", -2.0, -1.0, 2.0, 3.0, H - 0.02, H + 0.25, mat="Steel")
# lot lights at the front corners
for (lx, sgn) in ((-13.0, 1), (13.0, -1)):
    c("Pole", lx, -12.0, 3.5, 0.08, 7.0, segs=10, mat="Steel")
    ca("Pole", (lx, -12.0, 6.9), (lx + sgn * 1.2, -12.0, 7.0), 0.05, mat="Steel")
    K.lamp(((lx + sgn * 1.25) * M, -12.0 * M, 6.92 * M), (0.6 * M, 0.3 * M, 0.08 * M))
    c("Pole", lx, -12.0, 0.15, 0.25, 0.3, segs=12, mat="Walk")

# ================================================================ markers for Server/GunShop
spot("SpotBuy", 3.05, -1.05, F + 0.02)
spot("SpotClerk", 3.05, 1.35, F + 0.02)
spot("SpotCam", 1.2, -3.6, F + 1.85)
spot("SpotCamLook", 3.6, YP, F + 2.2)

K.finish(keep_normals=("DecoRifle", "DecoRifleT", "DecoRifleC", "DecoRifleCT"))
meta = K.export()
meta["driveways"] = [[-1.4 * M, 1.4 * M, "N"]]
import json  # noqa: E402
json.dump(meta, open(os.path.join(A["out"], "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    for name, loc, target, lens in (
            ("01_front", (9 * M, -30 * M, 5 * M), (0, -6 * M, 3 * M), 28),
            ("02_aerial", (26 * M, -30 * M, 24 * M), (0, 2 * M, 0), 26),
            ("03_counter", (-4 * M, -5.2 * M, 1.75 * M), (4 * M, 2.5 * M, 1.6 * M), 20),
            ("04_left", (6 * M, -4.5 * M, 1.8 * M), (-11 * M, -1 * M, 1.4 * M), 20),
            ("05_range", (-10 * M, 3.8 * M, 1.8 * M), (2 * M, 11 * M, 1.4 * M), 18),
            ("06_right", (-3 * M, -2.5 * M, 1.8 * M), (11 * M, -2 * M, 1.3 * M), 20)):
        K.shot(name, loc, target, lens=lens)
