"""Writes src/workspace/City.model.json: the ground, streets and spawn of the tulevo city.

  python3 tools/build_city_map.py

The city is built one building at a time. Buildings are Blender models (art/models/<Model>,
uploaded with tools/upload_models.py) listed in BUILDINGS below. Each becomes an empty Model
under City/Buildings with attributes LiveSyncAsset (asset id) + LiveSyncBoxCenter; the
LiveSync plugin (v5+) loads the mesh into it in edit mode, and
src/server/CityBuildings.server.luau loads it at run time if it is still empty.
Everything else here is flat: ground, sidewalks, roads (tagged Road so the radar, full map
and GPS see them), lane lines and the spawn.

Layout (studs, Roblox axes, +Z = south on the map):
  Arkwell Bank tower at the origin, entrance facing -Z (north) onto Vault Avenue.
  Vault Avenue runs east-west in front of it; two cross streets and a back street make a
  block loop round the tower so the GPS has a route.
  Main spawn: a plaza across Vault Avenue (SpawnPlaza_S, fountain + WELCOME TO TULEVO), Spawn
  on its compass inlay facing the avenue.
  Gang neighborhoods (GANGS, original names) on two outer residential streets: Vipers (yellow)
  on North Street east, Red Crowns on South Street east, Grove Kings (green) on South Street west. Each hood: a corner store, a
  fenced basketball court with the gang spawn (SpawnLocation <Gang>Spawn, attribute Gang) and
  rows of houses. Gang looks are texture variants: BUILDINGS entries may carry a 4th element
  {part: variant} that picks "<part>@<variant>" from the model's textures.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import road_dressing  # noqa: E402  realistic street asphalt, wear, cracks, crosswalks (tools/road_dressing.py)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "src", "workspace", "City.model.json")

ASPHALT = "#2E2F31"
SIDEWALK = "#8C8D89"
GROUND = "#5B5D5A"
LINE_W = "#D8D8D2"
LINE_Y = "#D9A63A"

ROAD_W = 44          # 2 lanes each way
SIDE_W = 18          # sidewalk width
BLOCK_X = 120        # cross streets at x = +-BLOCK_X
AVE_Z = -132         # Vault Avenue centre
BACK_Z = 132         # back street centre
EXTENT = 640         # roads run out to +-EXTENT
NORTH_Z = -480       # North Street (Vipers hood)
SOUTH_Z = 480        # South Street (Red Crowns + Grove Kings hoods)
RES_W, RES_SIDE = 30, 12   # residential streets: one lane each way, narrower sidewalks


# name, model key (art/models/<Model>), where its Blender origin (ground centre) goes
BUILDINGS = [
    ("ArkwellBank", "BankTower", (0, 0.6, 0)),
    # outer corner of West Street x Back Street, pumps facing Back Street, price sign on the corner
    ("KestrelGas", "GasStation", (-246.4, 0.5, 244)),
    # LA-style office towers (fronts face -Z / north onto the street in front)
    ("HollisTower", "OfficeStone", (0, 0.6, 240)),      # stepped limestone, across Back Street from the bank
    ("MeridianPlaza", "OfficeDark", (250, 0.6, 226)),   # black glass slab, corner of East St x Back St
    ("CrestlineTower", "OfficeRound", (240, 0.6, -40)),  # rounded glass tower on Vault Avenue, east of the bank
    # lots sit 0.3 above the ground (a step down from the 0.6 kerb), fronts face north onto the street
    ("PalmviewMotel", "Motel", (-262, 0.3, -12)),       # west of West Street, facing Vault Avenue
    ("TheMarlowe", "Apartments", (430, 0.3, 211.6)),    # east of Meridian Plaza, facing Back Street
    # main spawn plaza across Vault Avenue, turned to face it (south)
    ("MainSpawnPlaza", "SpawnPlaza_S", (0, 0.6, AVE_Z - ROAD_W / 2 - SIDE_W - 72)),
]

# ---------------------------------------------------------------- gang neighborhoods
# lots are 16 m (57.6) wide houses, 26 m (93.6) deep; the store is 93.6 wide, the court 115.2.
# Lots south of a street face north (default build), lots north of it face south (<Model>_S).
LOT_D = 93.6
GANGS = {
    # gang: street z, first lot x (next to the downtown cross street), direction, wall paints
    "Vipers": (NORTH_Z, 172, 1, ("Butter", "Tan", "Peach", "Sand", "Butter", "Cream")),
    "RedCrowns": (SOUTH_Z, 172, 1, ("Rose", "Brick", "Blush", "Rose", "Sand", "Cream")),
    "GroveKings": (SOUTH_Z, -172, -1, ("Mint", "Sage", "Teal", "Mint", "Sky", "Cream")),
}
# Each street side has 345.6 studs of house lots after the court / store. Mixed house types
# (A bungalow, B two-floor, C ranch with carport, D Spanish courtyard) with tree-filled side
# yards between some of them, so the row reads like a real street. Widths in studs.
LOT_W = {"HouseA": 57.6, "HouseB": 57.6, "HouseC": 72.0, "HouseD": 57.6, "SideYard": 21.6}
ROWS = {
    "Vipers": (("HouseC", "SideYard", "HouseA", "HouseD", "SideYard", "HouseB", "HouseA"),
               ("HouseD", "HouseA", "SideYard", "HouseC", "HouseB", "SideYard", "HouseA")),
    "RedCrowns": (("HouseA", "HouseD", "SideYard", "HouseB", "HouseC", "SideYard", "HouseA"),
                  ("HouseB", "SideYard", "HouseC", "HouseA", "SideYard", "HouseD", "HouseA")),
    "GroveKings": (("HouseD", "SideYard", "HouseC", "HouseA", "HouseB", "SideYard", "HouseD"),
                   ("HouseA", "HouseC", "SideYard", "HouseD", "HouseB", "SideYard", "HouseA")),
}
GANG_SPAWNS = []
for gang, (sz, x0, d, paints) in GANGS.items():
    edge = RES_W / 2 + RES_SIDE + LOT_D / 2
    north, south = ROWS[gang]
    for side, z, lots in ((1, sz + edge, [("Court", 115.2)] + [(h, LOT_W[h]) for h in north]),
                          (-1, sz - edge, [("Store", 93.6)] + [(h, LOT_W[h]) for h in south])):
        assert sum(w for _, w in lots) <= EXTENT - abs(x0) + 0.01, (gang, side)
        x = x0
        n = 0
        for i, (model, w) in enumerate(lots):
            cx = x + d * w / 2
            x += d * w
            key = model if side > 0 else f"{model}_S"
            if model == "Court":
                BUILDINGS.append((f"{gang}Court", key, (cx, 0.3, z), {"CourtPaint": gang, "Tag": gang}))
                GANG_SPAWNS.append((gang, (cx, 0.3, z)))
            elif model == "Store":
                BUILDINGS.append((f"{gang}Store", key, (cx, 0.3, z), {"Walls": paints[3], "Tag": gang}))
            elif model == "SideYard":
                BUILDINGS.append((f"{gang}Yard{'N' if side > 0 else 'S'}{i}", key, (cx, 0.3, z)))
            else:
                n += 1
                BUILDINGS.append((f"{gang}House{'N' if side > 0 else 'S'}{i}", key, (cx, 0.3, z),
                                  {"Walls": paints[(n + (side < 0) * 2) % len(paints)], "Tag": gang}))

# ---------------------------------------------------------------- Fort Halden army base
# (thread "Build realistic army base"; art/blender/army/build_army.py, built with --face E so
# the gate faces the city). West of the city, on the line of Vault Avenue: FortRoad carries the
# avenue on from its west end (x = -EXTENT) to the gate apron, where the model's own asphalt
# starts (a step higher, so nothing is coplanar). Model ground front edge sits at x = -650.
ARMY_M = 3.6
ARMY_AT = (-650 - 68 * ARMY_M, 0.15, AVE_Z)          # model origin; front edge is 68 m in front of it
ARMY_APRON_X = ARMY_AT[0] + 52 * ARMY_M + 1.0       # model asphalt starts 52 m in front (+1 stud overlap)
BUILDINGS.append(("FortHalden", "ArmyBase_E", ARMY_AT, {}, {"MeshNoCollide": True}))

# ---------------------------------------------------------------- street furniture
# (thread "Fill city with buildings and street props"): street lights, trees, bins, benches,
# hydrants, news boxes, meters, bus stops, signs and traffic signals, one merged model per street
# plus StreetCorners for the intersections. tools/street_layout.py places them along the
# sidewalks above; art/blender/cityfill/build_street.py builds them in world coordinates, so each
# model's origin is the world origin.
STREET_MODELS = ("StreetVaultAvenue", "StreetBackStreet", "StreetWestStreet", "StreetEastStreet",
                 "StreetNorthStreet", "StreetSouthStreet", "StreetCorners")
for _m in STREET_MODELS:
    BUILDINGS.append((_m, _m, (0, 0, 0)))

# ---------------------------------------------------------------- Bellmont Hills (rich suburb)
# (thread "Build rich suburbs district"; art/blender/estate/build_estate.py). East of the city:
# Vault Avenue carries on east as Bellmont Drive, Back Street as Crestview Road, and Bellmont Way
# joins them at the far end so the GPS has a loop. Three rows of four 36 x 40 m mansion lots:
# north of Bellmont Drive (facing south, *_S builds), south of it, and south of Crestview Road.
EST_LOT_W, EST_LOT_D = 36 * 3.6, 40 * 3.6
EST_X0 = EXTENT + 22                                 # first lot edge, just past the city's last kerb
EST_X1 = EST_X0 + 4 * EST_LOT_W
EST_WAY_X = EST_X1 + SIDE_W + ROAD_W / 2              # Bellmont Way centre
EST_END = EST_WAY_X + ROAD_W / 2                      # east end of the two drives
EST_ROWS = [
    # lot centre z, facing, models west -> east, wall paints
    (AVE_Z - ROAD_W / 2 - SIDE_W - EST_LOT_D / 2, "S", ("Casa", "Modern", "Villa", "Hacienda"), ("Ivory", "Charcoal", "Sage", "Sand")),
    (AVE_Z + ROAD_W / 2 + SIDE_W + EST_LOT_D / 2, "N", ("Villa", "Hacienda", "Casa", "Modern"), ("Stone", "Blush", "White", "Slate")),
    (BACK_Z + ROAD_W / 2 + SIDE_W + EST_LOT_D / 2, "N", ("Modern", "Casa", "Hacienda", "Villa"), ("White", "Sand", "Ivory", "Ivory")),
]
for r, (z, face, models, paints) in enumerate(EST_ROWS):
    for i, (model, paint) in enumerate(zip(models, paints)):
        key = model if face == "N" else f"{model}_S"
        BUILDINGS.append((f"Bellmont{model}{r}{i}", key, (EST_X0 + (i + 0.5) * EST_LOT_W, 0.3, z),
                          {"Render" if model == "Modern" else "Walls": paint}))

# Tulevo Police Department (thread "Build rich suburbs district"): 32 x 50.8 m lot south of Back
# Street, east of The Marlowe; front (-Z) on the Back Street sidewalk, east edge at x = 640.
POLICE_W, POLICE_D = 32 * 3.6, 50.8 * 3.6
BUILDINGS.append(("TulevoPolice", "Police", (EXTENT - POLICE_W / 2, 0.3, BACK_Z + ROAD_W / 2 + SIDE_W + POLICE_D / 2)))

# paved plazas under the towers, from the kerb to behind the building: name, x0, x1, z0, z1
PLAZAS = [
    ("HollisPlaza", -70, 70, BACK_Z + 22 + 18, 310),
    ("MeridianLot", 160, 330, BACK_Z + 22 + 18, 280),
    ("CrestlinePlaza", 160, 320, AVE_Z + 22 + 18, 10),
]


def part(name, size, pos, color, material="Concrete", tags=None, rot=0, className="Part", **extra):
    p = {"name": name, "className": className, "properties": {
        "Anchored": True, "Size": list(size), "Color": color, "Material": material,
        "TopSurface": "Smooth", "BottomSurface": "Smooth",
        "CFrame": {"position": list(pos), "orientation": [0, rot, 0]}}}
    p["properties"].update(extra)
    if tags:
        p["tags"] = tags
    return p


children = []
# base ground (big, so the edge of the world is far away)
children.append(part("Ground", (2700, 2, 2700), (0, -1, 0), GROUND, "Concrete"))

# roads: E-W avenue + back street + the two outer residential streets, N-S cross streets;
# slightly different heights avoid z-fighting
roads = [
    ("VaultAvenue", (2 * EXTENT, 0.2, ROAD_W), (0, 0.1, AVE_Z)),
    ("BackStreet", (2 * EXTENT, 0.2, ROAD_W), (0, 0.1, BACK_Z)),
    ("NorthStreet", (2 * EXTENT, 0.2, RES_W), (0, 0.1, NORTH_Z)),
    ("SouthStreet", (2 * EXTENT, 0.2, RES_W), (0, 0.1, SOUTH_Z)),
    ("WestStreet", (ROAD_W, 0.2, 2 * EXTENT), (-BLOCK_X, 0.104, 0)),
    ("EastStreet", (ROAD_W, 0.2, 2 * EXTENT), (BLOCK_X, 0.104, 0)),
    # Bellmont Hills: the avenue and the back street carried on east, joined at the far end
    ("BellmontDrive", (EST_END - EXTENT, 0.2, ROAD_W), ((EXTENT + EST_END) / 2, 0.1, AVE_Z)),
    ("CrestviewRoad", (EST_END - EXTENT, 0.2, ROAD_W), ((EXTENT + EST_END) / 2, 0.1, BACK_Z)),
    ("BellmontWay", (ROAD_W, 0.2, BACK_Z - AVE_Z + ROAD_W), (EST_WAY_X, 0.104, 0)),
]
SIDEWALK_W = {"NorthStreet": RES_SIDE, "SouthStreet": RES_SIDE}   # others: SIDE_W
for name, size, pos in roads:
    children.append(road_dressing.style_road(part(name, size, pos, ASPHALT, "Asphalt", tags=["Road"])))

# sidewalks: raised kerb slabs along both sides of every road, cut at the crossings
# (not tagged; the map shows roads only)
kerb = 0.6
R = ROAD_W / 2


def crossings(size, pos):
    """[(centre, half width)] of the roads crossing this one, along its own axis."""
    along_x = size[0] > size[2]
    out = []
    lo = (pos[0] if along_x else pos[2]) - max(size[0], size[2]) / 2
    hi = lo + max(size[0], size[2])
    for _, s2, p2 in roads:
        if (s2[0] > s2[2]) == along_x:
            continue
        if not lo <= (p2[0] if along_x else p2[2]) <= hi:     # crosses the line further along, not this road
            continue
        if along_x and abs(pos[2] - p2[2]) <= s2[2] / 2:
            out.append((p2[0], s2[0] / 2))
        elif not along_x and abs(pos[0] - p2[0]) <= s2[0] / 2:
            out.append((p2[2], s2[2] / 2))
    return sorted(out)


def spans(size, pos):
    along_x = size[0] > size[2]
    lo = (pos[0] if along_x else pos[2]) - max(size[0], size[2]) / 2
    edges = [lo] + [e for c, h in crossings(size, pos) for e in (c - h, c + h)] + [lo + max(size[0], size[2])]
    edges = [min(max(e, lo), lo + max(size[0], size[2])) for e in edges]
    return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2) if edges[i + 1] - edges[i] > 1]


for name, size, pos in roads:
    along_x = size[0] > size[2]
    half, sw = min(size[0], size[2]) / 2, SIDEWALK_W.get(name, SIDE_W)
    for k, (a, b) in enumerate(spans(size, pos)):
        for side in (-1, 1):
            off = side * (half + sw / 2)
            if along_x:
                children.append(part(f"{name}Walk{k}{'N' if side < 0 else 'S'}", (b - a, kerb, sw),
                                     ((a + b) / 2, kerb / 2, pos[2] + off), SIDEWALK))
            else:
                children.append(part(f"{name}Walk{k}{'W' if side < 0 else 'E'}", (sw, kerb, b - a),
                                     (pos[0] + off, kerb / 2, (a + b) / 2), SIDEWALK))

# Fort Halden access road: added after the sidewalks loop (no kerbs out in the country), but
# part of `roads` so it gets lane lines, wear and the radar/GPS Road tag
FORT_ROAD = ("FortRoad", (-EXTENT - ARMY_APRON_X, 0.2, ROAD_W),
             ((-EXTENT + ARMY_APRON_X) / 2, 0.1, AVE_Z))
children.append(road_dressing.style_road(part(*FORT_ROAD, ASPHALT, "Asphalt", tags=["Road"])))
roads.append(FORT_ROAD)

# the tower block itself: one paved plaza between the four sidewalks
inner_x = BLOCK_X - R - SIDE_W
inner_z0, inner_z1 = AVE_Z + R + SIDE_W, BACK_Z - R - SIDE_W
children.append(part("BankPlaza", (2 * inner_x, kerb, inner_z1 - inner_z0), (0, kerb / 2, (inner_z0 + inner_z1) / 2), "#A3A39D", "Pavement"))

# Bellmont Hills grass: green verges round the lots (top 0.15: under the lots, kerbs and roads)
for name, x0, x1, z0, z1 in (
        ("BellmontGreenN", EXTENT, EST_END + 60, -700, AVE_Z - ROAD_W / 2 - SIDE_W),
        ("BellmontGreenMid", EXTENT + 2, EST_WAY_X - ROAD_W / 2 - SIDE_W, AVE_Z + ROAD_W / 2 + SIDE_W, BACK_Z - ROAD_W / 2 - SIDE_W),
        ("BellmontGreenS", EXTENT, EST_END + 60, BACK_Z + ROAD_W / 2 + SIDE_W, 700),
        ("BellmontGreenE", EST_WAY_X + ROAD_W / 2 + SIDE_W, EST_END + 60, AVE_Z - ROAD_W / 2 - SIDE_W, BACK_Z + ROAD_W / 2 + SIDE_W)):
    children.append(part(name, (x1 - x0, 0.15, z1 - z0), ((x0 + x1) / 2, 0.075, (z0 + z1) / 2), "#4E6A33", "Grass"))

for name, x0, x1, z0, z1 in PLAZAS:
    children.append(part(name, (x1 - x0, kerb, z1 - z0), ((x0 + x1) / 2, kerb / 2, (z0 + z1) / 2), "#A3A39D", "Pavement"))

# lane lines: solid double yellow centre + dashed white lane dividers, stopping at crossings
lines = []
for name, size, pos in roads:
    along_x = size[0] > size[2]
    half = min(size[0], size[2]) / 2
    for a, b in spans(size, pos):
        a, b = a + SIDE_W, b - SIDE_W  # stop short of the crosswalk area
        if b - a < 10:
            continue
        marks = [((a + b) / 2, b - a, off, LINE_Y) for off in (-0.5, 0.5)]
        v = a
        while half >= 20 and v + 8 <= b:   # dashed lane dividers on the 4-lane roads only
            marks += [(v + 4, 8, off, LINE_W) for off in (-half / 2, half / 2)]
            v += 24
        for c, length, off, color in marks:
            if along_x:
                lines.append(part("L", (length, 0.05, 0.4), (c, 0.22, pos[2] + off), color, "SmoothPlastic", CanCollide=False))
            else:
                lines.append(part("L", (0.4, 0.05, length), (pos[0] + off, 0.22, c), color, "SmoothPlastic", CanCollide=False))
for i, l in enumerate(lines):
    l["name"] = f"Line{i + 1}"
    road_dressing.style_line(l)
children.append({"name": "Lines", "className": "Folder", "children": lines})
children.append(road_dressing.dress(roads, children))

# main spawn: on the compass inlay of the spawn plaza (11 m from its centre towards the avenue), facing it (+Z)
SPAWN_Z = AVE_Z - R - SIDE_W - 72 + 11 * 3.6
children.append(part("Spawn", (10, 1, 10), (0, kerb + 0.5, SPAWN_Z), ASPHALT, "Asphalt",
                     rot=180, Transparency=1, CanCollide=False, Duration=0, className="SpawnLocation"))
# gang spawns: middle of each hood's court. CharacterSetup spawns a gang member (Team) only on
# spawns whose Gang attribute matches, everyone else on spawns without one.
for gang, (x, y, z) in GANG_SPAWNS:
    children.append(part(f"{gang}Spawn", (12, 1, 12), (x, y + 0.6, z), ASPHALT, "Asphalt", Transparency=1,
                         CanCollide=False, Duration=0, Neutral=False, className="SpawnLocation")
                    | {"attributes": {"Gang": gang}})

# buildings: empty Models the plugin / server fill with the uploaded mesh
def textures_attr(model, variants=None):
    """LiveSyncTextures = JSON { part: image id } from art/models/<model>/textures.json + art/textures.lock.json.
    variants {part: name} swaps in the "<part>@<name>" image (gang paint, tags, court colours)."""
    import hashlib
    tj = os.path.join(ROOT, "art", "models", model, "textures.json")
    tl = os.path.join(ROOT, "art", "textures.lock.json")
    if not (os.path.exists(tj) and os.path.exists(tl)):
        return {}
    tlock = json.load(open(tl))
    ids = {}
    tex = json.load(open(tj))
    for part, rel in tex.items():
        if "@" in part:
            continue
        # exact part name first, then any chosen variant that this part has (the store's many
        # wall pieces WallF1.. all take the "Walls" paint)
        for v in [(variants or {}).get(part)] + list((variants or {}).values()):
            if f"{part}@{v}" in tex:
                rel = tex[f"{part}@{v}"]
                break
        h = hashlib.sha256(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()
        if h in tlock:
            ids[part] = tlock[h]["id"]
    return {"LiveSyncTextures": json.dumps(ids, sort_keys=True, separators=(",", ":"))}



lock = json.load(open(os.path.join(ROOT, "art", "models.lock.json")))
buildings = []
for name, model, at, *rest in BUILDINGS:
    variants = rest[:1] if rest and rest[0] else []
    extra = rest[1] if len(rest) > 1 else {}
    meta = json.load(open(os.path.join(ROOT, "art", "models", model, "meta.json")))
    lo = [min(p["min"][i] for p in meta["parts"].values()) for i in range(3)]
    hi = [max(p["max"][i] for p in meta["parts"].values()) for i in range(3)]
    c = [(a + b) / 2 for a, b in zip(lo, hi)]
    # Blender (x, y, z) -> Roblox (-x, z, y)
    center = [round(at[0] - c[0], 3), round(at[1] + c[2], 3), round(at[2] + c[1], 3)]
    buildings.append({"name": name, "className": "Model", "tags": ["Building"], "attributes": {
        "LiveSyncAsset": lock[model]["id"], "LiveSyncBoxCenter": {"Vector3": center}, "CityModel": model,
        **textures_attr(model, variants[0] if variants else None), **extra}})
children.append({"name": "Buildings", "className": "Folder", "children": buildings})

# Fort Halden collision: the army base meshes never collide in game (MeshNoCollide; merged meshes
# made invisible walls), so these invisible boxes from build_army.py (meta "colliders") do instead
_army = json.load(open(os.path.join(ROOT, "art", "models", "ArmyBase_E", "meta.json")))
children.append({"name": "FortHaldenColliders", "className": "Folder", "children": [
    part(f"{c['name']}{i + 1}", c["size"], [ARMY_AT[k] + c["pos"][k] for k in range(3)], "#808080", "SmoothPlastic",
         Transparency=1, CastShadow=False, CanTouch=False)
    for i, c in enumerate(_army["colliders"])]})

json.dump({"className": "Folder", "children": children}, open(OUT, "w"), indent=1)
print(f"wrote {OUT}: {len(children)} parts + {len(lines)} lines")
