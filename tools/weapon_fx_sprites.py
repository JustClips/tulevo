"""Prepare the Blender gun VFX renders (art/blender/weapons/render_muzzle_fx.py) for Roblox.

  python3 tools/weapon_fx_sprites.py RENDER_OUT_DIR [--preview OUT.png] && python3 tools/upload_textures.py

Flash and tracer renders are on black: they get a soft bloom and alpha = brightness (they read
as light over anything). Smoke renders already have alpha and are copied as they are.
Everything lands in art/weapons/fx/ and is listed in art/weapons/fx/textures.json, which
upload_textures.py uploads into TextureIds.WeaponFx.
"""
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from weather_sprites import glow_to_alpha  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST = os.path.join(ROOT, "art", "weapons", "fx")

GLOW = ["MuzzleSide1", "MuzzleSide2", "MuzzleSide3", "MuzzleSide4", "MuzzleFront1", "MuzzleFront2", "Tracer"]
PLAIN = ["MuzzleSmoke1", "MuzzleSmoke2"]


def preview(out):
    """Every sprite composited over a dark street grey and a bright sky, to judge both."""
    names = GLOW + PLAIN
    cell = 260
    sheet = Image.new("RGB", (cell * len(names), cell * 2), (0, 0, 0))
    for row, bg in enumerate(((52, 56, 62), (170, 196, 222))):
        for i, n in enumerate(names):
            im = Image.open(os.path.join(DST, f"{n}.png")).convert("RGBA")
            im.thumbnail((cell - 10, cell - 10))
            base = Image.new("RGBA", (cell, cell), (*bg, 255))
            # additive for the glow sprites, alpha blend for smoke (like Roblox LightEmission 1 / 0)
            if n in GLOW:
                import numpy as np
                b = np.asarray(base).astype(np.float32)
                s = np.asarray(im).astype(np.float32)
                ox, oy = (cell - im.width) // 2, (cell - im.height) // 2
                a = s[..., 3:4] / 255
                b[oy:oy + im.height, ox:ox + im.width, :3] = np.clip(
                    b[oy:oy + im.height, ox:ox + im.width, :3] + s[..., :3] * a, 0, 255)
                base = Image.fromarray(b.astype(np.uint8), "RGBA")
            else:
                base.alpha_composite(im, ((cell - im.width) // 2, (cell - im.height) // 2))
            sheet.paste(base.convert("RGB"), (i * cell, row * cell))
    sheet.save(out)
    print("preview ->", out)


def main():
    src = sys.argv[1]
    os.makedirs(DST, exist_ok=True)
    listing = {}
    for n in GLOW:
        glow_to_alpha(os.path.join(src, f"{n}.png"), os.path.join(DST, f"{n}.png"))
        listing[n] = f"art/weapons/fx/{n}.png"
    for n in PLAIN:
        Image.open(os.path.join(src, f"{n}.png")).convert("RGBA").save(os.path.join(DST, f"{n}.png"))
        listing[n] = f"art/weapons/fx/{n}.png"
    json.dump(listing, open(os.path.join(DST, "textures.json"), "w"), indent=1)
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1])


if __name__ == "__main__":
    main()
