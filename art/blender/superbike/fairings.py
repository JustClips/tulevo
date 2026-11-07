"""Superbike fairings: nose cowl with headlights and centre intake, windscreen, side panels, belly pan.

  /home/user/bvenv/bin/python art/blender/superbike/fairings.py            build + export
  /home/user/bvenv/bin/python art/blender/superbike/fairings.py --scan F   refit the shape from the scan

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
Needs numpy + scipy in the venv.

How the shapes are made
  The panel surfaces follow a CC-BY-4.0 phone scan of a real bike ("BMW S 1000 RR - HSLU Midterm
  3DMOD4RT" by noe_auf on Sketchfab; credit goes in the game description). The scan is used for its
  shape only and is not committed: refscan.py stands it upright on our wheels, then this file samples
  it on an unrolled "stadium" chart (u = distance round the bike from the nose centre, +u = left side,
  z = height), makes it symmetric and fits a smooth spline to the fairing areas. The fitted depth grid
  is saved to fairing_shape.npz, so the build itself does not need the scan.
  Every panel is drawn as an outline (plus holes) in that (u, z) chart, triangulated in a flattened
  copy of the chart (3D arc length round the bike), mapped onto the fitted surface, given a real
  thickness and a rolled edge. Panel lines are just gaps between neighbouring outlines.
  Graphics are our own (no logos, names or the maker's livery).
"""
import json
import math
import os
import struct
import sys

import bpy
import bmesh  # noqa: F401  (after bpy)
import numpy as np
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt
from scipy.interpolate import RectBivariateSpline
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo as G  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "art", "models", "BikeFairings")
TEX = os.path.join(OUT, "tex")
SHAPE = os.path.join(HERE, "fairing_shape.npz")
STUDS = 3.6
MM = 0.001

# stadium chart: front half circle round (0, YC) of radius R, straight sides x = +-R behind it
YC, R = -0.52, 0.42
UQ = R * math.pi / 2                      # u where the straight side starts (y = YC)
CH_U, CH_Z = 1.34, (0.0, 1.25)            # chart extent: u in [-CH_U, CH_U], z in CH_Z


def stadium(u):
    """Point on the stadium at chart u, its outward normal, and both derivatives along u (plan view)."""
    u = np.asarray(u, float)
    s = np.where(u >= 0, 1.0, -1.0)
    a = np.abs(u)
    f = a <= UQ
    ph = np.minimum(a, UQ) / R
    sn, cs = np.sin(ph), np.cos(ph)
    px = np.where(f, s * R * sn, s * R)
    py = np.where(f, YC - R * cs, YC + a - UQ)
    nx = np.where(f, s * sn, s)
    ny = np.where(f, -cs, 0.0)
    dpx = np.where(f, cs, 0.0)
    dpy = np.where(f, s * sn, s)
    dnx = np.where(f, cs / R, 0.0)
    dny = np.where(f, s * sn / R, 0.0)
    return px, py, nx, ny, dpx, dpy, dnx, dny


