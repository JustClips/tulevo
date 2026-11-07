"""Texture sheets for Bellmont Hills, the rich suburb east of the city (art/blender/estate).

  python3 tools/estate_textures.py   ->  art/blender/estate/tex/*_Color.png

Real surfaces come from CC0 ambientCG scans (downloaded once to the git-ignored art/estate/src).
Roblox MeshParts only take a colour map, so each scan's normal + AO maps are baked into the
colour (soft light from above) and tinted. Hedges, ivy, doors, garage doors and window glass
are drawn here with PIL. Every name and sign is our own: no brands, links, credits or text
other than the district name and house numbers.
"""
import io
import math
import os
import random
import shutil
import sys
import urllib.request
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, _wrap_noise, fit_text, font, glass_pane, grime, saver, surface  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "estate", "src")
OUT = os.path.join(ROOT, "art", "blender", "estate", "tex")
HOOD = os.path.join(ROOT, "art", "blender", "hood", "tex")
save = saver(OUT)

ACG = "https://ambientcg.com/get?file={}_1K-PNG.zip"
SCANS = ("Plaster001", "PaintedPlaster017", "RoofingTiles014A", "RoofingTiles015A", "RoofingTiles007", "Concrete034",
         "PavingStones037", "PavingStones128", "Tiles098", "Grass004", "Bricks085", "Bricks076A", "Wood066",
         "WoodFloor051", "Tiles036", "Travertine009", "Gravel020", "Marble016")


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for aid in SCANS:
        if os.path.exists(os.path.join(SRC, aid, f"{aid}_1K-PNG_Color.png")):
            continue
        req = urllib.request.Request(ACG.format(aid), headers={"User-Agent": "Mozilla/5.0 tulevo-estate-textures"})
        zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req).read())).extractall(os.path.join(SRC, aid))


def scan(aid, kind, mode="RGB", size=1024):
    p = os.path.join(SRC, aid, f"{aid}_1K-PNG_{kind}.png")
    if not os.path.exists(p):
        return None
    return np.asarray(Image.open(p).convert(mode).resize((size, size), Image.LANCZOS), np.float32) / 255


def baked(aid, tint=(1, 1, 1), light=0.45, ao=0.8, gain=1.0, size=1024, sat=1.0):
    """Scan colour x tint, lit by its own normal map (light from the top-left) and AO."""
    c = scan(aid, "Color", size=size)
    g = c.mean(-1, keepdims=True)
    c = g + (c - g) * sat
    c = c * np.array(tint, np.float32)
    n = scan(aid, "NormalGL", size=size)
    if n is not None:
        n = n * 2 - 1
        L = np.array((-0.45, 0.55, 0.70), np.float32)
        L /= np.linalg.norm(L)
        lam = np.clip((n * L).sum(-1) / L[2], 0, 1.6)
        c = c * (1 - light + light * lam)[..., None]
    a = scan(aid, "AmbientOcclusion", "L", size)
    if a is not None:
        c = c * (1 - ao + ao * a)[..., None]
    return Image.fromarray(np.clip(c * gain * 255, 0, 255).astype(np.uint8), "RGB")


def recolor(img, rgb, keep=0.35):
    """Paint a light scan (plaster) a new colour, keeping its shading and texture."""
    a = np.asarray(img, np.float32) / 255
    lum = a.mean(-1, keepdims=True)
    lum = lum / max(1e-3, float(lum.mean()))
    out = np.array(rgb, np.float32)[None, None] / 255 * (1 - keep + keep * lum)
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), "RGB")


