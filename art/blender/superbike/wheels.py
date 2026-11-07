"""Superbike front + rear wheels (1000 cc sport bike proportions, no brand marks anywhere).

  python3 art/blender/superbike/wheels.py            (needs `pip install bpy numpy`)

Front: 120/70 ZR17 tyre on a 3.50x17 cast rim, twin 320 mm floating discs, two radial
4-piston monobloc calipers. Rear: 190/55 ZR17 tyre on a 6.00x17 rim, 220 mm disc + floating
1-piston caliper with its bracket on the right, 45-tooth sprocket on the left.

Writes art/models/BikeWheelFront|BikeWheelRear/<Name>.glb (in STUDS, x3.6 baked in, so
Scale 1 in game), meta.json, textures.json + tex/*.png, preview.png.
Blender axes: wheel axle = X (+X = bike's LEFT), bike front = -Y, up = +Z, origin = hub centre.
Calipers (and the rear caliper bracket) don't spin; everything else turns around X.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo as G  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODELS = os.path.join(ROOT, "art", "models")
STUDS = 3.6
BRAKES = "--brakes" in sys.argv   # Dev wants tyres + rims only for now (2026-11-07)
R17 = 0.4318 / 2          # 17 in bead seat radius
rad = math.radians


# ------------------------------------------------------------------ profiles
def catmull(pts, n=6):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (np.array(P[i + k]) for k in (-1, 0, 1, 2))
        for s in range(n):
            t = s / n
            out.append(tuple(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(pts[-1]))
    return out


def tyre_profile(W, Ro, rim_half):
    """Open (x, r) profile from the right bead over the crown to the left bead + v marks."""
    Rt = 0.58 * W
    xe = 0.965 * W / 2
    re = Ro - (Rt - math.sqrt(Rt * Rt - xe * xe))
    side = [(rim_half - 0.0045, R17 - 0.004), (rim_half - 0.0015, R17 + 0.010), (rim_half + 0.004, R17 + 0.0188),
            (W / 2 - 0.0035, (R17 + 0.0188 + re) / 2 - 0.004), (W / 2, re - 0.012), (xe, re)]
    side = catmull(side, 3)
    a_e = math.asin(xe / Rt)
    tread = [(Rt * math.sin(a_e * (1 - i / 14)), Ro - Rt + Rt * math.cos(a_e * (1 - i / 14))) for i in range(1, 15)]
    half = side + tread                                   # bead -> crown on +x
    prof = [(-x, r) for x, r in half] [:-1] + [(x, r) for x, r in half[::-1]]
    # arc-length marks for the texture
    L = [0.0]
    for a, b in zip(prof, prof[1:]):
        L.append(L[-1] + math.dist(a, b))
    tot = L[-1]
    n_side = len(side)
    v_edge = L[n_side - 1] / tot
    return prof, {"v_edge_a": v_edge, "v_edge_b": 1 - v_edge, "len": tot}


def rim_profile(rim_half):
    """Closed (x, r) loop of the rim barrel (bead seats, flanges, drop centre), +x half mirrored."""
    h = rim_half
    outer = [(0.0, R17 - 0.0125), (h - 0.022, R17 - 0.0125), (h - 0.013, R17 - 0.001), (h - 0.0015, R17),
             (h, R17 + 0.0025), (h + 0.0005, R17 + 0.0145), (h + 0.0025, R17 + 0.0178), (h + 0.0055, R17 + 0.0178),
             (h + 0.0072, R17 + 0.0150), (h + 0.0072, R17 + 0.004), (h + 0.0055, R17 - 0.003), (h + 0.001, R17 - 0.0075),
             (h - 0.012, R17 - 0.0115), (h - 0.022, R17 - 0.0165), (0.0, R17 - 0.0165)]
    half = outer[1:-1]
    loop = [(x, r) for x, r in half] + [(-x, r) for x, r in half[::-1]]
    # loop goes outer surface +x -> around flange -> inner surface back ... make it a closed ring
    pos = half                       # +x side, from outer well to inner well
    neg = [(-x, r) for x, r in half]
    return pos + neg[::-1]


# ------------------------------------------------------------------ spokes (5 split Y-spokes)
def spoke_arm(name, pts_r_ang, widths, thicks, x=0.0, n=14):
    """Loft rounded-rect sections along a quadratic curve in the wheel plane."""
    (r0, a0), (rc, ac), (r1, a1) = pts_r_ang
    P0, Pc, P1 = G.polar(r0, a0), G.polar(rc, ac), G.polar(r1, a1)
    secs = []
    for i in range(n + 1):
        t = i / n
        p = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * Pc + t * t * P1
        d = 2 * (1 - t) * (Pc - P0) + 2 * t * (P1 - Pc)
        d.normalize()
        perp = Vector((0, -d.z, d.y))
        w = np.interp(t, np.linspace(0, 1, len(widths)), widths)
        th = np.interp(t, np.linspace(0, 1, len(thicks)), thicks)
        sec = [p + perp * a + Vector((x + b, 0, 0)) for a, b in G.rounded_rect(w, th, 3, 0.45)]
        secs.append(sec)
    return G.loft(name, secs)


def y_spokes(rim_half, t_hub, t_rim, r_hub, r_end, spread=11.5):
    obs = []
    for k in range(5):
        phi = rad(90 + 72 * k)
        obs.append(spoke_arm(f"stem{k}", [(r_hub - 0.012, phi), (r_hub + 0.04, phi), (0.122, phi)],
                             [0.040, 0.030, 0.027], [t_hub, t_hub * 0.8, t_hub * 0.66]))
        for s in (-1, 1):
            obs.append(spoke_arm(f"arm{k}{s}", [(0.104, phi + s * rad(1.5)), (0.160, phi + s * rad(spread * 0.55)), (r_end, phi + s * rad(spread))],
                                 [0.022, 0.017, 0.018, 0.026], [t_hub * 0.62, t_rim * 0.85, t_rim, t_rim * 1.2]))
    return obs


# ------------------------------------------------------------------ brakes
def rotor_ring(name, xc, r_in, r_out, thick, holes, seg=192):
    t = thick / 2
    ob = G.lathe(name, [(xc - t, r_in), (xc + t, r_in), (xc + t, r_out), (xc - t, r_out)], seg=seg, uv=False)
    cut = [G.cylinder_x("h", hr, xc - 0.01, xc + 0.01, 12, *G.polar(hrr, ha).yz) for hrr, ha, hr in holes]
    G.boolean(ob, cut)
    return ob


def planar_uv(ob, half):
    me = ob.data
    lay = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        for li, vi in zip(p.loop_indices, p.vertices):
            v = me.vertices[vi].co
            lay.data[li].uv = (0.5 + v.y / (2 * half), 0.5 + v.z / (2 * half))


def front_disc(side):
    xc = side * 0.068
    holes = []
    for g in range(24):
        a = rad(g * 15)
        for j, rr in enumerate((0.127, 0.1385, 0.150)):
            holes.append((rr, a + rad(3.2 * j), 0.0031))
    n_btn = 10
    btn_r = 0.1182
    for b in range(n_btn):
        holes.append((btn_r, rad(b * 36 + 7.5), 0.0058))
    rotor = rotor_ring(f"Rotor{'L' if side > 0 else 'R'}", xc, 0.1155, 0.160, 0.005, holes)
    planar_uv(rotor, 0.165)
    # carrier: 10-arm spider out to the floating buttons
    n = 600
    outer, inner = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        f = ((1 + math.cos(10 * (a - rad(7.5)))) / 2) ** 2.2
        r = 0.079 + (0.1235 - 0.079) * f
        outer.append((r * math.cos(a), r * math.sin(a)))
        inner.append((0.034 * math.cos(a), 0.034 * math.sin(a)))
    car = G.plate("carrier", outer, inner, xc - 0.002, xc + 0.002)
    G.boolean(car, [G.cylinder_x("h", 0.0058, xc - 0.01, xc + 0.01, 16, *G.polar(btn_r, rad(b * 36 + 7.5)).yz) for b in range(n_btn)]
              + [G.cylinder_x("h", 0.0085, xc - 0.01, xc + 0.01, 16, *G.polar(0.094, rad(b * 36 + 25.5)).yz) for b in range(n_btn)])
    G.bevel(car, 0.0006, 2, 40)
    parts = [car]
    for b in range(n_btn):
        bt = G.lathe("btn", [(xc - 0.0045, 0.0), (xc - 0.0045, 0.0072), (xc - 0.0030, 0.0072), (xc - 0.0030, 0.0058),
                             (xc + 0.0030, 0.0058), (xc + 0.0030, 0.0072), (xc + 0.0045, 0.0072), (xc + 0.0045, 0.0)], seg=16, uv=False)
        bt.location = G.polar(btn_r, rad(b * 36 + 7.5))
        G.apply(bt)
        parts.append(bt)
    for b in range(6):   # carrier bolts on the outboard face
        hd = G.cylinder_x("bolt", 0.0042, xc + side * 0.0015, xc + side * 0.0055, 6, *G.polar(0.042, rad(b * 60)).yz)
        parts.append(hd)
    carrier = G.join(parts, f"Carrier{'L' if side > 0 else 'R'}")
    return rotor, carrier


def caliper(name, xc, side, ang, r_in, r_out, span, half_w, pistons, lugs):
    """U-section caliper body straddling the disc edge at wheel-plane angle `ang`.
    side = +1 when outboard is +X. pistons/lugs = lists of (r, d_ang, radius)."""
    s = side
    slot = 0.0062
    top = r_out
    prof = [(slot, r_in + 0.002), (half_w - 0.003, r_in), (half_w, r_in + 0.004), (half_w, top - 0.009), (half_w - 0.006, top),
            (-half_w + 0.006, top), (-half_w, top - 0.009), (-half_w, r_in + 0.004), (-half_w + 0.003, r_in), (-slot, r_in + 0.002),
            (-slot, top - 0.013), (slot, top - 0.013)]
    prof = [(xc + s * dx, r) for dx, r in prof]
    body = G.lathe(name, prof, seg=20, closed=True, a0=ang - span, a1=ang + span, uv=False, caps=True)
    G.bevel(body, 0.0018, 2, 40)
    parts = [body]
    for r, da, pr in pistons:          # piston bulges on both halves
        for sgn in (1, -1):
            x0 = xc + s * sgn * (half_w - 0.004)
            x1 = xc + s * sgn * (half_w + 0.0035)
            c = G.cylinder_x("pist", pr, min(x0, x1), max(x0, x1), 28, *G.polar(r, ang + da).yz)
            G.bevel(c, 0.0015, 2, 40)
            parts.append(c)
    for r, da, lr in lugs:             # radial mount lugs on the outboard half
        lug = G.cylinder_x("lug", lr, 0, 0.022, 20)
        lug.rotation_euler = (ang + da, 0, 0)  # X-cylinder; turn it to point radially
        lug.data.transform(__import__("mathutils").Matrix.Rotation(rad(-90), 4, 'Y'))
        lug.rotation_euler = (0, 0, 0)
        G.apply(lug)
        # lug now along +Z (radial at angle 90); rotate to the caliper angle
        lug.rotation_euler = (ang + da - rad(90), 0, 0)
        lug.location = (xc + s * (half_w - 0.006), 0, 0)
        G.apply(lug)
        lug.data.transform(__import__("mathutils").Matrix.Translation(G.polar(r, ang + da)))
        parts.append(lug)
    return parts


def front_caliper(side):
    xc = side * 0.068
    ang = rad(18)
    parts = caliper(f"Caliper{'L' if side > 0 else 'R'}", xc, side, ang, 0.112, 0.181, rad(23), 0.031,
                    pistons=[(0.1395, rad(-10.5), 0.0125), (0.1395, rad(10.5), 0.0135)],
                    lugs=[(0.176, rad(-19.5), 0.0085), (0.176, rad(19.5), 0.0085)])
    return G.join(parts, f"Caliper{'L' if side > 0 else 'R'}")


# ------------------------------------------------------------------ wheels
def build_rim(name, rim_half, hub_prof, t_hub, t_rim):
    barrel = G.lathe("barrel", rim_profile(rim_half), seg=160, uv=False)
    hub = G.lathe("hub", hub_prof, seg=64, uv=False)
    spokes = y_spokes(rim_half, t_hub, t_rim, 0.040, R17 - 0.0135)
    return G.join([barrel, hub] + spokes, name)


def valve(ang=rad(126), tilt=rad(-14)):
    """Tyre valve stem through the drop centre, between two spokes, cap pointing at the hub.
    Tilted a little toward the bike's right (-X) so it can be seen from the side."""
    prof = [(0.157, 0.0), (0.157, 0.0046), (0.1585, 0.0053), (0.1715, 0.0053), (0.1715, 0.0036), (0.1855, 0.0036),
            (0.1855, 0.0064), (0.1895, 0.0064), (0.1895, 0.0046), (R17 - 0.010, 0.0046), (R17 - 0.010, 0.0)]
    ob = G.lathe("Valve", prof, seg=20, uv=False)
    from mathutils import Matrix
    base_r = R17 - 0.0135                     # inside the drop-centre wall
    radial = G.polar(1.0, ang)
    d = (radial * math.cos(tilt) - Vector((math.sin(tilt), 0, 0))).normalized()   # cap leans to -X
    q = d.to_track_quat('X', 'Z')
    ob.data.transform(Matrix.Translation(G.polar(base_r, ang)) @ q.to_matrix().to_4x4() @ Matrix.Translation((-base_r, 0, 0)))
    return ob


