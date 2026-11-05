"""UV unwrap, bake PBR maps, swap to baked materials, export GLB/meta/renders.

Run after build_model.py:
  blender --background --python bake_export.py
"""
import bpy, os, sys, json, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

OUT = common.OUT
TEX = os.path.join(OUT, "textures")
REN = os.path.join(OUT, "renders")
os.makedirs(TEX, exist_ok=True); os.makedirs(REN, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "carbine_model.blend"))
scene = bpy.context.scene
common.enable_gpu(scene)
body = bpy.data.objects['Body']; mag = bpy.data.objects['Magazine']
EMPTIES = ['Grip', 'Grip2', 'Muzzle', 'Sight', 'MagWell']

# world used for the AO bake (short distance -> local contact occlusion)
w = bpy.data.worlds.new("BakeWorld"); scene.world = w
w.light_settings.distance = 0.025


def only_select(ob):
    for o in scene.objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob


def unwrap(ob):
    only_select(ob)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_obj(ob, prefix, res):
    only_select(ob)
    imgs = {}
    for ch, noncolor in (('Color', False), ('Normal', True), ('Roughness', True), ('Metalness', True), ('AO', True)):
        im = bpy.data.images.new(f"{prefix}_{ch}_bake", res, res, alpha=False)
        if noncolor:
            im.colorspace_settings.name = 'Non-Color'
        imgs[ch] = im
    mats = [s.material for s in ob.material_slots if s.material]

    def target(im):
        for m in mats:
            nt = m.node_tree
            n = nt.nodes.get('BAKE_IMG') or nt.nodes.new('ShaderNodeTexImage')
            n.name = 'BAKE_IMG'; n.image = im
            for x in nt.nodes:
                x.select = False
            n.select = True; nt.nodes.active = n

    bk = scene.render.bake
    bk.margin = 16; bk.margin_type = 'EXTEND'; bk.use_clear = True

    target(imgs['Normal']); scene.cycles.samples = 48
    bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
    target(imgs['AO']); scene.cycles.samples = 192
    bpy.ops.object.bake(type='AO')

    for ch, inp in (('Color', 'Base Color'), ('Roughness', 'Roughness'), ('Metalness', 'Metallic')):
        saved = []
        for m in mats:
            nt = m.node_tree; b = nt.nodes['BSDF']; out = nt.nodes['Material Output']
            em = nt.nodes.new('ShaderNodeEmission'); em.name = 'BAKE_EM'
            i = b.inputs[inp]
            if i.is_linked:
                nt.links.new(i.links[0].from_socket, em.inputs['Color'])
            else:
                v = i.default_value
                em.inputs['Color'].default_value = tuple(v) if hasattr(v, '__len__') else (v, v, v, 1)
            nt.links.new(em.outputs[0], out.inputs['Surface'])
            saved.append((nt, b, out, em))
        target(imgs[ch]); scene.cycles.samples = 32
        bpy.ops.object.bake(type='EMIT')
        for nt, b, out, em in saved:
            nt.links.new(b.outputs[0], out.inputs['Surface']); nt.nodes.remove(em)

    # fold AO lightly into the base color (in linear space)
    def arr(im):
        return np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
    col = arr(imgs['Color']); ao = arr(imgs['AO'])[:, :1]
    lin = np.where(col[:, :3] <= 0.04045, col[:, :3] / 12.92, ((col[:, :3] + 0.055) / 1.055) ** 2.4)
    lin *= 1.0 - 0.6 * (1.0 - np.clip(ao, 0, 1))
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    col[:, :3] = np.clip(srgb, 0, 1); col[:, 3] = 1.0
    imgs['Color'].pixels[:] = col.ravel()

    paths = {}
    for ch in ('Color', 'Normal', 'Roughness', 'Metalness'):
        p = os.path.join(TEX, f"{prefix}_{ch}.png")
        im = imgs[ch]; im.filepath_raw = p; im.file_format = 'PNG'; im.save()
        paths[ch] = p
    for m in mats:
        n = m.node_tree.nodes.get('BAKE_IMG')
        if n:
            m.node_tree.nodes.remove(n)
        m.use_fake_user = True          # keep detail materials in the .blend for re-baking
    for im in imgs.values():
        bpy.data.images.remove(im)
    return paths


def final_material(ob, name, paths):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']

    def img(ch, noncolor, x):
        n = N.new('ShaderNodeTexImage'); n.location = (-600, x)
        n.image = bpy.data.images.load(paths[ch], check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = 'Non-Color'
        return n
    L.new(img('Color', False, 300).outputs['Color'], b.inputs['Base Color'])
    L.new(img('Roughness', True, 0).outputs['Color'], b.inputs['Roughness'])
    L.new(img('Metalness', True, -300).outputs['Color'], b.inputs['Metallic'])
    nm = N.new('ShaderNodeNormalMap'); nm.location = (-250, -600)
    L.new(img('Normal', True, -600).outputs['Color'], nm.inputs['Color'])
    L.new(nm.outputs['Normal'], b.inputs['Normal'])
    ob.data.materials.clear(); ob.data.materials.append(m)
    ob.data.polygons.foreach_set('material_index', [0] * len(ob.data.polygons))
    ob.data.update()


unwrap(body); unwrap(mag)
pb = bake_obj(body, "Carbine", 2048)
pm = bake_obj(mag, "Magazine", 1024)
final_material(body, "Carbine_Mat", pb)
final_material(mag, "Magazine_Mat", pm)
scene.world = None
bpy.data.worlds.remove(w)

# ---------------------------------------------------------------- export
for o in scene.objects:
    o.select_set(o.name in ['Body', 'Magazine'] + EMPTIES)
bpy.context.view_layer.objects.active = body
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "carbine.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


lo, hi = common.mesh_bbox([body, mag])
meta = {
    "units": "meters",
    "axes": "Blender coords: -Y = muzzle/forward, +Z = up, +X = right side. GLB is exported +Y up, so glTF = (x, z, -y).",
    "origin": "pistol grip hold point (right hand)",
    "empties": {},
    "triangles": {"Body": tris(body), "Magazine": tris(mag)},
    "size_m": {"x_width": round(hi.x - lo.x, 4), "y_length": round(hi.y - lo.y, 4), "z_height": round(hi.z - lo.z, 4)},
    "bbox_m": {"min": [round(v, 4) for v in lo], "max": [round(v, 4) for v in hi]},
    "textures": {"Body": {k: os.path.basename(v) for k, v in pb.items()},
                 "Magazine": {k: os.path.basename(v) for k, v in pm.items()}},
}
for n in EMPTIES:
    e = bpy.data.objects[n]
    meta["empties"][n] = {"location": [round(v, 4) for v in e.location],
                          "rotation_euler_deg_XYZ": [round(math.degrees(v), 2) for v in e.rotation_euler]}
meta["empties"]["Grip"]["note"] = "rotated +18 deg about X so local +Z runs up the grip axis"
meta["empties"]["Muzzle"]["note"] = "tip of flash hider; fire direction is -Y"
meta["empties"]["Sight"]["note"] = "rear center of the reflex sight window; aim along -Y"
meta["empties"]["MagWell"]["note"] = "top center of the magazine where it seats; Magazine mesh is placed here"
with open(os.path.join(OUT, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print(json.dumps(meta, indent=2))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "carbine.blend"))

# ---------------------------------------------------------------- review renders
views = [(os.path.join(REN, f"carbine_{k}.png"), v[0], v[1]) for k, v in common.STANDARD_VIEWS.items()]
for e in EMPTIES:
    bpy.data.objects[e].hide_render = True
common.render_views(scene, [body, mag], views, samples=128)
