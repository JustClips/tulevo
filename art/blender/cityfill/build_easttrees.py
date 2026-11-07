"""Tree groves on the bare grass north of the Bellmont Hills mansions, east of the Vipers hood
(thread "Fill city with buildings and street props", 2026-11-07, Dev: "empty space here").

  blender --background --python build_easttrees.py -- OUT_DIR [--no-render]

Prop models in WORLD coordinates (placed at the origin), at most 44 trees each (build_street's leaf
part pairs). The grass is BellmontGreenN in tools/build_city_map.py (top 0.15).
"""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402

A = BS.A
Y = 0.15 + 0.1
X0, X1, Z0, Z1 = 652.0, 1150.0, -680.0, -330.0     # north of the mansion lots (z -316), off the city edge (x 640)


def layout(seed):
    rng = random.Random(seed)
    pts = []
    x = X0 + 6
    while x < X1:                                     # a row along the city edge and one behind the mansions
        pts.append((x + rng.uniform(-2, 2), -336.0 + rng.uniform(-2, 2)))
        x += rng.uniform(30, 38)
    z = Z1 - 20
    while z > Z0:
        pts.append((X0 + rng.uniform(-1.5, 1.5), z))
        z -= rng.uniform(30, 38)
    for gx, gz, r, n in ((760, -440, 50, 9), (930, -400, 45, 7), (1080, -470, 50, 8), (840, -590, 55, 9), (1020, -620, 45, 6),
                         (700, -620, 35, 5)):
        for _ in range(n):
            a, d = rng.uniform(0, math.tau), r * math.sqrt(rng.random())
            pts.append((gx + math.cos(a) * d, gz + math.sin(a) * d))
    keep = []
    for (px, pz) in pts:
        if X0 <= px <= X1 and Z0 <= pz <= Z1 and all((px - qx) ** 2 + (pz - qz) ** 2 > 81 for qx, qz in keep):
            keep.append((px, pz))
    return [{"kind": "Tree", "x": px, "z": pz, "y": Y, "hx": 0.0, "hz": 1.0, "seed": 900 + i} for i, (px, pz) in enumerate(keep)]


props = layout(7)
MODELS = [("EastTrees" + ("" if k == 0 else str(k // 44 + 1)), props[k:k + 44]) for k in range(0, len(props), 44)]
for name, ps in MODELS:
    S = BS.Street(name)
    S.grate = lambda *a, **k: None
    print(name, len(ps), "trees")
    S.build(ps)
    if A["render"]:
        S.K.render_setup(A["samples"], A["res"])
        S.K.shot("overview", (-600.0, -250.0, 70.0), (-900.0, -500.0, 0.0), lens=28)
