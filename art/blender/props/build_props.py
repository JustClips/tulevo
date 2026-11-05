"""Inventory / pickup props: Mead (bottle of honey mead), Chaser (soda can), FirstAidKit.

Run:  blender --background --factory-startup --python build_props.py -- <Mead|Chaser|FirstAidKit> <out_dir>
Units: meters, real size. Origin = bottom center (sits on the ground).
Coords (Blender): -Y = front (label side), +Z = up. GLB exported +Y up, so glTF = (x, z, -y).
Output: <out_dir>/<Name>/<Name>.glb, meta.json, preview.png (+ extra renders).
Original meshes; no logos.
"""
import bpy, bmesh, os, sys, json, math
import numpy as np
from mathutils import Vector, Matrix

ITEM = sys.argv[sys.argv.index("--") + 1]
OUTROOT = sys.argv[sys.argv.index("--") + 2]
OUT = os.path.join(OUTROOT, ITEM)
os.makedirs(OUT, exist_ok=True)
FONT = r"C:\Windows\Fonts\arialbd.ttf"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
PARTS = []


# ------------------------------------------------------------------ helpers
def mat(name, col, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.name = 'BSDF'
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m


def add_obj(name, bm, mats, bevel=None, seg=3, smooth=True, angle=35):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        me.materials.append(m)
    me.shade_smooth() if smooth else me.shade_flat()
    if bevel:
        md = ob.modifiers.new("bev", 'BEVEL'); md.width = bevel; md.segments = seg
        md.limit_method = 'ANGLE'; md.angle_limit = math.radians(angle)
    PARTS.append(ob)
    return ob


def lathe(name, prof, mats, seg=48, mat_of=None, cap=True):
    """prof: list of (r, z) bottom->top. Points with r == 0 become poles."""
    bm = bmesh.new(); rings = []
    for r, z in prof:
        if r == 0:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                          for i in range(seg)])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        zm = (prof[k][1] + prof[k + 1][1]) / 2
        mi = mat_of(zm) if mat_of else 0
        for i in range(seg):
            j = (i + 1) % seg
            if len(a) == 1:
                f = bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                f = bm.faces.new((a[i], a[j], b[0]))
            else:
                f = bm.faces.new((a[i], a[j], b[j], b[i]))
            f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return add_obj(name, bm, mats)


def box(name, size, loc, mats, bevel=0.003, seg=3):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0] + loc[0], v.co.y * size[1] + loc[1], v.co.z * size[2] + loc[2]))
    return add_obj(name, bm, mats, bevel, seg)


