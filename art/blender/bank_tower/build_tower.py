"""Arkwell Bank tower: tall glass bank skyscraper for the tulevo city (original design).

  blender --background --python build_tower.py -- [OUT_DIR] [--no-render] [--samples N]

Builds the tower, makes its textures, renders previews and exports BankTower.glb.
Units: 1 Blender unit = 1 stud (built in studs, use Scale 1 in Roblox, like CarbineRifle).
Blender -Y = front (Roblox -Z), Z up = Roblox Y up. Origin = ground centre of the tower.

Look: chamfered square glass shaft that tapers as it rises, darker glass on the cut
corners framed by silver fins, a band every ten floors, a crown sliced at a slant
toward the front with a lit rim and a mast on the high corner, a granite podium with
a glass lobby and a cantilevered canopy. Name "ARKWELL" + a chevron mark (our own).
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--")), r"C:\out\banktower")
RENDER = "--no-render" not in argv
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 96
RES_SCALE = float(argv[argv.index("--res") + 1]) if "--res" in argv else 1.0  # preview size factor
TEX = os.path.join(OUT, "textures")
REN = os.path.join(OUT, "renders")
for d in (OUT, TEX, REN):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- layout (studs)
FLOOR = 12.0          # floor height
BAY = 6.0             # window bay width
PODIUM_H = 36.0       # 3 tall floors
SHAFT_TOP = 560.0     # where the slanted crown starts (back edge)
CROWN_HIGH = 650.0    # front edge of the slanted cut
BASE_W, BASE_D, BASE_C = 96.0, 96.0, 20.0   # footprint and corner chamfer
TAPER = 0.84          # top footprint scale
MAST_H = 70.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'NONE'

# ---------------------------------------------------------------- textures
def save_png(name, rgb, alpha=None):
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = rgb
    img.pixels.foreach_set(px[::-1].ravel())  # Blender stores bottom row first
    img.filepath_raw = os.path.join(TEX, name + ".png")
    img.file_format = 'PNG'
    img.save()
    return img


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def solid(name, color, rough, metal):
    c = np.ones((8, 8, 3), np.float32) * np.array(color, np.float32)
    return {"Color": save_png(name + "_Color", c),
            "Roughness": save_png(name + "_Roughness", np.full((8, 8, 3), rough, np.float32)),
            "Metalness": save_png(name + "_Metalness", np.full((8, 8, 3), metal, np.float32))}


def curtain_wall(name, size, bays, floors, glass_top, glass_bot, frame, spandrel, mull=0.035, band=0.16, tint_rand=0.05, seed=1):
    """One repeating module: `bays` x `floors` panes. Returns colour/rough/metal images."""
    rng = np.random.default_rng(seed)
    n = size
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n          # y=0 top row
    fx, fy = (x * bays) % 1.0, (y * floors) % 1.0
    bx, by = np.floor(x * bays).astype(int), np.floor(y * floors).astype(int)
    col = np.zeros((n, n, 3), np.float32)
    gt, gb = np.array(glass_top, np.float32), np.array(glass_bot, np.float32)
    # pane: vertical gradient (sky reflection) + slight per-pane tint so it isn't flat
    pane_t = fy[..., None]
    col[:] = gt * (1 - pane_t) + gb * pane_t
    jitter = rng.uniform(-tint_rand, tint_rand, (floors, bays)).astype(np.float32)
    col *= (1 + jitter[by, bx])[..., None]
    # diagonal sheen across the module
    sheen = np.clip(1 - np.abs((x + y * 0.6) % 1.0 - 0.5) * 5, 0, 1) ** 2 * 0.06
    col += sheen[..., None]
    rough = np.full((n, n), 0.06, np.float32)
    metal = np.full((n, n), 0.85, np.float32)
    # spandrel band at the floor slab (bottom of each floor)
    sp = fy > 1 - band
    col[sp] = spandrel
    rough[sp], metal[sp] = 0.3, 0.7
    # mullions (vertical) and transoms (top/bottom of the band)
    mv = (fx < mull) | (fx > 1 - mull)
    mh = (fy < mull * 0.6) | (np.abs(fy - (1 - band)) < mull * 0.6)
    fr = mv | mh
    col[fr] = frame
    rough[fr], metal[fr] = 0.32, 1.0
    col = np.clip(col, 0, 1)
    return {"Color": save_png(name + "_Color", col),
            "Roughness": save_png(name + "_Roughness", np.repeat(rough[..., None], 3, 2)),
            "Metalness": save_png(name + "_Metalness", np.repeat(metal[..., None], 3, 2))}


def granite(name, size=512, seed=3):
    rng = np.random.default_rng(seed)
    n = size
    base = np.array([0.17, 0.17, 0.18], np.float32)
    noise = rng.normal(0, 1, (n, n)).astype(np.float32)
    # cheap blur for speckle clusters
    k = noise.copy()
    for s in (1, 2, 4):
        k += np.roll(noise, s, 0) + np.roll(noise, -s, 1)
    k /= k.std()
    col = base + (k[..., None] * 0.018) + rng.normal(0, 0.012, (n, n, 1)).astype(np.float32)
    # panel joints: 4 x 2 stone panels per tile
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    j = ((x * 2) % 1 < 0.008) | ((y * 4) % 1 < 0.008)
    col[j] = 0.07
    rough = np.where(j, 0.8, 0.35).astype(np.float32)
    return {"Color": save_png(name + "_Color", np.clip(col, 0, 1)),
            "Roughness": save_png(name + "_Roughness", np.repeat(rough[..., None], 3, 2)),
            "Metalness": save_png(name + "_Metalness", np.zeros((n, n, 3), np.float32))}


TEXSETS = {
    # glass module = 4 bays x 2 floors = 24 x 24 studs
    "Glass": curtain_wall("Glass", 1024, 4, 2, (0.30, 0.45, 0.55), (0.06, 0.13, 0.20),
                          (0.62, 0.65, 0.68), (0.10, 0.12, 0.14), seed=1),
    # corner glass: darker, narrower panes, 3 bays x 2 floors over a 20 x 24 tile
    "CornerGlass": curtain_wall("CornerGlass", 1024, 3, 2, (0.12, 0.17, 0.22), (0.03, 0.05, 0.08),
                                (0.55, 0.58, 0.60), (0.05, 0.06, 0.07), mull=0.05, band=0.22, seed=2),
    # lobby: tall clear panes, 2 bays x 1 floor over 12 x 36
    "LobbyGlass": curtain_wall("LobbyGlass", 1024, 2, 1, (0.55, 0.66, 0.70), (0.30, 0.38, 0.40),
                               (0.12, 0.12, 0.13), (0.12, 0.12, 0.13), mull=0.03, band=0.04, tint_rand=0.0, seed=4),
    "Stone": granite("Stone"),
    "Fins": solid("Fins", (0.70, 0.72, 0.75), 0.25, 1.0),
    "Bands": solid("Bands", (0.30, 0.32, 0.34), 0.35, 1.0),
    "Rim": solid("Rim", (0.78, 0.80, 0.82), 0.22, 1.0),
    "Roof": solid("Roof", (0.16, 0.17, 0.18), 0.6, 0.3),
    "Mast": solid("Mast", (0.72, 0.74, 0.76), 0.3, 1.0),
    "Light": solid("Light", (0.92, 0.96, 1.0), 0.5, 0.0),
    "Sign": solid("Sign", (0.95, 0.95, 0.93), 0.4, 0.2),
    "SignMark": solid("SignMark", (0.95, 0.62, 0.12), 0.4, 0.2),
    "Canopy": solid("Canopy", (0.13, 0.14, 0.15), 0.35, 0.9),
    "Steps": solid("Steps", (0.42, 0.42, 0.43), 0.7, 0.0),
    # v2 detail pass
    "Plant": solid("Plant", (0.14, 0.32, 0.12), 0.85, 0.0),
    "Bark": solid("Bark", (0.30, 0.22, 0.15), 0.95, 0.0),
    "Bench": solid("Bench", (0.55, 0.38, 0.22), 0.7, 0.0),
    "Steel": solid("Steel", (0.16, 0.17, 0.18), 0.4, 0.8),
    "Planter": solid("Planter", (0.36, 0.35, 0.34), 0.5, 0.0),
    "FlagTeal": solid("FlagTeal", (0.05, 0.40, 0.42), 0.8, 0.0),
    "FlagAmber": solid("FlagAmber", (0.95, 0.62, 0.12), 0.8, 0.0),
    "FlagBlue": solid("FlagBlue", (0.10, 0.20, 0.50), 0.8, 0.0),
    "RevDoor": curtain_wall("RevDoor", 256, 2, 1, (0.55, 0.62, 0.66), (0.30, 0.34, 0.36), (0.2, 0.2, 0.21), (0.2, 0.2, 0.21),
                            mull=0.04, band=0.02, tint_rand=0.0, seed=9),
}
SIGN_TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tex")   # tools/bank_textures.py
for _n in ("TowerSign", "PodiumSign", "AtmWall"):
    _img = lambda ch: bpy.data.images.load(os.path.join(SIGN_TEX, f"{_n}_{ch}.png"), check_existing=True)
    TEXSETS[_n] = {"Color": _img("Color"), "Roughness": _img("Roughness"),
                   "Metalness": save_png(_n + "_Metalness", np.full((8, 8, 3), 0.1, np.float32))}
TILE = {"Glass": (24, 24), "CornerGlass": (20, 24), "LobbyGlass": (12, 36), "Stone": (24, 12)}


def make_material(name, emissive=False):
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
    if emissive:
        b.inputs['Emission Color'].default_value = (0.85, 0.92, 1.0, 1)
        b.inputs['Emission Strength'].default_value = 6.0
    return m


# ---------------------------------------------------------------- mesh helpers
PARTS = {}


def new_part(name, mat=None):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.data.materials.append(make_material(mat or name, emissive=(name == "Light")))
    ob["mat"] = mat or name
    PARTS[name] = ob
    return ob


def profile(scale=1.0, grow=0.0):
    """8 corners of the chamfered footprint, counter-clockwise from the front-left chamfer."""
    w, d, c = BASE_W / 2 * scale + grow, BASE_D / 2 * scale + grow, BASE_C * scale + grow * 0.4
    return [Vector(p) for p in (
        (-w + c, -d), (w - c, -d), (w, -d + c), (w, d - c),
        (w - c, d), (-w + c, d), (-w, d - c), (-w, -d + c))]


def scale_at(z):
    return 1.0 + (TAPER - 1.0) * (z / CROWN_HIGH)


def loop_at(z, grow=0.0):
    return [Vector((p.x, p.y, z)) for p in profile(scale_at(z), grow)]


def box_uv(bm, tile, uv_layer):
    """World-space box projection per face, tile = (u studs, v studs)."""
    tu, tv = tile
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            co = l.vert.co
            if ax == 2:
                u, v = co.x, co.y
            elif ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            else:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            l[uv_layer].uv = (u / tu, v / tv)


def solid_uv(bm, uv_layer):
    for f in bm.faces:
        for l in f.loops:
            l[uv_layer].uv = (0.5, 0.5)


def finish(ob, bm):
    bm.normal_update()
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def add_box(bm, center, size, rot_z=0.0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    for v in vs:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
        v.co.rotate(__import__("mathutils").Euler((0, 0, rot_z)))
        v.co += Vector(center)
    return vs


def prism(bm, bottom, top, cap_bottom=True, cap_top=True):
    """Side walls between two equal-length vertex loops (CCW seen from above)."""
    vb = [bm.verts.new(p) for p in bottom]
    vt = [bm.verts.new(p) for p in top]
    n = len(vb)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((vb[i], vb[j], vt[j], vt[i])))
    if cap_bottom:
        bm.faces.new(list(reversed(vb)))
    if cap_top:
        bm.faces.new(vt)
    return faces


# ---------------------------------------------------------------- crown cut plane
# Plane through the back edge at SHAFT_TOP rising to CROWN_HIGH at the front edge.
def cut_z(y):
    d = BASE_D / 2
    t = (d - y) / (2 * d)            # 0 at back (+Y), 1 at front (-Y)
    return SHAFT_TOP + t * (CROWN_HIGH - SHAFT_TOP)


CUT_N = Vector((0, CROWN_HIGH - SHAFT_TOP, BASE_D)).normalized()  # plane normal (up + forward)
CUT_P = Vector((0, 0, cut_z(0)))


def clip_to_crown(bm):
    """Cut everything above the slanted crown plane and close the hole."""
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=CUT_P, plane_no=CUT_N, clear_outer=True)
    edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)


# ---------------------------------------------------------------- tower glass shaft
def shaft_parts():
    glass = new_part("Glass")
    corner = new_part("CornerGlass")
    z0, z1 = PODIUM_H - 2, CROWN_HIGH + 4
    lb, lt = loop_at(z0), loop_at(z1)
    for ob, idx in ((glass, (0, 2, 4, 6)), (corner, (1, 3, 5, 7))):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("UVMap")
        for i in idx:
            j = (i + 1) % 8
            a, b, c, d = lb[i], lb[j], lt[j], lt[i]
            # inset the corner glass 1.2 studs so the fins stand proud
            if ob is corner:
                n = (b - a).cross(Vector((0, 0, 1))).normalized()
                a, b, c, d = (p - n * 1.2 for p in (a, b, c, d))
            f = bm.faces.new([bm.verts.new(p) for p in (a, b, c, d)])
        clip_to_crown(bm)
        # UV: u = position along the face measured at the base width (bays converge with taper)
        tu, tv = TILE[ob.name]
        for f in bm.faces:
            if abs(f.normal.z) > 0.9:   # crown cap from the cut; roof covers it
                for l in f.loops:
                    l[uv].uv = (0.5, 0.0)
                continue
        bm.normal_update()
        for f in bm.faces:
            if abs(f.normal.z) > 0.9:
                continue
            h = Vector((f.normal.x, f.normal.y, 0)).normalized()
            side = Vector((0, 0, 1)).cross(h)  # along the face, left to right seen from outside
            for l in f.loops:
                co = l.vert.co
                s = scale_at(co.z)
                l[uv].uv = (side.dot(Vector((co.x, co.y, 0))) / s / tu, (co.z - PODIUM_H) / tv)
        # drop the cap faces; the Roof part closes the crown
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.5], context='FACES')
        finish(ob, bm)


def fins():
    """Silver fins on all 8 edges where faces meet the cut corners, full height."""
    ob = new_part("Fins")
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    z0, z1 = PODIUM_H - 2, CROWN_HIGH + 4
    for i in range(8):
        pb, pt = loop_at(z0)[i], loop_at(z1)[i]
        # fin: 1.6 wide, sticking out 2.2 along the corner bisector
        prev, nxt = loop_at(z0)[i - 1], loop_at(z0)[(i + 1) % 8]
        out = ((pb - prev).normalized() + (pb - nxt).normalized())
        out.z = 0
        out.normalize()
        tang = Vector((0, 0, 1)).cross(out)
        sb, st = [], []
        for p in (pb, pt):
            pts = [p + tang * -0.8 - out * 0.4, p + tang * 0.8 - out * 0.4, p + tang * 0.8 + out * 2.2, p + tang * -0.8 + out * 2.2]
            (sb if p is pb else st).append(pts)
        prism(bm, sb[0], st[0])
    clip_to_crown(bm)
    solid_uv(bm, uv)
    finish(ob, bm)


def bands():
    """Dark metal ring every ten floors (mechanical floors)."""
    ob = new_part("Bands")
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    z = PODIUM_H + FLOOR * 10
    while z < SHAFT_TOP - 20:
        prism(bm, loop_at(z - 1.6, 0.9), loop_at(z + 1.6, 0.9))
        z += FLOOR * 10
    solid_uv(bm, uv)
    finish(ob, bm)


def crown():
    """Roof cap on the slanted cut, a silver rim around it and a light strip below the rim."""
    roof, rim, light = new_part("Roof"), new_part("Rim"), new_part("Light")
    # the cut outline of the shaft (slightly grown so it covers the glass edge)
    big = bmesh.new()
    prism(big, loop_at(PODIUM_H, 0.0), loop_at(CROWN_HIGH + 40, 0.0))
    geom = list(big.verts) + list(big.edges) + list(big.faces)
    r = bmesh.ops.bisect_plane(big, geom=geom, plane_co=CUT_P, plane_no=CUT_N, clear_outer=True)
    cut_verts = [v for v in r["geom_cut"] if isinstance(v, bmesh.types.BMVert)]
    # order the outline by angle around the centre
    c = sum((v.co for v in cut_verts), Vector()) / len(cut_verts)
    outline = sorted((v.co.copy() for v in cut_verts), key=lambda p: math.atan2(p.y - c.y, p.x - c.x))
    big.free()
    up = CUT_N

    def ring(grow):
        res = []
        for p in outline:
            h = Vector((p.x, p.y, 0))
            hh = h + h.normalized() * grow
            res.append(Vector((hh.x, hh.y, cut_z(hh.y))))
        return res

    # roof: flat slab on the cut plane, 1 stud thick, slightly inset with a raised parapet (rim)
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    top = [p + up * 0.6 for p in ring(-1.0)]
    bot = [p - up * 2.0 for p in ring(-1.0)]
    prism(bm, bot, top)
    solid_uv(bm, u); finish(roof, bm)
    # rim: parapet wall 4 studs tall following the edge, 1.2 thick, sticking out past the fins
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    outer, inner = ring(3.2), ring(1.6)
    lo_o = [p - up * 2.5 for p in outer]; hi_o = [p + up * 3.0 for p in outer]
    lo_i = [p - up * 2.5 for p in inner]; hi_i = [p + up * 3.0 for p in inner]
    vlo_o = [bm.verts.new(p) for p in lo_o]; vhi_o = [bm.verts.new(p) for p in hi_o]
    vlo_i = [bm.verts.new(p) for p in lo_i]; vhi_i = [bm.verts.new(p) for p in hi_i]
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((vlo_o[i], vlo_o[j], vhi_o[j], vhi_o[i]))   # outside
        bm.faces.new((vhi_i[i], vhi_i[j], vlo_i[j], vlo_i[i]))   # inside
        bm.faces.new((vhi_o[i], vhi_o[j], vhi_i[j], vhi_i[i]))   # top
        bm.faces.new((vlo_i[i], vlo_i[j], vlo_o[j], vlo_o[i]))   # bottom
    solid_uv(bm, u); finish(rim, bm)
    # light strip: thin glowing band just under the rim
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    lo = [p - up * 4.2 for p in ring(2.6)]; hi = [p - up * 2.6 for p in ring(2.6)]
    prism(bm, lo, hi, cap_bottom=False, cap_top=False)
    solid_uv(bm, u); finish(light, bm)
    return outline


def mast():
    """Tapered mast standing on the high front edge of the crown, with a beacon."""
    ob = new_part("Mast")
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    base = Vector((0, -BASE_D / 2 * scale_at(CROWN_HIGH) + 12, cut_z(-BASE_D / 2 * scale_at(CROWN_HIGH) + 12)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=2.4, radius2=0.5, depth=MAST_H,
                          matrix=__import__("mathutils").Matrix.Translation(base + Vector((0, 0, MAST_H / 2 - 2))))
    # three stay rings
    for k in (0.25, 0.5, 0.75):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=3.6 - k * 2.4, radius2=3.6 - k * 2.4, depth=0.6,
                              matrix=__import__("mathutils").Matrix.Translation(base + Vector((0, 0, MAST_H * k))))
    solid_uv(bm, u); finish(ob, bm)
    # beacon at the tip goes into the Light part
    light = PARTS["Light"]
    bm = bmesh.new(); bm.from_mesh(light.data); u = bm.loops.layers.uv.verify()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.4,
                              matrix=__import__("mathutils").Matrix.Translation(base + Vector((0, 0, MAST_H - 1.5))))
    solid_uv(bm, u); finish(light, bm)
    return base


# ---------------------------------------------------------------- podium
POD_W, POD_D = 150.0, 136.0
POD_FRONT = -POD_D / 2      # y of the podium front


def podium():
    stone, lobby, canopy, steps = new_part("Stone"), new_part("LobbyGlass"), new_part("Canopy"), new_part("Steps")
    w, d, h = POD_W / 2, POD_D / 2, PODIUM_H
    # stone mass: back and sides solid, front recessed 10 for the lobby
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    rec = 10.0
    # main block behind the lobby
    add_box(bm, (0, rec / 2, h / 2 + 1.0), (POD_W, POD_D - rec, h))
    # two stone pylons framing the lobby at the front corners
    for sx in (-1, 1):
        add_box(bm, (sx * (w - 9), -d + rec / 2, h / 2 + 1.0), (18, rec, h))
    # attic band over the lobby (carries the sign)
    add_box(bm, (0, -d + rec / 2, h - 4 + 1.0), (POD_W - 36, rec, 8))
    # plinth all round
    add_box(bm, (0, 0, 0.5), (POD_W + 4, POD_D + 4, 1.0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    bm.normal_update()
    box_uv(bm, TILE["Stone"], u)
    finish(stone, bm)
    # lobby glass wall in the recess (flat, facing -Y)
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    gx = w - 18
    y = -d + rec - 0.5
    vs = [bm.verts.new(p) for p in ((-gx, y, 1.0), (gx, y, 1.0), (gx, y, h - 7), (-gx, y, h - 7))]
    bm.faces.new(vs)
    bm.normal_update()
    for f in bm.faces:
        for l in f.loops:
            l[u].uv = ((l.vert.co.x + gx) / TILE["LobbyGlass"][0], (l.vert.co.z - 1.0) / (h - 8))
    finish(lobby, bm)
    # canopy: thin cantilevered slab over the entrance, with a glowing underside strip
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    add_box(bm, (0, -d - 6, 15), (64, 32, 1.4))
    for sx in (-1, 1):  # two slim posts
        add_box(bm, (sx * 28, -d - 18, 7.5), (1.0, 1.0, 14))
    solid_uv(bm, u); finish(canopy, bm)
    light = PARTS["Light"]
    bm = bmesh.new(); bm.from_mesh(light.data); u = bm.loops.layers.uv.verify()
    add_box(bm, (0, -d - 21.6, 14.2), (62, 0.6, 0.3))
    solid_uv(bm, u); finish(light, bm)
    # entrance steps (3) in front of the lobby, down to the street
    bm = bmesh.new(); u = bm.loops.layers.uv.new("UVMap")
    for k in range(3):
        add_box(bm, (0, -d - 1 - k * 2.0, 0.5 - k * 0.33 + 0.33), (60 + k * 4, 2.0 + k * 0.0, 1.0))
    solid_uv(bm, u); finish(steps, bm)


# ---------------------------------------------------------------- signs
def text_mesh(bm, body, size, center, extrude=0.4):
    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 3
    cu.align_x, cu.align_y = 'CENTER', 'CENTER'
    cu.space_character = 1.15
    ob = bpy.data.objects.new("txt", cu)
    scene.collection.objects.link(ob)
    # stand the text up facing -Y
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location = center
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(deps).to_mesh()
    me.transform(ob.matrix_world)
    bm.from_mesh(me)
    ob.evaluated_get(deps).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)


def chevron(bm, center, size, depth=0.5):
    """Our mark: two stacked upward chevrons (an abstract 'A' / rising line)."""
    cx, cy, cz = center
    for k, off in enumerate((0.0, 0.42)):
        s = size * (1 - k * 0.25)
        t = s * 0.22
        pts2 = [(-s / 2, -s * 0.3), (0, s * 0.3), (s / 2, -s * 0.3), (s / 2 - t, -s * 0.3), (0, s * 0.3 - t * 1.25), (-s / 2 + t, -s * 0.3)]
        front = [bm.verts.new((cx + x, cy - depth, cz + z + off * size - size * 0.2)) for x, z in pts2]
        back = [bm.verts.new((cx + x, cy, cz + z + off * size - size * 0.2)) for x, z in pts2]
        # two convex quads per side so faces stay planar
        for a in ((0, 1, 4, 5), (1, 2, 3, 4)):
            bm.faces.new([front[i] for i in a])
            bm.faces.new([back[i] for i in reversed(a)])
        n = len(pts2)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((front[j], front[i], back[i], back[j]))


def panel(ob_name, x0, x1, y, z0, z1):
    """Printed sign panel facing -Y (Roblox drops the caps of 3D text, so signs are textures)."""
    ob = PARTS.get(ob_name) or new_part(ob_name)
    bm = bmesh.new()
    if len(ob.data.vertices):
        bm.from_mesh(ob.data)
    u = bm.loops.layers.uv.verify()
    f = bm.faces.new([bm.verts.new(p) for p in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1))])
    for l, t in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[u].uv = t
    finish(ob, bm)


def signs():
    # tower sign near the top of the front face (1024 x 176 sheet -> 58 x 10 studs)
    z = SHAFT_TOP - 30
    yf = -BASE_D / 2 * scale_at(z + 5) - 0.35
    panel("TowerSign", -29, 29, yf, z - 5, z + 5)
    # podium sign on the attic band over the lobby (1536 x 128 -> 72 x 6)
    panel("PodiumSign", -36, 36, -POD_D / 2 - 0.08, PODIUM_H - 6.2, PODIUM_H - 0.2)
    # ATM wall on the left stone pylon
    panel("AtmWall", -74, -60, -POD_D / 2 - 0.08, 1.2, 11.7)


def plaza():
    """Street details in front of the podium: revolving doors, planters with trees, benches,
    bollards, lamp posts (Lamp parts light the plaza at night) and three flagpoles."""
    rng = __import__("random").Random(7)
    bms = {}

    def bm_(name):
        if name not in bms:
            if name not in PARTS:
                new_part(name, "Light" if name.startswith("Lamp") else None)
            bms[name] = bmesh.new()
            bms[name].loops.layers.uv.new("UVMap")
        return bms[name]

    d = POD_D / 2
    # revolving doors in front of the lobby glass
    for dx in (-22, 22):
        cy = -d + 10 - 0.5 - 4.4
        bm = bm_("RevDoor")
        bot = [Vector((dx + 4 * math.cos(a), cy + 4 * math.sin(a), 1.0)) for a in [k / 16 * math.tau for k in range(16)]]
        top = [v + Vector((0, 0, 9)) for v in bot]
        prism(bm, bot, top, cap_bottom=False, cap_top=False)
        bm = bm_("Steel")
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=4.4, radius2=4.4, depth=1.2,
                              matrix=Matrix.Translation((dx, cy, 10.6)))
        for k in range(2):
            add_box(bm, (dx, cy, 5.5), (7.6, 0.15, 0.15) if k == 0 else (0.15, 7.6, 0.15))
            add_box(bm, (dx, cy, 5.5), (0.15, 0.15, 9) if k == 0 else (0.1, 0.1, 0.1))
    # planters with trees + shrubs, benches, bollards
    fy = -d - 12
    for sx in (-1, 1):
        for px in (46, 64):
            x = sx * px
            add_box(bm_("Planter"), (x, fy, 1.2), (9, 5, 2.4))
            add_box(bm_("Plant"), (x, fy, 2.45), (8.4, 4.4, 0.1))
            h = rng.uniform(11, 14)
            add_box(bm_("Bark"), (x, fy, h / 2), (0.8, 0.8, h))
            for k in range(3):
                r = bmesh.ops.create_icosphere(bm_("Plant"), subdivisions=1, radius=rng.uniform(2.8, 3.6))
                ox, oy, oz = rng.uniform(-1.6, 1.6), rng.uniform(-1.6, 1.6), h + rng.uniform(-0.5, 1.5)
                for v in r["verts"]:
                    v.co = Vector((x + ox + v.co.x, fy + oy + v.co.y, oz + v.co.z * 0.8))
        bx = sx * 55
        add_box(bm_("Bench"), (bx, fy, 1.5), (6, 1.6, 0.3))
        add_box(bm_("Bench"), (bx, fy + 0.7, 2.4), (6, 0.25, 1.6))
        for ex in (-2.4, 2.4):
            add_box(bm_("Steel"), (bx + ex, fy, 0.75), (0.3, 1.4, 1.5))
    for i in range(-15, 16):
        x = i * 4.5
        if abs(abs(x) - 28) < 2:
            continue
        add_box(bm_("Steel"), (x, -d - 23, 1.3), (0.9, 0.9, 2.6))
        add_box(bm_("Planter"), (x, -d - 23, 2.7), (1.1, 1.1, 0.2))
    lamps = []
    for sx in (-1, 1):
        x = sx * 74
        add_box(bm_("Steel"), (x, -d - 18, 7.5), (0.6, 0.6, 15))
        add_box(bm_("Steel"), (x - sx * 1.5, -d - 18, 15), (3.6, 0.4, 0.4))
        add_box(bm_("Steel"), (x - sx * 3.0, -d - 18, 14.7), (2.2, 1.2, 0.5))
        name = f"Lamp{len(lamps) + 1}"
        add_box(bm_(name), (x - sx * 3.0, -d - 18, 14.42), (1.9, 1.0, 0.06))
        lamps.append(name)
    # flagpoles on the right of the steps, flags as double-sided panels
    for k, flag in enumerate(("FlagTeal", "FlagAmber", "FlagBlue")):
        x = 44 + k * 9
        add_box(bm_("Steel"), (x, -d - 4, 1.0), (2.0, 2.0, 2.0))
        bmesh.ops.create_cone(bm_("Steel"), cap_ends=True, segments=10, radius1=0.35, radius2=0.25, depth=44,
                              matrix=Matrix.Translation((x, -d - 4, 24)))
        bm = bm_(flag)
        for side in (0, 1):
            pts = [(x + 0.3, -d - 4, 37), (x + 9.3, -d - 4 + 0.6, 37), (x + 9.3, -d - 4 + 0.6, 43), (x + 0.3, -d - 4, 43)]
            pts = [Vector(p) + Vector((0, 0.02 * side, 0)) for p in pts]
            bm.faces.new([bm.verts.new(p) for p in (pts if side == 0 else list(reversed(pts)))])
    for name, bm in bms.items():
        ob = PARTS[name]
        if len(ob.data.vertices):
            old = bmesh.new(); old.from_mesh(ob.data)
            old.to_mesh(ob.data); old.free()
        solid_uv(bm, bm.loops.layers.uv.active) if name != "RevDoor" else None
        if name == "RevDoor":
            u = bm.loops.layers.uv.active
            for f in bm.faces:
                for l in f.loops:
                    co = l.vert.co
                    l[u].uv = (math.atan2(co.y, co.x - math.copysign(22, co.x)) / math.tau * 4, (co.z - 1) / 9)
        finish(ob, bm)
    return lamps


# ---------------------------------------------------------------- build
shaft_parts()
fins()
bands()
outline = crown()
mast_base = mast()
podium()
signs()
LAMPS = plaza()

# normals: everything must face out (Roblox hides back faces)
for ob in PARTS.values():
    bm = bmesh.new(); bm.from_mesh(ob.data)
    if ob.name not in ("Glass", "CornerGlass", "LobbyGlass", "Light", "TowerSign", "PodiumSign", "AtmWall",
                       "FlagTeal", "FlagAmber", "FlagBlue", "RevDoor"):
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free()
    for p in ob.data.polygons:
        p.use_smooth = False
    ob.data.update()

# sanity: open glass sheets must face away from the tower axis
for name in ("Glass", "CornerGlass"):
    me = PARTS[name].data
    bad = sum(1 for p in me.polygons if Vector((p.center.x, p.center.y, 0)).dot(Vector((p.normal.x, p.normal.y, 0))) < 0)
    if bad:
        bm = bmesh.new(); bm.from_mesh(me)
        for f in bm.faces:
            if Vector((f.calc_center_median().x, f.calc_center_median().y, 0)).dot(Vector((f.normal.x, f.normal.y, 0))) < 0:
                f.normal_flip()
        bm.to_mesh(me); bm.free()
        print(f"flipped {bad} {name} faces")


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(ob):
    xs = [v.co for v in ob.data.vertices]
    return [round(min(v[i] for v in xs), 2) for i in range(3)], [round(max(v[i] for v in xs), 2) for i in range(3)]


meta = {"name": "BankTower", "units": "studs", "scale": 1, "parts": {}}
for name, ob in PARTS.items():
    lo, hi = bbox(ob)
    meta["parts"][name] = {"tris": tris(ob), "min": lo, "max": hi}
    print(f"{name:12s} tris {tris(ob):6d}  min {lo}  max {hi}")
meta["height"] = max(p["max"][2] for p in meta["parts"].values())
meta["lamps"] = LAMPS
# colour image per part (tools/upload_textures.py uploads these as Roblox Images, set as TextureID)
import shutil
meta["textures"] = {}
for name, ob in PARTS.items():
    img = TEXSETS[ob["mat"]]["Color"]
    src = bpy.path.abspath(img.filepath_raw or img.filepath)
    if os.path.abspath(os.path.dirname(src)) != os.path.abspath(TEX):
        shutil.copyfile(src, os.path.join(TEX, os.path.basename(src)))
    meta["textures"][name] = os.path.basename(src)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "BankTower.blend"))

# ---------------------------------------------------------------- export
for o in scene.objects:
    o.select_set(o.name in PARTS)
bpy.context.view_layer.objects.active = PARTS["Glass"]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "BankTower.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')
print("exported", os.path.join(OUT, "BankTower.glb"))

if not RENDER:
    sys.exit(0)

# ---------------------------------------------------------------- preview renders
def enable_gpu():
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


enable_gpu()
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = -0.7
scene.render.resolution_x, scene.render.resolution_y = 1600, 900

# sky: physical sky if available, else a gradient
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
        sky.sun_elevation = math.radians(28)
        sky.sun_rotation = math.radians(215)
    except Exception:
        pass
    L.new(sky.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.35
except Exception as e:
    print("sky texture unavailable:", e)
    bg.inputs['Color'].default_value = (0.45, 0.6, 0.8, 1)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 3.5
sun.data.angle = math.radians(1.0)
sun.rotation_euler = (math.radians(62), 0, math.radians(215 - 180 + 90))
scene.collection.objects.link(sun)

# ground + a few plain blocks so the scale reads
gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.035, 0.035, 0.04, 1)
gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0)); bpy.context.object.data.materials.append(gm)
bm_ = bpy.data.materials.new("Block"); bm_.use_nodes = True
bm_.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.10, 0.10, 0.10, 1)
for (x, y, sx, sy, sz) in ((-210, 30, 90, 110, 120), (220, 60, 110, 90, 180), (230, -220, 80, 80, 90), (-230, -230, 90, 70, 60),
                            (0, 260, 160, 80, 140), (-260, 260, 80, 100, 220), (300, 300, 120, 120, 100)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, sz / 2)); o = bpy.context.object
    o.scale = (sx, sy, sz); o.data.materials.append(bm_)
# a 5-stud person for scale at the entrance
pm = bpy.data.materials.new("Person"); pm.use_nodes = True
pm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.6, 0.12, 0.1, 1)
bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=5, location=(6, -POD_D / 2 - 26, 2.5)); bpy.context.object.data.materials.append(pm)
# road strips in front
rm = bpy.data.materials.new("Road"); rm.use_nodes = True
rm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.012, 0.012, 0.014, 1)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -POD_D / 2 - 60, 0.05)); o = bpy.context.object; o.scale = (3000, 40, 1); o.data.materials.append(rm)
bpy.ops.mesh.primitive_plane_add(size=1, location=(-POD_W / 2 - 40, 0, 0.05)); o = bpy.context.object; o.scale = (40, 3000, 1); o.data.materials.append(rm)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scene.collection.objects.link(cam); scene.camera = cam


def shot(name, loc, target, lens=35, res=(1600, 900)):
    cam.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.clip_end = 20000
    scene.render.resolution_x, scene.render.resolution_y = int(res[0] * RES_SCALE), int(res[1] * RES_SCALE)
    scene.render.filepath = os.path.join(REN, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)


H = CROWN_HIGH
shot("01_hero_street", (-260, -520, 6), (0, 0, H * 0.48), lens=24, res=(1000, 1500))
shot("02_full_tower", (-900, -1300, 220), (0, 0, H * 0.45), lens=45, res=(1000, 1500))
shot("03_crown", (-220, -380, H + 40), (0, -10, H - 40), lens=40)
shot("04_entrance", (-60, -POD_D / 2 - 95, 9), (0, -POD_D / 2, 14), lens=28)
shot("05_back_34", (700, 900, 160), (0, 0, H * 0.45), lens=40, res=(1000, 1500))
print("done")
