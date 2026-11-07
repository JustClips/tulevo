"""Exact box collision for the city's Blender buildings.

  python3 tools/city_colliders.py [Model ...]     (default: every model placed by build_city_map)
    -> src/server/CityColliders.luau

Why: each Blender part is ONE merged mesh (all the benches, all the fences, every wall piece of
a house...). Roblox builds a MeshPart's collision from a limited number of convex hulls, so a
part made of many separate pieces gets hulls bridging the gaps between them: invisible walls,
players floating next to benches. Instead, this reads every model GLB (art/models/<M>/<M>.glb),
splits each part into its connected pieces and turns each piece into boxes:
  * a box-like piece (wall, slab, post, bench slat) -> one oriented box that fits it
  * a hollow or sloped piece (fountain basin, planter, roof) -> a height field of boxes, so
    the water, the soil and the roof slopes stay where they are
Thin pieces lying in the same plane next to each other (fence pickets, rails, gate bars) merge
into one slab; pieces inside other boxes are dropped.

CityBuildings.server makes these invisible boxes (Folder "Collision" in each building) and turns
collision and queries off on the visible meshes. Doors and gates (Swing*/Slide*/Lift* parts) are
skipped here: they move, so they keep their own collision (Client/CityDoors).

Coordinates: GLB (x, y, z) -> Roblox model space (-x, y, -z), studs.
"""
import json
import math
import os
import re
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "src", "server", "CityColliders.luau")

# parts that never collide (match CityBuildings: decor, plants, lights, water, moving doors)
SKIP_EXACT = {"Frame", "Sill", "WinIron", "Pipe", "Meter", "CandyRack", "FridgeDoors", "Tag", "Leaf", "LeafB",
              "Palm", "Shrub", "Hedge", "Net", "Sconce", "Water", "PriceFace", "ShopLamp", "Agave",
              "Grass", "MeterFace", "BinLabel", "Timetable", "BusDisplay", "AcGrille", "Register", "AtmFace",
              "Coffee", "FreezerTop", "IceFront", "NewsFace"}
SKIP_PREFIX = ("Light", "Lamp", "Neon", "Fx", "Poster", "ShelfGoods", "Deco", "Swing", "Slide", "Lift", "Flower",
               "Tag")
# Roblox material per part name (footsteps, bullet impacts); first match wins
MATERIALS = [
    (r"^(Lawn|Turf|Grass)", "Grass"),
    (r"^(Asphalt|Road|Court)", "Asphalt"),
    (r"^(Wood|Bark|Trunk|Picket|Shutter|Counter|Deck|Bench|Crate|Pallet)", "Wood"),
    (r"^(Iron|Pole|Frame|Mailbox|Bin|AcBody|Dumpster|Metal|Steel|Rail|Gondola|Cooler|Freezer|Atm|Pump|Canopy|Mast"
     r"|ChainLink|Hoop|Backboard|Grill)", "Metal"),
    (r"^(ClearGlass|Glass)", "Glass"),
    (r"^(Tiles|Roof|Shingles|Slate)", "Slate"),
    (r"^(Plastic|Yellow|Red|IceBox|IceBody|Paint)", "Plastic"),
    (r"^(Soil|Dirt|Mulch|Gravel)", "Ground"),
    (r"^(Brick|WallBrick)", "Brick"),
    (r"^(Granite|Stone|Marble|Kerb)", "Granite"),
    (r"^(Tile|ShopFloor)", "Slate"),
]
MAT_NAMES = ["Concrete", "Grass", "Asphalt", "Wood", "Metal", "Glass", "Slate", "Plastic", "Ground", "Brick", "Granite"]

MIN_PIECE = 0.45      # studs: pieces smaller than this in every direction don't collide
THIN = 0.2            # studs: paper-thin pieces (printed faces, glass) are thickened to this
CELL_MIN, CELL_MAX = 0.35, 1.2
QUANT = 0.25          # height-field heights snap to this
FILL_BOX = 0.82       # a piece filling this much of its fitted box is just that box


