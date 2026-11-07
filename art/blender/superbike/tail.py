"""Superbike tail: tail cowl with a recess the pillion seat sits in, black undertray, LED tail light,
number-plate hanger with a blank plate and two LED indicators.

  /home/user/bvenv/bin/python art/blender/superbike/tail.py            build + export art/models/BikeTail
  /home/user/bvenv/bin/python art/blender/superbike/tail.py --scan F   refit tail_shape.npz from the scan

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
The cowl shape is fitted to the scan like the tank (cylchart.py, here with an axis that rises toward the
tip, tail_shape.npz). The scan's tail top is its pillion seat, so the build presses a recess into the
fitted skin where our pillion (seats.py PLACE) sits; the pillion covers it. Outline points are chart
(u, y) or side-view (y, z) points on the left side, as in tank.py.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import bikeio as IO  # noqa: E402
import cylchart  # noqa: E402
import fairings as FA  # noqa: E402
import tank as TK  # noqa: E402
from tank import UV, VZ  # noqa: E402

MODEL = "BikeTail"
OUT = os.path.join(IO.MODELS, MODEL)
TEX = os.path.join(OUT, "tex")
SHAPE = os.path.join(HERE, "tail_shape.npz")
T_PANEL = 0.003

# pillion footprint (seats.py, placed): y -> half width of its sides, and the height of its pan
PILLION_Y = [0.603, 0.608, 0.623, 0.638, 0.668, 0.698, 0.728, 0.758, 0.788, 0.818, 0.836, 0.847]
PILLION_W = [0.000, 0.060, 0.082, 0.090, 0.094, 0.093, 0.090, 0.086, 0.078, 0.063, 0.045, 0.000]
FLOOR = (0.942, 0.040)        # recess floor z = a + b * (y - 0.60)
Y_END = 0.866                 # tail tip (rear face)


def pillion_poly(grow=0.0):
    y, w = np.array(PILLION_Y), np.array(PILLION_W)
    left = np.stack([w, y], 1)
    right = np.stack([-w[::-1], y[::-1]], 1)
    P = Polygon(np.vstack([left, right])).buffer(0)
    return P.buffer(grow, quad_segs=6) if grow else P


def load_surface(recess=True):
    d = np.load(SHAPE)
    zc, Rc, slope, v0 = (float(d[k]) for k in ("zc", "Rc", "slope", "v0"))
    S0 = cylchart.CylSurface(d["H"], d["us"], d["vs"], zc, Rc, slope, v0)
    if not recess:
        return S0
    us = np.arange(d["us"][0], d["us"][-1] + 1e-9, 0.004)
    vs = np.arange(d["vs"][0], d["vs"][-1] + 1e-9, 0.004)
    U, V = np.meshgrid(us, vs)
    H = S0.h(U, V)
    P = S0.point(U, V)
    poly = pillion_poly(-0.002)
    pts = shapely.points(P[..., 0].ravel(), P[..., 1].ravel())
    inside = shapely.contains(poly, pts).reshape(U.shape)
    dist = shapely.distance(poly.boundary, pts).reshape(U.shape)
    sd = np.where(inside, dist, -dist)
    wgt = np.clip(sd / 0.010, 0, 1)
    wgt = wgt * wgt * (3 - 2 * wgt)
    th = U / Rc
    zax = zc + slope * (V - v0)
    floor = FLOOR[0] + FLOOR[1] * (V - 0.60)
    with np.errstate(divide="ignore", invalid="ignore"):
        h_floor = Rc - (floor - zax) / np.cos(th)
    h_floor = np.where(np.cos(th) > 0.2, h_floor, H)
    Hn = H + wgt * np.maximum(h_floor - H, 0)
    return cylchart.CylSurface(Hn, us, vs, zc, Rc, slope, v0)


def crease_u(S0):
    """u of the side crease (widest point of each section) along y."""
    vv = np.arange(0.44, 0.90, 0.01)
    uu = np.linspace(0.05, 0.70, 651)
    out = []
    for v in vv:
        x = S0.point(uu, np.full_like(uu, v))[:, 0]
        out.append(uu[np.argmax(x)])
    return vv, np.array(out)


# ------------------------------------------------------------------ outline (left half, front centre -> rear centre)
COWL_HALF = [UV(0.0, 0.512), UV(0.06, 0.511), VZ(0.505, 0.840), VZ(0.490, 0.815), VZ(0.462, 0.803), VZ(0.432, 0.800),
             VZ(0.424, 0.780), VZ(0.427, 0.760), VZ(0.434, 0.745), VZ(0.462, 0.757), VZ(0.500, 0.785), VZ(0.560, 0.835),
             VZ(0.620, 0.885), VZ(0.680, 0.925), VZ(0.740, 0.955), VZ(0.800, 0.973), VZ(0.840, 0.981), VZ(0.858, 0.985),
             VZ(Y_END, 0.990), UV(0.15, Y_END), UV(0.0, Y_END)]
LOWER_EDGE = COWL_HALF[9:19]


def cowl_outline(S):
    uv = TK.to_uv(S, COWL_HALF)
    return TK.smooth_closed(FA.mirror_loop(uv), n=10)


# ------------------------------------------------------------------ paint
def cowl_paint(S, S0):
    vv, uc = crease_u(S0)
    poly = pillion_poly(0.014)

    def paint(u, v):
        col = np.empty(np.shape(u) + (3,))
        col[:] = IO.WHITE
        P = S.point(u, v)
        x, y = P[..., 0], P[..., 1]
        pts = shapely.points(x.ravel(), y.ravel())
        near = shapely.contains(poly, pts).reshape(x.shape)
        step = (y < 0.62) & (np.abs(x) < 0.104) & (y > 0.49)
        col[near | step] = IO.CHAR
        a = np.abs(u)
        c = np.interp(v, vv, uc)
        stripe = (a > c - 0.017) & (a < c - 0.011) & (v > 0.47) & (v < Y_END - 0.008) & ~(near | step)
        col[stripe] = IO.ACCENT
        return col
    return paint


# ------------------------------------------------------------------ small solids
def prism(acc, P0, D, depth):
    """Extrude a planar 3D loop P0 along D by depth: outward side walls + both end caps."""
    D = np.asarray(D, float)
    D = D / np.linalg.norm(D)
    P0 = np.asarray(P0, float)
    P1 = P0 + depth * D
    c = P0.mean(0)
    n = len(P0)
    V = np.vstack([P0, P1])
    rad = P0 - c
    rad -= np.outer(rad @ D, D)
    rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-12)
    NN = np.vstack([rad, rad])
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    dirs = [rad[i] + rad[(i + 1) % n] for i in range(n)]
    acc.add(V, NN, np.zeros((2 * n, 2)), faces, out_dir=np.array(dirs))
    FA.cap(acc, P0, -D)
    FA.cap(acc, P1, D)


# ------------------------------------------------------------------ undertray, tail end, light
def lower_edge_3d(S, n=60):
    """The cowl's lower edge (left), resampled along y, as 3D points + skin normals."""
    uv = TK.smooth_open(TK.to_uv(S, LOWER_EDGE), n=10)
    ys = np.linspace(LOWER_EDGE[0][1] + 0.002, Y_END - 0.002, n)
    u = np.interp(ys, uv[:, 1], uv[:, 0])
    return u, ys


