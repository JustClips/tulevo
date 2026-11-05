"""Plate-carrier armor vest for an R15 UpperTorso (~2 x 1.6 x 1 studs, 1 m = 1 stud).

Builds the mesh, bakes 2048 PBR maps, exports vest.glb + meta.json, renders 4 Eevee views.
Run:  blender --background --factory-startup --python build_vest.py
Coords (Blender): -Y = front (chest), +Z = up, +X = wearer's left. Origin = UpperTorso center.
"""
import bpy, bmesh, os, json, math
import numpy as np
from mathutils import Vector

OUT = r"C:\out\vest2"
TEX = os.path.join(OUT, "textures")
REN = os.path.join(OUT, "renders")
os.makedirs(TEX, exist_ok=True); os.makedirs(REN, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# torso the vest has to fit around (half extents)
TX, TY, TZ = 1.0, 0.5, 0.8


# ------------------------------------------------------------------ materials
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N = m.node_tree.nodes
    b = N['Principled BSDF']; b.name = 'BSDF'
    return m, m.node_tree, b


def fabric_mat(name, col, rough=0.88, weave=90.0, bump=0.35, stripe=False):
    m, nt, b = new_mat(name); N = nt.nodes; L = nt.links
    tc = N.new('ShaderNodeTexCoord')
    # colour variation
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; nz.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    c0 = [c * 0.78 for c in col]; c1 = [min(1, c * 1.15) for c in col]
    ramp.color_ramp.elements[0].color = (*c0, 1); ramp.color_ramp.elements[1].color = (*c1, 1)
    L.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    # weave bump: two crossing wave textures
    w1 = N.new('ShaderNodeTexWave'); w1.inputs['Scale'].default_value = weave; w1.bands_direction = 'X'
    w2 = N.new('ShaderNodeTexWave'); w2.inputs['Scale'].default_value = weave; w2.bands_direction = 'Z'
    for w in (w1, w2):
        w.inputs['Distortion'].default_value = 0.5
        L.new(tc.outputs['Object'], w.inputs['Vector'])
    mx = N.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'
    if stripe:  # webbing: ribs along its length only
        L.new(w2.outputs['Fac'], mx.inputs[0]); mx.inputs[1].default_value = 0.0
    else:
        L.new(w1.outputs['Fac'], mx.inputs[0]); L.new(w2.outputs['Fac'], mx.inputs[1])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.004
    L.new(mx.outputs[0], bp.inputs['Height'])
    L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def plastic_mat(name, col, rough=0.45):
    m, nt, b = new_mat(name)
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    return m


COYOTE = (0.205, 0.148, 0.088)
M_FAB = fabric_mat("Fabric", COYOTE, weave=420, bump=0.08)
M_WEB = fabric_mat("Webbing", (0.17, 0.125, 0.075), rough=0.8, weave=520, bump=0.12, stripe=True)
M_VEL = fabric_mat("Velcro", (0.09, 0.075, 0.055), rough=0.97, weave=700, bump=0.15)
M_PLA = plastic_mat("Plastic", (0.018, 0.018, 0.02))

PARTS = []


def add_obj(name, bm, mat, bevel=None, seg=2):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    if bevel:
        md = ob.modifiers.new("bev", 'BEVEL'); md.width = bevel; md.segments = seg
        md.limit_method = 'ANGLE'; md.angle_limit = math.radians(35); md.harden_normals = False
    PARTS.append(ob)
    return ob


def slab(name, nu, nv, pos, nrm, t, mat, bevel=0.012):
    """Thick sheet: pos(u,v) on the inner surface, offset by nrm(u,v)*t for the outer one."""
    bm = bmesh.new()
    V = {}
    for l in (0, 1):
        for j in range(nv + 1):
            for i in range(nu + 1):
                u, v = i / nu, j / nv
                p = Vector(pos(u, v))
                if l:
                    p = p + Vector(nrm(u, v)).normalized() * t
                V[l, i, j] = bm.verts.new(p)
    F = lambda *k: bm.faces.new([V[x] for x in k])
    for j in range(nv):
        for i in range(nu):
            F((0, i, j), (0, i, j + 1), (0, i + 1, j + 1), (0, i + 1, j))
            F((1, i, j), (1, i + 1, j), (1, i + 1, j + 1), (1, i, j + 1))
    for i in range(nu):
        for j in (0, nv):
            F((0, i, j), (0, i + 1, j), (1, i + 1, j), (1, i, j))
    for j in range(nv):
        for i in (0, nu):
            F((0, i, j), (0, i, j + 1), (1, i, j + 1), (1, i, j))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return add_obj(name, bm, mat, bevel)


def box(name, size, loc, mat, bevel=0.02, seg=2, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    if rot:
        from mathutils import Euler
        bmesh.ops.rotate(bm, verts=bm.verts[:], matrix=Euler(rot).to_matrix())
    for v in bm.verts:
        v.co += Vector(loc)
    return add_obj(name, bm, mat, bevel, seg)


# ------------------------------------------------------------------ main panels
# Long cut: covers UpperTorso and LowerTorso, bottom edge sits just above the belt.
FT, BT = 0.11, 0.10          # front / back panel thickness
FHW, BHW = 1.04, 1.04        # half width at bottom
PZ0, PZ1 = -1.16, 0.56       # panel bottom / top
M_RED = plastic_mat("RedPatch", (0.45, 0.03, 0.025), rough=0.7)
M_DARK = plastic_mat("DarkPatch", (0.04, 0.045, 0.04), rough=0.8)
M_METAL = plastic_mat("Metal", (0.25, 0.25, 0.26), rough=0.35)


def half_w(z, hw):            # shooter's-cut taper above the chest line
    return hw if z < 0.15 else hw - (hw - 0.66) * ((z - 0.15) / (PZ1 + 0.06 - 0.15)) ** 0.8


def front_in(x):              # inner surface y of the front panel (bulges forward in the middle)
    s = min(1.0, abs(x) / FHW)
    return -(TY + 0.03) - 0.06 * (1 - s * s)


def back_in(x):
    s = min(1.0, abs(x) / BHW)
    return (TY + 0.03) + 0.035 * (1 - s * s)


def front_out(x):
    return front_in(x) - FT


def back_out(x):
    return back_in(x) + BT


def fpos(u, v):
    z = PZ0 + v * (PZ1 - PZ0)
    x = (2 * u - 1) * half_w(z, FHW)
    return (x, front_in(x), z)


def bpos(u, v):
    z = PZ0 + v * (PZ1 + 0.06 - PZ0)
    x = (2 * u - 1) * half_w(z, BHW)
    return (x, back_in(x), z)


slab("FrontPanel", 14, 12, fpos, lambda u, v: (0, -1, 0), FT, M_FAB, bevel=0.03)
slab("BackPanel", 14, 12, bpos, lambda u, v: (0, 1, 0), BT, M_FAB, bevel=0.03)

# binding tape along the bottom edges
for nm_, side, outf in (("FBind", -1, front_out), ("BBind", 1, back_out)):
    def bindpos(u, v, outf=outf, side=side):
        x = (2 * u - 1) * (FHW - 0.01)
        return (x, outf(x) - side * 0.004, PZ0 - 0.005 + v * 0.05)
    slab(nm_, 12, 1, bindpos, lambda u, v, side=side: (0, side, 0), 0.012, M_WEB, bevel=0.004)

# cummerbund (sides, full torso length)
CZ0, CZ1, CY = -1.12, -0.02, 0.62
for sx in (-1, 1):
    def cpos(u, v, sx=sx):
        y = (2 * u - 1) * CY
        s = y / CY
        return (sx * (TX + 0.03 + 0.03 * (1 - s * s)), y, CZ0 + v * (CZ1 - CZ0))
    slab(f"Cummerbund{sx}", 10, 5, cpos, lambda u, v, sx=sx: (sx, 0, 0), 0.06, M_FAB, bevel=0.015)
    for k, zc in enumerate((-1.0, -0.84, -0.68, -0.52, -0.36, -0.20)):
        def wpos(u, v, sx=sx, zc=zc):
            y = (2 * u - 1) * (CY - 0.08)
            s = y / CY
            return (sx * (TX + 0.09 + 0.03 * (1 - s * s)), y, zc - 0.022 + v * 0.044)
        slab(f"CWeb{sx}_{k}", 6, 1, wpos, lambda u, v, sx=sx: (sx, 0, 0), 0.014, M_WEB, bevel=0.004)
    # buckles + pull tabs where the cummerbund meets the front panel
    for zc in (-0.85, -0.35):
        box(f"CBuckle{sx}", (0.05, 0.14, 0.09), (sx * (TX + 0.11), -0.46, zc), M_PLA, bevel=0.01)

# side pouches: radio with antenna on the left, med pouch with red cross on the right
RX = TX + 0.12
box("RadioPouch", (0.16, 0.30, 0.52), (RX + 0.08, 0.02, -0.62), M_FAB, bevel=0.03)
box("RadioFlap", (0.18, 0.32, 0.08), (RX + 0.08, 0.02, -0.38), M_FAB, bevel=0.02)
box("Radio", (0.11, 0.20, 0.16), (RX + 0.08, 0.02, -0.30), M_PLA, bevel=0.02)
box("RadioKnob", (0.05, 0.05, 0.06), (RX + 0.08, 0.08, -0.19), M_PLA, bevel=0.01)
box("Antenna", (0.03, 0.03, 0.42), (RX + 0.08, -0.04, -0.02), M_PLA, bevel=0.012)
box("MedPouch", (0.17, 0.36, 0.40), (-(RX + 0.085), 0.0, -0.68), M_FAB, bevel=0.035)
box("MedFlap", (0.19, 0.38, 0.09), (-(RX + 0.085), 0.0, -0.49), M_FAB, bevel=0.02)
box("MedHandle", (0.03, 0.14, 0.05), (-(RX + 0.18), 0.0, -0.44), M_RED, bevel=0.01)
box("MedCrossV", (0.02, 0.06, 0.18), (-(RX + 0.175), 0.0, -0.70), M_RED, bevel=0.006)
box("MedCrossH", (0.02, 0.18, 0.06), (-(RX + 0.175), 0.0, -0.70), M_RED, bevel=0.006)

# shoulder straps: boxy arc from front panel top, over the shoulder, to back panel top
SA, SB, SZ, SP = 0.64, 0.43, 0.44, 0.42
for sx in (-1, 1):
    xc, hw = sx * 0.62, 0.15

    def spath(v):
        th = -math.pi / 2 + v * math.pi
        s, c = math.sin(th), math.cos(th)
        return (SA * math.copysign(abs(s) ** SP, s), SZ + SB * abs(c) ** SP, s, c)

    def spos(u, v, xc=xc, hw=hw):
        y, z, s, c = spath(v)
        return (xc + (2 * u - 1) * hw, y, z)

    def snrm(u, v):
        y, z, s, c = spath(v)
        return (0, y / SA ** 2, (z - SZ) / SB ** 2)
    slab(f"Strap{sx}", 3, 13, spos, snrm, 0.06, M_FAB, bevel=0.012)

    def ppos(u, v, xc=xc):
        y, z, s, c = spath(0.28 + v * 0.44)
        return (xc + (2 * u - 1) * 0.17, y, z + 0.045)
    slab(f"Pad{sx}", 2, 6, ppos, (lambda u, v: (0, spath(0.28 + v * 0.44)[0] / SA ** 2,
                                               (spath(0.28 + v * 0.44)[1] - SZ) / SB ** 2)),
         0.045, M_FAB, bevel=0.015)
    box(f"Buckle{sx}", (0.24, 0.04, 0.12), (xc, front_out(xc) - 0.045, 0.50), M_PLA, bevel=0.012)
    box(f"BuckleBar{sx}", (0.18, 0.05, 0.025), (xc, front_out(xc) - 0.06, 0.50), M_METAL, bevel=0.006)

# ------------------------------------------------------------------ front details
for k in range(9):
    zc = -1.02 + k * 0.14
    def mpos(u, v, zc=zc):
        x = (2 * u - 1) * 0.94
        return (x, front_out(x) + 0.004, zc - 0.022 + v * 0.044)
    slab(f"FWeb{k}", 8, 1, mpos, lambda u, v: (0, -1, 0), 0.014, M_WEB, bevel=0.004)

# triple rifle magazine pouches (lower front)
for k, xc in enumerate((-0.42, 0.0, 0.42)):
    w, h, d = 0.36, 0.50, 0.17
    zc = -0.80
    yb = front_out(xc) + 0.01
    box(f"MagPouch{k}", (w, d, h), (xc, yb - d / 2, zc), M_FAB, bevel=0.035, seg=2)
    box(f"MagFlap{k}", (w + 0.03, d + 0.03, 0.14), (xc, yb - d / 2 - 0.006, zc + h / 2 - 0.03), M_FAB, bevel=0.03)
    box(f"MagTab{k}", (0.12, 0.02, 0.09), (xc, yb - d - 0.02, zc + h / 2 - 0.13), M_WEB, bevel=0.008)
    box(f"MagBand{k}", (w + 0.006, d + 0.006, 0.045), (xc, yb - d / 2, zc - 0.10), M_WEB, bevel=0.01)
    box(f"MagBand2_{k}", (w + 0.006, d + 0.006, 0.045), (xc, yb - d / 2, zc + 0.02), M_WEB, bevel=0.01)

# pistol mag / tourniquet pouches on the outer front
for sx in (-1, 1):
    xc = sx * 0.80
    yb = front_out(xc) + 0.01
    box(f"PistolPouch{sx}", (0.16, 0.10, 0.34), (xc, yb - 0.05, -0.78), M_FAB, bevel=0.025)
    box(f"PistolFlap{sx}", (0.18, 0.12, 0.08), (xc, yb - 0.055, -0.62), M_FAB, bevel=0.02)

# admin / map pouch across the stomach with zip and pull
box("AdminPouch", (0.92, 0.09, 0.30), (0.0, front_out(0) - 0.035, -0.30), M_FAB, bevel=0.03, seg=2)
box("AdminZip", (0.86, 0.012, 0.018), (0.0, front_out(0) - 0.083, -0.18), M_PLA, bevel=0.004)
box("AdminPull", (0.03, 0.012, 0.07), (0.38, front_out(0) - 0.088, -0.22), M_PLA, bevel=0.006)
box("AdminFlapLine", (0.88, 0.01, 0.012), (0.0, front_out(0) - 0.082, -0.40), M_WEB, bevel=0.003)

# chest: patch panel with a blank two-tone flag patch and a name tape, small utility pouches
box("PatchPanel", (0.62, 0.02, 0.32), (0.0, front_out(0) + 0.002, 0.08), M_VEL, bevel=0.008)
box("FlagPatch", (0.22, 0.012, 0.13), (-0.14, front_out(0) - 0.012, 0.15), M_DARK, bevel=0.004)
box("FlagStripe", (0.22, 0.014, 0.04), (-0.14, front_out(0) - 0.014, 0.15), M_RED, bevel=0.002)
box("NameTapeF", (0.26, 0.012, 0.08), (0.15, front_out(0) - 0.012, 0.15), M_DARK, bevel=0.004)
box("BloodTape", (0.48, 0.012, 0.07), (0.0, front_out(0) - 0.012, 0.0), M_DARK, bevel=0.004)
for sx in (-1, 1):
    xc = sx * 0.62
    yb = front_out(xc)
    box(f"ChestPouch{sx}", (0.22, 0.10, 0.24), (xc, yb - 0.05, 0.10), M_FAB, bevel=0.025)
    box(f"ChestFlap{sx}", (0.24, 0.12, 0.07), (xc, yb - 0.055, 0.21), M_FAB, bevel=0.02)
    box(f"ChestSnap{sx}", (0.04, 0.02, 0.04), (xc, yb - 0.12, 0.18), M_METAL, bevel=0.008)

# ------------------------------------------------------------------ back details
for k in range(10):
    zc = -1.02 + k * 0.13
    def bwpos(u, v, zc=zc):
        x = (2 * u - 1) * 0.9
        return (x, back_out(x) - 0.004, zc - 0.022 + v * 0.044)
    slab(f"BWeb{k}", 8, 1, bwpos, lambda u, v: (0, 1, 0), 0.014, M_WEB, bevel=0.004)

# hydration / utility carrier with zip, plus two side pouches
by = back_out(0)
box("BackPouch", (0.80, 0.16, 0.78), (0.0, by + 0.075, -0.50), M_FAB, bevel=0.045, seg=2)
box("BackPouchFlap", (0.83, 0.18, 0.12), (0.0, by + 0.08, -0.15), M_FAB, bevel=0.03)
box("BackZip", (0.012, 0.012, 0.66), (0.30, by + 0.158, -0.54), M_PLA, bevel=0.004)
box("BackZipPull", (0.04, 0.012, 0.07), (0.30, by + 0.163, -0.86), M_PLA, bevel=0.006)
box("HoseExit", (0.08, 0.05, 0.06), (-0.30, by + 0.10, -0.06), M_PLA, bevel=0.015)
for sx in (-1, 1):
    box(f"BackSide{sx}", (0.24, 0.12, 0.38), (sx * 0.66, by + 0.055, -0.72), M_FAB, bevel=0.03)
    box(f"BackSideFlap{sx}", (0.26, 0.14, 0.08), (sx * 0.66, by + 0.06, -0.52), M_FAB, bevel=0.02)
box("NameTape", (0.5, 0.02, 0.11), (0.0, by + 0.002, 0.42), M_VEL, bevel=0.006)
box("BackTape", (0.42, 0.012, 0.08), (0.0, by + 0.014, 0.42), M_DARK, bevel=0.004)

# drag handle: a loop of webbing at the top of the back panel
box("DragBar", (0.36, 0.05, 0.055), (0.0, by + 0.09, 0.66), M_WEB, bevel=0.015)
for sx in (-1, 1):
    box(f"DragPost{sx}", (0.05, 0.11, 0.05), (sx * 0.155, by + 0.045, 0.64), M_WEB, bevel=0.012)

# ------------------------------------------------------------------ apply + join
for o in scene.objects:
    o.select_set(o in PARTS)
bpy.context.view_layer.objects.active = PARTS[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.join()
vest = bpy.context.view_layer.objects.active
vest.name = "Vest"; vest.data.name = "Vest"
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


print("TRIANGLES:", tris(vest))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "vest_model.blend"))

# ------------------------------------------------------------------ GPU for baking
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

# ------------------------------------------------------------------ UV + bake
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.002, scale_to_bounds=False)
bpy.ops.uv.pack_islands(rotate=True, margin=0.002)
bpy.ops.object.mode_set(mode='OBJECT')

