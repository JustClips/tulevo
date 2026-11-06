"""Kestrel Fuel gas station for the tulevo city (original design, our own brand).

  blender --background --python build_gas_station.py -- [OUT_DIR] [--no-render] [--samples N] [--res F]

A typical American roadside station: a big flat canopy on four columns over two pump
islands (two double-sided pumps each), recessed lights under the canopy, a small shop with a
glass front and a lit sign band, a tall price sign, an air/water stand, bins and an ice box.
Brand "KESTREL" with a wing mark, teal + white + amber (ours, not any game's).

Built in studs (Scale 1 in Roblox), 1 m = 3.6 studs. Blender -Y = front (the street side,
Roblox -Z), Z up. Origin = ground centre of the forecourt slab.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--") and not a.replace(".", "").isdigit()), r"C:\out\gasstation")
RENDER = "--no-render" not in argv
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
RES_SCALE = float(argv[argv.index("--res") + 1]) if "--res" in argv else 1.0
TEX = os.path.join(OUT, "textures")
REN = os.path.join(OUT, "renders")
for d in (OUT, TEX, REN):
    os.makedirs(d, exist_ok=True)

M = 3.6  # studs per metre

# ---------------------------------------------------------------- layout (studs)
LOT_W, LOT_D = 48 * M, 40 * M          # forecourt slab
CAN_W, CAN_D = 30 * M, 15 * M          # canopy deck
CAN_Y = -5 * M                         # canopy centre (toward the street)
CAN_CLEAR = 5.0 * M                    # underside height
CAN_FASCIA = 1.3 * M                   # fascia band height
ISLAND_X = (-7.5 * M, 7.5 * M)         # pump island centres
SHOP_W, SHOP_D, SHOP_H = 22 * M, 12 * M, 5.0 * M
SHOP_Y = 12 * M                        # shop centre (back of the lot)

TEAL = (0.02, 0.36, 0.38)
AMBER = (0.98, 0.62, 0.10)
WHITE = (0.93, 0.93, 0.92)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


# ---------------------------------------------------------------- textures
def save_png(name, rgb):
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = rgb
    img.pixels.foreach_set(px[::-1].ravel())
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = 'PNG'
    img.save()
    return img


def texset(name, col, rough, metal):
    n = col.shape[0]
    r = rough if isinstance(rough, np.ndarray) else np.full((n, n), rough, np.float32)
    m = metal if isinstance(metal, np.ndarray) else np.full((n, n), metal, np.float32)
    return {"Color": save_png(name + "_Color", np.clip(col, 0, 1)),
            "Roughness": save_png(name + "_Roughness", np.repeat(r[..., None], 3, 2)),
            "Metalness": save_png(name + "_Metalness", np.repeat(m[..., None], 3, 2))}


def solid(name, color, rough, metal):
    return texset(name, np.ones((8, 8, 3), np.float32) * np.array(color, np.float32), rough, metal)


def concrete(name, size=512, seed=5, base=(0.42, 0.42, 0.40), joint=True):
    rng = np.random.default_rng(seed)
    n = size
    noise = rng.normal(0, 1, (n, n)).astype(np.float32)
    k = noise.copy()
    for s in (1, 3, 7, 15):
        k += np.roll(noise, s, 0) * 0.7 + np.roll(noise, -s, 1) * 0.7
    k /= k.std()
    col = np.array(base, np.float32) + k[..., None] * 0.02
    # oil stains, a few soft blobs
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    for _ in range(4):
        cx, cy, r = rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85), rng.uniform(0.05, 0.12)
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        col *= (1 - 0.18 * np.clip(1 - d, 0, 1) ** 2)[..., None]
    rough = np.full((n, n), 0.85, np.float32)
    if joint:  # saw-cut joints at the tile edge
        j = (x < 0.004) | (y < 0.004)
        col[j] *= 0.55
    return texset(name, col, rough, 0.0)


def shopfront(name, size=1024):
    """Shop glass: 3 tall panes per tile with dark aluminium frames, posters low down."""
    n = size
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    col = np.zeros((n, n, 3), np.float32)
    t = y[..., None]
    col[:] = np.array((0.42, 0.52, 0.55)) * (1 - t) + np.array((0.16, 0.20, 0.22)) * t
    fx = (x * 3) % 1
    frame = (fx < 0.025) | (fx > 0.975) | (y < 0.02) | (y > 0.98) | (np.abs(y - 0.18) < 0.01)
    col[frame] = (0.12, 0.12, 0.13)
    rough = np.where(frame, 0.4, 0.05).astype(np.float32)
    metal = np.where(frame, 1.0, 0.6).astype(np.float32)
    # warm interior glow in the lower half (lit shop)
    glow = np.clip((y - 0.25) / 0.5, 0, 1)[..., None] * np.array((0.18, 0.15, 0.08))
    col = np.where(frame[..., None], col, col + glow)
    return texset(name, col, rough, metal)


def stripes(name, size=256):
    """Fascia: teal band with a white stripe and a thin amber line (tiles along U)."""
    n = size
    y = np.mgrid[0:n, 0:n][0].astype(np.float32) / n  # 0 top
    col = np.ones((n, n, 3), np.float32) * np.array(TEAL)
    col[(y > 0.62) & (y < 0.80)] = WHITE
    col[(y > 0.84) & (y < 0.89)] = AMBER
    return texset(name, col, 0.35, 0.2)


TEXDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")  # tools/gas_station_textures.py


def file_set(name, metal=0.0):
    """Colour + roughness sheets drawn by tools/gas_station_textures.py; flat metalness."""
    img = lambda ch: bpy.data.images.load(os.path.join(TEXDIR, f"{name}_{ch}.png"), check_existing=True)
    n = 8
    return {"Color": img("Color"), "Roughness": img("Roughness"),
            "Metalness": save_png(name + "_Metalness", np.full((n, n, 3), metal, np.float32))}


TEXSETS = {
    "Forecourt": file_set("Forecourt"),
    "IslandKerb": file_set("IslandKerb"),
    "PumpFace": file_set("PumpFace", 0.15),
    "PumpSide": file_set("PumpSide", 0.15),
    "PriceFace": file_set("PriceSign"),
    "ShopSign": file_set("ShopSign"),
    "FasciaBrand": file_set("FasciaBrand"),
    "IceLabel": file_set("IceLabel"),
    "AirLabel": file_set("AirLabel"),
    "NozzleGrip": solid("NozzleGrip", (0.02, 0.02, 0.022), 0.75, 0.0),
    "Paint": solid("Paint", (0.92, 0.92, 0.88), 0.7, 0.0),
    "Kerb": concrete("Kerb", 256, seed=6, base=(0.55, 0.55, 0.53), joint=False),
    "Fascia": file_set("Fascia", 0.1),
    "CanopyUnder": file_set("CanopyUnder", 0.2),
    "Columns": solid("Columns", (0.90, 0.90, 0.89), 0.45, 0.0),
    "ColumnBase": solid("ColumnBase", TEAL, 0.4, 0.2),
    "Light": solid("Light", (0.95, 0.97, 1.0), 0.5, 0.0),
    "PumpBody": solid("PumpBody", (0.90, 0.91, 0.91), 0.35, 0.3),
    "PumpTrim": solid("PumpTrim", TEAL, 0.35, 0.3),
    "PumpDark": solid("PumpDark", (0.05, 0.05, 0.055), 0.3, 0.2),
    "Screen": solid("Screen", (0.10, 0.25, 0.32), 0.1, 0.0),
    "Hose": solid("Hose", (0.035, 0.035, 0.037), 0.55, 0.0),
    "Nozzle": solid("Nozzle", (0.55, 0.56, 0.58), 0.3, 1.0),
    "Bollards": solid("Bollards", (0.95, 0.70, 0.05), 0.45, 0.1),
    "ShopWall": file_set("ShopWall"),
    "ShopGlass": file_set("ShopGlass", 0.5),
    "ShopTrim": solid("ShopTrim", (0.10, 0.10, 0.11), 0.4, 0.8),
    "ShopBand": solid("ShopBand", TEAL, 0.35, 0.1),
    "Roof": solid("Roof", (0.30, 0.30, 0.30), 0.8, 0.0),
    "Units": solid("Units", (0.62, 0.63, 0.63), 0.5, 0.6),
    "Sign": solid("Sign", WHITE, 0.4, 0.0),
    "SignMark": solid("SignMark", AMBER, 0.4, 0.0),
    "SignPanel": solid("SignPanel", TEAL, 0.35, 0.1),
    "PriceBoard": solid("PriceBoard", (0.02, 0.02, 0.025), 0.3, 0.0),
    "PriceDigits": solid("PriceDigits", (1.0, 0.45, 0.05), 0.5, 0.0),
    "SignPole": solid("SignPole", (0.45, 0.46, 0.47), 0.4, 0.9),
    "Props": solid("Props", (0.55, 0.12, 0.10), 0.5, 0.2),
    "IceBox": solid("IceBox", (0.92, 0.94, 0.96), 0.4, 0.1),
    # v4 detail pass
    "DoorGlass": file_set("DoorGlass", 0.3),
    "Vending": file_set("Vending", 0.1),
    "Atm": file_set("Atm", 0.3),
    "PumpNumber": file_set("PumpNumber"),
    "StaffDoor": file_set("StaffDoor", 0.6),
    "PropaneLabel": file_set("PropaneLabel"),
    "BinLabel": file_set("BinLabel"),
    "Steel": solid("Steel", (0.52, 0.54, 0.56), 0.45, 0.85),
    "Bin": solid("Bin", (0.04, 0.26, 0.28), 0.5, 0.2),
    "Extinguisher": solid("Extinguisher", (0.75, 0.06, 0.05), 0.35, 0.1),
    "Tanks": solid("Tanks", (0.90, 0.90, 0.88), 0.4, 0.3),
    "Dumpster": solid("Dumpster", (0.10, 0.25, 0.14), 0.6, 0.3),
    "Block": solid("Block", (0.66, 0.64, 0.60), 0.9, 0.0),
    "Soil": solid("Soil", (0.18, 0.12, 0.08), 1.0, 0.0),
    "Shrub": solid("Shrub", (0.12, 0.30, 0.10), 0.85, 0.0),
    "Palm": solid("Palm", (0.20, 0.42, 0.14), 0.7, 0.0),
    "Trunk": solid("Trunk", (0.40, 0.31, 0.22), 0.95, 0.0),
    "WheelStop": solid("WheelStop", (0.75, 0.74, 0.70), 0.9, 0.0),
    "Coping": solid("Coping", (0.80, 0.80, 0.79), 0.6, 0.2),
}
TILE = {"Forecourt": (6 * M, 6 * M), "Kerb": (2 * M, 2 * M), "ShopWall": (3 * M, 3 * M), "ShopGlass": (3 * 1.6 * M, 3.2 * M),
        "CanopyUnder": (2.4 * M, 2.4 * M), "IslandKerb": (1.2 * M, 1.2 * M)}
EXPLICIT_UV = {"PumpFace", "PumpSide", "PriceFace", "ShopSign", "FasciaBrand", "IceLabel", "AirLabel",
               "DoorGlass", "Vending", "Atm", "PumpNumber", "StaffDoor", "PropaneLabel", "BinLabel"}   # UVs set when the quads are made
EMISSIVE = {"Light": (0.95, 0.97, 1.0), "Sign": (1.0, 1.0, 1.0)}


_mats = {}


def make_material(name):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    _mats[name] = m
    m.use_nodes = True
    N, L = m.node_tree.nodes, m.node_tree.links
    b = N['Principled BSDF']
    t = TEXSETS[name]
    for i, (ch, inp) in enumerate((("Color", "Base Color"), ("Roughness", "Roughness"), ("Metalness", "Metallic"))):
        n = N.new('ShaderNodeTexImage')
        n.location = (-500, 300 - i * 300)
        n.image = t[ch]
        n.extension = 'REPEAT'
        if ch != "Color":
            n.image.colorspace_settings.name = 'Non-Color'
        L.new(n.outputs['Color'], b.inputs[inp])
    if name in EMISSIVE:
        b.inputs['Emission Color'].default_value = (*EMISSIVE[name], 1)
        b.inputs['Emission Strength'].default_value = 4.0 if name == "Light" else 1.5
    return m


PARTS = {}
LAMPS = []  # canopy lamp parts, listed in meta.json for the Roblox lights
BMS = {}


def bm_of(name, mat=None):
    """bmesh for a part; created on first use, written out at the end."""
    if name not in BMS:
        me = bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
        scene.collection.objects.link(ob)
        ob.data.materials.append(make_material(mat or name))
        PARTS[name] = ob
        BMS[name] = bmesh.new()
        BMS[name].loops.layers.uv.new("UVMap")
    return BMS[name]


def quad(name, corners, uvs=((0, 0), (1, 0), (1, 1), (0, 1))):
    """One textured quad (corners counter-clockwise seen from the front) with its own UVs."""
    bm = bm_of(name)
    uv = bm.loops.layers.uv.active
    f = bm.faces.new([bm.verts.new(c) for c in corners])
    for l, t in zip(f.loops, uvs):
        l[uv].uv = t
    return f


def tube(name, pts, radius, segs=6):
    """Hose: a smooth tube through the points (poly curve with a round bevel)."""
    cu = bpy.data.curves.new("hose", 'CURVE')
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution, cu.resolution_u = '3D', radius, 1, 6
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.use_fill_caps = True
    ob = bpy.data.objects.new("hose", cu)
    scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(deps).to_mesh()
    bm_of(name).from_mesh(me)
    ob.evaluated_get(deps).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)


def catmull(pts, per=10):
    pts = [Vector(p) for p in pts]
    P = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def hose_tube(name, pts, radius, segs=8, rib=0.012):
    """Smooth tube through the control points; every other ring slightly fatter (ribbed rubber).
    Returns the sampled centre line so fittings can be placed along it."""
    bm = bm_of(name)
    line = catmull(pts, 7)
    # parallel-transport frames so the tube never twists
    t0 = (line[1] - line[0]).normalized()
    nrm = t0.cross(Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))).normalized()
    rings = []
    for i, c in enumerate(line):
        t = (line[min(i + 1, len(line) - 1)] - line[max(i - 1, 0)]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        r = radius + (rib if i % 2 else 0)
        rings.append([bm.verts.new(c + (nrm * math.cos(a) + bi * math.sin(a)) * r)
                      for a in (2 * math.pi * k / segs for k in range(segs))])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return line


def cyl_along(name, a, b, radius, segs=12):
    """Cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.create_cone(bm_of(name), cap_ends=True, segments=segs, radius1=radius, radius2=radius, depth=d.length,
                          matrix=Matrix.Translation((a + b) / 2) @ rot)


