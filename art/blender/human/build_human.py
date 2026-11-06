"""RULE: no text, URLs, watermarks or credit marks in any shipped texture (Roblox moderation).

Build tulevo's realistic test human ("Marcus Vale", original) from CC0 MakeHuman assets.

Run (Blender 5.2, headless):
  blender --background --python build_human.py -- <data_dir> <out_dir> [--samples N] [--no-render]

data_dir holds base.obj, rig.default.json, weights.default.json, targets/*.target.gz and
assets/<proxy>/ (obj + mhclo + png). All of those are MakeHuman system assets (CC0).

Steps: shape the base mesh with targets -> fit eyes/brows/hair/clothes/shoes (mhclo) ->
cut hidden skin -> build the default rig from joint helpers -> pose (arms down, relaxed) ->
paint stubble/brows/hairline into the skin -> bake visible skin to its own 1024 maps ->
export a GLB in studs (Blender -Y = front) + preview renders + meta.json.
"""
import gzip
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DATA = os.path.abspath(argv[0] if argv else "data")
OUT = os.path.abspath(argv[1] if len(argv) > 1 else "out")
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 32
RENDER = "--no-render" not in argv
ASSETS = os.path.join(DATA, "assets")
os.makedirs(OUT, exist_ok=True)

HEIGHT_STUDS = 6.2  # final standing height in Roblox studs (1 m = 3.6 studs -> ~1.72 m look)

# ---------------------------------------------------------------- character recipe
# Original person: mixed heritage, late 20s, athletic. Not based on any game character.
RACE = {"african": 0.5, "caucasian": 0.42, "asian": 0.08}
MUSCLE = 0.8   # 0.5 avg .. 1 max
WEIGHT = 0.5   # 0 min .. 0.5 avg
HEIGHT = 0.5   # 0.5 avg .. 1 max
PROPORTION = 0.7
DETAIL = {
    "chin-prominent-incr": 0.35, "chin-width-incr": 0.35, "chin-bones-incr": 0.3, "head-square": 0.3,
    "nose-hump-incr": 0.2, "nose-scale-horiz-incr": 0.1, "nose-width1-incr": 0.15,
    "l-cheek-bones-incr": 0.35, "r-cheek-bones-incr": 0.35, "neck-scale-horiz-incr": 0.1,
    "torso-vshape-incr": 0.35, "torso-muscle-pectoral-incr": 0.3, "eyebrows-trans-down": 0.25,
    "mouth-scale-horiz-incr": 0.1,
}
SKIN_MIX = 0.42  # 0 = light skin texture, 1 = dark skin texture


# ---------------------------------------------------------------- MakeHuman file readers
def read_obj(path):
    vs, vts, faces, groups = [], [], [], {}
    g = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("g "):
                g = line.split()[1]
            elif line.startswith("f "):
                vi, ti = [], []
                for tok in line.split()[1:]:
                    p = tok.split("/")
                    vi.append(int(p[0]) - 1)
                    ti.append(int(p[1]) - 1 if len(p) > 1 and p[1] else -1)
                faces.append((vi, ti, g))
                groups.setdefault(g, set()).update(vi)
    return np.array(vs, dtype=np.float64), np.array(vts, dtype=np.float64), faces, groups


def read_target(name):
    path = os.path.join(DATA, "targets", name + ".target.gz")
    idx, d = [], []
    with gzip.open(path, "rt") as f:
        for line in f:
            p = line.split()
            if len(p) == 4 and not line.startswith("#"):
                idx.append(int(p[0]))
                d.append([float(x) for x in p[1:]])
    return np.array(idx, dtype=np.int64), np.array(d, dtype=np.float64).reshape(-1, 3)