bw = bpy.data.worlds.new("BakeWorld"); scene.world = bw
bw.light_settings.distance = 0.12
RES = 2048
imgs = {}
for ch, nc in (('Color', False), ('Normal', True), ('Roughness', True), ('Metalness', True), ('AO', True)):
    im = bpy.data.images.new(f"Vest_{ch}_bake", RES, RES, alpha=False)
    if nc:
        im.colorspace_settings.name = 'Non-Color'
    imgs[ch] = im
mats = [s.material for s in vest.material_slots if s.material]


def target(im):
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.get('BAKE_IMG') or nt.nodes.new('ShaderNodeTexImage')
        n.name = 'BAKE_IMG'; n.image = im
        for x in nt.nodes:
            x.select = False
        n.select = True; nt.nodes.active = n


bk = scene.render.bake
bk.margin = 8; bk.margin_type = 'EXTEND'; bk.use_clear = True
target(imgs['Normal']); scene.cycles.samples = 4
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
target(imgs['AO']); scene.cycles.samples = 24
bpy.ops.object.bake(type='AO')
for ch, inp in (('Color', 'Base Color'), ('Roughness', 'Roughness'), ('Metalness', 'Metallic')):
    saved = []
    for m in mats:
        nt = m.node_tree; b = nt.nodes['BSDF']; out = nt.nodes['Material Output']
        em = nt.nodes.new('ShaderNodeEmission')
        i = b.inputs[inp]
        if i.is_linked:
            nt.links.new(i.links[0].from_socket, em.inputs['Color'])
        else:
            v = i.default_value
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
lin *= 1.0 - 0.55 * (1.0 - np.clip(ao, 0, 1))
srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
col[:, :3] = np.clip(srgb, 0, 1); col[:, 3] = 1.0
imgs['Color'].pixels[:] = col.ravel()

