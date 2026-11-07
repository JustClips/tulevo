"""Textures for the city fill (thread "Fill city with buildings and street props", 2026-11-07).

  python3 tools/cityfill_textures.py         -> art/blender/cityfill/tex/<Name>_Color.png (+ _Roughness)

Real surfaces come from CC0 ambientCG scans (downloaded once to the git-ignored art/cityfill/src;
ambientCG answers 403 without a User-Agent). Painted metal = the grain of a real scan (luminance
detail) laid over a paint colour, so poles, bins and hydrants show real wear without any text.
Printed parts (street name blades, news boxes, stop sign, ads, labels) are drawn here with PIL
into one atlas, DecoPrint, mapped with explicit UVs in art/blender/cityfill/build_street.py
(ATLAS below gives each region in pixels).

Content rules: no alcohol, no gambling, no real brands, no URLs, no credit text, no watermarks.
"""
import io
import json
import os
import random
import sys
import urllib.request
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, font, fit_text  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "cityfill", "src")
OUT = os.path.join(ROOT, "art", "blender", "cityfill", "tex")
UA = {"User-Agent": "Mozilla/5.0 (tulevo-build)"}

SCANS = ["Bricks085", "Bricks094", "Bricks101", "Bricks097", "Concrete034", "Concrete031", "Concrete044D",
         "Metal029", "PaintedMetal004", "PaintedMetal012", "Planks023A", "CorrugatedSteel005", "Plaster001",
         "PaintedPlaster017", "Tiles107", "Facade006", "WoodSiding008"]


def fetch():
    os.makedirs(SRC, exist_ok=True)
    for a in SCANS:
        if os.path.exists(os.path.join(SRC, f"{a}_Color.png")):
            continue
        url = f"https://ambientcg.com/get?file={a}_1K-PNG.zip"
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                for kind in ("Color", "Roughness"):
                    if n.endswith(f"_{kind}.png"):
                        open(os.path.join(SRC, f"{a}_{kind}.png"), "wb").write(z.read(n))
        print("fetched", a)


def scan(a, kind="Color", size=None):
    im = Image.open(os.path.join(SRC, f"{a}_{kind}.png")).convert("RGB")
    return im.resize((size, size), Image.LANCZOS) if size else im


def save(name, color, rough=None):
    os.makedirs(OUT, exist_ok=True)
    color.convert("RGB").save(os.path.join(OUT, f"{name}_Color.png"), optimize=True)
    if rough is not None:
        if isinstance(rough, (int, float)):
            rough = Image.new("L", color.size, int(rough))
        rough.convert("L").convert("RGB").save(os.path.join(OUT, f"{name}_Roughness.png"), optimize=True)
    print("wrote", name)


def real(name, a, size=512, tint=None, gain=1.0):
    """A scan as is (optionally colour-shifted toward tint, keeping its detail)."""
    c = scan(a, size=size)
    if tint:
        arr = np.asarray(c, np.float32) / 255
        lum = arr.mean(axis=2, keepdims=True)
        arr = arr * (1 - 0.5) + lum / max(lum.mean(), 1e-3) * np.array(tint, np.float32) / 255 * 0.5
        c = Image.fromarray(np.clip(arr * 255 * gain, 0, 255).astype(np.uint8))
    save(name, c, scan(a, "Roughness", size))


def paint(name, rgb, grain="PaintedMetal012", size=256, strength=0.35, rough=None):
    """Paint colour carrying the wear and grain of a real scan."""
    g = np.asarray(scan(grain, size=size).convert("L"), np.float32) / 255
    g = g / g.mean()
    arr = np.array(rgb, np.float32)[None, None, :] * (1 + (g[..., None] - 1) * strength)
    col = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    r = scan(grain, "Roughness", size) if rough is None else rough
    save(name, col, r)


# ---------------------------------------------------------------- printed atlas (DecoPrint)
A = 1024
ATLAS = {}       # name -> (x0, y0, x1, y1) in pixels
STREETS = ["VAULT AVE", "BACK ST", "WEST ST", "EAST ST", "NORTH ST", "SOUTH ST"]


def region(name, box):
    ATLAS[name] = box
    return box


