"""Texture sheets for the army base (Fort Halden), west of the city.

  python3 tools/army_textures.py   ->  art/blender/army/tex/*_Color.png

Real surfaces come from CC0 ambientCG scans (downloaded once to the git-ignored art/army/src).
Roblox MeshParts only take a colour map, so each scan's normal + AO maps are baked into the
colour (soft light from above) and tinted; corrugated siding keeps its ribs that way.
Printed sheets (signs, doors, windows, chain-link, razor wire) are drawn with PIL.
Every name, sign and emblem here is our own: no real units, insignia, brands, links or credits.
"""
import io
import math
import os
import random
import sys
import urllib.request
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, glass_set, grime, saver, scratches, text_c  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "army", "src")
OUT = os.path.join(ROOT, "art", "blender", "army", "tex")
save = saver(OUT)
rr = random.Random(41)

ACG = "https://ambientcg.com/get?file={}_1K-PNG.zip"
SCANS = ("CorrugatedSteel005", "Concrete034", "Concrete031", "Concrete042A", "Ground054", "Grass004",
         "Asphalt025C", "Bark007", "Planks023A", "Fabric066", "Metal032", "DiamondPlate008A", "Gravel023")


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for aid in SCANS:
        if os.path.exists(os.path.join(SRC, aid)):
            continue
        req = urllib.request.Request(ACG.format(aid), headers={"User-Agent": "Mozilla/5.0 tulevo-army-textures"})
        zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(req).read())).extractall(os.path.join(SRC, aid))


def scan(aid, kind, mode="RGB", size=1024):
    p = os.path.join(SRC, aid, f"{aid}_1K-PNG_{kind}.png")
    if not os.path.exists(p):
        return None
    return np.asarray(Image.open(p).convert(mode).resize((size, size), Image.LANCZOS), np.float32) / 255


def baked(aid, tint=(1, 1, 1), light=0.45, ao=0.8, gain=1.0, size=1024, sat=1.0):
    """Scan colour x tint, lit by its own normal map (light from the top-left) and AO."""
    c = scan(aid, "Color", size=size)
    if sat != 1.0:
        g = c.mean(-1, keepdims=True)
        c = g + (c - g) * sat
    c = c * np.array(tint, np.float32)
    n = scan(aid, "NormalGL", size=size)
    if n is not None:
        n = n * 2 - 1
        L = np.array((-0.45, 0.55, 0.70), np.float32)
        L /= np.linalg.norm(L)
        lam = np.clip((n * L).sum(-1) / L[2], 0, 1.6)   # flat = 1
        shade = 1 - light + light * lam
        c = c * shade[..., None]
    a = scan(aid, "AmbientOcclusion", "L", size)
    if a is not None:
        c = c * (1 - ao + ao * a)[..., None]
    return Image.fromarray(np.clip(c * gain * 255, 0, 255).astype(np.uint8), "RGB")


