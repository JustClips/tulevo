"""Superbike fuel tank: airbox cover (front), tank top with a flush fuel cap, rubber knee pads.

  /home/user/bvenv/bin/python art/blender/superbike/tank.py            build + export art/models/BikeTank
  /home/user/bvenv/bin/python art/blender/superbike/tank.py --scan F   refit tank_shape.npz from the scan

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.

How the shape is made
  Same idea as fairings.py, on a cylinder chart instead of the stadium one (cylchart.py): the scan is
  sampled along rays toward an axis running fore-aft above the engine, made symmetric and fitted with a
  smooth spline (tank_shape.npz, committed). Panels are outlines on that chart. The panel split is
  drawn as regions (whole tank, front region, knee pads) and cut apart with polygon maths, then every
  piece is shrunk by half a panel gap, so neighbouring panels always meet with an even shut line.
  Outline points are given either in chart (u, y) or as a side-view (y, z) point on the tank's left side.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import bikeio as IO  # noqa: E402
import cylchart  # noqa: E402
import fairings as FA  # noqa: E402

MODEL = "BikeTank"
OUT = os.path.join(IO.MODELS, MODEL)
TEX = os.path.join(OUT, "tex")
SHAPE = os.path.join(HERE, "tank_shape.npz")
GAP = 0.0040          # shut line between panels (m)
T_PANEL = 0.003


def load_surface():
    d = np.load(SHAPE)
    return cylchart.CylSurface(d["H"], d["us"], d["vs"], float(d["zc"]), float(d["Rc"]))


# ------------------------------------------------------------------ outline points
def UV(u, v):
    return ("uv", u, v)


def VZ(v, z):
    return ("vz", v, z)


def u_at(S, v, z):
    """Chart u on the left side (u > 0) where the tank surface at row y = v is at height z."""
    uu = np.linspace(0, S.us[-1] - 1e-4, 900)
    zz = S.point(uu, np.full_like(uu, v))[:, 2]
    k = np.where(zz < z)[0]
    if not len(k):
        return uu[-1]
    k = k[0]
    if k == 0:
        return 0.0
    t = (zz[k - 1] - z) / (zz[k - 1] - zz[k])
    return uu[k - 1] + t * (uu[k] - uu[k - 1])


def to_uv(S, pts):
    out = []
    for p in pts:
        out.append((p[1], p[2]) if p[0] == "uv" else (u_at(S, p[1], p[2]), p[1]))
    return np.array(out)


def flat(S, uv):
    uv = np.asarray(uv, float)
    return np.stack([S.to_flat(uv[:, 0], uv[:, 1]), uv[:, 1]], 1)


def unflat(S, sv):
    sv = np.asarray(sv, float)
    return np.stack([S.from_flat(sv[:, 0], sv[:, 1]), sv[:, 1]], 1)


def mirror(uv):
    m = np.asarray(uv, float).copy()
    m[:, 0] *= -1
    return m


# whole tank, left half: front centre -> front edge -> lower edge -> rear edge -> rear centre
R_HALF = [UV(0.0, -0.379), UV(0.07, -0.377), VZ(-0.370, 0.875), VZ(-0.360, 0.850), VZ(-0.345, 0.825), VZ(-0.327, 0.808),
          VZ(-0.30, 0.800), VZ(-0.20, 0.801), VZ(-0.10, 0.802), VZ(0.0, 0.802), VZ(0.10, 0.803),
          VZ(0.155, 0.807), VZ(0.180, 0.815), VZ(0.191, 0.832), VZ(0.196, 0.852), UV(0.07, 0.198), UV(0.0, 0.198)]
# the split between the airbox cover and the tank top: from inside the knee pad up and over the top centre
SPLIT_HALF = [VZ(-0.060, 0.79), VZ(-0.060, 0.92), VZ(-0.070, 0.950), VZ(-0.088, 0.968), UV(0.17, -0.106), UV(0.13, -0.130),
              UV(0.07, -0.146), UV(0.0, -0.150)]
# rubber knee pad (left), side-view outline; its bottom and rear run past the tank edge and get cut by it
KNEE = [VZ(-0.075, 0.790), VZ(-0.090, 0.815), VZ(-0.097, 0.850), VZ(-0.097, 0.890), VZ(-0.086, 0.922), VZ(-0.064, 0.940),
        VZ(-0.020, 0.946), VZ(0.030, 0.944), VZ(0.070, 0.935), VZ(0.100, 0.920), VZ(0.130, 0.898), VZ(0.155, 0.876),
        VZ(0.172, 0.862), VZ(0.190, 0.845), VZ(0.205, 0.820), VZ(0.200, 0.790), VZ(0.170, 0.784), VZ(0.100, 0.784),
        VZ(0.000, 0.785)]
KNEE_TOP = KNEE[5:13]
CAP_V, CAP_HOLE = -0.065, 0.0485       # fuel cap centre (chart v on the top centre line) and hole radius


def smooth_closed(P, n=10):
    return FA.cr_curve([tuple(p) for p in P], closed=True, n=n)


def smooth_open(P, n=10):
    return FA.cr_curve([tuple(p) for p in P], closed=False, n=n)


def poly_flat(S, uv):
    return Polygon(flat(S, uv)).buffer(0)


def regions(S):
    """Panel outlines in chart (u, v): {name: (outline, [holes])}."""
    R = smooth_closed(FA.mirror_loop(to_uv(S, R_HALF)))
    sp = smooth_open(to_uv(S, SPLIT_HALF))
    umax = S.us[-1] - 0.002
    front_half = np.vstack([[(0.0, -0.415), (umax, -0.415), (umax, sp[0, 1])], sp])
    Fr = FA.mirror_loop(front_half)
    kl = smooth_closed(to_uv(S, KNEE))
    kr = mirror(kl)[::-1]
    pR, pF, pKL, pKR = (poly_flat(S, x) for x in (R, Fr, kl, kr))
    c = np.array([0.0, CAP_V])
    ang = np.linspace(0, 2 * math.pi, 72, endpoint=False)
    hole = Polygon(np.stack([CAP_HOLE * np.cos(ang), c[1] + CAP_HOLE * np.sin(ang)], 1))   # in flat (s, v): s = 0 on the centre line
    pieces = {
        "AirboxCover": pR.intersection(pF).difference(pKL).difference(pKR),
        "TankTop": pR.difference(pF).difference(pKL).difference(pKR),
        "KneePadL": pR.intersection(pKL),
        "KneePadR": pR.intersection(pKR),
    }
    out = {}
    for name, poly in pieces.items():
        g = poly.buffer(-GAP / 2, join_style="round", quad_segs=4)
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda q: q.area)
        if name == "TankTop":
            g = g.difference(hole)
        ext = unflat(S, np.array(g.exterior.coords)[:-1])
        holes = [unflat(S, np.array(i.coords)[:-1]) for i in g.interiors]
        out[name] = (ext, holes)
    return out, {"split": sp, "knee_top": smooth_open(to_uv(S, KNEE_TOP))}


# ------------------------------------------------------------------ paint
def dist_flat(S, pts_uv, u, v):
    """Distance on the skin (flat chart) from (|u|, v) to the polyline pts_uv (left side)."""
    P = flat(S, pts_uv)
    s = np.abs(S.to_flat(u, v))
    return FA._dist_poly(P, s, v)


def top_paint(S, lines):
    def paint(u, v):
        col = np.empty(np.shape(u) + (3,))
        col[:] = IO.WHITE
        d = dist_flat(S, lines["knee_top"], u, v)
        col[(d > 0.0085) & (d < 0.0140) & (v < 0.185)] = IO.ACCENT
        return col
    return paint


def airbox_paint(S, lines):
    def paint(u, v):
        col = np.empty(np.shape(u) + (3,))
        col[:] = IO.CHAR
        d = dist_flat(S, lines["split"], u, v)
        col[(d > 0.0070) & (d < 0.0125)] = IO.ACCENT
        return col
    return paint


def knee_tex(path, box, N=1024):
    """Grip rubber: small raised diamonds on a 7 mm grid, smooth 5 mm border (border drawn by distance in UV)."""
    w, h = box[2] - box[0], box[3] - box[1]
    H = int(N * h / w) // 8 * 8
    s = box[0] + (np.arange(N) + 0.5) / N * w
    v = box[3] - (np.arange(H) + 0.5) / H * h
    Sg, Vg = np.meshgrid(s, v)
    p = 0.007
    a = (Sg + Vg) / p
    b = (Sg - Vg) / p
    da = np.abs(a - np.round(a))
    db = np.abs(b - np.round(b))
    dm = np.maximum(da, db)                          # 0 at diamond centres, 0.5 at the grooves
    t = np.clip((0.36 - dm) / 0.06, 0, 1)
    col = np.empty(Sg.shape + (3,))
    base = np.array([22, 22, 24.0])
    top = np.array([50, 51, 55.0])
    col[:] = base + (top - base) * t[..., None]
    return col, H


# ------------------------------------------------------------------ 3D details
def surf_lathe(acc, S, c_sv, profile, seg=48):
    """Ring that follows the skin: profile (r, h) -> flat offset r round c_sv, lifted h along the skin normal.
    Profile runs like FA.lathe's: the face normal is to the right of the direction of travel (up then inward = out/up)."""
    prof = np.asarray(profile, float)
    n = len(prof)
    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    uc = float(S.from_flat(np.array([c_sv[0]]), np.array([c_sv[1]]))[0])
    C = S.point(uc, c_sv[1])
    V, NN = [], []
    for j, (r, hh) in enumerate(prof):
        s = c_sv[0] + r * np.cos(ang)
        v = c_sv[1] + r * np.sin(ang)
        u = S.from_flat(s, v)
        N = S.normal(u, v)
        P = S.point(u, v)
        er = P - C
        er -= np.sum(er * N, 1, keepdims=True) * N
        er /= np.maximum(np.linalg.norm(er, axis=1, keepdims=True), 1e-12)
        jp, jn = prof[max(j - 1, 0)], prof[min(j + 1, n - 1)]
        dr, dh = jn[0] - jp[0], jn[1] - jp[1]
        nn = dh * er - dr * N
        nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
        V.append(P + hh * N)
        NN.append(nn)
    V, NN = np.vstack(V), np.vstack(NN)
    faces, dirs = [], []
    for j in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((j * seg + k, j * seg + k2, (j + 1) * seg + k2, (j + 1) * seg + k))
            dirs.append(NN[j * seg + k] + NN[(j + 1) * seg + k])
    UV = np.stack([np.tile(np.arange(seg) / seg, n), np.repeat(np.arange(n) / max(1, n - 1), seg)], 1)
    acc.add(V, NN, UV, faces, out_dir=np.array(dirs))


