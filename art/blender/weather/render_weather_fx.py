"""Realistic weather sprites for tulevo, rendered in Cycles (volumes + water shading).

    blender --background --python art/blender/weather/render_weather_fx.py -- OUT_DIR [--quick] [--only clouds|fx] [--gpu]

OUT_DIR/clouds/<Name>.png   volumetric clouds (Principled Volume, multiple scattering, sun from
                            above-side) on a transparent background, 1024 wide. The game puts
                            them on camera-facing cards that drift across the sky.
OUT_DIR/clouds/clouds.json  { name: [width, height] in pixels, ... } so the game keeps the aspect
OUT_DIR/fx/Splash.png       raindrop splash crown, 16 frames in a 4x4 grid (1024)
OUT_DIR/fx/Ripple.png       ring ripple seen from above, 16 frames 4x4 (1024)
OUT_DIR/fx/RainDrop.png     one falling drop, motion-stretched, with refraction highlights
OUT_DIR/fx/Spray.png        a burst of tiny droplets
OUT_DIR/preview_*.png       contact sheets on a sky colour

--quick renders small with few samples (for checking on CPU); full quality wants a GPU.
"""
import json
import math
import os
import random
import sys

import bpy  # noqa: I001 (bpy first: the pip build only exposes bmesh after it)
import bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--")), os.path.abspath("weather_fx_out"))
QUICK = "--quick" in argv
GPU = "--gpu" in argv
ONLY = argv[argv.index("--only") + 1] if "--only" in argv else None


# ------------------------------------------------------------------ scene

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(res_x, res_y, samples):
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
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 32
    sc.cycles.volume_bounces = 24
    sc.cycles.transparent_max_bounces = 32
    sc.cycles.transmission_bounces = 16
    sc.cycles.glossy_bounces = 8
    sc.cycles.volume_step_rate = 0.5 if not QUICK else 2.0
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = res_x, res_y
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    sc.view_settings.look = "None"


def world(color, strength, top=None):
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if top is None:
        bg.inputs[0].default_value = (*color, 1)
    else:
        # simple gradient sky: horizon colour -> top colour by view height
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*color, 1)
        ramp.color_ramp.elements[1].color = (*top, 1)
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = strength
    bpy.context.scene.world = w


def sun(elev, azim, strength, angle=0.53, color=(1, 0.98, 0.94)):
    s = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    s.data.energy = strength
    s.data.angle = math.radians(angle)
    s.data.color = color
    # pointing direction: from (azim, elev) toward the origin
    s.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim + 90))
    bpy.context.scene.collection.objects.link(s)
    return s


def ortho_cam(loc, rot_deg, scale):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_end = 1000
    cam.location = loc
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ clouds

def cumulus_puffs(rng, length, height, depth, lobes, tower):
    puffs = []
    for i in range(lobes):
        t = (i + 0.5) / lobes
        x = (t - 0.5) * length + rng.uniform(-0.3, 0.3)
        mid = 1 - abs(t - 0.5) * 2
        r = (0.6 + 0.55 * mid) * height * rng.uniform(0.8, 1.1)
        puffs.append((x, rng.uniform(-0.25, 0.25) * depth, r * 0.7, r))
        if rng.random() < 0.7:
            puffs.append((x + rng.uniform(-0.5, 0.5), rng.choice((-1, 1)) * depth * rng.uniform(0.2, 0.35), r * 0.6, r * rng.uniform(0.6, 0.85)))
    for _ in range(2 + int(tower * 3)):
        x = rng.uniform(-0.22, 0.22) * length
        r = height * rng.uniform(0.6, 0.85)
        top = height * (1.0 + tower * rng.uniform(0.6, 1.4))
        z = height * 0.9
        while z < top:
            puffs.append((x * (z / top), rng.uniform(-0.15, 0.15) * depth, z, r * 1.05))
            z += r * 0.8
        puffs.append((x, rng.uniform(-0.2, 0.2) * depth, top, r))
    big = list(puffs)
    for x, y, z, r in big:  # billows on the upper half
        for _ in range(int(5 + r * 5)):
            th = rng.uniform(0, 2 * math.pi)
            ph = rng.uniform(0.05, 1.3)
            d = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
            p = Vector((x, y, z)) + d * r * 0.72
            puffs.append((p.x, p.y, p.z, r * rng.uniform(0.3, 0.5)))
    return puffs


