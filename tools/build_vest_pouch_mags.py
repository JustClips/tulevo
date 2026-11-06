"""Adds PouchMag1..3 (carbine magazine tops standing in the vest's rifle pouches) to the Blender vest export,
and makes each MagFlap lid tall enough to cover them. Writes art/models/ArmorVest/ArmorVest.glb.

  python3 tools/build_vest_pouch_mags.py <vest3 export.glb> <vest3 meta.json>

Rule (agreed with the gun animation thread): the carbine Magazine from art/models/CarbineRifle/CarbineRifle.glb
at Config.Weapons.GunScale (1.7), its MagWell point at (pouch centre x, pouch centre y, pouch top z + MAG_UP)
in Blender coords, turned -90 deg about Z so the gun's muzzle direction points to the wearer's right (-X);
only the top KEEP studs are kept. Needs: pip install trimesh scipy networkx
"""
import json
import sys

import numpy as np
import trimesh

GUN_SCALE = 1.7
MAG_UP = 0.08
KEEP = 0.42
LID_RAISE = 0.05  # flap lid top moves up this much so the closed flap covers the mag top
OUT = "art/models/ArmorVest/ArmorVest.glb"

vest = trimesh.load(sys.argv[1])
meta = json.load(open(sys.argv[2]))
gun = trimesh.load("art/models/CarbineRifle/CarbineRifle.glb")
mag = gun.geometry["Magazine"].copy()
well = gun.graph.get("MagWell")[0][:3, 3]

# gun glTF space: +Z = muzzle (Blender -Y), +Y up. Scale, put MagWell at the origin.
mag.apply_scale(GUN_SCALE)
mag.apply_translation(-well * GUN_SCALE)
# -90 deg about up: muzzle (+Z glTF) -> -X (wearer's right)
mag.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
mag = mag.slice_plane([0, -KEEP, 0], [0, 1, 0], cap=False)

for p in meta["mag_flaps"]:
    k = p["k"]
    # flap lid: raise its top face
    fl = vest.geometry[[n for n in vest.geometry if n.startswith(f"MagFlap{k}")][0]]
    v = fl.vertices.copy()
    top_bl = p["flap_bbox_max"][2]
    v[v[:, 1] > top_bl - 0.035, 1] += LID_RAISE
    fl.vertices = v
    # magazine
    m = mag.copy()
    m.apply_translation([p["pouch_center_x"], p["pouch_top_z"] + MAG_UP, -p["pouch_center_y"]])  # Blender -> glTF
    vest.add_geometry(m, node_name=f"PouchMag{k}", geom_name=f"PouchMag{k}")

# exact mesh names in Roblox
for name in list(vest.geometry):
    if name.startswith("MagFlap") and "." in name:
        vest.geometry[name.split(".")[0]] = vest.geometry.pop(name)
        for node in vest.graph.nodes_geometry:
            if vest.graph[node][1] == name:
                vest.graph.update(frame_to=node, geometry=name.split(".")[0])

vest.export(OUT)
t = trimesh.load(OUT)
print("wrote", OUT, "bounds", t.bounds.round(3).tolist())
for n in t.graph.nodes_geometry:
    g = t.geometry[t.graph[n][1]]
    print(" ", n, t.graph[n][1], len(g.faces), g.bounds.round(3).tolist())