def fuel_cap(S):
    ring, lid, lock = FA.MeshAcc(), FA.MeshAcc(), FA.MeshAcc()
    c = (0.0, CAP_V)
    # flush aluminium ring: lip on the paint, then a short well down to the lid
    surf_lathe(ring, S, c, [(0.0480, -0.006), (0.0485, -0.0005), (0.0520, 0.0004), (0.0528, 0.0012), (0.0522, 0.0020),
                            (0.0500, 0.0026), (0.0470, 0.0026), (0.0455, 0.0018), (0.0448, 0.0002), (0.0446, -0.0022)], seg=64)
    # six screws on the lip
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        s, v = 0.0496 * math.cos(a), CAP_V + 0.0496 * math.sin(a)
        u = float(S.from_flat(np.array([s]), np.array([v]))[0])
        P = S.point(u, v)
        N = S.normal(u, v)
        FA.dome(ring, P + 0.0024 * N, N, 0.0021, 0.0012, seg=10, rings=2)
    # lid: slightly domed disc with a raised rim
    surf_lathe(lid, S, c, [(0.0446, -0.0022), (0.0440, 0.0006), (0.0432, 0.0016), (0.0410, 0.0019), (0.0390, 0.0015),
                           (0.030, 0.0020), (0.018, 0.0024), (0.006, 0.0026), (0.0005, 0.0026)], seg=64)
    # hinge block at the front, lock barrel near it
    u0 = float(S.from_flat(np.array([0.0]), np.array([CAP_V - 0.036]))[0])
    P = S.point(u0, CAP_V - 0.036)
    N = S.normal(u0, CAP_V - 0.036)
    FA.lathe(lock, [(0.0080, 0.0000), (0.0080, 0.0042), (0.0072, 0.0050), (0.0, 0.0050)], P, N, seg=24)
    return ring, lid, lock


