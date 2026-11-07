"""Measure the Roblox "City Prop" models (lamps + traffic signals, src/shared/CityPropIds.luau) and
write src/shared/CityPropInfo.luau, which Server/CityBuildings uses to stand them in the city.

  <blender python> tools/city_prop_scan.py [StreetLight1 TrafficLightPole ...]

Run it with Blender's bundled Python (it borrows Blender's Draco decoder for the v7 meshes), e.g.
  "%LOCALAPPDATA%\\Programs\\blender-5.2.3-windows-x64\\5.2\\python\\bin\\python.exe" tools/city_prop_scan.py
or set BLENDER_DIR to the Blender install folder. Needs env ROBLOXAPIKEY (asset download; never
printed). Downloads are cached in art/out/city_props/.

Per model (all points in the frame of its reference part, the biggest MeshPart, as uploaded):
  foot    bottom centre of the pole      height  model height (studs, unscaled)
  reach   horizontal direction from the pole to the lamp head / along the signal arm
  pole    pole width near the ground (for the invisible collider)
  glow    the lamp's bulb / glass part (smallest part high up): lit at night
  face    signals only: horizontal direction the signal heads face (toward the drivers)
  lenses  signals only: red / amber / green lens centres on the side drivers see, at the front of
          the lens cap { colour, x, y, z, nx, ny, nz, radius }, found through the lens spots of
          the shared signal texture
"""
import gzip
import json
import math
import os
import re
import struct
import sys
import urllib.request
from ctypes import c_bool, c_char_p, c_size_t, c_uint32, c_void_p, cdll

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_anims import CTX, request  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IDS = os.path.join(ROOT, "src", "shared", "CityPropIds.luau")
OUT = os.path.join(ROOT, "src", "shared", "CityPropInfo.luau")
CACHE = os.path.join(ROOT, "art", "out", "city_props")

# the shared signal texture: three painted lenses in one column (u, v from the top), radius in v
SIGNAL_ATLAS = "129011271395835"
LENS_UV = {"Red": (0.8545, 0.0635), "Amber": (0.8545, 0.1553), "Green": (0.8545, 0.2466)}
LENS_RADIUS_V = 25 / 1024


# ------------------------------------------------------------------ small vector helpers
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def unit(a):
    n = length(a)
    return mul(a, 1 / n) if n > 1e-9 else (0.0, 0.0, 0.0)


# ------------------------------------------------------------------ downloads
def fetch(asset_id):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, str(asset_id))
    if not os.path.exists(path):
        code, loc = request("GET", f"https://apis.roblox.com/asset-delivery-api/v1/assetId/{asset_id}")
        if code >= 300:
            raise RuntimeError(f"download {asset_id}: {code} {loc}")
        with urllib.request.urlopen(loc["location"], context=CTX, timeout=120) as r:
            open(path, "wb").write(r.read())
    d = open(path, "rb").read()
    return gzip.decompress(d) if d[:2] == b"\x1f\x8b" else d


# ------------------------------------------------------------------ binary model (.rbxm) reader
def _lz4(src):
    out, i, n = bytearray(), 0, len(src)
    while i < n:
        tok = src[i]; i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b != 255:
                    break
        out += src[i:i + lit]; i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8); i += 2
        ml = tok & 15
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b != 255:
                    break
        start = len(out) - off
        for k in range(ml + 4):
            out.append(out[start + k])
    return bytes(out)


def _cols(data, n, w):
    return [bytes(data[j * n + i] for j in range(w)) for i in range(n)]


def _i32(data, n):
    return [(u >> 1) ^ -(u & 1) for u in (int.from_bytes(b, "big") for b in _cols(data, n, 4))]


def _f32(data, n):
    out = []
    for b in _cols(data, n, 4):
        v = int.from_bytes(b, "big")
        out.append(struct.unpack("<f", struct.pack("<I", ((v >> 1) | ((v & 1) << 31)) & 0xFFFFFFFF))[0])
    return out


def _refs(data, n):
    acc, out = 0, []
    for x in _i32(data, n):
        acc += x
        out.append(acc)
    return out


_AX = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]


