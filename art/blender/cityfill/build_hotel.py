"""Hotel Solana: an eleven-storey 1920s stucco-and-stone hotel with a porte-cochere drop-off
(original design, thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py hotel
  blender --background --python build_hotel.py -- OUT_DIR [--face S] [--no-render] [--samples N] [--res F]

Ground floor: limestone base, tall lobby glass (printed walnut lobby, chandeliers, reception)
between stone piers, brass mullions and a centre door. Porte-cochere: a teal canopy on stone
columns with a lit soffit, fascia sign, valet stand, raised drop-off kerb. Drive loop in from
the street at one end and out at the other around a palm island with the monument sign.
Tower: warm stucco with stone piers between every bay, framed windows, balconies on the
centre bays, belt course and cornice. Corner blade sign HOTEL (red neon edge), roof crown with
the SOLANA sign (cyan neon edge) and red beacons. Back: service door, dock, dumpster.

Lot 46 x 48 m, origin = lot centre, z 0 = lot surface; place at y 0.3. meta "driveways" = both
drives at the front edge.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, M, args, model_name  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\hotel")
NAME = model_name("Hotel", A)
K = Kit(NAME, A["out"], TEX)
rng = random.Random(8)

LX, LY0, LY1 = 23 * M, -24 * M, 24 * M
TX, TY0, TY1 = 17 * M, -2 * M, 20 * M           # tower half width, front, back
GF, FH, NF = 5 * M, 3.3 * M, 10
TOP = GF + NF * FH
DRIVES = ((-21 * M, -14 * M), (14 * M, 21 * M))

for name, sheet, tile in (("Stucco", "HotelStucco", (2 * M, 2 * M)), ("Stone", "StoneTrim", (2 * M, 2 * M)),
                          ("Roof", "RoofTar", (4 * M, 4 * M)), ("Asphalt", "LotAsphalt", (6 * M, 6 * M)),
                          ("Pave", "Plinth", (3 * M, 3 * M)), ("Pavers", "Pavers", (1.5 * M, 1.5 * M)),
                          ("Teal", "HotelTeal", (1 * M, 1 * M)), ("Soffit", "BenchWood", (1.5 * M, 1.5 * M)),
                          ("AcBody", "HvacGrey", (1 * M, 1 * M)), ("Steel", "FireSteel", (1 * M, 1 * M))):
    K.mat(name, sheet=sheet, tile=tile)
for name in ("HotelLobby", "HotelSigns"):
    K.mat(name, sheet=name, explicit=True)
for name, col, rough, metal, emit in (("Brass", (0.72, 0.56, 0.30), 0.3, 1.0, 0), ("Dark", (0.05, 0.05, 0.055), 0.5, 0.3, 0),
                                      ("FrameB", (0.20, 0.17, 0.14), 0.45, 0.2, 0), ("Soil", (0.22, 0.16, 0.11), 1.0, 0, 0),
                                      ("Shrub", (0.16, 0.32, 0.12), 0.9, 0, 0), ("Palm", (0.16, 0.30, 0.10), 0.7, 0, 0),
                                      ("Trunk", (0.40, 0.31, 0.22), 0.95, 0, 0), ("Dumpster", (0.12, 0.30, 0.18), 0.6, 0.4, 0),
                                      ("LotLine", (0.92, 0.92, 0.88), 0.8, 0, 0),
                                      ("Light", (1.0, 0.95, 0.85), 0.5, 0, 4.0), ("Sconce", (1.0, 0.92, 0.75), 0.5, 0, 3.0),
                                      ("NeonRed", (1.0, 0.16, 0.12), 0.4, 0, 6.0), ("NeonCyan", (0.24, 0.92, 1.0), 0.4, 0, 6.0)):
    K.mat(name, color=col, rough=rough, metal=metal, emit=emit)
K.facade_mats(frame=(0.20, 0.17, 0.14), sill=(0.82, 0.78, 0.70))


def quad_uv(part, corners, box):
    u0, v0, u1, v1 = box
    K.quad(part, corners, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


def panel_y(part, x0, x1, y, z0, z1, box, back=None):
    """Printed panel facing -Y at y; with back = y2 also one facing +Y at y2."""
    quad_uv(part, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], box)
    if back is not None:
        quad_uv(part, [(x1, back, z0), (x0, back, z0), (x0, back, z1), (x1, back, z1)], box)


def neon_frame_y(part, x0, x1, y, z0, z1, t=0.08 * M):
    for (a0, a1, b0, b1) in ((x0, x1, z0, z0 + t), (x0, x1, z1 - t, z1), (x0, x0 + t, z0, z1), (x1 - t, x1, z0, z1)):
        K.boxr(part, a0, a1, y - t, y, b0, b1)


ROOF_UV, CANOPY_UV, VALET_UV, MONU_UV = (0.25, 0.751, 1, 1), (0.25, 0.564, 1, 0.749), (0.25, 0.377, 1, 0.562), (0.25, 0.0, 1, 0.374)
BLADE_UV = (0.0, 0.0, 0.249, 1.0)

# ---------------------------------------------------------------- lot, drive loop, island
K.boxr("Asphalt", -LX, LX, LY0, LY1, -0.5 * M, 0)
K.boxr("Pave", -14 * M, 14 * M, LY0, LY0 + 0.4 * M, 0, 0.15 * M)                     # front kerb between the drives
K.boxr("Soil", -13.6 * M, 13.6 * M, LY0 + 0.4 * M, LY0 + 1.6 * M, 0, 0.12 * M)          # planting strip
K.boxr("Pave", -14 * M, 14 * M, LY0 + 1.6 * M, LY0 + 1.9 * M, 0, 0.15 * M)
for k in range(11):
    K.shrub(-12.5 * M + k * 2.5 * M, LY0 + 1.0 * M, 0.12 * M, 0.45 * M, rng)
for sx in (-1, 1):                                                                 # side kerbs
    a, b = sorted((sx * LX, sx * (LX - 0.3 * M)))
    K.boxr("Pave", a, b, LY0, LY1, 0, 0.15 * M)
K.boxr("Pave", -LX, LX, LY1 - 0.3 * M, LY1, 0, 0.15 * M)
# palm island + monument sign
IX0, IX1, IY0, IY1 = -8 * M, 8 * M, -19.5 * M, -15.5 * M
K.boxr("Pave", IX0, IX1, IY0, IY1, 0, 0.18 * M)
K.boxr("Soil", IX0 + 0.3 * M, IX1 - 0.3 * M, IY0 + 0.3 * M, IY1 - 0.3 * M, 0.18 * M, 0.22 * M)
for x in (-6 * M, 6 * M):
    K.palm(x, (IY0 + IY1) / 2, 0.22 * M, 7.5 * M, (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6)), rng)
for k in range(6):
    K.shrub(-4 * M + k * 1.6 * M, IY0 + 0.8 * M, 0.22 * M, 0.4 * M, rng)
K.boxr("Stone", -2.6 * M, 2.6 * M, IY0 + 1.0 * M, IY0 + 1.6 * M, 0.18 * M, 2.4 * M)
K.boxr("Stone", -2.8 * M, 2.8 * M, IY0 + 0.95 * M, IY0 + 1.65 * M, 2.4 * M, 2.6 * M)
panel_y("HotelSigns", -2.3 * M, 2.3 * M, IY0 + 0.98 * M, 0.5 * M, 2.25 * M, MONU_UV, back=IY0 + 1.62 * M)
# arrows: in at the west drive, out at the east
for (x, d) in ((-17.5 * M, 1), (17.5 * M, -1)):
    y0, y1 = (-22.5 * M, -19.5 * M) if d > 0 else (-19.5 * M, -22.5 * M)
    K.boxr("LotLine", x - 0.12 * M, x + 0.12 * M, min(y0, y1), max(y0, y1), 0, 0.012 * M)
    K.quad("LotLine", [(x - 0.7 * M, y1, 0.012 * M), (x + 0.7 * M, y1, 0.012 * M), (x, y1 + d * 1.0 * M, 0.012 * M)][::d])
# parking along the east and west sides of the tower (lines run along x)
for sx in (-1, 1):
    for i in range(7):
        y = -1 * M + i * 3.0 * M
        a, b = sorted((sx * (TX + 1.2 * M), sx * (LX - 0.8 * M)))
        K.boxr("LotLine", a, b, y - 0.06 * M, y + 0.06 * M, 0, 0.012 * M)

# ---------------------------------------------------------------- ground floor
K.boxr("Stone", -TX, TX, TY0 + 0.4 * M, TY1, -0.7 * M, GF)                         # base mass, lobby glass 0.4 m in
LOB = [(-15 * M, -9.2 * M), (-8.6 * M, -1.6 * M), (1.6 * M, 8.6 * M), (9.2 * M, 15 * M)]
piers = [-TX, -9.2 * M, -1.6 * M, 1.6 * M, 9.2 * M, 15 * M]
for x0, x1 in ((-TX, -15 * M), (-9.2 * M, -8.6 * M), (-1.6 * M, -1.0 * M), (1.0 * M, 1.6 * M), (8.6 * M, 9.2 * M), (15 * M, TX)):
    K.boxr("Stone", x0, x1, TY0, TY0 + 0.4 * M, -0.7 * M, GF)
gy = TY0 + 0.38 * M
for i, (x0, x1) in enumerate(LOB):
    u0 = (x0 + TX) / (2 * TX)
    panel_y("HotelLobby", x0, x1, gy, 0.3 * M, 4.2 * M, (u0, 0, u0 + (x1 - x0) / (2 * TX), 1))
    n = round((x1 - x0) / (1.8 * M))
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k / n
        K.boxr("Brass", x - 0.05 * M, x + 0.05 * M, gy - 0.1 * M, gy + 0.01 * M, 0.3 * M, 4.2 * M)
    for z in (0.25 * M, 3.3 * M, 4.2 * M):
        K.boxr("Brass", x0, x1, gy - 0.1 * M, gy + 0.01 * M, z, z + 0.08 * M)
    K.boxr("Stone", x0, x1, TY0 + 0.1 * M, gy - 0.1 * M, 4.3 * M, GF)               # stone transom over the glass
# centre doors: dark glass double door in brass, transom glass above
K.boxr("Dark", -1.0 * M, 1.0 * M, TY0 + 0.5 * M, TY0 + 0.56 * M, 0, 3.2 * M)
for x in (-1.0 * M, 0, 1.0 * M):
    K.boxr("Brass", x - 0.06 * M, x + 0.06 * M, TY0 + 0.4 * M, TY0 + 0.5 * M, 0, 3.3 * M)
K.boxr("Brass", -1.0 * M, 1.0 * M, TY0 + 0.4 * M, TY0 + 0.5 * M, 3.2 * M, 3.3 * M)
for x in (-0.3 * M, 0.3 * M):
    K.boxr("Brass", x - 0.03 * M, x + 0.03 * M, TY0 + 0.3 * M, TY0 + 0.38 * M, 1.0 * M, 2.0 * M)
panel_y("HotelLobby", -1.0 * M, 1.0 * M, TY0 + 0.45 * M, 3.3 * M, 4.2 * M, (0.47, 0.6, 0.53, 1))
# belt course
K.boxr("Stone", -TX - 0.3 * M, TX + 0.3 * M, TY0 - 0.3 * M, TY1 + 0.3 * M, GF, GF + 0.45 * M)

# ---------------------------------------------------------------- porte-cochere
CY0 = -13 * M
K.boxr("Pavers", -TX, TX, -4.2 * M, TY0, 0, 0.18 * M)                              # raised drop-off walk
K.boxr("Stone", -TX, TX, -4.3 * M, -4.2 * M, 0, 0.18 * M)
for x in (-7.4 * M, 7.4 * M):
    K.boxr("Stone", x - 0.45 * M, x + 0.45 * M, CY0 + 0.6 * M, CY0 + 1.5 * M, 0, 4.4 * M)      # columns
    K.boxr("Stone", x - 0.6 * M, x + 0.6 * M, CY0 + 0.45 * M, CY0 + 1.65 * M, 0, 0.5 * M)
    K.boxr("Stone", x - 0.6 * M, x + 0.6 * M, CY0 + 0.45 * M, CY0 + 1.65 * M, 4.0 * M, 4.4 * M)
K.boxr("Teal", -8.5 * M, 8.5 * M, CY0, TY0, 4.4 * M, 5.1 * M)
K.boxr("Brass", -8.55 * M, 8.55 * M, CY0 - 0.05 * M, TY0, 5.1 * M, 5.16 * M)
K.boxr("Soffit", -8.4 * M, 8.4 * M, CY0 + 0.1 * M, TY0 - 0.05 * M, 4.36 * M, 4.4 * M)
panel_y("HotelSigns", -5 * M, 5 * M, CY0 - 0.02 * M, 4.45 * M, 5.05 * M, (0.25 + 0.0, 0.564, 1, 0.749))
for x in (-6 * M, -2 * M, 2 * M, 6 * M):
    for y in (CY0 + 3 * M, CY0 + 7.5 * M):
        K.lamp((x, y, 4.33 * M), (1.2 * M, 1.2 * M, 0.04 * M))
# valet stand
K.boxr("Brass", 5 * M, 5.9 * M, -6.2 * M, -5.6 * M, 0.18 * M, 1.2 * M)
K.boxr("Dark", 4.95 * M, 5.95 * M, -6.25 * M, -5.55 * M, 1.2 * M, 1.26 * M)
K.cyl("Brass", (4.2 * M, -5.9 * M, 1.1 * M), 0.04 * M, 1.8 * M, segs=6)
K.boxr("Brass", 3.6 * M, 4.8 * M, -5.95 * M, -5.85 * M, 1.4 * M, 2.0 * M)
panel_y("HotelSigns", 3.62 * M, 4.78 * M, -5.97 * M, 1.42 * M, 1.98 * M, VALET_UV, back=-5.83 * M)
# planters by the doors
for x in (-3.5 * M, 3.5 * M):
    K.cyl("Stone", (x, -3 * M, 0.6 * M), 0.6 * M, 0.85 * M, segs=16, r2=0.45 * M)
    K.shrub(x, -3 * M, 1.0 * M, 0.55 * M, rng)

# ---------------------------------------------------------------- tower
K.boxr("Stucco", -TX, TX, TY0, TY1, GF + 0.45 * M, TOP)
BAY = 3.4 * M
for i in range(11):                                                              # stone piers between the bays
    x = -TX + i * BAY
    a0, a1 = max(-TX - 0.05 * M, x - 0.3 * M), min(TX + 0.05 * M, x + 0.3 * M)
    K.boxr("Stone", a0, a1, TY0 - 0.25 * M, TY0, GF + 0.45 * M, TOP + 1.6 * M)
    K.boxr("Stone", a0, a1, TY1, TY1 + 0.25 * M, GF + 0.45 * M, TOP)
for j in range(7):
    y = TY0 + j * (TY1 - TY0) / 6
    for sx in (-1, 1):
        a, b = sorted((sx * TX, sx * (TX + 0.25 * M)))
        K.boxr("Stone", a, b, y - 0.3 * M, y + 0.3 * M, GF + 0.45 * M, TOP)
WIN_W, WIN_H = 1.8 * M, 2.0 * M
front_a = [-TX + (i + 0.5) * BAY for i in range(10)]
side_a = [TY0 + (j + 0.5) * (TY1 - TY0) / 6 for j in range(6)]
for k in range(NF):
    z0 = GF + 0.45 * M + k * FH + 0.75 * M
    fr = "Frame" if k < 5 else "FrameB"
    for a in front_a:
        K.window3d("y", TY0, -1, a, z0, WIN_W, WIN_H, mull=1, transom=True, head=False, frame=fr)
        K.window3d("y", TY1, 1, a, z0, WIN_W, WIN_H, mull=1, head=False, frame=fr)
    for a in side_a:
        K.window3d("x", TX, 1, a, z0, WIN_W, WIN_H, mull=1, head=False, frame=fr)
        K.window3d("x", -TX, -1, a, z0, WIN_W, WIN_H, mull=1, head=False, frame=fr)
    if k in (1, 3, 5, 7):                                                         # balconies, centre bays
        zb = z0 - 0.75 * M
        for a in front_a[3:7]:
            K.boxr("Stone", a - 1.3 * M, a + 1.3 * M, TY0 - 1.1 * M, TY0, zb - 0.2 * M, zb)
            for b in range(9):
                x = a - 1.2 * M + b * 0.3 * M
                K.boxr("WinIron", x - 0.02 * M, x + 0.02 * M, TY0 - 1.05 * M, TY0 - 1.01 * M, zb, zb + 1.0 * M)
            K.boxr("WinIron", a - 1.25 * M, a + 1.25 * M, TY0 - 1.07 * M, TY0 - 0.99 * M, zb + 1.0 * M, zb + 1.06 * M)
            for sx in (-1, 1):
                K.boxr("WinIron", a + sx * 1.25 * M - 0.03 * M, a + sx * 1.25 * M + 0.03 * M, TY0 - 1.07 * M, TY0,
                       zb + 1.0 * M, zb + 1.06 * M)
# cornice + parapet
K.boxr("Stone", -TX - 0.6 * M, TX + 0.6 * M, TY0 - 0.6 * M, TY1 + 0.6 * M, TOP - 0.5 * M, TOP)
K.boxr("Stone", -TX - 0.35 * M, TX + 0.35 * M, TY0 - 0.35 * M, TY1 + 0.35 * M, TOP - 0.9 * M, TOP - 0.5 * M)
for (x0, x1, y0, y1) in ((-TX, TX, TY0, TY0 + 0.3 * M), (-TX, TX, TY1 - 0.3 * M, TY1),
                         (-TX, -TX + 0.3 * M, TY0 + 0.3 * M, TY1 - 0.3 * M), (TX - 0.3 * M, TX, TY0 + 0.3 * M, TY1 - 0.3 * M)):
    K.boxr("Stucco", x0, x1, y0, y1, TOP, TOP + 1.2 * M)
    K.boxr("Stone", x0 - 0.05 * M, x1 + 0.05 * M, y0 - 0.05 * M, y1 + 0.05 * M, TOP + 1.2 * M, TOP + 1.35 * M)
K.boxr("Roof", -TX + 0.3 * M, TX - 0.3 * M, TY0 + 0.3 * M, TY1 - 0.3 * M, TOP, TOP + 0.05 * M)
# stepped crown at the centre of the front with the SOLANA sign on top
for (w, d, z0, z1) in ((6 * M, 6 * M, TOP, TOP + 3.0 * M), (4.4 * M, 4.6 * M, TOP + 3.0 * M, TOP + 4.6 * M)):
    K.boxr("Stucco", -w, w, TY0 + 0.3 * M, TY0 + d, z0, z1)
    K.boxr("Stone", -w - 0.1 * M, w + 0.1 * M, TY0 + 0.2 * M, TY0 + d + 0.1 * M, z1, z1 + 0.2 * M)
for x in (-4.4 * M, -1.5 * M, 1.5 * M, 4.4 * M):                                  # deco fins
    K.boxr("Stone", x - 0.2 * M, x + 0.2 * M, TY0 - 0.1 * M, TY0 + 0.3 * M, TOP, TOP + 4.2 * M)
SZ0 = TOP + 4.8 * M
SY = TY0 + 2.2 * M
for x in (-6 * M, 0, 6 * M):
    K.boxr("Steel", x - 0.1 * M, x + 0.1 * M, SY + 0.12 * M, SY + 0.32 * M, TOP + 4.8 * M, SZ0 + 5 * M)
    K.cyl_along("Steel", (x, SY + 0.2 * M, SZ0 + 3 * M), (x, SY + 2.2 * M, TOP + 4.8 * M), 0.06 * M, segs=6)
K.boxr("Dark", -7.5 * M, 7.5 * M, SY, SY + 0.12 * M, SZ0, SZ0 + 5 * M)
panel_y("HotelSigns", -7.4 * M, 7.4 * M, SY - 0.02 * M, SZ0 + 0.1 * M, SZ0 + 4.9 * M, ROOF_UV)
neon_frame_y("NeonCyan", -7.55 * M, 7.55 * M, SY - 0.04 * M, SZ0 - 0.05 * M, SZ0 + 5.05 * M)
for x in (-TX + 0.6 * M, TX - 0.6 * M):                                          # red beacons on the corners
    for y in (TY0 + 0.6 * M, TY1 - 0.6 * M):
        K.cyl("Steel", (x, y, TOP + 2.0 * M), 0.06 * M, 1.6 * M, segs=6)
        K.box("NeonRed", (x, y, TOP + 2.9 * M), (0.3 * M, 0.3 * M, 0.25 * M))
# roof plant
K.boxr("Stucco", 6 * M, 12 * M, 8 * M, 14 * M, TOP, TOP + 3.4 * M)                # lift overrun
K.boxr("Stone", 5.9 * M, 12.1 * M, 7.9 * M, 14.1 * M, TOP + 3.4 * M, TOP + 3.55 * M)
K.boxr("Dark", 8 * M, 9.4 * M, 7.85 * M, 7.9 * M, TOP, TOP + 2.2 * M)
for (x, y) in ((-12 * M, 6 * M), (-8 * M, 6 * M), (-12 * M, 12 * M)):
    K.boxr("AcBody", x - 1.4 * M, x + 1.4 * M, y - 1.0 * M, y + 1.0 * M, TOP + 0.05 * M, TOP + 1.5 * M)
    K.cyl("Dark", (x, y, TOP + 1.52 * M), 0.65 * M, 0.04 * M, segs=16)

# ---------------------------------------------------------------- blade sign on the west front corner
BX = -TX + 1.0 * M
BZ0, BZ1 = GF + 3 * M, GF + 15 * M
K.boxr("Dark", BX - 0.2 * M, BX + 0.2 * M, TY0 - 3.3 * M, TY0 - 0.3 * M, BZ0, BZ1)
for s in (-1, 1):
    x = BX + s * 0.22 * M
    cs = [(x, TY0 - 0.35 * M, BZ0 + 0.1 * M), (x, TY0 - 3.25 * M, BZ0 + 0.1 * M), (x, TY0 - 3.25 * M, BZ1 - 0.1 * M),
          (x, TY0 - 0.35 * M, BZ1 - 0.1 * M)]
    if s > 0:
        cs = [cs[1], cs[0], cs[3], cs[2]]
    quad_uv("HotelSigns", cs, BLADE_UV)
    t = 0.08 * M
    xa, xb = sorted((x, x + s * t))
    for (y0, y1, z0, z1) in ((TY0 - 3.35 * M, TY0 - 0.25 * M, BZ0 - 0.05 * M, BZ0 + 0.05 * M),
                             (TY0 - 3.35 * M, TY0 - 0.25 * M, BZ1 - 0.05 * M, BZ1 + 0.05 * M),
                             (TY0 - 3.35 * M, TY0 - 3.25 * M, BZ0, BZ1)):
        K.boxr("NeonRed", xa, xb, y0, y1, z0, z1)
for z in (BZ0 + 1 * M, BZ1 - 1 * M):                                              # wall brackets
    K.boxr("Steel", BX - 0.3 * M, BX + 0.3 * M, TY0 - 0.35 * M, TY0, z - 0.3 * M, z + 0.3 * M)

# ---------------------------------------------------------------- back: service door, dock, dumpster
K.boxr("Dark", -10 * M, -7 * M, TY1, TY1 + 0.06 * M, 0, 3 * M)                    # roll-up dock door
for z in range(10):
    K.boxr("Steel", -10 * M, -7 * M, TY1 + 0.06 * M, TY1 + 0.09 * M, z * 0.3 * M + 0.1 * M, z * 0.3 * M + 0.14 * M)
K.boxr("Pave", -10.5 * M, -6.5 * M, TY1, TY1 + 2 * M, 0, 1.1 * M)                 # dock
K.boxr("Dark", 4 * M, 5.4 * M, TY1, TY1 + 0.06 * M, 0, 2.3 * M)
K.box("Sconce", (4.7 * M, TY1 + 0.12 * M, 2.7 * M), (0.25 * M, 0.2 * M, 0.2 * M))
K.box("Sconce", (-8.5 * M, TY1 + 0.12 * M, 3.4 * M), (0.25 * M, 0.2 * M, 0.2 * M))
K.boxr("Dumpster", 8 * M, 11 * M, TY1 + 0.8 * M, TY1 + 2.6 * M, 0.15 * M, 1.4 * M)
K.boxr("Dark", 7.95 * M, 11.05 * M, TY1 + 0.75 * M, TY1 + 2.65 * M, 1.4 * M, 1.48 * M)
for x in (-TX + 0.4 * M, TX - 0.4 * M):
    K.downpipe(x, TY1 + 0.35 * M, 0, TOP)
# lot lights in the side parking
for (x, y) in ((-20 * M, 8 * M), (20 * M, 8 * M)):
    K.cyl("Pave", (x, y, 0.35 * M), 0.35 * M, 0.7 * M, segs=12)
    K.cyl("Steel", (x, y, 4.2 * M), 0.1 * M, 7.0 * M, segs=10)
    d = 1 if x < 0 else -1
    K.cyl_along("Steel", (x, y, 7.6 * M), (x + d * 1.4 * M, y, 7.6 * M), 0.06 * M, segs=6)
    K.boxr("Steel", min(x + d * 1.0 * M, x + d * 2.2 * M), max(x + d * 1.0 * M, x + d * 2.2 * M), y - 0.3 * M, y + 0.3 * M, 7.45 * M, 7.7 * M)
    K.lamp((x + d * 1.6 * M, y, 7.43 * M), (1.0 * M, 0.45 * M, 0.04 * M))

K.finish(face=A["face"])
meta = K.export()
s = 1 if A["face"] == "N" else -1
meta["driveways"] = [[a * s, b * s, A["face"]] for a, b in DRIVES]
json.dump(meta, open(os.path.join(K.out, "meta.json"), "w"), indent=1)

if A["render"]:
    K.render_setup(A["samples"], A["res"])
    s = -1 if A["face"] == "N" else 1
    K.shot("front", (-30 * M, s * 62 * M, 14 * M), (0, 0, 16 * M), lens=24)
    K.shot("street", (8 * M, s * 27 * M, 1.7 * M), (-2 * M, s * 4 * M, 4 * M), lens=22)
    K.shot("back", (40 * M, -s * 60 * M, 30 * M), (0, 0, 14 * M), lens=26)
