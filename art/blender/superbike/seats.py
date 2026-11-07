"""Superbike rider seat and passenger (pillion) seat in black leather, as their own part.

  /home/user/bvenv/bin/python art/blender/superbike/seats.py

Bike coordinates as in wheels.py / exhaust.py / chain.py: +X = bike's LEFT, -Y = front, +Z = up,
origin = ground between the axles.

Each seat is a real upholstered pad:
  Top    - domed top panel; a pleated, perforated centre zone inside a smooth leather border,
           grooves at every pleat and round the zone, double topstitching (colour map)
  Sides  - side panel from the piping seam down, round the shoulder, wrapped under the pan
  Piping - welt cord along the top seam
  Base   - black plastic seat pan under the cover, rubber bumpers, front hook tongue
and both seats share SeatLatch (the steel striker loops the seat lock catches).
The top panel is a Coons patch over the plan outline, so the pleats, borders and stitches are
drawn in the same (a, b) patch space in the texture as in the mesh and always line up.
Outputs art/models/BikeSeats/{BikeSeats.glb, meta.json, textures.json, tex/, work.blend}.
"""
import json
import math
import os
import struct
import sys

import bpy
import bmesh  # noqa: E402,F401  (after bpy)
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo as G  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "art", "models", "BikeSeats")
TEX = os.path.join(OUT, "tex")
STUDS = 3.6
MM = 0.001

Q = 1.0   # mesh detail


def q(n, lo=4):
    return max(lo, int(round(n * Q)))


# ------------------------------------------------------------------ seat specs (meters)
SEATS = {
    "Rider": {
        "y0": -0.070, "y1": 0.338,                       # nose tip .. rear end
        "w": lambda t: 0.040 + 0.100 * (1 - (1 - t) ** 2.2),   # half width of the top panel along the seat
        "n_front": 2.4, "n_rear": 5.0, "s_front": 0.80, "s_rear": 0.90,
        # seam (top panel edge) height along y: the pocket is lowest just behind the tank
        "seam": [(-0.070, 0.852), (-0.02, 0.840), (0.05, 0.828), (0.12, 0.824), (0.22, 0.830), (0.30, 0.848), (0.338, 0.856)],
        "zb": (0.772, 0.790),                            # bottom of the cover at y0 / y1
        "crown": 0.011, "crown2": 0.004,
        "border": 0.026, "zone_front": 0.110, "zone_rear": 0.034, "pleats": 7,
        "tongue": True, "bumpers": [(-0.05, 0.02), (0.05, 0.02), (-0.08, 0.26), (0.08, 0.26)], "latch_y": 0.30,
    },
    "Pillion": {
        "y0": 0.425, "y1": 0.655,
        "w": lambda t: 0.090 - 0.022 * t ** 1.6,
        "n_front": 4.0, "n_rear": 2.6, "s_front": 0.88, "s_rear": 0.80,
        "seam": [(0.425, 0.972), (0.50, 0.975), (0.58, 0.979), (0.655, 0.983)],
        "zb": (0.928, 0.936),
        "crown": 0.010, "crown2": 0.003,
        "border": 0.022, "zone_front": 0.030, "zone_rear": 0.042, "pleats": 4,
        "tongue": True, "bumpers": [(-0.045, 0.47), (0.045, 0.47), (-0.04, 0.60), (0.04, 0.60)], "latch_y": 0.615,
    },
}

GROOVE_BORDER = 0.0026     # depth of the groove round the pleated zone
GROOVE_PLEAT = 0.0030
RIB_PUFF = 0.0016
DOME_R = 0.034             # distance from the seam over which the top rolls up to full crown
VS = 0.10                  # side texture: meters covered by v = 0..1 down from the seam