class Surface:
    """Smooth fitted fairing skin: depth h(u, z) inward from the stadium."""

    def __init__(self, H, us, zs):
        self.H, self.us, self.zs = H, us, zs
        self.spl = RectBivariateSpline(zs, us, H, kx=3, ky=3)
        # flattening: s = 3D arc length along constant-z rows from the centre line
        uf = np.linspace(-CH_U, CH_U, 1341)
        self.zf = np.linspace(CH_Z[0], CH_Z[1], 126)
        Uf, Zf = np.meshgrid(uf, self.zf)
        Su, _ = self.derivs(Uf, Zf)
        sp = np.linalg.norm(Su, axis=-1)
        S = np.concatenate([np.zeros((len(self.zf), 1)), np.cumsum((sp[:, 1:] + sp[:, :-1]) / 2 * np.diff(uf), axis=1)], 1)
        S -= S[:, [len(uf) // 2]]
        self.s_spl = RectBivariateSpline(self.zf, uf, S, kx=3, ky=3)
        self.sf = np.linspace(S[:, 0].max(), S[:, -1].min(), 1341)
        Ui = np.stack([np.interp(self.sf, row, uf) for row in S])
        self.u_spl = RectBivariateSpline(self.zf, self.sf, Ui, kx=3, ky=3)

    def h(self, u, z, du=0, dz=0):
        return self.spl(z, u, dx=dz, dy=du, grid=False)

    def point(self, u, z):
        u, z = np.broadcast_arrays(np.asarray(u, float), np.asarray(z, float))
        px, py, nx, ny = stadium(u)[:4]
        h = self.h(u, z)
        return np.stack([px - h * nx, py - h * ny, z], -1)

    def derivs(self, u, z):
        u, z = np.broadcast_arrays(np.asarray(u, float), np.asarray(z, float))
        px, py, nx, ny, dpx, dpy, dnx, dny = stadium(u)
        h, hu, hz = self.h(u, z), self.h(u, z, du=1), self.h(u, z, dz=1)
        Su = np.stack([dpx - hu * nx - h * dnx, dpy - hu * ny - h * dny, np.zeros_like(u)], -1)
        Sz = np.stack([-hz * nx, -hz * ny, np.ones_like(u)], -1)
        return Su, Sz

    def normal(self, u, z):
        Su, Sz = self.derivs(u, z)
        n = np.cross(Su, Sz)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return n

    def to_flat(self, u, z):
        return self.s_spl(z, u, grid=False)

    def from_flat(self, s, z):
        return self.u_spl(z, s, grid=False)


def load_surface():
    d = np.load(SHAPE)
    return Surface(d["H"], d["us"], d["zs"])


# ------------------------------------------------------------------ 2D curve helpers (chart space)
def cr_curve(pts, closed=True, n=24):
    """Centripetal Catmull-Rom through pts, n samples per span."""
    P = np.asarray(pts, float)
    if closed:
        Q = np.vstack([P[-1], P, P[0], P[1]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** 0.5
        for t in np.linspace(t1, t2, n, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not closed:
        out.append(P[-1])
    return np.array(out)


def mirror_loop(half):
    """Left-half path from the centre line back to the centre line -> full symmetric closed loop."""
    H = np.asarray(half, float)
    M = H[::-1].copy()
    M[:, 0] *= -1
    return np.vstack([H, M[1:-1]])


def signed_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def pip(poly, X, Y):
    inside = np.zeros(np.shape(X), bool)
    x, y = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    for a, b, c, d in zip(x, y, x2, y2):
        cond = (b > Y) != (d > Y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = a + (Y - b) * (c - a) / (d - b)
        inside ^= cond & (X < xi)
    return inside


def resample_closed(P, step):
    """Resample a closed polyline at an even step (same units as P)."""
    Q = np.vstack([P, P[:1]])
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
    n = max(8, int(round(d[-1] / step)))
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.stack([np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])], 1)


# ------------------------------------------------------------------ mesh assembly
class MeshAcc:
    """Vertices with their own normals (custom split normals) + uv per vertex."""

    def __init__(self):
        self.v, self.n, self.uv, self.f = [], [], [], []

    def add(self, V, N, UV, F, out_dir=None):
        """F faces as index tuples into V. out_dir (per face, 3) = which way the face must point."""
        o = len(self.v)
        V = np.asarray(V, float)
        for k, f in enumerate(F):
            if out_dir is not None:
                P = V[list(f)]
                nn = np.cross(P[1] - P[0], P[2] - P[0])
                if nn @ out_dir[k] < 0:
                    f = f[::-1]
            self.f.append(tuple(i + o for i in f))
        self.v.extend(map(tuple, V))
        self.n.extend(map(tuple, np.asarray(N, float)))
        self.uv.extend(map(tuple, np.asarray(UV, float)))

    def merge(self, other):
        o = len(self.v)
        self.v += other.v
        self.n += other.n
        self.uv += other.uv
        self.f += [tuple(i + o for i in f) for f in other.f]

    def obj(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate()
        lay = me.uv_layers.new(name="UVMap")
        uv = np.array(self.uv, np.float32)
        li = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", li)
        lay.data.foreach_set("uv", uv[li].ravel())
        for p in me.polygons:
            p.use_smooth = True
        n = np.array(self.n, float)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        me.normals_split_custom_set_from_vertices([tuple(x) for x in n])
        me.update()
        return G.new_obj(name, me)


def panel(surf, outline, holes=(), spacing=0.012, t=0.003, offset=0.0, rim_k=4, uv_box=None, back=True, uv_sign=1.0):
    """Shell panel on the fitted surface. outline / holes: closed loops in chart (u, z).
    offset lifts the panel off the fitted skin along its normal (e.g. a screen sitting on the cowl).
    Returns (MeshAcc, info) - the outer skin, the inner skin and a rolled edge round every loop."""
    loops2 = [np.asarray(outline, float)] + [np.asarray(h, float) for h in holes]
    flat = []
    for k, L in enumerate(loops2):
        F = np.stack([surf.to_flat(L[:, 0], L[:, 1]), L[:, 1]], 1)
        F = resample_closed(F, spacing * 0.55)
        a = signed_area(F)
        if (k == 0) != (a > 0):          # outline CCW, holes CW in the flat (s, z) plane
            F = F[::-1]
        flat.append(F)
    # interior points on a staggered grid in (s, z)
    allb = np.vstack(flat)
    s0, z0 = allb.min(0) - spacing
    s1, z1 = allb.max(0) + spacing
    rows = np.arange(z0, z1, spacing * 0.866)
    pts = []
    for i, z in enumerate(rows):
        ss = np.arange(s0 + (spacing / 2 if i % 2 else 0), s1, spacing)
        pts.append(np.stack([ss, np.full_like(ss, z)], 1))
    pts = np.vstack(pts)
    ins = pip(flat[0], pts[:, 0], pts[:, 1])
    for h in flat[1:]:
        ins &= ~pip(h, pts[:, 0], pts[:, 1])
    pts = pts[ins]
    tree = cKDTree(allb)
    dist, _ = tree.query(pts)
    pts = pts[dist > spacing * 0.6]
    nb = len(allb)
    coords = np.vstack([allb, pts])
    edges, o = [], 0
    for F in flat:
        n = len(F)
        edges += [(o + i, o + (i + 1) % n) for i in range(n)]
        o += n
    vo, eo, fo, ov, oe, of = delaunay_2d_cdt([Vector(p) for p in coords], edges, [], 1, 1e-9)
    VV = np.array([tuple(v) for v in vo])
    tri = [f for f in fo if len(f) == 3]
    C = VV[np.array(tri)].mean(1)
    keep = pip(flat[0], C[:, 0], C[:, 1])
    for h in flat[1:]:
        keep &= ~pip(h, C[:, 0], C[:, 1])
    tri = [f for f, k in zip(tri, keep) if k]
    # map to 3D
    s, z = VV[:, 0], VV[:, 1]
    u = surf.from_flat(s, z)
    N = surf.normal(u, z)
    P = surf.point(u, z) + offset * N
    if uv_box is None:
        uv_box = ((s * uv_sign).min(), z.min(), (s * uv_sign).max(), z.max())
    UV = np.stack([(s * uv_sign - uv_box[0]) / (uv_box[2] - uv_box[0]), (z - uv_box[1]) / (uv_box[3] - uv_box[1])], 1)
    acc = MeshAcc()
    acc.add(P, N, UV, [tuple(f) for f in tri], out_dir=N[np.array(tri)].mean(1))
    if back:
        acc.add(P - t * N, -N, UV, [tuple(f) for f in tri], out_dir=-N[np.array(tri)].mean(1))
    # rolled edges: rings from the outer skin round to the inner skin
    for F in flat:
        uL = surf.from_flat(F[:, 0], F[:, 1])
        zL = F[:, 1]
        PL = surf.point(uL, zL)
        NL = surf.normal(uL, zL)
        PL = PL + offset * NL
        T = np.roll(PL, -1, 0) - np.roll(PL, 1, 0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        E = np.cross(T, NL)
        E /= np.linalg.norm(E, axis=1, keepdims=True)
        n = len(F)
        ring_v, ring_n = [], []
        K = rim_k if back else max(2, rim_k // 2)
        a_end = math.pi if back else math.pi / 2
        for k in range(K + 1):
            a = a_end * k / K
            d = math.cos(a) * NL + math.sin(a) * E
            ring_v.append(PL - (t / 2) * NL + (t / 2) * d)
            ring_n.append(d)
        RV = np.vstack(ring_v)
        RN = np.vstack(ring_n)
        RUV = np.tile(np.stack([(F[:, 0] * uv_sign - uv_box[0]) / (uv_box[2] - uv_box[0]), (zL - uv_box[1]) / (uv_box[3] - uv_box[1])], 1), (K + 1, 1))
        faces, dirs = [], []
        for k in range(K):
            for i in range(n):
                j = (i + 1) % n
                faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
                dirs.append((RN[k * n + i] + RN[(k + 1) * n + i]))
        acc.add(RV, RN, RUV, faces, out_dir=np.array(dirs))
    return acc, {"uv_box": uv_box}


# ------------------------------------------------------------------ outlines (chart u, z; left half)
COWL_HALF = [
    (0.000, 0.690), (0.05, 0.691), (0.12, 0.694), (0.20, 0.700), (0.28, 0.708), (0.36, 0.719), (0.43, 0.733),
    (0.49, 0.750), (0.535, 0.768), (0.565, 0.790), (0.570, 0.812), (0.550, 0.838), (0.515, 0.866), (0.494, 0.900),
    (0.492, 0.938), (0.512, 0.972), (0.556, 1.000), (0.610, 1.020), (0.652, 1.032), (0.676, 1.041), (0.684, 1.052),
    (0.668, 1.059), (0.62, 1.056), (0.54, 1.046), (0.46, 1.034), (0.38, 1.018), (0.30, 0.993), (0.24, 0.961), (0.18, 0.916),
    (0.12, 0.871), (0.08, 0.831), (0.056, 0.796), (0.036, 0.762), (0.018, 0.740), (0.000, 0.732),
]
HEADLIGHT = [
    (0.088, 0.728), (0.115, 0.713), (0.20, 0.717), (0.28, 0.725), (0.35, 0.735), (0.41, 0.748), (0.455, 0.764),
    (0.478, 0.778), (0.452, 0.789), (0.40, 0.793), (0.33, 0.793), (0.25, 0.788), (0.18, 0.778), (0.13, 0.762), (0.102, 0.746),
]


GAP = 0.0045        # panel line width (chart z ~ meters)
SIDE = [
    # top edge: follows the cowl's lower edge one panel gap below it
    (0.105, 0.6865), (0.13, 0.6895), (0.20, 0.6955), (0.28, 0.7035), (0.36, 0.7145), (0.43, 0.7285), (0.49, 0.7455),
    (0.532, 0.7625), (0.556, 0.778), (0.578, 0.784),
    # then back under where the tank goes
    (0.605, 0.770), (0.645, 0.750), (0.70, 0.735), (0.80, 0.727), (0.90, 0.722), (1.00, 0.717), (1.10, 0.707),
    (1.19, 0.694), (1.24, 0.684), (1.255, 0.670), (1.24, 0.657),
    # top of the cut-out, round into the rear edge of the tongue
    (1.15, 0.651), (1.05, 0.643), (0.96, 0.636), (0.905, 0.628), (0.862, 0.612), (0.846, 0.588), (0.872, 0.548),
    (0.893, 0.508), (0.890, 0.478), (0.866, 0.463), (0.833, 0.465),
    # front edge of the tongue, then the bottom edge forward to the tip
    (0.804, 0.483), (0.772, 0.517), (0.737, 0.556), (0.700, 0.590), (0.64, 0.594), (0.56, 0.590), (0.47, 0.592),
    (0.40, 0.601), (0.33, 0.614), (0.25, 0.634), (0.18, 0.656), (0.135, 0.674),
]


def side_loop(sign=1):
    L = cr_curve(SIDE, closed=True, n=10)
    L[:, 0] *= sign
    return L


def cowl_loops():
    out = cr_curve(mirror_loop(COWL_HALF), closed=True, n=10)
    hl = cr_curve(HEADLIGHT, closed=True, n=10)
    hr = hl.copy()
    hr[:, 0] *= -1
    return out, [hl, hr]


# side panel gills: three slanted slots just behind the cowl's rear corner (centre, half length, half width)
GILLS = [((0.598, 0.656), 0.030, 0.0065), ((0.628, 0.653), 0.032, 0.0065), ((0.658, 0.650), 0.030, 0.0065)]
GILL_LEAN = 0.55          # slots lean back (du per dz)

# screen: its lower side edges sit on the cowl just outside the V edge
SCREEN_EDGE = [(0.138, 0.858), (0.158, 0.872), (0.214, 0.915), (0.274, 0.959), (0.334, 0.991), (0.392, 1.010), (0.432, 1.019)]
SCREEN_BOTTOM_Z = 0.858
SCREEN_TOP = (0.0, -0.505, 1.105)
SCREEN_LIFT = 0.0035
# centre air intake below the screen: left half (V edge from the chin up to the screen's bottom edge)
INTAKE_HALF = [(0.0, 0.7335), (0.018, 0.7415), (0.036, 0.7635), (0.056, 0.7975), (0.080, 0.8325), (0.103, 0.8585), (0.0, 0.8585)]

# black inner panels behind the cowl's rear edge / above the side panel
INNER = [(0.468, 0.875), (0.484, 0.805), (0.525, 0.760), (0.60, 0.733), (0.70, 0.716), (0.80, 0.711), (0.86, 0.716),
         (0.875, 0.76), (0.85, 0.80), (0.78, 0.84), (0.70, 0.88), (0.62, 0.935), (0.555, 0.975), (0.505, 0.955)]
INNER_DEPTH = 0.013

# small dome-head fasteners (chart u, z) on the left; mirrored to the right
FASTENERS_COWL = [(0.515, 0.905), (0.545, 0.800), (0.06, 0.700)]
FASTENERS_SIDE = [(0.60, 0.752), (1.215, 0.676), (0.858, 0.478), (0.70, 0.602), (0.95, 0.704)]
FASTENERS_SCREEN = [(0.19, 0.898), (0.29, 0.968), (0.385, 1.007)]
MIRROR_BLANK = (0.592, 1.030)


def gill_loop(c, hl, hw, sign=1):
    """Slot with round ends, long axis up (leaning back by GILL_LEAN), in chart space."""
    u0, z0 = c
    pts = []
    for a in np.linspace(0, math.pi, 12):            # top end
        pts.append((hw * math.cos(a), (hl - hw) + hw * math.sin(a)))
    for a in np.linspace(math.pi, 2 * math.pi, 12):  # bottom end
        pts.append((hw * math.cos(a), -(hl - hw) + hw * math.sin(a)))
    P = np.array(pts)
    P = np.stack([u0 + P[:, 0] + P[:, 1] * GILL_LEAN, z0 + P[:, 1]], 1)
    P[:, 0] *= sign
    return P


def side_loops(sign=1):
    return side_loop(sign), [gill_loop(c, hl, hw, sign) for c, hl, hw in GILLS]


# ------------------------------------------------------------------ 3D helpers
def loop3d(surf, loop, step, offset=0.0, ccw=True):
    """Chart loop -> evenly spaced 3D loop on the skin (+offset along the normal). CCW in (s, z)."""
    L = np.asarray(loop, float)
    F = np.stack([surf.to_flat(L[:, 0], L[:, 1]), L[:, 1]], 1)
    F = resample_closed(F, step)
    if (signed_area(F) > 0) != ccw:
        F = F[::-1]
    u = surf.from_flat(F[:, 0], F[:, 1])
    N = surf.normal(u, F[:, 1])
    P = surf.point(u, F[:, 1]) + offset * N
    return P, N, F


def cap(acc, P, n_dir, uv=None):
    """Flat-ish cap over a 3D loop, facing n_dir (CDT in the loop's best-fit plane)."""
    c = P.mean(0)
    n = np.asarray(n_dir, float)
    n /= np.linalg.norm(n)
    a = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    Q = np.stack([(P - c) @ a, (P - c) @ b], 1)
    m = len(P)
    vo, eo, fo, ov, oe, of = delaunay_2d_cdt([Vector(q) for q in Q], [(i, (i + 1) % m) for i in range(m)], [], 1, 1e-9)
    VV = np.array([tuple(v) for v in vo])
    tri = [f for f in fo if len(f) == 3]
    C = VV[np.array(tri)].mean(1)
    tri = [f for f, k in zip(tri, pip(Q, C[:, 0], C[:, 1])) if k]
    # verts: map back (CDT may add none for a simple loop, but be safe)
    V3 = c + VV[:, :1] * a + VV[:, 1:2] * b
    # snap original verts back to their 3D positions (keeps non-planar loops closed)
    for i, o in enumerate(ov):
        if o:
            V3[i] = P[o[0]]
    UV = uv if uv is not None else (VV - VV.min(0)) / max(1e-9, (VV.max(0) - VV.min(0)).max())
    acc.add(V3, np.tile(n, (len(V3), 1)), UV[: len(V3)] if uv is not None else UV, [tuple(f) for f in tri],
            out_dir=np.tile(n, (len(tri), 1)))


def sleeve(acc, P, D, depth, rings=3, taper=0.0, close=True, cap_uv=None):
    """Tube from a 3D loop P going depth along D, shrinking toward the axis by taper. Faces look inward
    (it is seen from inside the opening). Returns the last ring."""
    D = np.asarray(D, float)
    D /= np.linalg.norm(D)
    c = P.mean(0)
    R = []
    for k in range(rings + 1):
        f = k / rings
        R.append(P + (c - P) * taper * f + D * depth * f)
    n = len(P)
    V = np.vstack(R)
    faces, dirs, NN = [], [], []
    for k in range(rings + 1):
        rad = R[k] - (c + D * depth * k / rings)
        rad -= np.outer(rad @ D, D)
        NN.append(-rad / np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9))
    NN = np.vstack(NN)
    for k in range(rings):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
            dirs.append(NN[k * n + i])
    UV = np.stack([np.tile(np.arange(n) / n, rings + 1), np.repeat(np.arange(rings + 1) / rings, n)], 1)
    acc.add(V, NN, UV, faces, out_dir=np.array(dirs))
    if close:
        cap(acc, R[-1], -D, cap_uv)
    return R[-1]


def tube(acc, pts, r, seg=10, closed=False, caps=True):
    pts = np.asarray(pts, float)
    n = len(pts)
    T = np.gradient(pts, axis=0) if not closed else (np.roll(pts, -1, 0) - np.roll(pts, 1, 0))
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0, 0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    Nv = [ref - T[0] * (ref @ T[0])]
    Nv[0] /= np.linalg.norm(Nv[0])
    for i in range(1, n):
        v = Nv[-1] - T[i] * (Nv[-1] @ T[i])
        Nv.append(v / np.linalg.norm(v))
    Nv = np.array(Nv)
    B = np.cross(T, Nv)
    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    V, NN = [], []
    for i in range(n):
        d = np.outer(np.cos(ang), Nv[i]) + np.outer(np.sin(ang), B[i])
        V.append(pts[i] + r * d)
        NN.append(d)
    V, NN = np.vstack(V), np.vstack(NN)
    m = n if closed else n - 1
    faces, dirs = [], []
    for i in range(m):
        i2 = (i + 1) % n
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k2, i2 * seg + k2, i2 * seg + k))
            dirs.append(NN[i * seg + k] + NN[i * seg + k2])
    UV = np.stack([np.repeat(np.arange(n) / max(1, n - 1), seg), np.tile(ang / (2 * math.pi), n)], 1)
    acc.add(V, NN, UV, faces, out_dir=np.array(dirs))
    if caps and not closed:
        for i, sgn in ((0, -1), (n - 1, 1)):
            c = pts[i]
            ring = V[i * seg:(i + 1) * seg]
            vv = np.vstack([ring, c])
            fs = [(k, (k + 1) % seg, seg) for k in range(seg)]
            acc.add(vv, np.tile(T[i] * sgn, (seg + 1, 1)), np.zeros((seg + 1, 2)), fs, out_dir=np.tile(T[i] * sgn, (seg, 1)))


def lathe(acc, profile, origin, axis, seg=32, uv_v=None):
    """Revolve (r, h) profile round axis through origin. Normals by finite differences, outward-ish."""
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    a = np.cross(axis, [0, 0, 1.0]) if abs(axis[2]) < 0.9 else np.cross(axis, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(axis, a)
    prof = np.asarray(profile, float)
    n = len(prof)
    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    V, NN = [], []
    for j, (r, h) in enumerate(prof):
        jp, jn = prof[max(j - 1, 0)], prof[min(j + 1, n - 1)]
        dr, dh = jn[0] - jp[0], jn[1] - jp[1]
        nr, nh = dh, -dr                       # profile normal (right of the direction of travel)
        ln = math.hypot(nr, nh) or 1.0
        nr, nh = nr / ln, nh / ln
        for t in ang:
            d = math.cos(t) * a + math.sin(t) * b
            V.append(origin + axis * h + d * r)
            NN.append(axis * nh + d * nr)
    V, NN = np.array(V), np.array(NN)
    faces, dirs = [], []
    for j in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((j * seg + k, j * seg + k2, (j + 1) * seg + k2, (j + 1) * seg + k))
            dirs.append(NN[j * seg + k] + NN[(j + 1) * seg + k])
    UV = np.stack([np.tile(ang / (2 * math.pi), n), np.repeat(np.arange(n) / max(1, n - 1), seg)], 1)
    acc.add(V, NN, UV, faces, out_dir=np.array(dirs))


def grid_shell(acc, P, t, out_hint, uv=None, rim_k=4, back=True):
    """Shell from a structured grid P[i, j] (rows i, cols j): outer skin, inner skin, rolled rim round
    the grid border. out_hint(points, normals) -> bool array: True where the normal already points out."""
    nI, nJ = P.shape[:2]
    Pi = np.gradient(P, axis=0)
    Pj = np.gradient(P, axis=1)
    N = np.cross(Pj, Pi)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    flip = ~out_hint(P, N)
    if flip.mean() > 0.5:
        N = -N
    if uv is None:
        uv = np.stack(np.meshgrid(np.linspace(0, 1, nJ), np.linspace(0, 1, nI)), -1)
    idx = np.arange(nI * nJ).reshape(nI, nJ)
    faces = [(idx[i, j], idx[i, j + 1], idx[i + 1, j + 1], idx[i + 1, j]) for i in range(nI - 1) for j in range(nJ - 1)]
    fN = np.array([N[i, j] + N[i + 1, j + 1] for i in range(nI - 1) for j in range(nJ - 1)])
    V, NV, UV = P.reshape(-1, 3), N.reshape(-1, 3), uv.reshape(-1, 2)
    acc.add(V, NV, UV, faces, out_dir=fN)
    if back:
        acc.add(V - t * NV, -NV, UV, faces, out_dir=-fN)
    # border loop (i=0 row, j=last col, i=last row reversed, j=0 col reversed)
    ring = [(0, j) for j in range(nJ)] + [(i, nJ - 1) for i in range(1, nI)] + \
           [(nI - 1, j) for j in range(nJ - 2, -1, -1)] + [(i, 0) for i in range(nI - 2, 0, -1)]
    BP = np.array([P[i, j] for i, j in ring])
    BN = np.array([N[i, j] for i, j in ring])
    BU = np.array([uv[i, j] for i, j in ring])
    T = np.roll(BP, -1, 0) - np.roll(BP, 1, 0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    E = np.cross(T, BN)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    cen = P.reshape(-1, 3).mean(0)
    # E must point away from the panel: compare with a step toward the grid's middle
    inward = np.array([P[min(max(i, 1), nI - 2), min(max(j, 1), nJ - 2)] for i, j in ring]) - BP
    if np.mean(np.sum(E * inward, 1)) > 0:
        E = -E
    n = len(ring)
    K = rim_k if back else max(2, rim_k // 2)
    a_end = math.pi if back else math.pi / 2
    RV, RN = [], []
    for k in range(K + 1):
        a = a_end * k / K
        d = math.cos(a) * BN + math.sin(a) * E
        RV.append(BP - (t / 2) * BN + (t / 2) * d)
        RN.append(d)
    RV, RN = np.vstack(RV), np.vstack(RN)
    faces, dirs = [], []
    for k in range(K):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
            dirs.append(RN[k * n + i] + RN[(k + 1) * n + i])
    acc.add(RV, RN, np.tile(BU, (K + 1, 1)), faces, out_dir=np.array(dirs))
    return N


def dome(acc, c, n, r, h, seg=12, rings=3):
    """Low dome head (fastener) sitting on a surface at c with normal n."""
    prof = [(r * math.cos(0.5 * math.pi * k / rings), h * math.sin(0.5 * math.pi * k / rings)) for k in range(rings + 1)]
    prof = [(r * 1.0, -0.0015)] + prof
    lathe(acc, prof, np.asarray(c, float), n, seg=seg)
    # hex socket: a small dark-ish dimple is too small to matter at game scale; the dome reads as a screw head


# ------------------------------------------------------------------ the parts
T_PANEL = 0.003


def build_cowl(surf):
    ol, holes = cowl_loops()
    acc, info = panel(surf, ol, holes, spacing=0.011, t=T_PANEL)
    return acc, info


def side_uv_box(surf):
    L = side_loop(1)
    s = surf.to_flat(L[:, 0], L[:, 1])
    return (s.min() - 0.01, L[:, 1].min() - 0.01, s.max() + 0.01, L[:, 1].max() + 0.01)


def build_sides(surf):
    """Left and right share one texture: the right side's UVs are mirrored (s -> -s)."""
    out = {}
    box = side_uv_box(surf)
    for sign, nm in ((1, "L"), (-1, "R")):
        ol, holes = side_loops(sign)
        acc, info = panel(surf, ol, holes, spacing=0.012, t=T_PANEL, uv_box=box, uv_sign=sign)
        out["SidePanel" + nm] = (acc, info)
    return out


def build_gill_ducts(surf):
    acc = MeshAcc()
    for sign in (1, -1):
        for c, hl, hw in GILLS:
            P, N, F = loop3d(surf, gill_loop(c, hl, hw, sign), 0.003, offset=-T_PANEL)
            D = -N.mean(0) + np.array([0, 0.35, 0])
            sleeve(acc, P, D, 0.022, rings=2, taper=0.1)
    return acc


def build_inner(surf):
    out = {}
    for sign, nm in ((1, "L"), (-1, "R")):
        L = cr_curve(INNER, closed=True, n=10)
        L[:, 0] *= sign
        acc, info = panel(surf, L, [], spacing=0.016, t=0.0025, offset=-INNER_DEPTH)
        out["InnerPanel" + nm] = (acc, info)
    return out


def headlight_parts(surf):
    housing, lens, drl, proj, plens = MeshAcc(), MeshAcc(), MeshAcc(), MeshAcc(), MeshAcc()
    for sign in (1, -1):
        H = cr_curve(HEADLIGHT, closed=True, n=10)
        H[:, 0] *= sign
        P, N, F = loop3d(surf, H, 0.004, offset=-T_PANEL)
        Navg = N.mean(0)
        Navg /= np.linalg.norm(Navg)
        D = -Navg + np.array([0, 0.45, 0.05])
        D /= np.linalg.norm(D)
        sleeve(housing, P, D, 0.050, rings=3, taper=0.18)
        # clear lens a little below the outer skin
        acc, _ = panel(surf, H, [], spacing=0.010, t=0.002, offset=-0.0045, back=False)
        lens.merge(acc)
        # LED daytime-running strip along the upper edge of the eye
        up = [(0.455, 0.778), (0.43, 0.7855), (0.39, 0.7875), (0.33, 0.7875), (0.26, 0.7835), (0.20, 0.7755), (0.155, 0.763), (0.125, 0.749)]
        C = cr_curve(up, closed=False, n=8)
        C[:, 0] *= sign
        u = C[:, 0]
        zz = C[:, 1]
        pts = surf.point(u, zz) - 0.012 * surf.normal(u, zz) + D * 0.0
        tube(drl, pts, 0.0032, seg=10)
        # two projector modules
        for (cu, cz, r) in ((0.255, 0.752, 0.0205), (0.365, 0.762, 0.0155)):
            c = surf.point(sign * cu, cz) - 0.020 * surf.normal(sign * cu, cz)
            ax = -D
            lathe(proj, [(r * 0.62, -0.012), (r * 0.95, -0.010), (r * 1.08, -0.002), (r * 1.10, 0.0015), (r * 0.98, 0.003), (r * 0.80, 0.0005)], c, ax, seg=28)
            lathe(plens, [(r * 0.80, 0.0), (r * 0.72, 0.0035), (r * 0.5, 0.0058), (r * 0.25, 0.0068), (0.0, 0.0071)], c, ax, seg=28)
    return {"HeadlightHousing": housing, "HeadlightLens": lens, "HeadlightDRL": drl, "Projector": proj, "ProjectorLens": plens}


def build_intake(surf):
    duct = MeshAcc()
    L = np.asarray(mirror_loop(INTAKE_HALF[:-1]), float)
    L = np.vstack([L, [(0.0, INTAKE_HALF[-1][1])]])
    L = cr_curve(L, closed=True, n=8)
    P, N, F = loop3d(surf, L, 0.004, offset=-T_PANEL)
    D = np.array([0.0, 1.0, -0.12])
    last = sleeve(duct, P, D, 0.12, rings=4, taper=0.30, close=False)
    grille = MeshAcc()
    c = last.mean(0)
    cap(grille, last, -D / np.linalg.norm(D))
    return duct, grille


def screen_grid(surf, rows=30, cols=34):
    e = cr_curve(SCREEN_EDGE, closed=False, n=12)
    EL = surf.point(e[:, 0], e[:, 1]) + SCREEN_LIFT * surf.normal(e[:, 0], e[:, 1])
    tE = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(EL, axis=0), axis=1))])
    tE /= tE[-1]
    c0 = surf.point(0.0, SCREEN_BOTTOM_Z) + SCREEN_LIFT * surf.normal(0.0, SCREEN_BOTTOM_Z)
    Su, Sz = surf.derivs(0.0, SCREEN_BOTTOM_Z)
    T0 = Sz / np.linalg.norm(Sz)
    c3 = np.array(SCREEN_TOP)
    T1 = np.array([0.0, 0.80, 0.60])
    T1 /= np.linalg.norm(T1)
    c1, c2 = c0 + 0.12 * T0, c3 - 0.10 * T1
    tt = np.linspace(0, 1, 400)
    B = ((1 - tt) ** 3)[:, None] * c0 + (3 * (1 - tt) ** 2 * tt)[:, None] * c1 + (3 * (1 - tt) * tt ** 2)[:, None] * c2 + (tt ** 3)[:, None] * c3
    tC = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(B, axis=0), axis=1))])
    tC /= tC[-1]
    ts = np.linspace(0, 1, rows)
    Lp = np.stack([np.interp(ts, tE, EL[:, k]) for k in range(3)], 1)
    Cp = np.stack([np.interp(ts, tC, B[:, k]) for k in range(3)], 1)
    ss = np.linspace(-1, 1, cols)
    G = np.zeros((rows, cols, 3))
    for i in range(rows):
        Lx = Lp[i]
        for j, s in enumerate(ss):
            f = abs(s) ** 2.1
            G[i, j, 0] = s * Lx[0]
            G[i, j, 1] = Cp[i, 1] + (Lx[1] - Cp[i, 1]) * f
            G[i, j, 2] = Cp[i, 2] + (Lx[2] - Cp[i, 2]) * f
    return G