def build_tyre(name, W, Ro, rim_half):
    prof, marks = tyre_profile(W, Ro, rim_half)
    ob = G.lathe(name, prof, seg=168, closed=False)
    G.flip_if_inward(ob)
    marks["circ"] = 2 * math.pi * Ro
    return ob, marks


def front_wheel():
    rim_half = 0.0889 / 2 - 0.0005
    hub = [(-0.0675, 0.0125), (0.0675, 0.0125), (0.0675, 0.047), (0.0655, 0.050), (0.057, 0.050), (0.050, 0.041),
           (-0.050, 0.041), (-0.057, 0.050), (-0.0655, 0.050), (-0.0675, 0.047)]
    rim = build_rim("Rim", rim_half, hub, 0.042, 0.022)
    tyre, marks = build_tyre("Tyre", 0.120, 0.2999, rim_half)
    obs = [tyre, rim, valve()]
    if BRAKES:
        for side in (1, -1):
            rotor, carrier = front_disc(side)
            obs += [rotor, carrier, front_caliper(side)]
    return obs, marks


def sprocket(xc, teeth=45, pitch=0.015875, roller=0.01016):
    Rp = pitch / (2 * math.sin(math.pi / teeth))
    rr = roller / 2 + 0.0002
    tip = Rp + 0.0062
    n = teeth * 24
    outer, inner = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = round(a / (2 * math.pi / teeth))
        d = Rp * (a - k * 2 * math.pi / teeth)
        if abs(d) < rr:
            r = Rp - math.sqrt(rr * rr - d * d)
        else:
            r = min(tip, Rp + (abs(d) - rr) * 1.9)
            r = min(r, tip - 0.0012 + 0.0012 * math.cos(min(1.0, (r - (tip - 0.0012)) / 0.0012) * math.pi / 2)) if r > tip - 0.0012 else r
        outer.append((r * math.cos(a), r * math.sin(a)))
        inner.append((0.0575 * math.cos(a), 0.0575 * math.sin(a)))
    sp = G.plate("sprocket", outer, inner, xc - 0.003, xc + 0.003)
    G.boolean(sp, [G.cylinder_x("h", 0.0135, xc - 0.01, xc + 0.01, 28, *G.polar(0.0815, rad(36 + 72 * k)).yz) for k in range(5)])
    G.bevel(sp, 0.0005, 1, 40)
    parts = [sp]
    for k in range(5):   # sprocket nuts
        parts.append(G.cylinder_x("nut", 0.0062, xc + 0.003, xc + 0.0085, 6, *G.polar(0.0645, rad(72 * k)).yz))
    return G.join(parts, "Sprocket"), Rp