def smooth_interp(xs, ys, x):
    """Catmull-Rom through (xs, ys), non-uniform spacing, clamped ends."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    x = np.clip(np.asarray(x, float), xs[0], xs[-1])
    m = np.gradient(ys, xs)
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    h = xs[i + 1] - xs[i]
    t = (x - xs[i]) / h
    h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
    h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    return h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1]


def arclen_param(P):
    d = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    return d / d[-1], d[-1]


# ------------------------------------------------------------------ the top panel patch
class Patch:
    """Plan outline of a seat top split into 4 edges (front, left, rear, right) and the Coons
    patch between them. a: 0 = right edge (-X) .. 1 = left edge (+X); b: 0 = front .. 1 = rear."""

    def __init__(self, S):
        self.S = S
        y0, y1 = S["y0"], S["y1"]
        L, ym = y1 - y0, (y0 + y1) / 2
        nf, nr = S["n_front"], S["n_rear"]

        def w(y):
            return S["w"](np.clip((y - y0) / L, 0, 1))

        def e(y):
            s = (y - ym) / (L / 2)
            n = np.where(s < 0, nf, nr)
            return (1 - np.abs(s) ** n) ** (1 / n)

        yA, yB = ym - S["s_front"] * L / 2, ym + S["s_rear"] * L / 2
        ys = np.linspace(yA, yB, 600)
        xs = w(ys) * e(ys)
        XA, XB, wA, wB = xs[0], xs[-1], w(yA), w(yB)
        ph = np.linspace(-1, 1, 600)
        cf = np.stack([XA * ph, ym - (L / 2) * (1 - (np.abs(XA * ph) / wA) ** nf) ** (1 / nf)], 1)
        cr = np.stack([XB * ph, ym + (L / 2) * (1 - (np.abs(XB * ph) / wB) ** nr) ** (1 / nr)], 1)
        self.curves = {"c0": cf, "c1": cr, "d0": np.stack([-xs, ys], 1), "d1": np.stack([xs, ys], 1)}
        self.t = {k: arclen_param(v)[0] for k, v in self.curves.items()}
        self.P00, self.P10 = cf[0], cf[-1]
        self.P01, self.P11 = cr[0], cr[-1]
        self.Lc = float(np.linalg.norm(self.curve("c1", 0.5) - self.curve("c0", 0.5)))
        self.zb = lambda y: S["zb"][0] + (S["zb"][1] - S["zb"][0]) * (y - y0) / L
        self.seam = lambda y: smooth_interp([p[0] for p in S["seam"]], [p[1] for p in S["seam"]], y)
        bz0, bz1 = S["zone_front"] / self.Lc, 1 - S["zone_rear"] / self.Lc
        K = S["pleats"]
        self.bz = (bz0, bz1)
        self.rib = (bz1 - bz0) / (K + 1)
        self.grooves = [bz0 + (k + 1) * self.rib for k in range(K)]

    def curve(self, k, s):
        s = np.asarray(s, float)
        C = self.curves[k]
        return np.stack([np.interp(s, self.t[k], C[:, 0]), np.interp(s, self.t[k], C[:, 1])], -1)

    def P(self, a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        A, B = a[..., None], b[..., None]
        return ((1 - B) * self.curve("c0", a) + B * self.curve("c1", a) + (1 - A) * self.curve("d0", b) + A * self.curve("d1", b)
                - ((1 - A) * (1 - B) * self.P00 + A * (1 - B) * self.P10 + (1 - A) * B * self.P01 + A * B * self.P11))

    def W(self, b):
        return np.linalg.norm(self.curve("d1", b) - self.curve("d0", b), axis=-1)

    # zone + groove fields, all in patch space with physical scale (shared by mesh and texture)
    def fields(self, a, b):
        S = self.S
        W = self.W(b)
        d_side = np.minimum(a, 1 - a) * W
        d_front, d_rear = b * self.Lc, (1 - b) * self.Lc
        B = np.minimum(S["border"], 0.36 * W)
        dx = S["border"] - d_side
        dy = np.maximum(S["zone_front"] - d_front, S["zone_rear"] - d_rear)
        sd = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0)   # <0 inside the zone
        inside = np.clip(-sd / 0.004, 0, 1)
        inside = inside * inside * (3 - 2 * inside)
        g_pleat = np.zeros_like(a)
        for bk in self.grooves:
            g_pleat = np.maximum(g_pleat, np.exp(-(((b - bk) * self.Lc) / 0.0018) ** 2))
        rib = np.sin(np.pi * np.clip((b - self.bz[0]) / self.rib, 0, None)) ** 2
        k = 0.006
        de = -k * np.log(np.exp(-d_side / k) + np.exp(-d_front / k) + np.exp(-d_rear / k))
        return {"W": W, "B": B, "d_side": d_side, "sd": sd, "inside": inside, "g_pleat": g_pleat, "rib": rib,
                "de": np.clip(de, 0, None), "d_edge": np.minimum(d_side, np.minimum(d_front, d_rear))}

    def top_z(self, a, b, y):
        S, f = self.S, self.fields(a, b)
        t = np.clip(f["de"] / DOME_R, 0, 1)
        dome = S["crown"] * (1 - (1 - t) ** 2.5) + S["crown2"] * (1 - (2 * a - 1) ** 2) * (1 - np.abs(2 * b - 1) ** 4)
        z = self.seam(y) + dome
        z -= GROOVE_BORDER * np.exp(-(f["sd"] / 0.0016) ** 2)
        z -= GROOVE_PLEAT * f["inside"] * f["g_pleat"]
        z += RIB_PUFF * f["inside"] * f["rib"]
        return z


# ------------------------------------------------------------------ mesh builder
class MB:
    """Faces turned to point away from an inside point given per add (normals right by construction)."""

    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add(self, verts, faces, uvs, inside):
        o = len(self.v)
        V = np.asarray(verts, float)
        ins = np.asarray(inside, float)
        per_face = ins.ndim == 2
        for fi, (f, fu) in enumerate(zip(faces, uvs)):
            Pp = V[list(f)]
            Q2 = np.roll(Pp, -1, 0)
            n = np.array([np.sum((Pp[:, 1] - Q2[:, 1]) * (Pp[:, 2] + Q2[:, 2])),
                          np.sum((Pp[:, 2] - Q2[:, 2]) * (Pp[:, 0] + Q2[:, 0])),
                          np.sum((Pp[:, 0] - Q2[:, 0]) * (Pp[:, 1] + Q2[:, 1]))])
            if n @ (Pp.mean(0) - (ins[fi] if per_face else ins)) < 0:
                f, fu = f[::-1], fu[::-1]
            self.f.append(tuple(i + o for i in f))
            self.uv.append(list(fu))
        self.v.extend(map(tuple, V))

    def obj(self, name, smooth=None):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        lay = me.uv_layers.new(name="UVMap")
        lay.data.foreach_set("uv", np.array([u for fu in self.uv for u in fu], np.float32).ravel())
        me.validate()
        me.update()
        ob = G.new_obj(name, me)
        if smooth:
            G.smooth(ob, smooth)
        return ob


def tube(mb, pts, r, seg, closed, up=None):
    """Round tube along a 3D polyline; frames by parallel transport."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    T = []
    for i in range(n):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        T.append(t.normalized())
    ref = Vector(up) if up else (Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0)))
    N = [(ref - T[0] * ref.dot(T[0])).normalized()]
    for i in range(1, n):
        v = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(v.normalized())
    rings = []
    for i in range(n):
        Bv = T[i].cross(N[i])
        rings.append([pts[i] + r * (math.cos(2 * math.pi * k / seg) * N[i] + math.sin(2 * math.pi * k / seg) * Bv) for k in range(seg)])
    m = n if closed else n - 1
    verts = [tuple(p) for ring in rings for p in ring]
    faces, ins = [], []
    for i in range(m):
        i2 = (i + 1) % n
        for k in range(seg):
            faces.append((i * seg + k, i * seg + (k + 1) % seg, i2 * seg + (k + 1) % seg, i2 * seg + k))
            ins.append(tuple((pts[i] + pts[i2]) / 2))
    mb.add(verts, faces, [[(0, 0)] * 4] * len(faces), ins)


