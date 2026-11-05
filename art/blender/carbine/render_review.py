"""Re-render the 4 review images from carbine.blend and report GLB contents.
Run: blender --background C:\\out\\carbine\\carbine.blend --python render_review.py
"""
import bpy, os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

OUT = common.OUT
scene = bpy.context.scene
objs = [bpy.data.objects['Body'], bpy.data.objects['Magazine']]
for o in scene.objects:
    if o.type == 'EMPTY':
        o.hide_render = True
views = [(os.path.join(OUT, "renders", f"carbine_{k}.png"), v[0], v[1]) for k, v in common.STANDARD_VIEWS.items()]
common.render_views(scene, objs, views, samples=128)

with open(os.path.join(OUT, "carbine.glb"), "rb") as f:
    data = f.read()
ln = struct.unpack_from("<I", data, 12)[0]
gl = json.loads(data[20:20 + ln])
print("GLB nodes:", [n.get("name") for n in gl.get("nodes", [])])
print("GLB meshes:", [m.get("name") for m in gl.get("meshes", [])])
print("GLB images:", [(i.get("name"), i.get("mimeType"), "bufferView" in i) for i in gl.get("images", [])])
print("GLB materials:", [m.get("name") for m in gl.get("materials", [])])
