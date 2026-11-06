"""Gun VFX sprites for tulevo (muzzle flash, muzzle smoke, bullet tracer), rendered in Cycles.

    blender --background --python art/blender/weapons/render_muzzle_fx.py -- OUT_DIR [--quick] [--gpu]

OUT_DIR/MuzzleSide1..4.png   rifle flash seen from the side, on BLACK, 512 x 384. The muzzle is
                             at x = 7.5% of the width, mid height (left), the gas shoots to the right.
                             A hot white core at the flash hider, an orange-yellow plume of
                             burning gas ahead of it, and 3-5 short jets out of the hider's
                             slots. Noise-shaped emission volumes, so every variant is ragged.
OUT_DIR/MuzzleFront1..2.png  the same flash looking down the barrel: a 4-5 point star, 256 x 256
OUT_DIR/MuzzleSmoke1..2.png  a thin grey puff of smoke, lit, on a transparent background, 256
OUT_DIR/Tracer.png           GTA-style tracer streak on BLACK, 512 x 64: a thin white-hot core,
                             bright head on the right fading to nothing at the tail (left)

tools/weapon_fx_sprites.py turns the black backgrounds into alpha and copies them into
art/weapons/fx/ for tools/upload_textures.py (TextureIds.WeaponFx).
"""
import math
import os
import random
import sys

import bpy  # noqa: I001 (bpy first: the pip build only exposes bmesh after it)
import bmesh
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--")), os.path.abspath("muzzle_fx_out"))
QUICK = "--quick" in argv
GPU = "--gpu" in argv


# ------------------------------------------------------------------ scene

def reset(transparent=False):
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
    sc.cycles.samples = 24 if QUICK else 256
    sc.cycles.use_denoising = False
    sc.cycles.volume_step_rate = 0.5
    sc.cycles.volume_max_steps = 512
    sc.render.film_transparent = transparent
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9 if transparent else 0.0
    sc.world = w
    # Filmic-style roll-off: the hottest gas burns out to white instead of clipping to yellow
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    return sc


def camera(cx, cz, scale):
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.location = (cx, -20, cz)
    cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam


