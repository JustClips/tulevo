"""Arkwell 24 HR ATM: a through-the-wall double ATM for the Arkwell Bank tower (our own brand).

  blender --background --python build_atm.py -- [OUT_DIR] [--no-render] [--samples N] [--res F]
  (textures first: python3 tools/atm_textures.py)

An anthracite wall surround with two recessed machines, a steel canopy with downlights and a
lit "ARKWELL | 24 HR ATM" sign box. Each machine: brushed-steel fascia, black screen shroud with a
visor, glowing screen, 4 + 4 function keys, a sloped keypad shelf with 16 real keys and privacy
fins, a card reader with a green throat light, receipt slot, cash dispenser with a shutter and
light, headphone jack, speaker grille, camera, rear-view mirror strip, service door and vents.

Built in studs (1 m = 3.6). Origin: centre of the back face at the bottom (the wall plane, on
top of the tower's plinth). -Y = front (Roblox -Z). Model placed by tools/build_city_map.py.

Parts the game hooks into (src/server/Atms.server.luau):
  Atm<N>Screen   the screen (thin box, its Front face = the display): SurfaceGui + ProximityPrompt
  AtmCardLight / AtmCashLight   green guide lights (Neon)
  LightCeil      canopy downlights (CityBuildings: Neon + SurfaceLight)
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit import Kit, args, M  # noqa: E402
import bpy, bmesh  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

A = args(r"C:\out\atm")
HERE = os.path.dirname(os.path.abspath(__file__))
k = Kit("ArkwellAtm", A["out"], os.path.join(HERE, "tex"))

# ---------------------------------------------------------------- materials
k.mat("AtmShell", sheet="AtmShell", tile=(6, 6))
k.mat("AtmSteel", sheet="AtmSteel", tile=(4, 4))
k.mat("AtmSteelDark", sheet="AtmSteelDark", tile=(4, 4))
k.mat("AtmBlack", sheet="AtmBlack", tile=(2, 2))
k.mat("AtmRubber", sheet="AtmRubber", tile=(1, 1))
k.mat("AtmMirror", sheet="AtmMirror", tile=(3.4, 0.9), metal=0.9)
k.mat("AtmScreen", sheet="AtmScreen", explicit=True, emit=1.5)
k.mat("AtmKeys", sheet="AtmKeys", explicit=True)
k.mat("AtmLabels", sheet="AtmLabels", explicit=True)
k.mat("AtmSign", sheet="AtmSign", explicit=True, emit=0.6)
k.mat("Light", color=(1.0, 0.96, 0.88), emit=4.0)
k.mat("AtmCardLight", color=(0.25, 0.95, 0.45), emit=6.0)
k.mat("AtmCashLight", color=(0.25, 0.95, 0.45), emit=4.0)

# ---------------------------------------------------------------- layout (studs)
W, D, H = 16.4, 1.6, 11.0       # surround width, depth (wall -> front), height
HW = W / 2
BAYS = (-3.6, 3.6)              # machine centres (x)
BHW = 2.5                       # half width of a bay opening
BZ0, BZ1 = 0.5, 6.6             # bay opening bottom / top
F = -0.45                       # fascia front (machines sit 1.15 inside the surround)
G = 0.05                        # gap for printed labels / quads (no coplanar faces)
cols = []                       # hand collider boxes (tools/city_colliders.py)


def obox(part, center, size, axes, mat=None):
    """Box with its own axes (3 column vectors: width, depth, height directions)."""
    bm = k.bm(part, mat)
    r = bmesh.ops.create_cube(bm, size=1.0)
    R = Matrix((axes[0], axes[1], axes[2])).transposed().to_4x4()
    mx = Matrix.Translation(Vector(center)) @ R @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=mx, verts=r["verts"])


def label(cell, cx, z0, w, h, y=F - G):
    """Printed label from the AtmLabels atlas (4 x 2 cells), facing -Y."""
    i, j = cell
    u0, u1 = i / 4, (i + 1) / 4
    v0, v1 = 1 - (j + 1) / 2, 1 - j / 2
    k.face_y("AtmLabels", cx, y, z0, w, h, uvs=((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


# ---------------------------------------------------------------- surround + canopy + sign
k.boxr("AtmShell", -HW, HW, -D, 0, 0, BZ0)                                  # kick
for x0, x1 in ((-HW, BAYS[0] - BHW), (BAYS[0] + BHW, BAYS[1] - BHW), (BAYS[1] + BHW, HW)):
    k.boxr("AtmShell", x0, x1, -D, 0, BZ0, BZ1)                             # stiles
k.boxr("AtmShell", -HW, HW, -D, 0, BZ1, H - 0.4)                             # header (sign wall)
k.boxr("AtmSteel", -HW - 0.1, HW + 0.1, -D - 0.1, 0, H - 0.4, H)             # coping
for s in (-1, 1):                                                           # corner trims
    k.boxr("AtmSteel", s * HW, s * (HW + 0.1), -D - 0.1, 0, 0, H - 0.4)
k.boxr("AtmSteel", -HW, HW, -D - 0.06, -D, 0.06, 0.44)                       # kick plate
for bx in BAYS:                                                             # steel ring round each bay
    k.boxr("AtmSteel", bx - BHW - 0.14, bx + BHW + 0.14, -D - 0.12, -D, BZ1, BZ1 + 0.14)
    k.boxr("AtmSteel", bx - BHW - 0.14, bx + BHW + 0.14, -D - 0.12, -D, BZ0 - 0.14, BZ0)
    for s in (-1, 1):
        x = bx + s * (BHW + 0.07)
        k.boxr("AtmSteel", x - 0.07, x + 0.07, -D - 0.12, -D, BZ0, BZ1)

# canopy: steel slab over both bays, front lip, two downlight strips underneath
CZ0, CZ1, CY = 6.86, 7.16, -3.1
k.boxr("AtmSteelDark", -HW - 0.1, HW + 0.1, CY, -D + 0.05, CZ0, CZ1)
k.boxr("AtmSteel", -HW - 0.1, HW + 0.1, CY - 0.1, CY, CZ0 - 0.1, CZ1 + 0.06)
for bx in BAYS:
    k.boxr("LightCeil", bx - 1.7, bx + 1.7, -2.45, -2.15, CZ0 - 0.06, CZ0, mat="Light")
# lit sign box on the header
SZ0, SZ1 = 7.5, 10.3
k.boxr("AtmBlack", -6.0, 6.0, -D - 0.28, -D + 0.05, SZ0 - 0.1, SZ1 + 0.1)
sh = SZ1 - SZ0
k.face_y("AtmSign", 0, -D - 0.28 - G, SZ0, sh * 4, sh)

# ---------------------------------------------------------------- the machines
# keypad shelf slope: front-top P0 -> back-top P1
P0, P1 = Vector((0, F - 1.1, 2.72)), Vector((0, F, 3.1))
S = (P1 - P0).normalized()              # up the slope (away from the user)
N = Vector((1, 0, 0)).cross(S)          # slope normal (up, toward the user)
X = Vector((1, 0, 0))
SL = (P1 - P0).length

for n, bx in enumerate(BAYS, 1):
    # fascia
    k.boxr("AtmSteel", bx - BHW + 0.02, bx + BHW - 0.02, F, -0.02, BZ0, BZ1)
    # brand plate + rear-view mirror strip
    k.boxr("AtmBlack", bx - 0.68, bx + 0.68, F - 0.06, F, 5.92, 6.5)
    label((0, 0), bx, 5.93, 1.2, 0.56, y=F - 0.06 - G)
    k.boxr("AtmMirror", bx - 1.7, bx + 1.7, F - 0.06, F, 5.7, 5.84)
    # screen shroud with a visor
    SX, SZA, SZB = 1.15, 3.6, 5.32
    k.boxr("AtmBlack", bx - 1.7, bx - SX, F - 0.42, F, 3.25, 5.65)
    k.boxr("AtmBlack", bx + SX, bx + 1.7, F - 0.42, F, 3.25, 5.65)
    k.boxr("AtmBlack", bx - SX, bx + SX, F - 0.42, F, SZB, 5.65)
    k.boxr("AtmBlack", bx - SX, bx + SX, F - 0.42, F, 3.25, SZA)
    k.boxr("AtmBlack", bx - 1.75, bx + 1.75, F - 0.78, F - 0.42, 5.55, 5.65)          # visor
    for s in (-1, 1):                                                                    # visor cheeks
        k.boxr("AtmBlack", bx + s * 1.7 - 0.05, bx + s * 1.7 + 0.05, F - 0.78, F - 0.42, 4.6, 5.55)
    k.boxr("AtmBlack", bx - SX, bx + SX, F - 0.08, F, SZA, SZB)                          # panel behind the glass
    # the screen: thin box, front face is the display (UVs on the front only)
    scr = f"Atm{n}Screen"
    k.boxr(scr, bx - 1.07, bx + 1.07, F - 0.22, F - 0.18, 3.66, 5.26, mat="AtmScreen")
    sbm = k.bms[scr]
    sbm.normal_update()
    uv = sbm.loops.layers.uv.active
    for f in sbm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = ((co.x - (bx - 1.07)) / 2.14, (co.z - 3.66) / 1.6) if f.normal.y < -0.9 else (0.02, 0.02)
    # camera in the top bar
    k.cyl("AtmBlack", (bx, F - 0.45, 5.47), 0.07, 0.06, segs=12, axis='Y')
    k.cyl("AtmMirror", (bx, F - 0.49, 5.47), 0.035, 0.04, segs=10, axis='Y')
    # function keys: 4 each side, line up with the on-screen buttons
    for s in (-1, 1):
        for z in (3.85, 4.2, 4.55, 4.9):
            k.boxr("AtmSteel", bx + s * 1.425 - 0.16, bx + s * 1.425 + 0.16, F - 0.5, F - 0.42, z - 0.1, z + 0.1)
    # card reader (right): bezel, green throat light, slot
    cx = bx + 2.1
    k.boxr("AtmBlack", cx - 0.3, cx + 0.3, F - 0.3, F, 3.3, 4.3)
    k.boxr("AtmBlack", cx - 0.3, cx + 0.3, F - 0.38, F - 0.3, 4.1, 4.3)                   # lip over the slot
    k.boxr("AtmCardLight", cx - 0.26, cx + 0.26, F - 0.36, F - 0.3, 3.78, 4.0)
    k.boxr("AtmRubber", cx - 0.21, cx + 0.21, F - 0.4, F - 0.36, 3.86, 3.92)
    label((1, 0), cx, 4.4, 0.6, 0.3)
    # receipt slot (left)
    rx = bx - 2.1
    k.boxr("AtmBlack", rx - 0.3, rx + 0.3, F - 0.22, F, 3.3, 3.72)
    k.boxr("AtmRubber", rx - 0.23, rx + 0.23, F - 0.26, F - 0.22, 3.48, 3.53)
    k.boxr("AtmSteel", rx - 0.26, rx + 0.26, F - 0.3, F - 0.22, 3.4, 3.45)                # lip
    label((3, 0), rx, 3.82, 0.6, 0.3)
    # headphone jack under the card reader
    k.cyl("AtmBlack", (cx, F - 0.03, 2.95), 0.08, 0.06, segs=12, axis='Y')
    k.cyl("AtmRubber", (cx, F - 0.07, 2.95), 0.035, 0.04, segs=10, axis='Y')

    # keypad shelf: a wedge across the fascia
    x0, x1 = bx - 1.9, bx + 1.9
    yb, ybot_b, yf, ybot_f = F, 2.2, F - 1.1, 2.52
    prof = [(yb, ybot_b), (yf, ybot_f), (yf, P0.z), (yb, P1.z)]          # back-bottom, front-bottom, front-top, back-top
    L = [Vector((x0, y, z)) for y, z in prof]
    R = [Vector((x1, y, z)) for y, z in prof]
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        k.quad("AtmSteelDark", [L[a], R[a], R[b], L[b]])
    k.quad("AtmSteelDark", list(reversed(L)))
    k.quad("AtmSteelDark", R)
    base = lambda x, t, h: Vector((x, 0, 0)) + Vector((0, P0.y, P0.z)) + S * t + N * h
    kx, tc = bx - 0.35, SL * 0.5
    # keypad bezel + privacy fins
    obox("AtmBlack", base(kx, tc, 0.02), (1.3, 1.0, 0.04), (X, S, N))
    for s in (-1, 1):
        obox("AtmBlack", base(kx + s * 0.67, tc, 0.18), (0.04, 1.0, 0.36), (X, S, N))
    obox("AtmBlack", base(kx, tc + 0.48, 0.1), (1.38, 0.04, 0.2), (X, S, N))
    # 16 keys with printed legends (AtmKeys atlas, 4 x 4)
    for r in range(4):
        for c in range(4):
            kxc, t = kx + (c - 1.5) * 0.29, tc + (1.5 - r) * 0.225
            obox("AtmSteel", base(kxc, t, 0.04 + 0.045), (0.25, 0.19, 0.09), (X, S, N))
            ctr = base(kxc, t, 0.04 + 0.09 + 0.012)
            hu, hv = 0.12, 0.09
            u0, u1, v0, v1 = c / 4, (c + 1) / 4, 1 - (r + 1) / 4, 1 - r / 4
            k.quad("AtmKeys", [ctr - X * hu - S * hv, ctr + X * hu - S * hv, ctr + X * hu + S * hv, ctr - X * hu + S * hv],
                   uvs=((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
    # speaker grille on the shelf, right of the keypad
    for i in range(5):
        obox("AtmRubber", base(bx + 1.2, tc - 0.3 + i * 0.15, 0.015), (0.6, 0.05, 0.03), (X, S, N))
    obox("AtmBlack", base(bx + 1.2, tc, 0.005), (0.72, 0.8, 0.01), (X, S, N))

    # cash dispenser under the shelf
    k.boxr("AtmSteel", bx - 1.25, bx + 1.25, F - 0.25, F, 1.45, 2.05)
    k.boxr("AtmRubber", bx - 1.1, bx + 1.1, F - 0.29, F - 0.25, 1.6, 1.84)
    k.boxr("AtmBlack", bx - 1.1, bx + 1.1, F - 0.33, F - 0.29, 1.69, 1.75)                # shutter seam
    k.boxr("AtmCashLight", bx - 1.1, bx + 1.1, F - 0.29, F - 0.25, 1.9, 1.95)
    label((2, 0), bx, 1.06, 0.6, 0.3)
    # service door outline, lock and vents on the lower fascia
    for z0, z1 in ((0.62, 0.66), (1.36, 1.4)):
        k.boxr("AtmSteelDark", bx - 2.2, bx + 2.2, F - 0.03, F, z0, z1)
    for s in (-1, 1):
        k.boxr("AtmSteelDark", bx + s * 2.2 - 0.02, bx + s * 2.2 + 0.02, F - 0.03, F, 0.66, 1.36)
    label((3, 1), bx + 1.75, 0.78, 0.4, 0.2, y=F - 0.03 - G)
    for i in range(5):
        k.boxr("AtmSteelDark", bx - 2.0, bx - 0.9, F - 0.06, F, 0.74 + i * 0.12, 0.79 + i * 0.12)

# collision: one box for the surround (machines sit inside it) + the canopy
cols.append([0, -(D + 0.12) / 2, H / 2, W + 0.2, D + 0.12, H, 0, "Metal"])
cols.append([0, (CY - 0.1 - D) / 2, (CZ0 + CZ1) / 2, W + 0.2, -(CY - 0.1) - D, CZ1 - CZ0, 0, "Metal"])

# ---------------------------------------------------------------- finish + export
k.finish(keep_normals=())
meta = k.export()
meta["collider_boxes"] = cols
meta["screens"] = [f"Atm{n}Screen" for n in range(1, len(BAYS) + 1)]
import json  # noqa: E402
json.dump(meta, open(os.path.join(A["out"], "meta.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(A["out"], "ArkwellAtm.blend"))

if not A["render"]:
    sys.exit(0)

# ---------------------------------------------------------------- preview renders (with a stand-in wall)
k.render_setup(A["samples"], A["res"], ground=400)
wall = bpy.data.materials.new("Wall"); wall.use_nodes = True
wall.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.09, 0.09, 0.1, 1)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.5, 8)); w_ = bpy.context.object
w_.scale = (30, 3, 18); w_.data.materials.append(wall)
pav = bpy.data.materials.new("Pave"); pav.use_nodes = True
pav.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.32, 0.32, 0.33, 1)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -6, -0.5)); p_ = bpy.context.object
p_.scale = (40, 12, 1); p_.data.materials.append(pav)
k.shot("atm_front34", (-9, -16, 6.5), (0, -1, 5), lens=35)
k.shot("atm_machine", (3.6 - 1.2, -6.0, 4.6), (3.6, -0.6, 3.4), lens=35)
k.shot("atm_keypad", (2.9, -3.0, 4.4), (3.3, -1.0, 2.9), lens=50)
