"""Three downtown office towers for the tulevo city (original designs, no brands).

  blender --background --python build_offices.py -- OUT_DIR [--only A|B|C] [--no-render] [--samples N] [--res F]

  A  OfficeStone   stepped limestone tower: three setback tiers of stone piers and dark
                   windows, granite base with a two-storey glass lobby, lit cornices
  B  OfficeDark    black glass slab: long rectangular block, thin silver mullions,
                   clipped corners, a set-back mechanical screen and a lobby canopy
  C  OfficeRound   rounded blue glass tower: stadium-shaped plan, white floor bands,
                   an open crown frame with a light ring, glass lobby drum

Built in studs (Scale 1), one floor = 12 studs. Blender -Y = front (Roblox -Z), Z up,
origin = ground centre. Each model goes to OUT/<Name>/<Name>.glb with meta.json,
textures/ (one colour PNG per part, listed in textures.json for tools/upload_textures.py)
and renders/.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--") and not a.replace(".", "").isdigit() and a not in "ABC"), r"C:\out\offices")
ONLY = argv[argv.index("--only") + 1] if "--only" in argv else "ABC"
RENDER = "--no-render" not in argv
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
RES_SCALE = float(argv[argv.index("--res") + 1]) if "--res" in argv else 1.0
FLOOR = 12.0


# ================================================================ textures (numpy)
def save_png(path, rgb):
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(px[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    return img


def noise(n, seed, scale=16, amp=1.0):
    rng = np.random.default_rng(seed)
    small = rng.normal(0, 1, (n // scale + 2, n // scale + 2)).astype(np.float32)
    ys = np.linspace(0, small.shape[0] - 2, n)
    xs = np.linspace(0, small.shape[1] - 2, n)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = small[y0][:, x0]; b = small[y0][:, x0 + 1]; c = small[y0 + 1][:, x0]; d = small[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy) * amp


def grimy(col, seed, amt=0.06):
    n = col.shape[0]
    g = noise(n, seed, 32, 1.0)
    y = np.linspace(0, 1, n)[:, None]
    return col * (1 - amt * (0.5 + 0.5 * np.tanh(g)) [..., None] - amt * 0.6 * y[..., None])


def glass_wall(n, bays, floors, top, bot, frame, spandrel, mull=0.03, band=0.18, seed=1, lit=0.0, horiz=False):
    """Curtain wall module: bays x floors panes, sky-gradient glass, a few lit offices."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    fx, fy = (x * bays) % 1, (y * floors) % 1
    bx, by = (x * bays).astype(int), (y * floors).astype(int)
    t = fy[..., None]
    col = np.array(top) * (1 - t) + np.array(bot) * t
    col = col * (1 + rng.uniform(-0.06, 0.06, (floors, bays))[by, bx])[..., None]
    if lit:
        on = rng.random((floors, bays)) < lit
        warm = np.array((0.95, 0.82, 0.55)) * 0.55
        col = np.where(on[by, bx][..., None] & (fy < 1 - band)[..., None], col * 0.5 + warm, col)
    col[fy > 1 - band] = spandrel
    fr = (fx < mull) | (fx > 1 - mull) | (np.abs(fy - (1 - band)) < mull * 0.5) | (fy < mull * 0.5)
    if horiz:  # strong horizontal lines, faint verticals
        fr = (np.abs(fy - (1 - band)) < mull) | (fy < mull) | (fx < mull * 0.4) | (fx > 1 - mull * 0.4)
    col[fr] = frame
    return grimy(col, seed + 10, 0.05)


