"""Lightning sprites for tulevo storms, rendered in Cycles.

    blender --background --python art/blender/weather/render_lightning.py -- OUT_DIR [--quick] [--gpu]

OUT_DIR/lightning/Bolt01..08.png  branching bolts on BLACK, 512 x 1024, top = cloud, bottom = hit
OUT_DIR/lightning/Impact.png      ground-strike flash: 16 frames, 4x4 grid on black (1024)

Bolts are tubes of glowing plasma: a hot white core inside a blue-violet sheath, thick at the
main channel, thin forks that branch off and die in the air. tools/weather_sprites.py adds
the soft glow and turns the black background into alpha for Roblox.
"""
import math
import os
import random
import sys

import bpy  # noqa: I001
import bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--")), os.path.abspath("lightning_out"))
QUICK = "--quick" in argv
GPU = "--gpu" in argv


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    if GPU:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == kind
                    break
            except TypeError:
                continue
        sc.cycles.device = "GPU"
    sc.cycles.samples = 16 if QUICK else 96
    sc.cycles.use_denoising = False
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0  # pure black
    sc.world = w
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    return sc


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def glow_volume(name, color, strength):
    """Soft glowing gas: emission in a volume, densest in the middle."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.0
    vol.inputs["Emission Color"].default_value = (*color, 1)
    # falloff: strength * (1 - distance from centre)^2 via object coords
    tc = nt.nodes.new("ShaderNodeTexCoord")
    centre = nt.nodes.new("ShaderNodeVectorMath")  # generated coords are 0..1 over the mesh
    centre.operation = "MULTIPLY_ADD"
    nt.links.new(tc.outputs["Generated"], centre.inputs[0])
    centre.inputs[1].default_value = (2, 2, 2)
    centre.inputs[2].default_value = (-1, -1, -1)
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(centre.outputs[0], ln.inputs[0])
    rng_ = nt.nodes.new("ShaderNodeMapRange")
    rng_.inputs["From Min"].default_value = 0
    rng_.inputs["From Max"].default_value = 1
    rng_.inputs["To Min"].default_value = strength
    rng_.inputs["To Max"].default_value = 0
    nt.links.new(ln.outputs["Value"], rng_.inputs["Value"])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(rng_.outputs["Result"], pw.inputs[0])
    pw.inputs[1].default_value = 2.0
    nt.links.new(pw.outputs[0], vol.inputs["Emission Strength"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m


def zigzag(rng, a, b, depth, jitter, out):
    if depth == 0:
        out.append(b)
        return
    mid = (a + b) / 2
    ln = (b - a).length
    mid += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1) * 0.4, rng.uniform(-0.25, 0.25))) * ln * jitter
    zigzag(rng, a, mid, depth - 1, jitter, out)
    zigzag(rng, mid, b, depth - 1, jitter, out)


def tube(bm, pts, r0, r1, sides=8):
    """Tube through pts, radius r0 at the start tapering to r1."""
    rings = []
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = d.cross(Vector((0, 1, 0)))
        if side.length < 1e-3:
            side = d.cross(Vector((1, 0, 0)))
        side.normalize()
        up = d.cross(side).normalized()
        r = r0 + (r1 - r0) * i / max(1, len(pts) - 1)
        rings.append([bm.verts.new(p + (side * math.cos(a) + up * math.sin(a)) * r)
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for i in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))


def bolt(seed, core_mat, sheath_mat):
    rng = random.Random(seed)
    top = Vector((rng.uniform(-1.5, 1.5), 0, 20))
    hit = Vector((rng.uniform(-1, 1), 0, 0))
    main = [top]
    zigzag(rng, top, hit, 7, 0.12, main)
    for p in main:  # stay inside the frame
        p.x = max(-3.6, min(3.6, p.x))
    core, sheath = bmesh.new(), bmesh.new()
    tube(core, main, 0.05, 0.07)
    tube(sheath, main, 0.16, 0.22)
    # forks, and forks of forks
    def fork(bm_c, bm_s, start_pts, level, count):
        for _ in range(count):
            i = rng.randint(2, max(2, int(len(start_pts) * 0.75)))
            frm = start_pts[i]
            down = (start_pts[min(i + 1, len(start_pts) - 1)] - frm).normalized()
            side = Vector((rng.choice((-1, 1)) * rng.uniform(0.6, 1.2), rng.uniform(-0.3, 0.3), 0))
            reach = rng.uniform(2.5, 7.0) / (level + 1)
            to = frm + (down * 0.7 + side).normalized() * reach
            pts = [frm]
            zigzag(rng, frm, to, 5 - level, 0.25, pts)
            for p in pts:
                p.x = max(-4.6, min(4.6, p.x))
            w = 0.6 / (level + 1)
            tube(bm_c, pts, 0.035 * w, 0.004)
            tube(bm_s, pts, 0.1 * w, 0.01)
            if level < 1:
                fork(bm_c, bm_s, pts, level + 1, rng.randint(1, 3))
    fork(core, sheath, main, 0, rng.randint(4, 8))
    obs = []
    for bm, mat, name in ((core, core_mat, "Core"), (sheath, sheath_mat, "Sheath")):
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


def camera(scale, z):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.location = (0, -50, z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def bolts():
    for n in range(1, 9):
        sc = reset()
        sc.render.resolution_x, sc.render.resolution_y = (128, 256) if QUICK else (512, 1024)
        core = emissive("Core", (1.0, 1.0, 1.0), 30)
        sheath = emissive("Sheath", (0.55, 0.62, 1.0), 2.2)
        sheath.blend_method = "BLEND" if hasattr(sheath, "blend_method") else None
        bolt(n * 17, core, sheath)
        camera(20.5, 10)  # ortho scale = the taller side, so 20.5 tall x 10.25 wide
        render(os.path.join(OUT, "lightning", f"Bolt{n:02d}.png"))


def impact():
    """Ground strike: white-hot flash ball that blooms and fades, a ring of sparks flying
    out and falling, seen from the side. 16 frames."""
    frames = []
    rng = random.Random(9)
    sparks = [(rng.uniform(0, 2 * math.pi), rng.uniform(4, 9), rng.uniform(2, 7), rng.uniform(0.02, 0.05)) for _ in range(40)]
    for f in range(16):
        t = f / 15
        sc = reset()
        sc.render.resolution_x = sc.render.resolution_y = 64 if QUICK else 256
        hot = glow_volume("Hot", (1, 0.97, 0.92), 3.2 * (1 - t) ** 1.5 + 0.05)
        glow = glow_volume("Glow", (0.6, 0.68, 1.0), 1.1 * (1 - t) ** 1.2)
        spark = emissive("Spark", (1.0, 0.8, 0.55), 25 * (1 - t))
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.3 + 0.9 * math.sqrt(t))
        for ob_bm, mat, name in ((bm, hot, "Ball"),):
            me = bpy.data.meshes.new(name)
            ob_bm.to_mesh(me)
            ob_bm.free()
            me.materials.append(mat)
            ob = bpy.data.objects.new(name, me)
            sc.collection.objects.link(ob)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.8 + 2.6 * math.sqrt(t))
        me = bpy.data.meshes.new("Halo")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(glow)
        halo = bpy.data.objects.new("Halo", me)
        sc.collection.objects.link(halo)
        # sparks: short streaks along their velocity
        bm = bmesh.new()
        tt = t * 0.8
        for ang, vo, vu, r in sparks:
            p0 = Vector((math.cos(ang) * vo * tt, math.sin(ang) * vo * tt * 0.3, vu * tt - 0.5 * 14 * tt * tt))
            if p0.z < 0:
                continue
            vel = Vector((math.cos(ang) * vo, math.sin(ang) * vo * 0.3, vu - 14 * tt))
            p1 = p0 - vel.normalized() * 0.35
            tube(bm, [p1, p0], r * 0.5, r, 5)
        me = bpy.data.meshes.new("Sparks")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(spark)
        sp = bpy.data.objects.new("Sparks", me)
        sc.collection.objects.link(sp)
        camera(9, 2.2)
        p = os.path.join(OUT, "lightning", "_frames", f"impact_{f:02d}.png")
        render(p)
        frames.append(p)
    # 4x4 grid with Blender's image API
    imgs = [bpy.data.images.load(p) for p in frames]
    fw, fh = imgs[0].size
    W, H = fw * 4, fh * 4
    big = [0.0] * (W * H * 4)
    for k, im in enumerate(imgs):
        px = list(im.pixels)
        cx, cy = k % 4, 3 - k // 4
        for y in range(fh):
            row = (cy * fh + y) * W + cx * fw
            big[row * 4:(row + fw) * 4] = px[y * fw * 4:(y + 1) * fw * 4]
    out = bpy.data.images.new("grid", W, H, alpha=True)
    out.pixels = big
    out.filepath_raw = os.path.join(OUT, "lightning", "Impact.png")
    out.file_format = "PNG"
    out.save()
    for p in frames:
        os.remove(p)


bolts()
impact()
print("done ->", OUT)
