"""Lindell Park + Lindell Skate Park on the block north of Vault Avenue, west of the brick blocks
(original design, thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py park
  blender --background --python build_park.py -- OUT_DIR [--no-render] [--samples N] [--res F]

Builds two models in WORLD coordinates (placed at the origin, like the street models):
  Park       lawn, low stone wall + iron fence, paths, fountain plaza, playground (play tower,
             slide, swings, seesaw), picnic tables, park lamps, entrance signs; skate park: a
             open concrete plaza (low steel-edged ledges) with a half-pipe, two quarter pipes, a funbox with ledge
             and rail, a stair set with handrail and hubba, a pyramid, a grind rail, a manual pad,
             flood lights and a bleacher. Collision from the mesh (ramps become height fields).
  ParkProps  shade trees, benches and bins from build_street.py (hand collision boxes).
"""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402  (its __main__ guard keeps it from building streets)
from kit import Kit, M  # noqa: E402
from mathutils import Vector  # noqa: E402

A = BS.A
rng = random.Random(42)
OX, OZ, Y0 = -463.0, -312.0, 0.3          # park centre (Roblox x, z) and lot level (Roblox y)
HU, HV = 167.0, 134.0                      # half size in studs: u = Roblox +x, v = Roblox +z (v+ = Vault Ave side)


def P(u, v, h=0.0):
    """Park-local (u, v studs, h studs above the lot) -> Blender world."""
    return (-(OX + u), OZ + v, Y0 + h)


K = Kit("Park", os.path.join(A["out"], "Park"), BS.TEX)


def B(part, u0, u1, v0, v1, h0, h1, mat=None):
    K.boxr(part, -(OX + u1), -(OX + u0), OZ + v0, OZ + v1, Y0 + h0, Y0 + h1, mat=mat)


def C(part, u, v, h, r, d, segs=12, r2=None, mat=None):
    K.cyl(part, P(u, v, h), r, d, segs=segs, r2=r2, mat=mat)


def ring(part, u, v, h0, h1, r_in, r_out, segs=32):
    """Closed annulus (hollow cylinder) round (u, v) from h0 to h1."""
    bm = K.bm(part)
    vs = []
    for k in range(segs):
        a = k / segs * math.tau
        c, s_ = math.cos(a), math.sin(a)
        vs.append([bm.verts.new(P(u + c * r, v + s_ * r, h)) for r, h in ((r_in, h0), (r_out, h0), (r_out, h1), (r_in, h1))])
    for k in range(segs):
        A, Bq = vs[k], vs[(k + 1) % segs]
        for j in range(4):
            bm.faces.new((A[j], Bq[j], Bq[(j + 1) % 4], A[(j + 1) % 4]))


def prism(part, prof, w0, w1, axis="v", base=0.12):
    """Solid ramp: each segment of the profile [(t, h), ...] becomes a closed slice down to base,
    extruded across w0..w1 (axis "v": t runs along v, w along u; axis "u": the other way round).
    Closed solids keep their normals right, so no see-through faces."""
    F = (lambda w, t, h: P(w, t, h)) if axis == "v" else (lambda w, t, h: P(t, w, h))
    for (ta, ha), (tb, hb) in zip(prof, prof[1:]):
        if abs(tb - ta) < 1e-3:
            continue
        bm = K.bm(part)
        q = [bm.verts.new(F(w, t, h)) for w in (w0, w1) for (t, h) in ((ta, ha), (tb, hb), (tb, base), (ta, base))]
        for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            bm.faces.new([q[i] for i in f])


def disc(part, u, v, r, h, segs=32, scale=8.0):
    bm = K.bm(part)
    uvl = bm.loops.layers.uv.active
    for i in range(segs):
        a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
        q = [(0, 0), (r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1))]
        f = bm.faces.new([bm.verts.new(P(u + du, v + dv, h)) for du, dv in q])
        for l, (du, dv) in zip(f.loops, q):
            l[uvl].uv = (du / scale, dv / scale)


