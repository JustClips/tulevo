"""Build the carbine mesh (Body + Magazine + empties) with detail materials.

Run: blender --background --python build_model.py -- [--preview]
Coordinates: meters, -Y = muzzle direction, Z up. Built in "gun space"
(bore axis at z=0) then shifted so the pistol-grip hold point is the origin.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

OUT = common.OUT
ASSETS = os.path.join(OUT, "assets")
R = math.radians

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'

# ---------------------------------------------------------------- materials
def _sock(node, io, name, typ):
    return [s for s in getattr(node, io) if s.name == name and s.type == typ][0]


def make_mat(name, base, rough_rng, metal, texid, scale, bump, wear=None, base_var=(0.8, 1.2)):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N['Principled BSDF']; bsdf.name = 'BSDF'

    def setv(sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            L.new(v, sock)
        else:
            sock.default_value = v

    def maprange(src, a, b, c, d, clamp=True):
        n = N.new('ShaderNodeMapRange'); n.clamp = clamp
        L.new(src, n.inputs['Value'])
        n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
        return n.outputs['Result']

    def mix(typ, fac, a, b, blend='MIX'):
        n = N.new('ShaderNodeMix'); n.data_type = typ
        if typ == 'RGBA':
            n.blend_type = blend
        st = 'RGBA' if typ == 'RGBA' else 'VALUE'
        setv(_sock(n, 'inputs', 'Factor', 'VALUE'), fac)
        setv(_sock(n, 'inputs', 'A', st), a)
        setv(_sock(n, 'inputs', 'B', st), b)
        return _sock(n, 'outputs', 'Result', st)

    def math_(op, a, b):
        n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = True
        setv(n.inputs[0], a); setv(n.inputs[1], b)
        return n.outputs[0]

    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale,) * 3
    L.new(tc.outputs['Object'], mp.inputs['Vector'])

    def tex(suffix, noncolor):
        n = N.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(os.path.join(ASSETS, texid, f"{texid}_1K-JPG_{suffix}.jpg"), check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = 'Non-Color'
        n.projection = 'BOX'; n.projection_blend = 0.3
        L.new(mp.outputs['Vector'], n.inputs['Vector'])
        return n.outputs['Color']

    tcol, trou, tdis = tex('Color', False), tex('Roughness', True), tex('Displacement', True)
    gray = N.new('ShaderNodeRGBToBW'); L.new(tcol, gray.inputs['Color'])
    # large-scale tonal variation so flat faces are not perfectly uniform
    big = N.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 18; big.inputs['Detail'].default_value = 3
    L.new(tc.outputs['Object'], big.inputs['Vector'])
    var = math_('MULTIPLY', maprange(gray.outputs[0], 0, 1, *base_var), maprange(big.outputs['Fac'], 0.3, 0.7, 0.92, 1.08))
    col = mix('RGBA', 1.0, base, var, 'MULTIPLY')
    rough = maprange(trou, 0, 1, *rough_rng)
    metal_s = metal

    bev = N.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = 0.0010; bev.samples = 8
    geo = N.new('ShaderNodeNewGeometry')
    if wear:
        dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        L.new(bev.outputs['Normal'], dot.inputs[0]); L.new(geo.outputs['Normal'], dot.inputs[1])
        edge = maprange(dot.outputs['Value'], wear.get('lo', 0.86), wear.get('hi', 0.995), 1.0, 0.0)
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 160
        nz.inputs['Detail'].default_value = 8; nz.inputs['Roughness'].default_value = 0.65
        L.new(tc.outputs['Object'], nz.inputs['Vector'])
        w = math_('MULTIPLY', edge, maprange(nz.outputs['Fac'], 0.38, 0.62, 0.0, 1.0))
        w = math_('MULTIPLY', w, wear['amount'])
        col = mix('RGBA', w, col, wear['color'])
        rough = mix('FLOAT', w, rough, wear['rough'])
        metal_s = mix('FLOAT', w, metal, wear['metal'])

    bmp = N.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = bump
    bmp.inputs['Distance'].default_value = 0.0004
    L.new(tdis, bmp.inputs['Height']); L.new(bev.outputs['Normal'], bmp.inputs['Normal'])

    setv(bsdf.inputs['Base Color'], col)
    setv(bsdf.inputs['Roughness'], rough)
    setv(bsdf.inputs['Metallic'], metal_s)
    L.new(bmp.outputs['Normal'], bsdf.inputs['Normal'])
    return m


MATS = {
    'Polymer': make_mat('Polymer', (0.055, 0.055, 0.052, 1), (0.55, 0.78), 0.0, 'Plastic011', 9.0, 0.25,
                        wear=dict(amount=0.55, color=(0.15, 0.15, 0.145, 1), rough=0.45, metal=0.0)),
    'MagPoly': make_mat('MagPoly', (0.062, 0.058, 0.050, 1), (0.50, 0.72), 0.0, 'Plastic011', 9.0, 0.25,
                        wear=dict(amount=0.5, color=(0.16, 0.155, 0.145, 1), rough=0.42, metal=0.0)),
    'Metal': make_mat('Metal', (0.045, 0.047, 0.052, 1), (0.38, 0.58), 0.75, 'Metal032', 12.0, 0.15,
                      wear=dict(amount=0.9, color=(0.42, 0.42, 0.43, 1), rough=0.22, metal=1.0, lo=0.88),
                      base_var=(0.85, 1.15)),
    'Rubber': make_mat('Rubber', (0.03, 0.03, 0.03, 1), (0.80, 0.95), 0.0, 'Rubber004', 7.0, 0.5),
}
glass = bpy.data.materials.new('Glass'); glass.use_nodes = True
gb = glass.node_tree.nodes['Principled BSDF']; gb.name = 'BSDF'
gb.inputs['Base Color'].default_value = (0.03, 0.07, 0.08, 1)
gb.inputs['Roughness'].default_value = 0.08; gb.inputs['Metallic'].default_value = 0.6
MATS['Glass'] = glass

# ---------------------------------------------------------------- geometry helpers
PARTS = []      # objects that become "Body"
CUTTERS = []


def finish(name, bm, mat, collect=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    if mat:
        me.materials.append(MATS[mat])
    if collect:
        PARTS.append(ob)
    return ob


def _P(axis, u, v, w):
    return {'X': (w, u, v), 'Y': (u, w, v), 'Z': (u, v, w)}[axis]


def add_prism(bm, pts, axis, a0, a1):
    v0 = [bm.verts.new(_P(axis, u, v, a0)) for u, v in pts]
    v1 = [bm.verts.new(_P(axis, u, v, a1)) for u, v in pts]
    bm.faces.new(v0); bm.faces.new(list(reversed(v1)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))


def prism(name, pts, axis, a0, a1, mat, collect=True):
    bm = bmesh.new(); add_prism(bm, pts, axis, a0, a1)
    return finish(name, bm, mat, collect)


def add_box(bm, c, s, rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(c) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*s, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts'])


def boxes(name, specs, mat, collect=True):
    """specs: list of (center, size[, Euler])"""
    bm = bmesh.new()
    for sp in specs:
        add_box(bm, Vector(sp[0]), sp[1], sp[2] if len(sp) > 2 else None)
    return finish(name, bm, mat, collect)


def add_cyl(bm, c, r, length, axis, segs, r2=None, rot=None):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r, radius2=r if r2 is None else r2, depth=length)
    A = {'Z': Matrix(), 'Y': Matrix.Rotation(R(90), 4, 'X'), 'X': Matrix.Rotation(R(90), 4, 'Y')}[axis]
    if rot:
        A = rot.to_matrix().to_4x4() @ A
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ A, verts=res['verts'])


def cyls(name, specs, mat, collect=True):
    """specs: list of dicts for add_cyl"""
    bm = bmesh.new()
    for sp in specs:
        add_cyl(bm, Vector(sp['c']), sp['r'], sp['len'], sp.get('axis', 'Y'), sp.get('segs', 16), sp.get('r2'), sp.get('rot'))
    return finish(name, bm, mat, collect)


def torus(name, c, major, minor, axis, mat, nmaj=14, nmin=6):
    bm = bmesh.new(); rings = []
    for i in range(nmaj):
        a = 2 * math.pi * i / nmaj
        ring = []
        for j in range(nmin):
            b = 2 * math.pi * j / nmin
            rr = major + minor * math.cos(b)
            p = Vector((rr * math.cos(a), rr * math.sin(a), minor * math.sin(b)))
            ring.append(bm.verts.new(p))
        rings.append(ring)
    for i in range(nmaj):
        for j in range(nmin):
            a, b = rings[i], rings[(i + 1) % nmaj]
            bm.faces.new((a[j], b[j], b[(j + 1) % nmin], a[(j + 1) % nmin]))
    A = {'Z': Matrix(), 'Y': Matrix.Rotation(R(90), 4, 'X'), 'X': Matrix.Rotation(R(90), 4, 'Y')}[axis]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c) @ A, verts=bm.verts)
    return finish(name, bm, mat)


def superellipse(n, p):
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(c) ** (2 / p), c), math.copysign(abs(s) ** (2 / p), s)))
    return out


def loft(name, sections, mat, n=24, p=4.0, collect=True):
    """sections: (center, u, v, w, front, back) -> ring with x in [-w,w] along u, v in [-front, back]."""
    bm = bmesh.new(); shape = superellipse(n, p); rings = []
    for c, u, v, w, f, b in sections:
        rings.append([bm.verts.new(c + u * (sx * w) + v * (sy * (b if sy > 0 else f))) for sx, sy in shape])
    for i in range(len(rings) - 1):
        for k in range(n):
            a, bb = rings[i], rings[i + 1]
            bm.faces.new((a[k], a[(k + 1) % n], bb[(k + 1) % n], bb[k]))
    bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    return finish(name, bm, mat, collect)


def rrect(cx, cz, hw, hh, r, seg=3):
    pts = []
    for (sx, sz, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccz = cx + sx * (hw - r), cz + sz * (hh - r)
        for i in range(seg + 1):
            a = R(a0 + 90 * i / seg)
            pts.append((ccx + r * math.cos(a), ccz + r * math.sin(a)))
    return pts


def cutter(name, build):
    ob = build(name)
    PARTS.remove(ob); CUTTERS.append(ob)
    ob.hide_render = True
    return ob


def boolean(ob, cut_ob):
    m = ob.modifiers.new('Bool', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cut_ob; m.solver = 'EXACT'
    m.use_self = True; m.use_hole_tolerant = True
    if not cut_ob.data.materials:      # cut faces inherit the target's material
        cut_ob.data.materials.append(ob.data.materials[0])


def bevel(ob, width, segs=2, angle=30):
    m = ob.modifiers.new('Bevel', 'BEVEL'); m.width = width; m.segments = segs
    m.limit_method = 'ANGLE'; m.angle_limit = R(angle); m.use_clamp_overlap = True
    m.miter_outer = 'MITER_ARC'


def apply_all(ob):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        for m in list(ob.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)


# ================================================================ PARTS (gun space)
# --- receiver (polymer)
rec = prism('Receiver', [(0.105, 0.040), (-0.215, 0.040), (-0.215, -0.035), (0.088, -0.035), (0.105, -0.020)],
            'X', -0.026, 0.026, 'Polymer')
c_rec = cutter('c_rec', lambda n: boxes(n, [
    ((0.024, -0.055, 0.012), (0.020, 0.060, 0.028)),        # ejection port (right side), 10 mm deep
    ((-0.029, -0.055, 0.012), (0.010, 0.056, 0.024)),       # left side recess panel
    ((0.029, -0.162, 0.010), (0.008, 0.070, 0.030)),        # front side panels
    ((-0.029, -0.162, 0.010), (0.008, 0.070, 0.030)),
    ((0.029, 0.068, 0.012), (0.008, 0.050, 0.024)),         # rear side panels
    ((-0.029, 0.068, 0.012), (0.008, 0.050, 0.024)),
    ((0.0275, -0.010, -0.0045), (0.006, 0.400, 0.0022)),     # upper/lower seam grooves
    ((-0.0275, -0.010, -0.0045), (0.006, 0.400, 0.0022)),
], None))
boolean(rec, c_rec); bevel(rec, 0.0018)

bolt = boxes('Bolt', [((0.0170, -0.055, 0.012), (0.004, 0.058, 0.026)),
                      ((0.0185, -0.055, 0.016), (0.002, 0.050, 0.004)),     # extractor ridge
                      ((0.0185, -0.035, 0.004), (0.002, 0.008, 0.008))], 'Metal')
bevel(bolt, 0.0005, 1)

# --- carry handle / optic rail housing (polymer)
ch = prism('CarryHandle', [(0.088, 0.039), (0.082, 0.084), (-0.172, 0.084), (-0.192, 0.039)], 'X', -0.017, 0.017, 'Polymer')
c_ch = cutter('c_ch', lambda n: prism(n, [(0.064, 0.030), (0.064, 0.070), (-0.146, 0.070), (-0.160, 0.030)], 'X', -0.03, 0.03, None))
boolean(ch, c_ch); bevel(ch, 0.0018)

# --- picatinny rail (metal) + teeth
rail = prism('Rail', [(-0.008, 0.0835), (0.008, 0.0835), (0.0105, 0.0865), (0.0105, 0.0885), (0.0090, 0.0895),
                      (-0.0090, 0.0895), (-0.0105, 0.0885), (-0.0105, 0.0865)], 'Y', 0.078, -0.168, 'Metal')
bevel(rail, 0.0005, 1)
teeth = boxes('RailTeeth', [((0, 0.072 - i * 0.010, 0.0915), (0.0205, 0.0052, 0.0042)) for i in range(24)], 'Metal')
bevel(teeth, 0.0005, 1)

# --- reflex optic on the rail
optic_base = boxes('OpticBase', [((0, -0.044, 0.0975), (0.026, 0.066, 0.008)),
                                 ((0, -0.024, 0.106), (0.026, 0.024, 0.012))], 'Metal')
bevel(optic_base, 0.0008)
knobs = cyls('OpticKnobs', [dict(c=(-0.0165, -0.030, 0.0965), r=0.0045, len=0.008, axis='X', segs=12),
                           dict(c=(-0.0165, -0.060, 0.0965), r=0.0045, len=0.008, axis='X', segs=12),
                           dict(c=(0.0175, -0.024, 0.110), r=0.0062, len=0.008, axis='X', segs=16),
                           dict(c=(0, -0.024, 0.1135), r=0.0045, len=0.005, axis='Z', segs=12)], 'Metal')
bevel(knobs, 0.0006, 1)
hood = prism('OpticHood', rrect(0, 0.1215, 0.0165, 0.0195, 0.006), 'Y', -0.012, -0.078, 'Metal')
c_hood = cutter('c_hood', lambda n: prism(n, rrect(0, 0.1235, 0.0125, 0.0148, 0.0045), 'Y', -0.002, -0.090, None))
boolean(hood, c_hood); bevel(hood, 0.0009)
lens = prism('Lens', rrect(0, 0.1235, 0.0128, 0.0151, 0.0046), 'Y', -0.066, -0.069, 'Glass')

# --- handguard (polymer) with vent pockets
HG = [(-0.020, -0.032), (0.020, -0.032), (0.028, -0.022), (0.028, 0.030), (0.022, 0.038), (-0.022, 0.038), (-0.028, 0.030), (-0.028, -0.022)]
hg = prism('Handguard', HG, 'Y', -0.213, -0.385, 'Polymer')
vents = []
for i in range(4):
    yc = -0.244 - i * 0.034
    for s in (-1, 1):
        vents.append(((s * 0.0295, yc, 0.016), (0.015, 0.024, 0.010)))
        vents.append(((s * 0.0295, yc, -0.008), (0.015, 0.024, 0.010)))
    vents.append(((0, yc, -0.0345), (0.022, 0.024, 0.012)))
    vents.append(((0, yc, 0.0405), (0.020, 0.024, 0.010)))
c_hg = cutter('c_hg', lambda n: boxes(n, vents, None))
boolean(hg, c_hg); bevel(hg, 0.0018)
hg_cap = prism('HandguardCap', [(x * 0.93, z * 0.93 + 0.0005) for x, z in HG], 'Y', -0.384, -0.392, 'Metal')
bevel(hg_cap, 0.0008)
fsight = boxes('FrontSight', [((0, -0.374, 0.0405), (0.016, 0.018, 0.006)),
                              ((0, -0.371, 0.0450), (0.012, 0.022, 0.003)),
                              ((0, -0.381, 0.0490), (0.003, 0.004, 0.006))], 'Metal')
bevel(fsight, 0.0006, 1)

# --- barrel + muzzle device (metal)
barrel = cyls('Barrel', [dict(c=(0, -0.430, 0), r=0.0085, len=0.090, segs=16),
                         dict(c=(0, -0.478, 0), r=0.0108, len=0.006, segs=6)], 'Metal')
bevel(barrel, 0.0007, 2)
fh = cyls('FlashHider', [dict(c=(0, -0.5055, 0), r=0.0112, len=0.049, segs=20)], 'Metal')
def _fh_cut(n):
    bm = bmesh.new()
    add_cyl(bm, Vector((0, -0.520, 0)), 0.0068, 0.040, 'Y', 16)
    for k in range(4):
        add_box(bm, Vector((0, -0.522, 0)), (0.030, 0.030, 0.0032), Euler((0, R(45 * k), 0)))
    return finish(n, bm, None)
c_fh = cutter('c_fh', _fh_cut)
boolean(fh, c_fh); bevel(fh, 0.0005, 1)

# --- magwell (polymer)
mw = boxes('Magwell', [((0, -0.134, -0.052), (0.043, 0.080, 0.044)),
                       ((0, -0.134, -0.0705), (0.047, 0.085, 0.007))], 'Polymer')
c_mw = cutter('c_mw', lambda n: boxes(n, [((0, -0.134, -0.058), (0.0275, 0.0705, 0.050))], None))
boolean(mw, c_mw); bevel(mw, 0.0015)
magrel = boxes('MagRelease', [((0, -0.0885, -0.070), (0.018, 0.009, 0.004)),
                              ((0, -0.0915, -0.060), (0.010, 0.004, 0.020))], 'Metal')
bevel(magrel, 0.0006, 1)

# --- trigger guard (polymer) and trigger (metal)
tg = prism('TriggerGuard', [(-0.093, -0.033), (-0.093, -0.066), (-0.083, -0.0765), (0.056, -0.0765), (0.056, -0.0715),
                            (-0.080, -0.0715), (-0.088, -0.064), (-0.088, -0.033)], 'X', -0.0055, 0.0055, 'Polymer')
bevel(tg, 0.0012)
trig = prism('Trigger', [(-0.038, -0.033), (-0.030, -0.033), (-0.0295, -0.045), (-0.031, -0.056), (-0.035, -0.0635),
                         (-0.041, -0.0675), (-0.042, -0.065), (-0.037, -0.059), (-0.0355, -0.050), (-0.036, -0.040)],
             'X', -0.0028, 0.0028, 'Metal')
bevel(trig, 0.0006, 1)

# --- pistol grip (lofted, finger grooves, polymer)
GTOP = Vector((0, 0.052, -0.030))
GD = Vector((0, math.sin(R(18)), -math.cos(R(18))))
GV = Vector((0, math.cos(R(18)), math.sin(R(18))))     # points to the rear
GU = Vector((1, 0, 0))
gt = [-0.010, 0.0, 0.012, 0.024, 0.036, 0.048, 0.060, 0.072, 0.084, 0.096, 0.103, 0.107]
gw = [0.0135, 0.0140, 0.0145, 0.0148, 0.0150, 0.0150, 0.0150, 0.0150, 0.0149, 0.0147, 0.0142, 0.0125]
gf = [0.019, 0.019, 0.0185, 0.0205, 0.0188, 0.0205, 0.0188, 0.0205, 0.0195, 0.0195, 0.0185, 0.0160]
gb_ = [0.020, 0.021, 0.022, 0.0225, 0.0228, 0.0228, 0.0228, 0.0228, 0.0228, 0.0226, 0.0218, 0.0185]
grip = loft('Grip', [(GTOP + GD * t, GU, GV, w, f, b) for t, w, f, b in zip(gt, gw, gf, gb_)], 'Polymer', n=24, p=3.5)
gripcap = loft('GripCap', [(GTOP + GD * 0.100, GU, GV, 0.0152, 0.0205, 0.0235),
                           (GTOP + GD * 0.110, GU, GV, 0.0150, 0.0200, 0.0230)], 'Polymer', n=24, p=3.5)
bevel(gripcap, 0.0015)

# --- selector, pins, charging handle (metal)
sel = cyls('Selector', [dict(c=(s * 0.0275, 0.028, -0.012), r=0.0065, len=0.003, axis='X', segs=16) for s in (-1, 1)], 'Metal')
bevel(sel, 0.0006, 1)
sel_lev = boxes('SelectorLever', [((s * 0.0290, 0.036, -0.018), (0.003, 0.004, 0.016), Euler((R(-35), 0, 0))) for s in (-1, 1)], 'Metal')
bevel(sel_lev, 0.0006, 1)
pins = cyls('Pins', [dict(c=(0, y, z), r=0.0028, len=0.0535, axis='X', segs=12)
                     for y, z in ((0.093, -0.022), (0.008, -0.026), (-0.203, -0.024), (-0.120, 0.030), (0.045, 0.030))], 'Metal')
bevel(pins, 0.0005, 1)
chg = boxes('ChargingHandle', [((0, 0.050, 0.0445), (0.012, 0.024, 0.009)),
                               ((0.016, 0.055, 0.046), (0.024, 0.008, 0.005), Euler((0, 0, R(12)))),
                               ((0.029, 0.058, 0.048), (0.006, 0.013, 0.011))], 'Metal')
bevel(chg, 0.0007, 1)

# --- folding stock: hinge block, skeleton stock, buttpad, hinge (polymer/metal/rubber)
hinge = prism('HingeBlock', [(0.104, 0.040), (0.124, 0.038), (0.124, -0.028), (0.104, -0.022)], 'X', -0.024, 0.024, 'Polymer')
bevel(hinge, 0.0018)
knuck = cyls('HingeKnuckles', [dict(c=(0.0215, 0.124, 0.020), r=0.0048, len=0.016, axis='Z', segs=14),
                               dict(c=(0.0215, 0.124, -0.012), r=0.0048, len=0.016, axis='Z', segs=14),
                               dict(c=(0.0215, 0.124, 0.004), r=0.0022, len=0.054, axis='Z', segs=10)], 'Metal')
bevel(knuck, 0.0006, 1)
stock = prism('Stock', [(0.122, 0.036), (0.282, 0.044), (0.290, 0.044), (0.290, -0.090), (0.272, -0.090), (0.122, -0.026)],
              'X', -0.0155, 0.0155, 'Polymer')
c_st_win = cutter('c_stw', lambda n: prism(n, [(0.145, 0.0272), (0.266, 0.0332), (0.266, -0.0744), (0.145, -0.0228)], 'X', -0.03, 0.03, None))
boolean(stock, c_st_win); bevel(stock, 0.0025)
pad = prism('Buttpad', [(0.289, 0.047), (0.301, 0.047), (0.301, -0.093), (0.289, -0.093)], 'X', -0.0175, 0.0175, 'Rubber')
c_pad = cutter('c_pad', lambda n: boxes(n, [((0, 0.3015, z), (0.04, 0.006, 0.0035)) for z in (0.032, 0.017, 0.002, -0.013, -0.028, -0.043, -0.058, -0.073)], None))
boolean(pad, c_pad); bevel(pad, 0.0025, 2)

# --- sling points
sl1 = torus('SlingRear', Vector((0, 0.262, -0.095)), 0.0075, 0.0017, 'X', 'Metal')
sl1b = boxes('SlingRearMount', [((0, 0.262, -0.0875), (0.008, 0.012, 0.006))], 'Metal'); bevel(sl1b, 0.0006, 1)
sl2 = torus('SlingFront', Vector((0, -0.372, -0.0405)), 0.0075, 0.0017, 'X', 'Metal')
sl2b = boxes('SlingFrontMount', [((0, -0.372, -0.0335), (0.008, 0.012, 0.006))], 'Metal'); bevel(sl2b, 0.0006, 1)

# ---------------------------------------------------------------- magazine (separate object)
def build_mag():
    R0, A0, L = 0.34, R(4), 0.205
    p0 = Vector((0, -0.133, -0.036))

    def frame(s):
        th = A0 + s / R0
        c = p0 + R0 * Vector((0, math.cos(th) - math.cos(A0), -(math.sin(th) - math.sin(A0))))
        return c, Vector((0, math.cos(th), -math.sin(th)))

    secs = [(0.000, 0.0095, 0.027, 0.029), (0.004, 0.0108, 0.030, 0.032), (0.009, 0.0122, 0.031, 0.033)]
    s = 0.03
    while s < 0.17:
        k = s / L
        f, b = 0.031 + 0.003 * k, 0.033 + 0.001 * k
        secs += [(s - 0.003, 0.0122, f, b), (s - 0.0015, 0.0131, f + 0.0006, b + 0.0006),
                 (s + 0.0015, 0.0131, f + 0.0006, b + 0.0006), (s + 0.003, 0.0122, f, b)]
        s += 0.03
    secs += [(0.188, 0.0122, 0.0340, 0.0340), (0.190, 0.0140, 0.0370, 0.0370), (0.202, 0.0140, 0.0370, 0.0370),
             (0.205, 0.0128, 0.0355, 0.0355)]
    sections = []
    for s, w, f, b in secs:
        c, v = frame(s)
        sections.append((c, Vector((1, 0, 0)), v, w, f, b))
    ob = loft('Magazine', sections, 'MagPoly', n=28, p=5.0, collect=False)
    return ob


mag = build_mag()

# ---------------------------------------------------------------- apply, join, normals
for ob in PARTS:
    apply_all(ob)
for c in CUTTERS:
    bpy.data.objects.remove(c)

body = PARTS[0]
with bpy.context.temp_override(active_object=body, selected_objects=PARTS, selected_editable_objects=PARTS):
    bpy.ops.object.join()
body.name = body.data.name = 'Body'


def smooth_and_weight(ob, angle=50):
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if e.is_manifold:
            e.smooth = e.calc_face_angle(0) < R(angle)
        else:
            e.smooth = False
    bm.to_mesh(me); bm.free()
    m = ob.modifiers.new('WN', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50; m.mode = 'FACE_AREA'
    apply_all(ob)


smooth_and_weight(body)
smooth_and_weight(mag, angle=60)

# shift so the pistol-grip hold point is the origin
GRIP = GTOP + GD * 0.042
for ob in (body, mag):
    ob.data.transform(Matrix.Translation(-GRIP))


def empty(name, p, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None); e.empty_display_type = 'ARROWS'; e.empty_display_size = 0.03
    e.location = Vector(p) - GRIP; e.rotation_euler = Euler(rot)
    scene.collection.objects.link(e); return e


empty('Grip', GRIP, (R(18), 0, 0))
empty('Grip2', (0, -0.300, -0.032))          # left hand under the handguard
empty('Muzzle', (0, -0.530, 0))
empty('Sight', (0, -0.012, 0.1235))
empty('MagWell', (0, -0.133, -0.036))


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


print("TRIS Body", tris(body), "Magazine", tris(mag))
lo, hi = common.mesh_bbox([body, mag])
print("SIZE", tuple(round(x, 4) for x in (hi - lo)))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "carbine_model.blend"))

if "--preview" in sys.argv:
    common.render_views(scene, [body, mag], [(os.path.join(OUT, "renders", "preview_shape.png"), *common.STANDARD_VIEWS["front34"])], samples=64)