def stone_wall(n, bays, floors, stone, window, seed=3, pier=0.32, sill=0.30, lit=0.08):
    """Limestone piers and spandrels with deep dark window openings."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    fx, fy = (x * bays) % 1, (y * floors) % 1
    bx, by = (x * bays).astype(int), (y * floors).astype(int)
    col = np.ones((n, n, 3), np.float32) * np.array(stone)
    col *= (1 + noise(n, seed, 8, 0.03))[..., None]
    win = (np.abs(fx - 0.5) < (1 - pier) / 2) & (fy > 0.08) & (fy < 1 - sill)
    t = ((fy - 0.08) / (1 - sill - 0.08))[..., None]
    wcol = np.array(window) * (1.2 - 0.5 * t)
    on = (rng.random((floors, bays)) < lit)[by, bx]
    wcol = np.where(on[..., None], wcol * 0.4 + np.array((0.9, 0.78, 0.5)) * 0.5, wcol)
    col = np.where(win[..., None], wcol, col)
    # reveal shadow on the left/top of each opening + stone joints
    rev = (np.abs(fx - 0.5) < (1 - pier) / 2 + 0.02) & ~win & (fy > 0.06) & (fy < 1 - sill + 0.02)
    col[rev] *= 0.7
    joint = (np.abs(fy - 0.5) < 0.006) | (np.abs(fy - 1 + sill / 2) < 0.006)
    col[joint & ~win] *= 0.82
    return grimy(col, seed + 7, 0.10)


def solid_col(color):
    return np.ones((8, 8, 3), np.float32) * np.array(color, np.float32)


def granite(n, seed, base=(0.16, 0.15, 0.15)):
    col = np.ones((n, n, 3), np.float32) * np.array(base) + noise(n, seed, 2, 0.02)[..., None] + noise(n, seed + 1, 1, 0.015)[..., None]
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    col[((x * 2) % 1 < 0.006) | ((y * 3) % 1 < 0.006)] = 0.06
    return col


# ================================================================ geometry helpers
class Building:
    def __init__(self, name):
        self.name = name
        self.dir = os.path.join(OUT, name)
        self.tex = os.path.join(self.dir, "textures")
        os.makedirs(self.tex, exist_ok=True)
        os.makedirs(os.path.join(self.dir, "renders"), exist_ok=True)
        self.parts, self.bms, self.mats, self.texfiles = {}, {}, {}, {}

    def material(self, mname, rgb, rough=0.4, metal=0.0, emit=None):
        if mname in self.mats:
            return
        path = os.path.join(self.tex, f"{self.name}_{mname}.png")
        img = save_png(path, rgb)
        m = bpy.data.materials.new(f"{self.name}_{mname}")
        m.use_nodes = True
        N, L = m.node_tree.nodes, m.node_tree.links
        b = N['Principled BSDF']
        t = N.new('ShaderNodeTexImage'); t.image = img; t.extension = 'REPEAT'
        L.new(t.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = rough
        b.inputs['Metallic'].default_value = metal
        if emit:
            b.inputs['Emission Color'].default_value = (*emit, 1)
            b.inputs['Emission Strength'].default_value = 5.0
        self.mats[mname] = (m, path)

    def bm(self, part, mname=None):
        if part not in self.bms:
            me = bpy.data.meshes.new(part)
            ob = bpy.data.objects.new(part, me)
            bpy.context.scene.collection.objects.link(ob)
            m, path = self.mats[mname or part]
            ob.data.materials.append(m)
            self.texfiles[part] = os.path.basename(path)
            self.parts[part] = ob
            self.bms[part] = bmesh.new()
            self.bms[part].loops.layers.uv.new("UVMap")
        return self.bms[part]

    def wall(self, part, pts, z0, z1, tile, mname=None, u0=0.0):
        """Vertical walls round a closed loop (CCW from above); u runs along the perimeter."""
        bm = self.bm(part, mname)
        uv = bm.loops.layers.uv.active
        u = u0
        for i in range(len(pts)):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            L = (b - a).length
            if L < 1e-4:
                continue
            vs = [bm.verts.new((a.x, a.y, z0)), bm.verts.new((b.x, b.y, z0)), bm.verts.new((b.x, b.y, z1)), bm.verts.new((a.x, a.y, z1))]
            f = bm.faces.new(vs)
            for l, (uu, vv) in zip(f.loops, ((u, z0), (u + L, z0), (u + L, z1), (u, z1))):
                l[uv].uv = (uu / tile[0], vv / tile[1])
            u += L

    def cap(self, part, pts, z, up=True, mname=None, tile=(24, 24)):
        bm = self.bm(part, mname)
        uv = bm.loops.layers.uv.active
        vs = [bm.verts.new((p[0], p[1], z)) for p in pts]
        f = bm.faces.new(vs if up else list(reversed(vs)))
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / tile[0], l.vert.co.y / tile[1])

    def slab(self, part, pts, z0, z1, mname=None, tile=(24, 24)):
        self.wall(part, pts, z0, z1, tile, mname)
        self.cap(part, pts, z1, True, mname, tile)
        self.cap(part, pts, z0, False, mname, tile)

    def box(self, part, c, s, mname=None, tile=(24, 24)):
        x, y, z = c
        w, d, h = s
        pts = [(x - w / 2, y - d / 2), (x + w / 2, y - d / 2), (x + w / 2, y + d / 2), (x - w / 2, y + d / 2)]
        self.slab(part, pts, z - h / 2, z + h / 2, mname, tile)

    def finish(self):
        for part, bm in self.bms.items():
            bm.normal_update()
            bm.to_mesh(self.parts[part].data)
            bm.free()
            for p in self.parts[part].data.polygons:
                p.use_smooth = False
        meta = {"name": self.name, "units": "studs", "scale": 1, "parts": {}, "lamps": getattr(self, "lamps", [])}
        for part, ob in self.parts.items():
            vs = [v.co for v in ob.data.vertices]
            tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            assert tris < 20000, f"{part} has {tris} tris"
            meta["parts"][part] = {"tris": tris, "min": [round(min(v[i] for v in vs), 2) for i in range(3)],
                                   "max": [round(max(v[i] for v in vs), 2) for i in range(3)]}
        meta["textures"] = self.texfiles
        json.dump(meta, open(os.path.join(self.dir, "meta.json"), "w"), indent=1)
        for o in bpy.context.scene.objects:
            o.select_set(o.name in self.parts)
        bpy.context.view_layer.objects.active = next(iter(self.parts.values()))
        bpy.ops.export_scene.gltf(filepath=os.path.join(self.dir, f"{self.name}.glb"), export_format='GLB', use_selection=True,
                                  export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                                  export_materials='EXPORT', export_image_format='AUTO')
        print(self.name, "parts", {k: v["tris"] for k, v in meta["parts"].items()})
        return meta


def rect(w, d, chamfer=0.0):
    x, y, c = w / 2, d / 2, chamfer
    if c <= 0:
        return [(-x, -y), (x, -y), (x, y), (-x, y)]
    return [(-x + c, -y), (x - c, -y), (x, -y + c), (x, y - c), (x - c, y), (-x + c, y), (-x, y - c), (-x, -y + c)]


def stadium(length, width, segs=10):
    """Rounded plan: straight long sides along X, half circles at the ends, CCW."""
    r = width / 2
    s = length / 2 - r
    pts = []
    for k in range(segs + 1):  # right end, from -90 to +90 deg
        a = -math.pi / 2 + math.pi * k / segs
        pts.append((s + r * math.cos(a), r * math.sin(a)))
    for k in range(segs + 1):  # left end, +90 to 270
        a = math.pi / 2 + math.pi * k / segs
        pts.append((-s + r * math.cos(a), r * math.sin(a)))
    return pts


def grow(pts, d):
    """Offset a convex CCW loop outward by d."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e1 = (p1 - p0).normalized(); e2 = (p2 - p1).normalized()
        n1 = Vector((e1.y, -e1.x)); n2 = Vector((e2.y, -e2.x))
        m = (n1 + n2).normalized()
        out.append(tuple(p1 + m * (d / max(0.3, m.dot(n1)))))
    return out


