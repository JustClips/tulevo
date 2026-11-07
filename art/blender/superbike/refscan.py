"""Reference scan for the superbike bodywork: load it, stand it upright and put it in bike coordinates.

  /home/user/bvenv/bin/python art/blender/superbike/refscan.py <scan.glb> <out_dir>

The scan is a CC-BY-4.0 phone scan of a real 2019+ bike ("BMW S 1000 RR - HSLU Midterm 3DMOD4RT" by
noe_auf on Sketchfab). It is a SHAPE GUIDE only: the fairing scripts fit their own clean panels to
it. Its textures carry logos and are never used, and the scan itself is not committed or uploaded.
Credit (CC-BY) goes in the game description once parts built from it ship.

The scan stands on its side stand, leaning left with the bars turned. load_aligned():
  1. fits circles to the rear tyre's silhouette -> rear hub + radius (front tyre is steered, unreliable)
  2. measures the lean from the rear tyre's centre plane and rolls the scan upright
  3. scales so the rear tyre radius matches ours (0.320 m) and moves the rear hub onto ours
Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
Running the file renders side/top/front overlays of the scan with our finished parts.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REAR_HUB = (0.0, 0.7205, 0.3204)
FRONT_HUB = (0.0, -0.7205, 0.2999)
REAR_R = 0.320


def _points(objs):
    P = []
    for o in objs:
        M = np.array(o.matrix_world)
        v = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", v)
        v = v.reshape(-1, 3)
        P.append(v @ M[:3, :3].T + M[:3, 3])
    return np.concatenate(P)


def _fit_rear(P, floor):
    X, Z = P[:, 0], P[:, 2]
    prof = []
    for z in np.linspace(floor + 0.01, floor + 0.33, 110):
        m = (X > 0.25) & (np.abs(Z - z) < 0.004)
        if m.sum() >= 3:
            prof.append((z, X[m].max()))
    prof = np.array(prof)
    best = None
    for hz in np.linspace(floor + 0.15, floor + 0.30, 151):
        for r in np.linspace(0.15, 0.30, 151):
            ok = np.abs(prof[:, 0] - hz) < r * 0.95
            if ok.sum() < 8:
                continue
            dx = np.sqrt(r * r - (prof[ok, 0] - hz) ** 2)
            hx = np.median(prof[ok, 1] - dx)
            err = np.mean(np.abs(hx + dx - prof[ok, 1])) + 0.5 * abs((hz - r) - floor)
            if best is None or err < best[0]:
                best = (err, hx, hz, r)
    return best[1:]


def _strip_floor(objs, z_cut):
    """Delete the scanned floor (everything below z_cut in scan space, before alignment)."""
    import bmesh
    for o in objs:
        M = o.matrix_world
        bm = bmesh.new()
        bm.from_mesh(o.data)
        kill = [v for v in bm.verts if (M @ v.co).z < z_cut]
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bm.to_mesh(o.data)
        bm.free()


def load_aligned(path, name="RefScan", strip_floor=True):
    """Import the scan and transform it into bike coordinates. Returns the joined mesh object."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH' and len(o.data.vertices) > 100]
    extra = [o.name for o in new if o not in meshes]
    P = _points(meshes)
    floor = float(P[:, 2].min())
    hx, hz, r = _fit_rear(P, floor)
    if strip_floor:
        _strip_floor(meshes, floor + 0.022)
        P = _points(meshes)
    # rear tyre centre plane: tread points near the contact patch vs at hub height behind the hub
    d = np.hypot(P[:, 0] - hx, P[:, 2] - hz)
    ang = np.degrees(np.arctan2(P[:, 2] - hz, P[:, 0] - hx))
    tread = (np.abs(d - r) < 0.03) & (P[:, 2] > floor + 0.03)
    Y = P[:, 1]

    def mid(a0, a1):
        m = tread & (ang >= a0) & (ang < a1)
        return (Y[m].min() + Y[m].max()) / 2

    y_low = mid(-120, -60)          # tyre centre near the ground
    y_hub = mid(-30, 30)            # tyre centre at hub height, behind the hub
    lean = math.atan2(y_low - y_hub, r * 0.85)     # the "low" band centre sits ~0.85 r below the hub
    s = REAR_R / r
    # roll about the scan's X axis through the rear contact patch so the hub sits over it
    pivot = Vector((hx, y_low, floor))
    roll = Matrix.Translation(pivot) @ Matrix.Rotation(-lean, 4, 'X') @ Matrix.Translation(-pivot)
    hub = roll @ Vector((hx, y_hub, hz))
    # scan -> bike: scan -X is the front (same as ours), scan -Y is the bike's left (ours +X)
    to_bike = Matrix(((0, -1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    M = (Matrix.Translation(Vector(REAR_HUB)) @ Matrix.Scale(s, 4) @ to_bike @
         Matrix.Translation(-Vector((hub.x, y_low, hub.z))) @ roll)
    print("rear hub after roll", tuple(round(v, 4) for v in hub), "plane y", round(y_low, 4))
    for o in meshes:
        o.data.transform(M @ o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    for n in extra:          # empties and the scan's floor card
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    info = {"scale": s, "lean_deg": math.degrees(lean), "rear_r_scan": r, "floor": floor}
    # front hub check: the steered front tyre's lowest point should sit near our front contact
    Pb = _points([ob])
    m = (Pb[:, 1] < -0.3) & (Pb[:, 2] < 0.03)
    info["front_contact_y"] = float(np.median(Pb[m, 1])) if m.sum() else None
    print("refscan aligned:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()})
    return ob, info


def import_part(name, loc=(0, 0, 0)):
    """One of our finished parts (GLB in studs) back in meters, for overlays."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ROOT, "art", "models", name, f"{name}.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.scale = (1 / 3.6,) * 3
            o.location = loc
    return new


def overlay(scan_path, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob, info = load_aligned(scan_path)
    import_part("BikeWheelFront", FRONT_HUB)
    import_part("BikeWheelRear", REAR_HUB)
    for n in ("BikeExhaust", "BikeChain", "BikeSeats"):
        import_part(n)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    sc.world = w
    sc.view_settings.view_transform = 'Standard'
    # our parts in solid orange so they stand out against the scan
    m = bpy.data.materials.new("Ours")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1.0, 0.35, 0.0, 1)
    for o in sc.objects:
        if o.type == 'MESH' and o is not ob:
            o.data.materials.clear()
            o.data.materials.append(m)
    sc.render.resolution_x, sc.render.resolution_y = 1800, 1100
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.4
    views = {"side": ((3.0, 0.0, 0.6), (-1, 0, 0)), "top": ((0.0, 0.0, 3.5), (0, 0, -1)),
             "front": ((0.0, -3.5, 0.6), (0, 1, 0))}
    os.makedirs(out, exist_ok=True)
    for name, (loc, d) in views.items():
        cam.location = loc
        cam.rotation_euler = Vector(d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, f"overlay_{name}.png")
        bpy.ops.render.render(write_still=True)
    return info


if __name__ == "__main__":
    overlay(sys.argv[-2], sys.argv[-1])