# ------------------------------------------------------------------ one seat
def a_columns(W, S):
    """Columns across one row, as patch a values: fine near the seam and round the zone groove."""
    B = min(S["border"], 0.36 * W)
    k = B / S["border"]
    band = [f * B for f in (0, 0.10, 0.21, 0.35, 0.50, 0.65, 0.79, 0.885, 0.94)] + [B, B + 0.0012 * k, B + 0.0028 * k]
    mid0, mid1 = band[-1] + 0.0025 * k, W - band[-1] - 0.0025 * k
    m = q(18, 8)
    mid = [mid0 + (mid1 - mid0) * i / m for i in range(m + 1)]
    right = [d for d in band]
    left = [W - d for d in reversed(band)]
    a = np.array(right + mid + left) / W
    assert np.all(np.diff(a) > 0), "columns must increase"
    return a


def b_rows(patch):
    Lc = patch.Lc
    base = list(np.linspace(0, 1, q(int(Lc / 0.0050), 30) + 1))
    extra = []
    for bk in patch.grooves:
        extra += [bk + o * MM / Lc for o in (-4.5, -2.6, -1.3, 0, 1.3, 2.6, 4.5)]
    for bz in patch.bz:
        extra += [bz + o * MM / Lc for o in (-3.2, -1.6, 0, 1.6, 3.2)]
    for o in (1.2, 2.6, 4.5, 7):           # tighter rows near the front/rear seam roll
        extra += [o * MM / Lc, 1 - o * MM / Lc]
    rows = sorted(set(round(float(b), 6) for b in base + extra if 0 <= b <= 1))
    keep = [rows[0]]
    for b in rows[1:]:
        if (b - keep[-1]) * Lc > 0.0006:
            keep.append(b)
    if keep[-1] != 1.0:
        keep[-1] = 1.0
    return np.array(keep)


