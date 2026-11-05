"""Re-export Hypercar.glb from the baked hypercar.blend with every texture capped at 1024 px
(Roblox's texture limit, so bigger images only make the upload heavier).

  blender --background --python reexport.py
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

bpy.ops.wm.open_mainfile(filepath=os.path.join(C.OUT, "hypercar.blend"))
for im in bpy.data.images:
    cap = 512 if any(t in im.name for t in ("Carbon_", "Leather_", "Perforated_", "Alcantara_", "BrushedAlu_", "Honeycomb_")) else 1024
    if im.size[0] > cap or im.size[1] > cap:
        im.scale(cap, cap)
        im.pack()
        print("scaled", im.name)
for o in bpy.context.scene.objects:
    o.select_set(o.type == 'MESH' and o.name not in ("Floor",))
bpy.ops.export_scene.gltf(filepath=os.path.join(C.OUT, "Hypercar.glb"), export_format='GLB', use_selection=True,
                          export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
                          export_materials='EXPORT', export_image_format='AUTO')
print("exported", os.path.getsize(os.path.join(C.OUT, "Hypercar.glb")))
