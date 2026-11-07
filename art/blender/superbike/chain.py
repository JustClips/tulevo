"""Superbike drive chain (525 X-ring, 116 links) and the 17T front sprocket, as its own part.

  /home/user/bvenv/bin/python art/blender/superbike/chain.py

Built link by link in bike coordinates (same layout as wheels.py / exhaust.py):
+X = bike's LEFT, -Y = front, +Z = up, origin = ground between the axles. The chain runs on the
left in the rear sprocket's plane (x = 0.085), wraps the 45T rear sprocket on the rear hub and a
17T front sprocket on the gearbox output shaft. The shaft position is solved so that exactly
116 links close the loop with a little sag on the bottom run, and every roller on the rear
sprocket sits in a tooth gap of the wheels.py sprocket.

Each link: inner (roller) links = 2 inner plates + rollers, outer (pin) links = 2 waisted outer
plates with chamfered edges + riveted pin heads, X-ring seals between the plates.
Outputs art/models/BikeChain/{BikeChain.glb, meta.json, textures.json, tex/, work.blend}.
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
OUT = os.path.join(ROOT, "art", "models", "BikeChain")
TEX = os.path.join(OUT, "tex")
STUDS = 3.6

# ------------------------------------------------------------------ 525 chain + layout
PITCH = 0.015875          # 5/8"
ROLLER_R = 0.00508        # 10.16 mm rollers
XC = 0.085                # chain centre plane = rear sprocket plane (wheels.py)
LINKS = 116
REAR = np.array([0.7205, 0.3204])    # rear hub (y, z)
T_REAR, T_FRONT = 45, 17
FRONT_Z = 0.375           # output shaft height; its y is solved
SAG = 0.012               # bottom run sag at mid span
START_ANGLE = math.radians(80)       # roller 0 sits in the rear sprocket gap at 80 deg (10 teeth up)

# across the chain, distance from the centre plane
ROLLER_HALF = 0.00393     # rollers fill the 7.94 mm inner width
INNER = (0.00397, 0.00597)            # inner plates 2.0 mm
OUTER = (0.00727, 0.00927)            # outer plates 2.0 mm, 1.3 mm gap for the X-rings
CHAMFER = 0.0003
IN_RE, IN_RW = 0.0073, 0.0062         # inner plate end radius / waist half height
OUT_RE, OUT_RW = 0.0071, 0.0057       # outer plate (more waisted)
MARGIN = 0.0004                       # texture tile margin around a plate

Q = 1.0   # mesh detail; a lighter chain for the rideable bike can use a lower value


def q(n, lo=6):
    return max(lo, int(round(n * Q)))


def pitch_radius(t):
    return PITCH / (2 * math.sin(math.pi / t))


R_REAR, R_FRONT = pitch_radius(T_REAR), pitch_radius(T_FRONT)


# ------------------------------------------------------------------ chain path (y, z plane)
def tangent_angles(F):
    D = REAR - F
    d = float(np.hypot(*D))
    phi = math.atan2(D[1], D[0])
    beta = math.acos((R_FRONT - R_REAR) / d)
    return phi + beta, phi - beta          # normals of the top and bottom runs


def pitch_path(yf, sag=SAG, step=0.0002):
    """Closed pitch line, clockwise seen from the left: rear arc from roller 0 down and round,
    sagging bottom run forward, front arc, straight top run back to roller 0."""
    F = np.array([yf, FRONT_Z])
    a_top, a_bot = tangent_angles(F)
    assert a_top > START_ANGLE
    nt = np.array([math.cos(a_top), math.sin(a_top)])
    nb = np.array([math.cos(a_bot), math.sin(a_bot)])
    pts = []

    def arc(c, r, a0, a1):
        n = max(2, int(abs(a1 - a0) * r / step))
        for i in range(n):
            a = a0 + (a1 - a0) * i / n
            pts.append(c + r * np.array([math.cos(a), math.sin(a)]))

    def line(p0, p1, bulge=0.0, normal=None):
        n = max(2, int(np.hypot(*(p1 - p0)) / step))
        for i in range(n):
            t = i / n
            p = p0 + (p1 - p0) * t
            if bulge:
                p = p + normal * bulge * math.sin(math.pi * t)
            pts.append(p)

    arc(REAR, R_REAR, START_ANGLE, a_bot)
    line(REAR + R_REAR * nb, F + R_FRONT * nb, sag, nb)
    arc(F, R_FRONT, a_bot, a_top - 2 * math.pi)
    line(F + R_FRONT * nt, REAR + R_REAR * nt)
    arc(REAR, R_REAR, a_top, START_ANGLE)
    return np.array(pts), F


def walk(pts, n, p):
    """Rollers along the closed polyline, each exactly one pitch (straight line) from the last."""
    M = len(pts)
    seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    L = cum[-1]
    c, j, s = pts[0], 0, 0.0
    out = [c]
    for _ in range(n):
        while np.hypot(*(pts[(j + 1) % M] - c)) < p:
            j += 1
        a, b = pts[j % M], pts[(j + 1) % M]
        ab, ac = b - a, a - c
        A, B, C = ab @ ab, 2 * ab @ ac, ac @ ac - p * p
        t = (-B + math.sqrt(max(0.0, B * B - 4 * A * C))) / (2 * A)
        c = a + t * ab
        s = cum[j % M] + (j // M) * L + t * seg[j % M]
        out.append(c)
    return np.array(out), s - L


def solve_layout():
    lo, hi = -0.05, 0.20       # output shaft y range
    for _ in range(60):
        mid = (lo + hi) / 2
        pts, F = pitch_path(mid)
        _, res = walk(pts, LINKS, PITCH)
        # res > 0: the chain is longer than the loop -> move the shaft forward
        if res > 0:
            hi = mid
        else:
            lo = mid
    pts, F = pitch_path((lo + hi) / 2)
    V, res = walk(pts, LINKS, PITCH)
    close = abs(np.hypot(*(V[-1] - V[0])))
    V = V[:-1]
    on_front = [i for i, v in enumerate(V) if abs(np.hypot(*(v - F)) - R_FRONT) < 2e-5]
    on_rear = [i for i, v in enumerate(V) if abs(np.hypot(*(v - REAR)) - R_REAR) < 2e-5]
    i0 = on_front[len(on_front) // 2]
    phase = math.atan2(V[i0][1] - F[1], V[i0][0] - F[0])
    print(f"chain: {LINKS} links, output shaft at y={F[0]:.4f} z={F[1]:.4f}, "
          f"closing error {close * 1000:.4f} mm, {len(on_rear)} rollers on the rear sprocket, {len(on_front)} on the front")
    assert close < 1e-4
    return V, F, phase


# ------------------------------------------------------------------ mesh builder
class MB:
    """Collects many small closed pieces into one mesh. Each face is turned to point away
    from the piece's inside point, so normals are right without a global recalc."""

    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def add(self, verts, faces, uvs, inside):
        o = len(self.v)
        ins = np.array(inside)
        V = np.array(verts)
        for f, fu in zip(faces, uvs):
            P = V[list(f)]
            Q2 = np.roll(P, -1, 0)
            n = np.array([np.sum((P[:, 1] - Q2[:, 1]) * (P[:, 2] + Q2[:, 2])),
                          np.sum((P[:, 2] - Q2[:, 2]) * (P[:, 0] + Q2[:, 0])),
                          np.sum((P[:, 0] - Q2[:, 0]) * (P[:, 1] + Q2[:, 1]))])
            if n @ (P.mean(0) - ins) < 0:
                f, fu = f[::-1], fu[::-1]
            self.f.append(tuple(i + o for i in f))
            self.uv.append(list(fu))
        self.v.extend(map(tuple, verts))

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