def build_seat(key):
    S = SEATS[key]
    patch = Patch(S)
    rows = b_rows(patch)
    W_rows = patch.W(rows)
    cols = [a_columns(float(W), S) for W in W_rows]
    J = len(cols[0]) - 1
    R = len(rows) - 1
    A = np.array(cols)                        # (R+1, J+1)
    Bm = np.repeat(rows[:, None], J + 1, 1)
    XY = patch.P(A, Bm)
    Z = patch.top_z(A, Bm, XY[..., 1])
    ym = (S["y0"] + S["y1"]) / 2
    zin = float(patch.zb(ym)) + 0.01
    # ---- top panel
    top = MB()
    idx = lambda i, j: i * (J + 1) + j  # noqa: E731
    verts = [(float(XY[i, j, 0]), float(XY[i, j, 1]), float(Z[i, j])) for i in range(R + 1) for j in range(J + 1)]
    uvv = [(float(A[i, j]), float(rows[i])) for i in range(R + 1) for j in range(J + 1)]
    faces = [(idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)) for i in range(R) for j in range(J)]
    # every top face points up: one inside point well below the panel works for the whole patch
    top.add(verts, faces, [[uvv[k] for k in f] for f in faces], (0.0, ym, zin - 0.3))
    # ---- seam loop (CCW seen from above): front a 0->1, left b 0->1, rear a 1->0, right b 1->0
    loop = [(0, j) for j in range(J + 1)] + [(i, J) for i in range(1, R + 1)] + [(R, j) for j in range(J - 1, -1, -1)] + [(i, 0) for i in range(R - 1, 0, -1)]
    Lp = np.array([[XY[i, j, 0], XY[i, j, 1], Z[i, j]] for i, j in loop])
    n = len(Lp)
    tang = np.roll(Lp[:, :2], -1, 0) - np.roll(Lp[:, :2], 1, 0)
    nout = np.stack([tang[:, 1], -tang[:, 0]], 1)
    nout /= np.linalg.norm(nout, axis=1)[:, None]
    # plan arc length (u) and a tile size that repeats a whole number of times round the seat
    seg_len = np.linalg.norm(np.roll(Lp[:, :2], -1, 0) - Lp[:, :2], axis=1)
    ucum = np.concatenate([[0.0], np.cumsum(seg_len)])
    perim = ucum[-1]
    tile = perim / max(1, round(perim / 0.10))
    # ---- side panel profile per seam point: shoulder, wall, roll under the pan
    sides = MB()
    prof_n = None
    rings = []
    for k in range(n):
        x, y, zs = Lp[k]
        H = zs - float(patch.zb(y))
        assert H > 0.03, (key, y, H)
        prof = [(0.0, 0.0), (0.0022, -0.0012), (0.0044, -0.0038), (0.0060, -0.0076), (0.0069, -0.0125)]
        wall0, wall1 = -0.0125, -(H - 0.0095)
        for t in (0.25, 0.5, 0.75):
            prof.append((0.0069 - 0.0008 * t + 0.0007 * math.sin(math.pi * t), wall0 + (wall1 - wall0) * t))
        prof += [(0.0060, wall1), (0.0042, -(H - 0.0042)), (0.0012, -(H - 0.0009)), (-0.0035, -H), (-0.0120, -H + 0.0002)]
        prof_n = len(prof)
        vlen = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff([p[0] for p in prof]), np.diff([p[1] for p in prof])))])
        ring = []
        for (o, dz), vl in zip(prof, vlen):
            ring.append(((x + o * nout[k, 0], y + o * nout[k, 1], zs + dz), vl / VS))
        rings.append(ring)
    sv, suv = [], []
    for k in range(n):
        for p, v in rings[k]:
            sv.append(p)
            suv.append(v)
    faces, uvs = [], []
    for k in range(n):
        k2 = (k + 1) % n
        u0, u1 = ucum[k] / tile, ucum[k + 1] / tile
        for j in range(prof_n - 1):
            f = (k * prof_n + j, k2 * prof_n + j, k2 * prof_n + j + 1, k * prof_n + j + 1)
            faces.append(f)
            # v = 0 at the seam: image row 0 is the bottom, so flip to put the seam at the top of the tile
            uvs.append([(u0, 1 - suv[f[0]]), (u1, 1 - suv[f[1]]), (u1, 1 - suv[f[2]]), (u0, 1 - suv[f[3]])])
    # orient: away from the seat's centre line at the same height band (vertices shared -> smooth)
    ins = []
    for f in faces:
        c = np.mean([sv[i] for i in f], 0)
        ins.append((0.0, float(np.clip(c[1], S["y0"] + 0.06, S["y1"] - 0.06)), float(c[2]) + 0.012))
    sides.add(sv, faces, uvs, ins)
    # ---- piping along the seam, sitting in the crease
    pp = [(Lp[k, 0] + 0.0011 * nout[k, 0], Lp[k, 1] + 0.0011 * nout[k, 1], Lp[k, 2] + 0.0004) for k in range(n)]
    piping = MB()
    tube(piping, pp, 0.0023, q(8, 6), True)
    # ---- seat pan (inset under the tucked cover), hook tongue, bumpers
    base = MB()
    inset = Lp[:, :2] - 0.004 * nout
    zt = np.array([float(patch.zb(y)) - 0.0006 for y in inset[:, 1]])
    zbt = zt - 0.0060
    pv = [(float(inset[k, 0]), float(inset[k, 1]), float(zt[k])) for k in range(n)] + \
         [(float(inset[k, 0]), float(inset[k, 1]), float(zbt[k])) for k in range(n)]
    pf = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)] + [tuple(range(n)), tuple(range(n, 2 * n))]
    base.add(pv, pf, [[(0, 0)] * len(f) for f in pf], (0.0, ym, float(patch.zb(ym)) - 0.0036))
    if S.get("tongue"):
        zt0 = float(patch.zb(S["y0"]))
        box(base, (-0.017, S["y0"] - 0.026, zt0 - 0.0100), (0.017, S["y0"] + 0.040, zt0 - 0.0030), r=0.004)
    for bx, by in S["bumpers"]:
        z0 = float(patch.zb(by))
        cyl_z(base, (bx, by), 0.0072, z0 - 0.0090, z0 - 0.0040, q(12, 8))
    # ---- latch striker loop under the rear of the seat
    latch = MB()
    zl = float(patch.zb(S["latch_y"])) - 0.0040
    U = [(-0.012, zl), (-0.012, zl - 0.016), (-0.010, zl - 0.0215), (-0.004, zl - 0.0240), (0.004, zl - 0.0240),
         (0.010, zl - 0.0215), (0.012, zl - 0.016), (0.012, zl)]
    tube(latch, [(x, S["latch_y"], z) for x, z in U], 0.0024, q(10, 6), False, up=(0, 1, 0))
    return {
        f"{key}Top": top.obj(f"{key}Top", 50),
        f"{key}Sides": sides.obj(f"{key}Sides", 55),
        f"{key}Piping": piping.obj(f"{key}Piping", 70),
        f"{key}Base": base.obj(f"{key}Base", 40),
    }, latch, patch, tile