def read_mhclo(path):
    refs, scales, delete = [], {}, []
    mode = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            p = s.split()
            if p[0] in ("x_scale", "y_scale", "z_scale"):
                scales[p[0][0]] = (int(p[1]), int(p[2]), float(p[3]))
                continue
            if p[0] == "verts":
                mode = "verts"
                continue
            if p[0] == "delete_verts":
                mode = "delete"
                continue
            if mode == "verts" and p[0][0].isdigit():
                if len(p) == 1:
                    refs.append(((int(p[0]),) * 3, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
                else:
                    refs.append(((int(p[0]), int(p[1]), int(p[2])), tuple(map(float, p[3:6])), tuple(map(float, p[6:9]))))
            elif mode == "delete" and p[0][0].isdigit():
                toks = s.replace("-", " - ").split()
                i = 0
                while i < len(toks):
                    if i + 2 < len(toks) and toks[i + 1] == "-":
                        delete.extend(range(int(toks[i]), int(toks[i + 2]) + 1))
                        i += 3
                    else:
                        delete.append(int(toks[i]))
                        i += 1
    return refs, scales, delete


def fit_proxy(refs, scales, base):
    """MakeHuman proxy fitting: weighted ref triangle + offset scaled by body measures (MH space)."""
    sc = np.ones(3)
    for ax, k in (("x", 0), ("y", 1), ("z", 2)):
        if ax in scales:
            a, b, den = scales[ax]
            sc[k] = abs(base[a][k] - base[b][k]) / den
    out = np.zeros((len(refs), 3))
    for i, (r, w, off) in enumerate(refs):
        out[i] = w[0] * base[r[0]] + w[1] * base[r[1]] + w[2] * base[r[2]] + np.array(off) * sc
    return out


def mh_to_blender(a):
    """MakeHuman (dm, Y up, +Z front) -> Blender metres (Z up, -Y front)."""
    a = np.asarray(a) * 0.1
    return np.stack([a[:, 0], -a[:, 2], a[:, 1]], axis=1)


# ---------------------------------------------------------------- shape the body
base_v, base_vt, base_f, base_groups = read_obj(os.path.join(DATA, "base.obj"))
shape = base_v.copy()


def add(name, w):
    if w <= 1e-4:
        return
    idx, d = read_target(name)
    shape[idx] += d * w


for race, w in RACE.items():
    add(f"{race}-male-young", w)
mu = (MUSCLE - 0.5) * 2  # share of maxmuscle
we = (0.5 - WEIGHT) * 2  # share of minweight
for m, wm in (("averagemuscle", 1 - mu), ("maxmuscle", mu)):
    for wt, ww in (("averageweight", 1 - we), ("minweight", we)):
        add(f"universal-male-young-{m}-{wt}", wm * ww)
    add(f"male-young-{m}-averageweight-maxheight", wm * (HEIGHT - 0.5) * 2)
    add(f"male-young-{m}-averageweight-idealproportions", wm * PROPORTION)
for name, w in DETAIL.items():
    add(name, w)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def make_mesh(name, verts_bl, faces, uvs, mat=None):
    """faces: list of (vert idx list, uv idx list)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts_bl], [], [f[0] for f in faces])
    uvl = me.uv_layers.new(name="UVMap")
    loop_uv = []
    for vi, ti in faces:
        for t in ti:
            loop_uv.extend(uvs[t] if t >= 0 else (0.0, 0.0))
    uvl.data.foreach_set("uv", loop_uv)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def img(path, color=True):
    im = bpy.data.images.load(path, check_existing=True)
    if not color:
        im.colorspace_settings.name = "Non-Color"
    return im


def pbr_mat(name, diffuse=None, normal=None, rough=0.6, alpha=False, color=(0.8, 0.8, 0.8, 1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Base Color"].default_value = color
    if diffuse:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = diffuse if isinstance(diffuse, bpy.types.Image) else img(diffuse)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha:
            nt.links.new(t.outputs["Alpha"], bsdf.inputs["Alpha"])
            m.blend_method = "CLIP" if hasattr(m, "blend_method") else None
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img(normal, color=False)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


# ---- proxies (fitted in MH space against the shaped body)
PROXIES = {
    "Clothes": ("male_casualsuit06", "male_casualsuit06_diffuse.png", None, 0.85, False),
    "Shoes": ("shoes05", "shoes05_diffuse.png", None, 0.55, False),
    "Hair": ("short02", "short02_diffuse.png", None, 0.7, True),
    "Brows": ("eyebrow001", "eyebrow001.png", None, 0.8, True),
    "Lashes": ("eyelashes01", "eyelashes01.png", None, 0.8, True),
    "Eyes": ("high-poly", "brown_eye.png", None, 0.15, False),
}
proxy_data = {}
deleted = set()
for key, (folder, diff, nrm, rough, alpha) in PROXIES.items():
    d = os.path.join(ASSETS, folder)
    refs, scales, dele = read_mhclo(os.path.join(d, folder + ".mhclo"))
    pv, pvt, pf, _ = read_obj(os.path.join(d, folder + ".obj"))
    fitted = fit_proxy(refs, scales, shape)
    if key in ("Clothes", "Shoes"):
        deleted.update(dele)
    proxy_data[key] = dict(v=fitted, vt=pvt, f=pf, refs=refs, folder=d, diff=diff, nrm=nrm, rough=rough, alpha=alpha)

# ---- body: only group "body", minus skin hidden under clothes/shoes
body_faces_all = [(vi, ti) for vi, ti, g in base_f if g == "body"]
body_faces = [f for f in body_faces_all if not any(v in deleted for v in f[0])]
used = sorted({v for f in body_faces for v in f[0]})
remap = {v: i for i, v in enumerate(used)}
body_bl = mh_to_blender(shape[used])
body_faces_r = [([remap[v] for v in vi], ti) for vi, ti in body_faces]

# blended skin texture (light <-> dark, same UV layout)


def load_px(path):
    im = img(path)
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(h, w, 4), im


light, _ = load_px(os.path.join(ASSETS, "young_lightskinned_male_diffuse.png"))
dark, _ = load_px(os.path.join(ASSETS, "young_darkskinned_male_diffuse.png"))
if dark.shape != light.shape:
    raise SystemExit(f"skin sizes differ {dark.shape} {light.shape}")
skin_px = light * (1 - SKIN_MIX) + dark * SKIN_MIX
SH, SW = skin_px.shape[:2]
print("skin texture", SW, SH)

# per-vertex paint masks (stubble / hairline) from 3D position on the shaped body
bv = mh_to_blender(shape)  # metres, all verts (incl helpers)
body_ids = np.array(sorted(base_groups["body"]))
zs = bv[body_ids, 2]
top = zs.max()
print("height m", top - zs.min())


def head_frame():
    eyes = [np.mean(bv[list(base_groups[g])], axis=0) for g in ("joint-l-eye", "joint-r-eye")]
    eye_c = (eyes[0] + eyes[1]) / 2
    return eye_c, abs(eyes[0][0] - eyes[1][0])


eye_c, eye_dist = head_frame()


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def paint_masks(P):
    """Return (stubble, hair) masks per vertex for points P (metres, blender space)."""
    rel = (P - eye_c) / eye_dist  # in "eye distance" units (~0.065 m)
    x, y, z = rel[:, 0], rel[:, 1], rel[:, 2]
    ax = np.abs(x)
    front = y < 0.4  # in front of the ears
    # stubble: jaw, chin, upper lip, cheeks below cheekbones; not lips (approx), fade on neck
    st = smooth(-0.55, -1.0, z) * smooth(1.55, 1.25, ax) * (front | (z < -1.6))
    st *= smooth(-2.6, -2.1, z)  # stop under the jaw
    lips = (ax < 0.55) & (z < -1.15) & (z > -1.75) & (y < -1.0)
    st = np.where(lips, st * 0.15, st)
    # hair (short fade / crop): scalp above the forehead line, sides above the ears
    hair = smooth(0.75, 1.15, z + 0.35 * smooth(0.0, 1.0, y + 0.3)) * smooth(-1.55, -1.25, y if True else y)
    hair = np.maximum(hair, smooth(0.15, 0.6, z) * smooth(0.0, 0.9, y - 0.6 * (1 - smooth(1.2, 1.6, ax))))
    neckback = smooth(-1.2, -0.4, z) * smooth(0.6, 1.2, y)
    hair = np.maximum(hair, neckback * 0.85)
    sideburn = smooth(1.15, 1.35, ax) * smooth(-0.4, 0.2, z) * smooth(0.9, 0.2, y) * smooth(-0.6, 0.0, y)
    hair = np.maximum(hair, sideburn * 0.9)
    return np.clip(st, 0, 1), np.clip(hair, 0, 1) * (rel[:, 2] > -2.2)


stub_v, hair_v = paint_masks(bv)


def raster(px, faces, uv, vals, color, strength, noise=None):
    """Paint color into px over UV triangles. The mask is built with max() first and blended once,
    so shared triangle edges never get painted twice (no grid lines)."""
    H, W = px.shape[:2]
    mask = np.zeros((H, W), dtype=np.float32)
    for vi, ti in faces:
        vv = vals[vi]
        if vv.max() < 0.02:
            continue
        tris = [(0, 1, 2)] if len(vi) == 3 else [(0, 1, 2), (0, 2, 3)]
        for a, b, c in tris:
            p = np.array([uv[ti[a]], uv[ti[b]], uv[ti[c]]]) * [W, H]
            q = np.array([vv[a], vv[b], vv[c]])
            x0, y0 = np.floor(p.min(0)).astype(int) - 1
            x1, y1 = np.ceil(p.max(0)).astype(int) + 1
            x0, y0 = max(x0, 0), max(y0, 0)
            x1, y1 = min(x1, W - 1), min(y1, H - 1)
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
            if abs(d) < 1e-9:
                continue
            l1 = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
            l2 = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= -0.08) & (l2 >= -0.08) & (l3 >= -0.08)
            if not inside.any():
                continue
            m = np.clip(l1 * q[0] + l2 * q[1] + l3 * q[2], 0, 1) * inside
            reg = mask[y0:y1 + 1, x0:x1 + 1]
            np.maximum(reg, m.astype(np.float32), out=reg)
    m = mask * strength
    if noise is not None:
        m = m * noise
    px[..., :3] = px[..., :3] * (1 - m[..., None]) + np.array(color, dtype=np.float32)[None, None, :] * m[..., None]


rng = np.random.default_rng(7)
grain = rng.random((SH, SW)).astype(np.float32)
stub_noise = 0.55 + 0.45 * grain
hair_noise = 0.55 + 0.45 * grain
body_uv = base_vt  # UVs in MH are (u, v) with v up; image rows start at bottom in Blender -> same
raster(skin_px, body_faces_all, body_uv, stub_v, (0.05, 0.038, 0.032), 0.55, stub_noise)
raster(skin_px, body_faces_all, body_uv, hair_v, (0.018, 0.014, 0.012), 0.93, hair_noise)

# eyebrows: draw the brow card texture into the skin via the brow's body reference triangles
brow = proxy_data["Brows"]
brow_px, _ = load_px(os.path.join(brow["folder"], brow["diff"]))
BH, BW = brow_px.shape[:2]
# UV of each brow vertex on the body = weighted ref-vertex UVs (first UV found for a vertex)
v2uv = {}
for vi, ti, g in base_f:
    if g == "body":
        for v, t in zip(vi, ti):
            v2uv.setdefault(v, base_vt[t])
buv = np.array([sum(w[k] * v2uv.get(r[k], np.zeros(2)) for k in range(3)) for r, w, _ in brow["refs"]])
for vi, ti, _ in brow["f"]:
    tris = [(0, 1, 2)] if len(vi) == 3 else [(0, 1, 2), (0, 2, 3)]
    for a, b, c in tris:
        dst = buv[[vi[a], vi[b], vi[c]]] * [SW, SH]
        src = brow["vt"][[ti[a], ti[b], ti[c]]] * [BW, BH]
        x0, y0 = np.floor(dst.min(0)).astype(int)
        x1, y1 = np.ceil(dst.max(0)).astype(int)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        p = dst
        dd = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(dd) < 1e-9:
            continue
        l1 = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / dd
        l2 = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / dd
        l3 = 1 - l1 - l2
        ins = (l1 >= -0.01) & (l2 >= -0.01) & (l3 >= -0.01)
        sx = np.clip((l1 * src[0, 0] + l2 * src[1, 0] + l3 * src[2, 0]).astype(int), 0, BW - 1)
        sy = np.clip((l1 * src[0, 1] + l2 * src[1, 1] + l3 * src[2, 1]).astype(int), 0, BH - 1)
        s = brow_px[sy, sx]
        al = s[..., 3] * ins * 0.95
        reg = skin_px[y0:y1 + 1, x0:x1 + 1, :3]
        al = np.minimum(al, 0.95)
        reg[:] = reg * (1 - al[..., None]) + np.array([0.02, 0.016, 0.014])[None, None, :] * al[..., None]

skin_img = bpy.data.images.new("SkinPainted", SW, SH, alpha=True)
skin_img.pixels.foreach_set(np.clip(skin_px, 0, 1).ravel())
skin_mat = pbr_mat("Skin", skin_img, rough=0.55)

body = make_mesh("Body", body_bl, body_faces_r, body_uv, skin_mat)

# proxies -> blender objects (eyebrows/hair painted into skin; keep only the crop hair shell low)
proxy_objs = {}
for key, p in proxy_data.items():
    if key in ("Brows", "Lashes"):
        continue
    mat = pbr_mat(key, os.path.join(p["folder"], p["diff"]),
                  os.path.join(p["folder"], p["nrm"]) if p["nrm"] else None, p["rough"], p["alpha"])
    faces = [(vi, ti) for vi, ti, g in p["f"]]
    if key == "Eyes":
        ea, _ = load_px(os.path.join(p["folder"], p["diff"]))
        eh, ew = ea.shape[:2]
        def alpha_at(ti):
            u, v = np.mean(p["vt"][ti], axis=0)
            return ea[min(int(v * eh), eh - 1), min(int(u * ew), ew - 1), 3]
        faces = [f for f in faces if alpha_at(f[1]) > 0.5]
    proxy_objs[key] = make_mesh(key, mh_to_blender(p["v"]), faces, p["vt"], mat)

# ---------------------------------------------------------------- rig (MakeHuman default skeleton)
rig_def = json.load(open(os.path.join(DATA, "rig.default.json")))
wdef = json.load(open(os.path.join(DATA, "weights.default.json")))["weights"]


def joint_pos(spec):
    s = spec["strategy"]
    if s == "CUBE":
        return np.mean(bv[list(base_groups[spec["cube_name"]])], axis=0)
    if s == "VERTEX":
        return bv[spec["vertex_index"]]
    return np.mean(bv[spec["vertex_indices"]], axis=0)


arm_data = bpy.data.armatures.new("Rig")
rig = bpy.data.objects.new("Rig", arm_data)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, b in rig_def.items():
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(joint_pos(b["head"]))
    eb.tail = Vector(joint_pos(b["tail"]))
    if (eb.tail - eb.head).length < 1e-4:
        eb.tail = eb.head + Vector((0, 0, 0.01))
    eb.roll = b["roll"]
for name, b in rig_def.items():
    if b["parent"]:
        arm_data.edit_bones[name].parent = arm_data.edit_bones[b["parent"]]
        arm_data.edit_bones[name].use_connect = b.get("use_connect", False)
bpy.ops.object.mode_set(mode="OBJECT")

# body weights
nb = len(base_v)
W = {bone: np.zeros(nb, dtype=np.float32) for bone in wdef}
for bone, lst in wdef.items():
    for vi, w in lst:
        W[bone][vi] = w


def bind(ob, vert_weights):
    for bone, arr in vert_weights.items():
        nz = np.nonzero(arr > 1e-4)[0]
        if not len(nz):
            continue
        vg = ob.vertex_groups.new(name=bone)
        for i in nz:
            vg.add([int(i)], float(arr[i]), "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    ob.parent = rig


bind(body, {b: a[used] for b, a in W.items()})
for key, ob in proxy_objs.items():
    refs = proxy_data[key]["refs"]
    R = np.array([r for r, _, _ in refs])
    Wt = np.array([w for _, w, _ in refs])
    bind(ob, {b: (a[R] * Wt).sum(1) for b, a in W.items()})

# ---------------------------------------------------------------- pose: relaxed standing
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"


def world_rot(bone, axis, deg):
    """Rotate a pose bone (with un-posed parents) about a world axis."""
    pb = rig.pose.bones[bone]
    M = pb.bone.matrix_local.to_3x3()
    q = Quaternion(axis, math.radians(deg)).to_matrix()
    pb.rotation_quaternion = (M.inverted() @ q @ M).to_quaternion()


def local_rot(bone, axis, deg):
    pb = rig.pose.bones[bone]
    pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(axis, math.radians(deg))


def rotw(bone, axis, deg):
    """Rotate a pose bone about a world axis through its head, respecting already-posed parents."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    m = pb.matrix.copy()
    r = Quaternion(Vector(axis).normalized(), math.radians(deg)).to_matrix()
    n = (r @ m.to_3x3()).to_4x4()
    n.translation = m.translation
    pb.matrix = n
    bpy.context.view_layer.update()


def head(bone):
    bpy.context.view_layer.update()
    return rig.pose.bones[bone].head.copy()


def tail(bone):
    bpy.context.view_layer.update()
    return rig.pose.bones[bone].tail.copy()


# GTA-style idle: shoulders relaxed, arms hanging straight beside the thighs, slight elbow bend,
# feet under the hips, head level.
def dbg(tag, side):
    print(tag, side, "elbow", tuple(round(c, 3) for c in head(f"lowerarm01.{side}")), "wrist", tuple(round(c, 3) for c in tail(f"lowerarm02.{side}")))


for side, sgn in (("L", 1), ("R", -1)):
    dbg("rest", side)
    rotw(f"clavicle.{side}", (0, 1, 0), sgn * 7)
    dbg("clav", side)
    d = (head(f"lowerarm01.{side}") - head(f"upperarm01.{side}")).normalized()
    ang = math.degrees(math.atan2(-d.z, abs(d.x)))
    rotw(f"upperarm01.{side}", (0, 1, 0), sgn * (87 - ang))
    dbg("down", side)
    rotw(f"upperarm01.{side}", (1, 0, 0), -5)  # hands a touch forward
    dbg("fwd", side)
    # elbow: the MakeHuman rest pose has the forearm bent ~45 deg forward. Straighten it to the
    # upper-arm direction plus a slight 12 deg forward bend.
    up = (head(f"lowerarm01.{side}") - head(f"upperarm01.{side}")).normalized()
    target = Quaternion(Vector((1, 0, 0)), math.radians(-12)) @ up
    cur = (tail(f"lowerarm02.{side}") - head(f"lowerarm01.{side}")).normalized()
    ax = cur.cross(target)
    if ax.length > 1e-6:
        rotw(f"lowerarm01.{side}", ax, math.degrees(cur.angle(target)))
    dbg("elbow", side)
    # palms toward the thighs, thumbs forward
    fa = (tail(f"lowerarm02.{side}") - head(f"lowerarm01.{side}")).normalized()
    rotw(f"lowerarm02.{side}", fa, sgn * 12)
    print(side, "wrist", tuple(round(c, 3) for c in tail(f"lowerarm02.{side}")),
          "hip", tuple(round(c, 3) for c in head(f"upperleg01.{side}")))

# legs: bring the feet in to roughly hip width
for side, sgn in (("L", 1), ("R", -1)):
    ank = head(f"foot.{side}")
    hip = head(f"upperleg01.{side}")
    want = 0.105  # metres from the centre line at the ankle
    off = abs(ank.x) - want
    if off > 0:
        deg = math.degrees(math.atan2(off, hip.z - ank.z))
        rotw(f"upperleg01.{side}", (0, 1, 0), sgn * deg)
        rotw(f"foot.{side}", (0, 1, 0), -sgn * deg)  # keep the sole flat
    print(side, "ankle x", round(head(f"foot.{side}").x, 3))

# fingers: soft natural curl
for side in ("L", "R"):
    for f in range(1, 6):
        for j in range(1, 4):
            n = f"finger{f}-{j}.{side}"
            if n in rig.pose.bones:
                local_rot(n, Vector((1, 0, 0)), (16 + 4 * j) if f > 1 else 8)
rotw("neck01", (1, 0, 0), 3)
# slight contrapposto: weight on right leg, head a touch down
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode="OBJECT")

# apply pose to meshes
meshes = [body] + list(proxy_objs.values())
for ob in meshes:
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="Armature")
    ob.parent = None
    ob.vertex_groups.clear()