def fasteners(S):
    acc = FA.MeshAcc()
    for v, z in ((-0.300, 0.835), (-0.125, 0.862)):
        u = u_at(S, v, z)
        for sg in (1, -1):
            P = S.point(sg * u, v)
            N = S.normal(sg * u, v)
            FA.dome(acc, P + 0.0006 * N, N, 0.0042, 0.0018, seg=12, rings=2)
    return acc


# ------------------------------------------------------------------ build
LOOKS = {
    "AirboxCover": IO.L_tex("AirboxCover", 0.24),
    "TankTop": IO.L_tex("TankTop", 0.22),
    "KneePad": IO.L_tex("KneePad", 0.75, refl=0.0, mat="Rubber", coat=0.0),
    "FuelCapRing": IO.L_col((196, 199, 204), 0.22, metal=1.0, mat="Metal", refl=0.25),
    "FuelCapLid": IO.L_col((150, 153, 160), 0.28, metal=1.0, mat="Metal", refl=0.15),
    "FuelCapLock": IO.L_col((30, 31, 34), 0.4, metal=1.0, mat="Metal", refl=0.1),
    "TankFasteners": IO.L_col((44, 45, 48), 0.3, metal=1.0, refl=0.1),
}
TEXFILES = {"AirboxCover": "AirboxCover_Color.png", "TankTop": "TankTop_Color.png", "KneePad": "KneePad_Color.png"}


