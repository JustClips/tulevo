"""Where the street furniture goes: lights, trees, bins, benches, hydrants, news boxes, meters,
bus stops, street signs, stop signs and traffic signals along every city sidewalk.

  python3 tools/street_layout.py      -> art/blender/cityfill/street_layout.json

Reads the road layout and the placed buildings from tools/build_city_map.py, so props follow
the streets and stay off driveways, store lots, crossings and corners. The Blender script
art/blender/cityfill/build_street.py turns the json into one merged model per street
(Street<Road>, plus StreetCorners for the intersections); build_city_map places them at the
world origin.

Units: Roblox studs. Each prop: kind, x, z (Roblox), y (ground), hx, hz = unit vector pointing
from the prop to the road (its "front"), plus kind options.
"""
import json
import math
import os
import random
import runpy
import io
import contextlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "blender", "cityfill", "street_layout.json")

with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path(os.path.join(ROOT, "tools", "build_city_map.py"))
KERB = 0.6
EXTENT = G["EXTENT"]
CITY = ("VaultAvenue", "BackStreet", "NorthStreet", "SouthStreet", "WestStreet", "EastStreet")
DOWNTOWN = ("VaultAvenue", "BackStreet", "WestStreet", "EastStreet")
ROADS = {n: (s, p) for n, s, p in G["roads"]}

# driveway / lot fronts that must stay clear: north-facing house keys (offsets from the lot x);
# *_S keys mirror them (from the "Build GTA-style city map" thread, 2026-11-07)
DRIVE = {"HouseA": (-27.7, -15.5), "HouseB": (-25.2, -7.2), "HouseC": (-29.2, -9.0), "HouseD": (-27.4, -7.9)}
# extra clear stretches: (road, side, u0, u1). side: N/S for east-west roads, W/E for north-south
CLEAR = [
    ("BackStreet", "S", -350, -150),        # Kestrel gas station forecourt
    ("WestStreet", "W", 160, 330),          # Kestrel gas station side entry
    ("VaultAvenue", "S", -232, -150),       # Palmview Motel driveway
    ("BackStreet", "S", 360, 472),          # The Marlowe garage
    ("BackStreet", "S", 545, 575),          # police station drives (Bellmont thread, 2026-11-07)
    ("BackStreet", "S", 600, 630),
    ("VaultAvenue", "N", -84, 84),          # main spawn plaza (it has its own lamps, bus stop, benches)
]
# bus stops: (road, side, u)
BUS = [("VaultAvenue", "S", 430), ("VaultAvenue", "N", -430), ("BackStreet", "N", 250),
       ("BackStreet", "S", -480), ("EastStreet", "E", -260), ("WestStreet", "W", -300)]
# extra driveways added by tools/build_city_map.py for the new city-fill buildings (meta "driveways")


def side_of(road, x, z):
    s, p = ROADS[road]
    if s[0] > s[2]:
        return "N" if z < p[2] else "S"
    return "W" if x < p[0] else "E"


def nearest_ew(z):
    return min(("VaultAvenue", "BackStreet", "NorthStreet", "SouthStreet"), key=lambda r: abs(ROADS[r][1][2] - z))


def building_clears():
    out = []
    for name, model, at, *rest in G["BUILDINGS"]:
        base = model[:-2] if model.endswith("_S") else model
        x, _, z = at
        if base in DRIVE:
            a, b = DRIVE[base]
            if model.endswith("_S"):
                a, b = -b, -a
            road = nearest_ew(z)
            out.append((road, side_of(road, x, z), x + a - 3, x + b + 3))
        elif base == "Store":
            road = nearest_ew(z)
            out.append((road, side_of(road, x, z), x - 50, x + 50))
        # new city-fill buildings carry their driveways in meta.json (Blender x, model-local)
        meta_p = os.path.join(ROOT, "art", "models", model, "meta.json")
        if os.path.exists(meta_p):
            meta = json.load(open(meta_p))
            for d in meta.get("driveways", []):
                # d = [blender x0, x1, "road side" N|S|E|W of the model]; Roblox x = at.x - blender x
                x0, x1 = sorted((x - d[0], x - d[1]))
                # the drive is on the street on that side of the lot (a lot through the block has both)
                road = nearest_ew(z + (90 if d[2] == "S" else -90))
                out.append((road, side_of(road, x, z), x0 - 3, x1 + 3))
    return out