def panel(name, center, width, height, facing=-1):
    """Flat printed sign facing -Y (facing=-1) or +Y, full texture on it."""
    cx, cy, cz = center
    xs = (cx - width / 2, cx + width / 2) if facing < 0 else (cx + width / 2, cx - width / 2)
    quad(name, [(xs[0], cy, cz - height / 2), (xs[1], cy, cz - height / 2), (xs[1], cy, cz + height / 2), (xs[0], cy, cz + height / 2)])


def box(name, center, size, rz=0.0):
    bm = bm_of(name)
    r = bmesh.ops.create_cube(bm, size=1.0)
    mat = Matrix.Translation(Vector(center)) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=mat, verts=r["verts"])
    return r["verts"]


def cyl(name, center, radius, depth, segs=12, axis='Z', r2=None):
    bm = bm_of(name)
    rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius, radius2=radius if r2 is None else r2, depth=depth,
                          matrix=Matrix.Translation(Vector(center)) @ rot)


def text(name, body, size, center, facing=-1, extrude=0.3, rz=None):
    """Text standing up, facing -Y (facing=-1) or +Y (facing=1)."""
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body, cu.size, cu.extrude, cu.resolution_u = body, size, extrude, 2
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    cu.space_character = 1.1
    ob = bpy.data.objects.new("txt", cu)
    scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0 if facing < 0 else math.pi) if rz is None else (math.radians(90), 0, rz)
    ob.location = center
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(deps).to_mesh()
    me.transform(ob.matrix_world)
    bm_of(name).from_mesh(me)
    ob.evaluated_get(deps).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)


