"""Turn a Microsoft Rocketbox avatar (MIT licence) into tulevo's static realistic human.

  blender --background --python build_rocketbox.py -- <avatar_dir> <out_dir> [--samples N] [--no-render]

avatar_dir holds <Name>.fbx plus its *_color.tga / *_normal.tga (from github.com/microsoft/Microsoft-Rocketbox,
Assets/Avatars/...). Steps: import -> pose a relaxed GTA-style idle -> one subdivision level for smooth
silhouettes -> split Body / Head -> 1024 colour + normal maps (cleaned: no text/logos) -> GLB in studs
(6.2 tall, Blender -Y = front) + preview renders + meta.json.

RULE: no text, URLs, watermarks, credit text, brand names or logos in any shipped texture (Roblox moderation).
"""
import glob
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 32
RENDER = "--no-render" not in argv
HEIGHT_STUDS = 6.2
TEX = 1024
# Areas painted over with plain surrounding fabric, as (x0, y0, x1, y1) fractions of the 2048 body map
# (top-left origin). Male_Adult_12: stitched designs on both back jean pockets.
CLEAN = {
    "m007_body": [(0.055, 0.045, 0.14, 0.13), (0.88, 0.05, 0.955, 0.13)],
}
os.makedirs(os.path.join(OUT, "tex"), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=glob.glob(os.path.join(SRC, "*.fbx"))[0])
rig = next(o for o in scene.objects if o.type == "ARMATURE")
body = next(o for o in scene.objects if o.type == "MESH")
for o in list(scene.objects):
    if o.type == "EMPTY":
        bpy.data.objects.remove(o)

# ---------------------------------------------------------------- pose
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
W = rig.matrix_world
Winv3 = W.inverted().to_3x3()


def upd():
    bpy.context.view_layer.update()


def head(b):
    upd()
    return W @ rig.pose.bones[b].head


def tail(b):
    upd()
    return W @ rig.pose.bones[b].tail


def rotw(b, axis, deg):
    """Rotate pose bone b about a WORLD axis through its head."""
    upd()
    pb = rig.pose.bones[b]
    ax = (Winv3 @ Vector(axis)).normalized()
    m = pb.matrix.copy()
    n = (Quaternion(ax, math.radians(deg)).to_matrix() @ m.to_3x3()).to_4x4()
    n.translation = m.translation
    pb.matrix = n
    upd()


def aim(b, child_point_fn, target_dir):
    """Rotate bone b so the vector head(b)->child point turns to target_dir (world)."""
    cur = (child_point_fn() - head(b)).normalized()
    t = Vector(target_dir).normalized()
    ax = cur.cross(t)
    if ax.length > 1e-6:
        rotw(b, ax, math.degrees(cur.angle(t)))


# which way is front? nose is in front of the head
front = (head("Bip01 MNose") - head("Bip01 Head"))
front.z = 0
front.normalize()
print("front", front)
side_l = head("Bip01 L UpperArm").x - head("Bip01 R UpperArm").x
print("L is +x" if side_l > 0 else "L is -x")
FWD = Vector((0, -1, 0))  # we'll turn the whole model to face -Y at the end

for s in ("L", "R"):
    sx = 1 if head(f"Bip01 {s} UpperArm").x > 0 else -1
    # shoulders relaxed
    rotw(f"Bip01 {s} Clavicle", (0, 1, 0), sx * 6)
    # upper arm hangs nearly straight down, slightly out and forward
    down = Vector((sx * 0.07, 0, -1)) + front * 0.06
    aim(f"Bip01 {s} UpperArm", lambda: head(f"Bip01 {s} Forearm"), down)
    # forearm: slight forward bend
    up_dir = (head(f"Bip01 {s} Forearm") - head(f"Bip01 {s} UpperArm")).normalized()
    fore = (up_dir + front * 0.22).normalized()
    aim(f"Bip01 {s} Forearm", lambda: head(f"Bip01 {s} Hand"), fore)
    # hand continues the forearm, palm toward the thigh
    fdir = (head(f"Bip01 {s} Hand") - head(f"Bip01 {s} Forearm")).normalized()
    aim(f"Bip01 {s} Hand", lambda: head(f"Bip01 {s} Finger2"), (fdir + front * 0.05).normalized())
    # palms in: twist forearm so the thumb points forward
    th = (head(f"Bip01 {s} Finger0") - head(f"Bip01 {s} Hand"))
    side = Vector((sx, 0, 0))
    for _ in range(2):
        th = (head(f"Bip01 {s} Finger0") - head(f"Bip01 {s} Hand"))
        th_p = th - th.project(fdir)
        if th_p.length < 1e-5:
            break
        want = front - front.project(fdir)
        ang = th_p.normalized().angle(want.normalized())
        ax = th_p.cross(want)
        if ax.length > 1e-6 and ang > math.radians(2):
            rotw(f"Bip01 {s} Forearm", ax, math.degrees(ang) * 0.85)
    # relaxed finger curl
    for f in range(5):
        for j, nm in enumerate((f"Bip01 {s} Finger{f}", f"Bip01 {s} Finger{f}1", f"Bip01 {s} Finger{f}2")):
            if nm not in rig.pose.bones:
                continue
            pb = rig.pose.bones[nm]
            # curl about the axis perpendicular to the finger and the palm side
            fd = (tail(nm) - head(nm)).normalized()
            ax = fd.cross(Vector((sx, 0, 0)) if f > 0 else front).normalized()
            if ax.length < 1e-6:
                continue
            rotw(nm, ax, -(14 + 6 * j) if f > 0 else -8)
    print(s, "wrist", tuple(round(c, 3) for c in head(f"Bip01 {s} Hand")))