def build():
    S = load_surface()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    outl, lines = regions(S)
    accs, boxes = {}, {}
    for name in ("AirboxCover", "TankTop", "KneePadL"):
        ol, holes = outl[name]
        accs[name], info = FA.panel(S, ol, holes, spacing=0.010, t=T_PANEL)
        boxes[name] = info["uv_box"]
    ol, holes = outl["KneePadR"]
    accs["KneePadR"], _ = FA.panel(S, ol, holes, spacing=0.010, t=T_PANEL, uv_box=boxes["KneePadL"], uv_sign=-1.0)
    accs["FuelCapRing"], accs["FuelCapLid"], accs["FuelCapLock"] = fuel_cap(S)
    accs["TankFasteners"] = fasteners(S)
    FA.paint_panel(os.path.join(TEX, TEXFILES["TankTop"]), S, boxes["TankTop"], top_paint(S, lines), (1024, 640))
    FA.paint_panel(os.path.join(TEX, TEXFILES["AirboxCover"]), S, boxes["AirboxCover"], airbox_paint(S, lines), (1024, 512))
    col, H = knee_tex(None, boxes["KneePadL"])
    IO.save_png(os.path.join(TEX, TEXFILES["KneePad"]), col / 255.0)
    parts = {name: acc.obj(name) for name, acc in accs.items()}
    IO.apply_materials(parts, LOOKS, TEXFILES, TEX)
    return parts


# ------------------------------------------------------------------ shape fit from the scan (--scan)
def fit_shape(scan_path):
    from mathutils import Matrix
    from mathutils.bvhtree import BVHTree
    import refscan
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob, info = refscan.load_aligned(scan_path)
    ob.data.transform(Matrix.Translation((0.026, 0, 0)))
    me = ob.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    zc, Rc = 0.62, 0.50
    H, us, vs = cylchart.sample(bvh, zc, Rc, (-0.47, 0.47), (-0.42, 0.21))
    U, V = np.meshgrid(us, vs)
    r = Rc - H
    Z, X = zc + r * np.cos(U / Rc), r * np.sin(U / Rc)
    m = np.isfinite(H) & (Z > 0.78) & (np.abs(X) < 0.235) & (V > -0.40) & (V < 0.19) & (np.abs(U) < 0.46)
    F, uo, vo = cylchart.pfit(H, us, vs, m, ku=0.035, kv=0.035)
    np.savez_compressed(SHAPE, H=F, us=uo, vs=vo, zc=zc, Rc=Rc)
    print("wrote", SHAPE)


if __name__ == "__main__":
    if "--scan" in sys.argv:
        fit_shape(sys.argv[sys.argv.index("--scan") + 1])
    else:
        os.makedirs(OUT, exist_ok=True)
        parts = build()
        IO.export_model(MODEL, parts, LOOKS, TEXFILES)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