def tileable_grime(img, amount, seed):
    """Soft tileable dirt blotches (no streaks, so the sheet still tiles)."""
    from tex_kit import _wrap_noise
    w, h = img.size
    n = np.asarray(_wrap_noise(w, h, w // 6, seed, w / 24), np.float32) / 255
    k = 1 - amount * np.clip((n - 0.45) * 3, 0, 1)
    return Image.fromarray(np.clip(np.asarray(img, np.float32) * k[..., None], 0, 255).astype(np.uint8), "RGB")


# ---------------------------------------------------------------- scanned surfaces
def surfaces():
    # barracks siding: off-white ribbed steel (ribs run vertically in the scan)
    save("Siding", tileable_grime(baked("CorrugatedSteel005", (1.05, 1.05, 1.06), light=0.55, gain=1.12, sat=0.3), 0.10, 3), 120)
    # olive drab siding for the motor pool shed and the training hut
    save("SidingOlive", tileable_grime(baked("CorrugatedSteel005", (0.55, 0.60, 0.42), light=0.55, gain=1.0, sat=0.2), 0.15, 4), 130)
    save("Concrete", baked("Concrete034", (0.92, 0.92, 0.90), light=0.3, gain=1.0), 200)          # tower, canopy, booth
    save("ConcreteDark", baked("Concrete031", (1.0, 1.0, 0.98), light=0.3, gain=1.05), 210)        # kerbs, footings, jersey barriers
    save("Roof", baked("Concrete042A", (0.62, 0.63, 0.66), light=0.25, gain=0.9, sat=0.4), 220)     # flat roof membrane
    save("Dirt", tileable_grime(baked("Ground054", (0.92, 0.84, 0.72), light=0.5, gain=0.95), 0.12, 5), 240)   # training yard
    save("Grass", baked("Grass004", (0.80, 0.88, 0.70), light=0.35, gain=1.0, sat=0.85), 245)
    save("Asphalt", baked("Asphalt025C", (1.18, 1.18, 1.2), light=0.3, gain=1.25), 230)
    save("Bark", baked("Bark007", (0.62, 0.48, 0.38), light=0.5, gain=0.9, sat=0.25), 250)
    save("Planks", baked("Planks023A", (1.15, 1.05, 0.95), light=0.4, gain=1.05), 200)              # bleachers, pallets
    save("Canvas", baked("Fabric066", (0.62, 0.64, 0.44), light=0.4, gain=1.0, sat=0.5), 250)       # truck covers, tents
    save("Sandbag", baked("Fabric066", (0.98, 0.88, 0.68), light=0.4, gain=1.05, sat=0.4), 250)
    save("Steel", baked("Metal032", (0.95, 0.96, 0.98), light=0.3, gain=1.1, sat=0.3), 90)           # galvanised posts, rails
    save("Tread", baked("DiamondPlate008A", (1, 1, 1), light=0.5, gain=1.1), 100)                    # steps, landings
    save("Gravel", baked("Gravel023", (0.62, 0.60, 0.56), light=0.5, gain=0.95), 250)


# ---------------------------------------------------------------- painted / printed sheets
def emblem(d, cx, cy, s, fill=(214, 186, 92), dark=(36, 52, 34)):
    """Fort Halden emblem (our own): a shield with a pine and two crossed bars."""
    pts = [(-0.5, -0.55), (0.5, -0.55), (0.5, 0.05), (0, 0.6), (-0.5, 0.05)]
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=fill)
    pts2 = [(-0.42, -0.47), (0.42, -0.47), (0.42, 0.02), (0, 0.5), (-0.42, 0.02)]
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts2], fill=dark)
    for k in range(3):                               # pine
        w, y0 = 0.16 + k * 0.08, -0.36 + k * 0.16
        d.polygon([(cx, cy + y0 * s), (cx + w * s, cy + (y0 + 0.2) * s), (cx - w * s, cy + (y0 + 0.2) * s)], fill=fill)
    d.rectangle([cx - 0.03 * s, cy + 0.12 * s, cx + 0.03 * s, cy + 0.24 * s], fill=fill)