# ------------------------------------------------------------------ GLB
def load_glb(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen = struct.unpack("<I", data[off:off + 4])[0]
    binbuf = data[off + 8:off + 8 + blen]

    def acc(i):
        a = j["accessors"][i]
        bv = j["bufferViews"][a["bufferView"]]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        comp = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a["componentType"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        stride = bv.get("byteStride")
        if stride and stride != n * np.dtype(comp).itemsize:
            raw = np.frombuffer(binbuf, dtype=np.uint8, count=stride * a["count"], offset=start)
            return np.stack([np.frombuffer(raw[k * stride:k * stride + n * np.dtype(comp).itemsize].tobytes(), comp)
                             for k in range(a["count"])])
        arr = np.frombuffer(binbuf, dtype=comp, count=a["count"] * n, offset=start)
        return arr.reshape(-1, n) if n > 1 else arr

    parts = {}
    for node in j["nodes"]:
        if "mesh" not in node:
            continue
        vs, ts, base = [], [], 0
        for prim in j["meshes"][node["mesh"]]["primitives"]:
            v = acc(prim["attributes"]["POSITION"]).astype(np.float64)
            if "indices" in prim:
                t = acc(prim["indices"]).astype(np.int64).reshape(-1, 3)
            else:
                t = np.arange(len(v)).reshape(-1, 3)
            vs.append(v)
            ts.append(t + base)
            base += len(v)
        v = np.concatenate(vs)
        if node.get("translation"):
            v = v + np.array(node["translation"])
        # GLB -> Roblox model space
        v = v * np.array([-1.0, 1.0, -1.0])
        parts[node["name"]] = (v, np.concatenate(ts))
    return parts


# ------------------------------------------------------------------ pieces
def pieces(v, t):
    """Split a mesh into connected pieces (vertices welded by position)."""
    key = np.round(v * 1000).astype(np.int64)
    _, weld = np.unique(key, axis=0, return_inverse=True)
    weld = weld.reshape(-1)
    tw = weld[t]
    n = weld.max() + 1
    parent = np.arange(n)

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
        return root

    for a, b, c in tw:
        ra, rb, rc = find(a), find(b), find(c)
        if ra != rb:
            parent[rb] = ra
        if ra != rc:
            parent[find(rc)] = ra
    roots = np.array([find(i) for i in range(n)])
    tri_root = roots[tw[:, 0]]
    out = []
    for r in np.unique(tri_root):
        tt = t[tri_root == r]
        out.append(tt)
    return out


def tri_normals(v, t):
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1) / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        n = n / (2 * area[:, None])
    return n, area


def candidate_frames(n, area):
    """Rotation matrices (columns = box axes) to try: world, and frames from the main face normals."""
    up = np.array([0.0, 1.0, 0.0])
    frames = [np.eye(3)]
    ok = area > 1e-9
    n, area = n[ok], area[ok]
    if len(n) == 0:
        return frames
    # distinct normal directions by area (sign-folded)
    folded = n * np.sign(n[:, np.argmax(np.abs(n).sum(0))] + 1e-12)[:, None]
    keyed = {}
    for d, a in zip(np.round(folded, 2), area):
        k = tuple(d)
        keyed[k] = keyed.get(k, 0) + a
    top = [np.array(k) for k, _ in sorted(keyed.items(), key=lambda kv: -kv[1])[:8]]
    top = [d / np.linalg.norm(d) for d in top if np.linalg.norm(d) > 0.5]
    for d in top:
        if abs(d[1]) < 0.05:                       # vertical face: keep the box upright
            x = np.array([d[0], 0, d[2]])
            x /= np.linalg.norm(x)
            frames.append(np.column_stack([x, up, np.cross(x, up)]))
    for i, a in enumerate(top):
        for b in top[i + 1:]:
            if abs(a @ b) < 0.05:
                c = np.cross(a, b)
                frames.append(np.column_stack([a, b, c / np.linalg.norm(c)]))
    return frames


def fit_box(pts, frames):
    best = None
    for R in frames:
        local = pts @ R
        lo, hi = local.min(0), local.max(0)
        vol = np.prod(np.maximum(hi - lo, 1e-3))
        upright = abs(R[1, 1]) > 0.999
        score = vol * (0.98 if upright else 1.0)
        if best is None or score < best[0] - 1e-9:
            best = (score, R, lo, hi)
    _, R, lo, hi = best
    return R, lo, hi


def samples(v, t, step):
    """Points spread over the triangles, about step apart."""
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    edge = np.maximum(np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1)), np.linalg.norm(a - c, axis=1))
    ks = np.clip(np.ceil(edge / step).astype(int), 1, 400)
    out = [a, b, c]
    for k in np.unique(ks):
        if k <= 1:
            continue
        sel = ks == k
        uu, vv = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        m = (uu + vv) <= k
        u, w = uu[m] / k, vv[m] / k
        A, B, C = a[sel], b[sel], c[sel]
        pts = A[:, None, :] + (B - A)[:, None, :] * u[None, :, None] + (C - A)[:, None, :] * w[None, :, None]
        out.append(pts.reshape(-1, 3))
    return np.concatenate(out)


