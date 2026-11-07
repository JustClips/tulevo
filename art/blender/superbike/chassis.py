"""Superbike chassis: aluminium twin-spar frame, bronze trellis subframe, black swingarm with underslung
bracing, rear shock (red-orange spring, piggyback reservoir) and linkage, rider footrests with gear and
brake levers, pillion pegs, side stand (folded up) and the rear hugger.

  /home/user/bvenv/bin/python art/blender/superbike/chassis.py      build + export art/models/BikeChassis

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
Positions follow the reference scan's side and top views (frame visible under the tank, trellis under the
seat, pivot at y 0.12) and the parts already built: wheels at the hubs, chain line x = 0.085 (left),
exhaust box under the engine and silencer on the right, seats and tail on top.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bikeio as IO  # noqa: E402
import fairings as FA  # noqa: E402
import solids as SD  # noqa: E402

MODEL = "BikeChassis"
OUT = os.path.join(IO.MODELS, MODEL)

RAKE = math.radians(23.1)
STEER_DIR = np.array([0.0, math.sin(RAKE), math.cos(RAKE)])
STEER_GROUND_Y = -0.8144
PIVOT = np.array([0.0, 0.12, 0.42])
REAR_AXLE = np.array([0.0, 0.7205, 0.3204])
CHAIN_X = 0.085


def steer_point(z):
    return np.array([0.0, STEER_GROUND_Y + math.tan(RAKE) * z, z])


def smooth_path(pts, n=6):
    return FA.cr_curve([tuple(p) for p in pts], closed=False, n=n)


def mirror_pts(pts):
    P = np.array(pts, float)
    P[:, 0] *= -1
    return P


def side_pillow(sol, outline_yz, x_in, t, r, sgn, n=None):
    """Plate in the y-z plane: inner face at |x| = x_in, pushed outward (away from the centre) by t."""
    L = np.asarray(outline_yz, float)
    if sgn > 0:
        return SD.pillow(sol, L, (x_in, 0, 0), (0, 1, 0), (0, 0, 1), t, r, n=n)
    return SD.pillow(sol, L[:, ::-1], (-x_in, 0, 0), (0, 0, 1), (0, 1, 0), t, r, n=n)


def taper_sections(n, w0, h0, w1, h1, r=None, k=3):
    return [SD.rrect(w0 + (w1 - w0) * i / (n - 1), h0 + (h1 - h0) * i / (n - 1), r, k) for i in range(n)]


# ------------------------------------------------------------------ frame
SPAR = [(0.040, -0.505, 0.775), (0.090, -0.420, 0.765), (0.125, -0.300, 0.745), (0.138, -0.170, 0.722),
        (0.140, -0.050, 0.700), (0.138, 0.030, 0.665), (0.134, 0.075, 0.610)]
PIVOT_PLATE = [(0.035, 0.665), (0.105, 0.670), (0.150, 0.625), (0.180, 0.540), (0.185, 0.470), (0.172, 0.385), (0.135, 0.345),
               (0.095, 0.345), (0.062, 0.380), (0.045, 0.450), (0.030, 0.560)]


def frame():
    sol = SD.Solid()
    # head tube on the steering axis
    p0 = steer_point(0.665)
    L = (0.855 - 0.665) / math.cos(RAKE)
    SD.lathe(sol, [(0.0, -0.002), (0.030, -0.002), (0.033, 0.006), (0.033, L - 0.006), (0.030, L + 0.002), (0.0, L + 0.002)],
             p0, STEER_DIR, seg=28)
    for sg in (1, -1):
        path = smooth_path([(sg * x, y, z) for x, y, z in SPAR], n=6)
        n = len(path)
        secs = [SD.rrect(0.016, 0.048 - 0.010 * i / (n - 1), 0.008) for i in range(n)]
        SD.sweep(sol, path, secs)
        # gusset joining the spar to the head tube
        SD.sweep(sol, [steer_point(0.70) + np.array([sg * 0.02, 0.02, 0]), np.array([sg * 0.075, -0.445, 0.725])],
                 SD.rrect(0.012, 0.030, 0.006))
        side_pillow(sol, PIVOT_PLATE, 0.118, 0.026, 0.006, sg)
        # pivot bolt head + nut
        SD.lathe(sol, [(0.0, 0.0), (0.024, 0.0), (0.024, 0.006), (0.020, 0.010), (0.0, 0.010)],
                 PIVOT + np.array([sg * 0.143, 0, 0]), (sg, 0, 0), seg=6)
    # cross tubes between the pivot plates and under the spars
    SD.tube(sol, [(-0.125, 0.08, 0.625), (0.125, 0.08, 0.625)], 0.017, seg=14, up=(0, 1, 0))
    SD.tube(sol, [(-0.125, 0.06, 0.375), (0.125, 0.06, 0.375)], 0.015, seg=14, up=(0, 1, 0))
    return sol


# ------------------------------------------------------------------ subframe (round trellis tubes)
SUB_UPPER = [(0.130, 0.020, 0.680), (0.092, 0.080, 0.712), (0.090, 0.200, 0.735), (0.088, 0.400, 0.752), (0.082, 0.560, 0.795)]
SUB_LOWER = [(0.130, 0.105, 0.555), (0.112, 0.180, 0.598), (0.104, 0.260, 0.645), (0.096, 0.340, 0.700), (0.090, 0.405, 0.748)]
SUB_STRUTS = [((0.112, 0.180, 0.598), (0.090, 0.130, 0.726)), ((0.112, 0.180, 0.598), (0.090, 0.270, 0.741)),
              ((0.096, 0.340, 0.700), (0.090, 0.270, 0.741))]


def subframe():
    sol = SD.Solid()
    r = 0.0105
    for sg in (1, -1):
        for rail in (SUB_UPPER, SUB_LOWER):
            P = smooth_path([(sg * x, y, z) for x, y, z in rail], n=6)
            SD.tube(sol, P, r, seg=12, up=(1, 0, 0))
        for a, b in SUB_STRUTS:
            SD.tube(sol, [(sg * a[0], a[1], a[2]), (sg * b[0], b[1], b[2])], r * 0.85, seg=10, up=(1, 0, 0))
        # mounting lugs at the frame
        for p in (SUB_UPPER[0], SUB_LOWER[0]):
            SD.lathe(sol, [(0.0, -0.012), (0.014, -0.012), (0.014, 0.012), (0.0, 0.012)], (sg * p[0], p[1], p[2]), (1, 0, 0), seg=12)
    for y, z in ((0.20, 0.735), (0.48, 0.770)):
        SD.tube(sol, [(-0.09, y, z), (0.09, y, z)], r, seg=12, up=(0, 1, 0))
    return sol


# ------------------------------------------------------------------ swingarm
def arm_x(y):
    """Arm centre line: narrow between the pivot plates, wider behind them (left arm clears the chain)."""
    return np.interp(y, [0.12, 0.20, 0.30, 0.75], [0.107, 0.118, 0.125, 0.125])


def arm_w(y):
    return np.interp(y, [0.12, 0.20, 0.30, 0.75], [0.010, 0.014, 0.020, 0.018])


def arm_h(y):
    return np.interp(y, [0.10, 0.30, 0.55, 0.76], [0.056, 0.048, 0.040, 0.032])


def swingarm():
    sol = SD.Solid()
    ys = np.linspace(0.095, 0.755, 34)
    d = REAR_AXLE - PIVOT
    for sg in (1, -1):
        zc = PIVOT[2] + (ys - PIVOT[1]) / d[1] * d[2]
        path = np.stack([sg * arm_x(ys), ys, zc], 1)
        SD.sweep(sol, path, [SD.rrect(arm_w(y), arm_h(y), 0.008) for y in ys])
        # underslung brace: from under the pivot down and back, up into the arm before the axle
        br = smooth_path([(sg * 0.120, 0.215, 0.372), (sg * 0.124, 0.330, 0.300), (sg * 0.125, 0.470, 0.280),
                          (sg * 0.125, 0.600, 0.295), (sg * 0.125, 0.665, 0.318)], n=6)
        SD.sweep(sol, br, SD.rrect(0.011, 0.013, 0.005))
        for yy in (0.33, 0.47, 0.58):
            zt = PIVOT[2] + (yy - PIVOT[1]) / d[1] * d[2]
            zb = float(np.interp(yy, br[:, 1], br[:, 2]))
            side_pillow(sol, [(yy - 0.012, zb), (yy + 0.012, zb), (yy + 0.008, zt), (yy - 0.008, zt)], 0.117, 0.016, 0.004, sg)
        # axle block, chain adjuster and axle nut
        SD.box(sol, (sg * 0.125, 0.722, 0.3204), (0.021, 0.020, 0.024), r=0.004)
        SD.lathe(sol, [(0.0, 0.0), (0.019, 0.0), (0.019, 0.012), (0.014, 0.016), (0.0, 0.016)],
                 REAR_AXLE + np.array([sg * 0.146, 0, 0]), (sg, 0, 0), seg=6)
        SD.tube(sol, [(sg * 0.125, 0.742, 0.3204), (sg * 0.125, 0.772, 0.3204)], 0.005, seg=8, up=(1, 0, 0))
    # pivot tube and cross brace
    SD.lathe(sol, [(0.0, -0.118), (0.030, -0.118), (0.030, 0.118), (0.0, 0.118)], PIVOT, (1, 0, 0), seg=24)
    SD.sweep(sol, [(-0.118, 0.272, 0.392), (0.118, 0.272, 0.392)], SD.rrect(0.022, 0.032, 0.008), up=(0, 0, 1))
    # chain slider on the left arm (black plastic, kept in the same part)
    return sol


def chain_slider():
    sol = SD.Solid()
    ys = np.linspace(0.13, 0.40, 10)
    d = REAR_AXLE - PIVOT
    zc = PIVOT[2] + (ys - PIVOT[1]) / d[1] * d[2]
    path = np.stack([arm_x(ys) - arm_w(ys) * 0.2, ys, zc + arm_h(ys) + 0.004], 1)
    SD.sweep(sol, path, SD.rrect(0.016, 0.005, 0.003))
    return sol


# ------------------------------------------------------------------ shock + linkage
SHOCK_TOP = np.array([0.0, 0.200, 0.650])
SHOCK_BOT = np.array([0.0, 0.206, 0.360])


def shock():
    body, spring, res, link = SD.Solid(), SD.Solid(), SD.Solid(), SD.Solid()
    ax = SHOCK_BOT - SHOCK_TOP
    L = np.linalg.norm(ax)
    ax /= L
    # eyes (along x)
    for p in (SHOCK_TOP, SHOCK_BOT):
        SD.lathe(body, [(0.0, -0.014), (0.014, -0.014), (0.014, 0.014), (0.0, 0.014)], p, (1, 0, 0), seg=14)
    # damper body from the top eye down, shaft to the bottom eye
    SD.lathe(body, [(0.0, 0.010), (0.024, 0.012), (0.026, 0.020), (0.026, 0.150), (0.022, 0.158), (0.0, 0.160)], SHOCK_TOP, ax, seg=20)
    SD.lathe(body, [(0.0, 0.150), (0.008, 0.150), (0.008, L - 0.012), (0.0, L - 0.012)], SHOCK_TOP, ax, seg=10)
    # spring seats (preload collar at the top, lower seat on the shaft clevis)
    SD.lathe(body, [(0.0, 0.040), (0.040, 0.040), (0.040, 0.050), (0.0, 0.050)], SHOCK_TOP, ax, seg=20)
    SD.lathe(body, [(0.0, L - 0.060), (0.038, L - 0.060), (0.038, L - 0.050), (0.0, L - 0.050)], SHOCK_TOP, ax, seg=20)
    SD.lathe(body, [(0.0, L - 0.050), (0.014, L - 0.050), (0.014, L - 0.012), (0.0, L - 0.012)], SHOCK_TOP, ax, seg=12)
    SD.spring(spring, SHOCK_TOP + ax * 0.050, ax, 0.031, 0.0055, 7.5, L - 0.110, seg=8, per_turn=18)
    # piggyback reservoir on the left of the body
    rp = SHOCK_TOP + ax * 0.03 + np.array([0.052, 0.0, 0.0])
    SD.lathe(res, [(0.0, -0.002), (0.017, 0.0), (0.017, 0.095), (0.012, 0.100), (0.0, 0.100)], rp, ax, seg=16)
    SD.sweep(res, [SHOCK_TOP + ax * 0.03 + np.array([0.02, 0, 0]), rp], SD.rrect(0.010, 0.010, 0.004), up=(0, 1, 0))
    # linkage: rocker from the frame lug to the shock eye and the swingarm brace
    for sg in (1, -1):
        side_pillow(link, [(0.150, 0.300), (0.215, 0.345), (0.285, 0.360), (0.285, 0.380), (0.215, 0.372), (0.140, 0.322)], 0.016, 0.008, 0.002, sg)
    SD.lathe(link, [(0.0, -0.03), (0.010, -0.03), (0.010, 0.03), (0.0, 0.03)], np.array([0, 0.145, 0.31]), (1, 0, 0), seg=10)
    return body, spring, res, link


# ------------------------------------------------------------------ footrests, levers, pillion pegs, stand
REARSET = [(0.090, 0.515), (0.150, 0.525), (0.215, 0.500), (0.300, 0.468), (0.338, 0.455), (0.340, 0.428), (0.300, 0.418),
           (0.200, 0.428), (0.120, 0.452), (0.082, 0.480)]
PEG = np.array([0.0, 0.312, 0.443])


def rearsets():
    alu, pegs = SD.Solid(), SD.Solid()
    for sg in (1, -1):
        side_pillow(alu, REARSET, 0.144, 0.009, 0.003, sg)
        # heel guard
        side_pillow(alu, [(0.255, 0.470), (0.330, 0.520), (0.350, 0.505), (0.345, 0.455), (0.300, 0.452)], 0.153, 0.004, 0.0015, sg)
        # peg pivot block + knurled peg
        SD.box(alu, (sg * 0.160, PEG[1], PEG[2]), (0.010, 0.012, 0.012), r=0.003)
        SD.lathe(pegs, [(0.0, 0.0), (0.0115, 0.0), (0.0115, 0.085), (0.0090, 0.092), (0.0, 0.093)],
                 (sg * 0.165, PEG[1], PEG[2]), (sg, 0, 0), seg=12)
        # lever: pivot under the peg, arm forward to a toe peg
        piv = np.array([sg * 0.160, PEG[1] - 0.004, PEG[2] - 0.028])
        tip = np.array([sg * 0.168, 0.135 if sg > 0 else 0.150, 0.405])
        SD.sweep(alu, [piv, tip], SD.rrect(0.004, 0.009, 0.003), up=(0, 0, 1))
        SD.lathe(pegs, [(0.0, 0.0), (0.008, 0.0), (0.008, 0.038), (0.0, 0.040)], tip, (sg, 0, 0), seg=10)
    # gear linkage rod (left) up to the gearbox shaft, brake master cylinder (right)
    SD.tube(alu, [(0.168, 0.150, 0.402), (0.150, 0.085, 0.470)], 0.0045, seg=8, up=(1, 0, 0))
    SD.lathe(alu, [(0.0, 0.0), (0.010, 0.0), (0.010, 0.060), (0.0, 0.060)], np.array([-0.158, 0.268, 0.452]), (0, -0.25, 1.0), seg=12)
    return alu, pegs


def pillion_pegs():
    alu, pegs = SD.Solid(), SD.Solid()
    for sg in (1, -1):
        side_pillow(alu, [(0.380, 0.735), (0.420, 0.742), (0.528, 0.655), (0.540, 0.618), (0.512, 0.608), (0.470, 0.640), (0.372, 0.712)],
                    0.104, 0.008, 0.003, sg)
        SD.lathe(pegs, [(0.0, 0.0), (0.0105, 0.0), (0.0105, 0.075), (0.0085, 0.082), (0.0, 0.083)],
                 (sg * 0.112, 0.522, 0.628), (sg, 0, 0), seg=12)
    return alu, pegs


def side_stand():
    sol = SD.Solid()
    piv = np.array([0.112, 0.055, 0.300])
    foot = np.array([0.140, 0.335, 0.338])
    n = 8
    path = np.array([piv + (foot - piv) * i / (n - 1) for i in range(n)])
    SD.sweep(sol, path, [SD.circle(0.0125 - 0.004 * i / (n - 1), 12) for i in range(n)], up=(1, 0, 0))
    SD.lathe(sol, [(0.0, -0.014), (0.020, -0.014), (0.020, 0.014), (0.0, 0.014)], piv, (1, 0, 0), seg=14)
    # foot pad turned out to the side, and the tab you kick it down with
    SD.box(sol, foot + np.array([0.012, 0.010, 0.0]), (0.020, 0.028, 0.006), axes=[(1, 0, 0), (0, 1, 0), (0, 0, 1)], r=0.004)
    SD.tube(sol, [piv + np.array([0.0, 0.03, 0.004]), piv + np.array([0.040, 0.035, 0.012])], 0.006, seg=8, up=(0, 1, 0))
    SD.spring(sol, piv + np.array([-0.012, 0.03, -0.012]), (0, 1, 0.05), 0.006, 0.0018, 9, 0.10, seg=6, per_turn=10, ground=False)
    return sol


# ------------------------------------------------------------------ rear hugger (over the rear tyre, on the swingarm)
def hugger():
    acc = FA.MeshAcc()
    angs = np.radians(np.linspace(62, 152, 34))
    xs = np.linspace(-1, 1, 23)
    P = np.zeros((len(angs), len(xs), 3))
    for i, a in enumerate(angs):
        for j, s in enumerate(xs):
            x = 0.098 * s
            skirt = max(0.0, (abs(s) - 0.72) / 0.28)
            rr = 0.352 - 0.030 * skirt ** 2
            xx = x * (1 - 0.10 * skirt)
            P[i, j] = REAR_AXLE + np.array([xx, rr * math.cos(a), rr * math.sin(a)])
            # lower front end flares down toward the cross brace
    def out_hint(Q, N):
        rad = Q - REAR_AXLE
        rad[..., 0] = 0
        return np.sum(rad * N, -1) > 0
    FA.grid_shell(acc, P, 0.0025, out_hint, rim_k=4)
    # mounting tabs down to the arms
    sol = SD.Solid()
    for sg in (1, -1):
        a = math.radians(140)
        top = REAR_AXLE + np.array([sg * 0.090, 0.338 * math.cos(a), 0.338 * math.sin(a)])
        y = top[1]
        d = REAR_AXLE - PIVOT
        za = PIVOT[2] + (y - PIVOT[1]) / d[1] * d[2] + arm_h(y)
        side_pillow(sol, [(y - 0.012, za - 0.004), (y + 0.012, za - 0.004), (y + 0.008, top[2]), (y - 0.008, top[2])],
                    0.090, 0.005, 0.0015, sg)
    return acc, sol


# ------------------------------------------------------------------ build
LOOKS = {
    "Frame": IO.L_col((176, 179, 185), 0.32, metal=1.0, mat="Metal", refl=0.18),
    "Subframe": IO.L_col((148, 110, 62), 0.36, metal=1.0, mat="Metal", refl=0.15),
    "Swingarm": IO.L_col((30, 31, 34), 0.38, metal=0.6, refl=0.12),
    "ChainSlider": IO.L_col((16, 16, 17), 0.7),
    "ShockBody": IO.L_col((28, 29, 32), 0.3, metal=1.0, mat="Metal", refl=0.15),
    "ShockSpring": IO.L_col(IO.ACCENT, 0.3, refl=0.1),
    "ShockReservoir": IO.L_col((196, 160, 72), 0.25, metal=1.0, mat="Metal", refl=0.25),
    "Linkage": IO.L_col((50, 51, 55), 0.35, metal=1.0, mat="Metal", refl=0.1),
    "Rearsets": IO.L_col((196, 199, 205), 0.25, metal=1.0, mat="Metal", refl=0.25),
    "Pegs": IO.L_col((40, 41, 44), 0.5, metal=1.0, mat="Metal"),
    "PillionBrackets": IO.L_col((196, 199, 205), 0.25, metal=1.0, mat="Metal", refl=0.25),
    "PillionPegs": IO.L_col((40, 41, 44), 0.5, metal=1.0, mat="Metal"),
    "SideStand": IO.L_col((34, 35, 38), 0.4, metal=1.0, mat="Metal"),
    "Hugger": IO.L_col(IO.CHAR, 0.3, refl=0.06, coat=0.4),
    "HuggerTabs": IO.L_col((20, 20, 22), 0.6),
}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = {}
    s["Frame"] = frame()
    s["Subframe"] = subframe()
    s["Swingarm"] = swingarm()
    s["ChainSlider"] = chain_slider()
    s["ShockBody"], s["ShockSpring"], s["ShockReservoir"], s["Linkage"] = shock()
    s["Rearsets"], s["Pegs"] = rearsets()
    s["PillionBrackets"], s["PillionPegs"] = pillion_pegs()
    s["SideStand"] = side_stand()
    hug, tabs = hugger()
    parts = {name: sol.obj(name, 40) for name, sol in s.items()}
    parts["Hugger"] = hug.obj("Hugger")
    parts["HuggerTabs"] = tabs.obj("HuggerTabs")
    IO.apply_materials(parts, LOOKS, {}, None)
    return parts


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = build()
    IO.export_model(MODEL, parts, LOOKS, {}, credit=None)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