def revolve(mb, prof, x_sign, yz, seg, a0=0.0):
    """Ring of (x, r) profile rows around an X-parallel axis at yz; x is from the centre plane
    (mirrored by x_sign). A last row with r = 0 closes with a fan."""
    verts, faces = [], []
    rows = []
    for x, r in prof:
        if r == 0:
            rows.append([len(verts)])
            verts.append((XC + x_sign * x, yz[0], yz[1]))
            continue
        row = []
        for i in range(seg):
            a = a0 + 2 * math.pi * i / seg
            row.append(len(verts))
            verts.append((XC + x_sign * x, yz[0] + r * math.cos(a), yz[1] + r * math.sin(a)))
        rows.append(row)
    for ra, rb in zip(rows, rows[1:]):
        for i in range(seg):
            i2 = (i + 1) % seg
            if len(rb) == 1:
                faces.append((ra[i], ra[i2], rb[0]))
            else:
                faces.append((ra[i], ra[i2], rb[i2], rb[i]))
    return verts, faces


# ------------------------------------------------------------------ plates
def half_height(u, pp, re, rw):
    return rw + (re - rw) * (1 + np.cos(2 * np.pi * u / pp)) / 2


def outline(pp, re, rw, ke, km):
    """Waisted figure-8 plate outline in link space (u along the link, w across), CCW.
    Pin centres at u = 0 and u = pp."""
    pts = []
    for i in range(ke + 1):
        a = math.pi / 2 + math.pi * i / ke
        pts.append((re * math.cos(a), re * math.sin(a)))
    for i in range(1, km + 1):
        u = pp * i / (km + 1)
        pts.append((u, -half_height(u, pp, re, rw)))
    for i in range(ke + 1):
        a = -math.pi / 2 + math.pi * i / ke
        pts.append((pp + re * math.cos(a), re * math.sin(a)))
    for i in range(1, km + 1):
        u = pp * (1 - i / (km + 1))
        pts.append((u, half_height(u, pp, re, rw)))
    return np.array(pts)