def main():
    rng = random.Random(11)
    clears = CLEAR + building_clears()
    props = {}          # model -> list
    corners = []

    def add(model, kind, x, z, hx, hz, **kw):
        props.setdefault(model, []).append({"kind": kind, "x": round(x, 3), "z": round(z, 3), "y": KERB,
                                            "hx": round(hx, 4), "hz": round(hz, 4), **kw})

    for road in CITY:
        size, pos = ROADS[road]
        along_x = size[0] > size[2]
        half = min(size[0], size[2]) / 2
        sw = G["SIDEWALK_W"].get(road, G["SIDE_W"])
        down = road in DOWNTOWN
        model = f"Street{road}"
        for si, side in enumerate(("N", "S") if along_x else ("W", "E")):
            sgn = -1 if side in ("N", "W") else 1
            # (u along the road, offset from the road centre) -> Roblox x, z; front = toward the road
            def at(u, off):
                return (u, pos[2] + sgn * off) if along_x else (pos[0] + sgn * off, u)
            hx, hz = (0, -sgn) if along_x else (-sgn, 0)
            my_clear = [(a, b) for r, s_, a, b in clears if r == road and s_ == side]
            for spi, (a, b) in enumerate(G["spans"](size, pos)):
                a, b = max(a, -EXTENT), min(b, EXTENT)
                if b - a < 40:
                    continue
                # corner squares belong to the crossing street; keep the crosswalk ramps clear
                ends_cross = [abs(a) < EXTENT - 1, abs(b) < EXTENT - 1]
                u0 = a + (sw + 6 if ends_cross[0] else 6)
                u1 = b - (sw + 6 if ends_cross[1] else 6)
                used = []           # (u, half length) along the kerb line

                def free(u, r, line="kerb"):
                    if not (u0 <= u - r and u + r <= u1):
                        return False
                    if any(c0 - r <= u <= c1 + r for c0, c1 in my_clear):
                        return False
                    return all(abs(u - v) > r + w for v, w, ln in used if ln == line or line == "any" or ln == "any")

                def take(u, r, line="kerb"):
                    used.append((u, r, line))

                kerb_off = half + (2.2 if down else 1.8)
                # bus stop first (it needs the most room)
                for r_, s_, ub in BUS:
                    if r_ == road and s_ == side and u0 < ub < u1:
                        x, z = at(ub, half + 9.5)
                        add(model, "BusStop", x, z, hx, hz)
                        take(ub, 12, "any")
                        x, z = at(ub - 9, kerb_off)
                        add(model, "BusFlag", x, z, hx, hz)
                # street lights, staggered between the two sides
                step = 84 if down else 100
                n = max(1, int((u1 - u0) / step))
                gap = (u1 - u0) / n
                lights = []
                for i in range(n + 1):
                    u = u0 + (i + (0.5 if si else 0.0)) * gap
                    if u > u1 + 0.1:
                        continue
                    for du in (0, 6, -6, 12, -12, 18, -18):
                        if free(u + du, 1.5):
                            x, z = at(u + du, kerb_off)
                            add(model, "Light", x, z, hx, hz, palm=False)
                            take(u + du, 1.5)
                            lights.append(u + du)
                            break
                # hydrant near one end, alternating
                for du in range(0, 60, 6):
                    u = (u0 + 8 + du) if si == 0 else (u1 - 8 - du)
                    if free(u, 1.5):
                        x, z = at(u, kerb_off)
                        add(model, "Hydrant", x, z, hx, hz)
                        take(u, 1.5)
                        break
                if down:
                    # street trees between the lights (palms on Vault Avenue, shade trees elsewhere)
                    for la, lb in zip(lights, lights[1:]):
                        u = (la + lb) / 2
                        if free(u, 4):
                            x, z = at(u, kerb_off + 0.6)
                            add(model, "Palm" if road == "VaultAvenue" else "Tree", x, z, hx, hz, seed=rng.randint(0, 9999))
                            take(u, 4)
                    # bins at both ends and mid-block
                    for u in (u0 + 14, u1 - 14, (u0 + u1) / 2 + 10):
                        for du in (0, 5, -5, 10, -10):
                            if free(u + du, 1.6):
                                x, z = at(u + du, kerb_off)
                                add(model, "Bin", x, z, hx, hz)
                                take(u + du, 1.6)
                                break
                    # news boxes near one corner (front to the sidewalk)
                    for du in range(0, 50, 5):
                        u = (u1 - 24 - du) if si == 0 else (u0 + 24 + du)
                        if free(u, 4.5):
                            x, z = at(u, kerb_off)
                            add(model, "NewsBoxes", x, z, -hx, -hz, n=rng.choice((2, 3)), seed=rng.randint(0, 99))
                            take(u, 4.5)
                            break
                    # benches facing the street, every ~200 studs
                    k = int((u1 - u0) / 200)
                    for i in range(k):
                        u = u0 + (i + 0.5) * (u1 - u0) / max(k, 1) + 20
                        for du in (0, 8, -8, 16, -16):
                            if free(u + du, 4, "bench") and free(u + du, 2):
                                x, z = at(u + du, half + 6.0)
                                add(model, "Bench", x, z, hx, hz)
                                take(u + du, 4, "bench")
                                break
                    # parking meters on the two avenues near downtown
                    if road in ("VaultAvenue", "BackStreet"):
                        u = u0 + 10
                        while u < u1 - 10:
                            if abs(u) < 420 and free(u, 1.0):
                                x, z = at(u, kerb_off - 0.4)
                                add(model, "Meter", x, z, hx, hz)
                                take(u, 1.0)
                            u += 22
                    # a mailbox and a utility cabinet once per block side
                    for kind, r in (("Mailbox", 1.8), ("Cabinet", 2.2)):
                        if (kind == "Mailbox" and (spi + si) % 2) or (kind == "Cabinet" and (spi + si + 1) % 3):
                            continue
                        for du in range(0, 200, 7):
                            u = (u0 + u1) / 2 + (du if kind == "Mailbox" else -du) * (1 if si else -1)
                            if free(u, r):
                                x, z = at(u, kerb_off)
                                add(model, kind, x, z, -hx, -hz)
                                take(u, r)
                                break
                else:
                    # residential: one bin per block side
                    for du in range(0, 120, 6):
                        u = (u0 + u1) / 2 + du * (1 if si else -1)
                        if free(u, 1.6):
                            x, z = at(u, kerb_off)
                            add(model, "Bin", x, z, hx, hz)
                            take(u, 1.6)
                            break
                # speed limit sign once per block side, near the start in the travel direction
                for du in range(0, 80, 5):
                    u = (u0 + 30 + du) if sgn > 0 else (u1 - 30 - du)
                    if free(u, 1.0):
                        x, z = at(u, kerb_off)
                        add(model, "Speed", x, z, hx, hz)
                        take(u, 1.0)
                        break

    # intersections: traffic signals downtown, stop signs where a residential street meets one
    ew = [r for r in CITY if ROADS[r][0][0] > ROADS[r][0][2]]
    ns = [r for r in CITY if r not in ew]
    names = {"VaultAvenue": "VAULT AVE", "BackStreet": "BACK ST", "WestStreet": "WEST ST", "EastStreet": "EAST ST",
             "NorthStreet": "NORTH ST", "SouthStreet": "SOUTH ST"}
    for r1 in ew:
        for r2 in ns:
            (s1, p1), (s2, p2) = ROADS[r1], ROADS[r2]
            cx, cz = p2[0], p1[2]
            h1, h2 = s1[2] / 2, s2[0] / 2           # half widths (E-W road along z, N-S road along x)
            sw1 = G["SIDEWALK_W"].get(r1, G["SIDE_W"])
            sw2 = G["SIDEWALK_W"].get(r2, G["SIDE_W"])
            signal = r1 in DOWNTOWN and r2 in DOWNTOWN
            # one pole per corner; each serves the traffic arriving from the opposite side
            # (far-side signals). Travel direction d with right-hand traffic: the far-right corner
            # is centre + d * (half of the crossing road) + right(d) * (half of its own road).
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rx, rz = -dz, dx                     # right of travel (+X east, +Z south, Y up)
                along = h2 if dx else h1             # half width of the road being crossed
                own = h1 if dx else h2               # half width of the road travelled
                cxp = cx + dx * (along + 2.6) + rx * (own + 2.6)
                czp = cz + dz * (along + 2.6) + rz * (own + 2.6)
                phase = "EW" if dx else "NS"
                if signal:
                    corners.append({"kind": "Signal", "x": round(cxp, 3), "z": round(czp, 3), "y": KERB,
                                    "dx": dx, "dz": dz, "arm": own + 1, "phase": phase,
                                    "blades": [names[r1], names[r2]] if (dx, dz) == (1, 0) else []})
                else:
                    on_res = (r1 not in DOWNTOWN and dx) or (r2 not in DOWNTOWN and dz)
                    if on_res:
                        # stop sign at the near-right corner, facing the arriving driver
                        sx = cx - dx * (along + 2.6) + rx * (own + 2.0)
                        sz = cz - dz * (along + 2.6) + rz * (own + 2.0)
                        corners.append({"kind": "StopSign", "x": round(sx, 3), "z": round(sz, 3), "y": KERB,
                                        "dx": dx, "dz": dz, "blades": [names[r1], names[r2]] if dx else []})
    props["StreetCorners"] = corners
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(props, open(OUT, "w"), indent=0)
    for m, ps in props.items():
        kinds = {}
        for p in ps:
            kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
        print(m, kinds)


if __name__ == "__main__":
    main()
