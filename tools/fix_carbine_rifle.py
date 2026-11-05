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
MAG_SCALE = 0.7  # magazine height kept
OUT = "art/models/CarbineRifle/CarbineRifle.glb"

s = trimesh.load(sys.argv[1])
g = s.geometry["Body"]

# Shorter stock like Dev's reference: shorten the buffer tube and pull the stock parts forward.
_m = g.copy()
_m.merge_vertices(merge_tex=True, merge_norm=True)
TUBE_END_OLD, TUBE_END_NEW = -0.223, -0.175
for comp in trimesh.graph.connected_components(_m.face_adjacency, nodes=np.arange(len(_m.faces))):
    vi = np.unique(g.faces[comp])
    lo, hi = g.vertices[vi].min(0), g.vertices[vi].max(0)
    if hi[2] >= -0.045:
        continue
    v = g.vertices
    if abs(lo[2] - TUBE_END_OLD) < 0.002 and abs(hi[2] + 0.046) < 0.002:  # buffer tube: squash toward the receiver
        v[vi, 2] = -0.046 + (v[vi, 2] + 0.046) * (TUBE_END_NEW + 0.046) / (TUBE_END_OLD + 0.046)
    elif lo[2] < -0.21:  # buttplate, end collar, strut: same offset as the tube end
        v[vi, 2] += 0.064
    else:  # stock body and its screws sit right in front of the buttplate
        v[vi, 2] += 0.017
g.vertices = v
c = g.triangles_center


def uv_of(mask):
    idx = np.where(mask)[0]
    return g.visual.uv[g.faces[idx[len(idx) // 2]]].mean(0)


def cyl(r, z0, z1, y, sec=24):
    m = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sec)
    m.apply_translation([0, y, (z0 + z1) / 2])
    return m


def cyl_z(r, z0, z1, y):
    return cyl(r, z0, z1, y, 32)


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
    textured([box(-0.026, 0.026, 0.086, 0.102, -0.030, -0.012), box(-0.008, 0.008, 0.088, 0.098, -0.014, 0.004),
              box(-0.036, -0.024, 0.088, 0.102, -0.028, -0.014)], receiver),
    # lower receiver rear (buffer tower): solid block from the grip up to the buffer tube
    textured([box(-0.0125, 0.0125, 0.040, 0.068, -0.036, 0.002), cyl_z(0.0175, -0.050, -0.030, 0.075)], receiver),
]
s.geometry["Body"] = trimesh.util.concatenate([g] + adds)

# Shorter magazine (Dev: too long): squash it toward the top where it seats in the mag well.
mag = s.geometry["Magazine"]
mv = mag.vertices.copy()
top = mv[:, 1].max()
mv[:, 1] = top + (mv[:, 1] - top) * MAG_SCALE
mag.vertices = mv

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
