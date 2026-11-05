"""Post-fixes for the carbine rifle GLB (art/models/CarbineRifle), applied on top of the Blender export.

  python3 tools/fix_carbine_rifle.py <blender_export_in_meters.glb>

Adds a barrel, gas tube and front cap inside the handguard, a bigger charging handle at the back
of the upper, then scales everything (meshes and Grip/Muzzle/... empties) to studs (x3.6) and
writes art/models/CarbineRifle/CarbineRifle.glb. Needs: pip install trimesh scipy networkx
"""
import sys
import numpy as np
import trimesh

STUDS = 3.6
OUT = "art/models/CarbineRifle/CarbineRifle.glb"

s = trimesh.load(sys.argv[1])
g = s.geometry["Body"]
c = g.triangles_center


def uv_of(mask):
    idx = np.where(mask)[0]
    return g.visual.uv[g.faces[idx[len(idx) // 2]]].mean(0)


def cyl(r, z0, z1, y, sec=24):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sec)
    m.apply_translation([0, y, (z0 + z1) / 2])
    return m


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def textured(meshes, uv):
    m = trimesh.util.concatenate(meshes)
    m.visual = trimesh.visual.TextureVisuals(uv=np.tile(uv, (len(m.vertices), 1)), material=g.visual.material)
    return m


collar = (c[:, 2] > 0.381) & (c[:, 2] < 0.413) & (abs(c[:, 0]) < 0.012) & (c[:, 1] < 0.09)
cv = g.vertices[g.faces[collar]].reshape(-1, 3)
axis_y = (cv[:, 1].min() + cv[:, 1].max()) / 2
metal = uv_of(collar)
receiver = uv_of((c[:, 2] > 0.05) & (c[:, 2] < 0.15) & (c[:, 1] > 0.07) & (c[:, 1] < 0.09) & (c[:, 0] > 0.011))

adds = [
    textured([cyl(0.0085, 0.17, 0.395, axis_y), cyl(0.0035, 0.17, 0.385, axis_y + 0.012, 12),
              cyl(0.0192, 0.385, 0.3895, axis_y, 32)], metal),
    # charging handle: T-bar behind the upper, stem into the receiver, latch on the left
    textured([box(-0.023, 0.023, 0.087, 0.099, -0.024, -0.010), box(-0.007, 0.007, 0.089, 0.097, -0.012, 0.004),
              box(-0.031, -0.021, 0.089, 0.099, -0.022, -0.012)], receiver),
]
s.geometry["Body"] = trimesh.util.concatenate([g] + adds)

for geom in s.geometry.values():
    geom.apply_scale(STUDS)
edges = s.graph.transforms.edge_data
for (parent, child), data in list(edges.items()):
    M = np.array(data.get("matrix", np.eye(4)), dtype=float).copy()
    M[:3, 3] *= STUDS
    s.graph.update(frame_from=parent, frame_to=child, matrix=M)

s.export(OUT)
t = trimesh.load(OUT)
print("wrote", OUT, "size", t.extents.round(3), "nodes", sorted(n for n in t.graph.nodes if n != "world"),
      "tris", {k: len(v.faces) for k, v in t.geometry.items()})