def gate_sign():
    """Big sign on the gate canopy: FORT HALDEN + emblem. 4:1."""
    W, H = 1024, 256
    im = Image.new("RGB", (W, H), (38, 56, 38))
    d = ImageDraw.Draw(im)
    d.rectangle([6, 6, W - 7, H - 7], outline=(214, 186, 92), width=6)
    emblem(d, 128, 128, 190)
    emblem(d, W - 128, 128, 190)
    fit_text(d, (W // 2, 104), "FORT HALDEN", FONT_B, 520, 110, (238, 232, 214))
    fit_text(d, (W // 2, 190), "MILITARY RESERVATION", FONT_B, 500, 44, (214, 186, 92))
    save("GateSign", grime(scratches(im, 60, 11), 0.06, 12), 160)


def warn_sign(name, lines, head="WARNING", head_col=(190, 30, 30), size=(512, 384)):
    W, H = size
    im = Image.new("RGB", (W, H), (240, 238, 230))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, int(H * 0.3)], fill=head_col)
    fit_text(d, (W // 2, int(H * 0.15)), head, FONT_B, W - 60, int(H * 0.2), (255, 255, 255))
    y = H * 0.3 + (H * 0.7) / (len(lines) + 1)
    for ln in lines:
        fit_text(d, (W // 2, int(y)), ln, FONT_B, W - 50, int(H * 0.12), (24, 24, 24))
        y += (H * 0.7) / (len(lines) + 1)
    d.rectangle([3, 3, W - 4, H - 4], outline=(24, 24, 24), width=6)
    save(name, grime(scratches(im, 40, rr.randint(0, 99)), 0.08, rr.randint(0, 99)), 150)


def signs():
    warn_sign("SignRestricted", ["RESTRICTED AREA", "AUTHORIZED", "PERSONNEL ONLY"])
    warn_sign("SignStop", ["ALL VEHICLES", "STOP FOR", "ID CHECK"], head="STOP", head_col=(200, 24, 24))
    warn_sign("SignSpeed", ["SPEED LIMIT", "15", "ON POST"], head="CAUTION", head_col=(226, 170, 20))
    warn_sign("SignNoPhoto", ["NO PHOTOGRAPHY", "BEYOND", "THIS POINT"], head="NOTICE", head_col=(30, 70, 150))
    # building number plates (dark green, stencil-white text)
    for n in ("101", "102", "103", "104", "HQ", "MOTOR POOL", "RANGE TOWER"):
        W, H = 512, 160
        im = Image.new("RGB", (W, H), (40, 58, 40))
        d = ImageDraw.Draw(im)
        d.rectangle([4, 4, W - 5, H - 5], outline=(230, 228, 214), width=4)
        fit_text(d, (W // 2, H // 2), n if not n.isdigit() else f"BLDG {n}", FONT_B, W - 50, 84, (236, 234, 222))
        save("Plate" + n.replace(" ", "").title().replace("Hq", "HQ"), im, 160)


def flag():
    """Original flag: forest green, gold band, the emblem."""
    W, H = 512, 320
    im = Image.new("RGB", (W, H), (44, 76, 46))
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(H * 0.40), W, int(H * 0.60)], fill=(214, 186, 92))
    d.rectangle([0, int(H * 0.44), W, int(H * 0.56)], fill=(44, 76, 46))
    emblem(d, W * 0.27, H * 0.5, H * 0.62)
    save("Flag", im, 240)


def doors():
    """Steel barracks door: painted panel, push bar, small wired-glass window, kick plate. 1:2."""
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (70, 84, 68))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, H - 1], outline=(40, 48, 40), width=10)
    d.rectangle([60, 70, 196, 210], fill=(60, 68, 74))                    # wired glass
    for k in range(70, 210, 14):
        d.line([(60, k), (196, k)], fill=(150, 156, 160), width=1)
    for k in range(60, 196, 14):
        d.line([(k, 70), (k, 210)], fill=(150, 156, 160), width=1)
    d.rectangle([56, 66, 200, 214], outline=(30, 30, 30), width=4)
    d.rectangle([20, 270, 236, 286], fill=(150, 150, 146))                 # push bar
    d.rectangle([14, H - 70, W - 14, H - 14], fill=(130, 132, 128))        # kick plate
    d.ellipse([200, 290, 220, 310], fill=(160, 160, 156))
    save("Door", grime(scratches(im, 70, 21), 0.12, 22), 120)
    # roll-up garage door for the motor pool
    W, H = 512, 512
    im = Image.new("RGB", (W, H), (150, 152, 146))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 16):
        d.rectangle([0, y, W, y + 3], fill=(108, 110, 106))
        d.line([(0, y + 13), (W, y + 13)], fill=(176, 178, 172), width=1)
    save("RollDoor", grime(im, 0.18, 23), 110)


def chain_link():
    """Galvanised chain-link mesh with alpha (holes see-through). One tile = 2 x 2 diamonds."""
    W = 128
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(-W, W * 2, 32):
        d.line([(k, 0), (k + W, W)], fill=(176, 180, 184, 255), width=3)
        d.line([(k, W), (k + W, 0)], fill=(150, 154, 158, 255), width=3)
    im.save(os.path.join(OUT, "ChainLink_Color.png"))
    print("wrote ChainLink")


def razor_wire():
    """Concertina razor wire seen on a tube: overlapping loops with small blades, alpha.
    u runs along the coil, v around it."""
    W, H = 512, 128
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (196, 200, 206, 255)
    loops = 8
    for k in range(loops * 2):
        x0 = k * W / (loops * 2)
        pts = [(x0 + 0.5 * W / loops * math.sin(t / 40 * math.pi) * 0.9 + t / 40 * W / loops * 0.6, t / 40 * H) for t in range(41)]
        for dx in (-W, 0, W):
            q = [(x + dx, y) for x, y in pts]
            d.line(q, fill=col, width=3)
            for j in range(2, 40, 4):                       # blades
                x, y = q[j]
                d.polygon([(x - 5, y - 2), (x + 5, y), (x - 5, y + 2)], fill=col)
    im.save(os.path.join(OUT, "RazorWire_Color.png"))
    print("wrote RazorWire")


def camo_net():
    """Woodland camouflage netting with leaf cut-outs (alpha)."""
    from tex_kit import _wrap_noise
    W = 512
    a = np.asarray(_wrap_noise(W, W, 48, 61, 8), np.float32) / 255
    b = np.asarray(_wrap_noise(W, W, 24, 62, 3), np.float32) / 255
    cols = np.array([(58, 70, 42), (86, 92, 58), (44, 48, 34), (110, 100, 70)], np.float32)
    idx = np.clip((a * 3.2 - 0.6).astype(int), 0, 3)
    rgb = cols[idx] * (0.9 + 0.2 * b[..., None])
    alpha = ((b > 0.36) | (a > 0.62)).astype(np.float32) * 255
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA")
    im.save(os.path.join(OUT, "CamoNet_Color.png"))
    print("wrote CamoNet")


def pine_needles():
    """Dark pine foliage: needle strokes over deep green, lighter tips. Tileable."""
    from tex_kit import _wrap_noise
    W = 512
    big = np.asarray(_wrap_noise(W, W, 64, 71, 14), np.float32) / 255 - 0.5
    base = np.array((34, 54, 32), np.float32) + big[..., None] * np.array((18, 22, 12))
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    r = random.Random(72)
    for _ in range(16000):
        x, y = r.uniform(0, W), r.uniform(0, W)
        ln, ang = r.uniform(5, 12), r.uniform(-0.5, 0.5) + math.pi / 2
        g = r.random()
        col = (22, 36, 22, 170) if g < 0.4 else (58, 84, 46, 150) if g < 0.85 else (92, 116, 64, 140)
        for ox in (-W, 0, W):
            for oy in (-W, 0, W):
                if -14 < x + ox < W + 14 and -14 < y + oy < W + 14:
                    d.line([(x + ox, y + oy), (x + ox + math.cos(ang) * ln, y + oy + math.sin(ang) * ln)], fill=col, width=1)
    save("Needles", im, 250)


def paint():
    """Road paint, booth stripes, HVAC grilles, solid colours."""
    flat = {"PaintYellow": (222, 176, 40), "PaintWhite": (232, 232, 226), "BoomRed": (196, 32, 30),
            "BoomWhite": (236, 236, 232), "Olive": (78, 86, 58), "DarkSteel": (52, 54, 56), "Rubber": (26, 26, 28),
            "Tire": (30, 30, 32), "Glass": (60, 70, 80), "Hesco": (150, 140, 112), "Water": (90, 110, 120)}
    for n, c in flat.items():
        save(n, Image.new("RGB", (16, 16), c), 150)
    # HVAC unit side: louvres + fan grille top
    W = 256
    im = Image.new("RGB", (W, W), (176, 178, 172))
    d = ImageDraw.Draw(im)
    for y in range(20, W - 20, 10):
        d.rectangle([16, y, W - 16, y + 5], fill=(120, 122, 118))
    d.rectangle([2, 2, W - 3, W - 3], outline=(140, 142, 138), width=4)
    save("Hvac", grime(im, 0.12, 31), 120)
    im = Image.new("RGB", (W, W), (170, 172, 166))
    d = ImageDraw.Draw(im)
    for rad in range(110, 10, -12):
        d.ellipse([W / 2 - rad, W / 2 - rad, W / 2 + rad, W / 2 + rad], outline=(40, 40, 40), width=3)
    for a in range(0, 360, 30):
        d.line([(W / 2, W / 2), (W / 2 + 110 * math.cos(math.radians(a)), W / 2 + 110 * math.sin(math.radians(a)))], fill=(60, 60, 60), width=3)
    save("HvacTop", grime(im, 0.12, 32), 120)
    # helipad: a big H in a circle on concrete-grey
    W = 512
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([20, 20, W - 20, W - 20], outline=(236, 236, 230, 255), width=22)
    d.rectangle([150, 130, 196, 382], fill=(236, 236, 230, 255))
    d.rectangle([316, 130, 362, 382], fill=(236, 236, 230, 255))
    d.rectangle([196, 234, 316, 278], fill=(236, 236, 230, 255))
    im.save(os.path.join(OUT, "Helipad_Color.png"))
    print("wrote Helipad")


def main():
    fetch()
    os.makedirs(OUT, exist_ok=True)
    surfaces()
    gate_sign()
    signs()
    flag()
    doors()
    chain_link()
    razor_wire()
    camo_net()
    pine_needles()
    paint()
    glass_set(save, prefix="Glass", n=4, seed=1300, kinds=("office",), size=(256, 256))
    glass_set(save, prefix="TowerGlass", n=1, seed=1400, kinds=("office",), size=(256, 256))


if __name__ == "__main__":
    main()