def build_screen(surf):
    G = screen_grid(surf)
    acc = MeshAcc()
    grid_shell(acc, G, 0.0035, lambda P, N: (N[..., 1] * -0.6 + N[..., 2] * 0.8) > 0)
    return acc, G


# ------------------------------------------------------------------ belly pan (its own parametric hull)
BELLY = {   # y: (half width at the top edge a, top edge z, bottom z, superellipse n)
    -0.505: (0.166, 0.425, 0.190, 3.2), -0.46: (0.176, 0.392, 0.150, 4.0), -0.40: (0.182, 0.352, 0.124, 4.6),
    -0.32: (0.182, 0.318, 0.114, 5.0), -0.22: (0.178, 0.304, 0.112, 5.0), -0.13: (0.170, 0.300, 0.114, 4.8),
    -0.06: (0.160, 0.300, 0.118, 4.6),
}


def belly_section(y, th):
    ys = sorted(BELLY)
    vals = np.array([BELLY[k] for k in ys])
    from_ys = np.array(ys)
    y = np.asarray(y, float)
    a, zt, zb, n = (np.interp(y, from_ys, vals[:, k]) for k in range(4))
    ph = np.asarray(th, float) * math.pi / 2
    x = a * np.sign(ph) * np.abs(np.sin(ph)) ** (2 / n)
    z = zt - (zt - zb) * np.abs(np.cos(ph)) ** (2 / n)
    return x, z