def torus(name, R, r, z, mats, seg=40, mseg=8):
    bm = bmesh.new(); V = []
    for i in range(seg):
        a = 2 * math.pi * i / seg; row = []
        for j in range(mseg):
            b = 2 * math.pi * j / mseg
            rr = R + r * math.cos(b)
            row.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z + r * math.sin(b))))
        V.append(row)
    for i in range(seg):
        for j in range(mseg):
            bm.faces.new((V[i][j], V[(i + 1) % seg][j], V[(i + 1) % seg][(j + 1) % mseg], V[i][(j + 1) % mseg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return add_obj(name, bm, mats)


def text_bm(txt, size, depth):
    """Text as a bmesh in the XY plane, centered on x/y, z in [-depth, depth]."""
    cu = bpy.data.curves.new("txt", 'FONT'); cu.body = txt
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = size; cu.extrude = depth; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    cu.resolution_u = 3
    ob = bpy.data.objects.new("txt", cu); scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bm = bmesh.new(); bm.from_mesh(me)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    return bm


def hex_bm(rad, depth):
    bm = bmesh.new()
    vs = [bm.verts.new((rad * math.cos(math.pi / 6 + k * math.pi / 3), rad * math.sin(math.pi / 6 + k * math.pi / 3), -depth))
          for k in range(6)]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z = depth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def wrap(bm, R, zc, depth, xoff=0.0):
    """Wrap a flat XY bmesh (z in [-depth, depth]) onto a cylinder of radius R, facing -Y, centered at height zc."""
    for v in bm.verts:
        x, y, z = v.co
        r = R + (z + depth) * 0.5 - depth * 0.15   # slightly sunk so it never floats
        a = (x + xoff) / R
        v.co = Vector((r * math.sin(a), -r * math.cos(a), zc + y))
    return bm


def flat_front(bm, yface, zc, xc=0.0):
    """Put a flat XY bmesh on a face at y = yface (facing -Y)."""
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((xc + x, yface - z, zc + y))
    return bm


def flat_back(bm, yface, zc):
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((-x, yface + z, zc + y))
    return bm


# ------------------------------------------------------------------ items
DESC = {}


def build_mead():
    glass = mat("AmberGlass", (0.13, 0.042, 0.006), rough=0.07)
    kraft = mat("Label", (0.80, 0.60, 0.30), rough=0.85)
    brown = mat("LabelBrown", (0.11, 0.045, 0.015), rough=0.7)
    gold = mat("Gold", (0.95, 0.62, 0.16), rough=0.3, metal=0.9)
    wax = mat("Wax", (0.20, 0.014, 0.012), rough=0.35)
    twine = mat("Twine", (0.36, 0.25, 0.12), rough=0.95)
    R = 0.038
    lathe("Bottle", [(0, 0.004), (0.02, 0.0025), (0.031, 0.0), (0.0365, 0.003), (R, 0.012), (R, 0.168),
                     (0.0365, 0.182), (0.031, 0.197), (0.022, 0.21), (0.0145, 0.222), (0.0135, 0.232),
                     (0.0135, 0.246), (0.0152, 0.248), (0.0152, 0.253), (0.0125, 0.255), (0, 0.255)], glass, seg=56)
    # label: kraft sleeve with dark bands
    LZ0, LZ1 = 0.04, 0.142
    lathe("Label", [(R + 0.0004, LZ0), (R + 0.0004, LZ1)], [kraft], seg=56)
    for z in (LZ0 + 0.004, LZ1 - 0.004):
        lathe("Band", [(R + 0.0007, z - 0.0035), (R + 0.0007, z + 0.0035)], [brown], seg=56)
    lathe("ShoulderFoil", [(0.0364, 0.1832), (0.0314, 0.1968), (0.0316, 0.1972)], [gold], seg=56)
    # wax-dipped top with a little lip
    lathe("Wax", [(0, 0.2295), (0.0148, 0.2295), (0.0162, 0.231), (0.0162, 0.252), (0.0168, 0.2555),
                  (0.0160, 0.2595), (0.012, 0.262), (0, 0.2625)], [wax], seg=40)
    torus("Twine1", 0.0142, 0.0011, 0.2255, [twine]); torus("Twine2", 0.0142, 0.0011, 0.2235, [twine])
    # front graphics
    LR = R + 0.0004
    PARTS.append(add_obj("Title", wrap(text_bm("МЕДОВУХА", 0.0125, 0.0006), LR, 0.083, 0.0006), [brown]))
    PARTS.append(add_obj("Sub", wrap(text_bm("НАСТОЯЩАЯ · МЕДОВАЯ", 0.0052, 0.0004), LR, 0.067, 0.0004), [brown]))
    hr = 0.0072
    for dx, dz in ((0, 0), (-2 * hr * 0.87, 0), (2 * hr * 0.87, 0), (-hr * 0.87, 1.5 * hr), (hr * 0.87, 1.5 * hr)):
        PARTS.append(add_obj("Hex", wrap(hex_bm(hr * 0.88, 0.0006), LR, 0.106 + dz, 0.0006, xoff=dx), [gold]))
    DESC.update(model="Bottle of mead (honey drink): amber glass bottle, kraft label with honeycomb emblem, wax-sealed top with twine.",
                pivot="bottom center")


def build_chaser():
    alu = mat("Aluminium", (0.80, 0.80, 0.82), rough=0.28, metal=1.0)
    paint = mat("Paint", (0.95, 0.30, 0.02), rough=0.32)
    lime = mat("Lime", (0.40, 0.85, 0.05), rough=0.32)
    white = mat("White", (0.95, 0.95, 0.93), rough=0.35)
    R = 0.033
    lathe("Can", [(0, 0.009), (0.020, 0.0035), (0.0255, 0.0), (0.0285, 0.0008), (0.0315, 0.004), (R, 0.010),
                  (R, 0.100), (0.0305, 0.1075), (0.0270, 0.1125), (0.0276, 0.1150), (0.0270, 0.1162),
                  (0.0255, 0.1150), (0.0252, 0.1105), (0, 0.1105)], [alu, paint], seg=56,
          mat_of=lambda z: 1 if 0.0102 < z < 0.0998 else 0)
    for z0, z1 in ((0.025, 0.031), (0.086, 0.092)):
        lathe("Stripe", [(R + 0.0003, z0), (R + 0.0003, z1)], [lime], seg=56)
    PARTS.append(add_obj("Title", wrap(text_bm("ЗАПИВКА", 0.0118, 0.0005), R, 0.061, 0.0005), [white]))
    PARTS.append(add_obj("Sub", wrap(text_bm("ЛИМОН · АПЕЛЬСИН", 0.0046, 0.0004), R, 0.048, 0.0004), [white]))
    PARTS.append(add_obj("Vol", wrap(text_bm("0,33 Л", 0.0045, 0.0004), R, 0.017, 0.0004), [white]))
    # leaf-ish lime drops on the back
    for k, (dx, dz) in enumerate(((-0.01, 0.07), (0.0, 0.055), (0.01, 0.07))):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, radius=0.0045, segments=16)
        r = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
        for v in [e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)]:
            v.co.z += 0.0008
        for v in bm.verts:
            v.co.z -= 0.0004
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        wrap(bm, R, dz, 0.0004, xoff=dx + math.pi * R)   # opposite side
        PARTS.append(add_obj("Drop", bm, [lime]))
    # pull tab + rivet on the lid
    box("Tab", (0.012, 0.021, 0.0010), (0, 0.004, 0.1112), [alu], bevel=0.0018, seg=3)
    hole = box("TabHole", (0.0066, 0.007, 0.0012), (0, 0.009, 0.1114), [mat("Dark", (0.05, 0.05, 0.05), 0.5)], bevel=0.002)
    lathe("Rivet", [(0, 0.1124), (0.0022, 0.1118), (0.0022, 0.1108)], [alu], seg=16)
    box("Mouth", (0.013, 0.018, 0.0006), (0, -0.011, 0.1106), [alu], bevel=0.003)
    DESC.update(model="Chaser soda can (0.33 l): aluminium can, orange sleeve with lime stripes and title, pull tab.",
                pivot="bottom center")


def build_kit():
    red = mat("RedPlastic", (0.62, 0.025, 0.02), rough=0.38)
    grey = mat("GreyPlastic", (0.12, 0.12, 0.13), rough=0.5)
    white = mat("White", (0.95, 0.95, 0.93), rough=0.4)
    W, D, H = 0.30, 0.10, 0.21
    for s in (-1, 1):   # two shells with a seam between them
        box("Shell", (W, D / 2 - 0.002, H), (0, s * (D / 4 + 0.001), H / 2), [red], bevel=0.016, seg=5)
    box("Seam", (W - 0.008, 0.006, H - 0.008), (0, 0, H / 2), [grey], bevel=0.004)
    # handle on top
    for x in (-0.06, 0.06):
        box("HandlePost", (0.022, 0.03, 0.03), (x, 0, H + 0.008), [grey], bevel=0.005)
    box("HandleBar", (0.15, 0.026, 0.016), (0, 0, H + 0.03), [grey], bevel=0.007, seg=4)
    # latches
    for x in (-0.11, 0.11):
        box("Latch", (0.03, 0.018, 0.012), (x, 0, H + 0.002), [grey], bevel=0.004)
        box("LatchFront", (0.03, 0.004, 0.032), (x, -0.012, H - 0.012), [grey], bevel=0.0015)
    # side hinges
    for z in (0.05, 0.16):
        box("Hinge", (0.008, 0.02, 0.03), (W / 2 + 0.002, 0, z), [grey], bevel=0.003)
    # white cross on both faces, with a white rounded plate behind it
    for side in (-1, 1):
        yf = side * (D / 2 + 0.0005)
        for sz in ((0.1, 0.032), (0.032, 0.1)):
            bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
            for v in bm.verts:
                v.co = Vector((v.co.x * sz[0], v.co.y * sz[1], v.co.z * 0.006))
            (flat_front if side < 0 else flat_back)(bm, yf, 0.118)
            add_obj("Cross", bm, [white], bevel=0.004, seg=3)
    t = text_bm("АПТЕЧКА", 0.019, 0.0012)
    add_obj("Title", flat_front(t, -(D / 2 + 0.0002), 0.035), [white])
    DESC.update(model="First-aid kit: red hard plastic case with a white cross on both sides, grey handle, latches and hinges.",
                pivot="bottom center")


{"Mead": build_mead, "Chaser": build_chaser, "FirstAidKit": build_kit}[ITEM]()

# ------------------------------------------------------------------ join
bpy.ops.object.select_all(action='DESELECT')
for o in PARTS:
    if o.name in bpy.data.objects:
        o.select_set(True)
bpy.context.view_layer.objects.active = PARTS[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
obj.name = obj.data.name = ITEM


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ------------------------------------------------------------------ bake
scene.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dt in ('OPTIX', 'CUDA', 'HIP'):
        try:
            prefs.compute_device_type = dt; prefs.get_devices()
            if any(d.type == dt for d in prefs.devices):
                break
        except Exception:
            continue
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = 'GPU'
except Exception as e:
    print("GPU setup failed:", e)

bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, scale_to_bounds=False)
bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
bpy.ops.object.mode_set(mode='OBJECT')

bw = bpy.data.worlds.new("BakeWorld"); scene.world = bw
dims = obj.dimensions
bw.light_settings.distance = max(dims) * 0.06
RES = 1024
imgs = {}
for ch, nc in (('Color', False), ('Roughness', True), ('Metalness', True), ('AO', True)):
    im = bpy.data.images.new(f"{ITEM}_{ch}_bake", RES, RES, alpha=False)
    if nc:
        im.colorspace_settings.name = 'Non-Color'
    imgs[ch] = im
mats = [s.material for s in obj.material_slots if s.material]


def target(im):
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.get('BAKE_IMG') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'BAKE_IMG'; n.image = im
        for x in nt.nodes:
            x.select = False
        n.select = True; nt.nodes.active = n


bk = scene.render.bake
bk.margin = 6; bk.margin_type = 'EXTEND'; bk.use_clear = True
target(imgs['AO']); scene.cycles.samples = 32
bpy.ops.object.bake(type='AO')
for ch, inp in (('Color', 'Base Color'), ('Roughness', 'Roughness'), ('Metalness', 'Metallic')):
    saved = []
    for m in mats:
        nt = m.node_tree; b = nt.nodes['BSDF']; out = nt.nodes['Material Output']
        em = nt.nodes.new('ShaderNodeEmission')
        v = b.inputs[inp].default_value
        em.inputs['Color'].default_value = tuple(v) if hasattr(v, '__len__') else (v, v, v, 1)
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        saved.append((nt, b, out, em))
    target(imgs[ch]); scene.cycles.samples = 1
    bpy.ops.object.bake(type='EMIT')
    for nt, b, out, em in saved:
        nt.links.new(b.outputs[0], out.inputs['Surface']); nt.nodes.remove(em)


def arr(im):
    return np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)