def height_field(v, t, R, lo, hi):
    """Upright box frame R (column 1 = up): columns of [bottom, top] per cell, merged into rectangles.
    Returns [(R, lo, hi)] boxes, and the fill ratio of the fitted box. A cell counts when at least
    half of it is covered (checked on a grid twice as fine), so round edges don't bulge out."""
    ext = hi - lo
    cell = float(np.clip(min(ext[0], ext[2]) / 14, CELL_MIN, CELL_MAX))
    sub = cell / 2
    pts = samples(v, t, sub * 0.45) @ R
    nx, nz = max(1, int(math.ceil(ext[0] / cell))), max(1, int(math.ceil(ext[2] / cell)))
    sx, sz = nx * 2, nz * 2
    ix = np.clip(((pts[:, 0] - lo[0]) / sub).astype(int), 0, sx - 1)
    iz = np.clip(((pts[:, 2] - lo[2]) / sub).astype(int), 0, sz - 1)
    flat = ix * sz + iz
    stop = np.full(sx * sz, -np.inf)
    sbot = np.full(sx * sz, np.inf)
    np.maximum.at(stop, flat, pts[:, 1])
    np.minimum.at(sbot, flat, pts[:, 1])
    stop, sbot = stop.reshape(nx, 2, nz, 2), sbot.reshape(nx, 2, nz, 2)
    count = np.isfinite(stop).sum(axis=(1, 3))
    top = stop.max(axis=(1, 3)).reshape(-1)
    bot = sbot.min(axis=(1, 3)).reshape(-1)
    filled = (count >= 2).reshape(-1)
    vol = np.sum((top[filled] - bot[filled])) * cell * cell
    fill = vol / max(np.prod(np.maximum(ext, 1e-3)), 1e-6)
    tq = np.where(filled, np.ceil((top - lo[1]) / QUANT - 1e-6) * QUANT + lo[1], np.nan).reshape(nx, nz)
    bq = np.where(filled, np.floor((bot - lo[1]) / QUANT + 1e-6) * QUANT + lo[1], np.nan).reshape(nx, nz)
    tq = np.minimum(tq, hi[1])
    bq = np.maximum(bq, lo[1])
    used = ~filled.reshape(nx, nz)
    boxes = []
    for i in range(nx):
        for k in range(nz):
            if used[i, k]:
                continue
            b0, t0 = bq[i, k], tq[i, k]
            # grow along z, then along x, while the cells match
            k1 = k
            while k1 + 1 < nz and not used[i, k1 + 1] and bq[i, k1 + 1] == b0 and tq[i, k1 + 1] == t0:
                k1 += 1
            i1 = i
            while i1 + 1 < nx and all(not used[i1 + 1, kk] and bq[i1 + 1, kk] == b0 and tq[i1 + 1, kk] == t0
                                      for kk in range(k, k1 + 1)):
                i1 += 1
            used[i:i1 + 1, k:k1 + 1] = True
            if t0 - b0 < 0.05:
                t0 = b0 + 0.05
            blo = np.array([lo[0] + i * cell, b0, lo[2] + k * cell])
            bhi = np.array([min(lo[0] + (i1 + 1) * cell, hi[0]), t0, min(lo[2] + (k1 + 1) * cell, hi[2])])
            boxes.append((R, blo, bhi))
    return boxes, fill


