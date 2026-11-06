"""Writes src/workspace/City.model.json: the ground, streets and spawn of the tulevo city.

  python3 tools/build_city_map.py

The city is built one building at a time. Buildings are Blender models loaded by
src/server/CityBuildings.server.luau (list in src/shared/CityLayout.luau); this file only
holds the flat parts: ground, sidewalks, roads (tagged Road so the radar, full map and GPS
see them), lane lines and the spawn.

Layout (studs, Roblox axes, +Z = south on the map):
  Arkwell Bank tower at the origin, entrance facing -Z (north) onto Vault Avenue.
  Vault Avenue runs east-west in front of it; two cross streets and a back street make a
  block loop round the tower so the GPS has a route. Spawn is across the avenue, facing it.
"""
import json
import os

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
EXTENT = 600         # roads run out to +-EXTENT


def part(name, size, pos, color, material="Concrete", tags=None, rot=0, **extra):
    p = {"name": name, "className": "Part", "properties": {
        "Anchored": True, "Size": list(size), "Color": color, "Material": material,
        "TopSurface": "Smooth", "BottomSurface": "Smooth",
        "CFrame": {"position": list(pos), "orientation": [0, rot, 0]}}}
    p["properties"].update(extra)
    if tags:
        p["tags"] = tags
    return p


children = []
# base ground (big, so the edge of the world is far away)
children.append(part("Ground", (2400, 2, 2400), (0, -1, 0), GROUND, "Concrete"))

# roads: E-W avenue + back street, N-S cross streets; slightly different heights avoid z-fighting
roads = [
    ("VaultAvenue", (2 * EXTENT, 0.2, ROAD_W), (0, 0.1, AVE_Z)),
    ("BackStreet", (2 * EXTENT, 0.2, ROAD_W), (0, 0.1, BACK_Z)),
    ("WestStreet", (ROAD_W, 0.2, 2 * EXTENT), (-BLOCK_X, 0.104, 0)),
    ("EastStreet", (ROAD_W, 0.2, 2 * EXTENT), (BLOCK_X, 0.104, 0)),
]
for name, size, pos in roads:
    children.append(part(name, size, pos, ASPHALT, "Asphalt", tags=["Road"]))

# sidewalks: raised kerb slabs along both sides of every road, cut at the crossings
# (not tagged; the map shows roads only)
kerb = 0.6
R = ROAD_W / 2


def spans(cross):
    cuts = sorted(cross)
    edges = [-EXTENT] + [c for x in cuts for c in (x - R, x + R)] + [EXTENT]
    return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]


for name, size, pos in roads:
    along_x = size[0] > size[2]
    for k, (a, b) in enumerate(spans((-BLOCK_X, BLOCK_X) if along_x else (AVE_Z, BACK_Z))):
        for side in (-1, 1):
            off = side * (R + SIDE_W / 2)
            if along_x:
                children.append(part(f"{name}Walk{k}{'N' if side < 0 else 'S'}", (b - a, kerb, SIDE_W),
                                     ((a + b) / 2, kerb / 2, pos[2] + off), SIDEWALK))
            else:
                children.append(part(f"{name}Walk{k}{'W' if side < 0 else 'E'}", (SIDE_W, kerb, b - a),
                                     (pos[0] + off, kerb / 2, (a + b) / 2), SIDEWALK))

# the tower block itself: one paved plaza between the four sidewalks
inner_x = BLOCK_X - R - SIDE_W
inner_z0, inner_z1 = AVE_Z + R + SIDE_W, BACK_Z - R - SIDE_W
children.append(part("BankPlaza", (2 * inner_x, kerb, inner_z1 - inner_z0), (0, kerb / 2, (inner_z0 + inner_z1) / 2), "#A3A39D", "Pavement"))

# lane lines: solid double yellow centre + dashed white lane dividers, stopping at crossings
lines = []
for name, size, pos in roads:
    along_x = size[0] > size[2]
    for a, b in spans((-BLOCK_X, BLOCK_X) if along_x else (AVE_Z, BACK_Z)):
        a, b = a + SIDE_W, b - SIDE_W  # stop short of the crosswalk area
        if b - a < 10:
            continue
        marks = [((a + b) / 2, b - a, off, LINE_Y) for off in (-0.5, 0.5)]
        v = a
        while v + 8 <= b:
            marks += [(v + 4, 8, off, LINE_W) for off in (-R / 2, R / 2)]
            v += 24
        for c, length, off, color in marks:
            if along_x:
                lines.append(part("L", (length, 0.05, 0.4), (c, 0.22, pos[2] + off), color, "SmoothPlastic", CanCollide=False))
            else:
                lines.append(part("L", (0.4, 0.05, length), (pos[0] + off, 0.22, c), color, "SmoothPlastic", CanCollide=False))
children.append({"name": "Lines", "className": "Folder", "children": lines})

# spawn: far sidewalk of Vault Avenue, facing the tower (+Z)
children.append(part("Spawn", (10, 1, 10), (0, kerb + 0.5, AVE_Z - ROAD_W / 2 - SIDE_W / 2), ASPHALT, "Asphalt",
                     rot=180, Transparency=1, CanCollide=False, Duration=0))
# paved lot behind the spawn for the test cars and showcase
children.append(part("SpawnLot", (80, kerb, 40), (0, kerb / 2, AVE_Z - R - SIDE_W - 20), "#45474A", "Asphalt"))

json.dump({"className": "Folder", "children": children}, open(OUT, "w"), indent=1)
print(f"wrote {OUT}: {len(children)} parts + {len(lines)} lines")