def z_bottom(y):
    return np.interp(y, [0.43, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.87],
                     [0.700, 0.730, 0.770, 0.815, 0.855, 0.884, 0.903, 0.925, 0.948, 0.955])


def undertray(S, cols=34):
    """Loft from the left lower edge (tucked 8 mm up under the cowl, 4 mm in) down over the bottom to the right."""
    u, ys = lower_edge_3d(S)
    rows = []
    for ui, y in zip(u, ys):
        # point 8 mm up the skin from the cowl edge, pushed 4 mm inside the cowl
        uu = ui - 0.008 * np.sign(ui)
        P = S.point(uu, y)
        N = S.normal(uu, y)
        L = P - 0.0045 * N
        zb = float(z_bottom(y))
        ctrl = np.array([L[0] * 0.92, y, zb + 0.004])
        B = np.array([0.0, y, zb])
        t = np.linspace(0, 1, cols // 2 + 1)[:, None]
        half = (1 - t) ** 2 * L + 2 * (1 - t) * t * ctrl + t ** 2 * B
        other = half[::-1].copy()
        other[:, 0] *= -1
        rows.append(np.vstack([half, other[1:]]))
    G = np.array(rows)
    acc = FA.MeshAcc()

    def out_hint(P, N):
        c = np.stack([np.zeros_like(P[..., 0]), P[..., 1], P[..., 2] + 0.08], -1)
        return np.sum((P - c) * N, -1) > 0
    FA.grid_shell(acc, G, 0.0025, out_hint, rim_k=4)
    return acc, G


def tail_end(S, G):
    """Rear face of the tip: cap over the cowl section + the undertray's last row; the tail light sits on it."""
    y = Y_END - 0.0015
    u_low = float(np.interp(y, *TK.smooth_open(TK.to_uv(S, LOWER_EDGE), n=10)[:, ::-1].T))
    uu = np.linspace(u_low, -u_low, 41)
    top = S.point(uu, np.full_like(uu, y)) - 0.0015 * S.normal(uu, np.full_like(uu, y))
    bot = G[-1][::-1].copy()
    bot[:, 1] = y
    loop = np.vstack([top, bot[1:-1]])
    acc = FA.MeshAcc()
    FA.cap(acc, loop, (0, 1.0, 0))
    return acc, top


def tail_light(S):
    """Slim LED bar across the rear face under the tip: red lens + the lit strip behind it."""
    lens, led = FA.MeshAcc(), FA.MeshAcc()
    y = Y_END
    zt = float(S.point(0.0, y)[2])
    zc = zt - 0.024
    w, h, d = 0.050, 0.0075, 0.006

    def slab(acc, w, h, y0, y1, zc, k=8):
        # rounded-end bar (stadium) extruded along +y
        a = np.linspace(-math.pi / 2, math.pi / 2, k)
        right = np.stack([w - h + h * np.cos(a), h * np.sin(a)], 1)
        left = np.stack([-(w - h) - h * np.cos(a), -h * np.sin(a)], 1)
        ring = np.vstack([right, left])
        P0 = np.stack([ring[:, 0], np.full(len(ring), y0), zc + ring[:, 1]], 1)
        prism(acc, P0, (0, 1.0, 0), y1 - y0)
    slab(led, w - 0.003, h - 0.003, y - 0.004, y + 0.0015, zc)
    slab(lens, w, h, y - 0.003, y + d, zc)
    return lens, led


# ------------------------------------------------------------------ plate hanger, plate, indicators
def plate_parts():
    hanger, plate, frame, ind, lens = (FA.MeshAcc() for _ in range(5))
    # arm: from under the tail back and down to the plate (a flat-sided box sweep)
    path = FA.cr_curve([(0.0, 0.770, 0.900), (0.0, 0.835, 0.905), (0.0, 0.890, 0.880), (0.0, 0.925, 0.845), (0.0, 0.951, 0.785)], closed=False, n=6)
    sec = []
    for k in range(len(path)):
        t = k / (len(path) - 1)
        hw, hh = 0.034 - 0.006 * t, 0.010
        sec.append([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)])
    rings = []
    for k, p in enumerate(path):
        tgt = path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]
        tgt /= np.linalg.norm(tgt)
        side = np.array([1.0, 0, 0])
        up = np.cross(tgt, side)
        up /= np.linalg.norm(up)
        rings.append(np.array([p + a * side + b * up for a, b in sec[k]]))
    n = 4
    V = np.vstack(rings)
    faces, dirs = [], []
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
            mid = (rings[k][i] + rings[k][j]) / 2 - path[k]
            dirs.append(mid)
    NN = np.vstack([r - p for r, p in zip(rings, path)])
    hanger.add(V, NN, np.zeros((len(V), 2)), faces, out_dir=np.array(dirs))
    FA.cap(hanger, rings[0], -(path[1] - path[0]))
    FA.cap(hanger, rings[-1], path[-1] - path[-2])
    # plate: 18 x 12 cm, leaning back 18 degrees, blank (no text), in a black frame
    c = np.array([0.0, 0.952, 0.770])
    tilt = math.radians(18)
    up = np.array([0.0, math.sin(tilt), math.cos(tilt)])
    nrm = np.array([0.0, math.cos(tilt), -math.sin(tilt)])
    side = np.array([1.0, 0, 0])

    def rect(acc, w, h, d0, d1, r=0.008, k=4):
        a = []
        for cx, cy, a0 in ((w - r, h - r, 0), (-(w - r), h - r, 90), (-(w - r), -(h - r), 180), (w - r, -(h - r), 270)):
            for t in np.linspace(math.radians(a0), math.radians(a0 + 90), k):
                a.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        a = np.array(a)
        P0 = np.array([c + x * side + y * up + d0 * nrm for x, y in a])
        prism(acc, P0, nrm, d1 - d0)
    rect(frame, 0.098, 0.066, -0.006, 0.004)
    rect(plate, 0.090, 0.058, 0.004, 0.0055, r=0.005)
    # plate light: small black housing over the plate's top edge
    FA.tube(frame, [c + 0.072 * up + 0.012 * nrm - 0.03 * side, c + 0.072 * up + 0.012 * nrm + 0.03 * side], 0.007, seg=10)
    # indicators on short stalks from the arm, LED lenses facing back
    for sx in (1, -1):
        base = np.array([0.026 * sx, 0.905, 0.868])
        tip = np.array([0.075 * sx, 0.915, 0.872])
        FA.tube(ind, [base, tip], 0.0055, seg=10)
        body_c = tip + np.array([0.006 * sx, 0.006, 0.0])
        FA.lathe(ind, [(0.0, -0.014), (0.009, -0.0135), (0.011, -0.012), (0.012, -0.006), (0.012, 0.000)], body_c, (0, 1.0, 0), seg=16)
        FA.lathe(lens, [(0.0118, 0.000), (0.0100, 0.0035), (0.0050, 0.0050), (0.0, 0.0052)], body_c, (0, 1.0, 0), seg=16)
    return hanger, frame, plate, ind, lens