col = arr(imgs['Color']); ao = arr(imgs['AO'])[:, :1]
lin = np.where(col[:, :3] <= 0.04045, col[:, :3] / 12.92, ((col[:, :3] + 0.055) / 1.055) ** 2.4)
lin *= 1.0 - 0.45 * (1.0 - np.clip(ao, 0, 1))
srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
col[:, :3] = np.clip(srgb, 0, 1); col[:, 3] = 1.0
imgs['Color'].pixels[:] = col.ravel()

TEX = os.path.join(OUT, "textures"); os.makedirs(TEX, exist_ok=True)
paths = {}
for ch in ('Color', 'Roughness', 'Metalness'):
    p = os.path.join(TEX, f"{ITEM}_{ch}.png")
    im = imgs[ch]; im.filepath_raw = p; im.file_format = 'PNG'; im.save(); paths[ch] = p
for im in imgs.values():
    bpy.data.images.remove(im)
scene.world = None; bpy.data.worlds.remove(bw)

fm = bpy.data.materials.new(f"{ITEM}_Mat"); fm.use_nodes = True
N = fm.node_tree.nodes; L = fm.node_tree.links; b = N['Principled BSDF']


def img(ch, nc):
    n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(paths[ch], check_existing=True)
    if nc:
        n.image.colorspace_settings.name = 'Non-Color'
    return n


