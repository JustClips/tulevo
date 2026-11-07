"""The whole superbike in one model: every part model put together, written to art/models/Superbike.

  /home/user/bvenv/bin/python art/blender/superbike/assemble.py           -> art/models/Superbike (full detail)
  /home/user/bvenv/bin/python art/blender/superbike/assemble.py --lite    -> art/models/BikeRide (rideable copy)

Run the part scripts first (wheels, exhaust, chain, seats, fairings, tank, tail, chassis, front, engine): this
reads their exported GLBs (studs, bike coordinates), moves the hub-centred wheels onto their axles and renames
the wheel parts Front*/Rear* so every part name in the bike is unique. Colour maps are not copied: textures.json
points at the PNGs in the part folders, so tools/upload_textures.py reuses the images already uploaded.

meta.json also lists, for the rideable bike later, which parts spin with each wheel and which turn with the bars.

--lite: the copy the game rides (Shared/Vehicles/Defs/Superbike.luau). Big parts are decimated to about a
quarter (small ones are kept), and meta.json "groups" says which parts move together: Steer turns about the
steering axis, Fork slides along it with the front wheel, FrontWheel / RearWheel spin, Swing (swingarm, chain,
rear wheel) pivots, Stand is the side stand. Everything else is the rigid body.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

import bikeio as IO  # noqa: E402
from chassis import REAR_AXLE  # noqa: E402
from front import FRONT_AXLE  # noqa: E402

LITE = "--lite" in sys.argv
MODEL = "BikeRide" if LITE else "Superbike"
OUT = os.path.join(IO.MODELS, MODEL)
KEEP = 1200     # --lite: parts up to this many triangles stay as they are
RATIO = 0.25    # --lite: bigger parts keep this share of their triangles (never fewer than KEEP)
WHEELS = {"BikeWheelFront": ("Front", FRONT_AXLE), "BikeWheelRear": ("Rear", REAR_AXLE)}
# wheels first, so their renamed parts never push a suffix onto another model's part of the same name
SOURCES = ["BikeWheelFront", "BikeWheelRear", "BikeFairings", "BikeTank", "BikeTail", "BikeSeats", "BikeFront",
           "BikeChassis", "BikeEngine", "BikeExhaust", "BikeChain"]
STEERING = ["ForkOuter", "ForkInner", "ForkFeet", "TopClamp", "BottomClamp", "Bars", "Grips", "Controls", "Levers",
            "Mudguard", "MudguardFins"]
# --lite moving groups (the rest is the rigid body). Fork = sliding fork legs + everything on the front axle.
GROUPS = {
    "Steer": ["ForkOuter", "TopClamp", "BottomClamp", "Bars", "Grips", "Controls", "Levers"],
    "Fork": ["ForkInner", "ForkFeet", "Mudguard", "MudguardFins", "FrontCaliperL", "FrontCaliperR", "FrontPadL", "FrontPadR"],
    "FrontWheel": ["FrontTyre", "FrontRim", "FrontValve", "FrontRotorL", "FrontRotorR", "FrontCarrierL", "FrontCarrierR"],
    "Swing": ["Swingarm", "ChainSlider", "Hugger", "HuggerTabs", "RearCaliper", "RearPad", "RearBracket",
              "OuterPlatesL", "OuterPlatesR", "InnerPlates", "Rollers", "Pins", "Seals"],
    "RearWheel": ["RearTyre", "RearRim", "RearValve", "RearRotor", "RearSprocket"],
    "Stand": ["SideStand"],
}


def lighten(ob):
    """Decimate a big part to RATIO of its triangles, then re-shade it smooth with sharp edges by angle."""
    n = IO.G.tris(ob)
    if n <= KEEP:
        return
    mod = ob.modifiers.new("lite", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(RATIO, KEEP / n)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if ob.data.has_custom_normals:
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    IO.G.smooth(ob, 40)


def import_model(m):
    """Part objects of one model, in meters, bike coordinates. Returns {part name: object}."""
    folder = os.path.join(IO.MODELS, m)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(folder, m + ".glb"))
    prefix, hub = WHEELS.get(m, ("", (0.0, 0.0, 0.0)))
    out = {}
    for ob in set(bpy.data.objects) - before:
        if ob.type != 'MESH':
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        ob.data.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        ob.data.transform(Matrix.Scale(1 / IO.STUDS, 4))
        ob.data.transform(Matrix.Translation(tuple(hub)))
        name = prefix + re.sub(r"\.\d{3}$", "", ob.name)
        ob.name = name
        assert ob.name == name, f"name clash: {name}"
        out[name] = ob
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT, exist_ok=True)
    parts, looks, source = {}, {}, {}
    wheels = {}
    for m in SOURCES:
        meta = json.load(open(os.path.join(IO.MODELS, m, "meta.json")))
        tex = json.load(open(os.path.join(IO.MODELS, m, "textures.json")))
        prefix, hub = WHEELS.get(m, ("", None))
        obs = import_model(m)
        for name, ob in obs.items():
            src = name[len(prefix):]
            assert src in meta["parts"], (m, name)
            assert LITE or IO.G.tris(ob) == meta["parts"][src]["tris"], (m, name)
            if LITE:
                lighten(ob)
            look = {"roblox": meta["looks"][src]}
            if src in tex:
                look["texpath"] = tex[src]
            parts[name], looks[name], source[name] = ob, look, m
        if prefix:
            wheels[prefix] = {"hub": [round(c * IO.STUDS, 4) for c in hub],
                              "spin": [prefix + p for p in meta["spin"]], "fixed": [prefix + p for p in meta["static"]]}
        missing = set(meta["parts"]) - {n[len(prefix):] for n in obs}
        assert not missing, (m, missing)
    steering = [n for n in STEERING if n in parts] + wheels["Front"]["spin"] + wheels["Front"]["fixed"]
    extra = {"from": source, "wheels": wheels, "steering": steering,
             "steering_axis": "through the ground point y -0.8144 m, tilted back 23.1 deg (rake); x 0"}
    if LITE:
        for g, names in GROUPS.items():
            missing = [n for n in names if n not in parts]
            assert not missing, (g, missing)
        extra["groups"] = GROUPS
        extra["points_m"] = {"front_axle": [float(c) for c in FRONT_AXLE], "rear_axle": [float(c) for c in REAR_AXLE],
                             "swingarm_pivot": [0.0, 0.12, 0.42], "stand_pivot": [0.112, 0.055, 0.300],
                             "rake_deg": 23.1, "steer_ground_y": -0.8144}
    IO.export_model(MODEL, parts, looks, {}, extra=extra)


if __name__ == "__main__":
    main()