def sheet_rev(part, u, v, r0, h0, r1, h1, segs=32, urep=6, vrep=1.0, both=True):
    """Surface of revolution between two rings (falling water curtains, ripple bands), UV u round, v down."""
    for side in ((1, -1) if both else (1,)):
        for i in range(segs):
            a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
            p = [P(u + r0 * math.cos(a0), v + r0 * math.sin(a0), h0), P(u + r0 * math.cos(a1), v + r0 * math.sin(a1), h0),
                 P(u + r1 * math.cos(a1), v + r1 * math.sin(a1), h1), P(u + r1 * math.cos(a0), v + r1 * math.sin(a0), h1)]
            uv = [(i / segs * urep, 0), ((i + 1) / segs * urep, 0), ((i + 1) / segs * urep, vrep), (i / segs * urep, vrep)]
            if side < 0:
                p, uv = p[::-1], uv[::-1]
            K.quad(part, p, uv)


def R(part, a, b, r, segs=8, mat=None):
    K.cyl_along(part, P(*a), P(*b), r, segs=segs, mat=mat)


for name, sheet, tile in (("Lawn", "ParkLawn", (3 * M, 3 * M)), ("Plinth", "ParkCap", (2 * M, 2 * M)),
                          ("Pavers", "ParkPavers", (2.4 * M, 2.4 * M)), ("PlazaStone", "PlazaStone", (3 * M, 3 * M)),
                          ("FountainStone", "FountainStone", (2 * M, 2 * M)), ("SkateConcrete", "SkateCrete", (4 * M, 4 * M)),
                          ("MatBark", "ParkMulch", (2 * M, 2 * M)),
                          ("IronBlack", "IronBlack", (1 * M, 1 * M)), ("PoleGalv", "PoleGalv", (1.2 * M, 1.2 * M)),
                          ("PlayRed", "PlayRed", (1 * M, 1 * M)), ("PlayBlue", "PlayBlue", (1 * M, 1 * M)),
                          ("PlayYellow", "PlayYellow", (1 * M, 1 * M)), ("PlayGreen", "PlayGreen", (1 * M, 1 * M)),
                          ("BenchWood", "BenchWood", (1.2 * M, 1.2 * M)), ("StoneTrim", "ParkWall", (2 * M, 2 * M))):
    K.mat(name, sheet=sheet, tile=tile)
K.mat("ParkSigns", sheet="ParkSigns", explicit=True)
K.mat("Light", color=(1.0, 0.95, 0.85), emit=4.0)
# animated fountain water (flipbooks swapped in game by Client/FountainFx, same frames as the estate fountains)
K.mat("FxPool", sheet="FxPool", explicit=True, rough=0.05)
K.mat("FxFall", sheet="FxFall", explicit=True, alpha=True, rough=0.05)
K.mat("FxRipple", sheet="FxRipple", explicit=True, alpha=True, rough=0.05)
K.mat("Steel", color=(0.62, 0.63, 0.64), rough=0.3, metal=1.0)

# ---------------------------------------------------------------- ground, edge wall, fence
# the lot runs right up to the Vault Ave sidewalk (z -172) and the city's west edge (x -640), so no bare
# strips are left round it
U0, U1, V0, V1 = -177.0, HU, -HV, 140.0
B("Lawn", U0, U1, V0, V1 + 0.1, -1.0 * M, 0)
GATES_FRONT = ((-100, -80), (70, 92))                 # u ranges of the two entrances on the Vault Ave side


