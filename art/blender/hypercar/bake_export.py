"""UV unwrap, bake colour/roughness/metalness (+AO folded into colour), export GLB, meta, renders.

Run after build_model.py:
  blender --background --python bake_export.py
Writes OUT/Hypercar.glb, OUT/meta.json, OUT/textures/*, OUT/renders/*.
"""
import bpy, os, sys, json, math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

OUT = C.OUT
TEX = os.path.join(OUT, "textures")
REN = os.path.join(OUT, "renders")
os.makedirs(TEX, exist_ok=True)
os.makedirs(REN, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "hypercar_model.blend"))
scene = bpy.context.scene
C.enable_gpu(scene)

RES = {"Body_Front": 2048, "Body_Mid": 2048, "Body_Rear": 2048, "Trim": 2048, "Interior": 1024, "Door_L": 1024, "Door_R": 1024, "SteeringWheel": 512,
       "Pedal_Gas": 128, "Pedal_Brake": 128}
for w in ("FL", "FR", "RL", "RR"):
    RES[f"Wheel_{w}"] = 1024
    RES[f"Caliper_{w}"] = 128
PARTS = list(RES) + ["Glass"]

bw = bpy.data.worlds.new("BakeWorld")
scene.world = bw
bw.light_settings.distance = 0.25


def only_select(ob):
    for o in scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def unwrap(ob):
    only_select(ob)
    while ob.data.uv_layers:
        ob.data.uv_layers.remove(ob.data.uv_layers[0])
    ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake_obj(ob, res):
    only_select(ob)
    imgs = {}
    for ch, noncolor in (('Color', False), ('Roughness', True), ('Metalness', True), ('AO', True)):
        im = bpy.data.images.new(f"{ob.name}_{ch}_bake", res, res, alpha=False)
        if noncolor:
            im.colorspace_settings.name = 'Non-Color'
        imgs[ch] = im
    mats = [s.material for s in ob.material_slots if s.material]

    def target(im):
        for m in mats:
            nt = m.node_tree
            n = nt.nodes.get('BAKE_IMG') or nt.nodes.new('ShaderNodeTexImage')
            n.name = 'BAKE_IMG'
            n.image = im
            for x in nt.nodes:
                x.select = False
            n.select = True
            nt.nodes.active = n

    bk = scene.render.bake
    bk.margin = 8
    bk.margin_type = 'EXTEND'
    bk.use_clear = True
    target(imgs['AO'])
    scene.cycles.samples = 96
    bpy.ops.object.bake(type='AO')
    for ch, inp in (('Color', 'Base Color'), ('Roughness', 'Roughness'), ('Metalness', 'Metallic')):
        saved = []
        for m in mats:
            nt = m.node_tree
            b = nt.nodes['BSDF']
            out = nt.nodes['Material Output']
            em = nt.nodes.new('ShaderNodeEmission')
            em.name = 'BAKE_EM'
            i = b.inputs[inp]
            if i.is_linked:
                nt.links.new(i.links[0].from_socket, em.inputs['Color'])
            else:
                v = i.default_value
                em.inputs['Color'].default_value = tuple(v) if hasattr(v, '__len__') else (v, v, v, 1)
            nt.links.new(em.outputs[0], out.inputs['Surface'])
            saved.append((nt, b, out, em))
        target(imgs[ch])
        scene.cycles.samples = 4
        bpy.ops.object.bake(type='EMIT')
        for nt, b, out, em in saved:
            nt.links.new(b.outputs[0], out.inputs['Surface'])
            nt.nodes.remove(em)

    def arr(im):
        return np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
    col = arr(imgs['Color'])
    ao = arr(imgs['AO'])[:, :1]
    lin = np.where(col[:, :3] <= 0.04045, col[:, :3] / 12.92, ((col[:, :3] + 0.055) / 1.055) ** 2.4)
    lin *= 1.0 - 0.55 * (1.0 - np.clip(ao, 0, 1))
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    col[:, :3] = np.clip(srgb, 0, 1)
    col[:, 3] = 1.0
    imgs['Color'].pixels[:] = col.ravel()

    paths = {}
    for ch in ('Color', 'Roughness', 'Metalness'):
        p = os.path.join(TEX, f"{ob.name}_{ch}.png")
        im = imgs[ch]
        im.filepath_raw = p
        im.file_format = 'PNG'
        im.save()
        paths[ch] = p
    for m in mats:
        n = m.node_tree.nodes.get('BAKE_IMG')
        if n:
            m.node_tree.nodes.remove(n)
    for im in imgs.values():
        bpy.data.images.remove(im)
    return paths