# ---------------------------------------------------------------- stand on z=0, centre, scale to studs
zmin = min(min((ob.matrix_world @ v.co).z for v in ob.data.vertices) for ob in meshes)
allx = [v.co for ob in meshes for v in ob.data.vertices]
zmax = max(v.z for v in allx)
cx = (min(v.x for v in allx) + max(v.x for v in allx)) / 2
cy = np.mean([v.co.y for v in body.data.vertices])
S = HEIGHT_STUDS / (zmax - zmin)
for ob in meshes:
    me = ob.data
    for v in me.vertices:
        v.co = Vector(((v.co.x - cx) * S, (v.co.y - cy) * S, (v.co.z - zmin) * S))
# push the tee/jeans a hair outward so posed skin never pokes through the sleeves
cl = proxy_objs["Clothes"].data
cl.update()
for v in cl.vertices:
    v.co = v.co + v.normal * 0.03
print("final height studs", (zmax - zmin) * S, "metres look", (zmax - zmin))
rig.hide_render = True

# ---------------------------------------------------------------- split skin: Head and Arms, each with its own cropped 1024 map
TEX = 1024
tex_files = {}


def save_img(name, px):
    h, w = px.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=True)
    im.pixels.foreach_set(np.clip(px, 0, 1).astype(np.float32).ravel())
    if (w, h) != (TEX, TEX):
        im.scale(TEX, TEX)
    path = os.path.join(OUT, "tex", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    tex_files[name] = path
    return bpy.data.images.load(path, check_existing=False)


def repack_bake(ob, src_img, name):
    """Pack this part's UV islands to fill 0..1 and bake the skin colour into its own TEX map."""
    me = ob.data
    old = me.uv_layers[0]
    old.name = "Src"
    new = me.uv_layers.new(name="UVMap")
    me.uv_layers.active = new
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.006)
    bpy.ops.object.mode_set(mode="OBJECT")
    target = bpy.data.images.new(name, TEX, TEX, alpha=False)
    m = bpy.data.materials.new(name + "Bake")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "Src"
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = src_img
    em = nt.nodes.new("ShaderNodeEmission")
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(uvn.outputs["UV"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    tgt = nt.nodes.new("ShaderNodeTexImage")
    tgt.image = target
    nt.nodes.active = tgt
    me.materials.clear()
    me.materials.append(m)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 1
    scene.render.bake.margin = 8
    bpy.ops.object.bake(type="EMIT")
    path = os.path.join(OUT, "tex", name + ".png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    target.filepath_raw = path
    target.file_format = "PNG"
    target.save()
    tex_files[name] = path
    me.uv_layers.remove(me.uv_layers["Src"])
    me.materials.clear()
    me.materials.append(pbr_mat(name, target, rough=0.5))


bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = body
body.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
neck_z = HEIGHT_STUDS * 0.80
for poly in body.data.polygons:
    poly.select = poly.center.z > neck_z
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
head = [o for o in bpy.context.selected_objects if o != body][0]
head.name = "Head"
body.name = "Arms"
repack_bake(head, skin_img, "Head")
repack_bake(body, skin_img, "Arms")
meshes = [head, body] + list(proxy_objs.values())

# clothes / shoes / hair / eyes colour maps at 1024 for Roblox
for key, ob in proxy_objs.items():
    p = proxy_data[key]
    px, _ = load_px(os.path.join(p["folder"], p["diff"]))
    if key == "Hair":
        px = px.copy()
        px[..., 3] = 1.0
    save_img(key, px)
    if key in ("Hair", "Clothes", "Shoes", "Eyes"):
        ob.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 1.0

meta = {"parts": {}, "height": HEIGHT_STUDS}
for ob in meshes:
    ob.data.calc_loop_triangles()
    meta["parts"][ob.name] = len(ob.data.loop_triangles)
meta["tris"] = sum(meta["parts"].values())
print("tris", meta)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)


meta["textures"] = {k: os.path.relpath(v, OUT) for k, v in tex_files.items()}
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Human.blend"))
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Human.glb"), export_format="GLB", use_selection=True,
                          export_apply=True, export_image_format="JPEG", export_jpeg_quality=92)
print("exported", os.path.join(OUT, "Human.glb"))

# ---------------------------------------------------------------- preview renders
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
    except Exception as e:  # CPU fallback
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
    floor = bpy.data.meshes.new("Floor")
    floor.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    fo = bpy.data.objects.new("Floor", floor)
    fo.data.materials.append(pbr_mat("FloorM", color=(0.35, 0.35, 0.36, 1), rough=0.9))
    scene.collection.objects.link(fo)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    H = HEIGHT_STUDS

    def shot(name, pos, target, lens):
        cam.location = Vector(pos)
        cam.data.lens = lens
        d = Vector(target) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)

    shot("front", (0, -22, H * 0.55), (0, 0, H * 0.5), 50)
    shot("front34", (12, -17, H * 0.6), (0, 0, H * 0.5), 50)
    shot("back34", (-12, 17, H * 0.6), (0, 0, H * 0.5), 50)
    shot("face", (1.2, -4.2, H * 0.93), (0, 0, H * 0.92), 85)
