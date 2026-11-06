"""Weather meshes for tulevo: drifting sky clouds + rain splash pieces.

    blender --background --python art/blender/weather/build_weather.py -- [OUT_DIR] [--render]
    (or: python3 art/blender/weather/build_weather.py  with `pip install bpy==5.2.3`)

Writes OUT_DIR/WeatherMeshes.glb (default art/models/WeatherMeshes/) with one mesh per object:
  Cumulus1..5     fair-weather cumulus: big rounded base lobes, cauliflower tops, flat base
  Congestus       a taller towering cumulus for the odd big one
  Strato1..2      long low lumpy stratocumulus for overcast / rain skies
  RainCrown       the crown a drop throws up when it hits the ground
  RainRipple      a thin ring that spreads on wet ground
Units: 1 m = 1 stud. Clouds are built about 10 studs long with the base at z = 0 (the game
scales them to hundreds of studs). Splash pieces are ~1 stud wide. No textures: the game
colours them, and Roblox lighting shades the cloud bottoms.
"""
import math
import os
import random
import sys

import bpy  # noqa: I001 (bpy first: the pip build only exposes bmesh after it)
import bmesh
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in argv if not a.startswith("--")), os.path.join(ROOT, "art", "models", "WeatherMeshes"))
RENDER = "--render" in argv


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.metaballs, bpy.data.materials):
        for item in list(coll):
            coll.remove(item)