def strato_puffs(rng, length, height, depth, lobes):
    puffs = []
    for i in range(lobes):
        for j in range(3):
            x = ((i + rng.uniform(0.2, 0.8)) / lobes - 0.5) * length
            y = ((j + rng.uniform(0.2, 0.8)) / 3 - 0.5) * depth
            r = height * rng.uniform(1.5, 2.1)
            puffs.append((x, y, -r * 0.35 + rng.uniform(0, 0.4), r))
    for x, y, z, r in list(puffs):
        for _ in range(4):
            puffs.append((x + rng.uniform(-r, r) * 0.6, y + rng.uniform(-r, r) * 0.6, z + r * 0.75, r * rng.uniform(0.35, 0.55)))
    return puffs


def drop_islands(bm):
    """Keep only the biggest connected piece (stray puffs read as floating blobs)."""
    seen, groups = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, group = [v], []
        seen.add(v)
        while stack:
            a = stack.pop()
            group.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b not in seen:
                    seen.add(b)
                    stack.append(b)
        groups.append(group)
    groups.sort(key=len, reverse=True)
    for g in groups[1:]:
        bmesh.ops.delete(bm, geom=g, context="VERTS")


def metaball_mesh(name, puffs, flat):
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = mb.render_resolution = 0.18 if not QUICK else 0.3
    mb.threshold = 0.6
    for x, y, z, r in puffs:
        el = mb.elements.new()
        el.co = (x, y, z)
        el.radius = r
        el.stiffness = 1.6
    ob = bpy.data.objects.new(name + "_mbob", mb)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob, do_unlink=True)
    bm = bmesh.new()
    bm.from_mesh(me)
    drop_islands(bm)
    for v in bm.verts:  # flat-ish base, like real cumulus
        if v.co.z < flat:
            v.co.z = flat + (v.co.z - flat) * 0.1
    bm.to_mesh(me)
    bm.free()
    shape = bpy.data.objects.new(name + "_shape", me)
    bpy.context.scene.collection.objects.link(shape)
    shape.hide_render = True
    return shape


def noise_tex(name, kind, size, depth=2):
    t = bpy.data.textures.new(name, kind)
    t.noise_scale = size
    if hasattr(t, "noise_depth"):
        t.noise_depth = depth
    if hasattr(t, "noise_type"):
        t.noise_type = "SOFT_NOISE"
    return t