def tile_uv(P, re, tile, flip):
    """Plate space -> one 512x256 tile of the 2x2 plate atlas (same mapping as plate_texture)."""
    u0, u1 = -re - MARGIN, PITCH + re + MARGIN
    w0, w1 = -re - MARGIN, re + MARGIN
    ut = (P[:, 0] - u0) / (u1 - u0)
    vt = (P[:, 1] - w0) / (w1 - w0)
    if flip:
        ut = 1 - ut
    tx, ty = tile % 2, tile // 2
    return np.stack([(tx + ut) / 2, (ty + vt) / 2], 1)


def plate(mb, V0, V1, side, xs, re, rw, ke, km, chamfer, tile, flip):
    pp = float(np.hypot(*(V1 - V0)))
    d = (V1 - V0) / pp
    nrm = np.array([-d[1], d[0]])
    P = outline(pp, re, rw, ke, km)
    n = len(P)
    x0, x1 = XC + side * xs[0], XC + side * xs[1]
    if x0 > x1:
        x0, x1 = x1, x0
    if chamfer:
        T = np.roll(P, -1, 0) - np.roll(P, 1, 0)
        No = np.stack([T[:, 1], -T[:, 0]], 1)
        No /= np.linalg.norm(No, axis=1)[:, None]
        Pin = P - chamfer * No
        rings = [(Pin, x0), (P, x0 + chamfer), (P, x1 - chamfer), (Pin, x1)]
    else:
        rings = [(P, x0), (P, x1)]
    verts, uvv = [], []
    for R2, x in rings:
        Y = V0[0] + R2[:, 0] * d[0] + R2[:, 1] * nrm[0]
        Z = V0[1] + R2[:, 0] * d[1] + R2[:, 1] * nrm[1]
        verts += [(x, y, z) for y, z in zip(Y, Z)]
        uvv += [tuple(t) for t in tile_uv(R2, re, tile, flip)]
    faces = []
    for r in range(len(rings) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            faces.append((r * n + j, r * n + j2, (r + 1) * n + j2, (r + 1) * n + j))
    faces.append(tuple(range(n)))
    faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    uvs = [[uvv[i] for i in f] for f in faces]
    mid = V0 + d * pp / 2
    mb.add(verts, faces, uvs, ((x0 + x1) / 2, mid[0], mid[1]))


# ------------------------------------------------------------------ chain parts
def build_chain(V):
    rng = np.random.default_rng(525)
    N = len(V)
    outerL, outerR, inner, rollers, pins, seals = MB(), MB(), MB(), MB(), MB(), MB()
    ke_o, km_o = q(7, 4), q(6, 3)
    ke_i, km_i = q(6, 4), q(5, 3)
    for i in range(N):
        A, B = V[i], V[(i + 1) % N]
        if i % 2 == 0:      # roller link
            for side in (1, -1):
                plate(inner, A, B, side, INNER, IN_RE, IN_RW, ke_i, km_i, 0.0, int(rng.integers(4)), bool(rng.integers(2)))
        else:               # pin link
            for side, mb in ((1, outerL), (-1, outerR)):
                plate(mb, A, B, side, OUTER, OUT_RE, OUT_RW, ke_o, km_o, CHAMFER, int(rng.integers(4)), bool(rng.integers(2)))
    seg_r, seg_p, seg_s = q(12), q(8), q(8)
    for v in V:
        yz = (float(v[0]), float(v[1]))
        # roller: tube with rounded ends between the inner plates
        prof = [(-ROLLER_HALF, ROLLER_R - 0.0003), (-ROLLER_HALF + 0.0004, ROLLER_R),
                (ROLLER_HALF - 0.0004, ROLLER_R), (ROLLER_HALF, ROLLER_R - 0.0003)]
        vs, fs = revolve(rollers, prof, 1, yz, seg_r)
        rollers.add(vs, fs, [[(0, 0)] * len(f) for f in fs], (XC, *yz))
        for side in (1, -1):
            # riveted pin head: starts inside the outer plate, domed with a peened dimple
            f0 = OUTER[1]
            prof = [(f0 - 0.0002, 0.00262), (f0 + 0.0004, 0.00262), (f0 + 0.0008, 0.0016), (f0 + 0.00055, 0.0)]
            vs, fs = revolve(pins, prof, side, yz, seg_p, a0=math.pi / seg_p)
            pins.add(vs, fs, [[(0, 0)] * len(f) for f in fs], (XC + side * (f0 - 0.001), *yz))
            # X-ring seal in the gap between the inner and outer plate (ends hidden in both plates)
            prof = [(INNER[1] - 0.0001, 0.0041), ((INNER[1] + OUTER[0]) / 2, 0.00468), (OUTER[0] + 0.0001, 0.0041)]
            vs, fs = revolve(seals, prof, side, yz, seg_s)
            seals.add(vs, fs, [[(0, 0)] * len(f) for f in fs], (XC + side * (INNER[1] + OUTER[0]) / 2, *yz))
    return {
        "OuterPlatesL": outerL.obj("OuterPlatesL", 35),
        "OuterPlatesR": outerR.obj("OuterPlatesR", 35),
        "InnerPlates": inner.obj("InnerPlates", 35),
        "Rollers": rollers.obj("Rollers", 50),
        "Pins": pins.obj("Pins", 60),
        "Seals": seals.obj("Seals", 60),
    }


# ------------------------------------------------------------------ front sprocket + nut
def tooth_outline(c, Rp, teeth, phase, n, tip_h=0.0058):
    rr = ROLLER_R + 0.0002
    tip = Rp + tip_h
    out = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        k = round((a - phase) / (2 * math.pi / teeth))
        d = Rp * ((a - phase) - k * 2 * math.pi / teeth)
        if abs(d) < rr:
            r = Rp - math.sqrt(rr * rr - d * d)
        else:
            r = min(tip, Rp + (abs(d) - rr) * 1.9)
            if r > tip - 0.0012:
                r = min(r, tip - 0.0012 + 0.0012 * math.cos(min(1.0, (r - (tip - 0.0012)) / 0.0012) * math.pi / 2))
        out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return out


def front_sprocket(F, phase):
    n = T_FRONT * q(16, 10)
    outer = tooth_outline(F, R_FRONT, T_FRONT, phase, n)
    inner = [(F[0] + 0.0172 * math.cos(phase + 2 * math.pi * i / n), F[1] + 0.0172 * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]
    sp = G.plate("teeth", outer, inner, XC - 0.0036, XC + 0.0036)
    G.bevel(sp, 0.0004, 1, 40)
    # stepped boss round the splined bore (wider than the teeth; the plate's bore is buried in it)
    boss = G.lathe("boss", [(XC - 0.0064, 0.0126), (XC + 0.0058, 0.0126), (XC + 0.0058, 0.0196),
                            (XC + 0.0050, 0.0206), (XC - 0.0056, 0.0206), (XC - 0.0064, 0.0198)], seg=q(48, 24), uv=False)
    boss.data.transform(Matrix.Translation((0, F[0], F[1])))
    G.smooth(boss, 40)
    sp = G.join([sp, boss], "FrontSprocket")
    G.smooth(sp, 15)   # low angle: the faces stay flat next to the small tooth chamfers
    # tab washer, chamfered nut, shaft end, inner shaft stub, washer tab bent up onto a nut flat
    af = 0.027
    rc = af / 2 / math.cos(math.pi / 6)
    washer = G.lathe("washer", [(XC + 0.0059, 0.0090), (XC + 0.0072, 0.0090), (XC + 0.0072, 0.0186), (XC + 0.0059, 0.0186)],
                     seg=q(40, 20), uv=False)
    nut = G.lathe("nut", [(XC + 0.0072, 0.0090), (XC + 0.0162, 0.0090), (XC + 0.0162, rc * 0.90), (XC + 0.0154, rc),
                          (XC + 0.0080, rc), (XC + 0.0072, rc * 0.90)], seg=6, uv=False)
    shaft = G.cylinder_x("shaft", 0.0096, XC + 0.0050, XC + 0.0168, q(24, 12))
    stub = G.cylinder_x("stub", 0.0126, XC - 0.0180, XC - 0.0060, q(32, 16))
    for o in (washer, nut):
        o.data.transform(Matrix.Translation((0, F[0], F[1])))
    for o in (shaft, stub):
        o.data.transform(Matrix.Translation((0, F[0], F[1])))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    me = bpy.data.meshes.new("tab")
    bm.to_mesh(me)
    bm.free()
    tab = G.new_obj("tab", me)
    tab.data.transform(Matrix.Translation((XC + 0.0108, F[0], F[1] + af / 2 + 0.0007)) @ Matrix.Diagonal((0.0072, 0.0085, 0.0013, 1)))
    nutpart = G.join([washer, nut, shaft, stub, tab], "SprocketNut")
    G.smooth(nutpart, 35)
    return sp, nutpart


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


def value_noise(H, W, gh, gw, rng):
    g = rng.random((gh + 1, gw + 1))
    y = np.linspace(0, gh, H)
    x = np.linspace(0, gw, W)
    y0, x0 = np.minimum(y.astype(int), gh - 1), np.minimum(x.astype(int), gw - 1)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def plate_texture(path, re, rw, base, edge, grime_col, grime, seed):
    """2x2 atlas of plate tiles (512x256 each), drawn in the same plate space as tile_uv:
    brushed steel along the link, bright chamfer edge, oily grime pooled at the edges and round
    the pins, a few fine scratches. Each tile uses its own noise so the links don't repeat."""
    TW, TH = 512, 256
    img = np.zeros((TH * 2, TW * 2, 3), np.float32)
    u = -re - MARGIN + (np.arange(TW) + 0.5) / TW * (PITCH + 2 * re + 2 * MARGIN)
    w = -re - MARGIN + (np.arange(TH) + 0.5) / TH * (2 * re + 2 * MARGIN)
    U, Wm = np.meshgrid(u, w)
    dl = re - np.hypot(U, Wm)
    dr = re - np.hypot(U - PITCH, Wm)
    dm = np.where((U >= 0) & (U <= PITCH), half_height(U, PITCH, re, rw) - np.abs(Wm), -1.0)
    depth = np.maximum(np.maximum(dl, dr), dm)            # distance inside the outline (approx)
    dpin = np.minimum(np.hypot(U, Wm), np.hypot(U - PITCH, Wm))
    for t in range(4):
        rng = np.random.default_rng(seed + t)
        col = np.ones((TH, TW, 3), np.float32) * np.array(base) * (0.94 + 0.12 * rng.random())
        # brushed grain along the link
        lines = rng.normal(0, 1, TH)
        lines = np.convolve(lines, [0.25, 0.5, 0.25], "same")
        col *= (1 + 0.05 * lines[:, None] + 0.02 * rng.normal(0, 1, (TH, TW)))[..., None]
        # polished chamfer edge
        e = np.clip(1 - depth / 0.00038, 0, 1) ** 1.5
        col = col * (1 - e[..., None]) + np.array(edge) * e[..., None]
        # grime: blotchy, heavier near the edges and in a ring round each pin (where the seal oil seeps)
        blot = value_noise(TH, TW, 5, 10, rng) * 0.7 + value_noise(TH, TW, 14, 28, rng) * 0.3
        near_edge = np.exp(-np.clip(depth, 0, None) / 0.0011)
        ring = np.exp(-((dpin - 0.0034) / 0.0007) ** 2)
        g = grime * np.clip((blot - 0.35) * 2.2, 0, 1) * (0.35 + 0.65 * near_edge) + 0.35 * grime * ring * blot
        g = np.clip(g, 0, 0.92)[..., None]
        col = col * (1 - g) + np.array(grime_col) * g
        # fine scratches mostly along the link
        for _ in range(int(rng.integers(3, 7))):
            y0 = rng.uniform(0.15, 0.85) * TH
            x0 = rng.uniform(0.1, 0.7) * TW
            ln = rng.uniform(30, 120)
            ang = rng.normal(0, 0.12)
            xs = np.arange(int(ln))
            xx = np.clip((x0 + xs * math.cos(ang)).astype(int), 0, TW - 1)
            yy = np.clip((y0 + xs * math.sin(ang)).astype(int), 0, TH - 1)
            col[yy, xx] = col[yy, xx] * 0.6 + np.array(edge) * 0.4
        ty, tx = t // 2, t % 2
        img[ty * TH:(ty + 1) * TH, tx * TW:(tx + 1) * TW] = col
    save_png(path, img)


# ------------------------------------------------------------------ looks
LOOKS = {
    "OuterPlatesL": {"tex": "Outer", "rough": 0.3, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.1}},
    "OuterPlatesR": {"tex": "Outer", "rough": 0.3, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.1}},
    "InnerPlates": {"tex": "Inner", "rough": 0.42, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.05}},
    "Rollers": {"color": (0.17, 0.17, 0.175), "rough": 0.38, "metal": 1.0, "roblox": {"Color": [92, 92, 96], "Material": "SmoothPlastic", "Reflectance": 0.06}},
    "Pins": {"color": (0.62, 0.63, 0.65), "rough": 0.22, "metal": 1.0, "roblox": {"Color": [178, 180, 186], "Material": "SmoothPlastic", "Reflectance": 0.15}},
    "Seals": {"color": (0.012, 0.012, 0.013), "rough": 0.55, "metal": 0.0, "roblox": {"Color": [24, 24, 26], "Material": "SmoothPlastic"}},
    "FrontSprocket": {"color": (0.26, 0.26, 0.27), "rough": 0.33, "metal": 1.0, "roblox": {"Color": [118, 119, 124], "Material": "SmoothPlastic", "Reflectance": 0.08}},
    "SprocketNut": {"color": (0.52, 0.53, 0.55), "rough": 0.28, "metal": 1.0, "roblox": {"Color": [160, 162, 168], "Material": "SmoothPlastic", "Reflectance": 0.12}},
}
TEXFILES = {"Outer": "OuterPlate_Color.png", "Inner": "InnerPlate_Color.png"}