def material(name, color=(1, 1, 1, 1)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.95
    mat.diffuse_color = color
    return mat


# ------------------------------------------------------------------ clouds

def cloud_puffs(rng, length, height, depth, lobes, tower=0.0):
    """(x, y, z, r) puffs: base lobes along X, a crown on top, then many small bumps over the
    upper surface so the top reads as cauliflower and the outline is never a smooth blob."""
    puffs = []
    for i in range(lobes):
        t = (i + 0.5) / lobes
        x = (t - 0.5) * length + rng.uniform(-0.3, 0.3)
        mid = 1 - abs(t - 0.5) * 2  # 1 in the middle, 0 at the ends
        r = (0.7 + 0.45 * mid) * height * rng.uniform(0.8, 1.1)
        puffs.append((x, rng.uniform(-0.25, 0.25) * depth, r * 0.75, r))
        if rng.random() < 0.7:  # a second row so it's not a sausage
            puffs.append((x + rng.uniform(-0.5, 0.5), rng.choice((-1, 1)) * depth * rng.uniform(0.25, 0.4),
                          r * 0.6, r * rng.uniform(0.6, 0.85)))
    # crown: a few big puffs riding on the middle
    for _ in range(2 + int(tower * 3)):
        x = rng.uniform(-0.25, 0.25) * length
        r = height * rng.uniform(0.6, 0.85)
        top = height * (1.0 + tower * rng.uniform(0.6, 1.4))
        # fill the column under it so a tall crown never floats on a thin neck
        z = height * 0.9
        while z < top:
            puffs.append((x * (z / top), rng.uniform(-0.15, 0.15) * depth, z, r * 1.05))
            z += r * 0.8
        puffs.append((x, rng.uniform(-0.2, 0.2) * depth, top, r))
    big = list(puffs)
    # cauliflower bumps on the upper half of every big puff
    for x, y, z, r in big:
        for _ in range(int(6 + r * 7)):
            th = rng.uniform(0, 2 * math.pi)
            ph = rng.uniform(0.05, 1.25)  # from the top down to a bit below the equator
            d = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
            rr = r * rng.uniform(0.32, 0.5)
            p = Vector((x, y, z)) + d * r * 0.72
            puffs.append((p.x, p.y, p.z, rr))
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


def build_cloud(name, puffs, mat, seed, flat=0.3, target_tris=3200, res=0.16):
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = res
    mb.render_resolution = res
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
    bpy.data.metaballs.remove(mb)

    bm = bmesh.new()
    bm.from_mesh(me)
    drop_islands(bm)
    # organic wobble: push verts along their normal with 3D noise (bigger up top)
    bm.normal_update()
    off = Vector((seed * 7.3, seed * 3.1, seed * 1.7))
    for v in bm.verts:
        n1 = noise.noise(v.co * 0.9 + off)
        n2 = noise.noise(v.co * 2.6 + off * 2)
        up = max(0.0, v.normal.z)
        v.co += v.normal * (n1 * 0.12 + n2 * 0.05) * (0.4 + 0.6 * up)
    # flat-ish base: squash everything under `flat` onto a gently bumpy plane
    for v in bm.verts:
        if v.co.z < flat:
            v.co.z = flat + (v.co.z - flat) * 0.08 + noise.noise(v.co * 0.7 + off) * 0.04
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    bm.to_mesh(me)
    bm.free()
    me.name = name
    out = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(out)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    if tris > target_tris:
        dec = out.modifiers.new("dec", "DECIMATE")
        dec.ratio = target_tris / tris
        bpy.context.view_layer.objects.active = out
        out.select_set(True)
        bpy.ops.object.modifier_apply(modifier=dec.name)
        out.select_set(False)
    return out


CLOUDS = [
    # name, seed, length, height, depth, lobes, tower, flat
    ("Cumulus1", 1, 10.0, 2.4, 5.0, 5, 0.3, 0.45),
    ("Cumulus2", 2, 8.0, 2.2, 4.5, 4, 0.2, 0.4),
    ("Cumulus3", 3, 12.0, 2.6, 5.5, 6, 0.4, 0.5),
    ("Cumulus4", 4, 6.5, 1.9, 4.0, 3, 0.1, 0.35),
    ("Cumulus5", 5, 9.0, 2.0, 6.0, 5, 0.25, 0.4),
    ("Congestus", 6, 9.0, 3.0, 6.0, 4, 1.4, 0.55),
]
STRATO = [("Strato1", 11, 16.0, 1.3, 9.0, 9), ("Strato2", 12, 14.0, 1.1, 10.0, 8)]


def strato_puffs(rng, length, height, depth, lobes):
    puffs = []
    for i in range(lobes):
        for j in range(4):
            x = ((i + rng.uniform(0.3, 0.7)) / lobes - 0.5) * length
            y = ((j + rng.uniform(0.3, 0.7)) / 4 - 0.5) * depth
            r = height * rng.uniform(1.5, 1.9)
            puffs.append((x, y, -r * 0.2, r))
    big = list(puffs)
    for x, y, z, r in big:
        for _ in range(3):
            th = rng.uniform(0, 2 * math.pi)
            ph = rng.uniform(0.1, 0.9)
            d = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
            p = Vector((x, y, z)) + d * r * 0.7
            puffs.append((p.x, p.y, p.z, r * rng.uniform(0.4, 0.55)))
    return puffs


# ------------------------------------------------------------------ splash pieces

def ring(r, z, n, phase=0.0):
    return [Vector((r * math.cos(2 * math.pi * (i + phase) / n), r * math.sin(2 * math.pi * (i + phase) / n), z))
            for i in range(n)]


def bridge(bm, a, b):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))