def cloud_material(dark=0.0, wispy=1.0):
    m = bpy.data.materials.new("CloudVol")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (1 - 0.35 * dark,) * 3 + (1,)
    vol.inputs["Anisotropy"].default_value = 0.7
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "density"
    attr.attribute_type = "GEOMETRY"
    # erode the edges with fractal noise so they break up into wisps
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 10
    noise.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "MULTIPLY_ADD"  # density + (noise - 0.5) * wispy
    nt.links.new(noise.outputs["Fac"], sub.inputs[0])
    sub.inputs[1].default_value = 1.1 * wispy
    sub.inputs[2].default_value = -0.55 * wispy
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(attr.outputs["Fac"], add.inputs[0])
    nt.links.new(sub.outputs[0], add.inputs[1])
    clamp = nt.nodes.new("ShaderNodeMath")
    clamp.operation = "MULTIPLY"
    clamp.use_clamp = False
    nt.links.new(add.outputs[0], clamp.inputs[0])
    clamp.inputs[1].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.08
    ramp.inputs["From Max"].default_value = 0.7
    ramp.inputs["To Min"].default_value = 0.0
    ramp.inputs["To Max"].default_value = 16.0 * (1 + 0.5 * dark)
    nt.links.new(clamp.outputs[0], ramp.inputs["Value"])
    nt.links.new(ramp.outputs["Result"], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m


def cloud_volume(name, shape, mat, seed):
    vol = bpy.data.objects.new(name, bpy.data.volumes.new(name))
    bpy.context.scene.collection.objects.link(vol)
    m2v = vol.modifiers.new("m2v", "MESH_TO_VOLUME")
    m2v.object = shape
    m2v.resolution_mode = "VOXEL_SIZE"
    m2v.voxel_size = 0.045 if not QUICK else 0.12
    m2v.interior_band_width = 0.9
    m2v.density = 1.0
    # billows: big soft lumps, then small cauliflower detail
    for i, (size, strength) in enumerate(((1.4, 0.55), (0.45, 0.22))):
        d = vol.modifiers.new(f"disp{i}", "VOLUME_DISPLACE")
        tx = noise_tex(f"{name}_n{i}", "CLOUDS", size, 3)
        d.texture = tx
        d.strength = strength
        d.texture_mid_level = (0.5, 0.5, 0.5)
        d.texture_map_mode = "GLOBAL"
    vol.data.materials.append(mat)
    vol.location = (seed * 0.0, 0, 0)
    return vol


CLOUDS = [
    # name, kind, seed, length, height, depth, lobes, tower
    ("Cu01", "cu", 1, 10.0, 2.4, 5.0, 5, 0.3),
    ("Cu02", "cu", 2, 8.0, 2.2, 4.5, 4, 0.2),
    ("Cu03", "cu", 3, 12.0, 2.6, 5.5, 6, 0.4),
    ("Cu04", "cu", 4, 6.0, 2.0, 4.0, 3, 0.15),
    ("Cu05", "cu", 5, 9.0, 2.0, 6.0, 5, 0.25),
    ("Cu06", "cu", 7, 11.0, 2.2, 5.0, 6, 0.1),
    ("Cu07", "cu", 8, 7.0, 2.5, 4.5, 4, 0.5),
    ("Cu08", "cu", 9, 13.0, 2.1, 6.0, 7, 0.2),
    ("Cg01", "cu", 6, 9.0, 3.0, 6.0, 4, 1.4),
    ("Cg02", "cu", 10, 10.0, 3.2, 6.0, 5, 1.1),
    ("St01", "st", 11, 16.0, 1.2, 8.0, 9, 0),
    ("St02", "st", 12, 14.0, 1.0, 9.0, 8, 0),
    ("St03", "st", 13, 18.0, 1.3, 8.0, 10, 0),
    ("St04", "st", 14, 12.0, 1.1, 7.0, 7, 0),
]


def render_clouds():
    clear()
    width_px = 1024 if not QUICK else 256
    setup_render(width_px, width_px // 2, 384 if not QUICK else 16)
    world((0.42, 0.55, 0.78), 0.35, top=(0.18, 0.32, 0.62))
    sun(42, -35, 9.0)
    sizes = {}
    for name, kind, seed, length, height, depth, lobes, tower in CLOUDS:
        if QUICK and name not in ("Cu01", "Cg01", "St01"):
            continue
        for ob in [o for o in bpy.data.objects if o.type in ("MESH", "VOLUME", "CAMERA")]:
            bpy.data.objects.remove(ob, do_unlink=True)
        rng = random.Random(seed)
        if kind == "cu":
            shape = metaball_mesh(name, cumulus_puffs(rng, length, height, depth, lobes, tower), 0.45)
            mat = cloud_material(0.0, 1.0)
        else:
            shape = metaball_mesh(name, strato_puffs(rng, length, height, depth, lobes), 0.2)
            mat = cloud_material(0.25, 0.8)
        cloud_volume(name, shape, mat, seed)
        # frame from the side, a little below (we look up at clouds)
        mn = Vector([min(v.co[i] for v in shape.data.vertices) for i in range(3)])
        mx = Vector([max(v.co[i] for v in shape.data.vertices) for i in range(3)])
        w = (mx.x - mn.x) * 1.12 + 1.0
        h = (mx.z - mn.z) * 1.2 + 1.0
        aspect = max(1.0, w / h)
        ry = int(round(width_px / aspect / 8)) * 8
        bpy.context.scene.render.resolution_y = max(ry, 64)
        cz = (mn.z + mx.z) / 2
        ortho_cam((0, -60, cz - 60 * math.tan(math.radians(7))), (90 + 7, 0, 0), w)
        render_to(os.path.join(OUT, "clouds", name + ".png"))
        sizes[name] = [width_px, bpy.context.scene.render.resolution_y]
    os.makedirs(os.path.join(OUT, "clouds"), exist_ok=True)
    json.dump(sizes, open(os.path.join(OUT, "clouds", "clouds.json"), "w"), indent=1)


# ------------------------------------------------------------------ water fx

def water_material(emit=0.25):
    """Clear water for sprites: see-through in the middle, bright fresnel rims and highlights."""
    m = bpy.data.materials.new("Water")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    glass = nt.nodes.new("ShaderNodeBsdfGlossy")
    glass.inputs["Roughness"].default_value = 0.04
    glass.inputs["Color"].default_value = (1, 1, 1, 1)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    trans.inputs["Color"].default_value = (0.9, 0.95, 1, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.85, 0.9, 1, 1)
    em.inputs["Strength"].default_value = emit
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lw.outputs["Facing"], mix.inputs[0])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(glass.outputs[0], mix.inputs[2])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(mix.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    # emission only on the rims too
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(lw.outputs["Facing"], mul.inputs[0])
    mul.inputs[1].default_value = emit * 3
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m


def fx_scene():
    clear()
    world((0.75, 0.8, 0.88), 1.0, top=(1.6, 1.7, 1.8))
    sun(55, -30, 3.0)


def link(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def drop_sphere(bm, c, r, stretch=1.0):
    res = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
    for v in res["verts"]:
        v.co.z *= stretch
        v.co += c


def splash_frame(f, n_frames, rng_seed, mat):
    """Crown at time t (0..1): a thin wall that rises and flares, its rim breaking into
    fingers that throw droplets, then it all sinks back while the droplets fall."""
    rng = random.Random(rng_seed)
    t = f / (n_frames - 1)
    bm = bmesh.new()
    seg = 40
    rise = math.sin(min(t / 0.55, 1) * math.pi * 0.5) * (1 - max(0, (t - 0.55) / 0.45) ** 1.5)
    h = 0.75 * rise
    r0 = 0.12 + 0.32 * math.sqrt(t)
    r1 = r0 + 0.12 + 0.35 * math.sqrt(t)
    if h > 0.02:
        rows = []
        prof = [(r0 * 0.9, 0.0), (r0, h * 0.25), ((r0 + r1) / 2, h * 0.7), (r1, h)]
        for k, (r, z) in enumerate(prof):
            row = []
            for i in range(seg):
                a = 2 * math.pi * i / seg
                finger = 0.0
                if k == len(prof) - 1:
                    finger = (0.25 * h) * max(0.0, math.cos(a * 9 + rng_seed)) ** 6
                row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z + finger)))
            rows.append(row)
        for k in range(len(rows) - 1):
            for i in range(seg):
                j = (i + 1) % seg
                bm.faces.new((rows[k][i], rows[k][j], rows[k + 1][j], rows[k + 1][i]))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.025)
    # central bump (the drop's rebound) late in the splash
    if 0.45 < t < 0.95:
        k = (t - 0.45) / 0.5
        drop_sphere(bm, Vector((0, 0, 0.1 + 0.35 * math.sin(k * math.pi))), 0.07 * (1 - k * 0.5), 1.6)
    # thrown droplets: leave the rim at ~t=0.25 and fly out ballistically
    for i in range(14):
        a = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / 14
        start = 0.18 + rng.uniform(0, 0.15)
        if t < start:
            continue
        tt = (t - start) * 0.35
        v_out = rng.uniform(1.6, 2.6)
        v_up = rng.uniform(2.2, 3.2)
        z = 0.6 + v_up * tt - 0.5 * 30 * tt * tt
        if z < 0:
            continue
        rr = 0.5 + v_out * tt
        drop_sphere(bm, Vector((rr * math.cos(a), rr * math.sin(a), z)), rng.uniform(0.025, 0.045), 1.3)
    return link("Splash", bm, mat)


