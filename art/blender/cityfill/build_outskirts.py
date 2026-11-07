"""Countryside west of the city, on the old Fort Halden site (thread "Fill city with buildings and
street props", 2026-11-07): shade trees along the fort road and groves on the grass either side.

  blender --background --python build_outskirts.py -- OUT_DIR [--no-render]

Builds prop models in WORLD coordinates (placed at the origin, like ParkProps): WestTreesN[2]
north of the road (z < -154), WestTreesS[2] south of it (z > -110); at most 44 trees per model
(build_street has six leaf part pairs of 8 trees each). The grass itself is flat
city ground (WestGreen* parts in tools/build_city_map.py).
"""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402

A = BS.A
ROAD_Z, ROAD_HALF = -132.0, 22.0
X_CITY, X_FORT = -650.0, -1700.0         # city edge (roads end at -640) .. short of the fort's ground (-1750)
Y = 0.15 + 0.1                           # grass top + the props' usual lift


def grove(rng, cx, cz, r, n, out):
    for _ in range(n):
        a, d = rng.uniform(0, math.tau), r * math.sqrt(rng.random())
        out.append((cx + math.cos(a) * d, cz + math.sin(a) * d))


def layout(side, seed):
    """side -1: north of the road (z smaller), +1: south."""
    rng = random.Random(seed)
    pts = []
    x = X_CITY - 20
    while x > X_FORT:                                                   # avenue of trees along the road
        pts.append((x + rng.uniform(-3, 3), ROAD_Z + side * (ROAD_HALF + 14 + rng.uniform(-1.5, 1.5))))
        x -= rng.uniform(34, 42)
    groves = [(-760, 260, 45, 8), (-980, 420, 60, 10), (-1240, 230, 50, 8), (-1500, 380, 55, 9), (-1180, 640, 45, 6),
              (-820, 620, 40, 5)]
    for gx, gd, r, n in groves:                                         # groves away from the road
        grove(rng, gx, ROAD_Z + side * gd, r, n, pts)
    keep = []
    for (px, pz) in pts:                                                # no two trunks closer than 9 studs
        if all((px - qx) ** 2 + (pz - qz) ** 2 > 81 for qx, qz in keep) and X_FORT <= px <= X_CITY:
            keep.append((px, pz))
    return [{"kind": "Tree", "x": px, "z": pz, "y": Y, "hx": 0.0, "hz": 1.0, "seed": 500 + seed * 100 + i}
            for i, (px, pz) in enumerate(keep)]


MODELS = []
for base, side, seed in (("WestTreesN", -1, 1), ("WestTreesS", 1, 2)):
    props = layout(side, seed)
    for k in range(0, len(props), 44):                       # 6 leaf part pairs x 8 trees per model at most
        MODELS.append((base + ("" if k == 0 else str(k // 44 + 1)), side, props[k:k + 44]))

for name, side, props in MODELS:
    S = BS.Street(name)
    S.grate = lambda *a, **k: None                   # trees stand in the grass, not in sidewalk grates
    print(name, len(props), "trees")
    S.build(props)
    if A["render"]:
        S.K.render_setup(A["samples"], A["res"])
        S.K.shot("overview", (620.0, ROAD_Z, 60.0), (1000.0, ROAD_Z + side * 250, 0.0), lens=28)