def build_crown(mat):
    """A thin flared cup with spiky tips and a droplet on most tips. ~1 stud across, 0.6 tall."""
    rng = random.Random(42)
    bm = bmesh.new()
    n = 24
    rows = [(0.18, 0.0), (0.26, 0.12), (0.36, 0.3), (0.44, 0.46)]
    outer = [[bm.verts.new(v) for v in ring(r, z, n)] for r, z in rows]
    inner = [[bm.verts.new(v) for v in ring(r - 0.03, z + 0.01, n)] for r, z in rows]
    tips_o, tips_i = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        spike = i % 2 == 0
        h = 0.62 + (rng.uniform(0.0, 0.14) if spike else -0.04)
        r = 0.5 + (0.05 if spike else 0.02)
        tips_o.append(bm.verts.new((r * math.cos(a), r * math.sin(a), h)))
        tips_i.append(bm.verts.new(((r - 0.025) * math.cos(a), (r - 0.025) * math.sin(a), h - 0.01)))
    outer.append(tips_o)
    inner.append(tips_i)
    for k in range(len(outer) - 1):
        bridge(bm, outer[k], outer[k + 1])
        bridge(bm, inner[k + 1], inner[k])
    bridge(bm, outer[-1], inner[-1])  # rim
    bridge(bm, inner[0], outer[0])  # bottom lip
    # droplets thrown off the tips
    for i in range(0, n, 2):
        if rng.random() < 0.7:
            a = 2 * math.pi * i / n
            r = 0.58 + rng.uniform(0, 0.08)
            c = Vector((r * math.cos(a), r * math.sin(a), 0.78 + rng.uniform(0, 0.12)))
            res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.035)
            for v in res["verts"]:
                v.co += c
    me = bpy.data.meshes.new("RainCrown")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("RainCrown", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build_ripple(mat):
    """A flat thin ring (0.5 radius, slight rounded lip) lying on the ground."""
    bm = bmesh.new()
    n = 40
    prof = [(0.44, 0.0), (0.47, 0.012), (0.5, 0.016), (0.53, 0.012), (0.56, 0.0)]
    rows = [[bm.verts.new(v) for v in ring(r, z, n)] for r, z in prof]
    for k in range(len(rows) - 1):
        bridge(bm, rows[k], rows[k + 1])
    me = bpy.data.meshes.new("RainRipple")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("RainRipple", me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


# ------------------------------------------------------------------ export / preview

def export(path, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_materials="EXPORT")


def render(path, objs):
    scene = bpy.context.scene
    # lay everything out in a row for the preview, then put it back
    xs = 0.0
    saved = []
    for o in objs:
        w = o.dimensions.x
        saved.append(o.location.copy())
        sc = 1.0 if o.name.startswith(("Cum", "Con", "Str")) else 4.0
        o.scale = (sc, sc, sc)
        o.location = (xs + w * sc / 2, 0, 0)
        xs += w * sc + 2
    bpy.context.view_layer.update()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.location = (xs / 2, -xs * 0.95, 1.5)
    cam.rotation_euler = (math.radians(91), 0, 0)
    cam.data.lens = 50
    scene.camera = cam
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(40), math.radians(20), math.radians(30))
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.55, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.device = "CPU"
    scene.render.resolution_x, scene.render.resolution_y = 1600, 400
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o, loc in zip(objs, saved):
        o.location = loc
        o.scale = (1, 1, 1)


def main():
    clear()
    os.makedirs(OUT, exist_ok=True)
    cloud_mat = material("CloudWhite")
    fx_mat = material("RainWater", (0.85, 0.9, 1.0, 1))
    objs = []
    for name, seed, length, height, depth, lobes, tower, flat in CLOUDS:
        rng = random.Random(seed)
        objs.append(build_cloud(name, cloud_puffs(rng, length, height, depth, lobes, tower), cloud_mat, seed, flat))
    for name, seed, length, height, depth, lobes in STRATO:
        rng = random.Random(seed)
        objs.append(build_cloud(name, strato_puffs(rng, length, height, depth, lobes), cloud_mat, seed, 0.3, 3600))
    objs.append(build_crown(fx_mat))
    objs.append(build_ripple(fx_mat))
    for o in objs:
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        d = o.dimensions
        print(f"{o.name:10} {tris:6} tris  {d.x:.1f} x {d.y:.1f} x {d.z:.1f}")
    export(os.path.join(OUT, "WeatherMeshes.glb"), objs)
    print("wrote", os.path.join(OUT, "WeatherMeshes.glb"))
    if RENDER:
        render(os.path.join(OUT, "preview.png"), objs)


main()