def wing(name, center, size, facing=-1, depth=0.4):
    """Brand mark: a stylised kestrel wing, three swept feathers."""
    bm = bm_of(name)
    cx, cy, cz = center
    for k in range(3):
        s = size * (1 - k * 0.22)
        off = k * size * 0.26
        pts = [(-s * 0.5, -off), (s * 0.5, s * 0.30 - off), (s * 0.5, s * 0.12 - off), (-s * 0.25, -off - s * 0.12)]
        f = [bm.verts.new((cx + x, cy + facing * depth, cz + z)) for x, z in pts]
        b = [bm.verts.new((cx + x, cy, cz + z)) for x, z in pts]
        bm.faces.new(f if facing < 0 else list(reversed(f)))
        bm.faces.new(list(reversed(b)) if facing < 0 else b)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((f[j], f[i], b[i], b[j]) if facing < 0 else (f[i], f[j], b[j], b[i]))


# ---------------------------------------------------------------- forecourt
box("Forecourt", (0, 0, -0.25), (LOT_W, LOT_D, 0.5))
# kerb strip along the back and sides (planting edge), open to the street at -Y
for sx in (-1, 1):
    box("Kerb", (sx * (LOT_W / 2 - 0.6), 0, 0.3), (1.2, LOT_D, 0.6))
box("Kerb", (0, LOT_D / 2 - 0.6, 0.3), (LOT_W, 1.2, 0.6))

# ---------------------------------------------------------------- canopy
top = CAN_CLEAR + CAN_FASCIA
box("CanopyUnder", (0, CAN_Y, CAN_CLEAR + 0.2), (CAN_W - 1.0, CAN_D - 1.0, 0.4))
box("Roof", (0, CAN_Y, top - 0.3), (CAN_W - 0.6, CAN_D - 0.6, 0.6))
# fascia band all round (4 slabs so the stripe texture runs along each side)
for (cx, cy, sx, sy) in ((0, CAN_Y - CAN_D / 2, CAN_W, 0.6), (0, CAN_Y + CAN_D / 2, CAN_W, 0.6),
                         (-CAN_W / 2, CAN_Y, 0.6, CAN_D), (CAN_W / 2, CAN_Y, 0.6, CAN_D)):
    box("Fascia", (cx, cy, CAN_CLEAR + CAN_FASCIA / 2), (sx, sy, CAN_FASCIA))
# recessed light panels under the deck, 3 rows x 6
for ix in range(6):
    for iy in range(3):
        x = (ix - 2.5) * CAN_W / 6.4
        y = CAN_Y + (iy - 1) * CAN_D / 3.4
        lamp = f"Lamp{len(LAMPS) + 1}"
        bm_of(lamp, "Light")
        box(lamp, (x, y, CAN_CLEAR - 0.06), (2.2 * M * 0.55, 1.0 * M * 0.55, 0.12))
        LAMPS.append(lamp)
# thin glow line under the fascia edge
box("Light", (0, CAN_Y - CAN_D / 2 + 0.1, CAN_CLEAR - 0.05), (CAN_W - 1.2, 0.3, 0.12))
# brand on the street-facing fascia and the two ends
for face in (-1, 1):  # brand panel on the street side and the back of the canopy
    panel("FasciaBrand", (0, CAN_Y + face * (CAN_D / 2 + 0.33), CAN_CLEAR + CAN_FASCIA / 2), CAN_FASCIA * 9.14, CAN_FASCIA, facing=face)
# columns: one per island end (4), white cladding over a teal base
for ix in ISLAND_X:
    for sy in (-1, 1):
        y = CAN_Y + sy * 3.2 * M
        box("Columns", (ix, y, (CAN_CLEAR + 0.4) / 2 + 0.6), (0.55 * M, 0.55 * M, CAN_CLEAR - 1.0))
        box("ColumnBase", (ix, y, 0.6 + 0.6 * M / 2 + 0.6), (0.62 * M, 0.62 * M, 0.6 * M))

