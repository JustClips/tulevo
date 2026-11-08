"""Pack each city model's small part textures into a few shared 1024 px sheets (texture atlases).

  python3 tools/atlas_city.py [Model ...]     # default: every model in City/Buildings
  then: python3 tools/upload_models.py && python3 tools/upload_textures.py
        && python3 tools/grant_all.py && python3 tools/build_city_map.py

Why: the city used ~600 separate images (30-40 per building). Studio and the game ask Roblox for
all of them at once and Roblox turns many away ("Asset content representation is being
generated"), so buildings stayed white. Big games use a few sheets per building instead.

What it does per model (art/models/<M>/<M>.glb + textures.json):
- parts whose UVs stay inside 0..1 (labels, signs, props, flat colour swatches) get packed into
  Atlas<n>.png sheets (max 1024 x 1024, Roblox's image limit) and their UVs are remapped in the
  GLB. Each image sits in its own cell with a 4 px edge-colour border so mipmaps don't bleed.
- parts with tiling UVs (walls, floors, roads: the texture repeats), parts with "Part@Variant"
  paint, and images with see-through pixels keep their own image.
- textures.json then points the packed parts at the sheet files.
Re-running is safe: parts already on an Atlas sheet are left alone. A fresh Blender export of a
model overwrites both files, so run this again after it.
"""
import json
import os
import struct
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHEET = 1024
PAD = 4
MIN_CELL = 32  # tiny colour swatches (8 x 8) get a cell this big so the border fits
UV_TOL = 0.01


def read_glb(path):
    data = open(path, "rb").read()
    jlen = struct.unpack("<I", data[12:16])[0]
    j = json.loads(data[20:20 + jlen])
    off = 20 + jlen
    blen = struct.unpack("<I", data[off:off + 4])[0]
    return j, bytearray(data[off + 8:off + 8 + blen])


def write_glb(path, j, binary):
    while len(binary) % 4:
        binary.append(0)
    j["buffers"][0]["byteLength"] = len(binary)
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    out = struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(binary), 0x004E4942) + bytes(binary)
    open(path, "wb").write(out)


def accessor(j, binary, i):
    a = j["accessors"][i]
    v = j["bufferViews"][a["bufferView"]]
    assert a["componentType"] == 5126 and a["type"] == "VEC2", "TEXCOORD must be float VEC2"
    stride = v.get("byteStride", 8)
    assert stride == 8, "interleaved UVs not supported"
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    return np.frombuffer(bytes(binary[off:off + a["count"] * 8]), dtype=np.float32).reshape(-1, 2).copy()


def add_accessor(j, binary, uv):
    while len(binary) % 4:
        binary.append(0)
    off = len(binary)
    binary += uv.astype(np.float32).tobytes()
    j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": uv.size * 4, "target": 34962})
    j["accessors"].append({"bufferView": len(j["bufferViews"]) - 1, "componentType": 5126, "count": len(uv),
                           "type": "VEC2", "min": uv.min(0).tolist(), "max": uv.max(0).tolist()})
    return len(j["accessors"]) - 1


def has_alpha(img):
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        a = np.asarray(img.convert("RGBA"))[..., 3]
        return a.min() < 250
    return False


