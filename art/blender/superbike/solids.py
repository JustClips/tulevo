"""Solid-part helpers for the mechanical superbike parts (frame, swingarm, forks, engine ...).

Solid collects faces and turns each one to face outward (by a per-face direction), then makes an object
shaded smooth with sharp edges by angle, so boxy castings keep crisp edges and tubes stay round.
Builders: sweep (any 2D section along a 3D path), pillow (a 2D outline extruded with a rounded front
edge, for covers, plates and castings), lathe, spring, and section shapes rrect / circle.
"""
import math

import bpy
import numpy as np
from shapely.geometry import Polygon

import geo as G


def _newell(P):
    Q = np.roll(P, -1, 0)
    return np.array([np.sum((P[:, 1] - Q[:, 1]) * (P[:, 2] + Q[:, 2])),
                     np.sum((P[:, 2] - Q[:, 2]) * (P[:, 0] + Q[:, 0])),
                     np.sum((P[:, 0] - Q[:, 0]) * (P[:, 1] + Q[:, 1]))])


class Solid:
    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add(self, V, F, out, UV=None):
        """out: (nF, 3) direction each face must point, or one inside point (3,) for all faces."""
        V = np.asarray(V, float)
        o = len(self.v)
        out = np.asarray(out, float)
        for k, f in enumerate(F):
            P = V[list(f)]
            d = out[k] if out.ndim == 2 else P.mean(0) - out
            if _newell(P) @ d < 0:
                f = f[::-1]
            self.f.append(tuple(i + o for i in f))
        self.v.extend(map(tuple, V))
        self.uv.extend(map(tuple, UV if UV is not None else np.zeros((len(V), 2))))

    def merge(self, other):
        o = len(self.v)
        self.v += other.v
        self.uv += other.uv
        self.f += [tuple(i + o for i in f) for f in other.f]

    def obj(self, name, angle=40):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.validate()
        lay = me.uv_layers.new(name="UVMap")
        uv = np.array(self.uv, np.float32)
        li = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", li)
        lay.data.foreach_set("uv", uv[li].ravel())
        me.update()
        ob = G.new_obj(name, me)
        G.smooth(ob, angle)
        return ob


# ------------------------------------------------------------------ sections (2D loops, counter-clockwise)
def circle(r, m=16, a0=0.0):
    a = a0 + np.linspace(0, 2 * math.pi, m, endpoint=False)
    return np.stack([r * np.cos(a), r * np.sin(a)], 1)


def rrect(w, h, r=None, k=3):
    """Rounded rectangle, half sizes w (side) x h (up), corner radius r."""
    r = min(w, h) * 0.35 if r is None else min(r, w, h)
    pts = []
    for cx, cy, a0 in ((w - r, h - r, 0), (-(w - r), h - r, 90), (-(w - r), -(h - r), 180), (w - r, -(h - r), 270)):
        for t in np.linspace(math.radians(a0), math.radians(a0 + 90), k + 1):
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return np.array(pts)


def resample_loop(P, n, start_dir=(1.0, 0.0)):
    """Closed 2D loop -> n points evenly by arc length, counter-clockwise, starting nearest start_dir from the centroid."""
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    if 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) < 0:
        P = P[::-1]
    c = P.mean(0)
    ang = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
    a0 = math.atan2(start_dir[1], start_dir[0])
    k = int(np.argmin(np.abs(np.angle(np.exp(1j * (ang - a0))))))
    P = np.roll(P, -k, 0)
    Q = np.vstack([P, P[:1]])
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.stack([np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])], 1)


# ------------------------------------------------------------------ builders
def frames(path, up=(0, 0, 1.0)):
    path = np.asarray(path, float)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.asarray(up, float)
    S, U = [], []
    s_prev = None
    for t in T:
        s = np.cross(t, up)
        if np.linalg.norm(s) < 1e-6:
            s = s_prev if s_prev is not None else np.cross(t, [1.0, 0, 0])
        s = s / np.linalg.norm(s)
        u = np.cross(s, t)
        S.append(s)
        U.append(u)
        s_prev = s
    return T, np.array(S), np.array(U)