def belly_grid(rows=46, cols=60):
    th = np.linspace(-1, 1, cols)
    b = np.linspace(0, 1, rows)
    TH, Bb = np.meshgrid(th, b)
    # front edge: scooped back at the middle (clears the front tyre), cheeks reach forward at the sides
    w = np.clip((np.abs(TH) - 0.42) / 0.45, 0, 1)
    w = w * w * (3 - 2 * w)
    y_front = -0.392 - 0.113 * w
    y_back = -0.068 - 0.030 * np.abs(TH) ** 3
    Y = y_front + (y_back - y_front) * Bb
    X, Z = belly_section(Y, TH)
    G = np.stack([X, Y, Z], -1)
    return G, TH, Bb


def build_belly():
    G, TH, Bb, S, Smax = belly_uv()
    acc = MeshAcc()
    uv = np.stack([0.5 + S / (2 * Smax), Bb], -1)
    grid_shell(acc, G, T_PANEL, lambda P, N: (N[..., 2] * -1 + np.sign(P[..., 0]) * N[..., 0]) > 0, uv=uv)
    return acc, G


def fasteners(surf):
    acc = MeshAcc()
    for sign in (1, -1):
        for (u, z) in FASTENERS_COWL + FASTENERS_SIDE:
            c = surf.point(sign * u, z)
            dome(acc, c, surf.normal(sign * u, z), 0.0042, 0.0018)
    G = screen_grid(surf)
    rows, cols = G.shape[:2]
    for (u, z) in FASTENERS_SCREEN:
        for sign in (1, -1):
            c = surf.point(sign * u, z) + (SCREEN_LIFT + 0.0035) * surf.normal(sign * u, z)
            dome(acc, c, surf.normal(sign * u, z), 0.0040, 0.0016)
    # belly pan: two on each side near the top edge
    for (y, th) in ((-0.43, 0.97), (-0.12, 0.97)):
        for sign in (1, -1):
            x, z = belly_section(y, sign * th)
            x2, z2 = belly_section(y, sign * (th - 0.02))
            n = np.array([x - x2, 0, z - z2])
            n = np.array([n[2], 0, -n[0]]) * sign
            n /= np.linalg.norm(n)
            dome(acc, np.array([x, y, z]) + n * 0.0002, n, 0.0042, 0.0018)
    return acc


