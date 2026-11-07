"""Street lamps and traffic signals as Roblox "City Prop" models instead of baked meshes (2026-11-07).

They stand in the map itself (src/workspace/City.model.json, folders City/StreetLamps and
City/TrafficSignals), so they show in Studio edit mode like the buildings:

- world_folders() (called by tools/build_city_map.py) makes one empty Model per spot of
  art/blender/cityfill/street_layout.json ("Light" spots of every Street* model, "Signal" corners)
  with attributes
    LiveSyncAsset   the City Prop model (Shared/CityPropIds)
    LiveSyncScale   art/city_props.json "scale" (the pack is modelled small)
    LiveSyncCFrame  where the scaled asset goes: pole foot on the plinth, lamp arm over the road,
                    signal heads facing their traffic with the arm over its lanes
    CityProp        the CityPropIds key; SignalPhase EW / NS on signals
  The LiveSync plugin (v10+) loads the model into it in edit mode; Server/CityBuildings does the
  same at run time if one is still empty, then lights the lamp glass and adds the signal lens discs
  and pole colliders (Shared/CityPropInfo).
- Street* models get LiveSyncDrop: their old baked lamps are deleted after loading.

Which model stands where: art/city_props.json (street_lamp, signal_model). After changing it run
  python3 tools/build_city_map.py
A model not in art/city_props.json "models" yet needs its ref / foot / reach (/ face) there: ref is
where its CityPropInfo ref part sits in the uploaded asset (InsertService:LoadAsset, Open Cloud Luau
Execution), the rest is in Shared/CityPropInfo (tools/city_prop_scan.py).

  python3 tools/city_props.py && python3 tools/city_colliders.py StreetVaultAvenue StreetBackStreet \
      StreetNorthStreet StreetSouthStreet StreetWestStreet StreetEastStreet
drops the old lamp pole collider boxes (the non-concrete box on each lamp spot) from
art/models/Street*/meta.json, so no invisible poles stay behind. The concrete plinth box stays.
Safe to run again.
"""
import json
import math
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LAYOUT = os.path.join(ROOT, "art", "blender", "cityfill", "street_layout.json")
CONFIG = os.path.join(ROOT, "art", "city_props.json")
IDS = os.path.join(ROOT, "src", "shared", "CityPropIds.luau")

# parts of the old baked street lamps in the Street* meshes (Lua patterns, LiveSyncDrop)
OLD_LAMP_DROP = "^PoleLamp$,^MetalLampHead$,^MetalLampCap$,^StreetLamp%d"


def prop_ids():
    ids = {}
    for line in open(IDS, encoding="utf-8"):
        m = re.match(r"\s*(\w+)\s*=\s*(\d+)", line)
        if m:
            ids[m.group(1)] = int(m.group(2))
    return ids


def _r(v):
    v = round(v, 4)
    return 0.0 if v == 0 else v


def placement(info, scale, at, axis, want):
    """CFrame (12 numbers) that moves the asset, scaled by `scale` about its origin, so its pole foot
    is on `at` and its horizontal direction `axis` (asset space) points along `want` (world)."""
    foot = [(info["ref"][i] + info["foot"][i]) * scale for i in range(3)]
    # yaw about Y: (x, z) -> (x c + z s, -x s + z c), i.e. (x - iz) turns by the angle
    turn = math.atan2(-want[1], want[0]) - math.atan2(-axis[2], axis[0])
    c, s = math.cos(turn), math.sin(turn)
    rx, rz = foot[0] * c + foot[2] * s, -foot[0] * s + foot[2] * c
    pos = [at[0] - rx, at[1] - foot[1], at[2] - rz]
    return [_r(v) for v in pos + [c, 0, s, 0, 1, 0, -s, 0, c]]


def world_folders():
    """City/StreetLamps and City/TrafficSignals for City.model.json."""
    layout = json.load(open(LAYOUT))
    cfg = json.load(open(CONFIG))
    ids = prop_ids()
    scale, top = cfg["scale"], cfg["plinth_top"]

    def prop(name, key, cf, extra=None):
        return {"name": name, "className": "Model", "tags": ["CityProp"], "attributes": {
            "LiveSyncAsset": ids[key], "LiveSyncScale": scale, "LiveSyncCFrame": {"CFrame": cf},
            "CityProp": key, **(extra or {})}}

    lamps = []
    for street, props in layout.items():
        key = cfg["street_lamp"].get(street)
        if not key:
            continue
        info = cfg["models"][key]
        lights = [p for p in props if p.get("kind") == "Light"]
        for i, p in enumerate(lights, 1):
            cf = placement(info, scale, (p["x"], p["y"] + top, p["z"]), info["reach"], (p["hx"], p["hz"]))
            lamps.append(prop(f"{street}Lamp{i}", key, cf))
    signals = []
    sigs = [p for props in layout.values() for p in props if p.get("kind") == "Signal"]
    for i, p in enumerate(sigs, 1):
        key = cfg["signal_model"][p["phase"]]
        info = cfg["models"][key]
        # heads look back along the traffic's direction of travel (dx, dz); seen from the driver's
        # seat the pole is on the far right corner and the arm reaches left, over their lanes
        cf = placement(info, scale, (p["x"], p["y"] + top, p["z"]), info["face"], (-p["dx"], -p["dz"]))
        signals.append(prop(f"Signal{p['phase']}{i}", key, cf, {"SignalPhase": p["phase"]}))
    return [{"name": "StreetLamps", "className": "Folder", "children": lamps},
            {"name": "TrafficSignals", "className": "Folder", "children": signals}]


def main():
    layout = json.load(open(LAYOUT))
    total = dropped = 0
    for model, props in layout.items():
        lights = [p for p in props if p.get("kind") == "Light"]
        if not lights:
            continue
        total += len(lights)
        meta_p = os.path.join(ROOT, "art", "models", model, "meta.json")
        meta = json.load(open(meta_p))
        spots = {(round(-p["x"], 2), round(p["z"], 2)) for p in lights}   # Blender (x, y) = Roblox (-x, z)
        keep = []
        for b in meta.get("collider_boxes", []):
            if (round(b[0], 2), round(b[1], 2)) in spots and b[7] != "Concrete":
                dropped += 1
                continue
            keep.append(b)
        meta["collider_boxes"] = keep
        json.dump(meta, open(meta_p, "w", newline="\n"), indent=1)
    print(f"{total} lamp spots, dropped {dropped} pole colliders")


if __name__ == "__main__":
    main()