def blade(d, box, text):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=10, fill=(16, 92, 52))
    d.rounded_rectangle((x0 + 5, y0 + 5, x1 - 5, y1 - 5), radius=7, outline=(235, 240, 235), width=3)
    fit_text(d, ((x0 + x1) / 2, (y0 + y1) / 2 + 2), text, FONT_B, x1 - x0 - 40, 44, (245, 247, 245))


def news_face(img, box, title, sub, col, seed):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    d.rectangle(box, fill=col)
    d.rectangle((x0 + 8, y0 + 8, x1 - 8, y0 + 46), fill=(250, 250, 246))
    fit_text(d, ((x0 + x1) / 2, y0 + 28), title, FONT_B, w - 26, 26, col)
    # window onto today's paper
    wx0, wy0, wx1, wy1 = x0 + 12, y0 + 58, x1 - 12, y0 + int(h * 0.62)
    d.rectangle((wx0, wy0, wx1, wy1), fill=(214, 216, 210))
    r = random.Random(seed)
    d.rectangle((wx0 + 6, wy0 + 6, wx1 - 6, wy0 + 20), fill=(40, 40, 40))
    d.rectangle((wx0 + 6, wy0 + 26, wx0 + (wx1 - wx0) // 2, wy0 + 70), fill=(110, 120, 130))
    for k in range(9):
        y = wy0 + 28 + k * 7
        d.line((wx0 + (wx1 - wx0) // 2 + 6, y, wx1 - 6 - r.randint(0, 20), y), fill=(90, 90, 90), width=2)
    for k in range(4):
        y = wy0 + 78 + k * 7
        if y < wy1 - 4:
            d.line((wx0 + 6, y, wx1 - 6 - r.randint(0, 30), y), fill=(90, 90, 90), width=2)
    d.rectangle((wx0, wy0, wx1, wy1), outline=(30, 30, 30), width=3)
    fit_text(d, ((x0 + x1) / 2, y0 + int(h * 0.72)), sub, FONT_B, w - 30, 18, (250, 250, 246))
    # coin slot + price plate
    d.rectangle((x0 + w * 0.3, y0 + h * 0.8, x0 + w * 0.7, y0 + h * 0.92), fill=(170, 172, 175), outline=(60, 60, 60), width=2)
    d.rectangle((x0 + w * 0.47, y0 + h * 0.83, x0 + w * 0.53, y0 + h * 0.89), fill=(25, 25, 25))


def atlas():
    img = Image.new("RGB", (A, A), (120, 120, 120))
    d = ImageDraw.Draw(img)
    # street name blades: 6 x (440 x 72), left column
    for i, s in enumerate(STREETS):
        blade(d, region(f"Blade_{s}", (8, 8 + i * 80, 448, 8 + i * 80 + 72)), s)
    # stop sign (octagon) 256 x 256 at (456, 8)
    x0, y0, s = 456, 8, 256
    region("Stop", (x0, y0, x0 + s, y0 + s))
    d.rectangle((x0, y0, x0 + s, y0 + s), fill=(200, 200, 200))
    import math
    oct_ = [(x0 + s / 2 + s / 2 * math.cos(math.radians(22.5 + 45 * k)), y0 + s / 2 + s / 2 * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(oct_, fill=(245, 245, 245))
    oct2 = [(x0 + s / 2 + (s / 2 - 9) * math.cos(math.radians(22.5 + 45 * k)), y0 + s / 2 + (s / 2 - 9) * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(oct2, fill=(196, 22, 30))
    fit_text(d, (x0 + s / 2, y0 + s / 2 + 4), "STOP", FONT_B, s - 50, 84, (250, 250, 250))
    # news box fronts: 3 x (176 x 300)
    for i, (t, sub, col) in enumerate((("TULEVO LEDGER", "DAILY  50c", (24, 70, 140)),
                                      ("CITY WEEKLY", "FREE  TAKE ONE", (170, 30, 30)),
                                      ("APARTMENT GUIDE", "FREE", (225, 160, 20)))):
        news_face(img, region(f"News{i}", (8 + i * 184, 496, 8 + i * 184 + 176, 796)), t, sub, col, i)
    d = ImageDraw.Draw(img)
    # bus shelter ad 256 x 384 at (720, 8): an ad for the in-game hypercar (original model name)
    x0, y0 = 720, 8
    region("BusAd", (x0, y0, x0 + 296, y0 + 440))
    for yy in range(440):
        t = yy / 440
        d.line((x0, y0 + yy, x0 + 296, y0 + yy), fill=(int(20 + 30 * t), int(24 + 20 * t), int(60 + 80 * t)))
    d.polygon([(x0 + 30, y0 + 300), (x0 + 90, y0 + 255), (x0 + 210, y0 + 248), (x0 + 270, y0 + 290), (x0 + 270, y0 + 318), (x0 + 30, y0 + 318)], fill=(200, 30, 36))
    d.polygon([(x0 + 100, y0 + 262), (x0 + 200, y0 + 256), (x0 + 236, y0 + 284), (x0 + 96, y0 + 286)], fill=(30, 36, 50))
    for wx in (x0 + 80, x0 + 222):
        d.ellipse((wx - 26, y0 + 296, wx + 26, y0 + 348), fill=(20, 20, 22)); d.ellipse((wx - 12, y0 + 310, wx + 12, y0 + 334), fill=(170, 170, 175))
    fit_text(d, (x0 + 148, y0 + 70), "VELOCE H9", FONT_B, 260, 54, (245, 245, 250))
    fit_text(d, (x0 + 148, y0 + 120), "BUILT FOR THE NIGHT", FONT_R, 250, 24, (230, 200, 120))
    fit_text(d, (x0 + 148, y0 + 395), "NOW AT DEALERS", FONT_B, 240, 26, (245, 245, 250))
    # bin label 256 x 64, meter face 96 x 144, mail label 200 x 80, bus stop flag 140 x 200, utility sticker
    x0, y0 = 568, 496
    region("BinLabel", (x0, y0, x0 + 256, y0 + 64))
    d.rectangle(ATLAS["BinLabel"], fill=(18, 64, 40))
    fit_text(d, (x0 + 128, y0 + 33), "KEEP TULEVO CLEAN", FONT_B, 236, 26, (240, 240, 230))
    x0, y0 = 568, 570
    region("MeterFace", (x0, y0, x0 + 96, y0 + 144))
    d.rectangle(ATLAS["MeterFace"], fill=(40, 42, 44))
    d.rectangle((x0 + 10, y0 + 12, x0 + 86, y0 + 52), fill=(140, 170, 120), outline=(20, 20, 20), width=3)
    fit_text(d, (x0 + 48, y0 + 32), "1:25", FONT_B, 70, 26, (30, 40, 30))
    d.rectangle((x0 + 20, y0 + 66, x0 + 76, y0 + 82), fill=(150, 150, 150))
    fit_text(d, (x0 + 48, y0 + 108), "PAY HERE", FONT_B, 80, 16, (230, 230, 230))
    d.ellipse((x0 + 36, y0 + 118, x0 + 60, y0 + 140), fill=(20, 110, 190))
    x0, y0 = 672, 570
    region("MailLabel", (x0, y0, x0 + 200, y0 + 80))
    d.rectangle(ATLAS["MailLabel"], fill=(20, 52, 120))
    fit_text(d, (x0 + 100, y0 + 30), "CITY MAIL", FONT_B, 180, 30, (245, 245, 245))
    fit_text(d, (x0 + 100, y0 + 62), "PICKUP 5 PM", FONT_R, 170, 16, (230, 230, 230))
    x0, y0 = 880, 496
    region("BusFlag", (x0, y0, x0 + 136, y0 + 200))
    d.rectangle(ATLAS["BusFlag"], fill=(245, 245, 245))
    d.rectangle((x0 + 6, y0 + 6, x0 + 130, y0 + 70), fill=(20, 80, 170))
    fit_text(d, (x0 + 68, y0 + 38), "BUS", FONT_B, 110, 46, (250, 250, 250))
    fit_text(d, (x0 + 68, y0 + 100), "STOP", FONT_B, 110, 34, (20, 80, 170))
    fit_text(d, (x0 + 68, y0 + 150), "LINES 3  7  12", FONT_B, 120, 16, (30, 30, 30))
    fit_text(d, (x0 + 68, y0 + 178), "NO PARKING", FONT_B, 120, 16, (190, 20, 20))
    x0, y0 = 672, 660
    region("CabLabel", (x0, y0, x0 + 200, y0 + 120))
    d.rectangle(ATLAS["CabLabel"], fill=(196, 200, 188))
    d.rectangle((x0 + 20, y0 + 20, x0 + 180, y0 + 70), fill=(245, 200, 30), outline=(20, 20, 20), width=3)
    fit_text(d, (x0 + 100, y0 + 45), "HIGH VOLTAGE", FONT_B, 150, 22, (20, 20, 20))
    fit_text(d, (x0 + 100, y0 + 95), "SIGNAL CONTROL  14", FONT_R, 170, 16, (40, 40, 40))
    # one-way arrow sign 256 x 80, speed limit 120 x 160
    x0, y0 = 8, 820
    region("OneWay", (x0, y0, x0 + 256, y0 + 80))
    d.rectangle(ATLAS["OneWay"], fill=(15, 15, 15))
    d.rectangle((x0 + 8, y0 + 8, x0 + 248, y0 + 72), fill=(250, 250, 250))
    d.polygon([(x0 + 20, y0 + 30), (x0 + 180, y0 + 30), (x0 + 180, y0 + 18), (x0 + 236, y0 + 40), (x0 + 180, y0 + 62), (x0 + 180, y0 + 50), (x0 + 20, y0 + 50)], fill=(15, 15, 15))
    fit_text(d, (x0 + 100, y0 + 40), "ONE WAY", FONT_B, 130, 18, (250, 250, 250))
    x0, y0 = 280, 820
    region("Speed", (x0, y0, x0 + 120, y0 + 160))
    d.rectangle(ATLAS["Speed"], fill=(250, 250, 250), outline=(15, 15, 15), width=6)
    fit_text(d, (x0 + 60, y0 + 34), "SPEED", FONT_B, 100, 22, (15, 15, 15))
    fit_text(d, (x0 + 60, y0 + 60), "LIMIT", FONT_B, 100, 22, (15, 15, 15))
    fit_text(d, (x0 + 60, y0 + 115), "35", FONT_B, 100, 64, (15, 15, 15))
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    save("DecoPrint", img, 120)
    json.dump({k: [v / A for v in box] for k, box in ATLAS.items()}, open(os.path.join(OUT, "atlas.json"), "w"), indent=1)


def grate():
    """Cast-iron tree grate: concentric slots round the trunk hole."""
    s = 256
    img = Image.new("RGB", (s, s), (38, 36, 34))
    d = ImageDraw.Draw(img)
    import math
    for r in range(36, 124, 12):
        for k in range(int(r * 0.6)):
            a0 = k / int(r * 0.6) * 360
            d.arc((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), a0 + 2, a0 + 360 / int(r * 0.6) - 3, fill=(8, 6, 5), width=5)
    d.ellipse((s / 2 - 28, s / 2 - 28, s / 2 + 28, s / 2 + 28), fill=(52, 38, 26))
    g = np.asarray(scan("Metal029", size=s).convert("L"), np.float32) / 255
    arr = np.asarray(img, np.float32) * (0.75 + 0.5 * g[..., None])
    save("Grate", Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), 150)


def glass():
    """Bus shelter glass: faint frosted band with dots."""
    s = 256
    img = Image.new("RGB", (s, s), (170, 196, 205))
    d = ImageDraw.Draw(img)
    for x in range(6, s, 14):
        d.ellipse((x - 3, s * 0.45 - 3, x + 3, s * 0.45 + 3), fill=(235, 240, 242))
    save("ShelterGlass", img, 20)


def leaves():
    """Canopy colour: dense leaf clusters in a few greens (tileable noise, no photo)."""
    s = 256
    r = random.Random(5)
    img = Image.new("RGB", (s, s), (44, 74, 30))
    d = ImageDraw.Draw(img)
    for _ in range(2200):
        x, y = r.randint(-8, s + 8), r.randint(-8, s + 8)
        c = r.choice([(36, 66, 24), (58, 92, 34), (72, 108, 40), (30, 54, 22), (88, 120, 46)])
        a = r.uniform(0, 6.28)
        L = r.randint(5, 10)
        import math
        pts = [(x + math.cos(a) * L, y + math.sin(a) * L), (x + math.cos(a + 1.9) * L * 0.45, y + math.sin(a + 1.9) * L * 0.45),
               (x - math.cos(a) * L * 0.6, y - math.sin(a) * L * 0.6), (x + math.cos(a - 1.9) * L * 0.45, y + math.sin(a - 1.9) * L * 0.45)]
        for ox in (-s, 0, s):
            for oy in (-s, 0, s):
                d.polygon([(px + ox, py + oy) for px, py in pts], fill=c)
    save("Leaves", img.filter(ImageFilter.GaussianBlur(0.5)), 210)


def leaf_card():
    """Leafy branch tip with see-through gaps (RGBA): shade tree canopy cards."""
    import math
    s = 512
    r = random.Random(21)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # twigs from the bottom centre outwards
    tips = []
    for k in range(9):
        a = math.radians(-90 + r.uniform(-75, 75))
        L = r.uniform(0.3, 0.44) * s
        x1, y1 = s / 2 + math.cos(a) * L, s * 0.92 + math.sin(a) * L
        d.line((s / 2, s * 0.95, x1, y1), fill=(70, 52, 36, 255), width=3)
        tips.append((x1, y1, a))
    greens = [(52, 86, 30), (64, 102, 36), (78, 118, 42), (44, 74, 26), (90, 128, 50), (58, 96, 40)]
    for _ in range(900):
        rr = s * 0.44 * math.sqrt(r.random()) ** 0.8
        th = r.uniform(0, math.tau)
        cx, cy = s / 2 + math.cos(th) * rr, s * 0.5 + math.sin(th) * rr * 0.9
        ang = r.uniform(0, math.tau)
        L, W = r.uniform(18, 34), r.uniform(8, 14)
        pts = []
        for k in range(10):
            u = k / 9
            pts.append((u * L, math.sin(u * math.pi) * W / 2))
        pts += [(u, -v) for u, v in pts[::-1]]
        c = r.choice(greens)
        shade = r.uniform(0.75, 1.15)
        col = tuple(min(255, int(v * shade)) for v in c) + (255,)
        d.polygon([(cx + math.cos(ang) * u - math.sin(ang) * v, cy + math.sin(ang) * u + math.cos(ang) * v) for u, v in pts], fill=col)
        d.line((cx, cy, cx + math.cos(ang) * L * 0.9, cy + math.sin(ang) * L * 0.9), fill=tuple(int(v * 0.8) for v in c) + (255,), width=1)
    # keep alpha hard (Roblox cut-out) and bleed colour into the clear pixels so edges do not halo
    a_ = img.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    rgb = Image.new("RGB", (s, s), (56, 90, 32))
    rgb.paste(img.convert("RGB"), mask=a_)
    out = rgb.convert("RGBA"); out.putalpha(a_)
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, "LeafCard_Color.png"), optimize=True)
    Image.new("RGB", (s, s), (200, 200, 200)).save(os.path.join(OUT, "LeafCard_Roughness.png"))
    print("wrote LeafCard")


def street():
    paint("PoleSteel", (54, 58, 60), grain="Metal029", strength=0.5)          # dark grey painted steel
    paint("PoleGalv", (150, 154, 156), grain="CorrugatedSteel005", strength=0.45)
    paint("BinGreen", (26, 62, 42), grain="PaintedMetal012", strength=0.3)
    paint("IronBlack", (26, 27, 28), grain="Metal029", strength=0.6)
    paint("HydrantRed", (176, 30, 26), grain="PaintedMetal004", strength=0.25)
    paint("SafetyYellow", (226, 176, 24), grain="PaintedMetal012", strength=0.3)
    paint("MailBlue", (24, 56, 128), grain="PaintedMetal012", strength=0.3)
    paint("CabGrey", (150, 156, 146), grain="PaintedMetal012", strength=0.35)
    paint("NewsBlue", (24, 70, 140), grain="PaintedMetal012", strength=0.3)
    paint("NewsRed", (170, 30, 30), grain="PaintedMetal012", strength=0.3)
    paint("NewsAmber", (225, 160, 20), grain="PaintedMetal012", strength=0.3)
    paint("SignalBody", (40, 42, 38), grain="Metal029", strength=0.5)
    real("BenchWood", "Planks023A", 512, tint=(150, 104, 66), gain=1.15)
    real("Plinth", "Concrete034", 512)
    real("Bark", "WoodSiding008", 256, tint=(90, 72, 56))
    grate(); glass(); leaves(); leaf_card(); atlas()


if __name__ == "__main__":
    fetch()
    street()