def rear_disc(xc):
    holes = [(rr, rad(g * 20 + 4.5 * j), 0.0028) for g in range(18) for j, rr in enumerate((0.090, 0.1005))]
    ring = rotor_ring("ringR", xc, 0.0825, 0.110, 0.005, holes, seg=160)
    n = 480
    outer, inner = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        f = ((1 + math.cos(6 * a)) / 2) ** 1.6
        r = 0.060 + (0.0865 - 0.060) * f
        outer.append((r * math.cos(a), r * math.sin(a)))
        inner.append((0.034 * math.cos(a), 0.034 * math.sin(a)))
    sp = G.plate("spider", outer, inner, xc - 0.002, xc + 0.002)
    G.boolean(sp, [G.cylinder_x("h", 0.0045, xc - 0.01, xc + 0.01, 12, *G.polar(0.041, rad(30 + 60 * k)).yz) for k in range(6)])
    rotor = G.join([ring, sp], "Rotor")
    planar_uv(rotor, 0.165)
    return rotor


def rear_caliper(xc, side):
    ang = rad(180 + 38)
    parts = caliper("Caliper", xc, side, ang, 0.078, 0.123, rad(21), 0.024,
                    pistons=[(0.096, 0.0, 0.0165)], lugs=[])
    # bracket (torque plate) from the axle to the caliper, outboard of it
    end = G.polar(0.100, ang)
    ey, ez = end.y, end.z
    n = 240
    outer, inner = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        d = np.array([math.cos(a), math.sin(a)])
        r = 0.0
        for _ in range(300):        # march to the capsule edge (axle r 0.030 -> caliper end r 0.026)
            p = d * (r + 0.0005)
            t = max(0.0, min(1.0, float(np.dot(p, (ey, ez)) / (ey * ey + ez * ez))))
            q = np.array((ey, ez)) * t
            if np.linalg.norm(p - q) > 0.030 - 0.004 * t:
                break
            r += 0.0005
        outer.append((d[0] * r, d[1] * r))
        inner.append((0.0135 * d[0], 0.0135 * d[1]))
    hw = 0.024
    x0, x1 = xc + side * (hw - 0.002), xc + side * (hw + 0.004)
    br = G.plate("bracket", outer, inner, min(x0, x1), max(x0, x1))
    G.bevel(br, 0.001, 2, 40)
    parts.append(br)
    return G.join(parts, "Caliper")