def piece_boxes(v, t):
    vi = np.unique(t)
    pts = v[vi]
    ext_world = pts.max(0) - pts.min(0)
    if ext_world.max() < MIN_PIECE:
        return []
    n, area = tri_normals(v, t)
    R, lo, hi = fit_box(pts, candidate_frames(n, area))
    ext = hi - lo
    # paper-thin (printed faces, glass sheets): give them some body
    for ax in range(3):
        if ext[ax] < THIN:
            mid = (lo[ax] + hi[ax]) / 2
            lo[ax], hi[ax] = mid - THIN / 2, mid + THIN / 2
    ext = hi - lo
    upright = abs(R[1, 1]) > 0.999
    if upright and ext[0] > 1.6 and ext[2] > 1.6:
        boxes, fill = height_field(v, t, R, lo, hi)
        if fill < FILL_BOX and len(boxes) > 1:
            return boxes
    return [(R, lo, hi)]


# ------------------------------------------------------------------ boxes -> world AABB tools
def world_box(R, lo, hi):
    c_local = (lo + hi) / 2
    return R @ c_local, R, (hi - lo)


def axis_aligned(R):
    """If R is a permutation of the world axes, return the world size order, else None."""
    a = np.abs(R)
    if np.all((a > 0.999) | (a < 1e-3)):
        return np.argmax(a, axis=0)
    return None


def to_aabb(c, R, s):
    perm = axis_aligned(R)
    if perm is None:
        return None
    size = np.zeros(3)
    size[perm] = s
    return c - size / 2, c + size / 2


def merge_thin(aabbs):
    """Thin boxes in one plane next to each other (fence pickets + rails, gate bars) -> one slab."""
    changed = True
    boxes = [list(b) for b in aabbs]
    while changed:
        changed = False
        out = []
        used = [False] * len(boxes)
        for i in range(len(boxes)):
            if used[i]:
                continue
            lo, hi, mat = boxes[i]
            for j in range(i + 1, len(boxes)):
                if used[j]:
                    continue
                lo2, hi2, mat2 = boxes[j]
                if mat2 != mat:
                    continue
                ulo, uhi = np.minimum(lo, lo2), np.maximum(hi, hi2)
                us = uhi - ulo
                thin_ax = int(np.argmin(us))
                if us[thin_ax] > 0.6:
                    continue
                gap = np.maximum(np.maximum(lo, lo2) - np.minimum(hi, hi2), 0)
                if gap.max() > 0.8:
                    continue
                # the two must overlap in height, or one sits on the other
                if gap[1] > 0.05:
                    continue
                lo, hi = ulo, uhi
                used[j] = True
                changed = True
            out.append([lo, hi, mat])
        boxes = out
    return [tuple(b) for b in boxes]


def drop_contained(items, tol=0.15):
    """items: (lo, hi, ...) AABBs; drop any that sits inside a bigger one."""
    los = np.array([i[0] for i in items])
    his = np.array([i[1] for i in items])
    vol = np.prod(his - los, axis=1)
    keep = []
    order = np.argsort(-vol)
    kept_lo, kept_hi = [], []
    for idx in order:
        lo, hi = los[idx], his[idx]
        if kept_lo:
            KL, KH = np.array(kept_lo), np.array(kept_hi)
            inside = np.all(KL - tol <= lo, axis=1) & np.all(KH + tol >= hi, axis=1)
            if inside.any():
                continue
        kept_lo.append(lo)
        kept_hi.append(hi)
        keep.append(idx)
    return [items[i] for i in sorted(keep)]


def material_of(name):
    for pat, mat in MATERIALS:
        if re.match(pat, name):
            return MAT_NAMES.index(mat)
    return 0


def skip(name):
    base = name.split("@")[0]
    return base in SKIP_EXACT or base.startswith(SKIP_PREFIX)