def scale_pts(pts, k):
    return [(x * k, y * k) for x, y in pts]


# ================================================================ A: stepped limestone tower
def build_A():
    B = Building("OfficeStone")
    STONE = (0.78, 0.72, 0.62)
    B.material("Facade", stone_wall(1024, 3, 3, STONE, (0.10, 0.13, 0.16), seed=3), 0.75)
    B.material("Cornice", grimy(solid_col(STONE) * 1.05 + noise(8, 1, 1, 0.0)[..., None], 2, 0.0), 0.7)
    B.material("Base", granite(512, 5), 0.35, 0.0)
    B.material("Lobby", glass_wall(1024, 3, 1, (0.45, 0.52, 0.55), (0.20, 0.22, 0.22), (0.12, 0.11, 0.10), (0.12, 0.11, 0.10), mull=0.02, band=0.03, seed=4, lit=0.6), 0.08, 0.5)
    B.material("Roof", solid_col((0.28, 0.28, 0.27)), 0.85)
    B.material("Mech", solid_col((0.55, 0.56, 0.57)), 0.5, 0.6)
    B.material("Light", solid_col((1.0, 0.92, 0.75)), 0.5, 0.0, emit=(1.0, 0.85, 0.6))
    tiers = [(84, 84, 10, 2 * FLOOR, 18 * FLOOR), (70, 70, 8, 18 * FLOOR, 26 * FLOOR), (56, 56, 6, 26 * FLOOR, 31 * FLOOR)]
    tile = (84 / 3 * 3 / 3 * 1.0, 3 * FLOOR)  # 3 bays of ~9.3 studs x 3 floors
    tile = (28.0, 3 * FLOOR)
    for i, (w, d, c, z0, z1) in enumerate(tiers):
        p = rect(w, d, c)
        B.wall("Facade", p, z0, z1, tile)
        B.slab("Cornice", grow(p, 1.6), z1, z1 + 2.4)                 # cornice band at each setback
        B.slab("Roof", p, z1 + 2.4, z1 + 2.6) if i < 2 else None
        B.slab("Light", grow(p, 1.7), z1 - 0.6, z1, mname="Light") if i == 2 else None
    # top: mechanical penthouse + stone crown with a lit band
    top = rect(36, 36, 4)
    B.slab("Cornice", top, 31 * FLOOR + 2.4, 31 * FLOOR + 22)
    B.slab("Light", grow(top, 0.15), 31 * FLOOR + 18, 31 * FLOOR + 19.2, mname="Light")
    B.slab("Roof", rect(54, 54, 6), 31 * FLOOR + 2.4, 31 * FLOOR + 2.6)
    for k, (x, y) in enumerate(((-16, 16), (16, -16))):
        B.box("Mech", (x, y, 31 * FLOOR + 8), (8, 8, 10))
    # base: granite podium (2 floors), glass lobby recessed on the front, columns
    base = rect(92, 92, 12)
    B.wall("Base", base, 0, 2 * FLOOR, (24, 12))
    B.slab("Cornice", grow(base, 1.0), 2 * FLOOR, 2 * FLOOR + 1.6)
    B.slab("Roof", base, 2 * FLOOR + 1.6, 2 * FLOOR + 1.8)
    # lobby glass panel set in front of the base, with granite columns
    bm = B.bm("Lobby"); uv = bm.loops.layers.uv.active
    y = -46 - 0.1
    f = bm.faces.new([bm.verts.new(p) for p in ((-30, y, 0.0), (30, y, 0.0), (30, y, 2 * FLOOR - 2), (-30, y, 2 * FLOOR - 2))])
    for l, t in zip(f.loops, ((0, 0), (60 / 12, 0), (60 / 12, 1), (0, 1))):
        l[uv].uv = t
    for x in (-30, -15, 0, 15, 30):
        B.box("Base", (x, -47, FLOOR - 1), (2.4, 2.4, 2 * FLOOR - 2))
    B.box("Cornice", (0, -50, 2 * FLOOR - 2.5), (66, 8, 1.4))           # entrance canopy
    B.box("Light", (0, -54.1, 2 * FLOOR - 3.3), (64, 0.3, 0.3), mname="Light")
    detail(B, -62, -46.1, (-22, 22), 60, 31 * FLOOR + 22, (12, 12), mast_z=31 * FLOOR + 22, seed=1)
    return B