def material(key):
    L = LOOKS[key]
    m = bpy.data.materials.new("M_" + key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = L["rough"]
    b.inputs["Metallic"].default_value = L["metal"]
    if L.get("tex"):
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, TEXFILES[L["tex"]]), check_existing=True)
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*L["color"], 1)
    return m


def context_sprocket():
    """The wheels.py rear sprocket on the rear hub, only for the preview renders (not exported)."""
    import wheels
    spr, _ = wheels.sprocket(XC)
    spr.data.transform(Matrix.Translation((0, REAR[0], REAR[1])))
    spr.name = "_ctx_RearSprocket"
    spr.data.materials.clear()
    m = bpy.data.materials.new("M_ctx")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.03, 0.03, 0.032, 1)
    b.inputs["Metallic"].default_value = 0.8
    b.inputs["Roughness"].default_value = 0.4
    spr.data.materials.append(m)
    return spr


# ------------------------------------------------------------------ build + export
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    plate_texture(os.path.join(TEX, TEXFILES["Outer"]), OUT_RE, OUT_RW, base=(0.40, 0.40, 0.41), edge=(0.72, 0.72, 0.73),
                  grime_col=(0.030, 0.026, 0.022), grime=0.55, seed=11)
    plate_texture(os.path.join(TEX, TEXFILES["Inner"]), IN_RE, IN_RW, base=(0.15, 0.15, 0.155), edge=(0.34, 0.34, 0.35),
                  grime_col=(0.020, 0.018, 0.016), grime=0.7, seed=31)
    V, F, phase = solve_layout()
    parts = build_chain(V)
    parts["FrontSprocket"], parts["SprocketNut"] = front_sprocket(F, phase)
    for name, ob in parts.items():
        ob.data.materials.clear()
        ob.data.materials.append(material(name))
    context_sprocket()
    return parts, V, F


def export(parts, F):
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: +X = bike's LEFT, -Y = front, +Z = up; origin = ground between the axles (bike layout).",
            "chain": {"links": LINKS, "pitch_m": PITCH, "rear_teeth": T_REAR, "front_teeth": T_FRONT,
                      "output_shaft_yz_m": [round(float(F[0]), 4), round(float(F[1]), 4)], "plane_x_m": XC},
            "parts": {}, "looks": {}}
    texmap = {}
    for name, ob in parts.items():
        meta["parts"][name] = {"tris": G.tris(ob)}
        meta["looks"][name] = LOOKS[name]["roblox"]
        if LOOKS[name].get("tex"):
            texmap[name] = f"art/models/BikeChain/tex/{TEXFILES[LOOKS[name]['tex']]}"
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
    path = os.path.join(OUT, "BikeChain.glb")
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
    print("BikeChain tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})
    for k, v in meta["parts"].items():
        assert v["tris"] < 20000, (k, v)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts, V, F = build()
    export(parts, F)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