def fasteners(S):
    acc = FA.MeshAcc()
    for y, z in ((0.47, 0.775), (0.60, 0.886)):
        u = TK.u_at(S, y, z)
        for sg in (1, -1):
            P = S.point(sg * u, y)
            N = S.normal(sg * u, y)
            FA.dome(acc, P + 0.0006 * N, N, 0.0042, 0.0018, seg=12, rings=2)
    return acc


# ------------------------------------------------------------------ build
LOOKS = {
    "TailCowl": IO.L_tex("TailCowl", 0.22),
    "TailUnder": IO.L_col((20, 20, 22), 0.6),
    "TailEnd": IO.L_col((24, 25, 28), 0.5),
    "TailLens": IO.L_col((190, 20, 24), 0.05, mat="Glass", transp=0.35, transmit=0.6),
    "TailLED": IO.L_col((255, 40, 36), 0.3, mat="Neon", emit=5.0),
    "PlateHanger": IO.L_col((22, 22, 24), 0.55),
    "PlateFrame": IO.L_col((18, 18, 20), 0.5),
    "Plate": IO.L_col((228, 230, 232), 0.35, refl=0.05),
    "Indicators": IO.L_col((28, 29, 32), 0.4),
    "IndicatorLens": IO.L_col((255, 150, 40), 0.05, mat="Glass", transp=0.2, transmit=0.6),
    "TailFasteners": IO.L_col((44, 45, 48), 0.3, metal=1.0, refl=0.1),
}
TEXFILES = {"TailCowl": "TailCowl_Color.png"}


