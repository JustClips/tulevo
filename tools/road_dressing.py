"""City street look for tools/build_city_map.py: one road type, worn LA-style city asphalt.

    import road_dressing
    road_parts = road_dressing.style_road(part_dict)        # each road Part
    road_dressing.style_line(line_part_dict)                 # each lane line Part
    children.append(road_dressing.dress(roads))              # overlay folder

Textures come from tools/road_textures.py (art/road/tex, CC0 photo scans + generated wear) and
are uploaded by tools/upload_textures.py (ids in art/textures.lock.json, looked up by file hash).
Until every road texture has an id, nothing changes: ready() is False and the helpers no-op.

- Roads get MaterialVariant "TulevoStreet" (src/materials/TulevoStreet.model.json, written here):
  tiling asphalt colour/normal/roughness maps. MaterialVariant maps can only be set by plugins,
  so the LiveSync plugin creates it in Studio and it is saved with the place.
- dress(roads) adds a Folder "RoadDressing" of thin see-through parts carrying Decals/Textures:
  lane wear (oil strip, wheel paths, dusty gutters), big dark/dusty blotches, tar-sealed cracks,
  open cracks, alligator cracking, sawcut patches, oil stains, manholes, and worn crosswalks +
  stop lines at every crossing. Placement is seeded per road name, so it is stable between runs.
  The parts never collide, can't be ray-hit (CanQuery false: car wheels, guns, footsteps ignore
  them) and cast no shadows.
- Image axes: x = along the road, y = across. Overlay parts are rotated so their local X runs
  along the road, which is the Top face's U direction.

Any road width works: lane count = 2 under 40 studs wide, 4 under 60, else 6.
"""
import hashlib
import json
import math
import os
import random

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX_JSON = os.path.join(ROOT, "art", "road", "textures.json")
LOCK = os.path.join(ROOT, "art", "textures.lock.json")
VARIANT = "TulevoStreet"
VARIANT_OUT = os.path.join(ROOT, "src", "materials", VARIANT + ".model.json")
STUDS_PER_TILE = 16

# top-face heights of the layers (road tops are 0.2 / 0.204; lane lines sit above all of these)
Y_LANES, Y_GRIME, Y_PATCH, Y_CRACK, Y_STAIN, Y_MANHOLE, Y_PAINT = 0.212, 0.22, 0.228, 0.236, 0.244, 0.252, 0.262
THICK = 0.01


def _ids():
    if not (os.path.exists(TEX_JSON) and os.path.exists(LOCK)):
        return {}
    lock = json.load(open(LOCK))
    ids = {}
    for name, rel in json.load(open(TEX_JSON)).items():
        h = hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()
        if h in lock:
            ids[name] = "rbxassetid://%d" % lock[h]["id"]
    return ids


IDS = _ids()


def ready():
    return bool(IDS) and len(IDS) == len(json.load(open(TEX_JSON)))


def write_variant():
    """src/materials/TulevoStreet.model.json (MaterialService, see default.project.json)."""
    os.makedirs(os.path.dirname(VARIANT_OUT), exist_ok=True)
    json.dump({"className": "MaterialVariant", "properties": {
        "BaseMaterial": "Asphalt", "StudsPerTile": STUDS_PER_TILE, "MaterialPattern": "Regular",
        "ColorMap": IDS["StreetColor"], "NormalMap": IDS["StreetNormal"], "RoughnessMap": IDS["StreetRough"],
    }}, open(VARIANT_OUT, "w"), indent=1)


def style_road(p):
    """Road Part dict -> uses the street MaterialVariant (white tint so the maps show true colour)."""
    if ready():
        p["properties"].update({"Material": "Asphalt", "MaterialVariant": VARIANT, "Color": "#FFFFFF"})
    return p


def style_line(p):
    """Lane line Part dict -> see-through part carrying a worn, chipped paint Texture in its colour."""
    if not ready():
        return p
    props = p["properties"]
    sx, sy, sz = props["Size"]
    along_x = sx >= sz
    color = props["Color"]
    pos = props["CFrame"]["position"]
    props.update({"Transparency": 1, "CanCollide": False, "CanQuery": False, "CanTouch": False, "CastShadow": False,
                  "Size": [sx, THICK, sz], "CFrame": {"position": [pos[0], Y_PAINT - THICK / 2, pos[2]],
                                                       "orientation": props["CFrame"].get("orientation", [0, 0, 0])}})
    p["children"] = [_texture(IDS["Paint"] if along_x else IDS["PaintV"], 6 if along_x else sx, sz if along_x else 6,
                              color=color, name="Paint")]
    return p


# ---------------------------------------------------------------- parts
def _texture(tex, u, v, color="#FFFFFF", transparency=0, name="Wear"):
    return {"name": name, "className": "Texture", "properties": {
        "Texture": tex, "Face": "Top", "StudsPerTileU": u, "StudsPerTileV": v, "Color3": color,
        "Transparency": transparency}}