def rear_wheel():
    rim_half = 0.1524 / 2 - 0.0005
    hub = [(-0.0705, 0.0135), (0.060, 0.0135), (0.060, 0.050), (0.054, 0.056), (0.050, 0.047), (-0.050, 0.047),
           (-0.057, 0.052), (-0.0685, 0.052), (-0.0705, 0.049)]
    rim = build_rim("Rim", rim_half, hub, 0.052, 0.026)
    if not BRAKES:
        tyre, marks = build_tyre("Tyre", 0.190, 0.3204, rim_half)
        return [tyre, rim, valve()], marks
    # cush-drive carrier on the left (+X), part of the rim colour
    cush = G.lathe("cush", [(0.055, 0.0135), (0.0835, 0.0135), (0.0835, 0.052), (0.0805, 0.0575), (0.074, 0.060),
                            (0.066, 0.060), (0.058, 0.054), (0.055, 0.050)], seg=72, uv=False)
    rim = G.join([rim, cush], "Rim")
    tyre, marks = build_tyre("Tyre", 0.190, 0.3204, rim_half)
    xd = -0.072
    rotor = rear_disc(xd)
    cal = rear_caliper(xd, -1)
    spr, Rp = sprocket(0.085)
    return [tyre, rim, valve(), rotor, cal, spr], marks