def ripple_frame(f, n_frames, mat):
    """Rings on a flat disc: displaced grid, emission on the slopes only."""
    t = f / (n_frames - 1)
    bm = bmesh.new()
    n = 96 if not QUICK else 40
    size = 1.0
    verts = {}
    for i in range(n + 1):
        for j in range(n + 1):
            x = (i / n - 0.5) * 2 * size
            y = (j / n - 0.5) * 2 * size
            r = math.hypot(x, y)
            z = 0.0
            for k, (delay, amp) in enumerate(((0.0, 1.0), (0.18, 0.55), (0.34, 0.3))):
                tt = t - delay
                if tt <= 0:
                    continue
                c = 0.08 + 0.85 * tt
                w = 0.035 + 0.04 * tt
                z += amp * 0.05 * (1 - t) ** 1.2 * math.exp(-((r - c) / w) ** 2)
            verts[i, j] = bm.verts.new((x, y, z))
    for i in range(n):
        for j in range(n):
            bm.faces.new((verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1]))
    return link("Ripple", bm, mat)


def ripple_material():
    m = bpy.data.materials.new("RippleMat")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs[0])
    slope = nt.nodes.new("ShaderNodeMapRange")
    slope.inputs["From Min"].default_value = 0.995
    slope.inputs["From Max"].default_value = 0.93
    nt.links.new(sep.outputs["Z"], slope.inputs["Value"])
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.9, 0.94, 1, 1)
    em.inputs["Strength"].default_value = 1.2
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(slope.outputs["Result"], mix.inputs[0])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def grid(paths, out_path, cols=4):
    """Pack frames into a cols x cols flipbook with Blender's own image API (no PIL on the PC)."""
    imgs = [bpy.data.images.load(p) for p in paths]
    fw, fh = imgs[0].size
    W, H = fw * cols, fh * cols
    big = [0.0] * (W * H * 4)
    for k, im in enumerate(imgs):
        px = list(im.pixels)
        cx, cy = k % cols, cols - 1 - k // cols  # frame 0 top-left (Blender rows go bottom-up)
        for y in range(fh):
            row = (cy * fh + y) * W + cx * fw
            big[row * 4:(row + fw) * 4] = px[y * fw * 4:(y + 1) * fw * 4]
    out = bpy.data.images.new("grid", W, H, alpha=True)
    out.pixels = big
    out.filepath_raw = out_path
    out.file_format = "PNG"
    out.save()
    for p in paths:
        os.remove(p)