L.new(img('Color', False).outputs['Color'], b.inputs['Base Color'])
L.new(img('Roughness', True).outputs['Color'], b.inputs['Roughness'])
L.new(img('Metalness', True).outputs['Color'], b.inputs['Metallic'])
obj.data.materials.clear(); obj.data.materials.append(fm)
obj.data.polygons.foreach_set('material_index', [0] * len(obj.data.polygons)); obj.data.update()

# ------------------------------------------------------------------ export
bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{ITEM}.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')
lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for c in obj.bound_box:
    w = obj.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
meta = dict(DESC)
meta.update({
    "units": "meters (real size). Showcase scales x3.6 like the carbine.",
    "axes": "Blender -Y = front (label), +Z = up. GLB +Y up: glTF = (x, z, -y), front faces glTF +Z.",
    "mesh": f"single mesh '{ITEM}', single material '{ITEM}_Mat' (Color/Roughness/Metalness {RES}px)",
    "triangles": tris(obj),
    "size_m": {"x": round(hi.x - lo.x, 4), "y": round(hi.y - lo.y, 4), "z": round(hi.z - lo.z, 4)},
    "bbox_m": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
})
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=2, ensure_ascii=False)
print(json.dumps(meta, indent=2, ensure_ascii=False))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{ITEM}.blend"))