# ================================================================ B: black glass slab
def build_B():
    B = Building("OfficeDark")
    B.material("Glass", glass_wall(1024, 4, 3, (0.10, 0.11, 0.13), (0.03, 0.035, 0.045), (0.55, 0.57, 0.60), (0.04, 0.04, 0.05), mull=0.02, band=0.12, seed=7, lit=0.10, horiz=True), 0.05, 0.85)
    B.material("Frame", solid_col((0.62, 0.64, 0.67)), 0.3, 1.0)
    B.material("Base", granite(512, 9, (0.10, 0.10, 0.11)), 0.3)
    B.material("Lobby", glass_wall(1024, 4, 1, (0.50, 0.56, 0.58), (0.24, 0.26, 0.27), (0.10, 0.10, 0.11), (0.10, 0.10, 0.11), mull=0.02, band=0.02, seed=8, lit=0.7), 0.06, 0.5)
    B.material("Roof", solid_col((0.24, 0.24, 0.25)), 0.85)
    B.material("Screen", glass_wall(256, 16, 1, (0.20, 0.21, 0.22), (0.16, 0.17, 0.18), (0.35, 0.36, 0.37), (0.2, 0.2, 0.2), mull=0.25, band=0.0, seed=9), 0.5, 0.8)
    B.material("Light", solid_col((0.85, 0.92, 1.0)), 0.5, 0.0, emit=(0.8, 0.9, 1.0))
    W, D, H = 112, 58, 26 * FLOOR
    plan = rect(W, D, 6)
    tile = (32, 3 * FLOOR)
    B.wall("Glass", plan, 2 * FLOOR, H, tile)
    # silver fins at the clipped corners and every 16 studs on the long faces
    for (x, y) in plan:
        B.box("Frame", (x, y, (2 * FLOOR + H) / 2), (1.2, 1.2, H - 2 * FLOOR))
    for x in range(-48, 49, 16):
        for y in (-D / 2 - 0.4, D / 2 + 0.4):
            B.box("Frame", (x, y, (2 * FLOOR + H) / 2), (0.6, 0.9, H - 2 * FLOOR))
    B.slab("Frame", grow(plan, 0.8), H, H + 1.6)                       # roof edge
    B.slab("Roof", plan, H + 1.6, H + 1.8)
    # mechanical screen box set back on the roof, lit line round its top
    scr = rect(64, 36, 3)
    B.wall("Screen", scr, H + 1.8, H + 22, (16, 20))
    B.cap("Roof", scr, H + 22)
    B.slab("Light", grow(scr, 0.1), H + 20.8, H + 21.6, mname="Light")
    # base: dark granite, lobby glass on front + back, canopy
    B.wall("Base", plan, 0, 2 * FLOOR, (24, 12))
    B.slab("Frame", grow(plan, 0.6), 2 * FLOOR - 0.8, 2 * FLOOR + 0.6)
    for y, s in ((-D / 2 - 0.15, 1), (D / 2 + 0.15, -1)):
        bm = B.bm("Lobby"); uv = bm.loops.layers.uv.active
        xs = (-40, 40) if s > 0 else (40, -40)
        f = bm.faces.new([bm.verts.new(p) for p in ((xs[0], y, 0), (xs[1], y, 0), (xs[1], y, 2 * FLOOR - 1.2), (xs[0], y, 2 * FLOOR - 1.2))])
        for l, t in zip(f.loops, ((0, 0), (80 / 16, 0), (80 / 16, 1), (0, 1))):
            l[uv].uv = t
    B.box("Frame", (0, -D / 2 - 7, 15), (44, 14, 0.9))                 # canopy
    for x in (-20, 20):
        B.box("Frame", (x, -D / 2 - 13, 7.3), (0.8, 0.8, 14.6))
    B.box("Light", (0, -D / 2 - 7, 14.5), (40, 10, 0.1), mname="Light")
    detail(B, -48, -D / 2 - 0.15, (-30, 30), 70, H + 22, (24, 12), mast_z=H + 22, seed=2)
    return B


