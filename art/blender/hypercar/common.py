"""Shared constants and render helpers for the hypercar build scripts.

Blender coords (meters): -Y = front of the car, +Z = up, +X = the car's LEFT side
(driver side, left-hand drive). Origin = ground, centred between the axles.
In Roblox (x3.6 studs per meter): Roblox X = -Blender X, Y = Blender Z, Z = Blender Y.
"""
import bpy, math
from mathutils import Vector

OUT = r"C:\out\car918\work"

# ---- layout (meters) ----
WHEELBASE = 2.73
Y_FRONT_AXLE = -WHEELBASE / 2
Y_REAR_AXLE = WHEELBASE / 2
X_FRONT_HUB = 0.80
X_REAR_HUB = 0.785
WHEEL_R = 0.36
HUB_Z = WHEEL_R
TIRE_W_FRONT = 0.265
TIRE_W_REAR = 0.325

DRIVER_X = 0.38                     # left-hand drive
SEAT = Vector((DRIVER_X, 0.10, 0.30))  # top of the driver's seat cushion
STEER_CENTER = Vector((DRIVER_X, -0.36, 0.66))
STEER_TILT = 22.0                   # degrees the column rises toward the driver
STEER_AXIS = Vector((0, math.cos(math.radians(STEER_TILT)), math.sin(math.radians(STEER_TILT))))  # toward driver
PEDAL_PIVOT_Y = -0.93
PEDAL_PIVOT_Z = 0.50
PEDAL_GAS_X = DRIVER_X - 0.10
PEDAL_BRAKE_X = DRIVER_X + 0.05
DOOR_HINGE = Vector((0.90, -0.86, 0.50))  # left door; mirror X for the right one

WHEELS = {
    "FL": Vector((X_FRONT_HUB, Y_FRONT_AXLE, HUB_Z)),
    "FR": Vector((-X_FRONT_HUB, Y_FRONT_AXLE, HUB_Z)),
    "RL": Vector((X_REAR_HUB, Y_REAR_AXLE, HUB_Z)),
    "RR": Vector((-X_REAR_HUB, Y_REAR_AXLE, HUB_Z)),
}


def enable_gpu(scene):
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev_type in ('OPTIX', 'CUDA'):
            try:
                prefs.compute_device_type = dev_type
                prefs.get_devices()
                if any(d.type == dev_type for d in prefs.devices):
                    break
            except Exception:
                continue
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = 'GPU'
    except Exception as e:
        print("GPU setup failed, using CPU:", e)


def _aim(ob, target):
    d = (Vector(target) - ob.location).normalized()
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def setup_studio(scene):
    """Grey studio: soft world light, floor, three big area lights."""
    w = bpy.data.worlds.get("Studio") or bpy.data.worlds.new("Studio")
    w.use_nodes = True
    nt = w.node_tree; N = nt.nodes
    for n in list(N):
        if n.bl_idname != 'ShaderNodeOutputWorld':
            N.remove(n)
    out = [n for n in N if n.bl_idname == 'ShaderNodeOutputWorld'][0]
    sky = N.new('ShaderNodeTexSky') if False else None
    bg = N.new('ShaderNodeBackground'); bg.inputs['Color'].default_value = (0.42, 0.44, 0.47, 1); bg.inputs['Strength'].default_value = 0.6
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    scene.world = w
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass

    made = []
    if "Floor" not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
        fl = bpy.context.active_object; fl.name = "Floor"
        m = bpy.data.materials.new("FloorMat"); m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.32, 0.33, 0.35, 1); b.inputs['Roughness'].default_value = 0.55
        fl.data.materials.append(m)
        made.append(fl)
    for nm, power, size, loc in (("Key", 2600, 5, (-5, -5, 6)), ("Fill", 900, 6, (6, -2, 3)),
                                 ("Rim", 2200, 4, (2, 7, 5)), ("Top", 1200, 7, (0, 0, 8))):
        if nm in bpy.data.objects:
            continue
        ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = power; ld.size = size
        lo = bpy.data.objects.new(nm, ld); scene.collection.objects.link(lo)
        lo.location = loc; _aim(lo, (0, 0, 0.5))
        made.append(lo)
    return made


def render(scene, path, cam_loc, target=(0, 0, 0.55), lens=50, samples=48, res=(1600, 900)):
    enable_gpu(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    cam = bpy.data.objects.get("RenderCam")
    if not cam:
        cd = bpy.data.cameras.new("RenderCam")
        cam = bpy.data.objects.new("RenderCam", cd); scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.location = cam_loc; _aim(cam, target)
    scene.camera = cam
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


VIEWS = {
    "front34": ((-4.6, -6.2, 2.2), (0, -0.2, 0.5), 50),
    "rear34": ((4.8, 6.0, 2.4), (0, 0.2, 0.5), 50),
    "side": ((-8.5, 0, 1.0), (0, 0, 0.5), 50),
    "top": ((0.01, 0, 11), (0, 0, 0), 50),
    "cockpit": ((-1.3, 1.6, 1.9), (0.25, -0.45, 0.55), 30),
    "front": ((0, -8.5, 1.0), (0, 0, 0.5), 50),
    "rear": ((0.6, 7.5, 2.2), (0, 1.2, 0.7), 40),
    "deck": ((1.2, 3.6, 2.6), (0, 1.0, 0.9), 40),
    "wheel": ((-2.9, -2.4, 0.55), (0.9, -1.365, 0.36), 60),
}