def render(path, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = (w // 4, h // 4) if QUICK else (w, h)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ materials

def _falloff(nt, power):
    """0..1 'how deep inside the mesh' from Generated coords (1 at the centre, 0 at the skin)."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    c = nt.nodes.new("ShaderNodeVectorMath")
    c.operation = "MULTIPLY_ADD"
    nt.links.new(tc.outputs["Generated"], c.inputs[0])
    c.inputs[1].default_value = (2, 2, 2)
    c.inputs[2].default_value = (-1, -1, -1)
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(c.outputs[0], ln.inputs[0])
    inv = nt.nodes.new("ShaderNodeMapRange")
    inv.inputs["From Min"].default_value = 0
    inv.inputs["From Max"].default_value = 1
    inv.inputs["To Min"].default_value = 1
    inv.inputs["To Max"].default_value = 0
    nt.links.new(ln.outputs["Value"], inv.inputs["Value"])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(inv.outputs["Result"], pw.inputs[0])
    pw.inputs[1].default_value = power
    return tc, pw


def _noise(nt, tc, scale, seed, detail, lo, hi):
    """Turbulence factor lo..hi from 4D noise in object space (seed = W)."""
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nz.inputs["Roughness"].default_value = 0.62
    nz.inputs["W"].default_value = seed
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.3
    mr.inputs["From Max"].default_value = 0.7
    mr.inputs["To Min"].default_value = lo
    mr.inputs["To Max"].default_value = hi
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    return mr.outputs["Result"]


def fire_volume(name, color, strength, seed, noise_scale=6.0, power=1.6, lo=0.0, hi=1.6):
    """Burning gas: pure emission (no absorption, so it adds like light), brightest in the
    middle of the mesh and torn up by noise so the edges are ragged licks of flame."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.0
    vol.inputs["Emission Color"].default_value = (*color, 1)
    tc, fall = _falloff(nt, power)
    turb = _noise(nt, tc, noise_scale, seed, 6.0, lo, hi)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(fall.outputs[0], mul.inputs[0])
    nt.links.new(turb, mul.inputs[1])
    # cut the thin outer haze so the flame has a crisp-ish silhouette
    cut = nt.nodes.new("ShaderNodeMapRange")
    cut.inputs["From Min"].default_value = 0.06
    cut.inputs["From Max"].default_value = 1.0
    cut.inputs["To Min"].default_value = 0
    cut.inputs["To Max"].default_value = strength
    nt.links.new(mul.outputs[0], cut.inputs["Value"])
    nt.links.new(cut.outputs["Result"], vol.inputs["Emission Strength"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m


def smoke_volume(name, seed, density):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.85, 0.84, 0.82, 1)
    vol.inputs["Anisotropy"].default_value = 0.3
    tc, fall = _falloff(nt, 1.3)
    turb = _noise(nt, tc, 3.2, seed, 8.0, 0.0, 1.8)
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(fall.outputs[0], mul.inputs[0])
    nt.links.new(turb, mul.inputs[1])
    d = nt.nodes.new("ShaderNodeMath")
    d.operation = "MULTIPLY"
    nt.links.new(mul.outputs[0], d.inputs[0])
    d.inputs[1].default_value = density
    nt.links.new(d.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return m


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


# ------------------------------------------------------------------ shapes

def blob(name, mat, length, radius, angle=0.0, start=0.0, squash=1.0, tilt=0.0):
    """Ellipsoid of gas from the muzzle (origin) out along +X turned by `angle` (degrees, in the
    XZ picture plane), starting `start` from the muzzle. `tilt` turns it out of the picture plane
    (around X) so side jets don't all lie flat."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector((length / 2, radius, radius * squash)), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    a = math.radians(angle)
    d = Vector((math.cos(a), 0, math.sin(a)))
    ob.matrix_world = (Matrix.Translation(d * (start + length / 2))
                       @ Matrix.Rotation(-a, 4, "Y") @ Matrix.Rotation(math.radians(tilt), 4, "X"))
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------ sprites

HOT = (1.0, 0.93, 0.78)     # white-hot core
YELLOW = (1.0, 0.72, 0.32)
ORANGE = (1.0, 0.42, 0.10)
DEEP = (0.85, 0.22, 0.04)


def side(n):
    """Rifle flash from the side. Muzzle at the origin, gas to +X. Frame: x -0.12..1.48, z +-0.6."""
    rng = random.Random(100 + n)
    reset()
    s = rng.random() * 50
    L = rng.uniform(0.75, 1.05)
    # white-hot core right at the flash hider
    blob("Core", fire_volume("Core", HOT, 70, s, 9, 1.2, 0.6, 1.3), 0.34, 0.085, start=-0.02)
    # inner yellow plume, then the big ragged orange plume of burning gas around it
    bend = rng.uniform(-3, 3)
    blob("Inner", fire_volume("Inner", YELLOW, 45, s + 3, 9, 1.4, 0.1, 1.8), L * 0.62, 0.075, bend, 0.04)
    blob("Plume", fire_volume("Plume", ORANGE, 30, s + 7, 9.0, 1.4, -0.5, 2.6), L, rng.uniform(0.15, 0.2), bend, 0.06,
         squash=rng.uniform(0.8, 1.0))
    # a soft deep-orange tongue that licks past the plume's tip
    blob("Tip", fire_volume("Tip", DEEP, 12, s + 11, 7, 1.6, 0.0, 2.2), L * 0.55, 0.09, bend + rng.uniform(-4, 4),
         L * 0.62)
    # jets out of the flash hider's slots: short, hot, fanned up and down, a few out of plane
    count = rng.randint(3, 5)
    for k in range(count):
        up = 1 if k % 2 == 0 else -1
        ang = up * rng.uniform(38, 80)
        blob(f"Jet{k}", fire_volume(f"Jet{k}", YELLOW, 60, s + 20 + k, 10, 1.4, 0.2, 1.5),
             rng.uniform(0.28, 0.55), rng.uniform(0.03, 0.05), ang, 0.02, tilt=rng.uniform(-40, 40))
    camera(0.68, 0, 1.6)
    render(os.path.join(OUT, f"MuzzleSide{n}.png"), 512, 384)


def front(n):
    """Looking down the barrel: a star of 4-5 jets out of the flash hider + a hot core."""
    rng = random.Random(200 + n)
    reset()
    s = rng.random() * 50
    blob("Core", fire_volume("Core", HOT, 60, s, 8, 1.1, 0.6, 1.3), 0.3, 0.15, 0, -0.15)
    blob("Glow", fire_volume("Glow", ORANGE, 10, s + 4, 5, 1.8, 0.0, 1.8), 0.7, 0.34, 0, -0.35)
    prongs = rng.choice((4, 5))
    off = rng.uniform(0, 360)
    for k in range(prongs):
        ang = off + 360 * k / prongs + rng.uniform(-10, 10)
        ln = rng.uniform(0.32, 0.5)
        blob(f"P{k}", fire_volume(f"P{k}", YELLOW, 32, s + 9 + k, 9, 1.4, 0.2, 1.5), ln, rng.uniform(0.04, 0.06),
             ang, 0.04)
    camera(0, 0, 1.15)
    render(os.path.join(OUT, f"MuzzleFront{n}.png"), 256, 256)


def smoke(n):
    rng = random.Random(300 + n)
    reset(transparent=True)
    s = rng.random() * 50
    for k in range(3):
        blob(f"Puff{k}", smoke_volume(f"Puff{k}", s + k * 5, 7.0), rng.uniform(0.9, 1.3), rng.uniform(0.3, 0.42),
             rng.uniform(-25, 25), -0.55 + k * 0.08, tilt=rng.uniform(0, 90))
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 6.0
    sun.rotation_euler = (math.radians(50), math.radians(25), 0)
    bpy.context.scene.collection.objects.link(sun)
    camera(0, 0, 1.6)
    render(os.path.join(OUT, f"MuzzleSmoke{n}.png"), 256, 256)


def tracer():
    """A thin streak of light along +X: tail at x=0 (nothing) to head at x=4 (white-hot tip)."""
    reset()
    m = bpy.data.materials.new("Streak")
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.86, 0.62, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    nt.links.new(sep.outputs["X"], pw.inputs[0])
    pw.inputs[1].default_value = 2.2
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY"
    nt.links.new(pw.outputs[0], st.inputs[0])
    st.inputs[1].default_value = 40
    nt.links.new(st.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.006, radius2=0.022, depth=3.9)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((1.95, 0, 0)))
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.022)
    for v in bm.verts[-((12 * 7) + 2):]:
        v.co.x += 3.9
    me = bpy.data.meshes.new("Streak")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new("Streak", me)
    bpy.context.scene.collection.objects.link(ob)
    # warm haze around the hot head
    blob("Haze", fire_volume("Haze", YELLOW, 1.4, 3.0, 2.0, 2.2, 0.9, 1.0), 2.6, 0.09, 0, 1.45)
    camera(2.0, 0, 4.0)
    render(os.path.join(OUT, "Tracer.png"), 512, 64)


def preview():
    """Check every sprite was written (tools/weapon_fx_sprites.py --preview makes the contact sheet)."""
    files = [f"MuzzleSide{n}.png" for n in range(1, 5)] + ["MuzzleFront1.png", "MuzzleFront2.png",
                                                            "MuzzleSmoke1.png", "MuzzleSmoke2.png", "Tracer.png"]
    missing = [f for f in files if not os.path.exists(os.path.join(OUT, f))]
    print("missing:", missing) if missing else print("all", len(files), "sprites rendered")


for i in range(1, 5):
    side(i)
for i in range(1, 3):
    front(i)
for i in range(1, 3):
    smoke(i)
tracer()
preview()
print("done ->", OUT)