def build():
    S0 = load_surface(recess=False)
    S = load_surface()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    accs = {}
    accs["TailCowl"], info = FA.panel(S, cowl_outline(S), spacing=0.009, t=T_PANEL)
    accs["TailUnder"], G = undertray(S)
    accs["TailEnd"], _ = tail_end(S, G)
    accs["TailLens"], accs["TailLED"] = tail_light(S)
    accs["PlateHanger"], accs["PlateFrame"], accs["Plate"], accs["Indicators"], accs["IndicatorLens"] = plate_parts()
    accs["TailFasteners"] = fasteners(S)
    FA.paint_panel(os.path.join(TEX, TEXFILES["TailCowl"]), S, info["uv_box"], cowl_paint(S, S0), (1024, 1024))
    parts = {name: acc.obj(name) for name, acc in accs.items()}
    IO.apply_materials(parts, LOOKS, TEXFILES, TEX)
    return parts


def fit_shape(scan_path):
    from mathutils import Matrix
    from mathutils.bvhtree import BVHTree
    import refscan
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob, info = refscan.load_aligned(scan_path)
    ob.data.transform(Matrix.Translation((0.026, 0, 0)))
    me = ob.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    zc, Rc, slope, v0 = 0.76, 0.35, 0.37, 0.40
    H, us, vs = cylchart.sample(bvh, zc, Rc, (-0.75, 0.75), (0.36, 0.92), slope=slope, v0=v0)
    U, V = np.meshgrid(us, vs)
    Z = zc + slope * (V - v0) + (Rc - H) * np.cos(U / Rc)
    ZB = np.interp(V, [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.92],
                   [0.62, 0.635, 0.675, 0.74, 0.795, 0.845, 0.875, 0.895, 0.945, 0.975, 0.99])
    m = np.isfinite(H) & (Z > ZB) & (V > 0.40) & (V < 0.85) & (np.abs(U) < 0.72)
    F, uo, vo = cylchart.pfit(H, us, vs, m, ku=0.025, kv=0.025, lam=0.5)
    np.savez_compressed(SHAPE, H=F, us=uo, vs=vo, zc=zc, Rc=Rc, slope=slope, v0=v0)
    print("wrote", SHAPE)


if __name__ == "__main__":
    if "--scan" in sys.argv:
        fit_shape(sys.argv[sys.argv.index("--scan") + 1])
    else:
        os.makedirs(OUT, exist_ok=True)
        parts = build()
        IO.export_model(MODEL, parts, LOOKS, TEXFILES)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