# ---------------------------------------------------------------- pump islands
ISLAND_TOP = 0.7
for ix in ISLAND_X:
    # raised island, painted with yellow/black safety bands, bollards at each end
    box("IslandKerb", (ix, CAN_Y, ISLAND_TOP / 2), (1.3 * M, 9.0 * M, ISLAND_TOP))
    for sy in (-1, 1):
        cyl("Bollards", (ix, CAN_Y + sy * 4.9 * M, ISLAND_TOP + 0.5 * M), 0.12 * M, 1.0 * M, segs=12)
        cyl("Bollards", (ix, CAN_Y + sy * 4.9 * M, ISLAND_TOP + 1.0 * M + 0.15), 0.12 * M, 0.3, segs=12, r2=0.05)
    # two dispensers per island; the wide faces point +-X at the two lanes
    for sy in (-1, 1):
        py = CAN_Y + sy * 1.2 * M
        h, w, d = 2.4 * M, 1.25 * M, 0.6 * M        # height, width (along Y), depth (along X)
        z0 = ISLAND_TOP
        zb, zt = z0 + 0.3, z0 + 0.3 + h * 0.94      # cabinet bottom / top
        box("PumpDark", (ix, py, z0 + 0.15), (d + 0.5, w + 0.5, 0.3))                 # plinth on the island
        box("PumpBody", (ix, py, (zb + zt) / 2), (d - 0.1, w - 0.1, zt - zb))          # cabinet core
        box("PumpDark", (ix, py, zt + 0.18), (d + 0.25, w + 0.25, 0.36))              # cap
        # printed faces (screen, keypad, grade buttons, stickers, brand header) as textures
        for side in (-1, 1):
            x = ix + side * d / 2
            ys = (py - w / 2, py + w / 2) if side > 0 else (py + w / 2, py - w / 2)
            quad("PumpFace", [(x, ys[0], zb), (x, ys[1], zb), (x, ys[1], zt), (x, ys[0], zt)])
            yy = py + side * w / 2
            xs = (ix + d / 2, ix - d / 2) if side > 0 else (ix - d / 2, ix + d / 2)
            quad("PumpSide", [(xs[0], yy, zb), (xs[1], yy, zb), (xs[1], yy, zt), (xs[0], yy, zt)])
        # nozzles in their boots on both faces; each hose runs from a fitting at the top of the
        # face, hangs in a loop down toward the island and comes back up into the nozzle
        for side in (-1, 1):
            fx = ix + side * d / 2
            o = lambda dist: fx + side * dist          # x at a distance out from the face
            for off in (-1, 1):
                hy = py + off * (w / 2 - 0.05)   # at the face edges, clear of the screen
                hz = z0 + 0.3 + h * 0.42
                # boot (holster) with a lip
                box("PumpDark", (o(0.27), hy, hz - 0.05), (0.54, 0.6, 0.8))
                box("PumpDark", (o(0.5), hy, hz + 0.38), (0.12, 0.62, 0.12))
                # spout goes down into the boot, valve body above it
                cyl_along("Nozzle", (o(0.3), hy, hz - 0.25), (o(0.3), hy, hz + 0.75), 0.07)
                box("Nozzle", (o(0.36), hy, hz + 0.92), (0.42, 0.26, 0.42))
                # rubber grip rising out of the body, trigger + guard on its outer side
                box("NozzleGrip", (o(0.5), hy, hz + 1.42), (0.26, 0.24, 0.66))
                box("Nozzle", (o(0.74), hy, hz + 1.36), (0.05, 0.16, 0.5))           # guard bar
                box("Nozzle", (o(0.69), hy, hz + 1.12), (0.14, 0.16, 0.05))          # guard foot
                box("NozzleGrip", (o(0.66), hy, hz + 1.35), (0.07, 0.12, 0.36))      # trigger
                # scuff guard + swivel on top of the grip, the hose screws in here
                cyl_along("NozzleGrip", (o(0.5), hy, hz + 1.74), (o(0.5), hy, hz + 1.98), 0.15)
                cyl_along("Nozzle", (o(0.5), hy, hz + 1.98), (o(0.5), hy, hz + 2.16), 0.1)
                inlet = Vector((o(0.5), hy, hz + 2.16))
                # outlet fitting at the top of the face
                cyl_along("Nozzle", (o(-0.05), hy, zt - 0.4), (o(0.3), hy, zt - 0.4), 0.14)
                outlet = Vector((o(0.3), hy, zt - 0.4))
                line = hose_tube("Hose", [outlet,
                                          (o(0.65), hy, zt - 0.6),
                                          (o(1.0), hy + off * 0.3, hz + 1.2),
                                          (o(1.1), hy + off * 0.45, z0 + 1.1),
                                          (o(0.95), hy + off * 0.4, z0 + 0.5),
                                          (o(0.9), hy + off * 0.2, hz + 1.6),
                                          (o(0.75), hy, hz + 2.75),
                                          (o(0.52), hy, hz + 2.45),
                                          inlet], 0.11)
                # breakaway coupling a little way down the hose
                cyl_along("Nozzle", line[8], line[11], 0.15)

# ---------------------------------------------------------------- shop
sx0, sy0 = SHOP_W / 2, SHOP_Y
front = SHOP_Y - SHOP_D / 2
box("ShopWall", (0, SHOP_Y + 0.8 * M, SHOP_H / 2), (SHOP_W, SHOP_D - 1.6 * M, SHOP_H))     # main block behind the glass
for sx in (-1, 1):  # side walls returning to the front
    box("ShopWall", (sx * (SHOP_W / 2 - 1.0 * M), front + 0.8 * M, SHOP_H / 2), (2.0 * M, 1.6 * M, SHOP_H))
# glass front (recessed 1.2 m under the overhang), single plane facing -Y
bm = bm_of("ShopGlass")
gx, gy = SHOP_W / 2 - 2.0 * M, front + 1.2 * M
vs = [bm.verts.new(p) for p in ((-gx, gy, 0.0), (gx, gy, 0.0), (gx, gy, 3.2 * M), (-gx, gy, 3.2 * M))]
bm.faces.new(vs)
# door frame in the middle
box("ShopTrim", (0, gy - 0.1, 2.4 * M / 2), (2.2 * M, 0.2, 2.4 * M + 0.3))
box("ShopGlass", (0, gy - 0.15, 1.2 * M), (2.0 * M, 0.05, 2.35 * M))
# overhang band with the brand, lit edge under it
box("ShopBand", (0, front + 0.4 * M, SHOP_H - 0.9 * M), (SHOP_W + 0.4, 0.8 * M + 0.4, 1.8 * M))
bm_of("ShopLamp", "Light")
box("ShopLamp", (0, front + 0.02 * M - 0.2, SHOP_H - 1.8 * M - 0.05), (SHOP_W - 1.0, 0.3, 0.12))
band_front = front + 0.4 * M - (0.8 * M + 0.4) / 2
panel("ShopSign", (0, band_front - 0.03, SHOP_H - 0.9 * M), SHOP_W + 0.4, 1.8 * M)
# parapet + roof + rooftop units
box("Roof", (0, SHOP_Y + 0.4 * M, SHOP_H + 0.05), (SHOP_W - 0.4, SHOP_D - 0.8 * M - 0.4, 0.1))
for (cx, cy, w_, d_) in ((-SHOP_W / 4, SHOP_Y + 1.5 * M, 2.2 * M, 1.6 * M), (SHOP_W / 5, SHOP_Y + 2.5 * M, 1.6 * M, 1.6 * M)):
    box("Units", (cx, cy, SHOP_H + 0.6 * M), (w_, d_, 1.1 * M))
    cyl("Units", (cx, cy, SHOP_H + 1.2 * M), 0.5 * M, 0.2, segs=14)
# props at the shop front: ice box, two bins, propane cage (red)
box("IceBox", (-SHOP_W / 2 + 4.0 * M, front - 0.7 * M, 0.65 * M), (2.4 * M, 0.9 * M, 1.3 * M))
panel("IceLabel", (-SHOP_W / 2 + 4.0 * M, front - 0.7 * M - 0.45 * M - 0.03, 0.75 * M), 2.2 * M, 0.82 * M)

