"""Superbike exhaust (S1000RR-style layout, our own design, no text or marks).

  python art/blender/superbike/exhaust.py      (needs `pip install bpy numpy`)
  python art/blender/superbike/render.py exhaust

Four headers leave the cylinder head (ports face forward-down), drop in front of the engine,
and merge 4-2-1: cylinders 1+4 (pipe 4 crosses under 2 and 3) and 2+3, then both secondaries
run into a box under the engine. A short link pipe with the exhaust valve goes out to the
right to a compact silencer under the swingarm, with a carbon heat shield and a black end cap.

Coordinates are the bike's (meters): +X = bike's LEFT, -Y = front, +Z = up, origin on the
ground halfway between the axles (same as wheels.py / the future bike).
Writes art/models/BikeExhaust/BikeExhaust.glb in STUDS (x3.6 baked in, Scale 1), meta.json,
textures.json + tex/*.png, work.blend.
"""
import json
import math
import os
import struct
import sys

import bpy
import bmesh  # noqa: E402  (after bpy)
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo as G  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "art", "models", "BikeExhaust")
TEX = os.path.join(OUT, "tex")
STUDS = 3.6
rad = math.radians

R_HEADER = 0.0185       # 37 mm primaries
R_SECOND = 0.0245       # 49 mm secondaries
R_LINK = 0.027