# ================================================================ C: rounded blue glass tower
def build_C():
    B = Building("OfficeRound")
    B.material("Glass", glass_wall(1024, 4, 2, (0.40, 0.62, 0.70), (0.10, 0.28, 0.36), (0.82, 0.85, 0.86), (0.88, 0.89, 0.88), mull=0.025, band=0.22, seed=11, lit=0.06), 0.06, 0.7)
    B.material("Frame", solid_col((0.86, 0.87, 0.87)), 0.35, 0.6)
    B.material("Base", granite(512, 13, (0.30, 0.29, 0.28)), 0.4)
    B.material("Lobby", glass_wall(1024, 4, 1, (0.55, 0.66, 0.70), (0.28, 0.34, 0.36), (0.75, 0.76, 0.77), (0.75, 0.76, 0.77), mull=0.02, band=0.02, seed=12, lit=0.7), 0.06, 0.5)
    B.material("Roof", solid_col((0.30, 0.30, 0.31)), 0.85)
    B.material("Light", solid_col((0.80, 0.95, 1.0)), 0.5, 0.0, emit=(0.6, 0.9, 1.0))
    L, Wd, H = 100, 60, 34 * FLOOR
    plan = stadium(L, Wd, 12)
    B.wall("Glass", plan, 2 * FLOOR, H, (24, 2 * FLOOR))
    # crown: open frame 3 floors tall above the roof, light ring at its top
    B.slab("Frame", grow(plan, 0.6), H, H + 1.4)
    B.slab("Roof", plan, H + 1.4, H + 1.6)
    crown = grow(plan, 0.2)
    for i, (x, y) in enumerate(crown):
        if i % 2 == 0:
            B.box("Frame", (x, y, H + 18), (1.2, 1.2, 33))
    B.slab("Frame", grow(plan, 0.6), H + 33, H + 35)
    B.slab("Light", grow(plan, 0.7), H + 31.8, H + 32.8, mname="Light")
    # helipad-ish roof disc on a short core
    core = stadium(40, 26, 8)
    B.slab("Roof", core, H + 1.6, H + 12)
    # base: smaller round drum lobby under a podium ring
    B.wall("Base", plan, FLOOR * 1.5, 2 * FLOOR, (24, 12))
    lob = grow(plan, -6)
    B.wall("Lobby", lob, 0, FLOOR * 1.5, (16, FLOOR * 1.5))
    B.cap("Roof", plan, FLOOR * 1.5, up=False)
    B.slab("Frame", grow(plan, 0.5), 2 * FLOOR - 0.6, 2 * FLOOR + 0.6)
    for i, (x, y) in enumerate(plan):
        if i % 3 == 0:
            B.box("Base", (x * 0.97, y * 0.97, FLOOR * 0.75), (2.2, 2.2, FLOOR * 1.5))
    B.slab("Light", grow(plan, 0.55), FLOOR * 1.5 - 0.8, FLOOR * 1.5 - 0.4, mname="Light")
    detail(B, -42, -24.8, (0,), 70, H + 12, (16, 10), mast_z=H + 35, seed=3)
    return B