def mirror_blanks(surf):
    acc = MeshAcc()
    for sign in (1, -1):
        u0, z0 = MIRROR_BLANK
        k = np.linspace(0, 2 * math.pi, 28, endpoint=False)
        L = np.stack([sign * (u0 + 0.026 * np.cos(k)), z0 + 0.0085 * np.sin(k)], 1)
        a, _ = panel(surf, L, [], spacing=0.006, t=0.0022, offset=0.0022, back=True, rim_k=4)
        acc.merge(a)
    return acc


# ------------------------------------------------------------------ paint (our own scheme, no text or logos)
WHITE = (238, 239, 242)
CHAR = (36, 38, 42)
ACCENT = (226, 64, 30)
GREY = (120, 123, 130)


def _dist_poly(P, X, Y):
    """Distance from points to a polyline P (open)."""
    d = np.full(np.shape(X), np.inf)
    for (ax, ay), (bx, by) in zip(P[:-1], P[1:]):
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy or 1e-12
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
        d = np.minimum(d, np.hypot(X - ax - t * vx, Y - ay - t * vy))
    return d


def _below(P, X, Y):
    """True where (X, Y) is below the polyline P (P sorted by x, extended flat past its ends)."""
    return Y < np.interp(X, P[:, 0], P[:, 1])


