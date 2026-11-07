"""Render preview.png for each built wheel (run after wheels.py).

  python3 art/blender/superbike/render.py [front] [rear]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
NAMES = {"front": "BikeWheelFront", "rear": "BikeWheelRear", "bike": "Superbike", "exhaust": "BikeExhaust", "chain": "BikeChain", "seats": "BikeSeats", "fairings": "BikeFairings", "tank": "BikeTank", "tail": "BikeTail", "chassis": "BikeChassis", "frontend": "BikeFront", "engine": "BikeEngine"}


# camera shots per part: (tag, camera, target, lens). Parts sit in bike coordinates.
VIEWS = {
    "exhaust": [("q34", (-0.95, -0.95, 0.75), (-0.05, -0.05, 0.30), 45), ("side", (-1.45, 0.05, 0.38), (-0.05, 0.05, 0.33), 45),
                ("front", (0.35, -1.25, 0.42), (0.0, -0.32, 0.36), 55), ("rear", (-0.75, 1.15, 0.62), (-0.18, 0.42, 0.32), 40)],
    "chain": [("side", (1.35, 0.42, 0.40), (0.085, 0.42, 0.31), 42), ("q34", (0.80, 1.20, 0.80), (0.085, 0.50, 0.32), 40),
              ("rearwrap", (0.30, 0.98, 0.50), (0.085, 0.76, 0.40), 55), ("front", (0.26, -0.10, 0.50), (0.085, 0.07, 0.36), 60)],
    "seats": [("q34", (0.78, -0.42, 1.30), (0.0, 0.28, 0.87), 42), ("side", (1.25, 0.30, 0.98), (0.0, 0.30, 0.89), 42),
              ("close", (0.30, -0.05, 1.03), (0.02, 0.17, 0.835), 50), ("rear", (-0.60, 1.08, 0.78), (0.0, 0.42, 0.88), 40)],
    "fairings": [("q34", (1.55, -2.05, 1.25), (0.0, -0.42, 0.66), 42), ("side", (2.45, -0.30, 0.78), (0.0, -0.30, 0.66), 40),
                 ("face", (0.42, -1.75, 0.92), (0.0, -0.70, 0.80), 48), ("rq", (-1.55, -1.55, 0.55), (0.0, -0.38, 0.55), 42)],
    "tank": [("q34", (0.95, -1.05, 1.45), (0.0, -0.10, 0.90), 42), ("side", (1.30, -0.09, 0.92), (0.0, -0.09, 0.90), 50),
             ("rear", (-0.75, 0.85, 1.35), (0.0, -0.08, 0.92), 45), ("cap", (0.22, -0.32, 1.22), (0.0, -0.07, 1.01), 50)],
}


def light(name, loc, power, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy = power
    d.size = size
    d.color = color
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def shot(path, cam_loc, target, lens=50, res=(1100, 800)):
    sc = bpy.context.scene
    cam = sc.camera
    cam.location = cam_loc
    cam.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main(key):
    name = NAMES[key]
    folder = os.path.join(ROOT, "art", "models", name)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(folder, "work.blend"))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    # stand the wheel on a floor (tyre touches the ground)
    r = 0.0 if key in ("bike", "exhaust", "chain", "seats", "fairings", "tank", "tail", "chassis", "frontend", "engine") else max(max(abs(v.co.z) for v in o.data.vertices) for o in sc.objects if o.type == 'MESH')
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -r))
    fl = bpy.context.active_object
    m = bpy.data.materials.new("Floor")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.34, 0.35, 0.37, 1)
    b.inputs["Roughness"].default_value = 0.6
    fl.data.materials.append(m)
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    sc.world = w
    k = 3.0 if key == "bike" else 1.6 if key in VIEWS else 1.0
    light("Key", (1.6 * k, -1.4 * k, 1.5 * k), 130 * k * k, 1.4 * k)
    light("Fill", (-1.8 * k, -0.6 * k, 0.6 * k + 0.5), 45 * k * k, 2.0 * k, (0.85, 0.9, 1.0))
    light("Rim", (0.4 * k, 1.9 * k, 1.0 * k), 140 * k * k, 1.0 * k)
    camd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", camd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tmp = os.path.join(folder, "_r")
    os.makedirs(tmp, exist_ok=True)
    shots = [("side", (1.9, -0.25, 0.05), (0, 0, 0), 50), ("q34", (1.25, -1.35, 0.35), (0, 0, -0.02), 50),
             ("tread", (0.35, -1.25, 0.55), (0, -0.12, 0.05), 55), ("close", (-0.55, -0.42, 0.40), (0.0, -0.10, 0.14), 55)]
    # brake close-ups: front caliper sits behind the axle (+Y), rear one forward-down on the right (-X)
    brake = [] if key not in ("front", "rear") else {"front": [("brake", (0.55, 0.55, 0.22), (0.05, 0.13, 0.04), 50), ("brakeR", (-0.55, 0.50, 0.25), (-0.05, 0.12, 0.04), 50)],
             "rear": [("brake", (-0.55, -0.50, -0.05), (-0.06, -0.08, -0.05), 50), ("sprocket", (0.62, -0.35, 0.20), (0.06, -0.03, 0.0), 50)]}[key]
    shots = [shots[1], shots[2]] + brake
    if key in VIEWS:
        shots = VIEWS[key]
    elif key == "bike":
        shots = [("side", (3.6, 0.0, 0.75), (0, 0, 0.52), 45), ("q34", (2.3, -2.6, 1.15), (0, -0.05, 0.55), 45),
                 ("rear", (-2.2, 2.6, 1.2), (0, 0.05, 0.55), 45), ("cockpit", (0.0, 0.45, 1.55), (0, -0.65, 0.92), 32)]
    paths = []
    for tag, loc, tgt, lens in shots:
        p = os.path.join(tmp, f"{tag}.png")
        shot(p, loc, tgt, lens, (900, 700))
        paths.append(p)
    # 2x2 sheet
    ims = [bpy.data.images.load(p) for p in paths]
    W, H = ims[0].size
    import numpy as np
    sheet = np.zeros((H * 2, W * 2, 4), np.float32)
    for i, im in enumerate(ims):
        a = np.array(im.pixels[:], np.float32).reshape(H, W, 4)
        y, x = (1 - i // 2) * H, (i % 2) * W
        sheet[y:y + H, x:x + W] = a
    out = bpy.data.images.new("sheet", W * 2, H * 2, alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = os.path.join(folder, "preview.png")
    out.file_format = 'PNG'
    out.save()
    for p in paths:
        os.remove(p)
    os.rmdir(tmp)


if __name__ == "__main__":
    for k in [a for a in sys.argv[1:] if a in NAMES] or list(NAMES):
        main(k)
