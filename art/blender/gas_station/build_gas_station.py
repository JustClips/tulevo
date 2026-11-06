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


TEXSETS = {
    "Forecourt": concrete("Forecourt"),
    "Kerb": concrete("Kerb", 256, seed=6, base=(0.55, 0.55, 0.53), joint=False),
    "Fascia": stripes("Fascia"),
    "CanopyUnder": solid("CanopyUnder", (0.85, 0.86, 0.86), 0.5, 0.0),
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
    "ShopWall": concrete("ShopWall", 256, seed=7, base=(0.80, 0.79, 0.76), joint=False),
    "ShopGlass": shopfront("ShopGlass"),
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
TILE = {"Forecourt": (6 * M, 6 * M), "Kerb": (2 * M, 2 * M), "ShopWall": (3 * M, 3 * M), "ShopGlass": (3 * 1.6 * M, 3.2 * M)}
EMISSIVE = {"Light": (0.95, 0.97, 1.0), "Screen": (0.25, 0.6, 0.8), "PriceDigits": (1.0, 0.45, 0.05), "Sign": (1.0, 1.0, 1.0)}


def make_material(name):
    m = bpy.data.materials.new(name)
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
BMS = {}


def bm_of(name):
    """bmesh for a part; created on first use, written out at the end."""
    if name not in BMS:
        me = bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
        scene.collection.objects.link(ob)
        ob.data.materials.append(make_material(name))
        PARTS[name] = ob
        BMS[name] = bmesh.new()
        BMS[name].loops.layers.uv.new("UVMap")
    return BMS[name]


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
        box("Light", (x, y, CAN_CLEAR - 0.02), (2.2 * M * 0.55, 1.0 * M * 0.55, 0.1))
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
for ix in ISLAND_X:
    # raised island with rounded-ish ends (two boxes) + bollards at each end
    box("Kerb", (ix, CAN_Y, 0.35), (1.3 * M, 9.0 * M, 0.7))
    for sy in (-1, 1):
        cyl("Bollards", (ix, CAN_Y + sy * 4.9 * M, 0.7 + 0.5 * M), 0.12 * M, 1.0 * M, segs=10)
        cyl("Bollards", (ix, CAN_Y + sy * 4.9 * M, 0.7 + 1.0 * M + 0.15), 0.12 * M, 0.3, segs=10, r2=0.05)
    # two dispensers per island, between the columns
    for sy in (-1, 1):
        py = CAN_Y + sy * 1.2 * M
        h, w, d = 2.3 * M, 1.05 * M, 0.55 * M
        z0 = 0.7
        box("PumpDark", (ix, py, z0 + 0.15), (w + 0.4, d + 0.4, 0.3))                 # plinth
        box("PumpBody", (ix, py, z0 + 0.3 + h * 0.4), (w, d, h * 0.8))                # lower cabinet
        box("PumpTrim", (ix, py, z0 + 0.3 + h * 0.8 + h * 0.075), (w + 0.1, d + 0.1, h * 0.15))  # brand header
        box("PumpDark", (ix, py, z0 + 0.3 + h * 0.95 + 0.15), (w + 0.2, d + 0.2, 0.3))  # cap
        for side in (-1, 1):  # both faces (pumps serve both lanes, faces point +-X)
            fx = ix + side * (w / 2 + 0.05)
            box("Screen", (fx, py, z0 + 0.3 + h * 0.6), (0.1, w * 0.55 * 0.9, h * 0.18))
            box("PumpDark", (fx, py, z0 + 0.3 + h * 0.43), (0.12, w * 0.4, h * 0.12))   # keypad
            # three grade buttons
            for k in range(3):
                box("PumpTrim", (fx + side * 0.05, py - w * 0.28 + k * w * 0.28, z0 + 0.3 + h * 0.30), (0.1, w * 0.2, 0.25 * M * 0.6))
            # nozzle holsters + nozzles on the side, hose loops down
            for k, off in enumerate((-0.32, 0.32)):
                hy = py + off * w * 1.1
                box("PumpDark", (fx + side * 0.25, hy, z0 + 0.3 + h * 0.48), (0.5, 0.35, 0.6))
                box("Nozzle", (fx + side * 0.55, hy, z0 + 0.3 + h * 0.46), (0.25, 0.25, 0.9), rz=0)
                cyl("Hose", (fx + side * 0.6, hy, z0 + 0.3 + h * 0.28), 0.11, h * 0.35, segs=6)
        text("Sign", "KESTREL", 0.32 * M, (ix + w / 2 + 0.11, py, z0 + 0.3 + h * 0.875), extrude=0.06, rz=math.pi / 2)
        text("Sign", "KESTREL", 0.32 * M, (ix - w / 2 - 0.11, py, z0 + 0.3 + h * 0.875), extrude=0.06, rz=-math.pi / 2)

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
box("Light", (0, front + 0.02 * M - 0.2, SHOP_H - 1.8 * M - 0.05), (SHOP_W - 1.0, 0.3, 0.12))
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
pole_h = 9.0 * M
for sx in (-1, 1):
    box("SignPole", (px + sx * 1.0 * M, py, pole_h / 2), (0.35 * M, 0.35 * M, pole_h))
box("SignPanel", (px, py, pole_h - 1.6 * M), (3.2 * M, 0.5 * M, 3.0 * M))       # brand panel
box("PriceBoard", (px, py, pole_h - 4.4 * M), (3.2 * M, 0.45 * M, 2.6 * M))     # price board
for face in (-1, 1):
    fy = py + face * 0.26 * M
    text("Sign", "KESTREL", 0.55 * M, (px, fy, pole_h - 2.2 * M), facing=face, extrude=0.08)
    wing("SignMark", (px - 0.2 * M, fy, pole_h - 1.1 * M), 1.3 * M, facing=face, depth=0.12)
    for k, (grade, price) in enumerate((("REG", "3.49"), ("PLUS", "3.79"), ("PREM", "4.09"))):
        z = pole_h - 3.55 * M - k * 0.8 * M
        text("Sign", grade, 0.32 * M, (px - 0.85 * M * -face * -1 if False else px - 0.85 * M * (1 if face < 0 else -1), fy + face * 0.0, z), facing=face, extrude=0.05)
        text("PriceDigits", price + "9", 0.55 * M, (px + 0.55 * M * (1 if face < 0 else -1), fy, z), facing=face, extrude=0.05)
box("Kerb", (px, py, 0.4), (3.0 * M, 1.4 * M, 0.8))

# ---------------------------------------------------------------- finish meshes
for name, bm in BMS.items():
    uv = bm.loops.layers.uv.active
    bm.normal_update()
    tile = TILE.get(name)
    for f in bm.faces:
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
                l[uv].uv = (along / 20.0, (co.z - CAN_CLEAR) / CAN_FASCIA)
    if name not in ("ShopGlass",):
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


meta = {"name": "GasStation", "units": "studs", "scale": 1, "parts": {}}
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