def _decal(tex, transparency=0):
    return {"name": "Decal", "className": "Decal", "properties": {"Texture": tex, "Face": "Top", "Transparency": transparency}}


def _overlay(name, length, width, x, z, y_top, yaw, child):
    """Thin invisible part, local X (length) along yaw, top face at y_top."""
    return {"name": name, "className": "Part", "properties": {
        "Anchored": True, "CanCollide": False, "CanQuery": False, "CanTouch": False, "CastShadow": False,
        "Transparency": 1, "Size": [round(length, 3), THICK, round(width, 3)],
        "CFrame": {"position": [round(x, 3), round(y_top - THICK / 2, 4), round(z, 3)], "orientation": [0, yaw, 0]},
        "TopSurface": "Smooth", "BottomSurface": "Smooth"}, "children": [child]}


# ---------------------------------------------------------------- layout
class Road:
    def __init__(self, name, size, pos):
        self.name = name
        self.along_x = size[0] >= size[2]
        self.length = size[0] if self.along_x else size[2]
        self.width = size[2] if self.along_x else size[0]
        self.c_along = pos[0] if self.along_x else pos[2]  # centre along the road
        self.c_across = pos[2] if self.along_x else pos[0]  # centre line position
        self.top = pos[1] + size[1] / 2
        self.lanes = 2 if self.width < 40 else 4 if self.width < 60 else 6
        self.cuts = []  # (lo, hi) along-road intervals taken by crossings

    def world(self, a, c):
        """(along, across) -> world (x, z). across + = toward +Z on E-W roads, +X on N-S roads."""
        return (a, c) if self.along_x else (c, a)

    @property
    def yaw(self):
        # local X along the road: E-W roads unrotated, N-S roads turned 90
        return 0 if self.along_x else 90

    def segments(self):
        lo, hi = self.c_along - self.length / 2, self.c_along + self.length / 2
        out, v = [], lo
        for a, b in sorted(self.cuts):
            if a > v:
                out.append((v, a))
            v = max(v, b)
        if hi > v:
            out.append((v, hi))
        return out


def _crossings(rs):
    boxes = []
    for r in rs:
        for q in rs:
            if not (r.along_x and not q.along_x):
                continue
            # r runs E-W, q runs N-S; overlap if q's x is within r's span and r's z within q's span
            if abs(q.c_across - r.c_along) <= r.length / 2 and abs(r.c_across - q.c_along) <= q.length / 2:
                x0, x1 = q.c_across - q.width / 2, q.c_across + q.width / 2
                z0, z1 = r.c_across - r.width / 2, r.c_across + r.width / 2
                r.cuts.append((x0, x1))
                q.cuts.append((z0, z1))
                boxes.append((r, q, x0, x1, z0, z1))
    return boxes


def dress(roads):
    """roads: [(name, size, pos)] as in build_city_map. Returns the RoadDressing Folder dict."""
    if not ready():
        print("road_dressing: road textures not uploaded yet (python3 tools/upload_textures.py); roads left plain")
        return {"name": "RoadDressing", "className": "Folder", "children": []}
    write_variant()
    rs = [Road(*r) for r in roads]
    boxes = _crossings(rs)
    parts = []
    for r in rs:
        rnd = random.Random(r.name)
        lane_w = r.width / r.lanes
        for s0, s1 in r.segments():
            L = s1 - s0
            if L < 4:
                continue
            mid = (s0 + s1) / 2
            x, z = r.world(mid, r.c_across)
            # lane wear runs the whole segment; offset per segment so seams don't line up
            wear = _texture(IDS["Lanes%d" % r.lanes], 88, r.width)
            wear["properties"]["OffsetStudsU"] = round(rnd.uniform(0, 88), 2)
            parts.append(_overlay("LaneWear", L, r.width, x, z, Y_LANES, r.yaw, wear))
            parts += _scatter(r, s0, s1, rnd, lane_w)
    for r, q, x0, x1, z0, z1 in boxes:
        parts += _crossing(r, q, x0, x1, z0, z1)
    for i, p in enumerate(parts):
        p["name"] = "%s%d" % (p["name"], i + 1)
    return {"name": "RoadDressing", "className": "Folder", "children": parts}


