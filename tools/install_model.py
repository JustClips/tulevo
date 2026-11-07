"""Copy a Blender kit build (OUT_DIR with <Name>.glb, meta.json, textures/) into art/models/<Name>/
and write its textures.json ({part: png}, plus "<part>@<variant>" for meta["variants"]).

  python3 tools/install_model.py OUT_DIR [OUT_DIR ...]

Then: tools/upload_textures.py, tools/upload_models.py, tools/build_city_map.py.
"""
import json
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def install(out):
    meta = json.load(open(os.path.join(out, "meta.json")))
    name = meta["name"]
    dst = os.path.join(ROOT, "art", "models", name)
    tex = os.path.join(dst, "tex")
    if os.path.exists(tex):
        shutil.rmtree(tex)
    os.makedirs(tex)
    shutil.copyfile(os.path.join(out, f"{name}.glb"), os.path.join(dst, f"{name}.glb"))
    shutil.copyfile(os.path.join(out, "meta.json"), os.path.join(dst, "meta.json"))
    rel = lambda fn: f"art/models/{name}/tex/{fn}"
    tj = {}
    for part, fn in meta["textures"].items():
        shutil.copyfile(os.path.join(out, "textures", fn), os.path.join(tex, fn))
        tj[part] = rel(fn)
    for part, opts in (meta.get("variants") or {}).items():
        for v, fn in opts.items():
            shutil.copyfile(os.path.join(out, "textures", fn), os.path.join(tex, fn))
            tj[f"{part}@{v}"] = rel(fn)
    json.dump(dict(sorted(tj.items())), open(os.path.join(dst, "textures.json"), "w"), indent=1)
    print(f"installed {name}: {len(meta['parts'])} parts, {len(tj)} textures")


if __name__ == "__main__":
    for d in sys.argv[1:]:
        install(d)