# ================================================================ v2 detail pass: plaza furniture, revolving doors, roof kit
def detail(B, front_y, door_y, door_xs, plaza_x, roof_z, roof_xy, mast_z=None, seed=1):
    """Street + roof details shared by the three towers (front faces -Y).
    front_y: plaza line for planters/benches/bollards, door_y: lobby glass line, door_xs: revolving door x's,
    plaza_x: half width for planters + poles, roof_z/roof_xy: roof deck height + half size for units, mast_z: top for a mast."""
    rng = __import__("random").Random(seed)
    B.material("Plant", solid_col((0.14, 0.32, 0.12)), 0.85)
    B.material("Bark", solid_col((0.30, 0.22, 0.15)), 0.95)
    B.material("Bench", solid_col((0.55, 0.38, 0.22)), 0.7)
    B.material("Steel", solid_col((0.16, 0.17, 0.18)), 0.4, 0.8)
    B.material("Planter", granite(256, seed + 40, (0.36, 0.35, 0.34)), 0.5)
    B.material("NeonRed", solid_col((1.0, 0.1, 0.08)), 0.5, 0.0, emit=(1.0, 0.1, 0.05))
    B.material("RevDoor", glass_wall(256, 2, 1, (0.55, 0.62, 0.66), (0.30, 0.34, 0.36), (0.2, 0.2, 0.21), (0.2, 0.2, 0.21), mull=0.04, band=0.02, seed=seed + 50, lit=0.8), 0.05, 0.6)
    tree = lambda x, y, h: (B.box("Bark", (x, y, h / 2), (0.7, 0.7, h)), crown(x, y, h))

    def crown(x, y, h):
        bm = B.bm("Plant")
        for k in range(3):
            r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rng.uniform(2.6, 3.4))
            ox, oy, oz = rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5), h + rng.uniform(-0.5, 1.5)
            for v in r["verts"]:
                v.co = Vector((x + ox + v.co.x, y + oy + v.co.y, oz + v.co.z * 0.8))

    # planters with a tree + shrubs, benches between them, bollards along the plaza edge
    for sx in (-1, 1):
        for k, px in enumerate((plaza_x * 0.55, plaza_x * 0.9)):
            x = sx * px
            B.box("Planter", (x, front_y, 1.2), (8, 5, 2.4))
            B.box("Plant", (x, front_y, 2.45), (7.4, 4.4, 0.1))
            tree(x, front_y, rng.uniform(10, 13))
            bm = B.bm("Plant")
            for j in range(3):
                r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.1)
                for v in r["verts"]:
                    v.co = Vector((x - 2.5 + j * 2.5 + v.co.x, front_y + 1.3 + v.co.y, 2.9 + v.co.z * 0.7))
        bx = sx * plaza_x * 0.725
        B.box("Bench", (bx, front_y, 1.5), (6, 1.6, 0.3))
        B.box("Bench", (bx, front_y + 0.7, 2.4), (6, 0.25, 1.6))
        for ex in (-2.4, 2.4):
            B.box("Steel", (bx + ex, front_y, 0.75), (0.3, 1.4, 1.5))
    n = int(plaza_x * 0.35 / 4)
    for i in range(-n, n + 1):
        x = i * 4.0
        B.box("Steel", (x, front_y - 5, 1.3), (0.9, 0.9, 2.6))
        B.box("Planter", (x, front_y - 5, 2.7), (1.1, 1.1, 0.2))
    # lamp posts at the plaza corners (Lamp parts light the plaza at night)
    lamps = getattr(B, "lamps", [])
    B.lamps = lamps
    for sx in (-1, 1):
        x = sx * plaza_x * 1.08
        B.box("Steel", (x, front_y - 3, 7.5), (0.6, 0.6, 15))
        B.box("Steel", (x - sx * 1.5, front_y - 3, 15), (3.6, 0.4, 0.4))
        B.box("Steel", (x - sx * 3.0, front_y - 3, 14.7), (2.2, 1.2, 0.5))
        name = f"Lamp{len(B.lamps) + 1}"
        B.material("Light", solid_col((1.0, 0.95, 0.85)), 0.5, 0.0, emit=(1.0, 0.9, 0.7))
        B.bm(name, "Light")
        B.box(name, (x - sx * 3.0, front_y - 3, 14.42), (1.9, 1.0, 0.06), mname="Light")
        B.lamps.append(name)
    # revolving doors: glass drum, steel top + base discs, four wings
    for dx in door_xs:
        pts = [(dx + 4 * math.cos(a), door_y - 2.2 + 4 * math.sin(a)) for a in [k / 16 * math.tau for k in range(16)]]
        B.wall("RevDoor", pts, 0.2, 9.0, (6.3, 9))
        B.slab("Steel", grow(pts, 0.4), 9.0, 10.2)
        B.slab("Steel", grow(pts, 0.2), 0.0, 0.2)
        for k in range(2):
            a = k * math.pi / 2 + math.pi / 4
            B.box("Steel", (dx, door_y - 2.2, 4.6), (7.6 * abs(math.cos(a)) + 0.15, 7.6 * abs(math.sin(a)) + 0.15, 0.15))
    # roof: cooling units with fans, vent stacks, a window-washing gantry rail
    rx, ry = roof_xy
    for k in range(3):
        x = -rx * 0.5 + k * rx * 0.5
        B.box("Steel", (x, ry * 0.55, roof_z + 3), (7, 5, 6))
        for f in (-1.6, 1.6):
            pts = [(x + f + 1.3 * math.cos(a), ry * 0.55 + 1.3 * math.sin(a)) for a in [j / 12 * math.tau for j in range(12)]]
            B.slab("Planter", pts, roof_z + 6, roof_z + 6.6)
    for (vx, vy) in ((-rx * 0.6, -ry * 0.5), (rx * 0.6, -ry * 0.4), (0, -ry * 0.6)):
        B.box("Steel", (vx, vy, roof_z + 1.5), (0.8, 0.8, 3))
    B.box("Steel", (0, -ry + 1.0, roof_z + 1.2), (rx * 1.6, 0.4, 0.4))
    B.box("Steel", (-rx * 0.3, -ry + 1.6, roof_z + 2.2), (1.2, 1.2, 4.4))
    B.box("Steel", (-rx * 0.3, -ry - 0.6, roof_z + 4.2), (1.0, 5.0, 1.0))
    if mast_z:
        B.box("Steel", (rx * 0.4, 0, mast_z + 14), (1.0, 1.0, 28))
        for k in range(1, 4):
            B.box("Steel", (rx * 0.4, 0, mast_z + k * 7), (3.0, 0.3, 0.3))
        B.box("NeonRed", (rx * 0.4, 0, mast_z + 28.6), (1.4, 1.4, 1.2), mname="NeonRed")
        B.box("NeonRed", (rx * 0.4, 0, mast_z + 14), (1.2, 1.2, 0.8), mname="NeonRed")