# ---------------------------------------------------------------- air / water stand
ax, ay = LOT_W / 2 - 3.0 * M, SHOP_Y - SHOP_D / 2 - 2.0 * M
box("PumpTrim", (ax, ay, 0.8 * M), (0.6 * M, 0.45 * M, 1.6 * M))
box("PumpBody", (ax, ay - 0.24 * M, 1.1 * M), (0.5 * M, 0.05, 0.5 * M))
cyl_along("Nozzle", (ax + 0.28 * M, ay, 1.25 * M), (ax + 0.36 * M, ay, 1.25 * M), 0.12)
hose_tube("Hose", [(ax + 0.36 * M, ay, 1.25 * M), (ax + 0.55 * M, ay - 0.05 * M, 0.9 * M), (ax + 0.55 * M, ay - 0.1 * M, 0.2 * M),
                   (ax + 0.42 * M, ay - 0.15 * M, 0.12 * M), (ax + 0.36 * M, ay - 0.2 * M, 0.45 * M)], 0.09)
cyl_along("Nozzle", (ax + 0.36 * M, ay - 0.2 * M, 0.45 * M), (ax + 0.36 * M, ay - 0.2 * M, 0.75 * M), 0.12)
panel("AirLabel", (ax, ay - 0.225 * M - 0.03, 1.4 * M), 0.56 * M, 0.28 * M)

# ---------------------------------------------------------------- price pylon (street corner)
px, py = -LOT_W / 2 + 3.0 * M, -LOT_D / 2 + 2.0 * M
pole_h = 9.5 * M
for sx in (-1, 1):
    box("SignPole", (px + sx * 1.2 * M, py, pole_h / 2), (0.35 * M, 0.35 * M, pole_h))
# sign cabinet: 3.4 m wide, 6.8 m tall (1:2, matches the 512 x 1024 sheet), printed both sides
sw, sh = 3.4 * M, 6.8 * M
sz0 = pole_h - sh
box("SignPanel", (px, py, sz0 + sh / 2), (sw + 0.6, 0.55 * M, sh + 0.6))
for face in (-1, 1):
    y = py + face * (0.55 * M / 2 + 0.03)
    xs = (px - sw / 2, px + sw / 2) if face < 0 else (px + sw / 2, px - sw / 2)
    quad("PriceFace", [(xs[0], y, sz0), (xs[1], y, sz0), (xs[1], y, sz0 + sh), (xs[0], y, sz0 + sh)])
box("Kerb", (px, py, 0.4), (3.4 * M, 1.4 * M, 0.8))

# ---------------------------------------------------------------- painted markings
# parking bays in front of the shop (5 x 2.7 m), stop bars at the exits, lane arrows
front_y = SHOP_Y - SHOP_D / 2
for k in range(6):
    x = (k - 2.5) * 2.7 * M
    box("Paint", (x, front_y - 1.5 * M - 2.5 * M, 0.012), (0.12 * M, 5.0 * M, 0.024))
for sx in (-1, 1):
    box("Paint", (sx * (LOT_W / 2 - 6 * M), -LOT_D / 2 + 1.2 * M, 0.012), (8 * M, 0.4 * M, 0.024))


def arrow(cx, cy, s, ang):
    bm = bm_of("Paint")
    pts = [(-0.12, -0.5), (0.12, -0.5), (0.12, 0.1), (0.3, 0.1), (0, 0.5), (-0.3, 0.1), (-0.12, 0.1)]
    R = Matrix.Rotation(ang, 2)
    vs = [bm.verts.new((cx + (R @ Vector(p))[0] * s, cy + (R @ Vector(p))[1] * s, 0.026)) for p in pts]
    bm.faces.new(vs[:3] + [vs[6]])
    bm.faces.new([vs[2], vs[3], vs[4], vs[5], vs[6]][::1])


for ix in ISLAND_X:
    for side in (-1, 1):
        arrow(ix + side * 2.6 * M, CAN_Y + 7.5 * M, 2.4 * M, 0)

# ---------------------------------------------------------------- v4 detail pass (Dev: "detail all the buildings more")
def face_y(name, cx, y, z0, width, height, facing=-1, uvs=None):
    """Printed quad in a vertical plane at y, facing -Y (facing=-1) or +Y."""
    xs = (cx - width / 2, cx + width / 2) if facing < 0 else (cx + width / 2, cx - width / 2)
    c = [(xs[0], y, z0), (xs[1], y, z0), (xs[1], y, z0 + height), (xs[0], y, z0 + height)]
    return quad(name, c, uvs) if uvs else quad(name, c)


def face_x(name, x, cy, z0, width, height, facing=1):
    """Printed quad in a vertical plane at x, facing +X (facing=1) or -X."""
    ys = (cy - width / 2, cy + width / 2) if facing > 0 else (cy + width / 2, cy - width / 2)
    return quad(name, [(x, ys[0], z0), (x, ys[1], z0), (x, ys[1], z0 + height), (x, ys[0], z0 + height)])


# shop door: printed glass double door over the dark frame (was a plain black slab)
face_y("DoorGlass", 0, gy - 0.22, 0.02, 2.0 * M, 2.35 * M)
box("Steel", (0, gy - 0.6 * M, 2.45 * M + 0.15), (2.6 * M, 1.0 * M, 0.12))               # little door canopy
for sx in (-1, 1):
    box("Steel", (sx * 1.25 * M, gy - 1.05 * M, 2.45 * M - 0.25), (0.05 * M, 0.05 * M, 0.6))   # hangers to the canopy edge

# vending machines + ATM against the glass, square bins either side of the door
for vx in (14.5, 18.6):
    vy = gy - 0.1 - 1.44
    box("PumpDark", (vx, vy, 1.85 * M / 2), (1.0 * M, 0.8 * M, 1.85 * M))
    face_y("Vending", vx, vy - 0.4 * M - 0.03, 0.05 * M, 0.96 * M, 1.78 * M)
atx, aty = -16.5, gy - 0.1 - 1.26
box("Steel", (atx, aty, 1.7 * M / 2), (0.9 * M, 0.7 * M, 1.7 * M))
box("Steel", (atx, aty - 0.33 * M, 1.62 * M), (0.94 * M, 0.12 * M, 0.2 * M))              # hood over the screen
face_y("Atm", atx, aty - 0.35 * M - 0.03, 0.02 * M, 0.86 * M, 1.6 * M)
BIN_SPOTS = [(-9.5, front - 0.6 * M), (9.5, front - 0.6 * M)] + [(ix, CAN_Y) for ix in ISLAND_X]


def square_bin(bx, by, z0=0.0):
    box("Bin", (bx, by, z0 + 0.5 * M), (0.7 * M, 0.7 * M, 1.0 * M))
    box("Steel", (bx, by, z0 + 1.0 * M + 0.18), (0.76 * M, 0.76 * M, 0.36))                  # lid
    box("PumpDark", (bx, by - 0.38 * M, z0 + 0.86 * M), (0.4 * M, 0.02 * M, 0.12 * M))     # swing flap
    for f in (-1, 1):
        face_y("BinLabel", bx, by + f * (0.35 * M + 0.03), z0 + 0.45 * M, 0.6 * M, 0.22 * M, facing=f)


for bx, by in BIN_SPOTS:
    square_bin(bx, by, ISLAND_TOP if by == CAN_Y else 0.0)