COWL_MASK = np.array([(0.0, 0.0), (0.055, 0.66), (0.072, 0.700), (0.084, 0.735), (0.104, 0.790), (0.14, 0.842), (0.196, 0.889),
                      (0.258, 0.935), (0.320, 0.970), (0.388, 0.997), (0.455, 1.016), (0.52, 1.035), (0.60, 1.2)])
BROW_LOW = cr_curve([(0.07, 0.775), (0.14, 0.790), (0.24, 0.806), (0.34, 0.815), (0.44, 0.822), (0.52, 0.830), (0.60, 0.842)], closed=False, n=8)
BROW_HIGH = cr_curve([(0.07, 0.792), (0.14, 0.812), (0.24, 0.830), (0.34, 0.840), (0.44, 0.848), (0.52, 0.857), (0.60, 0.870)], closed=False, n=8)
SIDE_SPLIT = cr_curve([(0.08, 0.706), (0.22, 0.681), (0.40, 0.656), (0.56, 0.638), (0.68, 0.630), (0.80, 0.637), (0.95, 0.655),
                       (1.10, 0.672), (1.30, 0.690)], closed=False, n=8)


def cowl_paint(u, z):
    a = np.abs(u)
    col = np.empty(u.shape + (3,))
    col[:] = WHITE
    # charcoal frame round the intake and the screen base, carried down over the chin
    mask_u = np.interp(z, COWL_MASK[:, 1], COWL_MASK[:, 0])
    col[a < mask_u] = CHAR
    # charcoal brow over each headlight, with an accent pinstripe above it
    lo = np.interp(a, BROW_LOW[:, 0], BROW_LOW[:, 1])
    hi = np.interp(a, BROW_HIGH[:, 0], BROW_HIGH[:, 1])
    brow = (z < hi) & (a > 0.06)
    col[brow] = CHAR
    stripe = (z >= hi + 0.004) & (z < hi + 0.0125) & (a > mask_u + 0.006)
    col[stripe] = ACCENT
    return col


def side_paint(u, z):
    a = np.abs(u)
    col = np.empty(u.shape + (3,))
    col[:] = WHITE
    sz = np.interp(a, SIDE_SPLIT[:, 0], SIDE_SPLIT[:, 1])
    col[z < sz] = CHAR
    col[(z >= sz + 0.005) & (z < sz + 0.015)] = ACCENT
    col[(z >= sz + 0.019) & (z < sz + 0.022)] = GREY
    return col


def inner_paint(u, z):
    col = np.empty(u.shape + (3,))
    col[:] = CHAR
    return col


