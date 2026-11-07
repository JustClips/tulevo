"""Shared bits for the superbike part scripts: looks, Blender materials, PNG saving and the GLB export.

Every part script builds its meshes in meters in bike coordinates (+X = bike's LEFT, -Y = front, +Z = up,
origin = ground between the axles) and calls export_model(), which writes art/models/<Model>/:
  <Model>.glb   meshes in studs (x3.6 baked in, Scale 1 in Roblox), placeholder materials, no images
  meta.json     tris per part + the Roblox look (Color / Material / Reflectance / Transparency) per part
  textures.json part -> colour map PNG (uploaded separately by tools/upload_textures.py)
"""
import json
import os
import struct

import bpy
import numpy as np
from mathutils import Matrix

import geo as G

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODELS = os.path.join(ROOT, "art", "models")
STUDS = 3.6
CREDIT = "Body shapes fitted to 'BMW S 1000 RR - HSLU Midterm 3DMOD4RT' by noe_auf (Sketchfab, CC-BY-4.0). Graphics are our own."

# paint shared with the fairings
WHITE = (238, 239, 242)
CHAR = (36, 38, 42)
ACCENT = (226, 64, 30)
GREY = (120, 123, 130)


def L_tex(tex, rough, refl=0.04, mat="SmoothPlastic", metal=0.0, coat=0.5):
    return {"tex": tex, "rough": rough, "metal": metal, "coat": coat,
            "roblox": {"Color": [255, 255, 255], "Material": mat, "Reflectance": refl}}


def L_col(rgb, rough, metal=0.0, mat="SmoothPlastic", refl=0.0, transp=0.0, emit=0.0, transmit=0.0, coat=0.0):
    r = {"Color": [int(c) for c in rgb], "Material": mat}
    if refl:
        r["Reflectance"] = refl
    if transp:
        r["Transparency"] = transp
    return {"color": tuple((c / 255.0) ** 2.2 for c in rgb), "rough": rough, "metal": metal, "emit": emit,
            "transmit": transmit, "coat": coat, "roblox": r}


def save_png(path, rgb):
    """rgb: (h, w, 3) sRGB values 0..1, row 0 = top of the image."""
    a = np.clip(rgb, 0, 1)
    h, w = a.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = a[::-1]
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def material(name, look, tex_path=None):
    m = bpy.data.materials.new("M_" + name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = look["rough"]
    b.inputs["Metallic"].default_value = look["metal"]
    if not look["metal"]:
        b.inputs["Specular IOR Level"].default_value = 0.4
    if look.get("tex"):
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex_path, check_existing=True)
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*look["color"], 1)
    if look.get("coat"):
        b.inputs["Coat Weight"].default_value = look["coat"]
        b.inputs["Coat Roughness"].default_value = 0.05
    if look.get("emit"):
        b.inputs["Emission Color"].default_value = (*look["color"], 1)
        b.inputs["Emission Strength"].default_value = look["emit"]
    if look.get("transmit"):
        b.inputs["Transmission Weight"].default_value = look["transmit"]
    return m


def look_for(name, looks):
    """Exact name, else the name without a trailing L / R (KneePadL -> KneePad)."""
    if name in looks:
        return looks[name]
    return looks[name[:-1]]


def apply_materials(parts, looks, texfiles, tex_dir):
    for name, ob in parts.items():
        L = look_for(name, looks)
        ob.data.materials.clear()
        tp = os.path.join(tex_dir, texfiles[L["tex"]]) if L.get("tex") else None
        ob.data.materials.append(material(name, L, tp))


def export_model(model, parts, looks, texfiles, credit=CREDIT, max_tris=20000, extra=None):
    """parts: {name: object in meters}. looks: name (or name minus L/R) -> look. texfiles: tex key -> file in tex/.
    extra: more keys for meta.json."""
    out = os.path.join(MODELS, model)
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: +X = bike's LEFT, -Y = front, +Z = up; origin = ground between the axles (bike layout).",
            "parts": {}, "looks": {}}
    if credit:
        meta["credit"] = credit
    meta.update(extra or {})
    texmap = {}
    for name, ob in parts.items():
        L = look_for(name, looks)
        meta["parts"][name] = {"tris": G.tris(ob)}
        meta["looks"][name] = L["roblox"]
        if L.get("texpath"):    # a colour map that already lives in another model's folder (assemble.py)
            texmap[name] = L["texpath"]
        elif L.get("tex"):
            texmap[name] = f"art/models/{model}/tex/{texfiles[L['tex']]}"
    meta["total_tris"] = sum(p["tris"] for p in meta["parts"].values())
    for o in bpy.context.selected_objects:
        o.select_set(False)
    copies = []
    for ob in parts.values():
        c = ob.copy()
        c.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.data.transform(ob.matrix_world)
        c.matrix_world = Matrix.Identity(4)
        c.data.transform(Matrix.Scale(STUDS, 4))
        c.name = ob.name + "_x"
        c.select_set(True)
        copies.append(c)
    path = os.path.join(out, f"{model}.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_materials='PLACEHOLDER',
                              export_apply=True, export_yup=True, export_texcoords=True, export_normals=True)
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)
    data = open(path, "rb").read()
    ln = struct.unpack_from("<I", data, 12)[0]
    gl = json.loads(data[20:20 + ln])
    assert not gl.get("images"), "GLB must not embed images"
    for nd in gl["nodes"]:
        nd["name"] = nd["name"].removesuffix("_x")
    for m in gl.get("meshes", []):
        m["name"] = m["name"].removesuffix("_x")
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + data[20 + ln:]
    open(path, "wb").write(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    json.dump(texmap, open(os.path.join(out, "textures.json"), "w"), indent=1)
    print(model, "tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})
    for k, v in meta["parts"].items():
        assert v["tris"] < max_tris, (k, v)
    return meta