# propane exchange cage (steel frame, bars, red roof, tanks inside)
cx_, cy_ = SHOP_W / 2 - 4.0 * M, front - 0.7 * M
cw, cd, ch = 1.8 * M, 0.8 * M, 1.8 * M
for sx in (-1, 1):
    for sy in (-1, 1):
        box("Steel", (cx_ + sx * cw / 2, cy_ + sy * cd / 2, ch / 2), (0.06 * M, 0.06 * M, ch))
for z in (0.05 * M, ch / 2, ch - 0.05 * M):
    for sy in (-1, 1):
        box("Steel", (cx_, cy_ + sy * cd / 2, z), (cw, 0.05 * M, 0.05 * M))
    for sx in (-1, 1):
        box("Steel", (cx_ + sx * cw / 2, cy_, z), (0.05 * M, cd, 0.05 * M))
for k in range(1, 12):
    x = cx_ - cw / 2 + k * cw / 12
    for sy in (-1, 1):
        box("Steel", (x, cy_ + sy * cd / 2, ch / 2), (0.025 * M, 0.025 * M, ch))
box("Extinguisher", (cx_, cy_, ch + 0.08 * M), (cw + 0.2 * M, cd + 0.2 * M, 0.12 * M))
face_y("PropaneLabel", cx_, cy_ - cd / 2 - 0.1 * M - 0.03, ch - 0.02 * M, cw, 0.22 * M)
for shelf, z0 in ((0, 0.1 * M), (1, ch / 2 + 0.03 * M)):
    box("Steel", (cx_, cy_, z0 - 0.02 * M), (cw - 0.1 * M, cd - 0.1 * M, 0.04 * M))
    for k in range(4):
        tx = cx_ - cw / 2 + (k + 0.5) * cw / 4
        cyl("Tanks", (tx, cy_, z0 + 0.28 * M), 0.15 * M, 0.5 * M, segs=12)
        cyl("Tanks", (tx, cy_, z0 + 0.56 * M), 0.15 * M, 0.08 * M, segs=12, r2=0.08 * M)
        cyl("Steel", (tx, cy_, z0 + 0.64 * M), 0.06 * M, 0.1 * M, segs=8)

# columns: pump number boards, fire extinguishers, paper towel boxes
for i, ix in enumerate(ISLAND_X):
    for j, sy in enumerate((-1, 1)):
        y = CAN_Y + sy * 3.2 * M
        k = i * 2 + j
        u0, vt = (k % 2) * 0.5, 1 - (k // 2) * 0.5
        uvs = ((u0, vt - 0.5), (u0 + 0.5, vt - 0.5), (u0 + 0.5, vt), (u0, vt))
        face_y("PumpNumber", ix, y + sy * (0.275 * M + 0.03), 3.6 * M, 0.5 * M, 0.5 * M, facing=sy, uvs=uvs)
        side = 1 if i else -1                       # the outer face of each column
        ex = ix + side * (0.275 * M + 0.12 * M)
        box("Steel", (ix + side * (0.275 * M + 0.02 * M), y, 1.25 * M), (0.04 * M, 0.2 * M, 0.3 * M))
        cyl("Extinguisher", (ex, y, 1.15 * M), 0.09 * M, 0.5 * M, segs=12)
        cyl("PumpDark", (ex, y, 1.45 * M), 0.04 * M, 0.1 * M, segs=8)
        box("PumpDark", (ex + side * 0.03 * M, y, 1.5 * M), (0.12 * M, 0.04 * M, 0.04 * M))
        box("Steel", (ix - side * (0.275 * M + 0.08 * M), y, 1.4 * M), (0.16 * M, 0.3 * M, 0.4 * M))   # towels

# canopy: security cameras at the four corners
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * (CAN_W / 2 - 1.0 * M), CAN_Y + sy * (CAN_D / 2 - 1.0 * M)
        box("Steel", (x, y, CAN_CLEAR - 0.15 * M), (0.06 * M, 0.06 * M, 0.3 * M))
        box("PumpDark", (x, y - 0.1 * M * sy, CAN_CLEAR - 0.35 * M), (0.14 * M, 0.3 * M, 0.14 * M))

# shop roof: parapet + coping, extra vents and a duct
x0, x1, y0, y1 = -SHOP_W / 2, SHOP_W / 2, front, SHOP_Y + SHOP_D / 2
ph, pt = 0.7 * M, 0.25 * M
for (cx, cy, sx_, sy_) in (((x0 + x1) / 2, y0 + pt / 2, SHOP_W, pt), ((x0 + x1) / 2, y1 - pt / 2, SHOP_W, pt),
                          (x0 + pt / 2, (y0 + y1) / 2, pt, y1 - y0), (x1 - pt / 2, (y0 + y1) / 2, pt, y1 - y0)):
    box("ShopWall", (cx, cy, SHOP_H + ph / 2), (sx_, sy_, ph))
    box("Coping", (cx, cy, SHOP_H + ph + 0.1), (sx_ + 0.3 if sx_ > pt else sx_ + 0.3, sy_ + 0.3, 0.2))
for (vx, vy) in ((-SHOP_W / 3, SHOP_Y + 4 * M), (0, SHOP_Y + 3.5 * M), (SHOP_W / 3, SHOP_Y - 1 * M)):
    cyl("Steel", (vx, vy, SHOP_H + 0.5 * M), 0.08 * M, 1.0 * M, segs=8)
    cyl("Steel", (vx, vy, SHOP_H + 1.05 * M), 0.14 * M, 0.1 * M, segs=8)
box("Units", (-SHOP_W / 4, SHOP_Y + 0.2 * M, SHOP_H + 0.35 * M), (0.6 * M, 1.4 * M, 0.6 * M))   # duct from the AC unit
for cx, cy in ((-SHOP_W / 4, SHOP_Y + 1.5 * M), (SHOP_W / 5, SHOP_Y + 2.5 * M)):
    for k in range(5):  # grille slats on the unit fronts
        box("PumpDark", (cx - 0.6 * M + k * 0.3 * M, cy - 0.81 * M, SHOP_H + 0.6 * M), (0.12 * M, 0.04, 0.8 * M))

# shop back + side: staff door with a lamp, downpipes, AC condensers, electrical panel
face_y("StaffDoor", 10, y1 + 0.04, 0.0, 1.0 * M, 2.2 * M, facing=1)
box("Steel", (10, y1 + 0.5 * M, 2.45 * M), (1.5 * M, 1.0 * M, 0.1 * M))
bm_of("Lamp19", "Light")
box("Lamp19", (10, y1 + 0.85 * M, 2.38 * M), (0.5 * M, 0.2 * M, 0.06))
LAMPS.append("Lamp19")
for sx in (-1, 1):
    for yy in (front + 0.4 * M, y1):
        cyl("Steel", (sx * (SHOP_W / 2 + 0.12 * M), yy + (0.12 * M if yy == y1 else 1.5 * M), SHOP_H / 2), 0.08 * M, SHOP_H, segs=8)
for k, yy in enumerate((SHOP_Y + 0.5 * M, SHOP_Y + 2.2 * M)):
    xx = SHOP_W / 2 + 1.0 * M
    box("Kerb", (xx, yy, 0.1 * M), (1.3 * M, 1.3 * M, 0.2 * M))
    box("Units", (xx, yy, 0.2 * M + 0.45 * M), (1.0 * M, 1.0 * M, 0.9 * M))
    cyl("PumpDark", (xx, yy, 1.1 * M + 0.02), 0.38 * M, 0.04, segs=16)
    cyl("Steel", (xx - 0.5 * M - 0.02, yy, 0.5 * M), 0.04 * M, 0.08 * M, segs=6, axis='X')
    cyl_along("Steel", (xx - 0.54 * M, yy, 0.5 * M), (SHOP_W / 2, yy, 0.5 * M), 0.04 * M)
box("Steel", (SHOP_W / 2 + 0.12 * M, SHOP_Y - 3.0 * M, 1.6 * M), (0.25 * M, 0.8 * M, 1.1 * M))
cyl("Steel", (SHOP_W / 2 + 0.08 * M, SHOP_Y - 3.0 * M, 2.15 * M + (SHOP_H - 2.15 * M) / 2), 0.05 * M, SHOP_H - 2.15 * M, segs=6)

# dumpster enclosure (block walls, open to the front) on the left of the shop
ex0, ex1, ey0, ey1 = -LOT_W / 2 + 2.0 * M, -SHOP_W / 2 - 3.0 * M, SHOP_Y + 0.5 * M, SHOP_Y + 4.8 * M
wh, wt = 1.8 * M, 0.2 * M
box("Block", ((ex0 + ex1) / 2, ey1, wh / 2), (ex1 - ex0, wt, wh))
for xx in (ex0, ex1):
    box("Block", (xx, (ey0 + ey1) / 2, wh / 2), (wt, ey1 - ey0, wh))
    box("Coping", (xx, (ey0 + ey1) / 2, wh + 0.1), (wt + 0.2, ey1 - ey0, 0.2))
box("Coping", ((ex0 + ex1) / 2, ey1, wh + 0.1), (ex1 - ex0, wt + 0.2, 0.2))
for k, dx in enumerate((-1.3 * M, 1.3 * M)):
    cx = (ex0 + ex1) / 2 + dx
    cy = ey1 - 0.95 * M
    box("Dumpster", (cx, cy, 0.15 * M + 0.6 * M), (2.0 * M, 1.4 * M, 1.2 * M))
    for sx in (-1, 1):  # lids, slightly open on one
        box("Dumpster", (cx + sx * 0.5 * M, cy, 1.38 * M + (0.06 * M if k and sx > 0 else 0)), (0.98 * M, 1.5 * M, 0.06 * M),
            rz=0)
    box("Steel", (cx, cy - 0.72 * M, 1.2 * M), (1.9 * M, 0.06 * M, 0.06 * M))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl("PumpDark", (cx + sx * 0.85 * M, cy + sy * 0.55 * M, 0.08 * M), 0.08 * M, 0.08 * M, segs=8, axis='X')

# parking wheel stops
for k in range(5):
    box("WheelStop", ((k - 2) * 2.7 * M, front_y - 1.5 * M - 0.6 * M, 0.08 * M), (1.8 * M, 0.25 * M, 0.16 * M))

# planter beds with shrubs + palms along the quiet side and behind the shop
import random as _r
rng_ = _r.Random(4)


def planter(x0, x1, y0, y1):
    box("Soil", ((x0 + x1) / 2, (y0 + y1) / 2, 0.25 * M), (x1 - x0, y1 - y0, 0.1 * M))
    for (cx, cy, sx_, sy_) in (((x0 + x1) / 2, y0, x1 - x0, 0.3), ((x0 + x1) / 2, y1, x1 - x0, 0.3),
                              (x0, (y0 + y1) / 2, 0.3, y1 - y0), (x1, (y0 + y1) / 2, 0.3, y1 - y0)):
        box("Kerb", (cx, cy, 0.3 * M / 2), (sx_ + 0.3, sy_ + 0.3, 0.3 * M))


def shrub(x, y, s):
    bm = bm_of("Shrub")
    r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s)
    for v in r["verts"]:
        v.co = Vector((v.co.x * rng_.uniform(0.85, 1.15), v.co.y * rng_.uniform(0.85, 1.15), v.co.z * 0.75 * rng_.uniform(0.9, 1.1)))
        v.co += Vector((x, y, 0.3 * M + s * 0.6))