paths = {}
for ch in ('Color', 'Normal', 'Roughness', 'Metalness'):
    p = os.path.join(TEX, f"Vest_{ch}.png")
    im = imgs[ch]; im.filepath_raw = p; im.file_format = 'PNG'; im.save()
    paths[ch] = p
for m in mats:
    n = m.node_tree.nodes.get('BAKE_IMG')
    if n:
        m.node_tree.nodes.remove(n)
    m.use_fake_user = True
for im in imgs.values():
    bpy.data.images.remove(im)
scene.world = None; bpy.data.worlds.remove(bw)

# final single baked material
fm = bpy.data.materials.new("Vest_Mat"); fm.use_nodes = True
N = fm.node_tree.nodes; L = fm.node_tree.links; b = N['Principled BSDF']


def img(ch, nc, y):
    n = N.new('ShaderNodeTexImage'); n.location = (-600, y)
    n.image = bpy.data.images.load(paths[ch], check_existing=True)
    if nc:
        n.image.colorspace_settings.name = 'Non-Color'
    return n


L.new(img('Color', False, 300).outputs['Color'], b.inputs['Base Color'])
L.new(img('Roughness', True, 0).outputs['Color'], b.inputs['Roughness'])
L.new(img('Metalness', True, -300).outputs['Color'], b.inputs['Metallic'])
nm = N.new('ShaderNodeNormalMap'); nm.location = (-250, -600)
L.new(img('Normal', True, -600).outputs['Color'], nm.inputs['Color'])
L.new(nm.outputs['Normal'], b.inputs['Normal'])
vest.data.materials.clear(); vest.data.materials.append(fm)
vest.data.polygons.foreach_set('material_index', [0] * len(vest.data.polygons))
vest.data.update()

