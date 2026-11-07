"""Public parking lot round Ironwood Arms (east of the gun shop and behind it), thread "Fill city
with buildings and street props", 2026-11-07 (Dev: "parking spots and etc to fill spots").

  python3 tools/cityfill_textures.py fuel        (LotSigns)
  blender --background --python build_lot.py -- OUT_DIR [--no-render]

Built in WORLD coordinates (placed at the origin, like the Park). An L-shaped asphalt lot:
  east arm   x -429.5..-369.5, z -92..92: a two-way aisle from Vault Ave through to Back St with a
             row of stalls on each side
  back arm   x -530.4..-429.5, z 1.7..92: behind the gun shop, two rows of stalls off an aisle
             that joins the east arm, a planted strip with trees along Back St
Painted stalls, wheel stops, kerbs, lot lights, pay machine, P signs, bins, bollards.
"""
import json, math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import build_street as BS  # noqa: E402
from kit import Kit, M  # noqa: E402

A = BS.A
Y0 = 0.3
rng = random.Random(9)
K = Kit("LotParking", os.path.join(A["out"], "LotParking"), BS.TEX)
for name, sheet, tile in (("Asphalt", "LotAsphalt", (6 * M, 6 * M)), ("Pave", "Plinth", (3 * M, 3 * M)),
                          ("Bin", "BinGreen", (1 * M, 1 * M)), ("AcBody", "HvacGrey", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
K.mat("LotSigns", sheet="LotSigns", explicit=True)
for name, col, rough, metal, emit in (("Dark", (0.06, 0.06, 0.07), 0.5, 0.3, 0), ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Yellow", (0.95, 0.72, 0.08), 0.6, 0, 0), ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0),
                                      ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0), ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0),
                                      ("Steel", (0.55, 0.56, 0.58), 0.35, 1.0, 0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)


def B(part, x0, x1, z0, z1, h0, h1):
    """Roblox x/z (studs), h above the lot surface."""
    K.boxr(part, -x1, -x0, z0, z1, Y0 + h0, Y0 + h1)


def W(x, z, h):
    return (-x, z, Y0 + h)


E0, E1 = -429.5, -369.5                 # east arm
BX0, BZ0 = -530.4, 1.7                  # back arm (x BX0..E0, z BZ0..92)
Z0, Z1 = -92.0, 92.0
L = 0.012 * M                           # paint thickness
# ---------------------------------------------------------------- slab + kerbs
B("Asphalt", E0, E1, Z0, Z1, -1.5, 0)
B("Asphalt", BX0, E0, BZ0, Z1, -1.5, 0)
DR = (-418.0, -381.0)                   # drives on both streets (aisle x range)
for z0, z1 in ((Z0, Z0 + 1.0), (Z1 - 1.0, Z1)):
    for x0, x1 in ((E0, DR[0]), (DR[1], E1)):
        B("Pave", x0, x1, z0, z1, 0, 0.5)
B("Pave", E1 - 1.0, E1, Z0 + 1.0, Z1 - 1.0, 0, 0.5)                              # east kerb
B("Pave", E0, E0 + 1.0, Z0 + 1.0, BZ0, 0, 0.5)                                   # along the gun shop's east side
B("Pave", BX0, BX0 + 1.0, BZ0, Z1, 0, 0.5)                                       # west kerb (gas station side)


def stalls_z(x0, x1, z0, n, w, stop_x):
    """n stalls stacked along z, lines running x0..x1, wheel stops at stop_x."""
    for i in range(n + 1):
        z = z0 + i * w
        K.boxr("LotLine", -x1, -x0, z - 0.2, z + 0.2, Y0, Y0 + L)
    for i in range(n):
        z = z0 + (i + 0.5) * w
        B("Pave", stop_x - 0.5, stop_x + 0.5, z - 3.0, z + 3.0, 0, 0.45)


def stalls_x(x0, n, w, z0, z1, stop_z):
    for i in range(n + 1):
        x = x0 + i * w
        K.boxr("LotLine", -(x + 0.2), -(x - 0.2), z0, z1, Y0, Y0 + L)
    for i in range(n):
        x = x0 + (i + 0.5) * w
        B("Pave", x - 3.0, x + 3.0, stop_z - 0.5, stop_z + 0.5, 0, 0.45)


# east arm: stalls on both sides of the aisle (x -411..-387)
stalls_z(E0 + 1.0, -411.0, -80.0, 7, 9.0, E0 + 2.6)                              # west row, south half (by the gun shop)
stalls_z(-387.0, E1 - 1.0, -80.0, 17, 9.0, E1 - 2.6)                             # east row, full length
stalls_z(E0, -411.0, 46.0, 5, 9.0, E0 + 2.0)                                     # west row, north of the back aisle
# back arm: aisle z 21..45, stalls nose-in on both sides
stalls_x(BX0 + 4.0, 10, 9.0, BZ0 + 1.0, 20.0, BZ0 + 2.6)                         # by the gun shop's back wall
stalls_x(BX0 + 4.0, 10, 9.0, 46.0, 64.0, 62.4)
# centre line + arrows on the through aisle
for z in range(-84, 86, 12):
    K.boxr("LotLine", 399.2, 399.8, z, z + 6, Y0, Y0 + L)
for (az, d) in ((-80.0, 1), (80.0, -1)):
    for ax in (-405.0, -393.0):
        dd = d if ax > -399 else -d
        B("LotLine", ax - 0.3, ax + 0.3, az - 3.0, az + 3.0, 0, 0.012 * M)
        K.quad("LotLine", [W(ax - 1.8, az + dd * 3.0, 0.012 * M), W(ax + 1.8, az + dd * 3.0, 0.012 * M), W(ax, az + dd * 6.0, 0.012 * M)][::-dd])
# planted strip along Back St with trees (props model), low hedge kerb
B("Pave", BX0 + 1.0, E0, 66.0, 67.0, 0, 0.5)
B("Soil", BX0 + 1.0, E0, 67.0, Z1 - 1.0, 0, 0.45)
for k in range(14):
    K.shrub(-(BX0 + 5 + k * 7.0), 72.0 + (k % 2) * 6, Y0 + 0.45, rng.uniform(2.6, 3.4), rng)
B("Pave", BX0, E0, Z1 - 1.0, Z1, 0, 0.5)                                         # (kerb along Back St)
# lot lights
for (x, z) in ((-373.0, -53.0), (-373.0, 1.0), (-373.0, 55.0), (-500.0, 76.0), (-460.0, 76.0)):        # off the aisles
    B("Pave", x - 1.0, x + 1.0, z - 1.0, z + 1.0, 0, 1.6)
    K.cyl("Dark", W(x, z, 14.0), 0.35, 25.0, segs=8)
    for s in (-1, 1):
        B("Dark", x + s * 0.2, x + s * 3.2, z - 0.25, z + 0.25, 26.0, 26.5)
        K.lamp(W(x + s * 2.6, z, 25.9), (2.0, 1.0, 0.15))
# pay machine + P signs at both entrances
for (x, z, side) in ((-421.0, -86.0, -1), (-378.0, 86.0, 1)):
    B("Dark", x - 0.6, x + 0.6, z - 0.4, z + 0.4, 0, 0.3)
    B("AcBody", x - 0.5, x + 0.5, z - 0.35, z + 0.35, 0.3, 5.2)
    B("Yellow", x - 0.52, x + 0.52, z - 0.37, z + 0.37, 5.2, 5.6)
    px = x + side * 3.5
    K.cyl("Steel", W(px, z, 5.0), 0.15, 10.0, segs=8)
    for s in (-1, 1):                                                            # both faces of the P sign
        zz = z + s * 0.08
        cs = [W(px - 2.2, zz, 6.0), W(px + 2.2, zz, 6.0), W(px + 2.2, zz, 10.4), W(px - 2.2, zz, 10.4)]
        uv = ((0, 0), (1, 0), (1, 1), (0, 1))
        K.quad("LotSigns", cs if s < 0 else [cs[1], cs[0], cs[3], cs[2]], uv)
    B("Dark", px - 2.25, px + 2.25, z - 0.06, z + 0.06, 6.0, 10.4)
# bollards along the gun shop side + bins
for z in range(-80, 0, 10):
    K.cyl("Yellow", W(E0 + 0.5, z, 1.75), 0.35, 2.5, segs=10)
for (x, z) in ((-372.5, -86.0), (-372.5, 80.0), (-470.0, 70.0)):
    K.cyl("Bin", W(x, z, 1.6), 1.0, 3.2, segs=12)

K.finish()
meta = K.export()
meta["driveways"] = [[-DR[0], -DR[1], "N"], [-DR[0], -DR[1], "S"]]    # world model at the origin: blender x = -Roblox x
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)
if A["render"]:
    K.render_setup(A["samples"], A["res"])
    K.shot("overview", W(-330, -150, 90), W(-440, 10, 0), lens=26)
    K.shot("back", W(-540, 120, 40), W(-460, 30, 0), lens=26)