# close the mouth a little (rest pose has the jaw dropped)
z0 = head("Bip01 MBottomLip").z
rotw("Bip01 MJaw", (1, 0, 0), 4)
if head("Bip01 MBottomLip").z < z0:
    rotw("Bip01 MJaw", (1, 0, 0), -8)
print("lip moved", head("Bip01 MBottomLip").z - z0)

# feet under the hips (about 11 cm either side of centre at the ankles)
for s in ("L", "R"):
    sx = 1 if head(f"Bip01 {s} Thigh").x > 0 else -1
    ank = head(f"Bip01 {s} Foot")
    hip = head(f"Bip01 {s} Thigh")
    off = abs(ank.x) - 0.11
    if abs(off) > 0.005:
        deg = math.degrees(math.atan2(off, hip.z - ank.z))
        rotw(f"Bip01 {s} Thigh", (0, 1, 0) if True else (0, 1, 0), (1 if sx > 0 else -1) * deg * (1 if front.y < 0 else 1))
        if abs(head(f"Bip01 {s} Foot").x) > abs(ank.x):  # went the wrong way
            rotw(f"Bip01 {s} Thigh", (0, 1, 0), -2 * (1 if sx > 0 else -1) * deg)
        # keep the sole flat: undo the tilt on the foot
        fdz = tail(f"Bip01 {s} Foot")
    print(s, "ankle", tuple(round(c, 3) for c in head(f"Bip01 {s} Foot")))
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- bake the pose, smooth, scale, face -Y
bpy.context.view_layer.objects.active = body
for o in scene.objects:
    o.select_set(o == body)
for m in body.modifiers:
    if m.type == "ARMATURE":
        bpy.ops.object.modifier_apply(modifier=m.name)
mw = body.matrix_world.copy()
body.parent = None
body.matrix_world = mw
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.data.objects.remove(rig)
body.vertex_groups.clear()

# turn so the face points to -Y
yaw = math.atan2(front.x, -front.y)
R = Matrix.Rotation(yaw, 4, "Z")
me = body.data
me.transform(R)
co = np.empty(len(me.vertices) * 3)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)
zmin, zmax = co[:, 2].min(), co[:, 2].max()
S = HEIGHT_STUDS / (zmax - zmin)
cx, cy = (co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2
co = (co - [cx, cy, zmin]) * S
me.vertices.foreach_set("co", co.ravel())
me.update()
print("source height m", zmax - zmin)

sub = body.modifiers.new("Sub", "SUBSURF")
sub.levels = sub.render_levels = 1
sub.uv_smooth = "PRESERVE_BOUNDARIES"
bpy.ops.object.modifier_apply(modifier="Sub")
for p in me.polygons:
    p.use_smooth = True

# split by material: Body / Head
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="MATERIAL")
bpy.ops.object.mode_set(mode="OBJECT")
parts = [o for o in scene.objects if o.type == "MESH"]
# Roblox caps a MeshPart at ~20k triangles: cut the body at the waist into Upper / Lower
for ob in list(parts):
    ob.data.calc_loop_triangles()
    if "body" in ob.data.materials[0].name.lower() and len(ob.data.loop_triangles) > 19000:
        for o in scene.objects:
            o.select_set(o == ob)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for p in ob.data.polygons:
            p.select = p.center.z < HEIGHT_STUDS * 0.5
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.separate(type="SELECTED")
        bpy.ops.object.mode_set(mode="OBJECT")
        low = [o for o in scene.objects if o.type == "MESH" and o not in parts][0]
        low["part"] = "BodyLower"
        ob["part"] = "BodyUpper"
        parts.append(low)