def wall_run(u0, v0, u1, v1, pillars=True):
    """Low exposed-aggregate wall from (u0,v0) to (u1,v1) (axis aligned) with a concrete cap and
    square pillars every ~24 studs. No railings: thin bars shimmer at a distance in Roblox."""
    if v0 == v1:
        B("StoneTrim", min(u0, u1), max(u0, u1), v0 - 0.7, v0 + 0.7, -0.3, 2.4)
        B("Plinth", min(u0, u1) - 0.2, max(u0, u1) + 0.2, v0 - 0.95, v0 + 0.95, 2.4, 2.9)
    else:
        B("StoneTrim", u0 - 0.7, u0 + 0.7, min(v0, v1), max(v0, v1), -0.3, 2.4)
        B("Plinth", u0 - 0.95, u0 + 0.95, min(v0, v1) - 0.2, max(v0, v1) + 0.2, 2.4, 2.9)
    if not pillars:
        return
    L = abs(u1 - u0) + abs(v1 - v0)
    n = max(1, round(L / 24))
    for i in range(n + 1):
        t = i / n
        u, v = u0 + (u1 - u0) * t, v0 + (v1 - v0) * t
        B("StoneTrim", u - 1.3, u + 1.3, v - 1.3, v + 1.3, -0.3, 4.6)
        B("Plinth", u - 1.6, u + 1.6, v - 1.6, v + 1.6, 4.6, 5.1)


# front (Vault Ave side): split at the two entrances
cuts = [U0] + [x for g in GATES_FRONT for x in g] + [U1]
for i in range(0, len(cuts), 2):
    wall_run(cuts[i] + (1.8 if i else 0), V1 - 1.0, cuts[i + 1] - (1.8 if i + 2 < len(cuts) else 0), V1 - 1.0)
for a, b in GATES_FRONT:                                                              # gate piers
    for u in (a, b):
        B("StoneTrim", u - 1.8, u + 1.8, V1 - 2.8, V1 + 0.0, -0.3, 7.5)
        B("Plinth", u - 2.1, u + 2.1, V1 - 3.1, V1 + 0.0, 7.5, 8.0)
        K.lamp(P(u, V1 - 1.4, 8.6), (1.6, 1.6, 1.0))
wall_run(U0 + 1.0, V0 + 1.5, U0 + 1.0, V1 - 2.0)
wall_run(U1 - 1.0, V0 + 1.5, U1 - 1.0, V1 - 2.0)
wall_run(U0, V0 + 0.7, U1, V0 + 0.7, pillars=False)                                    # back: the houses' walls are behind


