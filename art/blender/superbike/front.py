"""Superbike front end: upside-down forks (gold outer tubes), triple clamps, clip-on bars with grips,
brake and clutch levers, switch pods, brake fluid reservoir, mirrors on the fairing, TFT dash, front
mudguard, front axle.

  /home/user/bvenv/bin/python art/blender/superbike/front.py      build + export art/models/BikeFront

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
Steering geometry from the wheel layout: rake 23.1 deg, trail 94 mm, fork legs 31 mm in front of the
steering axis (triple clamp offset), through the front axle. Built with the steering straight ahead.
The dash screen is its own part (DashScreen) so the game can put a live display on it later.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from shapely.geometry import Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

import bikeio as IO  # noqa: E402
import fairings as FA  # noqa: E402
import solids as SD  # noqa: E402

MODEL = "BikeFront"
OUT = os.path.join(IO.MODELS, MODEL)
TEX = os.path.join(OUT, "tex")

RAKE = math.radians(23.1)
AX = np.array([0.0, math.sin(RAKE), math.cos(RAKE)])          # up the steering axis
FWD = np.array([0.0, -math.cos(RAKE), math.sin(RAKE)])        # forward, square to the axis
FRONT_AXLE = np.array([0.0, -0.7205, 0.2999])
FORK_X = 0.108


def fork_pt(x, z):
    """Point on a fork leg axis (through the axle, parallel to the steering axis) at height z."""
    t = (z - FRONT_AXLE[2]) / AX[2]
    return np.array([x, FRONT_AXLE[1] + t * AX[1], z])


def steer_pt(z):
    return np.array([0.0, -0.8144 + math.tan(RAKE) * z, z])


# ------------------------------------------------------------------ forks
def forks():
    outer, inner, feet = SD.Solid(), SD.Solid(), SD.Solid()
    for sg in (1, -1):
        x = sg * FORK_X
        base = fork_pt(x, FRONT_AXLE[2])
        t_top = (0.905 - FRONT_AXLE[2]) / AX[2]
        t_out = (0.548 - FRONT_AXLE[2]) / AX[2]
        # gold outer tube: seal head at the bottom, plain tube up through both clamps, top cap
        SD.lathe(outer, [(0.0, t_out - 0.004), (0.0285, t_out - 0.004), (0.0300, t_out + 0.010), (0.0300, t_out + 0.040),
                         (0.0275, t_out + 0.048), (0.0275, t_top - 0.006), (0.0255, t_top), (0.0, t_top)], base, AX, seg=28)
        # dark stanchion (inner tube) from the foot up into the outer tube
        SD.lathe(inner, [(0.0, 0.070), (0.0225, 0.070), (0.0225, t_out + 0.02), (0.0, t_out + 0.02)], base, AX, seg=24)
        # top cap adjuster
        SD.lathe(feet, [(0.0, t_top), (0.017, t_top), (0.017, t_top + 0.010), (0.008, t_top + 0.014), (0.0, t_top + 0.014)], base, AX, seg=6)
        # axle foot: round boss on the axle with a clamp block, leg sleeve up to the stanchion
        SD.lathe(feet, [(0.0, -0.032), (0.026, -0.032), (0.030, -0.020), (0.030, 0.020), (0.026, 0.032), (0.0, 0.032)],
                 np.array([x, base[1], base[2]]), (1, 0, 0), seg=20)
        SD.lathe(feet, [(0.0, 0.0), (0.030, 0.0), (0.030, 0.085), (0.0255, 0.095), (0.0, 0.095)], base, AX, seg=24)
        # radial caliper mount reaching back to the caliper lugs (wheels.py: front caliper at 18 deg, lugs r 0.176)
        lug_a = FRONT_AXLE + 0.176 * np.array([0, math.cos(math.radians(-1.5)), math.sin(math.radians(-1.5))])
        lug_b = FRONT_AXLE + 0.176 * np.array([0, math.cos(math.radians(37.5)), math.sin(math.radians(37.5))])
        outline = [(base[1] + 0.02, base[2] - 0.028), (lug_a[1] + 0.012, lug_a[2] - 0.012), (lug_a[1] + 0.016, lug_a[2] + 0.010),
                   (lug_b[1] + 0.016, lug_b[2] + 0.004), (lug_b[1] - 0.004, lug_b[2] + 0.016), (base[1] + 0.03, base[2] + 0.075)]
        L = np.array(outline)
        if sg > 0:
            SD.pillow(feet, L, (0.084, 0, 0), (0, 1, 0), (0, 0, 1), 0.012, 0.003)
        else:
            SD.pillow(feet, L[:, ::-1], (-0.084, 0, 0), (0, 0, 1), (0, 1, 0), 0.012, 0.003)
    # axle with nuts
    SD.lathe(feet, [(0.0, -0.150), (0.012, -0.150), (0.012, 0.150), (0.0, 0.150)], FRONT_AXLE, (1, 0, 0), seg=12)
    for sg in (1, -1):
        SD.lathe(feet, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.010), (0.010, 0.013), (0.0, 0.013)],
                 FRONT_AXLE + np.array([sg * 0.139, 0, 0]), (sg, 0, 0), seg=6)
    return outer, inner, feet


# ------------------------------------------------------------------ triple clamps
def clamp_outline(r_fork, r_stem, tail):
    shapes = [Point(0.0, 0.0).buffer(r_stem, quad_segs=10)]
    for sg in (1, -1):
        shapes.append(Point(sg * FORK_X, 0.031).buffer(r_fork, quad_segs=10))
    hull = unary_union(shapes).convex_hull
    rear = Point(0.0, -tail).buffer(r_stem * 0.8, quad_segs=8)
    return np.array(unary_union([hull, rear]).convex_hull.exterior.coords)[:-1]


def clamps():
    top, bottom = SD.Solid(), SD.Solid()
    # top clamp: plate square to the steering axis; outline in (x, forward) -> pillow in (forward, x)
    for sol, z0, th, rf, rs, tail in ((top, 0.876, 0.020, 0.045, 0.034, 0.030), (bottom, 0.625, 0.040, 0.050, 0.040, 0.050)):
        o = steer_pt(z0)
        L = clamp_outline(rf, rs, tail)
        SD.pillow(sol, L[:, ::-1], o, FWD, (1, 0, 0), th, 0.005)
        if sol is bottom:
            # rounded underside
            SD.pillow(sol, L * 0.92, o, (1, 0, 0), FWD, 0.006, 0.004)
    # stem nut on top, pinch bolts at the fork tubes
    o = steer_pt(0.876) + AX * 0.020
    SD.lathe(top, [(0.0, 0.0), (0.020, 0.0), (0.020, 0.010), (0.016, 0.013), (0.0, 0.013)], o, AX, seg=6)
    for sg in (1, -1):
        p = fork_pt(sg * FORK_X, 0.885) + FWD * 0.0 + np.array([sg * 0.045, 0, 0])
        SD.lathe(top, [(0.0, -0.006), (0.006, -0.006), (0.006, 0.006), (0.0, 0.006)], p, (1, 0, 0), seg=6)
    return top, bottom


# ------------------------------------------------------------------ bars, grips, levers, switches
BAR_END = np.array([0.352, -0.305, 0.832])


def bars():
    bar, grips, ctrl, levers = SD.Solid(), SD.Solid(), SD.Solid(), SD.Solid()
    for sg in (1, -1):
        clamp_c = fork_pt(sg * FORK_X, 0.848)
        # clip-on clamp collar round the fork tube
        SD.lathe(bar, [(0.0, -0.024), (0.036, -0.024), (0.036, 0.024), (0.0, 0.024)], clamp_c, AX, seg=20)
        end = BAR_END * np.array([sg, 1, 1])
        start = clamp_c + np.array([sg * 0.030, 0.012, -0.004])
        d = end - start
        d /= np.linalg.norm(d)
        SD.tube(bar, [start, end], 0.011, seg=14, up=(0, 0, 1))
        # grip (left) / throttle grip (right) on the outer 125 mm, bar-end weight
        g0 = end - d * 0.128
        SD.lathe(grips, [(0.0, 0.0), (0.0175, 0.0), (0.0175, 0.118), (0.0185, 0.124), (0.0, 0.128)], g0, d, seg=16)
        SD.lathe(bar, [(0.0, 0.0), (0.0175, 0.002), (0.0180, 0.016), (0.0140, 0.024), (0.0, 0.025)], end + d * 0.002, d, seg=14)
        # switch pod at the inner end of the grip
        pod = g0 - d * 0.024
        SD.box(ctrl, pod, (0.026, 0.022, 0.024), axes=[np.cross(d, (0, 0, 1)), d, (0, 0, 1)], r=0.009)
        # lever perch + lever blade curving out in front of the grip
        perch = g0 - d * 0.004 + np.array([0, -0.030, 0.006])
        SD.box(ctrl, perch, (0.016, 0.022, 0.016), axes=[np.cross(d, (0, 0, 1)), d, (0, 0, 1)], r=0.006)
        blade = [perch + np.array([0, -0.010, 0]), perch + d * 0.050 + np.array([0, -0.040, -0.004]),
                 perch + d * 0.110 + np.array([0, -0.046, -0.010]), perch + d * 0.160 + np.array([0, -0.040, -0.014])]
        P = FA.cr_curve([tuple(p) for p in blade], closed=False, n=5)
        SD.sweep(levers, P, SD.rrect(0.004, 0.009, 0.003), up=(0, 0, 1))
        SD.lathe(levers, [(0.0, -0.012), (0.006, -0.012), (0.006, 0.012), (0.0, 0.012)], perch + np.array([0, -0.010, 0]), (0, 0, 1), seg=8)
    # front brake master cylinder (right) + fluid reservoir cup on a stalk; clutch reservoir (left, smaller)
    mc = fork_pt(-0.20, 0.86) + np.array([0.0, 0.05, 0.0])
    SD.lathe(ctrl, [(0.0, 0.0), (0.013, 0.0), (0.013, 0.060), (0.0, 0.060)], mc + np.array([-0.06, 0.02, 0.0]), (-1, -0.2, 0), seg=12)
    cup = mc + np.array([-0.035, 0.035, 0.065])
    SD.lathe(ctrl, [(0.0, 0.0), (0.021, 0.0), (0.022, 0.045), (0.020, 0.050), (0.0, 0.052)], cup, (0, 0.25, 1), seg=16)
    SD.tube(ctrl, [mc + np.array([-0.04, 0.03, 0.01]), cup + np.array([0, 0.0, 0.002])], 0.004, seg=8)
    return bar, grips, ctrl, levers


# ------------------------------------------------------------------ mirrors (on the fairing's mirror blanks)
def mirrors():
    housing, glass = SD.Solid(), SD.Solid()
    surf = FA.load_surface()
    u0, z0 = FA.MIRROR_BLANK
    for sg in (1, -1):
        P = surf.point(sg * u0, z0)
        N = surf.normal(sg * u0, z0)
        foot = P + 0.002 * N
        top = foot + N * 0.040 + np.array([sg * 0.030, 0.010, 0.050])
        SD.sweep(housing, FA.cr_curve([tuple(foot), tuple(foot + N * 0.025 + np.array([0, 0, 0.02])), tuple(top)], closed=False, n=6),
                 SD.rrect(0.009, 0.006, 0.004), up=(0, 1, 0))
        # head: rounded box facing the rider, glass on its rear face
        c = top + np.array([sg * 0.050, 0.012, 0.018])
        ax_side = np.array([sg * 1.0, 0.25 * sg, 0.0])
        ax_side /= np.linalg.norm(ax_side)
        ax_back = np.array([-0.25, 1.0, 0.0]) * np.array([sg, 1, 1])
        ax_back /= np.linalg.norm(ax_back)
        up = np.cross(ax_side, ax_back) * sg
        up = up if up[2] > 0 else -up
        SD.box(housing, c, (0.066, 0.020, 0.032), axes=[ax_side, ax_back, up], r=0.022)
        g = SD.rrect(0.060, 0.026, 0.020)
        pts = np.array([c + ax_back * 0.0205 + a * ax_side + b * up for a, b in g])
        SD.pillow(glass, g, c + ax_back * 0.0195, ax_side, up, 0.0025, 0.001, back=False) if np.cross(ax_side, up) @ ax_back > 0 else \
            SD.pillow(glass, g[:, ::-1], c + ax_back * 0.0195, up, ax_side, 0.0025, 0.001, back=False)
    return housing, glass


# ------------------------------------------------------------------ dash
DASH_C = np.array([0.0, -0.548, 0.965])


def dash():
    housing, screen = SD.Solid(), SD.Solid()
    tilt = math.radians(52)                     # screen leans back toward the rider
    n = np.array([0.0, math.cos(tilt), math.sin(tilt)])   # facing the rider (back and up)
    up = np.array([0.0, -math.sin(tilt), math.cos(tilt)])
    side = np.array([1.0, 0.0, 0.0])
    SD.box(housing, DASH_C - n * 0.016, (0.092, 0.020, 0.060), axes=[side, n, up], r=0.010)
    # sun hood over the top edge
    SD.box(housing, DASH_C + up * 0.058 + n * 0.012, (0.094, 0.016, 0.006), axes=[side, n, up], r=0.004)
    g = SD.rrect(0.080, 0.050, 0.006)
    SD.pillow(screen, g[:, ::-1], DASH_C + n * 0.0035, up, side, 0.0015, 0.0006, back=False)
    # mount stalk down to the top clamp area
    SD.tube(housing, [DASH_C - n * 0.03 - up * 0.04, steer_pt(0.90) + np.array([0, -0.06, 0.01])], 0.007, seg=8)
    return housing, screen


def dash_texture(path, W=512, H=320):
    """Idle dash: dark screen, rev bar outline with a few lit segments, gear and speed blocks (no text)."""
    img = np.zeros((H, W, 3))
    img[:] = (0.035, 0.04, 0.05)
    yy, xx = np.mgrid[0:H, 0:W]
    # rev bar: segments across the top, curving up at the right end
    for k in range(36):
        x0 = 30 + k * 12
        h = 22 + int(18 * max(0, (k - 24) / 11) ** 2)
        y1 = 80
        lit = k < 6
        col = (0.95, 0.95, 0.95) if lit else ((0.85, 0.25, 0.10) if k >= 30 else (0.18, 0.2, 0.24))
        img[(xx >= x0) & (xx < x0 + 9) & (yy >= y1 - h) & (yy < y1)] = col
    # gear box (right) and speed panel (centre) as plain blocks, thin divider lines
    img[(yy >= 110) & (yy < 250) & (xx >= 380) & (xx < 480)] = (0.10, 0.11, 0.13)
    img[(yy >= 140) & (yy < 222) & (xx >= 412) & (xx < 448)] = (0.95, 0.42, 0.14)
    img[(yy >= 140) & (yy < 222) & (xx >= 420) & (xx < 440)] = (0.10, 0.11, 0.13)
    img[(yy >= 96) & (yy < 98) & (xx >= 24) & (xx < 488)] = (0.3, 0.32, 0.36)
    img[(yy >= 270) & (yy < 272) & (xx >= 24) & (xx < 488)] = (0.3, 0.32, 0.36)
    for k in range(6):
        img[(yy >= 284) & (yy < 300) & (xx >= 40 + k * 70) & (xx < 90 + k * 70)] = (0.16, 0.18, 0.22)
    IO.save_png(path, img)


# ------------------------------------------------------------------ front mudguard
def mudguard():
    acc = FA.MeshAcc()
    angs = np.radians(np.linspace(28, 150, 40))
    xs = np.linspace(-1, 1, 15)
    P = np.zeros((len(angs), len(xs), 3))
    for i, a in enumerate(angs):
        for j, s in enumerate(xs):
            skirt = max(0.0, (abs(s) - 0.6) / 0.4)
            rr = 0.326 - 0.020 * skirt ** 1.5
            P[i, j] = FRONT_AXLE + np.array([0.064 * s * (1 - 0.08 * skirt), rr * math.cos(a), rr * math.sin(a)])

    def out_hint(Q, N):
        rad = Q - FRONT_AXLE
        rad[..., 0] = 0
        return np.sum(rad * N, -1) > 0
    FA.grid_shell(acc, P, 0.0025, out_hint, rim_k=4)
    tabs = SD.Solid()
    for sg in (1, -1):
        # side fins down to the fork legs
        a0, a1 = math.radians(70), math.radians(108)
        pts = []
        for a in np.linspace(a0, a1, 8):
            pts.append((FRONT_AXLE[1] + 0.312 * math.cos(a), FRONT_AXLE[2] + 0.312 * math.sin(a)))
        foot = fork_pt(sg * FORK_X, 0.43)
        pts += [(foot[1] + 0.03, foot[2] + 0.01), (foot[1] - 0.02, foot[2] - 0.01)]
        L = np.array(pts)
        if sg > 0:
            SD.pillow(tabs, L, (0.060, 0, 0), (0, 1, 0), (0, 0, 1), 0.026, 0.003)
        else:
            SD.pillow(tabs, L[:, ::-1], (-0.060, 0, 0), (0, 0, 1), (0, 1, 0), 0.026, 0.003)
    return acc, tabs


# ------------------------------------------------------------------ build
LOOKS = {
    "ForkOuter": IO.L_col((200, 160, 70), 0.22, metal=1.0, mat="Metal", refl=0.3),
    "ForkInner": IO.L_col((52, 52, 58), 0.15, metal=1.0, mat="Metal", refl=0.25),
    "ForkFeet": IO.L_col((30, 31, 34), 0.35, metal=1.0, mat="Metal", refl=0.1),
    "TopClamp": IO.L_col((170, 173, 180), 0.25, metal=1.0, mat="Metal", refl=0.2),
    "BottomClamp": IO.L_col((34, 35, 38), 0.35, metal=1.0, mat="Metal", refl=0.1),
    "Bars": IO.L_col((28, 29, 32), 0.3, metal=1.0, mat="Metal", refl=0.1),
    "Grips": IO.L_col((22, 22, 24), 0.85, mat="Rubber"),
    "Controls": IO.L_col((26, 27, 30), 0.45),
    "Levers": IO.L_col((180, 183, 190), 0.25, metal=1.0, mat="Metal", refl=0.2),
    "MirrorHousings": IO.L_col((24, 25, 28), 0.4, refl=0.05),
    "MirrorGlass": IO.L_col((205, 215, 225), 0.02, metal=1.0, mat="Glass", refl=0.7),
    "DashHousing": IO.L_col((20, 20, 22), 0.55),
    "DashScreen": IO.L_tex("DashScreen", 0.1, refl=0.1, coat=0.0),
    "Mudguard": IO.L_col(IO.CHAR, 0.28, refl=0.06, coat=0.4),
    "MudguardFins": IO.L_col((24, 25, 28), 0.5),
}
TEXFILES = {"DashScreen": "DashScreen_Color.png"}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    s = {}
    s["ForkOuter"], s["ForkInner"], s["ForkFeet"] = forks()
    s["TopClamp"], s["BottomClamp"] = clamps()
    s["Bars"], s["Grips"], s["Controls"], s["Levers"] = bars()
    s["MirrorHousings"], s["MirrorGlass"] = mirrors()
    s["DashHousing"], s["DashScreen"] = dash()
    mg, fins = mudguard()
    s["MudguardFins"] = fins
    parts = {name: sol.obj(name, 40) for name, sol in s.items()}
    parts["Mudguard"] = mg.obj("Mudguard")
    # dash screen UV: planar over the screen rectangle
    ob = parts["DashScreen"]
    tilt = math.radians(52)
    up = np.array([0.0, -math.sin(tilt), math.cos(tilt)])
    uvl = ob.data.uv_layers[0].data
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            co = np.array(ob.data.vertices[ob.data.loops[li].vertex_index].co) - DASH_C
            uvl[li].uv = (0.5 + co[0] / 0.16, 0.5 + (co @ up) / 0.10)
    dash_texture(os.path.join(TEX, TEXFILES["DashScreen"]))
    IO.apply_materials(parts, LOOKS, TEXFILES, TEX)
    return parts


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = build()
    IO.export_model(MODEL, parts, LOOKS, TEXFILES, credit=None)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