# ================================================================ render
def setup_world():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX', 'CUDA'):
            try:
                prefs.compute_device_type = t; prefs.get_devices()
                if any(d.type == t for d in prefs.devices):
                    break
            except Exception:
                continue
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception as e:
        print("GPU setup failed:", e)
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = -0.6
    w = bpy.data.worlds.new("Sky"); w.use_nodes = True; scene.world = w
    N, L = w.node_tree.nodes, w.node_tree.links
    bg = N['Background']
    try:
        sky = N.new('ShaderNodeTexSky')
        for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
            try:
                sky.sky_type = t; break
            except Exception:
                pass
        try:
            sky.sun_elevation, sky.sun_rotation = math.radians(30), math.radians(215)
        except Exception:
            pass
        L.new(sky.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 0.35
    except Exception as e:
        print("no sky", e)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
    sun.data.energy, sun.data.angle = 3.2, math.radians(1)
    sun.rotation_euler = (math.radians(60), 0, math.radians(125))
    scene.collection.objects.link(sun)
    gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.04, 0.04, 0.045, 1)
    bpy.ops.mesh.primitive_plane_add(size=5000); bpy.context.object.data.materials.append(gm)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam
    return cam


def shot(cam, path, loc, target, lens, res):
    scene = bpy.context.scene
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).normalized().to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens, cam.data.clip_end = lens, 20000
    scene.render.resolution_x, scene.render.resolution_y = int(res[0] * RES_SCALE), int(res[1] * RES_SCALE)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


BUILDERS = {"A": build_A, "B": build_B, "C": build_C}
for key in ONLY:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    b = BUILDERS[key]()
    meta = b.finish()
    if RENDER:
        cam = setup_world()
        h = max(p["max"][2] for p in meta["parts"].values())
        r = os.path.join(b.dir, "renders")
        shot(cam, os.path.join(r, "01_street.png"), (-110, -170, 6), (0, 0, h * 0.42), 24, (1000, 1500))
        shot(cam, os.path.join(r, "02_full.png"), (-420, -620, 120), (0, 0, h * 0.45), 40, (1000, 1400))
        shot(cam, os.path.join(r, "03_entrance.png"), (-30, -110, 8), (0, -40, 14), 28, (1600, 900))
        shot(cam, os.path.join(r, "04_roof.png"), (-90, -120, h + 40), (0, 0, h - 20), 30, (1600, 900))
print("done")