# ---------------------------------------------------------------- textures
def find_tex(mat_name, kind):
    base = mat_name.replace("_hipoly", "")
    for c in glob.glob(os.path.join(SRC, f"*{kind}.tga")) + glob.glob(os.path.join(SRC, f"*{kind}.png")):
        b = os.path.basename(c).lower()
        if b.startswith(base.lower() + "_") or b.startswith(base.lower()):
            return c
    return None


def clean_and_save(path, name, regions, normal=False):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    for (x0, y0, x1, y1) in regions:
        # Blender rows go bottom-up; regions are top-left fractions
        r0, r1 = int((1 - y1) * h), int((1 - y0) * h)
        c0, c1 = int(x0 * w), int(x1 * w)
        # patch with plain fabric copied from just below the region, feathered at the edges
        hh = r1 - r0
        src = px[r0 - hh - 4:r0 - 4, c0:c1, :3].copy()
        yy, xx = np.mgrid[0:hh, 0:c1 - c0]
        f = 10.0
        edge = np.minimum.reduce([yy, hh - 1 - yy, xx, c1 - c0 - 1 - xx]).astype(np.float32)
        a = np.clip(edge / f, 0, 1)[..., None]
        px[r0:r1, c0:c1, :3] = px[r0:r1, c0:c1, :3] * (1 - a) + src * a
    out = bpy.data.images.new(name, w, h, alpha=False, is_data=normal)
    out.pixels.foreach_set(px.ravel())
    if (w, h) != (TEX, TEX):
        out.scale(TEX, TEX)
    p = os.path.join(OUT, "tex", name + ".png")
    out.filepath_raw = p
    out.file_format = "PNG"
    out.save()
    return out, p


tex_files = {}
made = {}
meta = {"parts": {}, "height": HEIGHT_STUDS, "source": "Microsoft Rocketbox " + os.path.basename(SRC) + " (MIT)"}
for ob in parts:
    mat = ob.data.materials[0]
    mname = mat.name.split(".")[0]
    tex_name = "Head" if "head" in mname.lower() else "Body"
    pname = ob.get("part", tex_name)
    ob.name = pname
    col = find_tex(mname, "color")
    nrm = find_tex(mname, "normal")
    regions = CLEAN.get(mname, [])
    if tex_name not in made:
        cimg, cp = clean_and_save(col, tex_name, regions)
        nimg, np_ = clean_and_save(nrm, tex_name + "_Normal", regions, normal=True) if nrm else (None, None)
        made[tex_name] = (cimg, nimg)
        tex_files[tex_name] = cp
        if np_:
            tex_files[tex_name + "_Normal"] = np_
    cimg, nimg = made[tex_name]
    tex_files.setdefault("_parts", {})[pname] = tex_name
    m = bpy.data.materials.new(pname)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.68 if pname == "Head" else 0.85
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = cimg
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    if nimg:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = nimg
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    ob.data.calc_loop_triangles()
    meta["parts"][pname] = len(ob.data.loop_triangles)
meta["tris"] = sum(meta["parts"].values())
meta["part_texture"] = tex_files.pop("_parts")
meta["textures"] = {k: os.path.relpath(v, OUT) for k, v in tex_files.items()}
print("tris", meta)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Human.blend"))
for o in scene.objects:
    o.select_set(o in parts)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Human.glb"), export_format="GLB", use_selection=True,
                          export_apply=True, export_image_format="JPEG", export_jpeg_quality=92)

# ---------------------------------------------------------------- previews
if RENDER:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        scene.cycles.device = "GPU"
    except Exception as e:
        print("gpu", e)
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    scene.collection.objects.link(sun)
    fl = bpy.data.meshes.new("Floor")
    fl.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    fo = bpy.data.objects.new("Floor", fl)
    scene.collection.objects.link(fo)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    H = HEIGHT_STUDS

    def shot(name, pos, target, lens):
        cam.location = Vector(pos)
        cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)

    shot("front", (0, -22, H * 0.55), (0, 0, H * 0.5), 50)
    shot("front34", (12, -17, H * 0.6), (0, 0, H * 0.5), 50)
    shot("back34", (-12, 17, H * 0.6), (0, 0, H * 0.5), 50)
    shot("face", (1.2, -4.2, H * 0.93), (0, 0, H * 0.92), 85)