def cell_image(img, cw, ch):
    """img fitted to (cw-2P, ch-2P), then edge pixels repeated PAD px out to (cw, ch)."""
    iw, ih = cw - 2 * PAD, ch - 2 * PAD
    small = img.width <= 16 and img.height <= 16
    inner = img.convert("RGB").resize((iw, ih), Image.NEAREST if small else Image.LANCZOS)
    arr = np.pad(np.asarray(inner), ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
    return Image.fromarray(arr)


def _skyline_fit(sky, w, h):
    """Best (lowest, then leftmost) spot for a w x h cell on a skyline [(x, y, width)]."""
    best = None
    for i, (x, _, _) in enumerate(sky):
        if x + w > SHEET:
            break
        y, left, j = 0, w, i
        while left > 0:
            y = max(y, sky[j][1])
            left -= sky[j][2]
            j += 1
        if y + h <= SHEET and (best is None or y < best[1]):
            best = (x, y)
    return best


def _skyline_add(sky, x, y, w, h):
    new = [(x, y + h, w)]
    for sx, sy, sw in sky:
        if sx + sw <= x or sx >= x + w:
            new.append((sx, sy, sw))
        else:
            if sx < x:
                new.append((sx, sy, x - sx))
            if sx + sw > x + w:
                new.append((x + w, sy, sx + sw - x - w))
    new.sort()
    merged = [new[0]]
    for seg in new[1:]:
        if seg[1] == merged[-1][1]:
            merged[-1] = (merged[-1][0], merged[-1][1], merged[-1][2] + seg[2])
        else:
            merged.append(seg)
    return merged


def pack(cells):
    """Skyline-pack (key, w, h) cells into SHEET-square sheets. Returns ({key: (sheet, x, y)}, count)."""
    order = sorted(cells, key=lambda c: (-c[2], -c[1]))
    sheets = []
    out = {}
    for key, w, h in order:
        for si, sky in enumerate(sheets):
            spot = _skyline_fit(sky, w, h)
            if spot:
                sheets[si] = _skyline_add(sky, spot[0], spot[1], w, h)
                out[key] = (si, *spot)
                break
        else:
            sheets.append(_skyline_add([(0, 0, SHEET)], 0, 0, w, h))
            out[key] = (len(sheets) - 1, 0, 0)
    return out, len(sheets)


def atlas_model(model):
    mdir = os.path.join(ROOT, "art", "models", model)
    gpath, tpath = os.path.join(mdir, f"{model}.glb"), os.path.join(mdir, "textures.json")
    if not (os.path.exists(gpath) and os.path.exists(tpath)):
        return None
    tex = json.load(open(tpath))
    j, binary = read_glb(gpath)

    # parts that can go on a sheet: flat UVs, no paint variants, opaque image, not already packed
    cand = {}  # part -> (node, image file)
    for n in j["nodes"]:
        name = n.get("name")
        if "mesh" not in n or name not in tex or "/Atlas" in tex[name]:
            continue
        if any(k.startswith(name + "@") for k in tex):
            continue
        ok = True
        for pr in j["meshes"][n["mesh"]]["primitives"]:
            if "TEXCOORD_0" not in pr["attributes"]:
                ok = False
                break
            uv = accessor(j, binary, pr["attributes"]["TEXCOORD_0"])
            if uv.min() < -UV_TOL or uv.max() > 1 + UV_TOL:
                ok = False
                break
        if ok:
            cand[name] = n
    # parts sharing a mesh with a part that stays separate can't be remapped
    keep_meshes = {n["mesh"] for n in j["nodes"] if "mesh" in n and n.get("name") not in cand}
    cand = {k: n for k, n in cand.items() if n["mesh"] not in keep_meshes}

    images = {}  # file -> PIL image
    for part in list(cand):
        f = tex[part]
        if f not in images:
            img = Image.open(os.path.join(ROOT, f))
            img.load()
            if has_alpha(img):
                images[f] = None
            else:
                images[f] = img
        if images[f] is None:
            del cand[part]
    files = sorted({tex[p] for p in cand})
    if len(files) < 2:
        return f"{model}: nothing to pack"

    cells = []
    for f in files:
        img = images[f]
        w, h = min(img.width, SHEET), min(img.height, SHEET)
        cells.append((f, max(w, MIN_CELL), max(h, MIN_CELL)))
    where, count = pack(cells)
    if count >= len(files) - 1:
        return f"{model}: {len(files)} images would need {count} sheets, left as is"

    sheets = [Image.new("RGB", (SHEET, SHEET), (128, 128, 128)) for _ in range(count)]
    rects = {}
    used_h = [0] * count
    for f, cw, ch in cells:
        si, x, y = where[f]
        sheets[si].paste(cell_image(images[f], cw, ch), (x, y))
        rects[f] = (si, (x + PAD) / SHEET, (y + PAD) / SHEET, (cw - 2 * PAD) / SHEET, (ch - 2 * PAD) / SHEET)
        used_h[si] = max(used_h[si], y + ch)

    # crop each sheet to the next 64 px that holds what was placed (less memory for small sets)
    sheet_h = []
    for si in range(count):
        sheet_h.append(min(-(-used_h[si] // 64) * 64, SHEET))

    names = []
    for si, img in enumerate(sheets):
        rel = f"art/models/{model}/tex/Atlas{si + 1}.png"
        os.makedirs(os.path.dirname(os.path.join(ROOT, rel)), exist_ok=True)
        img.crop((0, 0, SHEET, sheet_h[si])).save(os.path.join(ROOT, rel), optimize=True)
        names.append(rel)

    # remap UVs (v runs down the image, so the same transform works for u and v)
    done_meshes = set()
    for part, n in cand.items():
        si, x, y, w, h = rects[tex[part]]
        hscale = SHEET / sheet_h[si]
        if n["mesh"] not in done_meshes:
            done_meshes.add(n["mesh"])
            for pr in j["meshes"][n["mesh"]]["primitives"]:
                uv = np.clip(accessor(j, binary, pr["attributes"]["TEXCOORD_0"]), 0, 1)
                uv[:, 0] = x + uv[:, 0] * w
                uv[:, 1] = (y + uv[:, 1] * h) * hscale
                pr["attributes"]["TEXCOORD_0"] = add_accessor(j, binary, uv)
        tex[part] = names[si]

    write_glb(gpath, j, binary)
    json.dump(tex, open(tpath, "w"), indent=1, sort_keys=True)
    return f"{model}: {len(cand)} parts, {len(files)} images -> {count} sheet(s) {sheet_h}"


def city_models():
    d = json.load(open(os.path.join(ROOT, "src", "workspace", "City.model.json")))
    b = next(c for c in d["children"] if c["name"] == "Buildings")
    return sorted({m["attributes"]["CityModel"] for m in b["children"] if "CityModel" in m.get("attributes", {})})


if __name__ == "__main__":
    for m in sys.argv[1:] or city_models():
        r = atlas_model(m)
        if r:
            print(r)
