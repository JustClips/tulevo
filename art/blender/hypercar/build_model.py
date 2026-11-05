"""Builds the hypercar (open-top mid-engine two-seater) as separate, rig-ready parts.

  blender --background --python build_model.py [-- --preview]

Parts (all with identity transforms, vertices in car space, see common.py for axes):
  Body, Glass, Interior, Door_L, Door_R, Wheel_FL/FR/RL/RR, Caliper_FL/FR/RL/RR,
  SteeringWheel, Pedal_Gas, Pedal_Brake
Saves OUT/hypercar_model.blend. --preview also renders quick previews to OUT/renders.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

os.makedirs(C.OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
coll = scene.collection

# ------------------------------------------------------------------ materials
MATS = {}


def mat(name, color, metal=0.0, rough=0.5, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.name = 'BSDF'
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*color, 1)
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    MATS[name] = m
    return m


mat("Paint", (0.035, 0.06, 0.13), 0.8, 0.22)  # dark metallic blue
mat("Carbon", (0.022, 0.022, 0.025), 0.1, 0.32)
mat("Black", (0.012, 0.012, 0.013), 0.0, 0.6)
mat("Grille", (0.02, 0.02, 0.022), 0.3, 0.45)
mat("Chrome", (0.80, 0.80, 0.82), 1.0, 0.15)
mat("Alu", (0.55, 0.56, 0.58), 1.0, 0.35)
mat("LampGlass", (0.035, 0.04, 0.05), 0.2, 0.08)
mat("LED", (1.0, 0.98, 0.93), 0.0, 0.2, emit=6.0)
mat("Tail", (0.85, 0.02, 0.015), 0.0, 0.25, emit=3.0)
mat("Leather", (0.035, 0.033, 0.032), 0.0, 0.55)
mat("Alcantara", (0.07, 0.07, 0.072), 0.0, 0.9)
mat("Accent", (0.42, 0.85, 0.06), 0.0, 0.4)
mat("Screen", (0.01, 0.015, 0.02), 0.0, 0.1)
mat("Dial", (0.85, 0.85, 0.85), 0.0, 0.4)
mat("Tire", (0.022, 0.022, 0.022), 0.0, 0.85)
mat("Rim", (0.10, 0.10, 0.11), 0.9, 0.3)
mat("Disc", (0.40, 0.40, 0.41), 1.0, 0.4)
mat("Well", (0.008, 0.008, 0.008), 0.0, 0.9)
mat("Glass", (0.04, 0.05, 0.055), 0.0, 0.02, alpha=0.35)
mat("Plate", (0.85, 0.85, 0.82), 0.0, 0.5)
mat("Stitch", (0.45, 0.45, 0.46), 0.0, 0.6)
mat("Belt", (0.025, 0.025, 0.028), 0.0, 0.75)
mat("Screen2", (0.10, 0.35, 0.55), 0.0, 0.1, emit=2.0)
mat("Soot", (0.006, 0.006, 0.006), 0.2, 0.7)
mat("TailDark", (0.18, 0.005, 0.005), 0.0, 0.15)


def mesh_mat(name, base, holes, scale):
    """Dark grille mesh: a fine checker of metal and holes (baked into the texture)."""
    m = mat(name, base, 0.5, 0.45)
    nt = m.node_tree
    ck = nt.nodes.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = scale
    ck.inputs['Color1'].default_value = (*base, 1)
    ck.inputs['Color2'].default_value = (*holes, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Object'], ck.inputs['Vector'])
    nt.links.new(ck.outputs['Color'], nt.nodes['BSDF'].inputs['Base Color'])


mesh_mat("Mesh", (0.06, 0.06, 0.065), (0.004, 0.004, 0.004), 110.0)


# ------------------------------------------------------------------ helpers
def link(name, bm, m):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if m:
        me.materials.append(MATS[m])
    return ob


def place(ob, loc=(0, 0, 0), rot=(0, 0, 0), matrix=None):
    if matrix is not None:
        ob.matrix_world = matrix
    else:
        ob.location = loc
        ob.rotation_euler = rot
    return ob


def bevel(ob, width, segs=2, angle=None):
    md = ob.modifiers.new("Bevel", 'BEVEL')
    md.width = width
    md.segments = segs
    if angle is not None:
        md.limit_method = 'ANGLE'
        md.angle_limit = math.radians(angle)
    else:
        md.limit_method = 'NONE'
    return ob


def cube(name, size, m, loc=(0, 0, 0), rot=(0, 0, 0), bev=0.0, segs=2, matrix=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    ob = place(link(name, bm, m), loc, rot, matrix)
    if bev:
        bevel(ob, bev, segs)
    return ob


def cyl(name, r, depth, m, loc=(0, 0, 0), rot=(0, 0, 0), segs=24, r2=None, matrix=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=depth)
    return place(link(name, bm, m), loc, rot, matrix)


def sphere(name, scale, m, loc=(0, 0, 0), rot=(0, 0, 0), u=24, v=12, matrix=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    return place(link(name, bm, m), loc, rot, matrix)


def from_pydata(name, verts, faces, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if m:
        me.materials.append(MATS[m])
    return ob


def revolve_x(name, prof, m, segs=48, cap=False):
    """Spin a (x, r) profile around the X axis."""
    verts, faces = [], []
    n = len(prof)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        for x, r in prof:
            verts.append((x, r * math.cos(a), r * math.sin(a)))
    for i in range(segs):
        j = (i + 1) % segs
        for k in range(n - 1):
            faces.append((i * n + k, i * n + k + 1, j * n + k + 1, j * n + k))
    if cap:
        faces.append(tuple(i * n for i in range(segs))[::-1])
        faces.append(tuple(i * n + n - 1 for i in range(segs)))
    return from_pydata(name, verts, faces, m)


def torus(name, R, r, m, segs=40, rsegs=10, arc=(0, 2 * math.pi), closed=True):
    """Ring in the local XY plane, axis = local Z."""
    verts, faces = [], []
    count = segs if closed else segs + 1
    for i in range(count):
        a = arc[0] + (arc[1] - arc[0]) * i / segs
        c = Vector((math.cos(a), math.sin(a), 0))
        for k in range(rsegs):
            b = 2 * math.pi * k / rsegs
            p = c * (R + r * math.cos(b)) + Vector((0, 0, r * math.sin(b)))
            verts.append(p)
    rings = count if closed else count - 1
    for i in range(rings):
        j = (i + 1) % count
        for k in range(rsegs):
            l = (k + 1) % rsegs
            faces.append((i * rsegs + k, j * rsegs + k, j * rsegs + l, i * rsegs + l))
    return from_pydata(name, verts, faces, m)


def tube(name, pts, r, m, segs=10):
    """Round tube along a polyline (open ends capped)."""
    pts = [Vector(p) for p in pts]
    verts, faces = [], []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = up if abs(t.dot(up)) < 0.9 else Vector((1, 0, 0))
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        for k in range(segs):
            ang = 2 * math.pi * k / segs
            verts.append(p + (a * math.cos(ang) + b * math.sin(ang)) * r)
    for i in range(len(pts) - 1):
        for k in range(segs):
            l = (k + 1) % segs
            faces.append((i * segs + k, i * segs + l, (i + 1) * segs + l, (i + 1) * segs + k))
    faces.append(tuple(range(segs))[::-1])
    last = (len(pts) - 1) * segs
    faces.append(tuple(last + k for k in range(segs)))
    return from_pydata(name, verts, faces, m)


def prism_yz(name, poly, x0, x1, m):
    """Extrude a (y, z) polygon along X from x0 to x1."""
    n = len(poly)
    verts = [(x0, y, z) for y, z in poly] + [(x1, y, z) for y, z in poly]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    ob = from_pydata(name, verts, faces, m)
    fix_normals(ob)
    return ob


def prism_xy(name, poly, z0, z1, m):
    """Extrude an (x, y) polygon along Z."""
    n = len(poly)
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    ob = from_pydata(name, verts, faces, m)
    fix_normals(ob)
    return ob


def rounded_rect(x0, x1, y0, y1, r, seg=5):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def apply_transform(ob):
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix()


def join(name, obs):
    obs = [o for o in obs if o]
    for o in obs:
        apply_mods(o)
        apply_transform(o)
    with bpy.context.temp_override(active_object=obs[0], object=obs[0],
                                   selected_objects=obs, selected_editable_objects=obs):
        bpy.ops.object.join()
    ob = obs[0]
    ob.name = name
    ob.data.name = name
    return ob


def boolean(ob, cutter, op='DIFFERENCE'):
    md = ob.modifiers.new("Bool", 'BOOLEAN')
    md.operation = op
    md.object = cutter
    md.solver = 'EXACT'
    try:
        md.material_mode = 'TRANSFER'
    except Exception:
        pass
    apply_mods(ob)
    print('bool', cutter.name, op, len(ob.data.polygons))


def delete(ob):
    bpy.data.objects.remove(ob, do_unlink=True)


def mirror_copy(ob, name):
    """Copy mirrored across X (flips normals back)."""
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    c.data.name = name
    coll.objects.link(c)
    apply_mods(c)
    apply_transform(c)
    c.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    c.data.flip_normals()
    return c


def smooth(ob, angle=35):
    ob.data.shade_smooth()
    try:
        ob.data.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def frame_matrix(origin, normal, forward):
    """Matrix with local Z = normal and local Y = forward projected onto the surface."""
    z = Vector(normal).normalized()
    y = Vector(forward) - z * Vector(forward).dot(z)
    y.normalize()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = origin
    return m


# ------------------------------------------------------------------ body loft
# station: y, zc (centre top), zf (fender crest), xf (crest x), w (half width),
#          zw (height of the widest point), zb (bottom), wb (bottom half width)
KEYS = [
    (-2.36, 0.33, 0.37, 0.48, 0.56, 0.27, 0.17, 0.46),
    (-2.33, 0.42, 0.47, 0.56, 0.76, 0.29, 0.14, 0.62),
    (-2.22, 0.50, 0.58, 0.64, 0.88, 0.34, 0.12, 0.74),
    (-2.00, 0.57, 0.68, 0.70, 0.935, 0.42, 0.11, 0.80),
    (-1.70, 0.62, 0.77, 0.74, 0.952, 0.52, 0.11, 0.80),
    (-1.365, 0.665, 0.815, 0.77, 0.958, 0.58, 0.11, 0.80),
    (-1.05, 0.71, 0.80, 0.77, 0.955, 0.56, 0.11, 0.82),
    (-0.80, 0.745, 0.785, 0.76, 0.945, 0.52, 0.11, 0.84),
    (-0.40, 0.77, 0.765, 0.77, 0.915, 0.47, 0.11, 0.84),
    (0.10, 0.80, 0.785, 0.79, 0.915, 0.46, 0.11, 0.84),
    (0.50, 0.89, 0.86, 0.80, 0.94, 0.50, 0.11, 0.84),
    (0.90, 0.93, 0.925, 0.80, 0.962, 0.55, 0.12, 0.82),
    (1.365, 0.935, 0.955, 0.80, 0.972, 0.60, 0.13, 0.80),
    (1.80, 0.925, 0.945, 0.78, 0.965, 0.60, 0.16, 0.78),
    (2.10, 0.92, 0.93, 0.74, 0.94, 0.58, 0.22, 0.76),
    (2.24, 0.905, 0.905, 0.70, 0.90, 0.57, 0.28, 0.74),
    (2.28, 0.86, 0.86, 0.66, 0.86, 0.56, 0.31, 0.72),
]


def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = 0
        while i < n - 2 and x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2
        h11 = t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


CURVES = [pchip([k[0] for k in KEYS], [k[c] for k in KEYS]) for c in range(1, 8)]


def section(y):
    zc, zf, xf, w, zw, zb, wb = (f(y) for f in CURVES)
    half = [(0, zc), (0.45 * xf, zc + 0.05 * (zf - zc)), (0.80 * xf, zc + 0.55 * (zf - zc)), (xf, zf),
            (xf + 0.55 * (w - xf), zf - 0.30 * (zf - zw)), (w - 0.008, zw + 0.12 * (zf - zw)), (w, zw),
            (w - 0.025, zw - 0.5 * (zw - zb)), (wb, zb + 0.04), (0.6 * wb, zb), (0, zb)]
    return half + [(-x, z) for x, z in reversed(half[1:-1])]


def build_loft():
    y0, y1 = KEYS[0][0], KEYS[-1][0]
    ys = [y0, y0 + 0.012]
    n = 64
    ys += [y0 + (y1 - y0) * i / n for i in range(1, n)]
    ys += [y1 - 0.012, y1]
    verts, faces = [], []
    for y in ys:
        for x, z in section(y):
            verts.append((x, y, z))
    R = len(section(0))
    for i in range(len(ys) - 1):
        for j in range(R):
            k = (j + 1) % R
            faces.append((i * R + j, i * R + k, (i + 1) * R + k, (i + 1) * R + j))
    faces.append(tuple(range(R)))
    last = (len(ys) - 1) * R
    faces.append(tuple(last + j for j in range(R))[::-1])
    ob = from_pydata("Body", verts, faces, "Paint")
    fix_normals(ob)
    md = ob.modifiers.new("Sub", 'SUBSURF')
    md.levels = 2
    md.render_levels = 2
    apply_mods(ob)
    return ob


body = build_loft()
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(body, dg)


def surf(x, y):
    """Body surface straight below (x, y)."""
    loc, nrm, _, _ = bvh.ray_cast(Vector((x, y, 4)), Vector((0, 0, -1)))
    return loc, nrm


def surf_back(x, z):
    """Rear face of the body at (x, z), seen from behind."""
    loc, nrm, _, _ = bvh.ray_cast(Vector((x, 5, z)), Vector((0, -1, 0)))
    return loc, nrm


def surf_side(y, z, s):
    """Side of the body at (y, z) on side s (+1 left, -1 right)."""
    loc, nrm, _, _ = bvh.ray_cast(Vector((s * 3, y, z)), Vector((-s, 0, 0)))
    return loc, nrm


def swept(name, pts, widths, thicks, m, side_ref):
    """Box section swept along a polyline (tapering), e.g. wheel spokes."""
    pts = [Vector(p) for p in pts]
    side_ref = Vector(side_ref)
    verts, faces = [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = (side_ref - t * side_ref.dot(t)).normalized()
        b = t.cross(a).normalized()
        w, h = widths[i] / 2, thicks[i] / 2
        for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            verts.append(p + a * sa * w + b * sb * h)
    n = len(pts)
    for i in range(n - 1):
        for k in range(4):
            l = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + l, (i + 1) * 4 + l, (i + 1) * 4 + k))
    faces.append((3, 2, 1, 0))
    faces.append(tuple((n - 1) * 4 + k for k in range(4)))
    ob = from_pydata(name, verts, faces, m)
    fix_normals(ob)
    return ob


# ------------------------------------------------------------------ cutters
cutters = []
for name, hub in C.WHEELS.items():
    r = 0.392 if name[0] == "F" else 0.40
    s = 1 if hub.x > 0 else -1
    x_in = 0.675 if name[0] == "F" else 0.62  # just inside the tyre, so the hood isn't cut
    c = cyl(f"Arch_{name}", r, 1.4 - x_in, "Well", loc=(s * (x_in + 1.4) / 2, hub.y, hub.z), rot=(0, math.radians(90), 0), segs=48)
    cutters.append(c)

cock = prism_xy("Cockpit", rounded_rect(-0.73, 0.73, -0.80, 0.56, 0.16), 0.27, 2.5, "Alcantara")
foot = cube("Footwell", (1.10, 0.50, 0.30), "Alcantara", loc=(0, -0.85, 0.40), bev=0.04)
cutters += [cock, foot]

for s in (1, -1):
    si = cube(f"SideIntake{s}", (0.4, 0.40, 0.26), "Grille", loc=(s * 1.04, 0.58, 0.43), rot=(math.radians(-8), 0, 0), bev=0.04)
    cutters.append(si)
    fi = cube(f"FrontIntakeSide{s}", (0.30, 0.6, 0.20), "Grille", loc=(s * 0.58, -2.46, 0.275), bev=0.04)
    cutters.append(fi)
cutters.append(cube("FrontIntakeMid", (0.62, 0.6, 0.14), "Grille", loc=(0, -2.47, 0.25), bev=0.04))
# rear: engine bay between the buttresses, plate recess, lower corner intakes
bay = prism_xy("Bay", rounded_rect(-0.27, 0.27, 0.70, 1.98, 0.08), 0.80, 1.6, "Mesh")
cutters.append(bay)
cutters.append(cube("PlateRecess", (0.58, 0.3, 0.15), "Black", loc=(0, 2.40, 0.47), bev=0.02))
for s in (1, -1):
    cutters.append(cube(f"RearIntake{s}", (0.36, 0.4, 0.20), "Mesh", loc=(s * 0.66, 2.42, 0.43), bev=0.035))
    cutters.append(cube(f"RearVent{s}", (0.30, 0.3, 0.05), "Black", loc=(s * 0.62, 2.40, 0.645), bev=0.012))

for c in cutters:
    apply_mods(c)
    fix_normals(c)
for c in cutters:
    boolean(body, c)
    delete(c)

# carbon lower edges
paint_i = body.data.materials.find("Paint")
if body.data.materials.find("Carbon") < 0:
    body.data.materials.append(MATS["Carbon"])
carbon_i = body.data.materials.find("Carbon")
for p in body.data.polygons:
    if p.material_index != paint_i:
        continue
    c = p.center
    if c.z < 0.20:
        p.material_index = carbon_i

# ------------------------------------------------------------------ shut lines
shut_lines = []


def groove(pts, r=0.0045):
    """Dark shut line laid on the paint (a thin strip following the surface)."""
    shut_lines.append(swept("ShutLine", pts, [r] * len(pts), [0.003] * len(pts), "Black", (0, 0, 1)))


lid = [surf(x, y)[0] + Vector((0, 0, 0.0005)) for x, y in rounded_rect(-0.50, 0.50, -2.16, -0.98, 0.14, seg=6)]
groove(lid + [lid[0]])
for s in (1, -1):
    # fender-to-bumper seam running down from the headlight to the wheel arch
    seam = [surf_side(-1.98 + 0.02 * k, 0.62 - 0.035 * k, s)[0] + Vector((s * 0.0005, 0, 0)) for k in range(9)]
    groove(seam)

# ------------------------------------------------------------------ doors
door_poly = [(-0.86, 0.26), (0.20, 0.26), (0.33, 0.48), (0.36, 1.4), (-0.86, 1.4)]
door_poly_gap = [(-0.865, 0.255), (0.205, 0.255), (0.337, 0.48), (0.367, 1.4), (-0.865, 1.4)]
doors = {}
for side, s in (("L", 1), ("R", -1)):
    d = body.copy()
    d.data = body.data.copy()
    d.name = f"Door_{side}"
    coll.objects.link(d)
    x0, x1 = (0.70, 1.3) if s > 0 else (-1.3, -0.70)
    cut = prism_yz("DoorCut", door_poly, x0, x1, "Alcantara")
    boolean(d, cut, 'INTERSECT')
    delete(cut)
    gap = prism_yz("DoorGap", door_poly_gap, x0, x1, "Black")
    boolean(body, gap)
    delete(gap)
    d.data.name = d.name
    doors[side] = d

# ------------------------------------------------------------------ exterior details
details = []   # painted / carbon pieces joined into Body
trim = []      # lights, grilles, exhausts, plate... joined into Trim


def on_surface(loc, nrm, fwd, inset=0.0):
    return frame_matrix(loc - nrm * inset, nrm, fwd)


# ---- headlights: tall teardrop lens with chrome bezel, four LED projectors and a DRL arc
for s in (1, -1):
    loc, nrm = surf(s * 0.665, -2.02)
    m = on_surface(loc, nrm, (s * -0.15, -1, 0), 0.014)
    trim.append(sphere("LensHousing", (0.135, 0.245, 0.048), "Black", matrix=m, u=32, v=12))
    bez = torus("Bezel", 1.0, 0.05, "Alu", segs=40, rsegs=6)
    bez.data.transform(Matrix.Diagonal((0.132, 0.242, 0.15, 1)))
    bez.matrix_world = m @ Matrix.Translation((0, 0, 0.022))
    trim.append(bez)
    for dx in (-0.048, 0.048):
        for dy in (-0.07, 0.07):
            p = m @ Matrix.Translation((dx, dy, 0.02))
            trim.append(cyl("LEDCup", 0.034, 0.03, "Chrome", matrix=p, segs=20))
            trim.append(cyl("LEDRing", 0.026, 0.034, "Black", matrix=p, segs=20))
            trim.append(sphere("LED", (0.018, 0.018, 0.012), "LED", matrix=p @ Matrix.Translation((0, 0, 0.016)), u=12, v=6))
    arc = [m @ Vector((0.11 * math.cos(a), 0.215 * math.sin(a), 0.03)) for a in [math.radians(t) for t in range(200, 341, 14)]]
    trim.append(tube("DRLArc", arc, 0.006, "LED", segs=6))
    trim.append(sphere("LensGlass", (0.13, 0.24, 0.046), "LampGlass", matrix=m @ Matrix.Translation((0, 0, 0.004)), u=32, v=12))
    # daytime light bar + slats inside the outer front intake
    trim.append(cube("DRL", (0.20, 0.015, 0.018), "LED", loc=(s * 0.58, -2.165, 0.31), bev=0.006))
    for z in (0.21, 0.25):
        trim.append(cube("FrontSlat", (0.26, 0.012, 0.010), "Black", loc=(s * 0.58, -2.18, z)))
    # side marker on the front bumper corner
    l2, n2 = surf_side(-2.05, 0.36, s)
    trim.append(cube("Marker", (0.004, 0.06, 0.016), "LED", matrix=on_surface(l2, n2, (0, -1, 0)), bev=0.002))

    # side mirror goes on the door: teardrop housing on a carbon stalk
    stalk = swept("MirrorStalk", [(s * 0.86, -0.72, 0.76), (s * 0.95, -0.71, 0.82), (s * 1.0, -0.69, 0.86)],
                  [0.05, 0.035, 0.03], [0.012, 0.012, 0.012], "Carbon", (0, 1, 0))
    house = sphere("Mirror", (0.11, 0.07, 0.052), "Paint", loc=(s * 1.045, -0.665, 0.885), rot=(0, 0, math.radians(s * 6)), u=32, v=16)
    cap = sphere("MirrorCap", (0.112, 0.045, 0.054), "Carbon", loc=(s * 1.045, -0.69, 0.885), rot=(0, 0, math.radians(s * 6)), u=32, v=16)
    mglass = sphere("MirrorGlass", (0.095, 0.01, 0.042), "Chrome", loc=(s * 1.045, -0.606, 0.885), u=24, v=8)
    side = "L" if s > 0 else "R"

    # door handle: recessed pocket with a flush pull bar near the top rear of the door
    hl, hn = surf_side(0.12, 0.70, s)
    hm = on_surface(hl, hn, (0, 1, 0))
    pocket = sphere("HandlePocket", (0.045, 0.085, 0.024), "Black", matrix=hm, u=24, v=10)
    boolean(doors[side], pocket)
    delete(pocket)
    handle = [cube("Handle", (0.026, 0.13, 0.012), "Alu", matrix=hm @ Matrix.Translation((0, 0, -0.004)), bev=0.005),
              cube("HandleKey", (0.014, 0.014, 0.004), "Black", matrix=hm @ Matrix.Translation((0, -0.05, 0.003)), bev=0.002)]
    # inside of the door: armrest, handle, pull strap, speaker
    ix = s * 0.722
    card = [cube("Armrest", (0.07, 0.42, 0.045), "Leather", loc=(ix - s * 0.03, -0.28, 0.52), bev=0.015),
            cube("InnerHandle", (0.012, 0.09, 0.022), "Alu", loc=(ix - s * 0.01, -0.56, 0.62), bev=0.004),
            cube("PullStrap", (0.008, 0.14, 0.02), "Accent", loc=(ix - s * 0.006, -0.10, 0.63)),
            cyl("Speaker", 0.06, 0.012, "Mesh", loc=(ix - s * 0.006, -0.62, 0.42), rot=(0, math.radians(90), 0), segs=24),
            torus("SpeakerRing", 0.062, 0.005, "Alu", segs=24, rsegs=6)]
    card[-1].matrix_world = Matrix.Translation((ix - s * 0.012, -0.62, 0.42)) @ Matrix.Rotation(math.radians(90), 4, 'Y')
    doors[side] = join(f"Door_{side}", [doors[side], stalk, house, cap, mglass] + handle + card)

    # ---- rear: tall buttresses running from behind the seats to the tail
    details.append(sphere("Buttress", (0.17, 1.06, 0.155), "Paint", loc=(s * 0.41, 1.16, 0.895), rot=(math.radians(-2.5), 0, 0), u=40, v=20))
    details.append(sphere("ButtressFoot", (0.20, 0.9, 0.08), "Paint", loc=(s * 0.43, 1.2, 0.86), u=32, v=12))

    # top-exit exhausts: polished tip, rolled lip, sooty inside, perforated core, heat collar
    ex = Matrix.Translation((s * 0.20, 1.0, 0.975)) @ Matrix.Rotation(math.radians(-14), 4, 'X')
    tip = revolve_x("ExhaustTip", [(-0.2, 0.08), (0.0, 0.08), (0.007, 0.085), (0.016, 0.083), (0.018, 0.073), (0.009, 0.069), (-0.2, 0.069)], "Chrome", segs=32)
    inner = revolve_x("ExhaustIn", [(0.008, 0.069), (-0.06, 0.068), (-0.075, 0.04), (-0.05, 0.034), (-0.05, 0.0)], "Soot", segs=32)
    core = revolve_x("ExhaustCore", [(-0.045, 0.0), (-0.045, 0.032), (-0.004, 0.032), (-0.004, 0.027), (-0.04, 0.027), (-0.04, 0.0)], "Grille", segs=24)
    collar = torus("ExhaustCollar", 0.10, 0.016, "Alu", segs=32, rsegs=8)
    for o in (tip, inner, core):
        o.data.transform(Matrix.Rotation(math.radians(-90), 4, 'Y'))  # axis X -> Z
        o.matrix_world = ex
    collar.matrix_world = ex @ Matrix.Translation((0, 0, -0.09))
    trim += [tip, inner, core, collar]
    trim.append(cyl("HeatShield", 0.125, 0.02, "Alu", matrix=ex @ Matrix.Translation((0, 0, -0.13)), segs=32))

    # taillights: slim angular units on each corner (wedge, rising outward) + thinner strip under
    for (x0, x1, z, h0, h1) in ((0.46, 0.83, 0.80, 0.022, 0.058), (0.56, 0.80, 0.752, 0.012, 0.014)):
        n = 12
        pts, hs = [], []
        for i in range(n + 1):
            t = i / n
            l, nn = surf_back(s * (x0 + (x1 - x0) * t), z + 0.035 * t ** 1.5)
            pts.append(l + nn * 0.002)
            hs.append(h0 + (h1 - h0) * t ** 0.7)
        trim.append(swept("TailHousing", pts, [x + 0.014 for x in hs], [0.014] * len(pts), "TailDark", (0, 0, 1)))
        trim.append(swept("TailLed", [p + Vector((0, 0.005, 0)) for p in pts], hs, [0.01] * len(pts), "Tail", (0, 0, 1)))    # wrap-around end of each taillight
    l, nn = surf_back(s * 0.835, 0.83)
    trim.append(cube("TailWrap", (0.05, 0.024, 0.012), "Tail", matrix=on_surface(l, nn, (0, 0, 1)) @ Matrix.Translation((0, 0, 0.004)), bev=0.004))

    # mesh intakes in the lower corners: bars across them
    for z in (0.38, 0.43, 0.48):
        trim.append(cube("IntakeBar", (0.32, 0.012, 0.01), "Black", loc=(s * 0.66, 2.24, z)))
    # diffuser strakes
    for fx in (0.12, 0.30, 0.48):
        trim.append(cube("Strake", (0.012, 0.22, 0.06), "Carbon", loc=(s * fx, 2.17, 0.34)))

# ---- engine bay between the buttresses (the deck cut leaves a dark mesh floor)
rw = [Vector((-0.25, 0.60, 1.02)), Vector((0.25, 0.60, 1.02)), Vector((0.25, 0.86, 0.89)), Vector((-0.25, 0.86, 0.89))]
rear_glass = from_pydata("RearWindow", rw, [(0, 1, 2, 3)], "Glass")
sol = rear_glass.modifiers.new("Solid", 'SOLIDIFY')
sol.thickness = 0.006
apply_mods(rear_glass)
details.append(tube("RearWindowFrame", rw + [rw[0]], 0.006, "Carbon", segs=6))
details.append(cube("BayBulkhead", (0.54, 0.04, 0.16), "Carbon", loc=(0, 0.62, 0.86), bev=0.01))
# centre comb grille between the exhausts
comb = Matrix.Translation((0, 1.02, 0.95)) @ Matrix.Rotation(math.radians(-8), 4, 'X')
trim.append(cube("CombFrame", (0.23, 0.30, 0.016), "Chrome", matrix=comb @ Matrix.Translation((0, 0, -0.035)), bev=0.006))
for i in range(11):
    x = -0.10 + 0.02 * i
    trim.append(cube("CombSlat", (0.007, 0.28, 0.085), "Chrome", matrix=comb @ Matrix.Translation((x, 0, 0)), bev=0.002))
trim.append(cube("CombBar", (0.22, 0.012, 0.012), "Chrome", matrix=comb @ Matrix.Translation((0, -0.14, 0.03)), bev=0.003))
# heat-mesh panels over the engine around the exhausts
for y in (0.80, 1.35, 1.65):
    trim.append(cube("EnginePanel", (0.50, 0.24, 0.01), "Mesh", loc=(0, y, 0.815)))
trim.append(cube("EngineBar", (0.52, 0.02, 0.02), "Alu", loc=(0, 1.50, 0.83)))

# flush rear spoiler across the tail, Gurney lip, third brake light
foil = [(0, 0), (0.03, 0.014), (0.10, 0.022), (0.18, 0.018), (0.24, 0.006), (0.24, 0.0), (0.16, -0.006), (0.06, -0.008)]
details.append(prism_yz("Spoiler", [(1.97 + y, 0.925 + z) for y, z in foil], -0.74, 0.74, "Paint"))
details.append(cube("Gurney", (1.46, 0.006, 0.016), "Carbon", loc=(0, 2.208, 0.937)))
trim.append(cube("BrakeLight", (0.30, 0.01, 0.012), "Tail", loc=(0, 2.212, 0.930)))
# dark band across the rear under the lights, plate, reverse light
l, nn = surf_back(0, 0.70)
trim.append(cube("RearBand", (1.30, 0.06, 0.01), "Black", matrix=on_surface(l, nn, (0, 0, 1)) @ Matrix.Translation((0, 0, 0.002))))
trim.append(cube("Plate", (0.52, 0.11, 0.006), "Plate", loc=(0, 2.255, 0.47), rot=(math.radians(90), 0, 0), bev=0.008))
trim.append(cube("PlateFrame", (0.54, 0.13, 0.004), "Black", loc=(0, 2.25, 0.47), rot=(math.radians(90), 0, 0), bev=0.01))
trim.append(cube("ReverseLight", (0.14, 0.012, 0.02), "LED", loc=(0, 2.25, 0.33), bev=0.004))
trim.append(cube("FogLight", (0.06, 0.012, 0.02), "Tail", loc=(0.20, 2.25, 0.33), bev=0.004))

# front: splitter and centre intake slat

details.append(cube("Splitter", (1.24, 0.12, 0.02), "Carbon", loc=(0, -2.24, 0.13), bev=0.008))
# fuel filler flap on the front right fender
fl, fn = surf(-0.62, -1.75)
trim.append(cyl("FuelFlap", 0.05, 0.004, "Paint", matrix=on_surface(fl, fn, (0, -1, 0)) @ Matrix.Translation((0, 0, 0.002)), segs=24))
trim.append(torus("FuelGap", 0.05, 0.003, "Black", segs=24, rsegs=4))
trim[-1].matrix_world = on_surface(fl, fn, (0, -1, 0))

# ---- front end: intake blades and vanes, mesh behind every opening, tow hook, splitter end plates
trim.append(cube("MidBlade", (0.60, 0.05, 0.016), "Paint", loc=(0, -2.215, 0.255), bev=0.006))
trim.append(cube("MidMesh", (0.62, 0.01, 0.14), "Mesh", loc=(0, -2.12, 0.25)))
for s in (1, -1):
    trim.append(cube("SideMesh", (0.30, 0.01, 0.20), "Mesh", loc=(s * 0.58, -2.10, 0.275)))
    for k in range(5):
        x = s * (0.46 + 0.06 * k)
        trim.append(cube("Vane", (0.008, 0.10, 0.17), "Carbon", loc=(x, -2.17, 0.27), rot=(0, 0, math.radians(s * 12))))
    trim.append(cube("SplitterPlate", (0.012, 0.16, 0.06), "Carbon", loc=(s * 0.62, -2.24, 0.15), bev=0.004))
    # canard winglet on the bumper corner
    l, n = surf_side(-2.15, 0.30, s)
    trim.append(cube("Canard", (0.004, 0.10, 0.06), "Carbon", matrix=on_surface(l, n, (0, -1, 0.25)) @ Matrix.Translation((0, 0, 0.015)) @ Matrix.Rotation(math.radians(90), 4, 'Y'), bev=0.002))
trim.append(cube("TowCover", (0.05, 0.006, 0.035), "Paint", loc=(0.30, -2.20, 0.34), bev=0.006))
# windscreen wiper (parked at the base) and washer jets
wl, wn = surf(0.10, -0.86)
trim.append(swept("WiperArm", [(0.55, -0.83, wl.z + 0.02), (0.10, -0.86, wl.z + 0.02), (-0.30, -0.84, wl.z + 0.02)], [0.016, 0.014, 0.012], [0.008] * 3, "Black", (0, 0, 1)))
trim.append(swept("WiperBlade", [(0.50, -0.82, wl.z + 0.012), (-0.45, -0.82, wl.z + 0.012)], [0.012, 0.012], [0.012] * 2, "Black", (0, 1, 0)))
for x in (-0.25, 0.25):
    l, n = surf(x, -1.00)
    trim.append(sphere("Jet", (0.008, 0.012, 0.006), "Black", matrix=on_surface(l, n, (0, -1, 0)), u=10, v=6))

# ---- sides: louvres in the side intake, carbon sill blade, rear fender outlet
for s in (1, -1):
    for k in range(4):
        y = 0.44 + 0.085 * k
        l, n = surf_side(y, 0.43, s)
        trim.append(cube("Louvre", (0.10, 0.008, 0.22), "Carbon", loc=(s * 0.89, y, 0.43), rot=(math.radians(-8), 0, math.radians(s * 25))))
    trim.append(cube("IntakeMesh", (0.01, 0.40, 0.24), "Mesh", loc=(s * 0.835, 0.58, 0.43), rot=(math.radians(-8), 0, 0)))
    sill = []
    for i in range(9):
        y = -0.90 + (0.95 + 0.90) * i / 8
        l, n = surf_side(y, 0.20, s)
        sill.append(l + n * 0.004)
    trim.append(swept("SillBlade", sill, [0.07] * 9, [0.02] * 9, "Carbon", (0, 0, 1)))
    l, n = surf_side(1.95, 0.55, s)
    om = on_surface(l, n, (0, 0, 1))
    trim.append(cube("FenderOutlet", (0.16, 0.08, 0.008), "Mesh", matrix=om, bev=0.01))
    trim.append(cube("FenderOutletRim", (0.17, 0.09, 0.004), "Carbon", matrix=om @ Matrix.Translation((0, 0, -0.003)), bev=0.012))

# windscreen frame (A pillars + header)
def ws_point(u, v):
    bx, by = u * 0.70, -0.82 + 0.10 * u * u
    loc, _ = surf(bx, by)
    bz = loc.z - 0.01
    tx, ty, tz = u * 0.60, -0.30 + 0.06 * u * u, 1.12 - 0.03 * u * u
    p = Vector((bx + (tx - bx) * v, by + (ty - by) * v, bz + (tz - bz) * v))
    p.y -= 0.025 * math.sin(math.pi * v) * (1 - u * u)
    return p


NU, NV = 16, 8
gv = [ws_point(-1 + 2 * i / NU, j / NV) for j in range(NV + 1) for i in range(NU + 1)]
gf = [(j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i) for j in range(NV) for i in range(NU)]
glass = from_pydata("Glass", gv, gf, "Glass")
sol = glass.modifiers.new("Solid", 'SOLIDIFY')
sol.thickness = 0.006
apply_mods(glass)

for u in (-1, 1):
    pts = [ws_point(u, j / NV) for j in range(NV + 1)]
    pts = [p + Vector((u * 0.012, 0.004, 0)) for p in pts]
    details.append(tube("APillar", pts, 0.024, "Carbon"))
details.append(tube("Header", [ws_point(-1 + 2 * i / NU, 1.0) + Vector((0, 0.008, 0.008)) for i in range(NU + 1)], 0.026, "Carbon"))

body = join("Body", [body] + details)
trim_ob = join("Trim", trim + shut_lines)
glass = join("Glass", [glass, rear_glass])

# ------------------------------------------------------------------ interior
inner = []


def quilt(origin_m, w, h, rows, mat_="Stitch"):
    """Thin stitched grooves across a seat panel (local XY panel, Z = out)."""
    out = []
    for i in range(1, rows):
        y = -h / 2 + h * i / rows
        out.append(cube("Quilt", (w * 0.86, 0.004, 0.003), mat_, matrix=origin_m @ Matrix.Translation((0, y, 0.001))))
    for x in (-w * 0.32, w * 0.32):
        out.append(cube("Seam", (0.003, h * 0.92, 0.003), mat_, matrix=origin_m @ Matrix.Translation((x, 0, 0.001))))
    return out


for s in (1, -1):
    cx = s * C.DRIVER_X
    # carbon bucket shell
    tilt = math.radians(-18)
    back = Vector((cx, 0.33, 0.29))
    up = Vector((0, math.sin(-tilt), math.cos(-tilt)))
    fwd_n = Vector((0, -math.cos(-tilt), math.sin(-tilt)))  # backrest front normal
    ctr = back + up * 0.34
    inner.append(cube("Shell", (0.52, 0.05, 0.74), "Carbon", loc=ctr + up * 0.0 - fwd_n * 0.05, rot=(tilt, 0, 0), bev=0.04, segs=3))
    for b in (-1, 1):
        inner.append(cube("ShellWing", (0.05, 0.20, 0.62), "Carbon", loc=ctr + Vector((b * 0.25, -0.05, -0.04)), rot=(tilt, 0, math.radians(b * 8)), bev=0.02, segs=2))
        inner.append(cube("ShellSide", (0.04, 0.50, 0.15), "Carbon", loc=(cx + b * 0.245, 0.10, 0.27), bev=0.015))
    # cushion with bolsters and quilting
    inner.append(cube("Cushion", (0.36, 0.46, 0.07), "Leather", loc=(cx, 0.10, 0.25), bev=0.025, segs=3))
    inner += quilt(Matrix.Translation((cx, 0.10, 0.286)), 0.30, 0.40, 6)
    for b in (-1, 1):
        inner.append(cube("Bolster", (0.08, 0.46, 0.12), "Leather", loc=(cx + b * 0.19, 0.10, 0.27), rot=(0, math.radians(-b * 12), 0), bev=0.03, segs=3))
        inner.append(cube("BolsterAccent", (0.012, 0.44, 0.10), "Accent", loc=(cx + b * 0.152, 0.10, 0.27), rot=(0, math.radians(-b * 12), 0)))
    # backrest: centre panel, side wings, integrated headrest with harness slots
    inner.append(cube("Back", (0.34, 0.07, 0.66), "Leather", loc=ctr, rot=(tilt, 0, 0), bev=0.03, segs=3))
    pm = Matrix.Translation(ctr + fwd_n * 0.036) @ Matrix.Rotation(tilt, 4, 'X') @ Matrix.Rotation(math.radians(-90), 4, 'X')
    inner += quilt(pm @ Matrix.Translation((0, 0.06, 0)), 0.28, 0.40, 7)
    for b in (-1, 1):
        inner.append(cube("BackWing", (0.08, 0.13, 0.52), "Leather", loc=ctr + Vector((b * 0.19, -0.03, -0.06)), rot=(tilt, 0, math.radians(-b * 14)), bev=0.03, segs=3))
    for b in (-1, 1):
        inner.append(cube("HarnessSlot", (0.05, 0.10, 0.022), "Black", loc=back + up * 0.56 + Vector((b * 0.09, 0, 0)), rot=(tilt, 0, 0), bev=0.008))
    inner.append(cube("HeadSlot", (0.16, 0.10, 0.06), "Black", loc=back + up * 0.66, rot=(tilt, 0, 0), bev=0.02))
    # 4-point harness: shoulder straps over the backrest, lap straps, buckle
    for b in (-1, 1):
        top = back + up * 0.57 + Vector((b * 0.09, 0, 0)) + fwd_n * 0.05
        mid = back + up * 0.25 + Vector((b * 0.07, 0, 0)) + fwd_n * 0.09
        low = Vector((cx + b * 0.02, 0.0, 0.32))
        inner.append(swept("Strap", [top, mid, low], [0.05, 0.05, 0.05], [0.004] * 3, "Belt", (1, 0, 0)))
        inner.append(swept("LapStrap", [Vector((cx + b * 0.2, 0.22, 0.30)), Vector((cx + b * 0.12, 0.06, 0.32)), low], [0.05] * 3, [0.004] * 3, "Belt", (0, 0, 1)))
    inner.append(cyl("Buckle", 0.035, 0.012, "Alu", loc=(cx, 0.0, 0.33), segs=24))
    inner.append(cyl("BuckleCenter", 0.018, 0.016, "Accent", loc=(cx, 0.0, 0.333), segs=16))
    # seat rails
    for b in (-1, 1):
        inner.append(cube("Rail", (0.02, 0.50, 0.02), "Alu", loc=(cx + b * 0.16, 0.08, 0.285 - 0.01)))
    # door sill kick plate
    inner.append(cube("SillPlate", (0.06, 0.95, 0.012), "Alu", loc=(s * 0.70, -0.25, 0.285)))

# ---- dashboard: leather top with stitching, alu trim, vents, glovebox line, grab handle
inner.append(cube("Dash", (1.44, 0.30, 0.20), "Leather", loc=(0, -0.66, 0.64), bev=0.05, segs=3))
inner.append(cube("DashLower", (1.40, 0.10, 0.16), "Alcantara", loc=(0, -0.52, 0.50), bev=0.03, segs=2))
inner.append(cube("DashTrim", (1.40, 0.016, 0.022), "Alu", loc=(0, -0.508, 0.585)))
inner.append(cube("DashStitch", (1.38, 0.003, 0.003), "Stitch", loc=(0, -0.512, 0.72)))
for s in (1, -1):
    vm = Matrix.Translation((s * 0.64, -0.505, 0.66)) @ Matrix.Rotation(math.radians(90), 4, 'X')
    inner.append(cyl("VentBezel", 0.045, 0.02, "Alu", matrix=vm, segs=28))
    inner.append(cyl("VentHole", 0.037, 0.024, "Black", matrix=vm, segs=28))
    for k in range(-2, 3):
        inner.append(cube("VentVane", (0.07, 0.004, 0.012), "Alu", matrix=vm @ Matrix.Translation((0, k * 0.013, 0.008))))
    inner.append(cyl("VentHub", 0.01, 0.03, "Alu", matrix=vm, segs=12))
for x in (-0.07, 0.07):
    vm = Matrix.Translation((x, -0.505, 0.67)) @ Matrix.Rotation(math.radians(90), 4, 'X')
    inner.append(cube("CentreVent", (0.10, 0.04, 0.02), "Black", matrix=vm, bev=0.006))
    for k in range(-2, 3):
        inner.append(cube("CentreVane", (0.004, 0.035, 0.022), "Alu", matrix=vm @ Matrix.Translation((k * 0.018, 0, 0))))
inner.append(cube("Glovebox", (0.40, 0.004, 0.004), "Black", loc=(-0.38, -0.505, 0.53)))
inner.append(swept("GrabHandle", [(-0.62, -0.52, 0.56), (-0.60, -0.48, 0.60), (-0.15, -0.48, 0.60), (-0.12, -0.52, 0.56)], [0.025] * 4, [0.02] * 4, "Leather", (0, 0, 1)))

# ---- instrument cluster: hood, three dials with tick marks, needles
bin_m = Matrix.Translation((C.DRIVER_X, -0.58, 0.76)) @ Matrix.Rotation(math.radians(90), 4, 'X')
inner.append(cyl("Binnacle", 0.135, 0.17, "Leather", matrix=bin_m, segs=40))
inner.append(torus("BinnacleLip", 0.135, 0.004, "Stitch", segs=40, rsegs=4))
inner[-1].matrix_world = bin_m @ Matrix.Translation((0, 0, 0.083))
for i, dx in enumerate((-0.088, 0.0, 0.088)):
    big = i == 1
    r = 0.056 if big else 0.04
    dm = Matrix.Translation((C.DRIVER_X + dx, -0.497, 0.735 + (0.012 if big else 0))) @ Matrix.Rotation(math.radians(90 - 22), 4, 'X')
    inner.append(cyl("DialRing", r + 0.006, 0.012, "Chrome", matrix=dm, segs=32))
    inner.append(cyl("Dial", r, 0.016, "Screen", matrix=dm, segs=32))
    ticks = 13 if big else 9
    for t in range(ticks):
        a = math.radians(-135 + 270 * t / (ticks - 1))
        tm = dm @ Matrix.Translation((0, 0, 0.0085)) @ Matrix.Rotation(-a, 4, 'Z') @ Matrix.Translation((0, r * 0.82, 0))
        inner.append(cube("Tick", (0.0025, r * (0.16 if t % 2 == 0 else 0.09), 0.001), "Dial" if t < ticks - 3 or not big else "Tail", matrix=tm))
    inner.append(cube("Needle", (0.003, r * 0.75, 0.002), "Accent", matrix=dm @ Matrix.Translation((0, 0, 0.0095)) @ Matrix.Rotation(math.radians(50), 4, 'Z') @ Matrix.Translation((0, r * 0.35, 0))))
    inner.append(cyl("NeedleHub", 0.008, 0.004, "Black", matrix=dm @ Matrix.Translation((0, 0, 0.01)), segs=12))
    if big:
        inner.append(cube("DigitalReadout", (0.04, 0.016, 0.001), "Screen2", matrix=dm @ Matrix.Translation((0, -0.028, 0.009))))

# ---- centre console: rising touch panel with buttons, screen, selector, start knob
a = Vector((0, -0.52, 0.60))
bpt = Vector((0, 0.14, 0.36))
mid = (a + bpt) / 2
ang = math.atan2(a.z - bpt.z, bpt.y - a.y)
cm = Matrix.Translation(mid) @ Matrix.Rotation(ang, 4, 'X')
L = (bpt - a).length
inner.append(cube("Console", (0.25, L, 0.10), "Leather", matrix=cm, bev=0.03, segs=3))
inner.append(cube("ConsoleTop", (0.20, L * 0.92, 0.012), "Screen", matrix=cm @ Matrix.Translation((0, 0, 0.052)), bev=0.004))
inner.append(cube("Touchscreen", (0.16, 0.12, 0.004), "Screen2", matrix=cm @ Matrix.Translation((0, -L * 0.30, 0.059)), bev=0.002))
for row in range(4):
    for col in (-1, 0, 1):
        bm = cm @ Matrix.Translation((col * 0.05, -L * 0.08 + row * 0.045, 0.059))
        inner.append(cube("Button", (0.038, 0.03, 0.006), "Alu" if row % 2 else "Black", matrix=bm, bev=0.003))
        inner.append(cube("ButtonIcon", (0.012, 0.004, 0.001), "LED", matrix=bm @ Matrix.Translation((0, 0, 0.0035))))
for s in (1, -1):
    inner.append(cube("ConsoleRail", (0.012, L, 0.022), "Alu", matrix=cm @ Matrix.Translation((s * 0.128, 0, 0.03))))
inner.append(cube("SelectorBase", (0.10, 0.12, 0.02), "Carbon", loc=(0, 0.02, 0.44), bev=0.008))
inner.append(cube("Selector", (0.04, 0.07, 0.045), "Alu", loc=(0, 0.02, 0.47), rot=(math.radians(-15), 0, 0), bev=0.012))
inner.append(cyl("StartKnob", 0.022, 0.02, "Accent", loc=(-0.10, -0.50, 0.57), rot=(math.radians(68), 0, 0), segs=20))
inner.append(cyl("StartRing", 0.028, 0.012, "Chrome", loc=(-0.10, -0.502, 0.568), rot=(math.radians(68), 0, 0), segs=20))
# tunnel and floor
inner.append(cube("Tunnel", (0.24, 0.90, 0.10), "Carbon", loc=(0, -0.25, 0.32), bev=0.02))
for s in (1, -1):
    inner.append(cube("Mat", (0.40, 0.55, 0.01), "Black", loc=(s * C.DRIVER_X, -0.55, 0.276), bev=0.004))
    inner.append(cube("MatEdge", (0.40, 0.012, 0.012), "Accent", loc=(s * C.DRIVER_X, -0.275, 0.28)))
inner.append(cube("DeadPedal", (0.07, 0.012, 0.13), "Alu", loc=(C.DRIVER_X + 0.17, -0.86, 0.34), rot=(math.radians(-30), 0, 0), bev=0.004))
# steering column with shroud and stalks
col0 = C.STEER_CENTER - C.STEER_AXIS * 0.06
col1 = C.STEER_CENTER - C.STEER_AXIS * 0.30
inner.append(tube("Column", [col1, col0], 0.03, "Black", segs=16))
inner.append(tube("Shroud", [col1, C.STEER_CENTER - C.STEER_AXIS * 0.12], 0.045, "Leather", segs=16))
for b in (-1, 1):
    p0 = C.STEER_CENTER - C.STEER_AXIS * 0.13 + Vector((b * 0.04, 0, 0))
    inner.append(tube("Stalk", [p0, p0 + Vector((b * 0.10, 0.01, -0.01))], 0.006, "Black", segs=8))
# rear-view mirror hanging from the windscreen header
inner.append(tube("MirrorArm", [(0, -0.33, 1.10), (0, -0.30, 1.04)], 0.007, "Black", segs=8))
inner.append(cube("RearMirror", (0.20, 0.025, 0.055), "Black", loc=(0, -0.29, 1.02), bev=0.012))
inner.append(cube("RearMirrorGlass", (0.19, 0.003, 0.045), "Chrome", loc=(0, -0.276, 1.02), bev=0.004))
# roll hoop pads behind the headrests
for s in (1, -1):
    inner.append(cube("HoopPad", (0.20, 0.05, 0.12), "Alcantara", loc=(s * C.DRIVER_X, 0.58, 0.96), rot=(math.radians(-18), 0, 0), bev=0.02))
interior = join("Interior", inner)

# ------------------------------------------------------------------ steering wheel
# local frame: wheel plane = XY, +Z toward the driver, -Y = up (turned below)
sw = []
rim = []
for i in range(65):
    a = 2 * math.pi * i / 64
    x, y = 0.175 * math.cos(a), 0.175 * math.sin(a)
    if y > 0.14:  # flat bottom (local +Y is down)
        y = 0.14 + (y - 0.14) * 0.15
    rim.append(Vector((x, y, 0)))
sw.append(tube("Rim", rim, 0.019, "Leather", segs=12))
for side in (-1, 1):  # thicker grips at 9 and 3
    g = [Vector((side * 0.175 * math.cos(math.radians(t)), 0.175 * math.sin(math.radians(t)), 0)) for t in range(-28, 29, 4)]
    sw.append(tube("Grip", g, 0.022, "Alcantara", segs=12))
top = [Vector((0.176 * math.cos(math.radians(t)), 0.176 * math.sin(math.radians(t)), 0)) for t in range(262, 279, 2)]
sw.append(tube("TopMark", top, 0.0205, "Accent", segs=12))
for ang in (0, 180, 90):
    a = math.radians(ang)
    d = Vector((math.cos(a), math.sin(a), 0))
    pts = [d * 0.05 + Vector((0, 0, -0.03)), d * 0.11 + Vector((0, 0, -0.015)), d * 0.165]
    sw.append(swept("Spoke", pts, [0.05, 0.04, 0.032], [0.02, 0.016, 0.016], "Leather", (0, 0, 1)))
    sw.append(swept("SpokeTrim", [p + Vector((0, 0, 0.009)) for p in pts[:2]], [0.03, 0.022], [0.003, 0.003], "Alu", (0, 0, 1)))
# buttons on the side spokes and the mode rotary at lower right
for side in (-1, 1):
    for k in range(3):
        sw.append(cube("WheelButton", (0.014, 0.012, 0.006), "Black", loc=(side * (0.075 + 0.02 * k), -0.018, -0.002), bev=0.002))
sw.append(cyl("ModeDial", 0.02, 0.014, "Accent", loc=(0.095, 0.075, -0.005), segs=20))
sw.append(cyl("ModeDialRing", 0.024, 0.008, "Chrome", loc=(0.095, 0.075, -0.01), segs=20))
sw.append(cyl("Hub", 0.06, 0.05, "Leather", loc=(0, 0, -0.025), segs=32))
sw.append(cyl("HubPad", 0.052, 0.008, "Black", loc=(0, 0, 0.002), segs=32))
sw.append(cyl("HubRing", 0.064, 0.012, "Chrome", loc=(0, 0, -0.04), segs=32))
for side in (-1, 1):
    sw.append(cube("Paddle", (0.11, 0.045, 0.006), "Alu", loc=(side * 0.15, -0.02, -0.06), rot=(0, 0, math.radians(side * 20)), bev=0.003))
    sw.append(cube("PaddleMark", (0.05, 0.008, 0.002), "Accent", loc=(side * 0.16, -0.02, -0.056), rot=(0, 0, math.radians(side * 20))))
steer = join("SteeringWheel", sw)
steer.data.transform(Matrix.Translation(C.STEER_CENTER) @ Matrix.Rotation(math.radians(-(90 - C.STEER_TILT)), 4, 'X') @ Matrix.Rotation(math.pi, 4, 'Z'))

# ------------------------------------------------------------------ pedals (hang from a pivot, pads face the driver)
def pedal(name, x, w, h):
    piv = Vector((x, C.PEDAL_PIVOT_Y, C.PEDAL_PIVOT_Z))
    pad = Vector((x, C.PEDAL_PIVOT_Y + 0.07, C.PEDAL_PIVOT_Z - 0.17))
    parts = [tube("Arm", [piv, piv + Vector((0, 0.02, -0.08)), pad + Vector((0, -0.012, 0))], 0.008, "Black", segs=8)]
    parts.append(cyl("Pivot", 0.012, 0.04, "Alu", loc=piv, rot=(0, math.radians(90), 0), segs=12))
    parts.append(cube("Pad", (w, 0.012, h), "Alu", loc=pad, rot=(math.radians(-30), 0, 0), bev=0.004))
    return join(name, parts)


pedal("Pedal_Gas", C.PEDAL_GAS_X, 0.055, 0.14)
pedal("Pedal_Brake", C.PEDAL_BRAKE_X, 0.09, 0.08)


# ------------------------------------------------------------------ wheels
def build_wheel(name, width):
    """Left-side wheel around the X axis (outer face +X): low-profile tyre with tread grooves and
    sidewall ribs, deep-dish rim with five twin spokes, centre-lock nut, drilled disc."""
    W = width
    R = C.WHEEL_R
    rr = 0.258  # rim radius (20")
    h = W / 2
    # tyre: bead, sidewall with rim protector rib, shoulder, tread with four grooves
    prof = [(-h + 0.012, rr - 0.004), (-h - 0.002, rr + 0.012), (-h - 0.008, rr + 0.03), (-h - 0.006, rr + 0.045),
            (-h - 0.002, R - 0.045), (-h + 0.006, R - 0.018), (-h + 0.022, R - 0.004), (-h + 0.04, R)]
    grooves = [-0.30, -0.10, 0.10, 0.30]
    for gx in grooves:
        x = gx * W
        prof += [(x - 0.008, R), (x - 0.006, R - 0.009), (x + 0.006, R - 0.009), (x + 0.008, R)]
    prof += [(h - 0.04, R), (h - 0.022, R - 0.004), (h - 0.006, R - 0.018), (h + 0.002, R - 0.045),
             (h + 0.006, rr + 0.045), (h + 0.008, rr + 0.03), (h + 0.002, rr + 0.012), (h - 0.012, rr - 0.004)]
    parts = [revolve_x("Tire", prof, "Tire", segs=64)]
    # lateral tread sipes across the shoulders
    for i in range(48):
        a = 2 * math.pi * i / 48
        for sx in (-1, 1):
            c = Vector((sx * (h - 0.05), (R - 0.002) * math.cos(a), (R - 0.002) * math.sin(a)))
            m = frame_matrix(c, Vector((0, math.cos(a), math.sin(a))), Vector((1, 0, 0)))
            parts.append(cube("Sipe", (0.004, 0.05, 0.006), "Soot", matrix=m))

    # rim: inner barrel, stepped outer lip, polished edge
    parts.append(revolve_x("Barrel", [(h - 0.02, rr), (h - 0.035, rr - 0.012), (-h + 0.02, rr - 0.012), (-h + 0.012, rr - 0.002)], "Rim", segs=64))
    parts.append(revolve_x("Lip", [(h - 0.035, rr - 0.012), (h - 0.03, rr - 0.03), (h - 0.012, rr - 0.03), (h - 0.006, rr - 0.012), (h - 0.008, rr + 0.004)], "Alu", segs=64))
    face_x = h - 0.034
    hub_x = h - 0.095  # deep dish: the centre sits well inside the lip
    for i in range(5):
        a = 2 * math.pi * i / 5
        for off in (-0.13, 0.13):
            aa = a + off
            pts = []
            for t in (0.0, 0.35, 0.7, 1.0):
                r = 0.072 + (rr - 0.03 - 0.072) * t
                ang = a + off * t ** 0.8
                x = hub_x + (face_x - hub_x) * (1 - (1 - t) ** 2)  # concave curve outward
                pts.append((x, r * math.cos(ang), r * math.sin(ang)))
            parts.append(swept("Spoke", pts, [0.036, 0.030, 0.024, 0.022], [0.034, 0.026, 0.022, 0.02], "Rim", (1, 0, 0)))
            # machined face strip on each spoke
            face = [(p[0] + 0.012, p[1], p[2]) for p in pts]
            parts.append(swept("SpokeFace", face, [0.02, 0.016, 0.012, 0.01], [0.004] * 4, "Alu", (0, math.cos(aa + math.pi / 2), math.sin(aa + math.pi / 2))))
        # window web between the twin spokes near the hub
        wm = frame_matrix(Vector((hub_x + 0.012, 0.10 * math.cos(a), 0.10 * math.sin(a))), Vector((1, 0, 0)), Vector((0, math.cos(a), math.sin(a))))
        parts.append(cube("Web", (0.05, 0.05, 0.016), "Rim", matrix=wm, bev=0.006))
    # centre: hub flange, centre-lock nut (coloured), polished cap with pin
    rx = Matrix.Rotation(math.radians(90), 4, 'Y')
    parts.append(cyl("Flange", 0.085, 0.03, "Rim", matrix=Matrix.Translation((hub_x, 0, 0)) @ rx, segs=40))
    parts.append(cyl("Nut", 0.048, 0.035, "Accent", matrix=Matrix.Translation((hub_x + 0.03, 0, 0)) @ rx, segs=6))
    parts.append(cyl("NutCap", 0.03, 0.02, "Chrome", matrix=Matrix.Translation((hub_x + 0.05, 0, 0)) @ rx, segs=24, r2=0.022))
    parts.append(cyl("Pin", 0.006, 0.03, "Black", matrix=Matrix.Translation((hub_x + 0.055, 0, 0.0)) @ rx, segs=8))
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 5
        parts.append(cyl("Bolt", 0.009, 0.012, "Chrome", matrix=Matrix.Translation((hub_x + 0.016, 0.068 * math.cos(a), 0.068 * math.sin(a))) @ rx, segs=8))
    # brake: vented disc with cross-drilling, bell with bolts
    parts.append(revolve_x("Disc", [(-0.03, 0.115), (-0.03, 0.205), (0.0, 0.205), (0.0, 0.115), (-0.03, 0.115)], "Disc", segs=64, cap=False))
    parts.append(revolve_x("Vanes", [(-0.022, 0.12), (-0.022, 0.2), (-0.008, 0.2), (-0.008, 0.12)], "Soot", segs=64))
    for ring, rad in enumerate((0.135, 0.16, 0.185)):
        for i in range(18):
            a = 2 * math.pi * (i + ring / 3) / 18
            parts.append(cyl("Hole", 0.0055, 0.032, "Soot", matrix=Matrix.Translation((-0.015, rad * math.cos(a), rad * math.sin(a))) @ rx, segs=6))
    parts.append(cyl("Bell", 0.11, 0.06, "Black", matrix=Matrix.Translation((0.02, 0, 0)) @ rx, segs=32))
    for i in range(10):
        a = 2 * math.pi * i / 10
        parts.append(cyl("BellBolt", 0.008, 0.07, "Chrome", matrix=Matrix.Translation((0.02, 0.12 * math.cos(a), 0.12 * math.sin(a))) @ rx, segs=6))
    return join(name, parts)


def build_caliper(name):
    """Six-piston monobloc caliper over the upper rear of the disc."""
    a0 = math.radians(55)
    parts = []
    for side, xo in ((1, 0.028), (-1, -0.058)):
        pts = []
        for i in range(7):
            a = a0 - math.radians(36) + math.radians(72) * i / 6
            pts.append((xo, 0.19 * math.cos(a), 0.19 * math.sin(a)))
        parts.append(swept("CaliperHalf", pts, [0.07] * 7, [0.035] * 7, "Accent", (0, 0, 1) if False else (0, math.cos(a0), math.sin(a0))))
    for t in (-0.6, 0.0, 0.6):
        a = a0 + math.radians(30) * t
        c = Vector((-0.015, 0.232 * math.cos(a), 0.232 * math.sin(a)))
        parts.append(cube("Bridge", (0.12, 0.02, 0.03), "Accent", matrix=frame_matrix(c, Vector((0, math.cos(a), math.sin(a))), Vector((1, 0, 0))), bev=0.006))
    # bleed nipple + pad pin
    c = Vector((0.05, 0.19 * math.cos(a0), 0.19 * math.sin(a0)))
    parts.append(cyl("PadPin", 0.008, 0.02, "Chrome", loc=c, rot=(0, math.radians(90), 0), segs=8))
    return join(name, parts)


for name, hub in C.WHEELS.items():
    width = C.TIRE_W_FRONT if name[0] == "F" else C.TIRE_W_REAR
    w = build_wheel(f"Wheel_{name}", width)
    cp = build_caliper(f"Caliper_{name}")
    for ob in (w, cp):
        if hub.x < 0:
            ob.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
            ob.data.flip_normals()
        ob.data.transform(Matrix.Translation(hub))

# ------------------------------------------------------------------ split the body into panels
# (one mesh per panel keeps each under Roblox's triangle limit per mesh)
def split_y(ob, y, name):
    """Moves everything of ob behind plane Y = y into a new object."""
    rest = ob.copy()
    rest.data = ob.data.copy()
    rest.name = name
    coll.objects.link(rest)
    for o, clear_inner, clear_outer in ((ob, False, True), (rest, True, False)):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y, 0), plane_no=(0, 1, 0),
                               clear_inner=clear_inner, clear_outer=clear_outer)
        bm.to_mesh(o.data)
        bm.free()
    rest.data.name = name
    return rest


body.name = "Body_Front"
body.data.name = "Body_Front"
mid = split_y(body, -0.86, "Body_Mid")
split_y(mid, 0.62, "Body_Rear")

# ------------------------------------------------------------------ tidy
for ob in list(scene.objects):
    if ob.type == 'MESH':
        apply_mods(ob)
        apply_transform(ob)
        fix = ob.name not in ("Glass",)
        smooth(ob, 40 if ob.name != "Body" else 50)
        ob.data.name = ob.name

for ob in scene.objects:
    if ob.type == 'MESH':
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print(f"{ob.name:16s} {tris:7d} tris")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.OUT, "hypercar_model.blend"))

if "--preview" in sys.argv:
    ren = os.path.join(C.OUT, "renders")
    os.makedirs(ren, exist_ok=True)
    C.setup_studio(scene)
    for k, (loc, tgt, lens) in C.VIEWS.items():
        C.render(scene, os.path.join(ren, f"wip_{k}.png"), loc, tgt, lens, samples=32, res=(1280, 720))
