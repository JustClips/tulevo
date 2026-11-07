"""Mesh helpers for the superbike wheel builds (pure bpy + bmesh, runs headless).

Wheel axis = Blender X. Wheel plane = YZ. Bike front = -Y, up = +Z, +X = bike's LEFT side.
Angles in the wheel plane: 0 = rearward (+Y), 90 = up (+Z).
"""
import math
import bmesh
import bpy
from mathutils import Vector


def polar(r, ang):
    return Vector((0.0, r * math.cos(ang), r * math.sin(ang)))


def new_obj(name, me):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def lathe(name, profile, seg=128, closed=True, a0=0.0, a1=2 * math.pi, uv=True, caps=False):
    """Revolve a (x, r) profile around X. closed = profile is a loop.
    Full turn when a1 - a0 == 2pi, else a partial sweep (caps closes the ends)."""
    full = abs((a1 - a0) - 2 * math.pi) < 1e-6
    cols = seg if full else seg + 1
    n = len(profile)
    verts = []
    for i in range(cols):
        a = a0 + (a1 - a0) * i / seg
        for x, r in profile:
            verts.append((x, r * math.cos(a), r * math.sin(a)))
    rows = n if closed else n - 1
    faces, uvs = [], []
    # arc length along the profile for v
    L = [0.0]
    for j in range(1, n + (1 if closed else 0)):
        p, q = profile[j - 1], profile[j % n]
        L.append(L[-1] + math.dist(p, q))
    tot = L[-1] or 1.0
    for i in range(seg):
        i2 = (i + 1) % cols
        for j in range(rows):
            j2 = (j + 1) % n
            faces.append((i * n + j, i2 * n + j, i2 * n + j2, i * n + j2))
            u0, u1 = i / seg, (i + 1) / seg
            v0, v1 = L[j] / tot, L[j + 1] / tot
            uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
    if caps and not full and closed:
        faces.append(tuple(range(n))[::-1])
        faces.append(tuple((cols - 1) * n + j for j in range(n)))
        uvs.append(tuple((0, 0) for _ in range(n)))
        uvs.append(tuple((0, 0) for _ in range(n)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if uv:
        lay = me.uv_layers.new(name="UVMap")
        k = 0
        for f, fu in zip(me.polygons, uvs):
            for li, u in zip(f.loop_indices, fu):
                lay.data[li].uv = u
            k += 1
    me.update()
    ob = new_obj(name, me)
    fix_normals(ob)
    return ob


def fix_normals(ob, outward_from=None):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def flip_if_inward(ob, axis_center=True):
    """For open surfaces of revolution: make normals point away from the X axis."""
    me = ob.data
    s = 0.0
    for p in me.polygons:
        c = p.center
        radial = Vector((0, c.y, c.z))
        s += p.normal.dot(radial.normalized()) * p.area
    if s < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()


def loft(name, sections, cap=True):
    """sections: list of lists of Vector (same count, closed loops). Builds a tube, caps ends."""
    n = len(sections[0])
    verts = [v for s in sections for v in s]
    faces = []
    for i in range(len(sections) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((i * n + j, i * n + j2, (i + 1) * n + j2, (i + 1) * n + j))
    if cap:
        faces.append(tuple(range(n))[::-1])
        last = (len(sections) - 1) * n
        faces.append(tuple(last + j for j in range(n)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = new_obj(name, me)
    fix_normals(ob)
    return ob


def rounded_rect(w, t, k=3, rr=0.35):
    """Rounded rectangle (2D, (a, b)) width w along a, thickness t along b. k pts per corner."""
    r = min(w, t) * rr
    pts = []
    for cx, cy, a0 in ((w / 2 - r, t / 2 - r, 0), (-w / 2 + r, t / 2 - r, 90), (-w / 2 + r, -t / 2 + r, 180), (w / 2 - r, -t / 2 + r, 270)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def plate(name, outer, inner, x0, x1):
    """Flat ring in the wheel plane between two closed outlines with the same point count
    (lists of (y, z)), extruded from x0 to x1. Gives clean quads, no ngons."""
    n = len(outer)
    assert len(inner) == n
    verts = []
    for x in (x0, x1):
        verts += [(x, y, z) for y, z in outer]
        verts += [(x, y, z) for y, z in inner]
    O0, I0, O1, I1 = 0, n, 2 * n, 3 * n
    faces = []
    for j in range(n):
        j2 = (j + 1) % n
        faces.append((O0 + j, I0 + j, I0 + j2, O0 + j2))      # x0 face
        faces.append((O1 + j, O1 + j2, I1 + j2, I1 + j))      # x1 face
        faces.append((O0 + j, O0 + j2, O1 + j2, O1 + j))      # outer wall
        faces.append((I0 + j, I1 + j, I1 + j2, I0 + j2))      # inner wall
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = new_obj(name, me)
    fix_normals(ob)
    return ob


def circle2d(r, n, cy=0.0, cz=0.0, a0=0.0):
    return [(cy + r * math.cos(a0 + 2 * math.pi * i / n), cz + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def cylinder_x(name, r, x0, x1, seg=24, cy=0.0, cz=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=abs(x1 - x0))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = new_obj(name, me)
    ob.rotation_euler = (0, math.pi / 2, 0)
    ob.location = ((x0 + x1) / 2, cy, cz)
    apply(ob)
    return ob


def apply(ob):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def boolean(ob, cutters, op='DIFFERENCE'):
    """Apply a boolean with a joined copy of all cutters, then delete the cutters."""
    if not cutters:
        return ob
    c = join(cutters, "_cut")
    m = ob.modifiers.new("b", 'BOOLEAN')
    m.object = c
    m.operation = op
    m.solver = 'EXACT'
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c, do_unlink=True)
    return ob


def join(obs, name):
    obs = [o for o in obs if o]
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def bevel(ob, width=0.0007, segs=2, angle=40):
    m = ob.modifiers.new("bev", 'BEVEL')
    m.width = width
    m.segments = segs
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle)
    m.harden_normals = False
    m.use_clamp_overlap = True
    apply(ob)


def smooth(ob, angle=35):
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.set_sharp_from_angle(angle=math.radians(angle))


def rotate_x(ob, ang):
    ob.rotation_euler = (ang, 0, 0)
    apply(ob)


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)