def tile_grime(img, amount, seed):
    w, h = img.size
    n = np.asarray(_wrap_noise(w, h, w // 6, seed, w / 24), np.float32) / 255
    k = 1 - amount * np.clip((n - 0.45) * 3, 0, 1)
    return Image.fromarray(np.clip(np.asarray(img, np.float32) * k[..., None], 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------- scanned surfaces
WALLS = {   # stucco paints a placed house can take (textures.json "Walls@<name>")
    "Ivory": (236, 224, 196), "Sand": (222, 200, 160), "White": (238, 236, 230), "Sage": (176, 184, 164),
    "Stone": (200, 196, 186), "Blush": (226, 196, 178), "Slate": (178, 188, 196), "Charcoal": (52, 56, 64),
}


def surfaces():
    plaster = baked("Plaster001", light=0.6, gain=1.0, sat=0.0)
    for name, rgb in WALLS.items():
        save(f"Wall{name}", tile_grime(recolor(plaster, rgb, keep=0.5 if name != "Charcoal" else 0.7), 0.06, 11), 215)
    save("Walls", Image.open(os.path.join(OUT, "WallIvory_Color.png")), 215)
    save("Render", tile_grime(recolor(baked("PaintedPlaster017", light=0.5, sat=0.0), (60, 64, 72), keep=0.6), 0.05, 12), 200)  # modern dark render
    save("RoofClay", baked("RoofingTiles014A", (1.02, 0.95, 0.9), light=0.6, gain=1.05, sat=0.85), 190)
    save("RoofBrown", baked("RoofingTiles015A", (1.10, 0.92, 0.82), light=0.6, gain=1.1, sat=0.9), 190)
    save("RoofBarrel", baked("RoofingTiles007", (1.0, 0.95, 0.92), light=0.55, gain=1.1, sat=0.75), 195)
    save("RoofFlat", baked("Concrete034", (0.78, 0.78, 0.80), light=0.3, gain=0.95), 230)
    save("Concrete", baked("Concrete034", (1.0, 1.0, 0.99), light=0.3, gain=1.05), 210)
    save("Pavers", baked("PavingStones037", (1.12, 0.98, 0.84), light=0.45, gain=1.0, sat=0.5), 200)   # warm herringbone
    save("Travert", baked("PavingStones128", (1.08, 1.02, 0.94), light=0.4, gain=1.0), 180)          # forecourt pavers
    save("Patio", baked("Tiles098", (1.0, 0.98, 0.92), light=0.4, gain=1.05, sat=0.35), 200)
    save("Lawn", baked("Grass004", (0.82, 0.92, 0.70), light=0.35, gain=1.05, sat=0.9), 245)
    save("Brick", baked("Bricks085", (0.95, 0.88, 0.84), light=0.5, gain=1.0, sat=0.8), 220)
    save("StoneWall", baked("Bricks076A", (1.05, 1.0, 0.92), light=0.5, gain=1.1, sat=0.4), 230)
    save("Cladding", baked("Wood066", (1.05, 0.95, 0.88), light=0.3, gain=1.1), 120)
    save("Deck", baked("WoodFloor051", (1.0, 0.95, 0.9), light=0.4, gain=1.0), 150)
    save("PoolTile", recolor(baked("Tiles036", light=0.5, sat=0.0), (90, 170, 200), keep=0.6), 60)
    save("Stone", baked("Travertine009", (1.0, 0.98, 0.94), light=0.3, gain=1.05), 140)              # coping, fountains, steps
    save("Gravel", baked("Gravel020", (1.0, 0.96, 0.9), light=0.5, gain=1.15, sat=0.5), 250)
    save("Marble", baked("Marble016", (1.0, 1.0, 1.0), light=0.2, gain=1.1), 60)


# ---------------------------------------------------------------- foliage
def leafy(base, seed, size=512, n=2600, alpha=False):
    """Dense clipped-hedge / ivy leaves: overlapping small leaf ellipses, light top-left."""
    r = random.Random(seed)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0) if alpha else (*[int(c * 0.35) for c in base], 255))
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x, y = r.uniform(0, size), r.uniform(0, size)
        L, W = r.uniform(8, 16), r.uniform(4, 8)
        a = r.uniform(0, math.pi)
        k = r.uniform(0.55, 1.25)
        col = tuple(max(0, min(255, int(c * k + r.uniform(-8, 8)))) for c in base)
        for ox in (-size, 0, size):          # wrap so the sheet tiles
            for oy in (-size, 0, size):
                cx, cy = x + ox, y + oy
                if -20 < cx < size + 20 and -20 < cy < size + 20:
                    pts = [(cx + math.cos(a) * L * math.cos(t) - math.sin(a) * W * math.sin(t),
                            cy + math.sin(a) * L * math.cos(t) + math.cos(a) * W * math.sin(t)) for t in np.linspace(0, math.tau, 9)]
                    d.polygon(pts, fill=(*col, 255))
                    d.line([pts[0], pts[4]], fill=(*[int(c * 0.8) for c in col], 255), width=1)
    return im if alpha else im.convert("RGB")


def foliage():
    save("HedgeBox", leafy((58, 92, 40), 1), 235)
    save("Leaf", leafy((52, 86, 34), 2, n=2200), 230)
    save("LeafB", leafy((84, 112, 44), 3, n=2200), 230)
    save("Blossom", leafy((222, 150, 196), 4, n=2400), 220)           # flowering trees (like the reference)
    ivy = leafy((50, 82, 36), 5, size=512, n=900, alpha=True)
    ivy.save(os.path.join(OUT, "Ivy_Color.png"))
    print("wrote Ivy")


# ---------------------------------------------------------------- printed sheets
def front_door():
    """Pair of tall panelled walnut doors with arched glass tops + bronze handles. 1:1 (two leaves)."""
    W, H = 512, 640
    wood = np.asarray(surface("wood", (96, 60, 36), seed=71, size=256).resize((W, H)), np.uint8)
    im = Image.fromarray(wood).convert("RGB")
    d = ImageDraw.Draw(im)
    for x0 in (0, W // 2):
        d.rectangle([x0 + 6, 6, x0 + W // 2 - 6, H - 6], outline=(52, 32, 18), width=10)
        d.pieslice([x0 + 50, 40, x0 + W // 2 - 50, 230], 180, 360, fill=(70, 86, 96))
        d.rectangle([x0 + 50, 135, x0 + W // 2 - 50, 260], fill=(70, 86, 96))
        for k in (x0 + W // 4,):
            d.line([(k, 40), (k, 260)], fill=(30, 26, 22), width=5)
        d.line([(x0 + 50, 190), (x0 + W // 2 - 50, 190)], fill=(30, 26, 22), width=5)
        for (a, b) in ((300, 440), (470, H - 40)):
            d.rectangle([x0 + 44, a, x0 + W // 2 - 44, b], outline=(60, 36, 20), width=8)
    d.rectangle([W // 2 - 40, 330, W // 2 - 26, 450], fill=(170, 130, 70))
    d.rectangle([W // 2 + 26, 330, W // 2 + 40, 450], fill=(170, 130, 70))
    save("FrontDoor", grime(im, 0.05, 72), 120)


def pivot_door():
    """Modern tall pivot door: vertical oak slats, long brushed-steel pull. 1:2.5"""
    W, H = 256, 640
    im = Image.new("RGB", (W, H), (120, 84, 54))
    d = ImageDraw.Draw(im)
    r = random.Random(5)
    for x in range(0, W, 16):
        c = tuple(int(v * r.uniform(0.85, 1.1)) for v in (126, 88, 56))
        d.rectangle([x, 0, x + 13, H], fill=c)
        d.line([(x + 14, 0), (x + 14, H)], fill=(40, 28, 20), width=2)
    d.rectangle([W - 50, 140, W - 38, 500], fill=(200, 202, 204))
    d.rectangle([0, 0, W - 1, H - 1], outline=(30, 30, 32), width=6)
    save("PivotDoor", im.filter(ImageFilter.GaussianBlur(0.6)), 140)


def garage_doors():
    """GarageWood: carriage-style wooden garage door with small windows (Spanish houses).
    GarageGlass: modern frosted glass + black aluminium sectional door. Both 2:1."""
    W, H = 768, 384
    im = Image.fromarray(np.asarray(surface("wood", (118, 76, 44), seed=81, size=256).resize((W, H)), np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(0, W, 24):
        d.line([(x, 0), (x, H)], fill=(70, 44, 26), width=3)
    d.line([(W // 2, 0), (W // 2, H)], fill=(40, 26, 16), width=8)
    for x0 in (0, W // 2):
        for k in range(4):
            wx = x0 + 30 + k * ((W // 2 - 60) // 4)
            d.rectangle([wx + 6, 34, wx + (W // 2 - 60) // 4 - 6, 96], fill=(56, 66, 74), outline=(40, 26, 16), width=6)
        d.line([(x0 + 20, 130), (x0 + W // 2 - 20, H - 20)], fill=(70, 44, 26), width=10)
    for x in (W // 2 - 60, W // 2 + 40):
        d.rectangle([x, 200, x + 20, 214], fill=(30, 30, 30))
        for hy in (130, 300):
            d.rectangle([x - 200 if x < W // 2 else x + 40, hy, x + 20 if x < W // 2 else x + 220, hy + 10], fill=(28, 28, 28))
    save("GarageWood", grime(im, 0.06, 82), 130)
    im = Image.new("RGB", (W, H), (24, 25, 27))
    d = ImageDraw.Draw(im)
    for row in range(4):
        y0 = 12 + row * 92
        for col in range(5):
            x0 = 12 + col * 149
            pane = glass_pane(140, 80, 300 + row * 5 + col, "bath")
            im.paste(pane, (x0, y0))
    save("GarageGlass", im, 70)


def glass():
    """House windows (home interiors) + big living-room panes for the modern glass walls."""
    for i in range(6):
        save(f"Glass{chr(65 + i)}", glass_pane(256, 256, 1200 + i, "home"), 25)
    save("GlassFrost", glass_pane(256, 256, 1299, "bath"), 80)
    for i in range(3):
        save(f"GlassBig{chr(65 + i)}", glass_pane(512, 512, 1300 + i, "home", lit=(i == 1)), 20)


def sign():
    """District monument plaque: BELLMONT HILLS carved into travertine. 4:1."""
    W, H = 1024, 256
    st = baked("Travertine009", (1.0, 0.97, 0.92), light=0.3, gain=1.05, size=1024).crop((0, 0, W, H))
    d = ImageDraw.Draw(st)
    for off, col in (((3, 3), (120, 104, 84)), ((0, 0), (64, 56, 46))):
        fit_text(d, (W // 2 + off[0], 108 + off[1]), "BELLMONT HILLS", FONT_B, W - 120, 110, col)
    d.line([(260, 190), (W - 260, 190)], fill=(150, 126, 80), width=4)
    d.ellipse([W // 2 - 10, 180, W // 2 + 10, 200], fill=(150, 126, 80))
    save("EstateSign", st, 160)


def numbers():
    """Brass house-number plates 1..12 on dark stone (a 4 x 3 atlas, one plate each)."""
    W, H = 1024, 768
    im = Image.new("RGB", (W, H), (40, 40, 42))
    d = ImageDraw.Draw(im)
    for i in range(12):
        cx, cy = (i % 4) * 256 + 128, (i // 4) * 256 + 128
        d.rectangle([cx - 120, cy - 120, cx + 120, cy + 120], outline=(150, 120, 70), width=6)
        fit_text(d, (cx, cy), str(100 + (i + 1) * 4), FONT_B, 200, 110, (196, 160, 90))
    save("HouseNumbers", im, 120)


def water():
    """Fountain / pool water flipbooks are the hood's (same images, same uploaded ids)."""
    for fn in os.listdir(HOOD):
        if fn.startswith(("FxPool", "FxFall", "FxRipple", "Water_")):
            shutil.copyfile(os.path.join(HOOD, fn), os.path.join(OUT, fn))


def mats():
    """Small realistic sheets for trims and fittings."""
    for name, (k, c) in {"Trim": ("paint", (238, 234, 224)), "Iron": ("paint", (22, 22, 24)), "Bronze": ("metal", (120, 92, 58)),
                         "Steel": ("metal", (176, 178, 180)), "Alu": ("paint", (34, 35, 38)), "Teak": ("wood", (128, 84, 52)),
                         "Cushion": ("plastic", (228, 222, 210)), "Soil": ("gravel", (58, 42, 30)), "Bark": ("wood", (72, 56, 42)),
                         "Pot": ("paint", (184, 108, 72)), "Rubber": ("rubber", (28, 28, 30))}.items():
        save(name, surface(k, c, seed=500 + len(name)), 200)


def main():
    fetch()
    os.makedirs(OUT, exist_ok=True)
    surfaces()
    foliage()
    front_door()
    pivot_door()
    garage_doors()
    glass()
    sign()
    numbers()
    water()
    mats()


if __name__ == "__main__":
    main()