def model_colliders(path):
    parts = load_glb(path)
    aabbs, rotated = [], []
    ref, ref_vol = None, -1
    for name, (v, t) in parts.items():
        lo, hi = v.min(0), v.max(0)
        vol = np.prod(np.maximum(hi - lo, 0.01))
        if vol > ref_vol and np.all(hi - lo > 0.05):
            ref, ref_vol = (name, lo, hi), vol
        if skip(name):
            continue
        mat = material_of(name)
        for tt in pieces(v, t):
            for R, blo, bhi in piece_boxes(v, tt):
                c, Rw, s = world_box(R, blo, bhi)
                ab = to_aabb(c, Rw, s)
                if ab is not None:
                    aabbs.append((ab[0], ab[1], mat))
                else:
                    rotated.append((c, Rw, s, mat))
    n_raw = len(aabbs) + len(rotated)
    aabbs = merge_thin(aabbs)
    aabbs = drop_contained(aabbs)
    return ref, aabbs, rotated, n_raw


def fmt(x):
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def placed_models():
    src = open(os.path.join(ROOT, "tools", "build_city_map.py")).read()
    names = set(re.findall(r'"([A-Z][A-Za-z]+(?:_S)?)"', src))
    base = os.path.join(ROOT, "art", "models")
    out = []
    for m in sorted(os.listdir(base)):
        meta = os.path.join(base, m, "meta.json")
        if (m in names or m.replace("_S", "") in names) and os.path.exists(meta):
            info = json.load(open(meta))
            # models with their own hand-placed "colliders" (Fort Halden) are left alone
            if "lamps" in info and "colliders" not in info:
                out.append(m)
    return out


def main():
    models = sys.argv[1:] or placed_models()
    existing = {}
    if os.path.exists(OUT) and sys.argv[1:]:
        # keep the other models' boxes when only some are rebuilt
        for m in re.finditer(r"^\t(\w+) = (\{.*?^\t\}),$", open(OUT).read(), re.M | re.S):
            existing[m.group(1)] = m.group(2)
    blocks = dict(existing)
    total = 0
    for m in models:
        path = os.path.join(ROOT, "art", "models", m, f"{m}.glb")
        if not os.path.exists(path):
            print(f"skip {m}: no GLB")
            continue
        ref, aabbs, rotated, n_raw = model_colliders(path)
        rname, rlo, rhi = ref
        lines = [f'\t\tref = "{rname}",', f"\t\trefMin = {{ {', '.join(fmt(x) for x in rlo)} }},",
                 f"\t\trefMax = {{ {', '.join(fmt(x) for x in rhi)} }},", "\t\tboxes = {"]
        for lo, hi, mat in aabbs:
            c, s = (lo + hi) / 2, hi - lo
            lines.append(f"\t\t\t{{ {', '.join(fmt(x) for x in (*c, *s))}, {mat} }},")
        for c, R, s, mat in rotated:
            lines.append(f"\t\t\t{{ {', '.join(fmt(x) for x in (*c, *s))}, {mat}, "
                         f"{', '.join(fmt(x) for x in R.reshape(-1))} }},")
        lines.append("\t\t},")
        blocks[m] = "{\n" + "\n".join(lines) + "\n\t}"
        n = len(aabbs) + len(rotated)
        total += n
        print(f"{m}: {n_raw} pieces -> {n} boxes ({len(rotated)} turned)")
    body = "\n".join(f"\t{k} = {v}," for k, v in sorted(blocks.items()))
    head = ("-- Generated by tools/city_colliders.py from art/models/<M>/<M>.glb. Invisible collision boxes per\n"
            "-- city building, in the model's Roblox space (studs). CityBuildings.server builds them.\n"
            "-- Box = { cx, cy, cz, sx, sy, sz, material [, r00, r01, r02, r10, r11, r12, r20, r21, r22] }\n"
            f"-- material: {', '.join(f'{i} {n}' for i, n in enumerate(MAT_NAMES))}\n")
    with open(OUT, "w") as fh:
        fh.write(head + "return {\n" + body + "\n}\n")
    print(f"wrote {OUT}: {total} boxes in {len(models)} models")


if __name__ == "__main__":
    main()
