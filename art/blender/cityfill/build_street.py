"""Street furniture for the tulevo city: one merged model per street (thread "Fill city with
buildings and street props", 2026-11-07). Original designs, real CC0 surface scans.

  python3 tools/cityfill_textures.py && python3 tools/street_layout.py
  blender --background --python build_street.py -- OUT_DIR [--only StreetVaultAvenue] [--no-render]

Reads street_layout.json (next to this script) and writes OUT_DIR/<Model>/ (glb, meta.json,
textures/, renders/) for every model in it: Street<Road> per city street and StreetCorners
(traffic signals, stop signs, street name blades). Models are built in world coordinates, so
tools/build_city_map.py places each at the origin.

Props:
  Light      9 m cobra-head street light on a tapered steel pole (StreetLamp<n> = the lit lens)
  Palm/Tree  street palm (Vault Avenue) or shade tree in a cast-iron tree grate
  Bin        slatted round litter bin with a domed lid
  Bench      cast-iron frame bench with hardwood slats, facing the street
  Hydrant    fire hydrant with yellow caps
  NewsBoxes  2-3 coin news boxes (original paper names)
  Meter      single parking meter
  Mailbox    blue city mail box
  Cabinet    signal control cabinet on a plinth
  Speed      speed limit sign; BusFlag bus stop sign; BusStop glass shelter with bench and ad
  Signal     corner mast-arm traffic signal (lenses Signal<EW|NS><Red|Amber|Green>, cycled by
             Client/TrafficSignals) + street name blades
  StopSign   stop sign on a post, with street blades on some

Blender (x, y, z) = Roblox (-x, z, y). Local prop frame: -Y = the prop's front (toward the road
for lights/benches/hydrants), +Z up, origin on the sidewalk surface.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bpy  # noqa: E402
from kit import Kit, M, args  # noqa: E402
from mathutils import Vector, Matrix  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")
A = args(r"C:\out\street")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = argv[argv.index("--only") + 1] if "--only" in argv else None
LAYOUT = json.load(open(os.path.join(HERE, "street_layout.json")))
ATLAS = json.load(open(os.path.join(TEX, "atlas.json")))
LEAF_PARTS = ("Leaf", "LeafB", "LeafC", "LeafD", "LeafE", "LeafF",
              "LeafCard", "LeafCardB", "LeafCardC", "LeafCardD", "LeafCardE", "LeafCardF")


def bmesh_icosphere(bm, subdiv, center, radii, rng):
    """Lumpy ellipsoid (canopy core) added to bm."""
    import bmesh
    r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in r["verts"]:
        k = rng.uniform(0.86, 1.1)
        v.co = Vector((center.x + v.co.x * radii[0] * k, center.y + v.co.y * radii[1] * k, center.z + v.co.z * radii[2] * k))
    return r


class Street:
    def __init__(self, name):
        self.K = Kit(name, os.path.join(A["out"], name), TEX)
        K = self.K
        for nm, sheet, tile in (("PoleSteel", "PoleSteel", (1.2 * M, 1.2 * M)), ("PoleGalv", "PoleGalv", (1.2 * M, 1.2 * M)),
                                ("BinGreen", "BinGreen", (1 * M, 1 * M)), ("IronBlack", "IronBlack", (1 * M, 1 * M)),
                                ("HydrantRed", "HydrantRed", (0.6 * M, 0.6 * M)), ("SafetyYellow", "SafetyYellow", (0.6 * M, 0.6 * M)),
                                ("MailBlue", "MailBlue", (1 * M, 1 * M)), ("CabGrey", "CabGrey", (1 * M, 1 * M)),
                                ("NewsBlue", "NewsBlue", (1 * M, 1 * M)), ("NewsRed", "NewsRed", (1 * M, 1 * M)),
                                ("NewsAmber", "NewsAmber", (1 * M, 1 * M)), ("SignalBody", "SignalBody", (1 * M, 1 * M)),
                                ("SignalYellow", "SignalYellow", (1 * M, 1 * M)),
                                ("BenchWood", "BenchWood", (1.2 * M, 1.2 * M)), ("Plinth", "Plinth", (1.5 * M, 1.5 * M)),
                                ("Bark", "Bark", (0.8 * M, 0.8 * M)), ("Leaves", "Leaves", (1.6 * M, 1.6 * M)),
                                ("ShelterGlass", "ShelterGlass", (1.5 * M, 2.4 * M))):
            K.mat(nm, sheet=sheet, tile=tile)
        K.mat("DecoPrint", sheet="DecoPrint", explicit=True)
        K.mat("Grate", sheet="Grate", explicit=True)
        K.mat("LeafCard", sheet="LeafCard", explicit=True, alpha=True)
        K.mat("Light", color=(1.0, 0.95, 0.85), emit=4.0)
        K.mat("Palm", color=(0.16, 0.30, 0.10), rough=0.7)
        K.mat("Trunk", color=(0.42, 0.34, 0.25), rough=0.95)
        K.mat("LensDark", color=(0.05, 0.05, 0.05), rough=0.3)
        for nm, col in (("LensRed", (0.55, 0.04, 0.03)), ("LensAmber", (0.6, 0.35, 0.02)), ("LensGreen", (0.03, 0.45, 0.25))):
            K.mat(nm, color=col, rough=0.2, emit=1.0)
        # glass used in renders only: in game ClearGlass* turns to Glass 0.6 (CityBuildings)
        g = K.mats["ShelterGlass"]["mat"]
        g.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = 0.25
        g.surface_render_method = 'DITHERED'
        self.n_lamp = 0
        self.leaf_i = 0
        self.leaf_count = 0
        self.T = Matrix.Identity(4)
        self.rz = 0.0
        self.cols = []       # one simple collision box or two per prop (tools/city_colliders.py)

    def col(self, c, s, mat="Metal", rz=0.0):
        """Collision box in the prop frame: centre c, size s (local), material name."""
        w = self.w(c)
        self.cols.append([round(w.x, 3), round(w.y, 3), round(w.z, 3), round(s[0], 3), round(s[1], 3), round(s[2], 3),
                          round(self.rz + rz, 5), mat])

    # ------------------------------------------------------------ transforms
    def place(self, p):
        """Set the local frame for a prop from its layout entry (Roblox coords + heading)."""
        x, z = -p["x"], p["z"]                       # Blender position
        fx, fy = -p["hx"], p["hz"]                   # prop front direction in Blender
        self.rz = math.atan2(fx, -fy)                # local -Y -> front
        self.T = Matrix.Translation((x, z, p["y"])) @ Matrix.Rotation(self.rz, 4, 'Z')

    def w(self, v):
        return self.T @ Vector(v)

    # ------------------------------------------------------------ local primitives
    def box(self, part, c, s, rz=0.0, mat=None):
        self.K.box(part, tuple(self.w(c)), s, rz=self.rz + rz, mat=mat)

    def cyl(self, part, c, r, h, segs=12, r2=None, mat=None):
        self.K.cyl(part, tuple(self.w(c)), r, h, segs=segs, r2=r2, mat=mat)

    def rod(self, part, a, b, r, segs=8, mat=None):
        self.K.cyl_along(part, tuple(self.w(a)), tuple(self.w(b)), r, segs=segs, mat=mat)

    def quad(self, part, corners, uvs, mat=None):
        self.K.quad(part, [tuple(self.w(c)) for c in corners], uvs, mat=mat)

    def tube(self, part, pts, r0, r1=None, segs=8, mat=None):
        """Tapered tube through local points (closed caps per segment)."""
        r1 = r0 if r1 is None else r1
        n = len(pts) - 1
        for i in range(n):
            ra = r0 + (r1 - r0) * i / n
            self.rod(part, pts[i], pts[i + 1], ra, segs=segs, mat=mat)

    def prism(self, part, prof, x0, x1, mat=None):
        """Extrude a closed (y, z) profile along local x from x0 to x1."""
        bm = self.K.bm(part, mat)
        a = [bm.verts.new(self.w((x0, y, z))) for y, z in prof]
        b = [bm.verts.new(self.w((x1, y, z))) for y, z in prof]
        n = len(prof)
        bm.faces.new(a[::-1])
        bm.faces.new(b)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([a[i], a[j], b[j], b[i]])

    def frustum(self, part, c, z0, z1, w0, d0, w1, d1, mat=None):
        bm = self.K.bm(part, mat)
        cx, cy = c
        lo = [bm.verts.new(self.w((cx + sx * w0 / 2, cy + sy * d0 / 2, z0))) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        hi = [bm.verts.new(self.w((cx + sx * w1 / 2, cy + sy * d1 / 2, z1))) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        bm.faces.new(lo[::-1]); bm.faces.new(hi)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new([lo[i], lo[j], hi[j], hi[i]])

    def printed(self, region, cx, y, z0, w, h, facing=-1, back=False):
        """A printed atlas region on a plane y = const (seen from facing side), both sides if back."""
        x0, y0, x1, y1 = ATLAS[region]
        uv = ((x0, 1 - y1), (x1, 1 - y1), (x1, 1 - y0), (x0, 1 - y0))
        xs = (cx - w / 2, cx + w / 2) if facing < 0 else (cx + w / 2, cx - w / 2)
        self.quad("DecoPrint", [(xs[0], y, z0), (xs[1], y, z0), (xs[1], y, z0 + h), (xs[0], y, z0 + h)], uv)
        if back:
            self.quad("DecoPrint", [(xs[1], y - facing * 0.01, z0), (xs[0], y - facing * 0.01, z0),
                                    (xs[0], y - facing * 0.01, z0 + h), (xs[1], y - facing * 0.01, z0 + h)], uv)


    # ------------------------------------------------------------ props
    def light(self, p):
        H = 8.6 * M
        self.box("Plinth", (0, 0, 0.03 * M - 0.02), (0.55 * M, 0.55 * M, 0.06 * M + 0.04))
        self.cyl("Pole", (0, 0, 0.09 * M), 0.2 * M, 0.06 * M, segs=12, mat="PoleSteel")             # base flange
        for a in range(4):                                                                         # anchor bolts
            ang = a * math.pi / 2 + math.pi / 4
            self.cyl("Pole", (math.cos(ang) * 0.15 * M, math.sin(ang) * 0.15 * M, 0.14 * M), 0.025 * M, 0.06 * M, segs=6, mat="PoleSteel")
        self.cyl("Pole", (0, 0, 0.12 * M + 0.3 * M), 0.17 * M, 0.6 * M, segs=8, r2=0.13 * M, mat="PoleSteel")   # base cover
        self.cyl("Pole", (0, 0, 0.7 * M + 0.03 * M), 0.14 * M, 0.06 * M, segs=8, mat="PoleSteel")            # cover lip
        self.cyl("Pole", (0, 0, (0.72 * M + H) / 2), 0.115 * M, H - 0.72 * M, segs=10, r2=0.065 * M, mat="PoleSteel")
        # curved arm out over the road (-Y), rising at the end
        pts = []
        for i in range(8):
            t = i / 7
            pts.append((0, -2.3 * M * t, H - 0.3 * M + 0.9 * M * math.sin(t * math.pi / 2) - 0.25 * M * t * t))
        self.tube("Pole", pts, 0.06 * M, 0.045 * M, segs=8, mat="PoleSteel")
        self.rod("Pole", (0, 0, H - 1.0 * M), (0, -0.9 * M, H - 0.15 * M + 0.35 * M), 0.025 * M, segs=6, mat="PoleSteel")  # brace
        ex, ez = -2.3 * M, H - 0.3 * M + 0.9 * M - 0.25 * M
        # cobra head: a tapered shell, lens underneath, photocell on top
        bmh = (0, ex - 0.32 * M)
        self.frustum("Pole", bmh, ez - 0.06 * M, ez + 0.1 * M, 0.36 * M, 0.82 * M, 0.24 * M, 0.66 * M, mat="PoleSteel")
        self.cyl("Pole", (0, ex - 0.2 * M, ez + 0.14 * M), 0.05 * M, 0.06 * M, segs=8, mat="PoleSteel")
        self.n_lamp += 1
        name = f"StreetLamp{self.n_lamp}"
        self.box(name, (0, ex - 0.36 * M, ez - 0.08 * M), (0.26 * M, 0.56 * M, 0.04 * M), mat="Light")
        self.K.lamps.append(name)
        self.col((0, 0, 0.36 * M), (0.5 * M, 0.5 * M, 0.72 * M))
        self.col((0, 0, (0.72 * M + H) / 2), (0.22 * M, 0.22 * M, H - 0.72 * M))

    def grate(self, s=1.3 * M):
        x0, y0, x1, y1 = 0, 0, 1, 1
        self.quad("Grate", [(-s / 2, -s / 2, 0.03), (s / 2, -s / 2, 0.03), (s / 2, s / 2, 0.03), (-s / 2, s / 2, 0.03)],
                  ((x0, y0), (x1, y0), (x1, y1), (x0, y1)))
        for k in (-1, 1):                                                       # cast frame (edges)
            self.box("Iron", (0, k * s / 2, 0.02), (s + 0.06 * M, 0.06 * M, 0.05), mat="IronBlack")
            self.box("Iron", (k * s / 2, 0, 0.02), (0.06 * M, s - 0.06 * M, 0.05), mat="IronBlack")

    def palm(self, p):
        rng = random.Random(p.get("seed", 1))
        self.grate()
        w = self.w((0, 0, 0))
        self.K.palm(w.x, w.y, w.z, rng.uniform(8.5, 11) * M, (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6)), rng)
        self.col((0, 0, 1.2 * M), (0.42 * M, 0.42 * M, 2.4 * M), "Wood")

    def tree(self, p):
        """Shade tree: tapered trunk splitting into limbs, a dark leafy core and ~30 crossed
        see-through leaf cards round it (LeafCard*, alpha cut-out in game)."""
        rng = random.Random(p.get("seed", 1))
        self.grate()
        h = rng.uniform(6.5, 8.0) * M                 # canopy top
        fork = rng.uniform(2.0, 2.6) * M
        cz, rx, rzh = h - 2.2 * M, rng.uniform(2.4, 2.9) * M, 2.0 * M     # canopy ellipsoid
        self.cyl("Bark", (0, 0, fork / 2), 0.17 * M, fork, segs=8, r2=0.13 * M)
        self.cyl("Bark", (0, 0, 0.12 * M), 0.24 * M, 0.24 * M, segs=8, r2=0.17 * M)        # root flare
        self.col((0, 0, fork / 2), (0.34 * M, 0.34 * M, fork), "Wood")
        top = Vector((0, 0, fork - 0.05 * M))
        for i in range(4):
            a = i / 4 * math.tau + rng.uniform(-0.35, 0.35)
            mid = top + Vector((math.cos(a) * rx * 0.35, math.sin(a) * rx * 0.35, 1.3 * M))
            end = mid + Vector((math.cos(a) * rx * 0.3, math.sin(a) * rx * 0.3, 1.1 * M))
            self.rod("Bark", tuple(top), tuple(mid), 0.085 * M, segs=6)
            self.rod("Bark", tuple(mid), tuple(end), 0.05 * M, segs=5)
        core, cards = self.leaf_parts()
        bm = self.K.bm(core, "Leaves")
        r = bmesh_icosphere(bm, 2, self.w((0, 0, cz)), (rx * 0.78, rx * 0.78, rzh * 0.78), rng)
        for k in range(30):
            # points on the ellipsoid shell, more on top; each a card facing outward-ish
            u, v = rng.uniform(0, math.tau), rng.uniform(-0.35, 1.0)
            d = Vector((math.cos(u) * math.sqrt(1 - v * v), math.sin(u) * math.sqrt(1 - v * v), v))
            c = Vector((0, 0, cz)) + Vector((d.x * rx * 0.85, d.y * rx * 0.85, d.z * rzh * 0.85))
            size = rng.uniform(1.5, 2.1) * M
            yaw = u + rng.uniform(-0.6, 0.6)
            for j in range(2):                        # two crossed cards per tuft
                ang = yaw + j * math.pi / 2
                t = Vector((math.cos(ang), math.sin(ang), 0))
                tilt = Vector((0, 0, 1)) + Vector((d.x, d.y, 0)) * rng.uniform(0.0, 0.5)
                tilt.normalize()
                a0, a1 = c - t * size / 2, c + t * size / 2
                lo, hi = -tilt * size * 0.45, tilt * size * 0.55
                quad = [a0 + lo, a1 + lo, a1 + hi, a0 + hi]
                uv = ((0, 0), (1, 0), (1, 1), (0, 1))
                self.quad(cards, [tuple(q) for q in quad], uv, mat="LeafCard")
                self.quad(cards, [tuple(q) for q in quad[::-1]], uv[::-1], mat="LeafCard")

    def leaf_parts(self):
        """(core part, card part) for the next tree; a new pair every 8 trees (20k tri cap)."""
        self.leaf_count += 1
        if self.leaf_count > 8:
            self.leaf_count, self.leaf_i = 1, self.leaf_i + 1
        sfx = "" if self.leaf_i == 0 else "BCDEF"[self.leaf_i - 1]
        return f"Leaf{sfx}", f"LeafCard{sfx}"

    def bin(self, p):
        R, H = 0.3 * M, 0.92 * M
        self.cyl("Bin", (0, 0, 0.02 * M), R + 0.03 * M, 0.04 * M, segs=12, mat="BinGreen")              # base plate
        self.cyl("BinLiner", (0, 0, 0.05 * M + 0.42 * M), R - 0.04 * M, 0.84 * M, segs=12, mat="IronBlack")
        n = 18
        for i in range(n):                                                                        # steel slats
            a = i / n * math.tau
            self.box("Bin", (math.cos(a) * R, math.sin(a) * R, 0.06 * M + 0.4 * M), (0.075 * M, 0.025 * M, 0.8 * M), rz=a + math.pi / 2, mat="BinGreen")
        for z in (0.12 * M, 0.82 * M):                                                            # hoops
            self.cyl("Bin", (0, 0, z), R + 0.02 * M, 0.05 * M, segs=16, mat="BinGreen")
        self.cyl("Bin", (0, 0, H - 0.02 * M), R + 0.04 * M, 0.06 * M, segs=16, mat="BinGreen")    # rim
        self.cyl("Bin", (0, 0, H + 0.08 * M), R + 0.02 * M, 0.14 * M, segs=16, r2=0.12 * M, mat="BinGreen")  # dome lid
        self.cyl("Bin", (0, 0, H + 0.17 * M), 0.12 * M, 0.04 * M, segs=12, mat="BinGreen")
        # label wrapped round the slats on the sidewalk side (local +Y faces the buildings):
        # a curved strip of facets lying on the slats, so nothing stands off the bin
        x0, y0, x1, y1 = ATLAS["BinLabel"]
        n_f, span = 8, math.radians(80)
        self.cyl("Bin", (0, 0, 0.545 * M), R + 0.015 * M, 0.15 * M, segs=18, mat="BinGreen")      # solid label band
        rl = R + 0.03 * M
        for k in range(n_f):
            a0 = math.pi / 2 + span / 2 - k * span / n_f
            a1 = a0 - span / n_f
            u0, u1 = x1 - (x1 - x0) * k / n_f, x1 - (x1 - x0) * (k + 1) / n_f
            p0 = (math.cos(a0) * rl, math.sin(a0) * rl)
            p1 = (math.cos(a1) * rl, math.sin(a1) * rl)
            z0, z1 = 0.49 * M, 0.6 * M
            self.quad("DecoPrint", [(p1[0], p1[1], z0), (p0[0], p0[1], z0), (p0[0], p0[1], z1), (p1[0], p1[1], z1)],
                      ((u1, 1 - y1), (u0, 1 - y1), (u0, 1 - y0), (u1, 1 - y0)))
        self.col((0, 0, 0.55 * M), (0.66 * M, 0.66 * M, 1.1 * M))

    def bench(self, p):
        L = 1.9 * M
        # cast-iron end frames + a middle one: profile in (y, z), front = -Y
        frame = [(-0.30, 0.0), (-0.24, 0.0), (-0.18, 0.40), (0.14, 0.40), (0.20, 0.0), (0.26, 0.0), (0.22, 0.43),
                 (0.30, 0.86), (0.25, 0.87), (0.16, 0.46), (-0.22, 0.46)]
        prof = [(y * M, z * M) for y, z in frame]
        for x in (-L / 2 + 0.12 * M, 0, L / 2 - 0.12 * M):
            self.prism("Iron", prof, x - 0.03 * M, x + 0.03 * M, mat="IronBlack")
        for k in range(4):                                                     # seat slats (small gaps)
            y = -0.2 * M + k * 0.115 * M
            self.box("Bench", (0, y, 0.475 * M), (L, 0.1 * M, 0.035 * M), mat="BenchWood")
        for k in range(3):                                                     # backrest boards, leaning back
            t = 0.55 + k * 0.13
            y, z = (0.16 + (t - 0.46) * (0.14 / 0.40)) * M + 0.035 * M, t * M
            self.box("Bench", (0, y, z), (L, 0.03 * M, 0.1 * M), mat="BenchWood")
        for x in (-L / 2 + 0.12 * M, L / 2 - 0.12 * M):                        # anchor plates
            self.box("Iron", (x, 0, 0.01), (0.1 * M, 0.62 * M, 0.04), mat="IronBlack")
        self.col((0, -0.02 * M, 0.25 * M), (L, 0.54 * M, 0.5 * M), "Wood")              # seat: sit or stand on it
        self.col((0, 0.24 * M, 0.68 * M), (L, 0.1 * M, 0.36 * M), "Wood")               # backrest

    def hydrant(self, p):
        self.cyl("MetalRed", (0, 0, 0.03 * M), 0.17 * M, 0.06 * M, segs=12, mat="HydrantRed")
        for a in range(6):
            ang = a / 6 * math.tau
            self.cyl("MetalYellow", (math.cos(ang) * 0.14 * M, math.sin(ang) * 0.14 * M, 0.07 * M), 0.018 * M, 0.03 * M, segs=6, mat="SafetyYellow")
        self.cyl("MetalRed", (0, 0, 0.06 * M + 0.28 * M), 0.12 * M, 0.56 * M, segs=14, r2=0.11 * M, mat="HydrantRed")
        self.cyl("MetalRed", (0, 0, 0.64 * M), 0.135 * M, 0.06 * M, segs=14, mat="HydrantRed")       # bonnet flange
        self.cyl("MetalYellow", (0, 0, 0.72 * M), 0.12 * M, 0.12 * M, segs=14, r2=0.06 * M, mat="SafetyYellow")  # bonnet
        self.cyl("MetalYellow", (0, 0, 0.81 * M), 0.035 * M, 0.06 * M, segs=5, mat="SafetyYellow")   # operating nut
        for sx in (-1, 1):                                                      # hose nozzles
            self.rod("MetalRed", (sx * 0.1 * M, 0, 0.45 * M), (sx * 0.2 * M, 0, 0.45 * M), 0.045 * M, segs=10, mat="HydrantRed")
            self.rod("MetalYellow", (sx * 0.2 * M, 0, 0.45 * M), (sx * 0.24 * M, 0, 0.45 * M), 0.055 * M, segs=6, mat="SafetyYellow")
        self.rod("MetalRed", (0, -0.1 * M, 0.38 * M), (0, -0.21 * M, 0.38 * M), 0.07 * M, segs=12, mat="HydrantRed")   # pumper nozzle
        self.rod("MetalYellow", (0, -0.21 * M, 0.38 * M), (0, -0.26 * M, 0.38 * M), 0.08 * M, segs=6, mat="SafetyYellow")
        self.col((0, 0, 0.42 * M), (0.36 * M, 0.36 * M, 0.84 * M))

    def newsboxes(self, p):
        rng = random.Random(p.get("seed", 3))
        n = p.get("n", 2)
        kinds = rng.sample([("MetalNewsB", "NewsBlue", "News0"), ("MetalNewsR", "NewsRed", "News1"), ("MetalNewsA", "NewsAmber", "News2")], n)
        W = 0.52 * M
        for i, (part, mat, face) in enumerate(kinds):
            x = (i - (n - 1) / 2) * (W + 0.05 * M)
            for sx in (-1, 1):                                                  # pedestal legs
                self.box("Iron", (x + sx * 0.18 * M, 0, 0.2 * M), (0.04 * M, 0.36 * M, 0.4 * M), mat="IronBlack")
            self.box("Iron", (x, 0, 0.03), (W, 0.42 * M, 0.06), mat="IronBlack")
            self.box(part, (x, 0, 0.4 * M + 0.33 * M), (W, 0.42 * M, 0.66 * M), mat=mat)
            self.frustum(part, (x, 0.02 * M), 1.06 * M, 1.12 * M, W + 0.02 * M, 0.46 * M, W - 0.04 * M, 0.38 * M, mat=mat)
            self.printed(face, x, -0.211 * M - 0.005, 0.42 * M, W - 0.04 * M, 0.62 * M, facing=-1)
        self.col((0, 0, 0.56 * M), (n * (W + 0.05 * M), 0.46 * M, 1.12 * M))

    def meter(self, p):
        self.cyl("PoleGalv", (0, 0, 0.55 * M), 0.035 * M, 1.1 * M, segs=8, mat="PoleGalv")
        self.cyl("PoleGalv", (0, 0, 0.02 * M), 0.07 * M, 0.04 * M, segs=8, mat="PoleGalv")
        self.box("MetalMeter", (0, 0, 1.28 * M), (0.2 * M, 0.15 * M, 0.36 * M), mat="SignalBody")
        self.cyl("MetalMeter", (0, 0, 1.47 * M), 0.1 * M, 0.04 * M, segs=10, mat="SignalBody")
        # face toward the sidewalk (+Y): the payer stands there
        self.printed("MeterFace", 0, 0.076 * M, 1.12 * M, 0.17 * M, 0.3 * M, facing=1)
        self.col((0, 0, 0.75 * M), (0.14 * M, 0.14 * M, 1.5 * M))

    def mailbox(self, p):
        W, D = 0.55 * M, 0.5 * M
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box("Mailbox", (sx * 0.22 * M, sy * 0.18 * M, 0.15 * M), (0.05 * M, 0.05 * M, 0.3 * M), mat="MailBlue")
        prof = [(-D / 2, 0.3 * M), (D / 2, 0.3 * M), (D / 2, 1.05 * M)] + \
               [(math.cos(t) * D / 2, 1.05 * M + math.sin(t) * 0.18 * M) for t in [k / 6 * math.pi for k in range(1, 6)]] + \
               [(-D / 2, 1.05 * M)]
        self.prism("Mailbox", prof, -W / 2, W / 2, mat="MailBlue")
        self.box("Iron", (0, -D / 2 - 0.02 * M, 1.0 * M), (0.36 * M, 0.06 * M, 0.08 * M), mat="IronBlack")   # pull handle / slot
        self.printed("MailLabel", 0, -D / 2 - 0.005, 0.62 * M, 0.42 * M, 0.17 * M, facing=-1)
        self.col((0, 0, 0.62 * M), (W, D, 1.24 * M))

    def cabinet(self, p):
        self.box("Plinth", (0, 0, 0.08 * M), (1.0 * M, 0.6 * M, 0.16 * M + 0.02))
        self.box("MetalCab", (0, 0, 0.16 * M + 0.65 * M), (0.86 * M, 0.48 * M, 1.3 * M), mat="CabGrey")
        self.box("MetalCab", (0, 0, 1.49 * M), (0.94 * M, 0.56 * M, 0.06 * M), mat="CabGrey")     # rain cap
        self.box("Iron", (0, -0.245 * M, 0.82 * M), (0.01 * M, 0.02 * M, 1.2 * M), mat="IronBlack")  # door seam
        for sx in (-1, 1):
            self.box("Iron", (sx * 0.06 * M, -0.25 * M, 0.85 * M), (0.03 * M, 0.03 * M, 0.12 * M), mat="IronBlack")  # handles
        self.printed("CabLabel", -0.2 * M, -0.241 * M - 0.005, 0.9 * M, 0.34 * M, 0.2 * M, facing=-1)
        for k in range(5):                                                      # side vents
            self.box("Iron", (0.431 * M, 0, 1.1 * M + k * 0.05 * M), (0.01 * M, 0.3 * M, 0.02 * M), mat="IronBlack")
        self.col((0, 0, 0.76 * M), (0.94 * M, 0.56 * M, 1.52 * M))

    def sign_post(self, h=2.9 * M):
        self.cyl("PoleGalv", (0, 0, h / 2), 0.035 * M, h, segs=8, mat="PoleGalv")
        self.col((0, 0, h / 2), (0.1 * M, 0.1 * M, h))
        self.cyl("PoleGalv", (0, 0, h + 0.02 * M), 0.045 * M, 0.04 * M, segs=8, mat="PoleGalv")

    def travel_face(self, p):
        """Local x direction of the sign plate normal: signs face the oncoming traffic on this side."""
        # Right-hand traffic: E-W road, south side (front -Z) carries eastbound (+X) traffic.
        return -p["hz"], p["hx"]                   # travel = front turned 90 deg (Roblox x, z)

    def plate(self, region, w, h, z, p, double=False):
        """Sign plate perpendicular to the road, facing traffic that drives toward it."""
        tx, tz = self.travel_face(p)
        # plate normal = -travel (Roblox) -> Blender (tx, -tz) negated
        n = Vector((tx, -tz, 0))                    # -travel (Roblox) as a Blender vector
        loc = self.T.inverted().to_3x3() @ n
        ax = "x" if abs(loc.x) > abs(loc.y) else "y"
        s = 1 if (loc.x if ax == "x" else loc.y) > 0 else -1
        x0, y0, x1, y1 = ATLAS[region]
        uv = ((x0, 1 - y1), (x1, 1 - y1), (x1, 1 - y0), (x0, 1 - y0))
        off = 0.05 * M * s
        if ax == "x":
            ys = (-w / 2, w / 2) if s > 0 else (w / 2, -w / 2)
            self.box("PoleGalv", (0, 0, z + h / 2), (0.03 * M, w + 0.04 * M, h + 0.04 * M), mat="PoleGalv")
            self.quad("DecoPrint", [(off, ys[0], z), (off, ys[1], z), (off, ys[1], z + h), (off, ys[0], z + h)], uv)
            if double:
                self.quad("DecoPrint", [(-off, ys[1], z), (-off, ys[0], z), (-off, ys[0], z + h), (-off, ys[1], z + h)], uv)
        else:
            xs = (w / 2, -w / 2) if s > 0 else (-w / 2, w / 2)
            self.box("PoleGalv", (0, 0, z + h / 2), (w + 0.04 * M, 0.03 * M, h + 0.04 * M), mat="PoleGalv")
            self.quad("DecoPrint", [(xs[0], off, z), (xs[1], off, z), (xs[1], off, z + h), (xs[0], off, z + h)], uv)
            if double:
                self.quad("DecoPrint", [(xs[1], -off, z), (xs[0], -off, z), (xs[0], -off, z + h), (xs[1], -off, z + h)], uv)

    def speed(self, p):
        self.sign_post(2.6 * M)
        self.plate("Speed", 0.6 * M, 0.8 * M, 1.7 * M, p)

    def busflag(self, p):
        self.sign_post(2.9 * M)
        self.plate("BusFlag", 0.45 * M, 0.66 * M, 2.15 * M, p, double=True)

    def busstop(self, p):
        L, D, H = 4.2 * M, 1.5 * M, 2.5 * M
        # four posts, glass back wall, side panel with an ad, roof, bench inside
        for x in (-L / 2, L / 2):
            for y in (-D / 2 + 0.05 * M, D / 2 - 0.05 * M):
                self.box("Pole", (x, y, H / 2), (0.08 * M, 0.08 * M, H), mat="PoleSteel")
        self.box("Pole", (0, D / 2 - 0.05 * M, H - 0.04 * M), (L, 0.08 * M, 0.08 * M), mat="PoleSteel")
        self.box("Pole", (0, D / 2 - 0.05 * M, 0.12 * M), (L, 0.06 * M, 0.06 * M), mat="PoleSteel")
        for k in range(3):                                                     # back glass panes
            x = -L / 2 + (k + 0.5) * L / 3
            self.box("ClearGlassBus", (x, D / 2 - 0.05 * M, H / 2 + 0.05 * M), (L / 3 - 0.1 * M, 0.02 * M, H - 0.3 * M), mat="ShelterGlass")
            if k:
                self.box("Pole", (-L / 2 + k * L / 3, D / 2 - 0.05 * M, H / 2), (0.05 * M, 0.06 * M, H - 0.1 * M), mat="PoleSteel")
        # ad panel on the right end (double-sided, lit box frame)
        self.box("MetalAdFrame", (L / 2, 0.05 * M, 1.2 * M), (0.14 * M, 1.12 * M, 1.8 * M), mat="SignalBody")
        x0, y0, x1, y1 = ATLAS["BusAd"]
        uv = ((x0, 1 - y1), (x1, 1 - y1), (x1, 1 - y0), (x0, 1 - y0))
        for s in (-1, 1):
            xp = L / 2 + s * 0.075 * M
            ys = (0.05 * M - 0.5 * M, 0.05 * M + 0.5 * M) if s > 0 else (0.05 * M + 0.5 * M, 0.05 * M - 0.5 * M)
            self.quad("DecoPrint", [(xp, ys[0], 0.4 * M), (xp, ys[1], 0.4 * M), (xp, ys[1], 2.0 * M), (xp, ys[0], 2.0 * M)], uv)
        # roof: thin steel tray with glass insert, a little overhang toward the road
        self.box("Pole", (0, -0.1 * M, H + 0.05 * M), (L + 0.3 * M, D + 0.4 * M, 0.1 * M), mat="PoleSteel")
        self.box("ClearGlassBusRoof", (0, -0.1 * M, H + 0.11 * M), (L, D + 0.1 * M, 0.02 * M), mat="ShelterGlass")
        # bench along the back glass, facing the road
        for k in range(3):
            self.box("Bench", (-0.3 * M, D / 2 - 0.55 * M + k * 0.13 * M, 0.47 * M), (L * 0.6, 0.11 * M, 0.04 * M), mat="BenchWood")
        for x in (-0.3 * M - L * 0.27, -0.3 * M + L * 0.27):
            self.box("Iron", (x, D / 2 - 0.42 * M, 0.23 * M), (0.06 * M, 0.36 * M, 0.45 * M), mat="IronBlack")
        for x in (-L / 2, L / 2):
            for y in (-D / 2 + 0.05 * M, D / 2 - 0.05 * M):
                self.col((x, y, H / 2), (0.12 * M, 0.12 * M, H))
        self.col((0, D / 2 - 0.05 * M, H / 2), (L, 0.1 * M, H), "Glass")                  # back glass
        self.col((L / 2, 0.05 * M, 1.2 * M), (0.16 * M, 1.12 * M, 1.8 * M))                # ad panel
        self.col((0, -0.1 * M, H + 0.06 * M), (L + 0.3 * M, D + 0.4 * M, 0.14 * M))        # roof
        self.col((-0.3 * M, D / 2 - 0.42 * M, 0.25 * M), (L * 0.6, 0.42 * M, 0.5 * M), "Wood")

    # ------------------------------------------------------------ intersection props (world space)
    def signal(self, p):
        """Mast-arm signal on a corner, heads facing traffic travelling (dx, dz) (Roblox)."""
        dx, dz = p["dx"], p["dz"]
        # Blender vectors: travel d, heads face -d, arm runs to the left of travel (over its lanes)
        d = Vector((-dx, dz, 0))
        right = Vector((dz, dx, 0))          # Roblox right (-dz, dx) -> Blender (dz, dx)
        self.T = Matrix.Translation((-p["x"], p["z"], p["y"]))
        self.rz = 0.0
        H = 6.2 * M
        self.box("Plinth", (0, 0, 0.0), (0.7 * M, 0.7 * M, 0.12 * M))
        self.cyl("PoleGalv", (0, 0, 0.1 * M), 0.22 * M, 0.08 * M, segs=12, mat="PoleGalv")
        self.cyl("PoleGalv", (0, 0, H / 2 + 0.1 * M), 0.15 * M, H, segs=10, r2=0.1 * M, mat="PoleGalv")
        self.cyl("PoleGalv", (0, 0, H + 0.35 * M), 0.08 * M, 0.5 * M, segs=8, mat="PoleGalv")
        self.col((0, 0, H / 2), (0.32 * M, 0.32 * M, H))
        self.col((0, 0, 0.0), (0.7 * M, 0.7 * M, 0.12 * M), "Concrete")
        arm = p["arm"]
        a0 = Vector((0, 0, H - 0.2 * M))
        a1 = a0 - right * arm
        self.rod("PoleGalv", tuple(a0 - right * 0.1 * M), tuple(a1), 0.07 * M, segs=8, mat="PoleGalv")
        self.box("PoleGalv", tuple(a0 - right * 0.12 * M), (0.36 * M, 0.36 * M, 0.42 * M), mat="PoleGalv")   # arm clamp
        self.rod("PoleGalv", tuple(a0 + Vector((0, 0, 1.0 * M))), tuple(a0 - right * arm * 0.35), 0.03 * M, segs=6, mat="PoleGalv")
        phase = p["phase"]
        for t in (0.35, 0.83):
            c = a0 - right * arm * t - Vector((0, 0, 0.75 * M))
            self.head(self.w(c), d, phase)
            # hanger: from inside the head's top, through the arm
            self.rod("PoleGalv", tuple(c + Vector((0, 0, 0.45 * M))), tuple(a0 - right * arm * t + Vector((0, 0, 0.08 * M))), 0.035 * M, segs=6, mat="PoleGalv")
            self.box("PoleGalv", tuple(a0 - right * arm * t), (0.2 * M, 0.2 * M, 0.2 * M), mat="PoleGalv")   # clamp on the arm
        # a third head on the pole itself, at driver height, on two brackets that reach into it
        hc = Vector((0, 0, 3.2 * M)) - right * 0.5 * M
        for dz in (-0.35 * M, 0.35 * M):
            self.rod("PoleGalv", (0, 0, 3.2 * M + dz), tuple(hc + Vector((0, 0, dz))), 0.04 * M, segs=6, mat="PoleGalv")
            self.cyl("PoleGalv", (0, 0, 3.2 * M + dz), 0.14 * M, 0.1 * M, segs=10, mat="PoleGalv")             # pole band
        self.head(self.w(hc), d, phase)
        # street name blades on top of the pole: one along each street
        names = p.get("blades") or []
        if names:
            self.blade(names[0], self.w((0, 0, H + 0.45 * M)), axis=Vector((1, 0, 0)))     # E-W street runs along x
            self.blade(names[1], self.w((0, 0, H + 0.75 * M)), axis=Vector((0, 1, 0)))     # N-S street runs along y

    def head(self, c, d, phase):
        """3-lens signal head centred at c (Blender), lenses facing -d."""
        f = -d                                  # facing
        side = Vector((-f.y, f.x, 0))
        def at(u, v, w):                        # u along side, v along facing, w up
            return c + side * u + f * v + Vector((0, 0, w))
        bm_box = lambda part, cc, s, mat: self.K.box(part, tuple(cc), (s[0], s[1], s[2]), rz=math.atan2(side.y, side.x), mat=mat)
        bm_box("MetalSignalHead", at(0, 0, 0), (0.36 * M, 0.3 * M, 1.05 * M), "SignalYellow")
        bm_box("MetalSignal", at(0, -0.17 * M, 0), (0.62 * M, 0.02 * M, 1.3 * M), "SignalBody")       # backplate
        bm_box("MetalSignalHead", at(0, -0.17 * M, 0), (0.66 * M, 0.015 * M, 1.34 * M), "SignalYellow")  # retro border
        for k, col in enumerate(("Red", "Amber", "Green")):
            w = (1 - k) * 0.33 * M
            self.K.cyl_along(f"Signal{phase}{col}", tuple(at(0, 0.16 * M, w)), tuple(at(0, 0.18 * M, w)), 0.12 * M, segs=12, mat=f"Lens{col}")
            bm_box("MetalSignalHead", at(0, 0.25 * M, w + 0.12 * M), (0.3 * M, 0.2 * M, 0.02 * M), "SignalYellow")  # visor
            for s in (-1, 1):
                bm_box("MetalSignalHead", at(s * 0.14 * M, 0.25 * M, w + 0.02 * M), (0.02 * M, 0.2 * M, 0.2 * M), "SignalYellow")

    def blade(self, text, c, axis):
        x0, y0, x1, y1 = ATLAS[f"Blade_{text}"]
        uv = ((x0, 1 - y1), (x1, 1 - y1), (x1, 1 - y0), (x0, 1 - y0))
        L, H = 1.6 * M, 0.26 * M
        n = Vector((-axis.y, axis.x, 0))
        self.K.box("PoleGalv", tuple(c), (L, 0.02 * M, H), rz=math.atan2(axis.y, axis.x), mat="PoleGalv")
        for s in (-1, 1):
            o = c + n * s * 0.012 * M
            a, b = (o - axis * L / 2, o + axis * L / 2) if s < 0 else (o + axis * L / 2, o - axis * L / 2)
            # seen from -n (s=-1): left->right = -axis -> +axis
            self.K.quad("DecoPrint", [tuple(a - Vector((0, 0, H / 2))), tuple(b - Vector((0, 0, H / 2))),
                                      tuple(b + Vector((0, 0, H / 2))), tuple(a + Vector((0, 0, H / 2)))], uv)
        self.K.cyl("PoleGalv", tuple(c - Vector((0, 0, H / 2 + 0.05 * M))), 0.04 * M, 0.1 * M, segs=6, mat="PoleGalv")

    def stop(self, p):
        dx, dz = p["dx"], p["dz"]
        d = Vector((-dx, dz, 0))
        self.T = Matrix.Translation((-p["x"], p["z"], p["y"]))
        self.rz = 0.0
        H = 3.1 * M
        self.cyl("PoleGalv", (0, 0, H / 2), 0.035 * M, H, segs=8, mat="PoleGalv")
        self.col((0, 0, H / 2), (0.1 * M, 0.1 * M, H))
        # octagon plate facing -d at 2.1 m
        f = -d
        side = Vector((-f.y, f.x, 0))
        c = Vector((-p["x"], p["z"], p["y"] + 2.1 * M)) + f * 0.05 * M
        r = 0.38 * M
        x0, y0, x1, y1 = ATLAS["Stop"]
        bm = self.K.bm("DecoPrint")
        uvl = bm.loops.layers.uv.active
        pts = []
        for k in range(8):
            a = math.radians(22.5 + 45 * k)
            pts.append((math.cos(a), math.sin(a)))
        verts = [bm.verts.new(tuple(c + side * (u * r) + Vector((0, 0, v * r)))) for u, v in pts]
        face = bm.faces.new(verts)
        for l, (u, v) in zip(face.loops, pts):
            l[uvl].uv = (x0 + (u * 0.5 + 0.5) * (x1 - x0), (1 - y1) + (v * 0.5 + 0.5) * (y1 - y0))
        bmb = self.K.bm("PoleGalv")
        back = [bmb.verts.new(tuple(c - f * 0.02 * M + side * (-u * r) + Vector((0, 0, v * r)))) for u, v in pts]
        bmb.faces.new(back[::-1])
        for i in range(8):
            j = (i + 1) % 8
            bmb.faces.new([back[i], back[j], bmb.verts.new(tuple(c - f * 0.005 * M + side * (-pts[j][0] * r) + Vector((0, 0, pts[j][1] * r)))),
                           bmb.verts.new(tuple(c - f * 0.005 * M + side * (-pts[i][0] * r) + Vector((0, 0, pts[i][1] * r))))])
        names = p.get("blades") or []
        if names:
            base = Vector((-p["x"], p["z"], p["y"] + H))
            self.blade(names[0], base + Vector((0, 0, 0.1 * M)), axis=Vector((1, 0, 0)))
            self.blade(names[1], base + Vector((0, 0, 0.4 * M)), axis=Vector((0, 1, 0)))

    # ------------------------------------------------------------ build
    def build(self, props):
        for p in props:
            k = p["kind"]
            if k not in ("Signal", "StopSign"):
                self.place(p)
            {"Light": self.light, "Palm": self.palm, "Tree": self.tree, "Bin": self.bin, "Bench": self.bench,
             "Hydrant": self.hydrant, "NewsBoxes": self.newsboxes, "Meter": self.meter, "Mailbox": self.mailbox,
             "Cabinet": self.cabinet, "Speed": self.speed, "BusFlag": self.busflag, "BusStop": self.busstop,
             "Signal": self.signal, "StopSign": self.stop}[k](p)
        self.K.finish(keep_normals=("Palm",) + LEAF_PARTS)
        meta = self.K.export()
        meta["collider_boxes"] = self.cols
        json.dump(meta, open(os.path.join(self.K.out, "meta.json"), "w"), indent=1)
        return meta


def render(K, props):
    """Close-up shots of a few props + one street overview."""
    K.render_setup(A["samples"], A["res"])
    seen = set()
    for p in props:
        k = p["kind"]
        if k in seen or k in ("Meter", "BusFlag", "Speed", "Hydrant", "Cabinet", "Mailbox"):
            continue
        seen.add(k)
        x, y, z = -p["x"], p["z"], p["y"]
        fx, fy = (-p.get("hx", 0), p.get("hz", 1)) if "hx" in p else (p["dx"], -p["dz"])
        side = Vector((-fy, fx, 0))
        target = Vector((x, y, z + 1.5 * M))
        loc = target + Vector((fx, fy, 0)) * 7 * M + side * 5 * M + Vector((0, 0, 2.5 * M))
        K.shot(f"{k}", tuple(loc), tuple(target), lens=28, size=(1200, 800))


if __name__ == "__main__":
    for name, props in LAYOUT.items():
        if ONLY and name != ONLY:
            continue
        S = Street(name)
        S.build(props)
        if A["render"]:
            render(S.K, props)