# ------------------------------------------------------------------ textures (procedural, no text anywhere)
def tyre_texture(path, marks, W=2048, H=512, seed=1):
    rng = np.random.default_rng(seed)
    circ, plen = marks["circ"], marks["len"]
    va, vb = marks["v_edge_a"], marks["v_edge_b"]
    v = (np.arange(H) + 0.5) / H
    img = np.zeros((H, W), np.float32)
    tread = (v > va) & (v < vb)
    base = np.where(tread, 0.032, 0.020).astype(np.float32)
    img[:] = base[:, None]
    # fine scuffing on the tread, faint sidewall ribs near the rim
    noise = rng.normal(0, 1, (H // 4, W // 4)).astype(np.float32)
    noise = np.kron(noise, np.ones((4, 4), np.float32))
    img += np.where(tread[:, None], 0.004, 0.0015) * noise
    for vv in (va - 0.035, 1 - (va - 0.035)):
        img[np.abs(v - vv) < 0.0035] *= 0.6
    rib = (v < 0.07) | (v > 0.93)
    img[rib] = 0.015
    # sport-tyre grooves: a sweeping groove each side, 12 per side, staggered
    mask = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    vc = 0.5
    span_v = (vb - va) / 2
    for side in (-1, 1):
        for k in range(12):
            u0 = (k + (0.5 if side > 0 else 0.0)) / 12
            for s in np.linspace(0, 1, 70):
                uu = (u0 + s * 0.085) % 1.0
                vv = vc + side * span_v * (0.12 + 0.62 * s ** 1.15)
                wid = 0.0045 * (1 - 0.6 * s)       # groove tapers toward the shoulder
                cx, cy = uu * W, vv * H
                rx, ry = wid / circ * W, wid / plen * H
                x0, x1 = int(cx - rx - 2), int(cx + rx + 3)
                y0, y1 = max(0, int(cy - ry - 2)), min(H, int(cy + ry + 3))
                xs = np.arange(x0, x1) % W
                sub = ((xx[y0:y1, :len(xs)] * 0 + np.arange(x0, x1)[None, :] - cx) / rx) ** 2 + ((yy[y0:y1, :len(xs)] - cy) / ry) ** 2 < 1
                mask[y0:y1, xs] |= sub
    img[mask] = 0.007
    rgb = np.clip(np.stack([img, img, img * 1.03], -1), 0, 1)
    save_png(path, rgb)


def rotor_texture(path, S=1024, seed=2, r_scale=0.165):
    rng = np.random.default_rng(seed)
    c = (np.arange(S) + 0.5) / S * 2 - 1
    X, Y = np.meshgrid(c, c)
    r = np.sqrt(X * X + Y * Y) * r_scale
    rings = rng.normal(0, 1, 4096).astype(np.float32)
    rings = np.convolve(rings, np.ones(3) / 3, "same")
    idx = np.clip((r / r_scale * 4095).astype(int), 0, 4095)
    g = 0.50 + 0.035 * rings[idx]
    # slight blueish heat tint on the swept band
    band = np.exp(-((r - 0.14) / 0.02) ** 2)
    rgb = np.stack([g - 0.02 * band, g - 0.01 * band, g + 0.015 * band], -1)
    save_png(path, np.clip(rgb, 0, 1))


def save_png(path, rgb):
    H, W, _ = rgb.shape
    im = bpy.data.images.new(os.path.basename(path), W, H, alpha=False)
    rgb = np.clip(rgb, 0, 1) ** (1 / 2.2)   # linear albedo -> sRGB file
    px = np.concatenate([rgb, np.ones((H, W, 1), np.float32)], -1)
    im.pixels.foreach_set(px.astype(np.float32).ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


# ------------------------------------------------------------------ looks (render + Roblox colours)
LOOKS = {
    "Tyre": {"tex": "Tyre", "rough": 0.72, "metal": 0.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic"}},
    "Rim": {"color": (0.010, 0.010, 0.011), "rough": 0.3, "metal": 0.0, "coat": 1.0, "roblox": {"Color": [24, 24, 26], "Material": "SmoothPlastic", "Reflectance": 0.06}},
    "Valve": {"color": (0.55, 0.56, 0.58), "rough": 0.25, "metal": 1.0, "roblox": {"Color": [168, 170, 176], "Material": "SmoothPlastic", "Reflectance": 0.2}},
    "Rotor": {"tex": "Rotor", "rough": 0.32, "metal": 1.0, "roblox": {"Color": [255, 255, 255], "Material": "SmoothPlastic", "Reflectance": 0.12}},
    "Carrier": {"color": (0.06, 0.062, 0.066), "rough": 0.4, "metal": 1.0, "roblox": {"Color": [62, 64, 68], "Material": "SmoothPlastic", "Reflectance": 0.08}},
    "Caliper": {"color": (0.02, 0.09, 0.42), "rough": 0.3, "metal": 0.6, "roblox": {"Color": [32, 74, 168], "Material": "SmoothPlastic", "Reflectance": 0.05}},
    "Sprocket": {"color": (0.025, 0.025, 0.027), "rough": 0.42, "metal": 1.0, "roblox": {"Color": [38, 38, 40], "Material": "SmoothPlastic", "Reflectance": 0.06}},
}


def look_key(name):
    for k in LOOKS:
        if name.startswith(k):
            return k
    raise KeyError(name)


def material(key, tex_path=None):
    L = LOOKS[key]
    m = bpy.data.materials.get(f"M_{key}_{os.path.basename(tex_path or '')}")
    if m:
        return m
    m = bpy.data.materials.new(f"M_{key}_{os.path.basename(tex_path or '')}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = L["rough"]
    b.inputs["Metallic"].default_value = L["metal"]
    if L.get("coat"):
        b.inputs["Coat Weight"].default_value = L["coat"]
        b.inputs["Coat Roughness"].default_value = 0.05
    if tex_path:
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(tex_path, check_existing=True)
        m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*L["color"], 1)
    return m


# ------------------------------------------------------------------ export
def export(name, obs, marks, extra):
    out = os.path.join(MODELS, name)
    tex = os.path.join(out, "tex")
    os.makedirs(tex, exist_ok=True)
    texmap = {}
    tyre_png = os.path.join(tex, "Tyre_Color.png")
    tyre_texture(tyre_png, marks)
    rotor_png = os.path.join(tex, "Rotor_Color.png")
    if any(look_key(o.name) == "Rotor" for o in obs):
        rotor_texture(rotor_png)
    meta = {"units": "studs (x3.6 baked in, use Scale 1)",
            "axes": "Blender: axle = X (+X = bike's LEFT), -Y = front, +Z = up. Roblox = (-x, z, y), so the axle is Roblox X.",
            "origin": "hub centre", "spin": [], "static": [], "parts": {}, "looks": {}, **extra}
    for ob in obs:
        k = look_key(ob.name)
        G.smooth(ob, 32 if k != "Tyre" else 60)
        tp = tyre_png if k == "Tyre" else rotor_png if k == "Rotor" else None
        ob.data.materials.clear()
        ob.data.materials.append(material(k, tp))
        if tp:
            texmap[ob.name] = os.path.relpath(tp, ROOT).replace(os.sep, "/")
        (meta["static"] if k == "Caliper" else meta["spin"]).append(ob.name)
        meta["looks"][ob.name] = LOOKS[k]["roblox"]
        mn = [min(v.co[i] for v in ob.data.vertices) for i in range(3)]
        mx = [max(v.co[i] for v in ob.data.vertices) for i in range(3)]
        meta["parts"][ob.name] = {"tris": G.tris(ob), "bbox_min_m": [round(a, 4) for a in mn], "bbox_max_m": [round(a, 4) for a in mx]}
    # export a stud-scaled copy, plain placeholder materials (no images inside the GLB)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    copies = []
    for ob in obs:
        c = ob.copy()
        c.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(c)
        c.data.transform(__import__("mathutils").Matrix.Scale(STUDS, 4))
        c.name = ob.name + "_x"
        c.select_set(True)
        copies.append(c)
    path = os.path.join(out, f"{name}.glb")
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_materials='PLACEHOLDER',
                              export_apply=True, export_yup=True, export_texcoords=True, export_normals=True)
    for c in copies:
        bpy.data.objects.remove(c, do_unlink=True)
    # GLB node names must be the part names
    import struct
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
    rest = data[20 + ln:]
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + rest
    open(path, "wb").write(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    meta["total_tris"] = sum(p["tris"] for p in meta["parts"].values())
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    json.dump(texmap, open(os.path.join(out, "textures.json"), "w"), indent=1)
    print(name, "tris", meta["total_tris"], {k: v["tris"] for k, v in meta["parts"].items()})


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in ("front", "rear")] or ["front", "rear"]
    for w in which:
        reset()
        if w == "front":
            obs, marks = front_wheel()
            export("BikeWheelFront", obs, marks, {"tyre": "120/70 ZR17", "rim": "3.50x17", "discs": "2x 320 mm floating", "radius_m": 0.2999})
        else:
            obs, marks = rear_wheel()
            export("BikeWheelRear", obs, marks, {"tyre": "190/55 ZR17", "rim": "6.00x17", "disc": "220 mm", "sprocket": "45T 525", "radius_m": 0.3204})
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(MODELS, "BikeWheelFront" if w == "front" else "BikeWheelRear", "work.blend"))