def render_fx():
    fx = os.path.join(OUT, "fx")
    tmp = os.path.join(OUT, "fx", "_frames")
    frame_px = 256 if not QUICK else 64
    samples = 128 if not QUICK else 8
    n = 16

    # splash: seen from a bit above, like a player looking at the street
    fx_scene()
    setup_render(frame_px, frame_px, samples)
    mat = water_material(0.35)
    ortho_cam((0, -20, 0.55 + 20 * math.tan(math.radians(18))), (90 - 18, 0, 0), 1.9)
    paths = []
    for f in range(n):
        for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
            bpy.data.objects.remove(ob, do_unlink=True)
        splash_frame(f, n, 3, mat)
        p = os.path.join(tmp, f"splash_{f:02d}.png")
        render_to(p)
        paths.append(p)
    grid(paths, os.path.join(fx, "Splash.png"))

    # ripple: straight down
    fx_scene()
    setup_render(frame_px, frame_px, samples)
    rmat = ripple_material()
    ortho_cam((0, 0, 10), (0, 0, 0), 2.1)
    paths = []
    for f in range(n):
        for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
            bpy.data.objects.remove(ob, do_unlink=True)
        ripple_frame(f, n, rmat)
        p = os.path.join(tmp, f"ripple_{f:02d}.png")
        render_to(p)
        paths.append(p)
    grid(paths, os.path.join(fx, "Ripple.png"))

    # one falling drop: a long thin water capsule (motion stretch), bright rim
    fx_scene()
    setup_render(frame_px, frame_px, samples * 2)
    ortho_cam((0, -20, 0), (90, 0, 0), 2.0)
    bm = bmesh.new()
    drop_sphere(bm, Vector((0, 0, 0)), 0.05, 17)
    link("Drop", bm, water_material(0.6))
    render_to(os.path.join(fx, "RainDrop.png"))

    # spray: a loose burst of droplets
    for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    rng = random.Random(5)
    bm = bmesh.new()
    for _ in range(22):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.1, 0.8)
        drop_sphere(bm, Vector((r * math.cos(a), rng.uniform(-0.2, 0.2), r * math.sin(a) * 0.8)), rng.uniform(0.03, 0.07), 1.2)
    link("Spray", bm, water_material(0.6))
    render_to(os.path.join(fx, "Spray.png"))
    try:
        os.rmdir(tmp)
    except OSError:
        pass


def main():
    os.makedirs(OUT, exist_ok=True)
    if ONLY in (None, "clouds"):
        render_clouds()
    if ONLY in (None, "fx"):
        render_fx()
    print("done ->", OUT)


main()