def _scatter(r, s0, s1, rnd, lane_w):
    out = []
    W = r.width
    half = W / 2

    def put(name, tex, length, width, a, c, y, flip=False, yaw_extra=0):
        x, z = r.world(a, r.c_across + c)
        yaw = r.yaw + (180 if flip else 0) + yaw_extra
        out.append(_overlay(name, length, width, x, z, y, yaw, _decal(IDS[tex])))

    # big layers: one free-running cursor each so pieces on the same layer never overlap
    for layer, y, every, make in (
        ("Grime", Y_GRIME, (30, 70), lambda a: ("Grime%d" % rnd.randint(1, 3), W * 1.5, W, 0)),
        ("Tar", Y_CRACK, (20, 90), lambda a: ("Tar%d" % rnd.randint(1, 4), W, W, 0)),
    ):
        a = s0 + rnd.uniform(0, every[1] / 2)
        while True:
            tex, length, width, c = make(a)
            if a + length > s1 + length * 0.15:
                break
            put(layer, tex, length, width, a + length / 2, c, y, flip=rnd.random() < 0.5)
            a += length + rnd.uniform(*every)

    # small things in the lanes: patches, cracks, gator, stains, manholes (per-lane cursors)
    for k in range(r.lanes):
        lane_c = -half + (k + 0.5) * lane_w
        a = s0 + rnd.uniform(4, 30)
        while a < s1 - 12:
            roll = rnd.random()
            if roll < 0.1:
                L, Wd = rnd.uniform(9, 22), rnd.uniform(0.55, 0.85) * lane_w
                put("Patch", "Patch%d" % rnd.randint(1, 3), L, Wd, a + L / 2, lane_c + rnd.uniform(-1, 1), Y_PATCH, flip=rnd.random() < 0.5)
                a += L
            elif roll < 0.5:
                S = rnd.uniform(14, 24)
                put("Crack", "Crack%d" % rnd.randint(1, 3), S, S, a + S / 2, lane_c + rnd.uniform(-2, 2), Y_CRACK + 0.004, yaw_extra=rnd.choice([0, 90, 180, 270]))
                a += S * 0.6
            elif roll < 0.6:
                S = rnd.uniform(12, 20)
                put("Gator", "Gator%d" % rnd.randint(1, 2), S, S * 0.75, a + S / 2, lane_c + rnd.uniform(-1, 1), Y_CRACK + 0.004, flip=rnd.random() < 0.5)
                a += S
            elif roll < 0.88:
                S = rnd.uniform(5, 9)
                put("Stain", "Stain%d" % rnd.randint(1, 3), S * 1.4, S, a + S / 2, lane_c + rnd.uniform(-0.8, 0.8), Y_STAIN, yaw_extra=rnd.choice([0, 180]))
                a += S
            elif roll < 0.95:
                put("Manhole", "Manhole", 3.2, 3.2, a + 2, lane_c + rnd.choice([-2.6, 2.6]), Y_MANHOLE, yaw_extra=rnd.uniform(0, 360))
                a += 4
            a += rnd.uniform(8, 34)
    return out


def _bar(name, length, width, x, z, yaw, y=Y_PAINT, color="#F2F2EC"):
    tex = (_texture(IDS["Paint"], 6, width, color=color, name="Paint") if length >= width
           else _texture(IDS["PaintV"], length, 6, color=color, name="Paint"))
    return _overlay(name, length, width, x, z, y, yaw, tex)


def _crossing(r, q, x0, x1, z0, z1):
    """Worn grime in the box + a zebra crosswalk and a stop line on each approach that has road."""
    out = []
    rnd = random.Random("%s|%s" % (r.name, q.name))
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    out.append(_overlay("Grime", (x1 - x0) * 1.2, (z1 - z0) * 1.2, cx, cz, Y_GRIME, rnd.choice([0, 90, 180, 270]),
                        _decal(IDS["Grime%d" % rnd.randint(1, 3)])))
    out.append(_overlay("Tar", x1 - x0, z1 - z0, cx, cz, Y_CRACK, rnd.choice([0, 90, 180, 270]), _decal(IDS["Tar%d" % rnd.randint(1, 4)])))
    # approaches: (road, the box edge on that side, direction away from the box)
    for road, edge, d, lo, hi in ((r, x1, 1, x0, x1), (r, x0, -1, x0, x1), (q, z1, 1, z0, z1), (q, z0, -1, z0, z1)):
        a_lo, a_hi = road.c_along - road.length / 2, road.c_along + road.length / 2
        if not (a_lo < edge + d * 12 < a_hi):
            continue
        W = road.width
        # zebra bars: 1.6 wide, 8 long (along the road), 1.6 gaps, across the full width
        a = edge + d * 5.5
        n = int((W - 2) // 3.2)
        start = -(n - 1) * 3.2 / 2
        for i in range(n):
            x, z = road.world(a, road.c_across + start + i * 3.2)
            out.append(_bar("Crosswalk", 8, 1.6, x, z, road.yaw))
        # stop line across the lanes that drive into the box (right-hand traffic)
        # heading into the box is -d along; its right side is across = -d on E-W roads, +d on N-S roads
        side = -d if road.along_x else d
        x, z = road.world(edge + d * 10.8, road.c_across + side * W / 4)
        out.append(_bar("StopLine", 0.9, W / 2 - 0.8, x, z, road.yaw))
    return out