# ------------------------------------------------------------------ export
for o in scene.objects:
    o.select_set(o == vest)
bpy.context.view_layer.objects.active = vest
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "vest.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')

lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
for c in vest.bound_box:
    w = vest.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
meta = {
    "model": "Long plate carrier armor vest covering UpperTorso + LowerTorso (front/back plate bags, full cummerbund with buckles, radio + med side pouches, 3 rifle mag + 2 pistol pouches, admin pouch, chest pouches, patch panel, hydration carrier, drag handle, MOLLE webbing). Original mesh.",
    "units": "meters (1 m = 1 stud)",
    "fits": "R15 UpperTorso ~2 x 1.6 x 1 studs (X width, Z height, Y depth). Hollow inside: torso box +-1.0 x +-0.5, z -1.2..+0.8 is clear; bottom edge at z -1.16 (just above the belt).",
    "origin": "UpperTorso center - weld with identity offset",
    "axes": "Blender coords: -Y = front (chest), +Z = up, +X = wearer's left. GLB exported +Y up, so glTF = (x, z, -y): front faces glTF +Z. If it imports facing backwards in Studio, rotate 180 deg about Y.",
    "mesh": "single mesh 'Vest', single material 'Vest_Mat'",
    "triangles": {"Vest": tris(vest)},
    "size_m": {"x_width": round(hi.x - lo.x, 4), "y_depth": round(hi.y - lo.y, 4), "z_height": round(hi.z - lo.z, 4)},
    "bbox_m": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
    "textures": {k: os.path.basename(v) for k, v in paths.items()},
    "texture_size": RES,
}
with open(os.path.join(OUT, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print(json.dumps(meta, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "vest.blend"))

# ------------------------------------------------------------------ Eevee review renders
for e in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = e; break
    except Exception:
        pass
scene.eevee.taa_render_samples = 32
wd = bpy.data.worlds.new("RenderWorld"); wd.use_nodes = True; scene.world = wd
wd.node_tree.nodes['Background'].inputs['Color'].default_value = (0.3, 0.3, 0.3, 1)
wd.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
scene.view_settings.view_transform = 'AgX'
scene.render.resolution_x, scene.render.resolution_y = 1400, 1400
scene.render.image_settings.file_format = 'PNG'

target_pt = (lo + hi) / 2; size = (hi - lo).length
cd = bpy.data.cameras.new("Cam"); cd.lens = 85
cam = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(cam); scene.camera = cam


def aim(ob, t):
    ob.rotation_euler = (t - ob.location).normalized().to_track_quat('-Z', 'Y').to_euler()


Z = Vector((0, 0, 1))
lights = []
for nm_, pw, sz in (("Key", 320, 2.5), ("Fill", 90, 3.0), ("Rim", 350, 1.6), ("Top", 80, 3.5)):
    ld = bpy.data.lights.new(nm_, 'AREA'); ld.energy = pw; ld.size = sz
    lo_ = bpy.data.objects.new(nm_, ld); scene.collection.objects.link(lo_); lights.append(lo_)
hfov = 2 * math.atan(18 / cd.lens)
VIEWS = {"front": (0, -1, 0.12), "front34": (-0.62, -0.72, 0.32), "back34": (0.62, 0.72, 0.32), "left": (1, 0, 0.1)}
paths_r = []
for k, d in VIEWS.items():
    d = Vector(d).normalized()
    cam.location = target_pt + d * (size * 0.47) / math.tan(hfov / 2); aim(cam, target_pt)
    r = d.cross(Z).normalized()
    key, fill, rim, top = lights
    key.location = target_pt + (d + 0.9 * r + 0.8 * Z).normalized() * 4.0
    fill.location = target_pt + (d - 1.1 * r + 0.1 * Z).normalized() * 4.5
    rim.location = target_pt + (-d + 0.3 * r + 0.9 * Z).normalized() * 3.5
    top.location = target_pt + Z * 3.5
    for l in lights:
        aim(l, target_pt)
    p = os.path.join(REN, f"vest_{k}.png"); scene.render.filepath = p
    bpy.ops.render.render(write_still=True); paths_r.append(p); print("rendered", p)
print("DONE")