# ------------------------------------------------------------------ path + sweep helpers
def catmull(pts, per=10):
    P = [Vector(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(per):
            t = s / per
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def resample(pts, step):
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    n = max(2, int(L[-1] / step) + 1)
    out = []
    j = 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append(pts[j].lerp(pts[j + 1], t))
    return out, L[-1]


def frames(pts, up=Vector((0, 0, 1))):
    """Parallel-transport frames (tangent, normal, binormal) along a polyline (no twisting)."""
    T = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        T.append((b - a).normalized())
    n = up - T[0] * up.dot(T[0])
    if n.length < 1e-4:
        n = Vector((1, 0, 0)) - T[0] * T[0].x
    n.normalize()
    N = [n]
    for i in range(1, len(pts)):
        v = T[i - 1].cross(T[i])
        n = N[-1]
        if v.length > 1e-8:
            ang = math.asin(min(1.0, v.length))
            if T[i - 1].dot(T[i]) < 0:
                ang = math.pi - ang
            n = Matrix.Rotation(ang, 3, v.normalized()) @ n
        n = (n - T[i] * n.dot(T[i])).normalized()
        N.append(n)
    B = [t.cross(n) for t, n in zip(T, N)]
    return T, N, B


def sweep(name, pts, section, step=0.006, cap=True, uv_len=None, up=Vector((0, 0, 1))):
    """Sweep a 2D section along a smooth path. section(s) -> list of (a, b) offsets (normal,
    binormal) for arc length fraction s, same count every time (closed loop).
    UV: u = arc length / uv_len (or 0..1), v = perimeter fraction. Returns the object."""
    pts, length = resample(pts, step)
    T, N, B = frames(pts, up)
    m = len(section(0.0))
    verts, uvs_v = [], []
    for i, p in enumerate(pts):
        s = i / (len(pts) - 1)
        sec = section(s)
        for a, b in sec:
            verts.append(p + N[i] * a + B[i] * b)
    # perimeter fractions for v
    sec0 = section(0.0)
    per = [0.0]
    for k in range(1, m + 1):
        a, b = sec0[k - 1], sec0[k % m]
        per.append(per[-1] + math.dist(a, b))
    per = [x / per[-1] for x in per]
    faces, uvs = [], []
    nrows = len(pts)
    for i in range(nrows - 1):
        u0 = (i / (nrows - 1)) * (length / uv_len if uv_len else 1.0)
        u1 = ((i + 1) / (nrows - 1)) * (length / uv_len if uv_len else 1.0)
        for k in range(m):
            k2 = (k + 1) % m
            faces.append((i * m + k, i * m + k2, (i + 1) * m + k2, (i + 1) * m + k))
            uvs.append(((u0, per[k]), (u0, per[k + 1]), (u1, per[k + 1]), (u1, per[k])))
    if cap:
        faces.append(tuple(range(m))[::-1])
        uvs.append(tuple((0.0, 0.0) for _ in range(m)))
        last = (nrows - 1) * m
        faces.append(tuple(last + k for k in range(m)))
        uvs.append(tuple((0.0, 0.0) for _ in range(m)))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    lay = me.uv_layers.new(name="UVMap")
    for f, fu in zip(me.polygons, uvs):
        for li, u in zip(f.loop_indices, fu):
            lay.data[li].uv = u
    me.update()
    ob = G.new_obj(name, me)
    G.fix_normals(ob)
    ob["length"] = length
    ob["start"] = list(pts[0])
    ob["end"] = list(pts[-1])
    ob["t0"] = list(T[0])
    ob["t1"] = list(T[-1])
    return ob


def circle(r, n=18):
    return lambda s: [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def chaikin(poly, it=2):
    for _ in range(it):
        out = []
        for i in range(len(poly)):
            a, b = np.array(poly[i]), np.array(poly[(i + 1) % len(poly)])
            out += [tuple(0.75 * a + 0.25 * b), tuple(0.25 * a + 0.75 * b)]
        poly = out
    return poly


def resample_poly(poly, n):
    pts = [np.array(p) for p in poly] + [np.array(poly[0])]
    L = np.r_[0, np.cumsum([np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])])]
    out = []
    for k in range(n):
        s = L[-1] * k / n
        j = min(np.searchsorted(L, s, side="right") - 1, len(pts) - 2)
        t = (s - L[j]) / max(1e-9, L[j + 1] - L[j])
        out.append(tuple(pts[j] * (1 - t) + pts[j + 1] * t))
    return out


def ring(name, r_in, r_out, length, p, d, seg=24):
    """Hollow ring (band clamp, flange collar) centred at p along direction d."""
    prof = [(-length / 2, r_in), (length / 2, r_in), (length / 2, r_out), (-length / 2, r_out)]
    ob = G.lathe(name, prof, seg=seg, uv=False)
    ob.data.transform(Matrix.Translation(p) @ Vector(d).to_track_quat('X', 'Z').to_matrix().to_4x4())
    return ob


def cyl(name, r, p0, p1, seg=16):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = G.new_obj(name, me)
    ob.data.transform(Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    return ob


def hexnut(name, r, p, d, h):
    return cyl(name, r, Vector(p), Vector(p) + Vector(d).normalized() * h, seg=6)


# ------------------------------------------------------------------ the layout
PORT_Y, PORT_Z = -0.330, 0.605
PORT_DIR = Vector((0, -0.90, -0.44)).normalized()
HEADERS = {
    # cylinder: control points (port first). Pipes 1+4 merge low on the left, 2+3 higher on the right.
    1: [(0.105, PORT_Y, PORT_Z), (0.106, -0.362, 0.589), (0.118, -0.392, 0.548), (0.128, -0.405, 0.465),
        (0.126, -0.397, 0.365), (0.117, -0.374, 0.272), (0.104, -0.33, 0.198), (0.088, -0.272, 0.170),
        (0.075, -0.215, 0.165), (0.070, -0.165, 0.165)],
    4: [(-0.105, PORT_Y, PORT_Z), (-0.106, -0.362, 0.589), (-0.118, -0.392, 0.548), (-0.128, -0.405, 0.465),
        (-0.126, -0.397, 0.365), (-0.116, -0.374, 0.272), (-0.098, -0.338, 0.192), (-0.055, -0.300, 0.157),
        (0.0, -0.262, 0.150), (0.024, -0.215, 0.157), (0.030, -0.165, 0.165)],
    2: [(0.035, PORT_Y, PORT_Z), (0.035, -0.362, 0.589), (0.040, -0.390, 0.548), (0.046, -0.399, 0.465),
        (0.046, -0.392, 0.365), (0.036, -0.368, 0.278), (0.012, -0.326, 0.228), (-0.014, -0.262, 0.210),
        (-0.020, -0.205, 0.205), (-0.020, -0.165, 0.205)],
    3: [(-0.035, PORT_Y, PORT_Z), (-0.035, -0.362, 0.589), (-0.040, -0.390, 0.548), (-0.046, -0.399, 0.465),
        (-0.048, -0.392, 0.365), (-0.052, -0.368, 0.278), (-0.060, -0.328, 0.230), (-0.061, -0.262, 0.212),
        (-0.060, -0.205, 0.206), (-0.060, -0.165, 0.205)],
}
MERGE_A = {"pipes": (1, 4), "y0": -0.165, "y1": -0.105, "end": Vector((0.050, -0.105, 0.165))}
MERGE_B = {"pipes": (2, 3), "y0": -0.165, "y1": -0.105, "end": Vector((-0.040, -0.105, 0.205))}
BOX = {"min": Vector((-0.118, 0.0, 0.122)), "max": Vector((0.108, 0.215, 0.252))}
SILENCER_A = Vector((-0.212, 0.262, 0.272))
SILENCER_B = Vector((-0.226, 0.565, 0.402))


def headers():
    obs = []
    for cyl_i, pts in HEADERS.items():
        path = catmull(pts, 12)
        ob = sweep(f"h{cyl_i}", path, circle(R_HEADER, 18), step=0.005, cap=True)
        obs.append(ob)
    return obs


def merge(spec):
    """Y collector: from two pipe ends side by side to one round secondary."""
    a, b = spec["pipes"]
    pa, pb = Vector(HEADERS[a][-1]), Vector(HEADERS[b][-1])
    mid = (pa + pb) / 2
    sep = (pa - pb).length / 2
    end = spec["end"]
    d = (end - mid).normalized()
    # stadium -> circle sections
    n = 32

    def section(s):
        half = sep * (1 - smooth(s))
        r = R_HEADER + 0.0012 + (R_SECOND - R_HEADER - 0.0012) * smooth(s)
        pts = []
        for k in range(n):
            ang = 2 * math.pi * k / n
            c, sn = math.cos(ang), math.sin(ang)
            pts.append((r * c + math.copysign(half, c) if abs(c) > 1e-9 else r * c, r * sn))
        return pts
    # the stadium's long axis must point from pipe b to pipe a: use that as the sweep "normal"
    axis = (pa - pb).normalized()
    up = axis.cross(d).cross(d) * -1
    path = [mid - d * 0.012 + d * (end - mid).length * t / 10 for t in range(11)]
    ob = sweep("merge", path, section, step=0.004, cap=True, up=axis)
    return ob, end, d


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def secondaries():
    obs = []
    ends = []
    for spec, entry in ((MERGE_A, Vector((0.050, 0.035, 0.165))), (MERGE_B, Vector((-0.040, 0.035, 0.205)))):
        m, end, d = merge(spec)
        obs.append(m)
        path = catmull([end - d * 0.004, end + d * 0.03, (end + entry) / 2, entry], 10)
        obs.append(sweep("sec", path, circle(R_SECOND, 22), step=0.006))
        ends.append((end, d))
    return obs, ends


def presilencer():
    """Rounded box under the engine with pressed seams, plus a front cone where the secondaries enter."""
    mn, mx = BOX["min"], BOX["max"]
    size = mx - mn
    ctr = (mn + mx) / 2
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new("box")
    bm.to_mesh(me)
    bm.free()
    ob = G.new_obj("box", me)
    ob.scale = size
    ob.location = ctr
    G.apply(ob)
    G.bevel(ob, 0.028, 4, 40)
    obs = [ob]
    # seam band round the middle (slightly proud), and two stiffening ribs on the bottom
    rr = G.rounded_rect(size.x + 0.004, size.z + 0.004, 5, 0.030 / min(size.x, size.z))
    seam = G.loft("seam", [[Vector((ctr.x + a, ctr.y + 0.02 + dy, ctr.z + b)) for a, b in rr] for dy in (-0.005, 0.005)])
    obs.append(seam)
    return obs


def link_and_valve():
    path = catmull([(-0.085, 0.165, 0.195), (-0.125, 0.18, 0.205), (-0.168, 0.205, 0.228), (-0.198, 0.238, 0.257),
                    SILENCER_A + (SILENCER_A - SILENCER_B).normalized() * 0.01], 12)
    link = sweep("link", path, circle(R_LINK, 22), step=0.006)
    # exhaust valve body round the link pipe + servo cable pulley on top
    pos = Vector((-0.150, 0.192, 0.215))
    d = (Vector((-0.168, 0.205, 0.228)) - Vector((-0.125, 0.18, 0.205))).normalized()
    valve = [ring("valve", R_LINK - 0.002, R_LINK + 0.009, 0.050, pos, d, 28)]
    valve.append(cyl("pulley", 0.016, pos + Vector((0, 0, R_LINK + 0.006)), pos + Vector((0, 0, R_LINK + 0.020)), 24))
    valve.append(hexnut("pulleynut", 0.006, pos + Vector((0, 0, R_LINK + 0.020)), (0, 0, 1), 0.006))
    return link, valve


def silencer():
    a, b = SILENCER_A, SILENCER_B
    d = (b - a).normalized()
    # cross-section: a chamfered hexagon, a little wider at the top (seen from behind)
    hexa = [(-0.040, -0.058), (0.040, -0.058), (0.051, -0.004), (0.037, 0.061), (-0.037, 0.061), (-0.051, -0.004)]
    base = resample_poly(chaikin(hexa, 2), 48)

    def body_sec(s):
        k = 1.0 - 0.10 * s
        return [(x * k, y * k) for x, y in base]

    L = (b - a).length
    up = Vector((1, 0, 0))   # section "x" = sideways, "y" = up
    path = [a + d * L * t / 12 for t in range(13)]
    body = sweep("Silencer", path, lambda s: [(y, x) for x, y in body_sec(s)], step=0.01, cap=True, uv_len=0.30, up=Vector((0, 0, 1)))

    # inlet cone from the link pipe into the body
    cone_path = [a - d * 0.055 + d * 0.06 * t / 6 for t in range(7)]

    def cone_sec(s):
        sc = s
        out = []
        for k in range(48):
            ang = 2 * math.pi * k / 48
            rc = (R_LINK + 0.001) * (1 - sc)
            bx, by = base[k]
            out.append((by * sc * 0.97 + rc * math.sin(ang) * (1 - sc) * 0 + (1 - sc) * rc * math.sin(ang),
                        bx * sc * 0.97 + (1 - sc) * rc * math.cos(ang)))
        return out
    cone = sweep("cone", cone_path, cone_sec, step=0.008, cap=True)

    # carbon heat shield on the outer (right, -X) side: offset shell over the outer faces
    def shield_sec(s):
        k = 1.0 - 0.10 * s
        pts = []
        idx = [i for i, (x, y) in enumerate(base) if x < -0.012]
        idx.sort(key=lambda i: math.atan2(base[i][1], base[i][0]) % (2 * math.pi))
        outer = [(base[i][0] * k * 1.0 - 0.0035, base[i][1] * k * 0.94) for i in idx]
        inner = [(base[i][0] * k * 1.0 - 0.0012, base[i][1] * k * 0.94) for i in idx[::-1]]
        pts = outer + inner
        return [(y, x) for x, y in pts]
    s0, s1 = 0.08, 0.86
    shield_path = [a + d * L * (s0 + (s1 - s0) * t / 10) for t in range(11)]
    shield = sweep("HeatShield", shield_path, shield_sec, step=0.01, cap=True, uv_len=0.03, up=Vector((0, 0, 1)))
    # box-project carbon UVs (repeat every 3 cm) so the weave stays square
    me = shield.data
    lay = me.uv_layers[0]
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            v = me.vertices[vi].co
            lay.data[li].uv = (v.y / 0.03, v.z / 0.03)

    # end cap: short bevelled tail + two outlets
    cap_path = [b - d * 0.004 + d * 0.042 * t / 6 for t in range(7)]

    def cap_sec(s):
        k = 0.9 * (1 - 0.12 * smooth((s - 0.4) / 0.6))
        return [(y * k * 1.005, x * k * 1.005) for x, y in base]
    endcap = sweep("EndCap", cap_path, cap_sec, step=0.006, cap=True)
    tips = []
    tip_end = b + d * 0.050
    side = Vector((0, 0, 1)).cross(d).normalized()
    for off in (Vector((0, 0, 0.022)), Vector((0, 0, -0.020))):
        c = tip_end + off + side * 0.004
        tips.append(ring("outlet", 0.0135, 0.0175, 0.034, c, d, 28))
        tips.append(cyl("outletdark", 0.0136, c - d * 0.017, c + d * 0.006, 24))
    # band clamp at the inlet + rivets along the shield
    band = ring("band", R_LINK + 0.0005, R_LINK + 0.0045, 0.016, a - d * 0.04, d, 28)
    rivets = []
    for t in (0.16, 0.47, 0.78):
        p = a + d * L * t
        rivets.append(cyl("rivet", 0.0035, p + Vector((-0.056 * (1 - 0.1 * t), 0, 0)), p + Vector((-0.062 * (1 - 0.1 * t), 0, 0)), 10))
    # hanger strap from the silencer top up to the rear-set plate
    hang = []
    hp = a + d * L * 0.62 + Vector((0, 0, 0.058))
    hang.append(G.loft("strap", [[hp + Vector((dx, 0, 0)) + Vector((0, a_, b_)) for a_, b_ in ((-0.012, 0), (0.012, 0), (0.012, 0.004), (-0.012, 0.004))]
                                 for dx in (0,)] + [[hp + Vector((0.045, -0.03, 0.10)) + Vector((0, a_, b_)) for a_, b_ in ((-0.012, 0), (0.012, 0), (0.012, 0.004), (-0.012, 0.004))]]))
    hang.append(cyl("hbolt", 0.007, hp + Vector((0.045, -0.03, 0.10)) - Vector((0.012, 0, 0)), hp + Vector((0.045, -0.03, 0.10)) + Vector((0.012, 0, 0)), 6))
    return body, cone, shield, endcap, tips, band, rivets, hang


def flanges():
    obs = []
    for cyl_i, pts in HEADERS.items():
        p = Vector(pts[0])
        d = PORT_DIR
        # oval flange plate across the pipe + collar
        side = Vector((1, 0, 0))
        up = d.cross(side).normalized()
        outline = [(math.cos(2 * math.pi * k / 32) * 0.036, math.sin(2 * math.pi * k / 32) * 0.022) for k in range(32)]
        secs = [[p + d * off + side * x + up * y for x, y in outline] for off in (0.006, 0.016)]
        obs.append(G.loft("flange", secs))
        obs.append(ring("collar", R_HEADER - 0.001, R_HEADER + 0.0045, 0.014, p + d * 0.021, d, 24))
        for sx in (-1, 1):
            q = p + side * sx * 0.027 + d * 0.016
            obs.append(cyl("stud", 0.004, q - d * 0.008, q + d * 0.012, 8))
            obs.append(hexnut("nut", 0.0068, q, d, 0.008))
    return obs


def sensors(ends):
    obs = []
    for (end, d), off in zip(ends, (Vector((0.0, 0.02, 0.0)), Vector((0.0, 0.02, 0.0)))):
        p = end + d * 0.05
        up = Vector((0, 0, 1))
        base = p + up * (R_SECOND - 0.002)
        obs.append(hexnut("bung", 0.010, base, up, 0.008))
        obs.append(cyl("o2", 0.0075, base + up * 0.008, base + up * 0.040, 14))
        obs.append(cyl("o2cap", 0.0055, base + up * 0.040, base + up * 0.055, 12))
    return obs


def spring_clamps(ends):
    """Two coil springs bridging each merge slip joint."""
    obs = []
    for end, d in ends:
        side = Vector((0, 0, 1)).cross(d).normalized()
        for sx in (-1, 1):
            c0 = end - d * 0.040 + side * sx * (R_SECOND + 0.005)
            c1 = end + d * 0.022 + side * sx * (R_SECOND + 0.005)
            coil = []
            turns, n = 9, 9 * 10
            ax = (c1 - c0)
            u = side * sx
            v = ax.normalized().cross(u).normalized()
            for k in range(n + 1):
                t = k / n
                ang = 2 * math.pi * turns * t
                coil.append(c0 + ax * t + (u * math.cos(ang) + v * math.sin(ang)) * 0.0045)
            obs.append(sweep("spring", coil, circle(0.0011, 6), step=0.0015, cap=True))
            # hooks onto lugs
            for c in (c0, c1):
                obs.append(cyl("lug", 0.0028, c - side * sx * 0.006, c + side * sx * 0.002, 8))
    return obs


# ------------------------------------------------------------------ textures (procedural, no text)
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


def brushed(H, W, seed, along="u", amp=0.04, scale=1.0):
    rng = np.random.default_rng(seed)
    if along == "u":
        lines = rng.normal(0, 1, H).astype(np.float32)
        lines = np.convolve(lines, [0.25, 0.5, 0.25], "same")
        n = np.repeat(lines[:, None], W, 1)
    else:
        lines = rng.normal(0, 1, W).astype(np.float32)
        n = np.repeat(lines[None, :], H, 0)
    n += 0.4 * rng.normal(0, 1, (H, W)).astype(np.float32)
    return 1 + amp * n


def header_texture(path):
    """u (x) = along the pipe from the port; heat colours near the head fading to brushed steel."""
    W, H = 1024, 64
    u = np.linspace(0, 1, W)[None, :]
    steel = np.array([0.42, 0.42, 0.43])
    # heat tint bands (linear albedo), port end first
    stops = [(0.00, (0.30, 0.20, 0.10)), (0.06, (0.35, 0.24, 0.10)), (0.13, (0.28, 0.14, 0.18)),
             (0.20, (0.12, 0.13, 0.30)), (0.28, (0.17, 0.22, 0.34)), (0.38, (0.36, 0.32, 0.20)),
             (0.50, (0.40, 0.38, 0.32)), (0.62, tuple(steel)), (1.0, tuple(steel))]
    xs = [s for s, _ in stops]
    col = np.stack([np.interp(u[0], xs, [c[i] for _, c in stops]) for i in range(3)], -1)
    rgb = np.repeat(col[None, :, :], H, 0)
    # irregular edges between colours: noise warps u a little
    rgb *= brushed(H, W, 3, "v", 0.035)[..., None]
    save_png(path, rgb)


def steel_texture(path, tint=(0.40, 0.40, 0.41), seed=5, straw=0.0):
    W, H = 512, 64
    u = np.linspace(0, 1, W)[None, :, None]
    base = np.array(tint)[None, None, :]
    rgb = np.repeat(base, H, 0).repeat(W, 1)
    if straw:
        rgb = rgb * (1 - straw * np.exp(-u * 6)) + np.array([0.36, 0.30, 0.18]) * straw * np.exp(-u * 6)
    rgb *= brushed(H, W, seed, "v", 0.04)[..., None]
    save_png(path, rgb)


def titanium_texture(path):
    W, H = 512, 256
    rgb = np.ones((H, W, 3), np.float32) * np.array([0.30, 0.30, 0.31])
    rgb *= brushed(H, W, 9, "v", 0.05)[..., None]
    # faint straw/blue heat tint near the inlet (u small)
    u = np.linspace(0, 1, W)[None, :, None]
    rgb = rgb * (1 - 0.35 * np.exp(-u * 9)) + np.array([0.30, 0.24, 0.30]) * 0.35 * np.exp(-u * 9)
    save_png(path, rgb)


def carbon_texture(path, S=256):
    """2x2 twill carbon weave, tiles seamlessly (UVs repeat every 3 cm)."""
    n = 8                      # tows across the tile
    y, x = np.mgrid[0:S, 0:S] / S * n
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    over = ((xi + yi) // 2) % 2 == 0          # twill: diagonal steps of 2
    fx, fy = x - xi, y - yi
    # each tow: bright along its length (anisotropic sheen), dark at the edges
    tow_h = np.sin(np.pi * fy) ** 0.6
    tow_v = np.sin(np.pi * fx) ** 0.6
    sheen_h = 0.55 + 0.45 * np.cos(np.pi * (fx - 0.5)) ** 2
    sheen_v = 0.55 + 0.45 * np.cos(np.pi * (fy - 0.5)) ** 2
    lum = np.where(over, tow_h * sheen_h * 1.0, tow_v * sheen_v * 0.65)
    lum = 0.012 + 0.05 * lum
    rgb = np.stack([lum, lum, lum * 1.06], -1)
    save_png(path, rgb)


def black_texture_free():
    return None


# ------------------------------------------------------------------ looks
LOOKS = {
    "Headers": {"tex": "Headers", "rough": 0.3, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.1}},
    "Collector": {"tex": "Collector", "rough": 0.3, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.1}},
    "PreSilencer": {"tex": "Steel", "rough": 0.35, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.08}},
    "LinkPipe": {"tex": "Steel", "rough": 0.3, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.1}},
    "Silencer": {"tex": "Titanium", "rough": 0.28, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.12}},
    "HeatShield": {"tex": "Carbon", "rough": 0.15, "metal": 0.0, "coat": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.05}},
    "EndCap": {"color": (0.018, 0.018, 0.02), "rough": 0.5, "metal": 0.3, "roblox": {"Color": [30, 30, 33], "Material": "SmoothPlastic"}},
    "Hardware": {"color": (0.55, 0.56, 0.58), "rough": 0.3, "metal": 1.0, "roblox": {"Color": [165, 168, 174], "Material": "SmoothPlastic", "Reflectance": 0.15}},
    "Valve": {"color": (0.03, 0.03, 0.033), "rough": 0.45, "metal": 0.5, "roblox": {"Color": [38, 38, 42], "Material": "SmoothPlastic"}},
    "Sensors": {"color": (0.30, 0.30, 0.31), "rough": 0.4, "metal": 1.0, "roblox": {"Color": [110, 110, 116], "Material": "SmoothPlastic"}},
}
TEXFILES = {"Headers": "Headers_Color.png", "Collector": "Collector_Color.png", "Steel": "Steel_Color.png",
            "Titanium": "Titanium_Color.png", "Carbon": "Carbon_Color.png"}