def final_material(ob, paths):
    m = bpy.data.materials.new(f"{ob.name}_Mat")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    b = N['Principled BSDF']

    def img(ch, noncolor, y):
        n = N.new('ShaderNodeTexImage')
        n.location = (-600, y)
        n.image = bpy.data.images.load(paths[ch], check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = 'Non-Color'
        return n
    L.new(img('Color', False, 300).outputs['Color'], b.inputs['Base Color'])
    L.new(img('Roughness', True, 0).outputs['Color'], b.inputs['Roughness'])
    L.new(img('Metalness', True, -300).outputs['Color'], b.inputs['Metallic'])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    ob.data.polygons.foreach_set('material_index', [0] * len(ob.data.polygons))
    ob.data.update()


textures = {}
for name, res in RES.items():
    ob = bpy.data.objects[name]
    unwrap(ob)
    p = bake_obj(ob, res)
    final_material(ob, p)
    textures[name] = {k: os.path.basename(v) for k, v in p.items()}
    print("baked", name)
scene.world = None
bpy.data.worlds.remove(bw)

# ---------------------------------------------------------------- export
for o in scene.objects:
    o.select_set(o.name in PARTS)
bpy.context.view_layer.objects.active = bpy.data.objects["Body_Mid"]
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "Hypercar.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def bbox(ob):
    xs = [v.co for v in ob.data.vertices]
    lo = [min(v[i] for v in xs) for i in range(3)]
    hi = [max(v[i] for v in xs) for i in range(3)]
    return lo, hi


meta = {
    "units": "meters (x3.6 = studs)",
    "axes": "Blender: -Y = front, +Z = up, +X = car's LEFT (driver side). Roblox car space = (-x, z, y).",
    "origin": "ground, centred between the axles",
    "parts": {},
    "pivots": {
        "SteeringWheel": {"center": list(C.STEER_CENTER), "axis_toward_driver": [round(v, 4) for v in C.STEER_AXIS]},
        "Pedal_Gas": {"pivot": [C.PEDAL_GAS_X, C.PEDAL_PIVOT_Y, C.PEDAL_PIVOT_Z], "axis": [1, 0, 0]},
        "Pedal_Brake": {"pivot": [C.PEDAL_BRAKE_X, C.PEDAL_PIVOT_Y, C.PEDAL_PIVOT_Z], "axis": [1, 0, 0]},
        "Door_L": {"hinge": list(C.DOOR_HINGE), "axis": [0, 0, 1]},
        "Door_R": {"hinge": [-C.DOOR_HINGE.x, C.DOOR_HINGE.y, C.DOOR_HINGE.z], "axis": [0, 0, 1]},
        "Seat": list(C.SEAT),
    },
    "wheels": {k: [round(c, 4) for c in v] for k, v in C.WHEELS.items()},
    "wheel_radius": C.WHEEL_R,
    "textures": textures,
}
total = 0
for n in PARTS:
    ob = bpy.data.objects[n]
    lo, hi = bbox(ob)
    t = tris(ob)
    total += t
    meta["parts"][n] = {"tris": t, "bbox_min": [round(v, 4) for v in lo], "bbox_max": [round(v, 4) for v in hi]}
meta["total_tris"] = total
with open(os.path.join(OUT, "meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
print("total tris", total)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "hypercar.blend"))

# ---------------------------------------------------------------- review renders (baked materials)
g = bpy.data.objects["Glass"]
C.setup_studio(scene)
for k, (loc, tgt, lens) in C.VIEWS.items():
    C.render(scene, os.path.join(REN, f"hypercar_{k}.png"), loc, tgt, lens, samples=96, res=(1600, 900))