def palm(x, y, h, lean=(0.6, 0.2)):
    pts = [Vector((x + lean[0] * M * (t ** 2), y + lean[1] * M * (t ** 2), 0.3 * M + h * t)) for t in [i / 14 for i in range(15)]]
    for i in range(14):
        r = 0.2 * M * (1 - 0.35 * i / 14) * (1.08 if i % 2 else 1.0)
        cyl_along("Trunk", pts[i], pts[i + 1], r, segs=8)
    top = pts[-1]
    cyl("Trunk", tuple(top + Vector((0, 0, 0.2 * M))), 0.2 * M, 0.5 * M, segs=8, r2=0.1 * M)
    bm = bm_of("Palm")
    for f in range(11):
        a = f / 11 * math.tau + rng_.uniform(-0.15, 0.15)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        L = rng_.uniform(3.6, 4.4) * M
        lift = rng_.uniform(0.3, 0.9)
        rows = []
        for s_ in range(8):
            t = s_ / 7
            c = top + Vector((0, 0, 0.35 * M)) + d * (L * t) + Vector((0, 0, (lift * t - 1.6 * t * t) * M))
            w = 0.55 * M * math.sin(math.pi * min(1.0, t * 1.15 + 0.05))
            dip = Vector((0, 0, -0.18 * M * w / (0.55 * M)))
            rows.append((c + side * w + dip, c, c - side * w + dip))
        for s_ in range(7):
            for k in range(2):
                a1, b1 = rows[s_][k], rows[s_][k + 1]
                a2, b2 = rows[s_ + 1][k], rows[s_ + 1][k + 1]
                top_ = [bm.verts.new(p) for p in (a1, b1, b2, a2)]
                bm.faces.new(top_)
                bot = [bm.verts.new(p - Vector((0, 0, 0.02))) for p in (a2, b2, b1, a1)]
                bm.faces.new(bot)


qx = LOT_W / 2 - 1.2 - 2.0 * M        # inner edge of the quiet-side bed
planter(qx, LOT_W / 2 - 1.2, -LOT_D / 2 + 3.0 * M, SHOP_Y - SHOP_D / 2 - 4.0 * M)
planter(SHOP_W / 2 + 2.5 * M, LOT_W / 2 - 1.2, LOT_D / 2 - 1.2 - 1.6 * M, LOT_D / 2 - 1.2)
planter(px - 1.8 * M, px + 1.8 * M, py + 1.2 * M, py + 3.0 * M)
for k in range(9):
    shrub(qx + 1.0 * M + rng_.uniform(-0.2, 0.2) * M, -LOT_D / 2 + 4.0 * M + k * 2.6 * M, rng_.uniform(0.55, 0.8) * M)
for k in range(6):
    shrub(SHOP_W / 2 + 3.6 * M + k * 2.4 * M, LOT_D / 2 - 2.0 * M, rng_.uniform(0.5, 0.7) * M)
for k in range(3):
    shrub(px - 1.0 * M + k * 1.0 * M, py + 2.1 * M, 0.45 * M)