def sweep(sol, path, section, caps=True, up=(0, 0, 1.0), closed=False, uv_len=None):
    """section: one (m, 2) loop, or a list of loops (one per path point, same m), in the (side, up) frame."""
    path = np.asarray(path, float)
    n = len(path)
    T, S, U = frames(path, up)
    secs = [np.asarray(section, float)] * n if np.ndim(section) == 2 else [np.asarray(s, float) for s in section]
    m = len(secs[0])
    V = np.vstack([path[i] + np.outer(secs[i][:, 0], S[i]) + np.outer(secs[i][:, 1], U[i]) for i in range(n)])
    faces, outs = [], []
    rng = n if closed else n - 1
    for i in range(rng):
        i2 = (i + 1) % n
        for j in range(m):
            j2 = (j + 1) % m
            f = (i * m + j, i * m + j2, i2 * m + j2, i2 * m + j)
            faces.append(f)
            outs.append(V[list(f)].mean(0) - (path[i] + path[i2]) / 2)
    seg = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    L = uv_len or max(seg[-1], 1e-6)
    UV = np.stack([np.tile(np.arange(m) / m, n), np.repeat(seg / L, m)], 1)
    sol.add(V, faces, np.array(outs), UV)
    if caps and not closed:
        for i, sg in ((0, -1.0), (n - 1, 1.0)):
            ring = V[i * m:(i + 1) * m]
            c = ring.mean(0)
            vv = np.vstack([ring, c])
            fs = [(j, (j + 1) % m, m) for j in range(m)]
            sol.add(vv, fs, np.tile(T[i] * sg, (m, 1)))
    return V


def pillow(sol, loop2d, origin, e1, e2, t, r=0.004, k=3, back=True, n=None):
    """2D outline (in e1, e2 at origin) pushed out along n = e1 x e2 by t, front edge rounded with radius r."""
    origin, e1, e2 = (np.asarray(a, float) for a in (origin, e1, e2))
    nrm = np.cross(e1, e2)
    nrm /= np.linalg.norm(nrm)
    poly = Polygon(loop2d).buffer(0)
    N = n or max(24, int(poly.length / 0.004))
    r = min(r, t)
    rings = []
    depths = [0.0] if back else []
    insets = [0.0] if back else []
    for j in range(k + 1):
        a = 0.5 * math.pi * j / k
        depths.append(t - r + r * math.sin(a))
        insets.append(r * (1 - math.cos(a)))
    for d, s in zip(depths, insets):
        p = poly.buffer(-s, join_style="round", quad_segs=4) if s > 1e-6 else poly
        if p.geom_type != "Polygon":
            p = max(p.geoms, key=lambda q: q.area)
        L = resample_loop(np.array(p.exterior.coords)[:-1], N)
        rings.append(origin + np.outer(L[:, 0], e1) + np.outer(L[:, 1], e2) + d * nrm)
    V = np.vstack(rings)
    faces, outs = [], []
    for i in range(len(rings) - 1):
        for j in range(N):
            j2 = (j + 1) % N
            f = (i * N + j, i * N + j2, (i + 1) * N + j2, (i + 1) * N + j)
            faces.append(f)
            c2 = rings[i].mean(0)
            outs.append(V[list(f)].mean(0) - c2 - (V[list(f)].mean(0) - c2) @ nrm * nrm + 1e-3 * nrm * (1 if i >= len(rings) - 2 else 0))
    sol.add(V, faces, np.array(outs))
    # front cap (CDT of the last ring) and back cap
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    for ring, sg in ((rings[-1], 1.0), (rings[0], -1.0)) if back else ((rings[-1], 1.0),):
        Q = np.stack([(ring - origin) @ e1, (ring - origin) @ e2], 1)
        vo, eo, fo, ov, oe, of = delaunay_2d_cdt([Vector(q) for q in Q], [(i, (i + 1) % N) for i in range(N)], [], 1, 1e-9)
        VV = np.array([tuple(v) for v in vo])
        tri = [f for f in fo if len(f) == 3]
        Cc = VV[np.array(tri)].mean(1)
        from shapely import points, contains
        ok = contains(Polygon(Q), points(Cc[:, 0], Cc[:, 1]))
        tri = [f for f, o in zip(tri, ok) if o]
        d = (ring[0] - origin) @ nrm
        V3 = origin + np.outer(VV[:, 0], e1) + np.outer(VV[:, 1], e2) + d * nrm
        sol.add(V3, tri, np.tile(nrm * sg, (len(tri), 1)))
    return rings


