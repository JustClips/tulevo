"""Strip embedded images/textures from GLB files (keeps meshes, part names, plain materials).

  python3 tools/strip_glb_textures.py art/models/Motel/Motel.glb [...]

City buildings get their colour maps from separately uploaded Images (LiveSyncTextures ->
MeshPart.TextureID). If the GLB also embeds images, Roblox turns them into SurfaceAppearances
and Studio retries uploading them as TexturePacks every play test ("Referenced Asset N is NOT
found", 429 rate limits). Without embedded images there is nothing to upload.
"""
import json
import struct
import sys


def strip(path):
    data = open(path, "rb").read()
    magic, ver, _ = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", path
    off, gltf, binc = 12, None, b""
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            gltf = json.loads(chunk)
        elif typ == 0x004E4942:
            binc = chunk
        off += 8 + ln
    if not gltf.get("images"):
        return False
    for m in gltf.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        for k in ("baseColorTexture", "metallicRoughnessTexture"):
            pbr.pop(k, None)
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            m.pop(k, None)
        m.pop("extensions", None)
    for k in ("images", "textures", "samplers"):
        gltf.pop(k, None)
    # keep only bufferViews used by accessors, repack the binary buffer
    used = sorted({a["bufferView"] for a in gltf.get("accessors", []) if "bufferView" in a})
    remap, out = {}, bytearray()
    views = gltf["bufferViews"]
    new_views = []
    for i in used:
        v = dict(views[i])
        while len(out) % 4:
            out.append(0)
        start = v.get("byteOffset", 0)
        out += binc[start: start + v["byteLength"]]
        v["byteOffset"] = len(out) - v["byteLength"]
        remap[i] = len(new_views)
        new_views.append(v)
    for a in gltf.get("accessors", []):
        if "bufferView" in a:
            a["bufferView"] = remap[a["bufferView"]]
    gltf["bufferViews"] = new_views
    while len(out) % 4:
        out.append(0)
    gltf["buffers"] = [{"byteLength": len(out)}]
    gltf.get("extensionsUsed", []) and gltf.update(extensionsUsed=[e for e in gltf["extensionsUsed"] if "texture" not in e.lower()])
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(out), 0x004E4942) + bytes(out)
    open(path, "wb").write(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
    return True


if __name__ == "__main__":
    for p in sys.argv[1:]:
        before = len(open(p, "rb").read())
        if strip(p):
            print(f"{p}: {before // 1024} KB -> {len(open(p, 'rb').read()) // 1024} KB")