def read_rbxm(d):
    """{ref: {ClassName, Name, size, CFrame (pos, rows), MeshId, TextureID, ..., children}}"""
    assert d[:8] == b"<roblox!", "not a binary model"
    pos, classes, inst = 32, {}, {}
    while pos < len(d):
        name = d[pos:pos + 4]
        clen, ulen = struct.unpack("<II", d[pos + 4:pos + 12])
        pos += 16
        body = d[pos:pos + ulen] if clen == 0 else _lz4(d[pos:pos + clen])
        pos += ulen if clen == 0 else clen
        if name == b"END\0":
            break
        if name == b"INST":
            cid, sl = struct.unpack("<iI", body[:8])
            p = 9 + sl
            cnt, = struct.unpack("<I", body[p:p + 4])
            ids = _refs(body[p + 4:p + 4 + 4 * cnt], cnt)
            classes[cid] = ids
            for r in ids:
                inst[r] = {"ClassName": body[8:8 + sl].decode(), "children": []}
        elif name == b"PROP":
            cid, sl = struct.unpack("<iI", body[:8])
            prop = body[8:8 + sl].decode()
            t = body[8 + sl]
            v = body[9 + sl:]
            ids = classes[cid]
            n = len(ids)
            vals = None
            if t == 0x01:
                vals, q = [], 0
                for _ in range(n):
                    L, = struct.unpack("<I", v[q:q + 4])
                    vals.append(v[q + 4:q + 4 + L].decode("utf-8", "replace"))
                    q += 4 + L
            elif t == 0x0E:
                x, y, z = _f32(v, n), _f32(v[4 * n:], n), _f32(v[8 * n:], n)
                vals = [(x[i], y[i], z[i]) for i in range(n)]
            elif t == 0x10:
                q, rots = 0, []
                for _ in range(n):
                    rid = v[q]; q += 1
                    if rid == 0:
                        rots.append(struct.unpack("<9f", v[q:q + 36])); q += 36
                    else:
                        c0, c1 = _AX[(rid - 1) // 6], _AX[(rid - 1) % 6]
                        c2 = cross(c0, c1)
                        rots.append((c0[0], c1[0], c2[0], c0[1], c1[1], c2[1], c0[2], c1[2], c2[2]))
                x, y, z = _f32(v[q:], n), _f32(v[q + 4 * n:], n), _f32(v[q + 8 * n:], n)
                vals = [((x[i], y[i], z[i]), rots[i]) for i in range(n)]
            if vals is not None:
                for r, val in zip(ids, vals):
                    inst[r][prop] = val
        elif name == b"PRNT":
            cnt, = struct.unpack("<I", body[1:5])
            for c, par in zip(_refs(body[5:5 + 4 * cnt], cnt), _refs(body[5 + 4 * cnt:5 + 8 * cnt], cnt)):
                if par in inst:
                    inst[par]["children"].append(c)
    return inst


# ------------------------------------------------------------------ mesh (v6/v7 COREMESH, Draco)
def _draco():
    base = os.environ.get("BLENDER_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
    hits = []
    for dp, _, fs in os.walk(base):
        for f in fs:
            if f.startswith(("bf_intern_draco_bridge", "libextern_draco", "extern_draco")) and f.endswith((".dll", ".so", ".dylib")):
                hits.append(os.path.join(dp, f))
    if not hits:
        sys.exit("Blender's Draco bridge not found: run with Blender's Python or set BLENDER_DIR")
    for dp in {os.path.join(base, "blender.shared"), os.path.dirname(hits[0])}:
        if os.path.isdir(dp) and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(dp)
    dll = cdll.LoadLibrary(hits[0])
    for fn, res, args in (("decoderCreate", c_void_p, []), ("decoderRelease", None, [c_void_p]),
                          ("decoderDecode", c_bool, [c_void_p, c_void_p, c_size_t]),
                          ("decoderReadAttribute", c_bool, [c_void_p, c_uint32, c_size_t, c_char_p]),
                          ("decoderGetVertexCount", c_uint32, [c_void_p]),
                          ("decoderGetAttributeByteLength", c_size_t, [c_void_p, c_uint32]),
                          ("decoderCopyAttribute", None, [c_void_p, c_uint32, c_void_p]),
                          ("decoderReadIndices", c_bool, [c_void_p, c_size_t]),
                          ("decoderGetIndicesByteLength", c_size_t, [c_void_p]),
                          ("decoderCopyIndices", None, [c_void_p, c_void_p])):
        getattr(dll, fn).restype = res
        getattr(dll, fn).argtypes = args
    return dll


DLL = None


def read_mesh(d):
    """-> (positions [(x,y,z)], uvs [(u,v)], triangles [(a,b,c)]) of a Roblox mesh v6/v7."""
    global DLL
    head = d[:d.index(b"\n")]
    if head not in (b"version 6.00", b"version 7.00"):
        raise RuntimeError(f"mesh {head!r} not handled")
    p = len(head) + 1
    while p < len(d):
        ver, size = struct.unpack("<II", d[p + 8:p + 16])
        if d[p:p + 8] == b"COREMESH":
            body = d[p + 16:p + 16 + size]
            break
        p += 16 + size
    else:
        raise RuntimeError("no COREMESH")
    if ver == 1:   # raw: numVerts, verts (40 bytes), numFaces, faces
        nv, = struct.unpack("<I", body[:4])
        verts = [struct.unpack("<3f3f2f", body[4 + i * 40:4 + i * 40 + 32]) for i in range(nv)]
        q = 4 + nv * 40
        nf, = struct.unpack("<I", body[q:q + 4])
        tris = [struct.unpack("<3I", body[q + 4 + i * 12:q + 16 + i * 12]) for i in range(nf)]
        return [v[0:3] for v in verts], [v[6:8] for v in verts], tris
    DLL = DLL or _draco()
    n, = struct.unpack("<I", body[:4])
    blob = body[4:4 + n]
    dec = DLL.decoderCreate()
    try:
        assert DLL.decoderDecode(dec, blob, len(blob)), "draco decode failed"
        nv = DLL.decoderGetVertexCount(dec)
        assert DLL.decoderReadIndices(dec, 5125)
        ib = bytes(DLL.decoderGetIndicesByteLength(dec))
        DLL.decoderCopyIndices(dec, ib)
        idx = struct.unpack(f"<{len(ib) // 4}I", ib)

        def attr(i, typ, k):
            assert DLL.decoderReadAttribute(dec, i, 5126, typ)
            buf = bytes(DLL.decoderGetAttributeByteLength(dec, i))
            DLL.decoderCopyAttribute(dec, i, buf)
            f = struct.unpack(f"<{len(buf) // 4}f", buf)
            return [tuple(f[j * k:j * k + k]) for j in range(nv)]
        # Roblox vertex layout: 0 position, 1 normal, 2 uv, 3 tangent, 4 colour
        return attr(0, b"VEC3", 3), attr(2, b"VEC2", 2), [idx[i:i + 3] for i in range(0, len(idx), 3)]
    finally:
        DLL.decoderRelease(dec)


def asset_id(s):
    m = re.search(r"(\d{6,})", s or "")
    return m.group(1) if m else None


# ------------------------------------------------------------------ measuring
def farthest_hit(o, d, tris, max_t):
    """Distance to the farthest triangle along the ray o + t d (0 < t < max_t), 0 if none."""
    far = 0.0
    for a, b, c in tris:
        e1, e2 = sub(b, a), sub(c, a)
        h = cross(d, e2)
        det = dot(e1, h)
        if abs(det) < 1e-12:
            continue
        s = sub(o, a)
        u = dot(s, h) / det
        if u < 0 or u > 1:
            continue
        q = cross(s, e1)
        v = dot(d, q) / det
        if v < 0 or u + v > 1:
            continue
        t = dot(e2, q) / det
        if 1e-3 < t < max_t:
            far = max(far, t)
    return far


def scan(key, model_id):
    inst = read_rbxm(fetch(model_id))
    parts = []
    for o in inst.values():
        if o["ClassName"] != "MeshPart":
            continue
        tex = asset_id(o.get("TextureID"))
        for c in o["children"]:
            if inst[c]["ClassName"] == "SurfaceAppearance":
                tex = tex or asset_id(inst[c].get("ColorMap"))
        verts, uvs, tris = read_mesh(fetch(asset_id(o.get("MeshId") or o.get("MeshID"))))
        lo = [min(v[i] for v in verts) for i in range(3)]
        hi = [max(v[i] for v in verts) for i in range(3)]
        size, (P, R) = o["size"], o["CFrame"]
        sc = [size[i] / (hi[i] - lo[i]) if hi[i] - lo[i] > 1e-6 else 1 for i in range(3)]
        mid = [(lo[i] + hi[i]) / 2 for i in range(3)]

        def world(v):   # mesh vertex -> model space (the bounding box of the mesh fills the part)
            lv = [(v[i] - mid[i]) * sc[i] for i in range(3)]
            return (P[0] + R[0] * lv[0] + R[1] * lv[1] + R[2] * lv[2],
                    P[1] + R[3] * lv[0] + R[4] * lv[1] + R[5] * lv[2],
                    P[2] + R[6] * lv[0] + R[7] * lv[1] + R[8] * lv[2])
        wv = [world(v) for v in verts]
        parts.append({"name": o.get("Name"), "tex": tex, "size": size, "P": P, "R": R, "v": wv, "uv": uvs,
                      "tris": tris, "vol": size[0] * size[1] * size[2]})
    names = [p["name"] for p in parts]
    if len(set(names)) != len(names):
        raise RuntimeError(f"{key}: part names are not unique: {names}")
    ref = max(parts, key=lambda p: p["vol"])
    allv = [v for p in parts for v in p["v"]]
    y0 = min(v[1] for v in allv)
    h = max(v[1] for v in allv) - y0
    base = [v for v in allv if v[1] < y0 + 0.02 * h]
    foot = (sum(v[0] for v in base) / len(base), y0, sum(v[2] for v in base) / len(base))
    # pole width: where the mesh crosses the plane 35 % up, near the foot
    cut, band = y0 + 0.35 * h, []
    for p in parts:
        for t in p["tris"]:
            for i, j in ((0, 1), (1, 2), (2, 0)):
                a, b = p["v"][t[i]], p["v"][t[j]]
                if (a[1] - cut) * (b[1] - cut) < 0:
                    q = add(a, mul(sub(b, a), (cut - a[1]) / (b[1] - a[1])))
                    if math.hypot(q[0] - foot[0], q[2] - foot[2]) < 0.06 * h + 0.3:
                        band.append(q)
    pole = max(max(v[0] for v in band) - min(v[0] for v in band), max(v[2] for v in band) - min(v[2] for v in band)) if band else 0.05 * h
    high = [p for p in parts if p is not ref and sum(v[1] for v in p["v"]) / len(p["v"]) > y0 + 0.5 * h]
    glow = min(high, key=lambda p: p["vol"]) if high else ref
    gc = tuple(sum(v[i] for v in glow["v"]) / len(glow["v"]) for i in range(3))

    # painted lenses on the shared signal texture (faces whose way out is blocked are inside a head)
    lenses = []
    for p in parts:
        if p["tex"] != SIGNAL_ATLAS:
            continue
        tv = p["v"]
        tris = [(tv[a], tv[b], tv[c]) for a, b, c in p["tris"]]
        for a, b, c in p["tris"]:
            ua, ub, uc = p["uv"][a], p["uv"][b], p["uv"][c]
            den = (ub[0] - ua[0]) * (uc[1] - ua[1]) - (uc[0] - ua[0]) * (ub[1] - ua[1])
            if abs(den) < 1e-12:
                continue

            def bary(q):
                l1 = ((q[0] - ua[0]) * (uc[1] - ua[1]) - (uc[0] - ua[0]) * (q[1] - ua[1])) / den
                l2 = ((ub[0] - ua[0]) * (q[1] - ua[1]) - (q[0] - ua[0]) * (ub[1] - ua[1])) / den
                return 1 - l1 - l2, l1, l2
            n = unit(cross(sub(tv[b], tv[a]), sub(tv[c], tv[a])))
            for colour, (lu, lv) in LENS_UV.items():
                w = bary((lu, lv))
                if min(w) < -1e-4:
                    continue
                c3 = add(add(mul(tv[a], w[0]), mul(tv[b], w[1])), mul(tv[c], w[2]))
                e = bary((lu, lv + LENS_RADIUS_V))
                r3 = add(add(mul(tv[a], e[0]), mul(tv[b], e[1])), mul(tv[c], e[2]))
                rad = length(sub(r3, c3))
                # each lens is painted on both sides of a thin plate: drivers see the side with only the
                # shallow lens cap in front of it; the other side faces into the deep head body
                ahead = farthest_hit(c3, n, tris, 0.15 * h)
                behind = farthest_hit(c3, mul(n, -1), tris, 0.15 * h)
                if ahead >= behind:
                    continue
                lenses.append((colour, add(c3, mul(n, ahead)), n, rad))
    face = None
    if lenses:   # along the arm, away from the pole, square to the way the lenses face
        face = unit((sum(l[2][0] for l in lenses), 0, sum(l[2][2] for l in lenses)))
        arm_end = max((l[1] for l in lenses), key=lambda c: math.hypot(c[0] - foot[0], c[2] - foot[2]))
        reach = (arm_end[0] - foot[0], 0, arm_end[2] - foot[2])
        reach = sub(reach, mul(face, dot(reach, face)))
    else:        # toward the lamp head
        reach = (gc[0] - foot[0], 0, gc[2] - foot[2])
    reach = unit(reach) if math.hypot(reach[0], reach[2]) > 0.05 * h else (0.0, 0.0, -1.0)

    # everything into the reference part's frame
    P, R = ref["P"], ref["R"]
    def lp(v):
        d = sub(v, P)
        return (R[0] * d[0] + R[3] * d[1] + R[6] * d[2], R[1] * d[0] + R[4] * d[1] + R[7] * d[2], R[2] * d[0] + R[5] * d[1] + R[8] * d[2])
    def lv(v):
        return lp(add(v, P))
    return {
        "ref": ref["name"], "glow": glow["name"], "height": h, "pole": pole,
        "foot": lp(foot), "reach": lv(reach), "up": lv((0, 1, 0)), "glowAt": lp(gc),
        "face": lv(face) if face else None,
        "lenses": [(c, lp(p_), lv(n), r) for c, p_, n, r in lenses],
    }


def num(x):
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "0", "-0") else s


def vec(v):
    return "{ " + ", ".join(num(x) for x in v) + " }"


def main():
    ids = dict(re.findall(r"(\w+)\s*=\s*(\d+)", open(IDS).read()))
    keys = sys.argv[1:] or sorted(ids)
    old = {}
    if sys.argv[1:] and os.path.exists(OUT):   # keep entries not rescanned
        cur = None
        for line in open(OUT).read().splitlines():
            m = re.match(r"\t(\w+) = \{$", line)
            if m:
                cur = m.group(1); old[cur] = [line]
            elif cur:
                old[cur].append(line)
                if line == "\t},":
                    cur = None
    blocks = dict(old)
    for k in keys:
        info = scan(k, ids[k])
        b = [f"\t{k} = {{",
             f"\t\tref = {json.dumps(info['ref'])},",
             f"\t\tglow = {json.dumps(info['glow'])},",
             f"\t\theight = {num(info['height'])},",
             f"\t\tpole = {num(info['pole'])},",
             f"\t\tfoot = {vec(info['foot'])},",
             f"\t\treach = {vec(info['reach'])},",
             f"\t\tup = {vec(info['up'])},",
             f"\t\tglowAt = {vec(info['glowAt'])},"]
        if info["face"]:
            b.append(f"\t\tface = {vec(info['face'])},")
        if info["lenses"]:
            b.append("\t\tlenses = {")
            for c, p_, n, r in info["lenses"]:
                b.append(f"\t\t\t{{ {json.dumps(c)}, {', '.join(num(x) for x in p_)}, {', '.join(num(x) for x in n)}, {num(r)} }},")
            b.append("\t\t},")
        b.append("\t},")
        blocks[k] = b
        print(f"{k}: ref {info['ref']!r}, height {info['height']:.2f}, pole {info['pole']:.2f}, {len(info['lenses'])} lenses, glow {info['glow']!r}")
    lines = ["-- Generated by tools/city_prop_scan.py: where the pole, arm, lamp glass and signal lenses sit in",
             "-- each City Prop model (Shared/CityPropIds). Points are in the frame of the model's `ref` part,",
             "-- in studs at the model's own (unscaled) size. lenses: { colour, x, y, z, nx, ny, nz, radius }.",
             "return {"]
    for k in sorted(blocks):
        lines += blocks[k]
    open(OUT, "w", newline="\n").write("\n".join(lines + ["}", ""]))
    print(f"wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