def lathe(sol, profile, origin, axis, seg=24):
    """Revolve (r, h) profile round axis. Travel so the outside is on the right (up the side, then inward over the top)."""
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
        nr, nh = jn[1] - jp[1], -(jn[0] - jp[0])
        for t in ang:
            d = math.cos(t) * a + math.sin(t) * b
            V.append(np.asarray(origin) + axis * h + d * r)
            NN.append(axis * nh + d * nr)
    V, NN = np.array(V), np.array(NN)
    faces, outs = [], []
    for j in range(n - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            r0, r1 = prof[j][0], prof[j + 1][0]
            if r0 < 1e-9 and r1 < 1e-9:
                continue
            if r0 < 1e-9:
                f = (j * seg + k, (j + 1) * seg + k2, (j + 1) * seg + k)
            elif r1 < 1e-9:
                f = (j * seg + k, j * seg + k2, (j + 1) * seg + k)
            else:
                f = (j * seg + k, j * seg + k2, (j + 1) * seg + k2, (j + 1) * seg + k)
            faces.append(f)
            outs.append(NN[j * seg + k] + NN[(j + 1) * seg + k])
    UV = np.stack([np.tile(ang / (2 * math.pi), n), np.repeat(np.arange(n) / max(1, n - 1), seg)], 1)
    sol.add(V, faces, np.array(outs), UV)


def tube(sol, pts, r, seg=12, caps=True, up=(0, 0, 1.0)):
    return sweep(sol, pts, circle(r, seg), caps=caps, up=up)


def spring(sol, p0, axis, R, wire, turns, length, seg=8, per_turn=20, ground=True):
    """Coil spring from p0 along axis; ground ends (a flat closed turn at each end)."""
    axis = np.asarray(axis, float)
    axis /= np.linalg.norm(axis)
    a = np.cross(axis, [0, 0, 1.0]) if abs(axis[2]) < 0.9 else np.cross(axis, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(axis, a)
    n = int(turns * per_turn) + 1
    t = np.linspace(0, 1, n)
    ang = 2 * math.pi * turns * t
    if ground:
        # end turns closed up: pitch ramps from 0 over the first and last turn
        e = 1.0 / turns
        h = np.where(t < e, wire * 2 * t / e * 0.5, np.where(t > 1 - e, length - wire * (1 - t) / e, 0))
        mid = (t >= e) & (t <= 1 - e)
        h[mid] = wire + (t[mid] - e) / (1 - 2 * e) * (length - 2 * wire)
    else:
        h = t * length
    pts = np.asarray(p0) + np.outer(np.cos(ang) * R, a) + np.outer(np.sin(ang) * R, b) + np.outer(h, axis)
    return sweep(sol, pts, circle(wire, seg), caps=True, up=axis)


def box(sol, c, size, axes=None, r=0.0):
    """Box centred at c with half sizes size along axes (3 unit vectors); r rounds the side edges (along axes[1])."""
    c = np.asarray(c, float)
    ax = np.eye(3) if axes is None else np.asarray(axes, float)
    path = [c - ax[1] * size[1], c + ax[1] * size[1]]
    sec = rrect(size[0], size[2], r if r > 0 else 1e-4, k=3 if r > 0 else 1)
    return sweep(sol, path, sec, caps=True, up=ax[2])
