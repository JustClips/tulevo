"""Shared helpers for the carbine build scripts (render setup, GPU)."""
import bpy, math
from mathutils import Vector

OUT = r"C:\out\carbine"


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


def mesh_bbox(objs):
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def _aim(ob, target):
    d = (target - ob.location).normalized()
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def setup_world(scene, grey=0.30):
    w = bpy.data.worlds.get("RenderWorld") or bpy.data.worlds.new("RenderWorld")
    w.use_nodes = True
    nt = w.node_tree; N = nt.nodes
    for n in list(N):
        if n.bl_idname != 'ShaderNodeOutputWorld':
            N.remove(n)
    out = [n for n in N if n.bl_idname == 'ShaderNodeOutputWorld'][0]
    cam_bg = N.new('ShaderNodeBackground'); cam_bg.inputs['Color'].default_value = (grey, grey, grey, 1)
    amb = N.new('ShaderNodeBackground'); amb.inputs['Color'].default_value = (0.08, 0.08, 0.085, 1)
    lp = N.new('ShaderNodeLightPath'); mx = N.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
    nt.links.new(amb.outputs[0], mx.inputs[1]); nt.links.new(cam_bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    scene.world = w
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Base Contrast'
    except Exception:
        pass


def render_views(scene, objs, views, samples=128, res=(1600, 900)):
    """views: list of (filepath, direction-from-target Vector)."""
    enable_gpu(scene)
    setup_world(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    lo, hi = mesh_bbox(objs)
    target = (lo + hi) / 2
    size = (hi - lo).length

    cam_data = bpy.data.cameras.new("RenderCam"); cam_data.lens = 85
    cam = bpy.data.objects.new("RenderCam", cam_data); scene.collection.objects.link(cam)
    scene.camera = cam
    lights = []
    for nm, power, sz in (("Key", 60, 1.2), ("Fill", 18, 1.5), ("Rim", 70, 0.8), ("Top", 15, 2.0)):
        ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = power; ld.size = sz
        lo_ = bpy.data.objects.new(nm, ld); scene.collection.objects.link(lo_); lights.append(lo_)

    hfov = 2 * math.atan(18 / cam_data.lens)
    Z = Vector((0, 0, 1))
    for path, d, *fit in views:
        d = Vector(d).normalized()
        dist = (size * (fit[0] if fit else 0.40)) / math.tan(hfov / 2)
        cam.location = target + d * dist; _aim(cam, target)
        r = d.cross(Z).normalized()
        key, fill, rim, top = lights
        key.location = target + (d + 0.9 * r + 0.8 * Z).normalized() * 1.6
        fill.location = target + (d - 1.1 * r + 0.1 * Z).normalized() * 1.8
        rim.location = target + (-d + 0.3 * r + 0.9 * Z).normalized() * 1.4
        top.location = target + Z * 1.5
        for l in lights:
            _aim(l, target)
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("rendered", path)

    for l in lights:
        bpy.data.objects.remove(l)
    bpy.data.objects.remove(cam)


STANDARD_VIEWS = {
    "left": ((-1, 0.0, 0.08), 0.56),
    "right": ((1, 0.0, 0.08), 0.56),
    "front34": ((-0.62, -0.72, 0.32), 0.46),
    "back34": ((0.62, 0.72, 0.32), 0.46),
}