palm(qx + 1.0 * M, -LOT_D / 2 + 6.0 * M, 10.5 * M, (-0.5, 0.3))
palm(qx + 1.0 * M, -LOT_D / 2 + 17.0 * M, 12.0 * M, (-0.7, -0.2))
palm(LOT_W / 2 - 3.0 * M, LOT_D / 2 - 2.0 * M, 11.0 * M, (-0.4, -0.6))

# lot lights on tall poles (lamp heads light the forecourt at night)
for (lx, ly, ax_dir) in ((LOT_W / 2 - 2.2 * M, -LOT_D / 2 + 12.5 * M, -1), (-LOT_W / 2 + 1.2 * M, SHOP_Y + 6.5 * M, 1)):
    ph_ = 8.0 * M
    cyl("SignPole", (lx, ly, 0.6 * M + ph_ / 2), 0.12 * M, ph_, segs=10, r2=0.09 * M)
    cyl("Kerb", (lx, ly, 0.3 * M), 0.3 * M, 0.6 * M, segs=12)
    box("SignPole", (lx + ax_dir * 0.8 * M, ly, 0.6 * M + ph_ - 0.1 * M), (1.6 * M, 0.12 * M, 0.12 * M))
    hx = lx + ax_dir * 1.7 * M
    box("PumpDark", (hx, ly, 0.6 * M + ph_ - 0.1 * M), (1.0 * M, 0.5 * M, 0.22 * M))
    lamp = f"Lamp{len(LAMPS) + 1}"
    bm_of(lamp, "Light")
    box(lamp, (hx, ly, 0.6 * M + ph_ - 0.1 * M - 0.12 * M), (0.8 * M, 0.38 * M, 0.04))
    LAMPS.append(lamp)

# ---------------------------------------------------------------- finish meshes
for name, bm in BMS.items():
    uv = bm.loops.layers.uv.active
    bm.normal_update()
    tile = TILE.get(name)
    for f in (bm.faces if name not in EXPLICIT_UV else []):
        n = f.normal
        ax_ = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            if not tile:
                l[uv].uv = (0.5, 0.5)
                continue
            if name == "Fascia":
                pass
            if ax_ == 2:
                u, v = co.x, co.y
            elif ax_ == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            else:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            l[uv].uv = (u / tile[0], v / tile[1])
    if name == "Fascia":  # stripe runs along the band: v from the band's bottom to top
        for f in bm.faces:
            for l in f.loops:
                co = l.vert.co
                along = co.x if abs(f.normal.y) > 0.5 else co.y
                l[uv].uv = (along / (6 * M), (co.z - CAN_CLEAR) / CAN_FASCIA)
    if name not in ("ShopGlass", "Palm") and name not in EXPLICIT_UV and name != "Paint":
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(PARTS[name].data)
    bm.free()
    for p in PARTS[name].data.polygons:
        p.use_smooth = False
    PARTS[name].data.update()


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(ob):
    xs = [v.co for v in ob.data.vertices]
    return [round(min(v[i] for v in xs), 2) for i in range(3)], [round(max(v[i] for v in xs), 2) for i in range(3)]


meta = {"name": "GasStation", "units": "studs", "scale": 1, "parts": {}, "lamps": LAMPS}
total = 0
for name, ob in PARTS.items():
    lo, hi = bbox(ob)
    meta["parts"][name] = {"tris": tris(ob), "min": lo, "max": hi}
    total += tris(ob)
    print(f"{name:12s} tris {tris(ob):6d}  min {lo}  max {hi}")
print("total tris", total)
# colour image per part (tools/upload_textures.py uploads these as Roblox Images, set as TextureID)
import shutil
meta["textures"] = {}
for name, ob in PARTS.items():
    img = TEXSETS[ob.data.materials[0].name]["Color"]
    src = bpy.path.abspath(img.filepath_raw or img.filepath)
    dst = os.path.join(TEX, os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    meta["textures"][name] = os.path.basename(src)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "GasStation.blend"))

for o in scene.objects:
    o.select_set(o.name in PARTS)
bpy.context.view_layer.objects.active = PARTS["Forecourt"]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "GasStation.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')
print("exported", os.path.join(OUT, "GasStation.glb"))
if not RENDER:
    sys.exit(0)

# ---------------------------------------------------------------- renders
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            if any(d.type == t for d in prefs.devices):
                break
        except Exception:
            continue
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("GPU setup failed, using CPU:", e)
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = -0.4

w = bpy.data.worlds.new("Sky"); w.use_nodes = True; scene.world = w
N, L = w.node_tree.nodes, w.node_tree.links
bg = N['Background']
try:
    sky = N.new('ShaderNodeTexSky')
    for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
        try:
            sky.sky_type = t
            break
        except Exception:
            pass
    try:
        sky.sun_elevation, sky.sun_rotation = math.radians(30), math.radians(215)
    except Exception:
        pass
    L.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.35
except Exception as e:
    print("sky texture unavailable:", e)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy, sun.data.angle = 3.0, math.radians(1.0)
sun.rotation_euler = (math.radians(58), 0, math.radians(125))
scene.collection.objects.link(sun)


def flat_mat(name, color, rough=0.9):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    return m


bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, -0.55)); bpy.context.object.data.materials.append(flat_mat("Ground", (0.05, 0.05, 0.05)))
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -LOT_D / 2 - 12 * M / 2, -0.5)); o = bpy.context.object
o.scale = (2000, 12 * M, 1); o.data.materials.append(flat_mat("Road", (0.015, 0.015, 0.017)))
# a 5-stud person and a car-sized block at a pump for scale
bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=5, location=(ISLAND_X[0] + 6, CAN_Y + 8, 2.5)); bpy.context.object.data.materials.append(flat_mat("Person", (0.6, 0.12, 0.1)))
bpy.ops.mesh.primitive_cube_add(size=1, location=(ISLAND_X[1] - 3.2 * M, CAN_Y, 0.75 * M)); o = bpy.context.object
o.scale = (1.85 * M, 4.6 * M, 1.4 * M); o.data.materials.append(flat_mat("Car", (0.15, 0.2, 0.35), 0.3))

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam


def shot(name, loc, target, lens=30, res=(1600, 900)):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).normalized().to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens, cam.data.clip_end = lens, 10000
    scene.render.resolution_x, scene.render.resolution_y = int(res[0] * RES_SCALE), int(res[1] * RES_SCALE)
    scene.render.filepath = os.path.join(REN, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


shot("01_street_34", (-120, -190, 18), (0, -5, 14), lens=26)
shot("02_pumps", (-14, CAN_Y * 1.0 - 30, 7), (ISLAND_X[0], CAN_Y, 6), lens=24)
shot("03_shop", (25, -10, 8), (0, SHOP_Y - SHOP_D / 2, 9), lens=22)
shot("04_aerial", (140, -170, 120), (0, 0, 0), lens=30)
shot("06_back", (LOT_W / 2 + 40, LOT_D / 2 + 70, 30), (0, SHOP_Y, 8), lens=24)
shot("07_dumpster", (-LOT_W / 2 + 10, SHOP_Y - 30, 9), (-LOT_W / 2 + 20, SHOP_Y + 12, 4), lens=26)
shot("05_price_sign", (px + 30, py - 28, 14), (px, py, pole_h - 3 * M), lens=35, res=(1000, 1400))
print("done")