def box(mb, lo, hi, r=0.0):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    if r:
        # rounded front corners in plan (the tongue's tip slides under the tank)
        arc = lambda cx, a0: [(cx + r * math.cos(math.radians(a0 + 90 * i / 4)), y0 + r + r * math.sin(math.radians(a0 + 90 * i / 4))) for i in range(5)]  # noqa: E731
        pts = [(x0, y1)] + arc(x0 + r, 180) + arc(x1 - r, 270) + [(x1, y1)]
    else:
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    m = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    f = [(k, (k + 1) % m, m + (k + 1) % m, m + k) for k in range(m)] + [tuple(range(m)), tuple(range(m, 2 * m))]
    mb.add(v, f, [[(0, 0)] * len(ff) for ff in f], ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))


def cyl_z(mb, xy, r, z0, z1, seg):
    v = [(xy[0] + r * math.cos(2 * math.pi * k / seg), xy[1] + r * math.sin(2 * math.pi * k / seg), z) for z in (z0, z1) for k in range(seg)]
    f = [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)] + [tuple(range(seg)), tuple(range(seg, 2 * seg))]
    mb.add(v, f, [[(0, 0)] * len(ff) for ff in f], (xy[0], xy[1], (z0 + z1) / 2))


# ------------------------------------------------------------------ textures (no text anywhere)
def save_png(path, rgb):
    H, W, _ = rgb.shape
    im = bpy.data.images.new(os.path.basename(path), W, H, alpha=False)
    rgb = np.clip(rgb, 0, 1) ** (1 / 2.2)
    px = np.concatenate([rgb, np.ones((H, W, 1), np.float32)], -1)
    im.pixels.foreach_set(px.astype(np.float32).ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


def worley(X, Y, cell, seed, wrap_x=None):
    """Pebble leather: distance to the nearest and second nearest jittered cell point (in cells)."""
    rng = np.random.default_rng(seed)
    gx, gy = X / cell, Y / cell
    ix0, iy0 = np.floor(gx).astype(int), np.floor(gy).astype(int)
    nx = int(wrap_x) if wrap_x else int(ix0.max()) + 3
    ny = int(iy0.max()) + 3
    offx = 0 if wrap_x else int(ix0.min()) - 1
    offy = int(iy0.min()) - 1
    jit = rng.random((ny - offy + 3, (nx if wrap_x else nx - offx + 3), 2))
    val = rng.random(jit.shape[:2])
    F1 = np.full(X.shape, 9.0)
    F2 = np.full(X.shape, 9.0)
    V1 = np.zeros(X.shape)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx, cy = ix0 + dx, iy0 + dy
            jx = (cx % nx) if wrap_x else (cx - offx)
            jy = cy - offy
            px = cx + jit[jy, jx, 0]
            py = cy + jit[jy, jx, 1]
            d = np.hypot(gx - px, gy - py)
            closer = d < F1
            F2 = np.where(closer, F1, np.minimum(F2, d))
            V1 = np.where(closer, val[jy, jx], V1)
            F1 = np.where(closer, d, F1)
    return F1, F2, V1


def leather(F1, F2, V1, base):
    crease = np.exp(-((F2 - F1) / 0.10) ** 2)
    shade = 1.0 + 0.16 * (V1 - 0.5) - 0.30 * crease + 0.06 * (0.5 - F1)
    return np.array(base)[None, None, :] * shade[..., None]


def draw_capsules(img, segs, to_px, radius, color, hole=None):
    """segs: list of (p0, p1) in physical meters on a local flat map; to_px maps meters to pixel (col, row)."""
    H, W, _ = img.shape
    col = np.array(color)
    for p0, p1 in segs:
        c0, c1 = to_px(p0), to_px(p1)
        r = radius
        lo = np.floor(np.minimum(c0, c1) - r - 2).astype(int)
        hi = np.ceil(np.maximum(c0, c1) + r + 2).astype(int)
        lo = np.maximum(lo, 0)
        hi = np.minimum(hi, (W - 1, H - 1))
        if lo[0] > hi[0] or lo[1] > hi[1]:
            continue
        cc, rr = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        P = np.stack([cc, rr], -1).astype(float)
        d = c1 - c0
        t = np.clip(((P - c0) @ d) / max(d @ d, 1e-9), 0, 1)
        dist = np.linalg.norm(P - (c0 + t[..., None] * d), axis=-1)
        m = np.clip(r + 0.5 - dist, 0, 1)
        # thread is round: lighter along its middle
        hl = 1.0 + 0.35 * np.clip(1 - dist / max(r, 0.5), 0, 1)
        if hole is not None:      # needle holes at both ends
            for c in (c0 - d / max(np.linalg.norm(d), 1e-9) * r * 0.8, c1 + d / max(np.linalg.norm(d), 1e-9) * r * 0.8):
                hd = np.linalg.norm(P - c, axis=-1)
                hm = np.clip(r * 0.7 + 0.5 - hd, 0, 1)
                img[rr, cc] = img[rr, cc] * (1 - hm[..., None] * 0.7)
        img[rr, cc] = img[rr, cc] * (1 - m[..., None]) + (col * hl[..., None]) * m[..., None]


THREAD = (0.20, 0.20, 0.205)
LEATHER = (0.030, 0.030, 0.032)
LEATHER_GRIP = (0.024, 0.024, 0.026)


def top_texture(path, patch, seed, N=1024):
    """Top panel colour map in patch (a, b) space: pebble grain, perforated ribs, grooves darkened
    (baked shade, Roblox shows no small grooves), double topstitching along every groove and seam."""
    a = (np.arange(N) + 0.5) / N
    b = (np.arange(N) + 0.5) / N
    Am, Bm = np.meshgrid(a, b)               # row = b (image row 0 = v 0)
    XY = patch.P(Am, Bm)
    X, Y = XY[..., 0], XY[..., 1]
    f = patch.fields(Am, Bm)
    F1, F2, V1 = worley(X, Y, 0.0011, seed)
    img = leather(F1, F2, V1, LEATHER)
    # grip leather on the ribs: a touch darker + perforations in a staggered grid
    zone = f["inside"][..., None]
    img = img * (1 - zone) + img * (np.array(LEATHER_GRIP) / np.array(LEATHER)) * zone
    sp = 0.0042
    gy = Y / sp
    row = np.round(gy)
    gx = X / sp + 0.5 * (row % 2)
    dd = np.hypot((gx - np.round(gx)) * sp, (gy - row) * sp)
    clear = (f["inside"] > 0.99) & (f["g_pleat"] < 0.02) & (f["sd"] < -0.0045)
    hole = np.clip((0.00058 - dd) / 0.00018, 0, 1) * clear
    img *= (1 - 0.85 * hole)[..., None]
    # baked groove shade + shade under the piping at the outer edge
    shade = 1 - 0.55 * np.exp(-(f["sd"] / 0.0017) ** 2) - 0.55 * f["inside"] * f["g_pleat"] - 0.35 * np.exp(-(f["d_edge"] / 0.0018) ** 2)
    img *= np.clip(shade, 0.25, 1)[..., None]
    # stitches: work on a physical map per stitch (P is smooth, so a local affine is fine)
    segs = []

    def run(ab_pts, pitch=0.0050, length=0.0034):
        ab_pts = np.asarray(ab_pts)
        P = patch.P(ab_pts[:, 0], ab_pts[:, 1])
        d = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        s = pitch / 2
        while s + length < d[-1]:
            t0, t1 = np.interp(s, d, np.arange(len(d))), np.interp(s + length, d, np.arange(len(d)))
            segs.append((np.array([np.interp(t0, np.arange(len(d)), ab_pts[:, 0]), np.interp(t0, np.arange(len(d)), ab_pts[:, 1])]),
                         np.array([np.interp(t1, np.arange(len(d)), ab_pts[:, 0]), np.interp(t1, np.arange(len(d)), ab_pts[:, 1])])))
            s += pitch

    S = patch.S
    bz0, bz1 = patch.bz
    bb = np.linspace(bz0, bz1, 400)
    Wb = patch.W(bb)
    for off in (-0.0030, 0.0030):          # round the pleated zone, both sides of its groove
        dside = S["border"] + off
        run(np.stack([dside / Wb, bb], 1))
        run(np.stack([1 - dside / Wb, bb], 1))
        for bz, sgn in ((bz0, -1), (bz1, 1)):
            bl = bz + sgn * off / patch.Lc * (-1)
            Wl = float(patch.W(bl))
            aa = np.linspace(dside / Wl, 1 - dside / Wl, 300)
            run(np.stack([aa, np.full_like(aa, bl)], 1))
    for bk in patch.grooves:               # both sides of every pleat groove
        for off in (-0.0026, 0.0026):
            bl = bk + off / patch.Lc
            Wl = float(patch.W(bl))
            aa = np.linspace((S["border"] + 0.004) / Wl, 1 - (S["border"] + 0.004) / Wl, 300)
            run(np.stack([aa, np.full_like(aa, bl)], 1))
    # topstitch 4 mm in from the outer seam all the way round
    e = 0.004
    loop = []
    bb2 = np.linspace(e / patch.Lc, 1 - e / patch.Lc, 500)
    loop += list(np.stack([e / patch.W(bb2), bb2], 1))
    aa2 = np.linspace(e / patch.W(bb2[-1]), 1 - e / patch.W(bb2[-1]), 200)
    loop += list(np.stack([aa2, np.full_like(aa2, bb2[-1])], 1))
    loop += list(np.stack([1 - e / patch.W(bb2[::-1]), bb2[::-1]], 1))
    aa3 = np.linspace(1 - e / patch.W(bb2[0]), e / patch.W(bb2[0]), 200)
    loop += list(np.stack([aa3, np.full_like(aa3, bb2[0])], 1))
    run(np.array(loop))
    # draw: pixel space is (a, b) * N; thread radius in px from the local physical scale
    for p0, p1 in segs:
        mid = (p0 + p1) / 2
        Wl = float(patch.W(mid[1]))
        r_px = max(0.9, 0.00042 / max(min(Wl, patch.Lc), 1e-6) * N)
        draw_capsules(img, [(p0, p1)], lambda p: np.array([p[0] * N - 0.5, p[1] * N - 0.5]), r_px, THREAD, hole=True)
    save_png(path, img)


def side_texture(path, tile, seed, N=1024):
    """Side panel tile (repeats along the seat): pebble grain, a topstitch row under the piping,
    shade right under the piping. v = 0 at the top of the image = the seam."""
    X = (np.arange(N) + 0.5) / N * tile
    Yd = (np.arange(N) + 0.5) / N * VS          # meters down from the seam, row 0 = top
    Xm, Ym = np.meshgrid(X, Yd)
    cells = max(1, round(tile / 0.0011))
    F1, F2, V1 = worley(Xm, Ym, tile / cells, seed, wrap_x=cells)
    img = leather(F1, F2, V1, LEATHER)
    img *= (1 - 0.55 * np.exp(-(Ym / 0.0018) ** 2))[..., None]
    n = max(1, round(tile / 0.0050))
    pitch = tile / n
    segs = []
    for row_y in (0.0048,):
        for i in range(n + 1):
            x0 = i * pitch - pitch / 2 + 0.0008
            segs.append((np.array([x0, row_y]), np.array([x0 + 0.0034, row_y])))
    to_px = lambda p: np.array([p[0] / tile * N - 0.5, p[1] / VS * N - 0.5])  # noqa: E731
    draw_capsules(img, segs, to_px, max(0.9, 0.00042 / VS * N), THREAD, hole=True)
    # rows were drawn top-down; the image array's row 0 is v = 0 (bottom) in Blender
    save_png(path, img[::-1].copy())


# ------------------------------------------------------------------ looks
def L_tex(tex, rough, refl=0.02):
    return {"tex": tex, "rough": rough, "metal": 0.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": refl}}


LOOKS = {
    "RiderTop": L_tex("RiderTop", 0.48), "RiderSides": L_tex("RiderSides", 0.4),
    "PillionTop": L_tex("PillionTop", 0.48), "PillionSides": L_tex("PillionSides", 0.4),
    "RiderPiping": {"color": (0.022, 0.022, 0.024), "rough": 0.38, "metal": 0.0, "roblox": {"Color": [30, 30, 32], "Material": "SmoothPlastic", "Reflectance": 0.03}},
    "PillionPiping": {"color": (0.022, 0.022, 0.024), "rough": 0.38, "metal": 0.0, "roblox": {"Color": [30, 30, 32], "Material": "SmoothPlastic", "Reflectance": 0.03}},
    "RiderBase": {"color": (0.012, 0.012, 0.013), "rough": 0.6, "metal": 0.0, "roblox": {"Color": [20, 20, 22], "Material": "SmoothPlastic"}},
    "PillionBase": {"color": (0.012, 0.012, 0.013), "rough": 0.6, "metal": 0.0, "roblox": {"Color": [20, 20, 22], "Material": "SmoothPlastic"}},
    "SeatLatch": {"color": (0.55, 0.56, 0.58), "rough": 0.3, "metal": 1.0, "roblox": {"Color": [160, 162, 168], "Material": "SmoothPlastic", "Reflectance": 0.12}},
}
TEXFILES = {"RiderTop": "RiderTop_Color.png", "RiderSides": "RiderSide_Color.png",
            "PillionTop": "PillionTop_Color.png", "PillionSides": "PillionSide_Color.png"}


def material(key):
    L = LOOKS[key]
    m = bpy.data.materials.new("M_" + key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = L["rough"]
    b.inputs["Metallic"].default_value = L["metal"]
    if not L["metal"]:
        b.inputs["Specular IOR Level"].default_value = 0.3
    if L.get("tex"):
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, TEXFILES[L["tex"]]), check_existing=True)
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*L["color"], 1)
    return m