# entrance signs on the front wall
def sign(u, v, w, h, h0, box):
    x0, x1 = -(OX + u - w / 2), -(OX + u + w / 2)
    y = OZ + v
    for yy, cs in ((y + 0.02, [(x0, y + 0.02, Y0 + h0), (x1, y + 0.02, Y0 + h0), (x1, y + 0.02, Y0 + h0 + h), (x0, y + 0.02, Y0 + h0 + h)]),
                   (y - 0.02, [(x1, y - 0.02, Y0 + h0), (x0, y - 0.02, Y0 + h0), (x0, y - 0.02, Y0 + h0 + h), (x1, y - 0.02, Y0 + h0 + h)])):
        u0, v0, u1, v1 = box
        K.quad("ParkSigns", cs, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


B("StoneTrim", -126, -104, V1 - 5.4, V1 - 3.6, -0.3, 2.0)                               # park name sign on a plinth
B("BenchWood", -125, -105, V1 - 4.8, V1 - 4.2, 2.0, 7.8)
sign(-115, V1 - 4.15, 19, 5.4, 2.2, (0, 0.502, 1, 1))
B("PoleGalv", 96, 98, V1 - 6, V1 - 5, 0, 9.5)
B("PoleGalv", 116, 118, V1 - 6, V1 - 5, 0, 9.5)
B("IronBlack", 96, 118, V1 - 5.9, V1 - 5.1, 4.4, 9.4)
sign(107, V1 - 5.95, 21.4, 4.8, 4.5, (0, 0, 1, 0.498))

# ---------------------------------------------------------------- paths + fountain plaza (park half, u < 0)
FX, FV = -90.0, 5.0
# walks: herringbone pavers 0.12 proud of the lawn; the plaza sits higher again (no shared tops)
B("Pavers", -95, -85, 30, V1 - 0.6, 0, 0.12)                                           # entrance walk to the plaza
B("Pavers", U0 + 2, -52, FV - 5, FV + 5, 0, 0.12)                                       # east-west promenade
B("Pavers", -52, 6.0, FV - 5, FV + 5, 0, 0.12)                                        # (stops at the skate pad)
B("Pavers", 70, 92, 108.0, V1 - 0.6, 0, 0.12)                                           # skate park entrance walk
B("Pavers", -95, -85, V0 + 2, -30, 0, 0.12)                                             # north walk
C("Plinth", FX, FV, 0.06, 38.6, 0.28, segs=48)                                          # plaza kerb ring (top 0.20)
C("PlazaStone", FX, FV, 0.13, 37.8, 0.26, segs=48)                                      # plaza slabs (top 0.26)
# fountain: travertine basin with a cap, water, centre column with two bowls
C("FountainStone", FX, FV, 0.45, 16.0, 0.7, segs=40)                                   # basin floor
ring("FountainStone", FX, FV, 0.1, 2.5, 15.6, 17.0, segs=40)                            # basin wall
ring("FountainStone", FX, FV, 2.5, 3.0, 15.3, 17.6, segs=40)                            # sitting cap
disc("FxPool", FX, FV, 15.62, 2.0, segs=40, scale=10.0)                                 # basin water
C("FountainStone", FX, FV, 4.2, 2.2, 4.6, segs=20)
C("FountainStone", FX, FV, 6.2, 7.0, 0.7, segs=32, r2=4.2)
disc("FxPool", FX, FV, 6.5, 6.6, segs=32, scale=5.0)
C("FountainStone", FX, FV, 8.2, 1.3, 3.4, segs=16)
C("FountainStone", FX, FV, 9.9, 3.6, 0.55, segs=24, r2=2.0)
disc("FxPool", FX, FV, 3.3, 10.22, segs=24, scale=3.0)
sheet_rev("FxFall", FX, FV, 7.05, 6.6, 7.7, 2.02, segs=40, urep=12, vrep=2.0)            # curtain off the big bowl
sheet_rev("FxFall", FX, FV, 3.65, 10.22, 4.1, 6.62, segs=24, urep=7, vrep=1.6)           # off the top bowl
sheet_rev("FxFall", FX, FV, 0.12, 13.4, 0.05, 10.22, segs=8, urep=1, vrep=1.0)           # jet
sheet_rev("FxRipple", FX, FV, 7.6, 2.04, 10.5, 2.04, segs=40, urep=10, vrep=1.0, both=False)
sheet_rev("FxRipple", FX, FV, 4.0, 6.64, 5.6, 6.64, segs=24, urep=6, vrep=1.0, both=False)

# ---------------------------------------------------------------- playground (south-west lawn)
PU, PV = -135.0, 80.0
B("StoneTrim", PU - 22, PU + 22, PV - 18, PV + 18, -0.3, 0.6)                          # kerb
B("MatBark", PU - 21, PU + 21, PV - 17, PV + 17, 0.6, 0.7)
# play tower: 4 posts, deck, roof, slide off one side, ladder on the other
tu, tv = PU - 6, PV - 2
for du in (-4, 4):
    for dv in (-4, 4):
        B("PlayBlue", tu + du - 0.4, tu + du + 0.4, tv + dv - 0.4, tv + dv + 0.4, 0.7, 13.5)
B("PlayYellow", tu - 4.6, tu + 4.6, tv - 4.6, tv + 4.6, 5.5, 6.0)
for s in (-1, 1):
    B("PlayGreen", tu - 4.4, tu + 4.4, tv + s * 4.4 - 0.15, tv + s * 4.4 + 0.15, 6.0, 9.0)
B("PlayGreen", tu - 4.55, tu - 4.25, tv - 4.4, tv + 4.4, 6.0, 9.0)
K.quad("PlayRed", [P(tu - 5.2, tv - 5.2, 13.5), P(tu + 5.2, tv - 5.2, 13.5), P(tu, tv, 17.0)])
K.quad("PlayRed", [P(tu + 5.2, tv - 5.2, 13.5), P(tu + 5.2, tv + 5.2, 13.5), P(tu, tv, 17.0)])
K.quad("PlayRed", [P(tu + 5.2, tv + 5.2, 13.5), P(tu - 5.2, tv + 5.2, 13.5), P(tu, tv, 17.0)])
K.quad("PlayRed", [P(tu - 5.2, tv + 5.2, 13.5), P(tu - 5.2, tv - 5.2, 13.5), P(tu, tv, 17.0)])
K.quad("PlayRed", [P(tu - 5.2, tv - 5.2, 13.5), P(tu - 5.2, tv + 5.2, 13.5), P(tu + 5.2, tv + 5.2, 13.5), P(tu + 5.2, tv - 5.2, 13.5)])
# slide: from the deck edge (u+) down to the mat, a sloped bed with side walls
s0, s1 = tu + 4.6, tu + 17
for i in range(12):
    a, b = i / 12, (i + 1) / 12
    za = 5.9 - 5.0 * (a * a * (3 - 2 * a))
    zb = 5.9 - 5.0 * (b * b * (3 - 2 * b))
    ua, ub = s0 + (s1 - s0) * a, s0 + (s1 - s0) * b
    K.quad("PlayYellow", [P(ua, tv - 1.4, za), P(ua, tv + 1.4, za), P(ub, tv + 1.4, zb), P(ub, tv - 1.4, zb)])
    K.quad("PlayYellow", [P(ub, tv - 1.4, zb - 0.25), P(ub, tv + 1.4, zb - 0.25), P(ua, tv + 1.4, za - 0.25), P(ua, tv - 1.4, za - 0.25)])
    for s in (-1, 1):
        R("PlayYellow", (ua, tv + s * 1.5, za + 0.6), (ub, tv + s * 1.5, zb + 0.6), 0.2, segs=6)
for i in range(6):                                                                    # ladder on the u- side
    B("PlayBlue", tu - 5.6, tu - 4.6, tv - 1.4, tv + 1.4, 1.2 + i * 0.9, 1.4 + i * 0.9)
# swing set: A-frames + top bar + 3 seats on chains
su, sv = PU + 15, PV + 9.5
for dv in (-7, 7):
    for du in (-2.6, 2.6):
        R("PlayRed", (su + du, sv + dv, 0.7), (su, sv + dv, 10.5), 0.3, segs=8)
R("PlayRed", (su, sv - 7.3, 10.5), (su, sv + 7.3, 10.5), 0.35, segs=10)
for dv in (-4.0, 0, 4.0):
    for s in (-0.9, 0.9):
        R("Steel", (su, sv + dv + s, 10.3), (su, sv + dv + s, 3.2), 0.06, segs=4)
    B("IronBlack", su - 0.8, su + 0.8, sv + dv - 1.1, sv + dv + 1.1, 3.0, 3.2)
# seesaw
SSU, SSV = PU + 14, PV - 10
B("PlayBlue", SSU - 0.6, SSU + 0.6, SSV - 0.6, SSV + 0.6, 0.7, 2.6)
B("PlayYellow", SSU - 0.5, SSU + 0.5, SSV - 6, SSV + 6, 2.6, 2.9)
for dv in (-5, 5):
    B("PlayRed", SSU - 0.15, SSU + 0.15, SSV + dv - 0.15, SSV + dv + 0.15, 2.9, 4.2)
# walk from the promenade to the playground
B("Pavers", PU + 15, PU + 23, FV + 5, PV - 18, 0, 0.1)

# ---------------------------------------------------------------- picnic tables
for (u, v) in ((-40, 60), (-52, 90), (-150, -50), (-120, -80), (-40, -70)):
    B("BenchWood", u - 4, u + 4, v - 1.6, v + 1.6, 2.6, 2.85)                                        # top
    for dv in (-2.8, 2.8):
        B("BenchWood", u - 4, u + 4, v + dv - 0.55, v + dv + 0.55, 1.5, 1.7)                         # seats
    for du in (-3, 3):
        R("IronBlack", (u + du, v - 3.2, 0), (u + du, v, 2.6), 0.12, segs=6)
        R("IronBlack", (u + du, v + 3.2, 0), (u + du, v, 2.6), 0.12, segs=6)
        B("IronBlack", u + du - 0.1, u + du + 0.1, v - 3.2, v + 3.2, 1.35, 1.5)

# ---------------------------------------------------------------- park lamps along the walks
LAMPS = [(-100, 110), (-80, 70), (-100, 40), (-140, 13), (-50, 13), (-10, -3), (40, 13), (66, 40), (96, 100), (-80, -60),
         (-100, -110)]
for (u, v) in LAMPS:
    C("IronBlack", u, v, 0.5, 0.7, 1.0, segs=10, r2=0.5)
    C("IronBlack", u, v, 6.5, 0.25, 12.0, segs=8)
    C("IronBlack", u, v, 12.7, 0.9, 0.4, segs=8)
    C("LightLantern", u, v, 14.0, 0.85, 2.3, segs=8, r2=0.95, mat="Light")
    C("IronBlack", u, v, 15.5, 1.3, 0.6, segs=8, r2=0.2)
    K.lamp(P(u, v, 12.95), (1.0, 1.0, 0.1))

# ---------------------------------------------------------------- skate park (u 5..160)
SU0, SU1, SV0, SV1 = 6.0, 160.0, -112.0, 108.0
B("SkateConcrete", SU0, SU1, SV0, SV1, -0.3, 0.12)
SG = (70, 92)                                                                           # opening toward the Vault Ave walk
# open plaza like a city skate park: a low concrete ledge round the pad (skateable, steel edge),
# open where the walks come in (no chain-link: its fine mesh shimmered)


def ledge(u0, u1, v0, v1, h=1.6):
    B("SkateConcrete", u0, u1, v0, v1, 0.12, h)
    if u1 - u0 > v1 - v0:
        B("Steel", u0, u1, v0 - 0.04, v0 + 0.3, h - 0.3, h + 0.04)
        B("Steel", u0, u1, v1 - 0.3, v1 + 0.04, h - 0.3, h + 0.04)
    else:
        B("Steel", u0 - 0.04, u0 + 0.3, v0, v1, h - 0.3, h + 0.04)
        B("Steel", u1 - 0.3, u1 + 0.04, v0, v1, h - 0.3, h + 0.04)


ledge(SU0, SU1, SV0, SV0 + 1.4)
ledge(SU1 - 1.4, SU1, SV0 + 1.5, SV1)
ledge(SU0, SU0 + 1.4, SV0 + 1.5, FV - 5.5)
ledge(SU0, SU0 + 1.4, FV + 5.5, SV1)
ledge(SU0 + 1.5, SG[0], SV1 - 1.4, SV1)
ledge(SG[1], SU1 - 1.5, SV1 - 1.4, SV1)


def ramp(profile, u0, u1, part="SkateConcrete", coping=True, axis="v"):
    """Solid ramp from a profile, with a steel coping pipe on its top lip."""
    prism(part, profile, u0, u1, axis=axis)
    if coping:
        F = (lambda w, t, h: P(w, t, h)) if axis == "v" else (lambda w, t, h: P(t, w, h))
        tl, hl = max(profile, key=lambda p: p[1])
        K.cyl_along("Steel", F(u0, tl, hl + 0.05), F(u1, tl, hl + 0.05), 0.25, segs=10)


def transition(t0, direction, R_, H, deck, n=16):
    """Quarter-pipe profile starting flat at t0 going `direction` (+1/-1): circular transition of
    radius R_ up to height H, then a flat deck."""
    pts = [(t0, 0.12)]
    ang = math.acos(max(-1.0, min(1.0, (R_ - H) / R_)))
    for i in range(1, n + 1):
        a = ang * i / n
        pts.append((t0 + direction * R_ * math.sin(a), 0.12 + R_ * (1 - math.cos(a))))
    tt = pts[-1][0]
    pts.append((tt + direction * deck, pts[-1][1]))
    return pts if direction > 0 else pts[::-1]


# half-pipe across the north end: two quarter pipes facing each other with a flat bottom
HP_U0, HP_U1 = 20.0, 70.0
ramp(transition(-80, -1, 14, 11, 7), HP_U0, HP_U1)
ramp(transition(-60, 1, 14, 11, 7), HP_U0, HP_U1)
for t in (-100.3, -39.7):                                                              # railings on the back edge of each deck
    B("PoleGalv", HP_U0, HP_U1, t - 0.15, t + 0.15, 14.6, 15.0)
    for u in range(int(HP_U0), int(HP_U1) + 1, 10):
        B("PoleGalv", u - 0.2, u + 0.2, t - 0.2, t + 0.2, 11.1, 15.0)
# quarter pipes on the east wall, facing west
ramp(transition(140, 1, 10, 7, 5), -60, -10, axis="u")
ramp(transition(140, 1, 10, 7, 5), 20, 70, axis="u")
# funbox: flat top with kicker banks at both ends, steel ledge edge, flat rail on top
FU0, FU1, FV0, FV1 = 60.0, 84.0, -20.0, -6.0
B("SkateConcrete", FU0, FU1, FV0, FV1, 0.12, 3.0)
B("Steel", FU0, FU1, FV1 - 0.4, FV1 + 0.05, 2.7, 3.05)
prism("SkateConcrete", [(FU0 - 12, 0.12), (FU0, 3.0)], FV0, FV1, axis="u")                  # kicker banks
prism("SkateConcrete", [(FU1, 3.0), (FU1 + 12, 0.12)], FV0, FV1, axis="u")
B("Steel", FU0 + 3, FU1 - 3, (FV0 + FV1) / 2 - 0.15, (FV0 + FV1) / 2 + 0.15, 4.9, 5.2)
for u in (FU0 + 4, FU1 - 4):
    B("Steel", u - 0.15, u + 0.15, (FV0 + FV1) / 2 - 0.12, (FV0 + FV1) / 2 + 0.12, 3.0, 4.9)
# stair set: raised platform with 4 steps down to the south, handrail in the middle, hubba ledges on both sides
ST_U0, ST_U1, ST_V = 100.0, 132.0, 20.0
B("SkateConcrete", ST_U0, ST_U1, ST_V - 22, ST_V, 0.12, 4.4)                            # platform
for i in range(4):
    B("SkateConcrete", ST_U0 + 6, ST_U1 - 6, ST_V + i * 2.4, ST_V + (i + 1) * 2.4, 0.12, 4.4 - (i + 1) * 1.07)
for u in (ST_U0 + 3, ST_U1 - 3):                                                       # hubba ledges
    prism("SkateConcrete", [(ST_V, 5.6), (ST_V + 9.6, 1.25)], u - 3, u + 3)
    R("Steel", (u + 3.05, ST_V, 5.62), (u + 3.05, ST_V + 9.6, 1.27), 0.15, segs=6)
R("Steel", ((ST_U0 + ST_U1) / 2, ST_V - 2, 7.6), ((ST_U0 + ST_U1) / 2, ST_V + 11, 3.0), 0.2, segs=8)
for (v, h) in ((ST_V - 2, 4.4), (ST_V + 4.6, 2.3), (ST_V + 11, 0.12)):
    B("Steel", (ST_U0 + ST_U1) / 2 - 0.15, (ST_U0 + ST_U1) / 2 + 0.15, v - 0.15, v + 0.15, h, 7.6 - (v - ST_V + 2) * 4.6 / 13)
# bank down the back of the platform
prism("SkateConcrete", [(ST_V - 36, 0.12), (ST_V - 22, 4.4)], ST_U0, ST_U1)
# pyramid: frustum with four banks
PYU, PYV = 34.0, 40.0
w0, w1, hh = 16.0, 6.0, 3.0
C("SkateConcrete", PYU, PYV, 0.12 + hh / 2, w0 * 0.7071 * 2, hh, segs=4, r2=w1 * 0.7071 * 2)
# grind rail + manual pad
R("Steel", (20, 80, 2.0), (55, 80, 2.0), 0.22, segs=10)
for u in (22, 37, 53):
    B("Steel", u - 0.15, u + 0.15, 79.85, 80.15, 0.12, 2.0)
    B("Steel", u - 0.8, u + 0.8, 79.2, 80.8, 0.12, 0.3)
B("SkateConcrete", 110, 134, 66, 76, 0.12, 1.0)
B("Steel", 110, 134, 75.7, 76.05, 0.75, 1.05)
# flood lights on the corners + a bleacher outside the west ledge
for (u, v) in ((SU0 + 2, SV0 + 2), (SU1 - 2, SV0 + 2), (SU0 + 2, SV1 - 2), (SU1 - 2, SV1 - 2)):
    C("PoleGalv", u, v, 11, 0.5, 22, segs=10)
    B("PoleGalv", u - 2.2, u + 2.2, v - 0.4, v + 0.4, 21.6, 22.6)
    for du in (-1.4, 1.4):
        K.lamp(P(u + du, v, 21.5), (1.6, 1.6, 0.15))
for k in range(3):
    B("BenchWood", -4.0 - k * 2.6, -1.6 - k * 2.6, -60, -20, 1.2 + k * 1.6, 1.6 + k * 1.6)
    for v in (-58, -40, -22):
        B("IronBlack", -3.0 - k * 2.6, -2.6 - k * 2.6, v - 0.2, v + 0.2, 0, 1.2 + k * 1.6)

K.finish(keep_normals=())
meta = K.export()
meta["driveways"] = []

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    c = Vector(P(0, 0, 0))
    K.shot("overview", tuple(Vector(P(-40, 260, 160))), tuple(c), lens=28)
    K.shot("fountain", tuple(Vector(P(-50, 60, 12))), tuple(Vector(P(FX, FV, 4))), lens=28)
    K.shot("skate", tuple(Vector(P(150, 120, 30))), tuple(Vector(P(70, -20, 0))), lens=26)
    K.shot("halfpipe", tuple(Vector(P(10, -55, 9))), tuple(Vector(P(50, -95, 5))), lens=26)
    K.shot("wall", tuple(Vector(P(-60, 160, 6))), tuple(Vector(P(-140, 135, 2))), lens=30)
    K.shot("playground", tuple(Vector(P(-100, 120, 18))), tuple(Vector(P(PU, PV, 3))), lens=28)

# ---------------------------------------------------------------- ParkProps: trees, benches, bins (build_street props)
S = BS.Street("ParkProps")
S.grate = lambda *a, **k: None                       # trees stand in the lawn, not in sidewalk grates


def prop(kind, u, v, face_u=0.0, face_v=1.0, seed=1):
    return {"kind": kind, "x": OX + u, "z": OZ + v, "y": Y0 + 0.1, "hx": face_u, "hz": face_v, "seed": seed}


props = []
TREES = [(-155, 120), (-150, 40), (-160, -20), (-150, -100), (-125, -120), (-60, -115), (-30, -90), (-15, 40), (-30, 110),
         (-60, 120), (-120, 30), (-55, -35), (-140, -30), (-20, -40), (-5, 95), (-118, 126), (-160, 70)]
for i, (u, v) in enumerate(TREES):
    props.append(prop("Tree", u, v, seed=100 + i))
# benches round the plaza, facing the fountain
for k in range(8):
    a = (k + 0.5) / 8 * math.tau
    if abs(math.sin(a)) > 0.92 or abs(math.cos(a)) > 0.92:
        continue
    u, v = FX + math.cos(a) * 33, FV + math.sin(a) * 33
    props.append(prop("Bench", u, v, -math.cos(a), -math.sin(a), seed=k))
for (u, v, fu, fv) in ((-80, 50, -1, 0), (-80, 95, -1, 0), (-100, 120, 1, 0), (-120, 0, 0, 1), (-40, 0, 0, 1), (20, 0, 0, 1),
                       (75, 60, 1, 0), (-100, -60, 1, 0)):
    props.append(prop("Bench", u, v, fu, fv))
for (u, v) in ((-104, V1 - 8), (66, V1 - 8), (-78, 30), (-20, -8), (96, 30), (-105, -40)):
    props.append(prop("Bin", u, v, 0, 1))
S.build(props)

