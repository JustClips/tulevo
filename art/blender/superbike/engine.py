"""Superbike engine: inline-four crankcase and gearbox, forward-leaning cylinder block and head, cam cover,
alternator cover (left), clutch cover (right), front sprocket cover, airbox under the tank, radiator with
side tanks and hoses.

  /home/user/bvenv/bin/python art/blender/superbike/engine.py      build + export art/models/BikeEngine

Bike coordinates as in wheels.py: +X = bike's LEFT, -Y = front, +Z = up, origin = ground between axles.
Packaged round the parts already built: exhaust ports at y -0.33 z 0.605 on the head's front face, the
collector and box under the crankcase, front sprocket at (0.085, 0.052, 0.375) outboard of the gearbox,
swingarm pivot at y 0.12 behind it, frame spars over the head, radiator between the front tyre and headers.
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
from chassis import side_pillow  # noqa: E402

MODEL = "BikeEngine"
OUT = os.path.join(IO.MODELS, MODEL)
TEX = os.path.join(OUT, "tex")

CRANK = [(-0.318, 0.300), (-0.330, 0.365), (-0.312, 0.432), (-0.200, 0.456), (-0.080, 0.472), (-0.030, 0.490), (-0.020, 0.300),
         (-0.120, 0.284), (-0.240, 0.285)]
GEARBOX = [(-0.050, 0.300), (-0.050, 0.500), (0.020, 0.548), (0.072, 0.560), (0.086, 0.505), (0.086, 0.380), (0.062, 0.312), (0.010, 0.292)]
# cylinder block leaning forward, then the head on top of it (a little wider and longer, so the joint shows)
BLOCK = [(-0.300, 0.420), (-0.318, 0.500), (-0.331, 0.572), (-0.098, 0.572), (-0.072, 0.470), (-0.105, 0.436)]
HEAD = [(-0.337, 0.558), (-0.346, 0.600), (-0.343, 0.648), (-0.124, 0.660), (-0.104, 0.600), (-0.094, 0.558)]
CAM = [(-0.336, 0.640), (-0.326, 0.682), (-0.290, 0.694), (-0.150, 0.697), (-0.120, 0.676), (-0.122, 0.655)]
AIRBOX = [(-0.440, 0.748), (-0.405, 0.842), (-0.300, 0.874), (-0.120, 0.888), (0.000, 0.862), (0.055, 0.800), (0.020, 0.722),
          (-0.120, 0.700), (-0.330, 0.700)]


def halves(sol, outline, w_left, w_right, r):
    side_pillow(sol, outline, 0.0, w_left, r, 1)
    side_pillow(sol, outline, 0.0, w_right, r, -1)


def engine():
    case, head, cam, covers, sprocket_cover, airbox = (SD.Solid() for _ in range(6))
    halves(case, CRANK, 0.135, 0.135, 0.018)
    halves(case, GEARBOX, 0.072, 0.108, 0.014)
    # ribs on the crankcase sides
    for sg in (1, -1):
        for y0, z0, y1, z1 in ((-0.29, 0.32, -0.20, 0.30), (-0.29, 0.36, -0.16, 0.33)):
            L = [(y0, z0), (y1, z1), (y1 + 0.004, z1 + 0.008), (y0 + 0.004, z0 + 0.008)]
            side_pillow(case, L, 0.133, 0.006, 0.002, sg)
    # upper / lower crankcase joint: a thin raised seam along both sides
    for sg in (1, -1):
        side_pillow(case, [(-0.312, 0.398), (-0.036, 0.398), (-0.036, 0.406), (-0.312, 0.406)], 0.130, 0.009, 0.002, sg)
    halves(head, BLOCK, 0.128, 0.128, 0.012)
    halves(head, HEAD, 0.142, 0.142, 0.012)
    # casting ribs across the block sides, following its forward lean
    for sg in (1, -1):
        for z in (0.474, 0.504, 0.534):
            yf = float(np.interp(z, [0.420, 0.500, 0.572], [-0.300, -0.318, -0.331])) + 0.014
            yr = float(np.interp(z, [0.470, 0.572], [-0.072, -0.098])) - 0.014
            side_pillow(head, [(yf, z), (yr, z), (yr, z + 0.007), (yf, z + 0.007)], 0.124, 0.009, 0.002, sg)
    halves(cam, CAM, 0.118, 0.118, 0.010)
    # cam cover bolts along the top
    for y in (-0.31, -0.25, -0.19, -0.14):
        for x in (0.07, -0.07):
            z = float(np.interp(y, [-0.326, -0.290, -0.150, -0.120], [0.682, 0.694, 0.697, 0.676]))
            SD.lathe(covers, [(0.0, -0.002), (0.0065, -0.002), (0.0065, 0.004), (0.0, 0.006)], (x, y, z), (0, 0, 1), seg=6)
    # alternator cover (left) and clutch cover (right): domed discs with a bolt ring
    for c, r, sg, depth in (((-0.115, 0.415), 0.068, 1, 0.026), ((-0.110, 0.490), 0.082, -1, 0.032)):
        base = np.array([sg * 0.132, c[0], c[1]])
        SD.lathe(covers, [(0.0, 0.0), (r, 0.0), (r, depth * 0.45), (r - 0.010, depth * 0.85), (r * 0.55, depth), (0.0, depth * 1.02)],
                 base, (sg, 0, 0), seg=40)
        for k in range(10):
            a = 2 * math.pi * k / 10
            p = base + np.array([sg * depth * 0.42, 0, 0]) + np.array([0, (r - 0.006) * math.cos(a), (r - 0.006) * math.sin(a)])
            SD.lathe(covers, [(0.0, 0.0), (0.0048, 0.0), (0.0048, 0.004), (0.0, 0.005)], p, (sg, 0, 0), seg=6)
        if sg < 0:
            # clutch pressure-plate cap in the middle of the clutch cover, with its own six bolts
            top = base + np.array([sg * depth * 0.95, 0, 0])
            SD.lathe(covers, [(0.0, 0.0), (0.042, 0.0), (0.042, 0.008), (0.036, 0.011), (0.0, 0.012)], top, (sg, 0, 0), seg=32)
            for k in range(6):
                a = 2 * math.pi * k / 6 + 0.3
                p = top + np.array([sg * 0.010, 0, 0]) + np.array([0, 0.030 * math.cos(a), 0.030 * math.sin(a)])
                SD.lathe(covers, [(0.0, 0.0), (0.0042, 0.0), (0.0042, 0.003), (0.0, 0.004)], p, (sg, 0, 0), seg=6)
    # water pump (left, front of the crankcase; the bottom radiator hose ends here) and pickup cover (right)
    SD.lathe(case, [(0.0, 0.0), (0.038, 0.0), (0.038, 0.018), (0.030, 0.026), (0.0, 0.028)], (0.130, -0.285, 0.395), (1, 0, 0), seg=28)
    SD.lathe(covers, [(0.0, 0.0), (0.036, 0.0), (0.036, 0.008), (0.028, 0.014), (0.0, 0.015)], (-0.132, -0.245, 0.345), (-1, 0, 0), seg=28)
    # front sprocket cover (left, outboard of the chain)
    side_pillow(sprocket_cover, [(-0.010, 0.360), (0.010, 0.430), (0.060, 0.448), (0.105, 0.420), (0.112, 0.370), (0.090, 0.322),
                                 (0.040, 0.310)], 0.098, 0.012, 0.004, 1)
    halves(airbox, AIRBOX, 0.104, 0.104, 0.020)
    # throttle-body boots between the airbox and the head
    for x in (-0.105, -0.035, 0.035, 0.105):
        SD.tube(airbox, [(x * 0.95, -0.235, 0.690), (x * 0.95, -0.215, 0.712)], 0.019, seg=12)
    return case, head, cam, covers, sprocket_cover, airbox


# ------------------------------------------------------------------ radiator
RAD_BOT = np.array([0.0, -0.432, 0.500])
RAD_TOP = np.array([0.0, -0.498, 0.762])
RAD_W = 0.188


def radiator():
    core, tanks, hoses = SD.Solid(), SD.Solid(), SD.Solid()
    up = RAD_TOP - RAD_BOT
    H = np.linalg.norm(up)
    up /= H
    side = np.array([1.0, 0, 0])
    fwd = np.cross(up, side)            # normal of the core (pointing forward-ish)
    if fwd[1] > 0:
        fwd = -fwd
    c = (RAD_BOT + RAD_TOP) / 2
    SD.box(core, c, (RAD_W, 0.016, H / 2), axes=[side, fwd, up], r=0.003)
    for sg in (1, -1):
        SD.box(tanks, c + side * sg * (RAD_W + 0.013), (0.014, 0.022, H / 2 + 0.010), axes=[side, fwd, up], r=0.006)
    # filler neck on the right tank, hoses (top: radiator -> head front, bottom: radiator -> water pump on the left)
    SD.lathe(tanks, [(0.0, 0.0), (0.011, 0.0), (0.011, 0.020), (0.016, 0.022), (0.016, 0.030), (0.0, 0.031)],
             RAD_TOP + side * -(RAD_W - 0.03) + up * 0.008, up, seg=12)
    top = FA.cr_curve([(-0.17, -0.488, 0.735), (-0.16, -0.430, 0.735), (-0.13, -0.375, 0.690), (-0.11, -0.340, 0.662)], closed=False, n=6)
    SD.tube(hoses, top, 0.014, seg=12)
    bot = FA.cr_curve([(0.20, -0.440, 0.530), (0.172, -0.400, 0.468), (0.165, -0.348, 0.430), (0.150, -0.312, 0.405)], closed=False, n=6)
    SD.tube(hoses, bot, 0.014, seg=12)
    return core, tanks, hoses, c, side, up, fwd, H


def radiator_texture(path, N=512):
    """Core face: thin bright louvres between dark vertical coolant tubes."""
    img = np.empty((N, N, 3))
    yy, xx = np.mgrid[0:N, 0:N]
    img[:] = (0.07, 0.075, 0.08)
    louvre = (yy % 4) < 1
    img[louvre] = (0.20, 0.21, 0.22)
    tube = (xx % 12) < 3
    img[tube] = (0.035, 0.037, 0.04)
    edge = (xx < 6) | (xx >= N - 6) | (yy < 6) | (yy >= N - 6)
    img[edge] = (0.05, 0.05, 0.055)
    IO.save_png(path, img)


# ------------------------------------------------------------------ build
LOOKS = {
    "Crankcase": IO.L_col((32, 33, 36), 0.45, metal=0.5),
    "CylinderHead": IO.L_col((44, 45, 49), 0.4, metal=0.5),
    "CamCover": IO.L_col((24, 25, 28), 0.3, refl=0.06, coat=0.3),
    "EngineCovers": IO.L_col((150, 153, 160), 0.28, metal=1.0, mat="Metal", refl=0.2),
    "SprocketCover": IO.L_col((20, 20, 22), 0.6),
    "Airbox": IO.L_col((18, 18, 20), 0.7),
    "RadiatorCore": IO.L_tex("RadiatorCore", 0.6, refl=0.0, coat=0.0),
    "RadiatorTanks": IO.L_col((22, 22, 24), 0.5),
    "Hoses": IO.L_col((16, 16, 17), 0.75, mat="Rubber"),
}
TEXFILES = {"RadiatorCore": "RadiatorCore_Color.png"}


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(TEX, exist_ok=True)
    s = {}
    s["Crankcase"], s["CylinderHead"], s["CamCover"], s["EngineCovers"], s["SprocketCover"], s["Airbox"] = engine()
    s["RadiatorCore"], s["RadiatorTanks"], s["Hoses"], c, side, up, fwd, H = radiator()
    parts = {name: sol.obj(name, 40) for name, sol in s.items()}
    # core UV: planar on the face
    ob = parts["RadiatorCore"]
    uvl = ob.data.uv_layers[0].data
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            co = np.array(ob.data.vertices[ob.data.loops[li].vertex_index].co) - c
            uvl[li].uv = (0.5 + (co @ side) / (2 * RAD_W), 0.5 + (co @ up) / H)
    radiator_texture(os.path.join(TEX, TEXFILES["RadiatorCore"]))
    IO.apply_materials(parts, LOOKS, TEXFILES, TEX)
    return parts


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    parts = build()
    IO.export_model(MODEL, parts, LOOKS, TEXFILES, credit=None)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "work.blend"))