# ------------------------------------------------------------------ build + export
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    parts, latches = {}, []
    for i, key in enumerate(SEATS):
        p, latch, patch, tile = build_seat(key)
        parts.update(p)
        latches.append(latch)
        top_texture(os.path.join(TEX, TEXFILES[f"{key}Top"]), patch, 100 + i)
        side_texture(os.path.join(TEX, TEXFILES[f"{key}Sides"]), tile, 200 + i)
    lm = MB()
    for l in latches:
        o = len(lm.v)
        lm.v += l.v
        lm.f += [tuple(i + o for i in f) for f in l.f]
        lm.uv += l.uv
    parts["SeatLatch"] = lm.obj("SeatLatch", 50)
    for name, ob in parts.items():
        ob.data.materials.clear()
        ob.data.materials.append(material(name))
    return parts


def export(parts):
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: +X = bike's LEFT, -Y = front, +Z = up; origin = ground between the axles (bike layout).",
            "parts": {}, "looks": {}}
    texmap = {}
    for name, ob in parts.items():
        meta["parts"][name] = {"tris": G.tris(ob)}
        meta["looks"][name] = LOOKS[name]["roblox"]
        if LOOKS[name].get("tex"):
            texmap[name] = f"art/models/BikeSeats/tex/{TEXFILES[LOOKS[name]['tex']]}"
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
    path = os.path.join(OUT, "BikeSeats.glb")
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
    print("BikeSeats tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})
    for k, v in meta["parts"].items():
        assert v["tris"] < 20000, (k, v)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = build()
    export(parts)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