def paint_panel(path, surf, uv_box, painter, size=(1024, 512), uv_sign=1.0, ss=2):
    W, H = size[0] * ss, size[1] * ss
    U, V = np.meshgrid((np.arange(W) + 0.5) / W, 1 - (np.arange(H) + 0.5) / H)
    s = uv_box[0] + U * (uv_box[2] - uv_box[0])
    z = uv_box[1] + V * (uv_box[3] - uv_box[1])
    u = surf.from_flat(s * uv_sign, z)
    col = painter(u, z)
    col = col.reshape(size[1], ss, size[0], ss, 3).mean((1, 3))
    save_png(path, col / 255.0)


def belly_paint_tex(path, size=(1024, 512), ss=2):
    """Belly pan: charcoal, with a white band and accent pinstripe along its top edge.
    UV u = arc length round the section from the bottom centre (normalised), v = front -> rear."""
    G, TH, Bb, S, Smax = belly_uv()
    W, H = size[0] * ss, size[1] * ss
    U, V = np.meshgrid((np.arange(W) + 0.5) / W, 1 - (np.arange(H) + 0.5) / H)
    s = np.abs((U - 0.5) * 2 * Smax)
    edge = np.interp(V, Bb[:, 0], S[:, -1])          # arc length to the top edge for this row
    d = edge - s                                     # distance below the top edge along the skin
    col = np.empty(U.shape + (3,))
    col[:] = CHAR
    col[d < 0.050] = WHITE
    col[(d >= 0.050) & (d < 0.058)] = ACCENT
    col = col.reshape(size[1], ss, size[0], ss, 3).mean((1, 3))
    save_png(path, col / 255.0)


