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
    "Hose": solid("Hose", (0.03, 0.03, 0.03), 0.6, 0.0),
    "Nozzle": solid("Nozzle", (0.15, 0.15, 0.16), 0.3, 1.0),
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
}
TILE = {"Forecourt": (6 * M, 6 * M), "Kerb": (2 * M, 2 * M), "ShopWall": (3 * M, 3 * M), "ShopGlass": (3 * 1.6 * M, 3.2 * M),
        "CanopyUnder": (2.4 * M, 2.4 * M), "IslandKerb": (1.2 * M, 1.2 * M)}
EXPLICIT_UV = {"PumpFace", "PumpSide", "PriceFace"}   # UVs set when the quads are made
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
text("Sign", "KESTREL", CAN_FASCIA * 0.55, (CAN_W * 0.12, CAN_Y - CAN_D / 2 - 0.32, CAN_CLEAR + CAN_FASCIA * 0.42), extrude=0.15)
wing("SignMark", (-CAN_W * 0.12 - 9.5, CAN_Y - CAN_D / 2 - 0.3, CAN_CLEAR + CAN_FASCIA * 0.48), CAN_FASCIA * 0.8, depth=0.25)
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
        # nozzle holsters on both faces, nozzles sit in them, hoses run from the cabinet top
        # down in a sag and back up into the nozzle, resting on the island
        for side in (-1, 1):
            fx = ix + side * d / 2
            for off in (-1, 1):
                hy = py + off * w * 0.38
                hz = z0 + 0.3 + h * 0.42
                box("PumpDark", (fx + side * 0.22, hy, hz), (0.44, 0.5, 0.8))              # holster cup
                box("Nozzle", (fx + side * 0.55, hy, hz + 0.15), (0.3, 0.28, 1.0))          # grip
                box("Nozzle", (fx + side * 0.75, hy, hz + 0.55), (0.7, 0.18, 0.18))         # spout
                top_pt = (ix + side * (d / 2 - 0.15), hy, zt - 0.2)
                tube("Hose", [top_pt,
                              (fx + side * 0.6, hy + off * 0.3, zt - 0.6),
                              (fx + side * 1.1, hy + off * 0.5, z0 + 1.2),
                              (fx + side * 0.9, hy + off * 0.2, z0 + 0.35),
                              (fx + side * 0.62, hy, hz - 0.5)], 0.11)

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
text("Sign", "KESTREL  MART", 0.75 * M, (1.2 * M, front - 0.2 + 0.02, SHOP_H - 0.9 * M), extrude=0.15)
wing("SignMark", (-5.8 * M, front - 0.18, SHOP_H - 0.85 * M), 1.2 * M, depth=0.25)
# parapet + roof + rooftop units
box("Roof", (0, SHOP_Y + 0.4 * M, SHOP_H + 0.05), (SHOP_W - 0.4, SHOP_D - 0.8 * M - 0.4, 0.1))
for (cx, cy, w_, d_) in ((-SHOP_W / 4, SHOP_Y + 1.5 * M, 2.2 * M, 1.6 * M), (SHOP_W / 5, SHOP_Y + 2.5 * M, 1.6 * M, 1.6 * M)):
    box("Units", (cx, cy, SHOP_H + 0.6 * M), (w_, d_, 1.1 * M))
    cyl("Units", (cx, cy, SHOP_H + 1.2 * M), 0.5 * M, 0.2, segs=14)
# props at the shop front: ice box, two bins, propane cage (red)
box("IceBox", (-SHOP_W / 2 + 4.0 * M, front - 0.7 * M, 0.65 * M), (2.4 * M, 0.9 * M, 1.3 * M))
text("Sign", "ICE", 0.5 * M, (-SHOP_W / 2 + 4.0 * M, front - 1.16 * M, 0.85 * M), extrude=0.05)
for bx_ in (-3.2 * M, 3.2 * M):
    cyl("Props", (bx_, front - 0.6 * M, 0.55 * M), 0.35 * M, 1.1 * M, segs=12)
box("Props", (SHOP_W / 2 - 4.0 * M, front - 0.7 * M, 0.9 * M), (1.8 * M, 0.8 * M, 1.8 * M))

# ---------------------------------------------------------------- air / water stand
ax, ay = LOT_W / 2 - 3.0 * M, SHOP_Y - SHOP_D / 2 - 2.0 * M
box("PumpTrim", (ax, ay, 0.8 * M), (0.6 * M, 0.45 * M, 1.6 * M))
box("PumpBody", (ax, ay - 0.24 * M, 1.1 * M), (0.5 * M, 0.05, 0.5 * M))
cyl("Hose", (ax + 0.35 * M, ay, 0.6 * M), 0.1, 0.9 * M, segs=6)
text("Sign", "AIR", 0.25 * M, (ax, ay - 0.27 * M, 1.45 * M), extrude=0.04)

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
    if name not in ("ShopGlass",) and name not in EXPLICIT_UV and name != "Paint":
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
shot("05_price_sign", (px + 30, py - 28, 14), (px, py, pole_h - 3 * M), lens=35, res=(1000, 1400))
print("done")