# ------------------------------------------------------------------ renders
for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = e; break
    except Exception:
        pass
scene.eevee.taa_render_samples = 48
wd = bpy.data.worlds.new("RenderWorld"); wd.use_nodes = True; scene.world = wd
wd.node_tree.nodes['Background'].inputs['Color'].default_value = (0.3, 0.3, 0.3, 1)
wd.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.4
scene.view_settings.view_transform = 'AgX'
scene.render.resolution_x = scene.render.resolution_y = 1200
scene.render.image_settings.file_format = 'PNG'
tp = (lo + hi) / 2; size = (hi - lo).length
cd = bpy.data.cameras.new("Cam"); cd.lens = 85; cd.clip_start = 0.001
cam = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(cam); scene.camera = cam


def aim(ob, t):
    ob.rotation_euler = (t - ob.location).normalized().to_track_quat('-Z', 'Y').to_euler()


Z = Vector((0, 0, 1)); lights = []
s2 = size * size
for nm_, pw, sz in (("Key", 60, 0.6), ("Fill", 18, 0.8), ("Rim", 70, 0.4), ("Top", 15, 1.0)):
    ld = bpy.data.lights.new(nm_, 'AREA'); ld.energy = pw * s2; ld.size = sz * size
    o = bpy.data.objects.new(nm_, ld); scene.collection.objects.link(o); lights.append(o)
hfov = 2 * math.atan(18 / cd.lens)
VIEWS = {"front34": (-0.55, -0.8, 0.35), "back34": (0.6, 0.75, 0.3), "front": (0, -1, 0.08)}
for k, d in VIEWS.items():
    d = Vector(d).normalized()
    cam.location = tp + d * (size * 0.5) / math.tan(hfov / 2); aim(cam, tp)
    r = d.cross(Z).normalized(); key, fill, rim, top = lights
    key.location = tp + (d + 0.9 * r + 0.8 * Z).normalized() * size * 2.0
    fill.location = tp + (d - 1.1 * r + 0.1 * Z).normalized() * size * 2.2
    rim.location = tp + (-d + 0.3 * r + 0.9 * Z).normalized() * size * 1.8
    top.location = tp + Z * size * 2.0
    for l in lights:
        aim(l, tp)
    p = os.path.join(OUT, "preview.png" if k == "front34" else f"render_{k}.png")
    scene.render.filepath = p; bpy.ops.render.render(write_still=True); print("rendered", p)
print("DONE")
