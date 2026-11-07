"""The whole superbike in one model: every part model put together, written to art/models/Superbike.

  /home/user/bvenv/bin/python art/blender/superbike/assemble.py

Run the part scripts first (wheels, exhaust, chain, seats, fairings, tank, tail, chassis, front, engine): this
reads their exported GLBs (studs, bike coordinates), moves the hub-centred wheels onto their axles and renames
the wheel parts Front*/Rear* so every part name in the bike is unique. Colour maps are not copied: textures.json
points at the PNGs in the part folders, so tools/upload_textures.py reuses the images already uploaded.

meta.json also lists, for the rideable bike later, which parts spin with each wheel and which turn with the bars.
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

MODEL = "Superbike"
OUT = os.path.join(IO.MODELS, MODEL)
WHEELS = {"BikeWheelFront": ("Front", FRONT_AXLE), "BikeWheelRear": ("Rear", REAR_AXLE)}
# wheels first, so their renamed parts never push a suffix onto another model's part of the same name
SOURCES = ["BikeWheelFront", "BikeWheelRear", "BikeFairings", "BikeTank", "BikeTail", "BikeSeats", "BikeFront",
           "BikeChassis", "BikeEngine", "BikeExhaust", "BikeChain"]
STEERING = ["ForkOuter", "ForkInner", "ForkFeet", "TopClamp", "BottomClamp", "Bars", "Grips", "Controls", "Levers",
            "Mudguard", "MudguardFins"]


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
            assert IO.G.tris(ob) == meta["parts"][src]["tris"], (m, name)
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
    IO.export_model(MODEL, parts, looks, {}, extra=extra)


if __name__ == "__main__":
    main()