def belly_uv():
    G, TH, Bb = belly_grid()
    seg = np.linalg.norm(np.diff(G, axis=1), axis=-1)
    S = np.concatenate([np.zeros((G.shape[0], 1)), np.cumsum(seg, axis=1)], 1)
    S -= S[:, [G.shape[1] // 2]] if G.shape[1] % 2 else (S[:, [G.shape[1] // 2 - 1]] + S[:, [G.shape[1] // 2]]) / 2
    Smax = np.abs(S).max()
    return G, TH, Bb, S, Smax


def grille_tex(path, N=256):
    """Honeycomb intake mesh: dark cells, slightly lighter walls."""
    y, x = np.mgrid[0:N, 0:N] / N * 8.0
    # hex grid distance (axial)
    qx = x / math.sqrt(3)
    col = np.empty((N, N, 3))
    best = np.full((N, N), 9.0)
    for cy in np.arange(-1, 10):
        for cx in np.arange(-1, 6):
            px = cx * math.sqrt(3) + (math.sqrt(3) / 2 if cy % 2 else 0)
            py = cy * 1.5
            dx, dy = np.abs(x - px), np.abs(y - py)
            d = np.maximum(dx, 0.5 * dx + 0.866 * dy)
            best = np.minimum(best, d)
    wall = np.clip((best - 0.76) / 0.05, 0, 1)
    col[:] = np.array([12, 12, 13]) * (1 - wall)[..., None] + np.array([58, 59, 62]) * wall[..., None]
    save_png(path, col / 255.0)


def save_png(path, rgb):
    a = np.clip(rgb, 0, 1)
    h, w = a.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = a[::-1]
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


# ------------------------------------------------------------------ looks
def L_tex(tex, rough, refl=0.04):
    return {"tex": tex, "rough": rough, "metal": 0.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": refl}}


def L_col(rgb, rough, metal=0.0, mat="SmoothPlastic", refl=0.0, transp=0.0, emit=0.0, transmit=0.0):
    r = {"Color": [int(c) for c in rgb], "Material": mat}
    if refl:
        r["Reflectance"] = refl
    if transp:
        r["Transparency"] = transp
    return {"color": tuple((c / 255.0) ** 2.2 for c in rgb), "rough": rough, "metal": metal, "emit": emit, "transmit": transmit, "roblox": r}


LOOKS = {
    "FairingNose": L_tex("FairingNose", 0.22), "SidePanelL": L_tex("SidePanel", 0.22), "SidePanelR": L_tex("SidePanel", 0.22),
    "BellyPan": L_tex("BellyPan", 0.25),
    "InnerPanelL": L_col((26, 27, 30), 0.55), "InnerPanelR": L_col((26, 27, 30), 0.55),
    "Screen": L_col((70, 74, 84), 0.04, mat="Glass", transp=0.45, transmit=1.0),
    "HeadlightLens": L_col((225, 230, 238), 0.03, mat="Glass", transp=0.7, transmit=1.0),
    "HeadlightHousing": L_col((34, 35, 39), 0.35, refl=0.2),
    "HeadlightDRL": L_col((235, 242, 255), 0.3, mat="Neon", emit=6.0),
    "Projector": L_col((176, 179, 186), 0.15, metal=1.0, refl=0.35),
    "ProjectorLens": L_col((20, 24, 34), 0.05, mat="Glass", refl=0.2),
    "IntakeDuct": L_col((14, 14, 15), 0.6), "IntakeGrille": L_tex("IntakeGrille", 0.5, 0.0),
    "GillDucts": L_col((14, 14, 15), 0.6),
    "Fasteners": L_col((44, 45, 48), 0.3, metal=1.0, refl=0.1),
    "MirrorBlanks": L_col((22, 22, 24), 0.7),
}
TEXFILES = {"FairingNose": "FairingNose_Color.png", "SidePanel": "SidePanel_Color.png", "BellyPan": "BellyPan_Color.png",
            "IntakeGrille": "IntakeGrille_Color.png"}


def material(key):
    L = LOOKS[key]
    m = bpy.data.materials.new("M_" + key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = L["rough"]
    b.inputs["Metallic"].default_value = L["metal"]
    if not L["metal"]:
        b.inputs["Specular IOR Level"].default_value = 0.4
    if L.get("tex"):
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, TEXFILES[L["tex"]]), check_existing=True)
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
        b.inputs["Coat Weight"].default_value = 0.5
        b.inputs["Coat Roughness"].default_value = 0.05
    else:
        b.inputs["Base Color"].default_value = (*L["color"], 1)
    if L.get("emit"):
        b.inputs["Emission Color"].default_value = (*L["color"], 1)
        b.inputs["Emission Strength"].default_value = L["emit"]
    if L.get("transmit"):
        b.inputs["Transmission Weight"].default_value = L["transmit"]
    return m


# ------------------------------------------------------------------ shape fit from the scan (run with --scan)
def sample_chart(scan_path, step=0.004, xshift=0.026):
    """Depth of the aligned scan along the stadium rays on a (z, u) grid. xshift centres the scan:
    its body sits ~26 mm to the right of the rear tyre's plane after refscan's alignment."""
    from mathutils.bvhtree import BVHTree
    import refscan
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob, info = refscan.load_aligned(scan_path)
    ob.data.transform(Matrix.Translation((xshift, 0, 0)))
    me = ob.data
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    us = np.arange(-CH_U, CH_U + 1e-9, step)
    zs = np.arange(CH_Z[0], CH_Z[1] + 1e-9, step)
    H = np.full((len(zs), len(us)), np.nan)
    px, py, nx, ny = stadium(us)[:4]
    for j in range(len(us)):
        d = Vector((-nx[j], -ny[j], 0.0))
        for i, z in enumerate(zs):
            hit = bvh.ray_cast(Vector((px[j], py[j], z)), d, R)
            if hit[0] is not None:
                H[i, j] = hit[3]
    return H, us, zs


def pspline_fit(H, us, zs, mask, ku=0.04, kz=0.04, lam=1.0, zr=(0.30, 1.20), iters=4, sub=2):
    """Penalised tensor B-spline fit of the symmetrised depth inside mask (robust: drops outliers)."""
    from scipy.interpolate import BSpline
    import scipy.sparse as sps
    import scipy.sparse.linalg as spl

    def basis(x, lo, hi, step):
        n_in = int(np.ceil((hi - lo) / step))
        t = lo + np.arange(-3, n_in + 4) * (hi - lo) / n_in
        return BSpline.design_matrix(np.clip(x, lo, hi - 1e-9), t, 3)

    Hm = H[:, ::-1]
    both = np.isfinite(H) & np.isfinite(Hm)
    H = np.where(both, np.where(np.abs(H - Hm) < 0.015, (H + Hm) / 2, np.maximum(H, Hm)), np.where(np.isfinite(H), H, Hm))
    m = mask & np.isfinite(H)
    m &= m[:, ::-1]
    U, Z = np.meshgrid(us, zs)
    sel = (slice(None, None, sub), slice(None, None, sub))
    Us, Zs, Hs, Ms = U[sel].ravel(), Z[sel].ravel(), H[sel].ravel(), m[sel].ravel()
    idx = np.where(Ms)[0]
    Bu = basis(Us[idx], -CH_U, CH_U, ku).toarray()
    Bz = basis(Zs[idx], zr[0], zr[1], kz).toarray()
    nu, nz = Bu.shape[1], Bz.shape[1]
    B = sps.csr_matrix(np.einsum('ij,ik->ijk', Bz, Bu).reshape(len(idx), -1))

    def D2(n):
        return sps.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    Pu, Pz = sps.kron(sps.eye(nz), D2(nu)), sps.kron(D2(nz), sps.eye(nu))
    Pen = lam * (Pu.T @ Pu + Pz.T @ Pz) + 1e-6 * sps.eye(nu * nz)
    y = Hs[idx]
    wk = np.ones(len(idx))
    for it in range(iters):
        c = spl.spsolve((B.T @ sps.diags(wk) @ B + Pen).tocsc(), B.T @ (wk * y))
        r = y - B @ c
        sd = np.sqrt(np.average(r ** 2, weights=wk))
        wk = np.where(np.abs(r) > max(2.5 * sd, 0.003), 0.0, 1.0)
        print(f"fit pass {it}: rms {sd * 1000:.2f} mm, {np.sum(wk == 0)} of {len(wk)} samples dropped")
    uo = np.round(np.arange(-CH_U, CH_U + 1e-9, 0.01), 4)
    zo = np.round(np.arange(CH_Z[0], CH_Z[1] + 1e-9, 0.01), 4)
    F = basis(zo, zr[0], zr[1], kz).toarray() @ c.reshape(nz, nu) @ basis(uo, -CH_U, CH_U, ku).toarray().T
    return F, uo, zo


def fit_shape(scan_path):
    from scipy import ndimage
    H, us, zs = sample_chart(scan_path)
    U, Z = np.meshgrid(us, zs)
    ol, _ = cowl_loops()
    mask = pip(ol, U, Z) | pip(side_loop(1), U, Z) | pip(side_loop(-1), U, Z)
    mask = ndimage.binary_erosion(mask, iterations=2)
    F, uo, zo = pspline_fit(H, us, zs, mask)
    np.savez_compressed(SHAPE, H=F.astype(np.float32), us=uo, zs=zo)
    print("wrote", SHAPE)


# ------------------------------------------------------------------ build + export
def build():
    surf = load_surface()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    accs, boxes = {}, {}
    accs["FairingNose"], info = build_cowl(surf)
    boxes["FairingNose"] = info["uv_box"]
    for k, (a, i) in build_sides(surf).items():
        accs[k] = a
        boxes[k] = i["uv_box"]
    for k, (a, i) in build_inner(surf).items():
        accs[k] = a
    accs.update(headlight_parts(surf))
    accs["IntakeDuct"], accs["IntakeGrille"] = build_intake(surf)
    accs["Screen"] = build_screen(surf)[0]
    accs["BellyPan"] = build_belly()[0]
    accs["GillDucts"] = build_gill_ducts(surf)
    accs["Fasteners"] = fasteners(surf)
    accs["MirrorBlanks"] = mirror_blanks(surf)
    # paint
    paint_panel(os.path.join(TEX, TEXFILES["FairingNose"]), surf, boxes["FairingNose"], cowl_paint, (1024, 512))
    paint_panel(os.path.join(TEX, TEXFILES["SidePanel"]), surf, boxes["SidePanelL"], side_paint, (1024, 384))
    belly_paint_tex(os.path.join(TEX, TEXFILES["BellyPan"]))
    grille_tex(os.path.join(TEX, TEXFILES["IntakeGrille"]))
    parts = {}
    for name, acc in accs.items():
        ob = acc.obj(name)
        ob.data.materials.append(material(name))
        parts[name] = ob
    return parts


def export(parts):
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: +X = bike's LEFT, -Y = front, +Z = up; origin = ground between the axles (bike layout).",
            "credit": "Shapes fitted to 'BMW S 1000 RR - HSLU Midterm 3DMOD4RT' by noe_auf (Sketchfab, CC-BY-4.0). Graphics are our own.",
            "parts": {}, "looks": {}}
    texmap = {}
    for name, ob in parts.items():
        meta["parts"][name] = {"tris": G.tris(ob)}
        meta["looks"][name] = LOOKS[name]["roblox"]
        if LOOKS[name].get("tex"):
            texmap[name] = f"art/models/BikeFairings/tex/{TEXFILES[LOOKS[name]['tex']]}"
    meta["total_tris"] = sum(p["tris"] for p in meta["parts"].values())
    for o in bpy.context.selected_objects:
        o.select_set(False)
    copies = []
    for ob in parts.values():
        c = ob.copy()
        c.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.data.transform(Matrix.Scale(STUDS, 4))
        c.name = ob.name + "_x"
        c.select_set(True)
        copies.append(c)
    path = os.path.join(OUT, "BikeFairings.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_materials='PLACEHOLDER',
                              export_apply=True, export_yup=True, export_texcoords=True, export_normals=True)
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)
    data = open(path, "rb").read()
    ln = struct.unpack_from("<I", data, 12)[0]
    gl = json.loads(data[20:20 + ln])
    assert not gl.get("images"), "GLB must not embed images"
    for nd in gl["nodes"]:
        nd["name"] = nd["name"].removesuffix("_x")
    for m in gl.get("meshes", []):
        m["name"] = m["name"].removesuffix("_x")
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + data[20 + ln:]
    open(path, "wb").write(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    json.dump(texmap, open(os.path.join(OUT, "textures.json"), "w"), indent=1)
    print("BikeFairings tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})
    for k, v in meta["parts"].items():
        assert v["tris"] < 20000, (k, v)


if __name__ == "__main__":
    if "--scan" in sys.argv:
        fit_shape(sys.argv[sys.argv.index("--scan") + 1])
    else:
        os.makedirs(OUT, exist_ok=True)
        parts = build()
        export(parts)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