def material(key):
    L = LOOKS[key]
    m = bpy.data.materials.new("M_" + key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = L["rough"]
    b.inputs["Metallic"].default_value = L["metal"]
    if L.get("coat"):
        b.inputs["Coat Weight"].default_value = 1.0
        b.inputs["Coat Roughness"].default_value = 0.03
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
    header_texture(os.path.join(TEX, TEXFILES["Headers"]))
    steel_texture(os.path.join(TEX, TEXFILES["Collector"]), (0.40, 0.40, 0.41), 6, straw=0.5)
    steel_texture(os.path.join(TEX, TEXFILES["Steel"]), (0.38, 0.38, 0.39), 7)
    titanium_texture(os.path.join(TEX, TEXFILES["Titanium"]))
    carbon_texture(os.path.join(TEX, TEXFILES["Carbon"]))

    parts = {}
    parts["Headers"] = G.join(headers(), "Headers")
    secs, ends = secondaries()
    parts["Collector"] = G.join(secs, "Collector")
    parts["PreSilencer"] = G.join(presilencer(), "PreSilencer")
    link, valve = link_and_valve()
    body, cone, shield, endcap, tips, band, rivets, hang = silencer()
    parts["LinkPipe"] = G.join([link, cone], "LinkPipe")
    parts["Silencer"] = body
    parts["HeatShield"] = shield
    dark = [t for t in tips if t.name.startswith("outletdark")]
    bright = [t for t in tips if not t.name.startswith("outletdark")]
    parts["EndCap"] = G.join([endcap] + dark, "EndCap")
    parts["Hardware"] = G.join(flanges() + spring_clamps(ends) + [band] + rivets + hang + bright, "Hardware")
    parts["Valve"] = G.join(valve, "Valve")
    parts["Sensors"] = G.join(sensors(ends), "Sensors")
    for name, ob in parts.items():
        ob.name = ob.data.name = name
        G.smooth(ob, 40)
        ob.data.materials.clear()
        ob.data.materials.append(material(name))
    return parts


def check_clearance():
    """Pipe centre lines must stay apart (no pipe running through another)."""
    paths = {k: resample(catmull(v, 12), 0.005)[0] for k, v in HEADERS.items()}
    worst = 9.0
    for a in paths:
        for b in paths:
            if a >= b:
                continue
            for i, p in enumerate(paths[a]):
                if i > len(paths[a]) - 12:      # the merge ends are meant to touch
                    continue
                for j, q in enumerate(paths[b][:-12]):
                    worst = min(worst, (p - q).length)
    print("closest header centre lines", round(worst, 4), "need >", 2 * R_HEADER)
    assert worst > 2 * R_HEADER + 0.003, worst


def export(parts):
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: +X = bike's LEFT, -Y = front, +Z = up; origin = ground between the axles (bike layout).",
            "parts": {}, "looks": {}}
    texmap = {}
    for name, ob in parts.items():
        meta["parts"][name] = {"tris": G.tris(ob)}
        meta["looks"][name] = LOOKS[name]["roblox"]
        if LOOKS[name].get("tex"):
            texmap[name] = f"art/models/BikeExhaust/tex/{TEXFILES[LOOKS[name]['tex']]}"
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
    path = os.path.join(OUT, "BikeExhaust.glb")
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
    print("BikeExhaust tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})
    for k, v in meta["parts"].items():
        assert v["tris"] < 20000, (k, v)


if __name__ == "__main__":
    check_clearance()
    os.makedirs(OUT, exist_ok=True)
    parts = build()
    export(parts)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
