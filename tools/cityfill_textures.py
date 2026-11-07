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
import math
import os
import random
import sys
import urllib.request
import shutil
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
         "PaintedPlaster017", "Tiles107", "Facade006", "WoodSiding008",
         # Lindell Park v2 (paths, plaza, fountain, wall, lawn, playground mulch, skate concrete)
         "PavingStones081", "PavingStones128", "Travertine009", "Concrete025", "Concrete016", "Grass004",
         "WoodChips001", "Concrete042A"]


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
    paint("SignalBody", (58, 60, 58), grain="Metal029", strength=0.5)
    paint("SignalYellow", (214, 168, 34), grain="PaintedMetal012", strength=0.35)
    real("BenchWood", "Planks023A", 512, tint=(150, 104, 66), gain=1.15)
    real("Plinth", "Concrete034", 512)
    real("Bark", "WoodSiding008", 256, tint=(90, 72, 56))
    grate(); glass(); leaves(); leaf_card(); atlas()




# ================================================================= buildings
def glass_over(im, seed, amount=0.38):
    """Sky reflection, a glint and edge grime over a drawn interior (shop windows)."""
    r = random.Random(seed)
    w, h = im.size
    base = np.asarray(im.convert("RGB"), np.float32)
    ys = np.linspace(0, 1, h)[:, None]
    sky = np.stack([190 - 70 * ys, 214 - 70 * ys, 232 - 60 * ys], -1) * np.ones((1, w, 1))
    a = np.ones((h, w, 1)) * (amount * (1 - 0.5 * ys))[..., None]
    out = base * (1 - a) + sky * a
    gl = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(gl)
    for _ in range(2):
        g = r.uniform(0.1, 0.9)
        gd.polygon([(w * g, 0), (w * (g + 0.08), 0), (w * (g - 0.12), h), (w * (g - 0.2), h)], fill=34)
    gl = np.asarray(gl.filter(ImageFilter.GaussianBlur(3)), np.float32)[..., None] / 255
    out = out * (1 - gl) + 255 * gl
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def shop_interior(kind, seed, w=1024, h=480):
    """What you see through a shop window: back wall, floor, fittings, people-free, door at the right."""
    r = random.Random(seed)
    wall = {"barber": (214, 206, 190), "donut": (246, 222, 196), "pharmacy": (232, 236, 236), "noodle": (176, 48, 40),
            "cafe": (120, 88, 64), "phone": (228, 230, 234), "tailor": (200, 186, 160), "books": (90, 70, 52),
            "pizza": (200, 150, 100), "pets": (210, 230, 220), "games": (34, 30, 52), "nails": (244, 214, 222),
            "dental": (226, 238, 242), "tax": (214, 214, 206), "shoes": (180, 150, 120), "florist": (232, 240, 226),
            "mart": (236, 234, 228)}[kind]
    im = Image.new("RGB", (w, h), wall)
    d = ImageDraw.Draw(im)
    d.rectangle((0, int(h * 0.78), w, h), fill=(150, 140, 128) if kind != "noodle" else (90, 70, 60))      # floor
    for x in range(0, w, 64):
        d.line((x, int(h * 0.78), x - 40, h), fill=(130, 120, 110), width=2)
    # ceiling lights
    for x in range(80, w, 220):
        d.rectangle((x, 6, x + 120, 16), fill=(255, 250, 230))
    if kind == "mart":
        for k in range(4):                                                                   # soda coolers on the back wall
            x = 40 + k * 120
            d.rectangle((x, 60, x + 110, 360), fill=(40, 44, 50))
            d.rectangle((x + 8, 68, x + 102, 352), fill=(150, 190, 210))
            for row in range(5):
                y = 90 + row * 52
                d.rectangle((x + 10, y + 34, x + 100, y + 38), fill=(200, 200, 205))
                for j in range(6):
                    c = r.choice([(200, 30, 30), (30, 90, 200), (40, 160, 70), (240, 180, 40), (240, 240, 240)])
                    d.rectangle((x + 14 + j * 14, y + 6, x + 24 + j * 14, y + 34), fill=c)
        for row in range(3):                                                                 # snack aisle
            y = 220 + row * 50
            d.rectangle((540, y + 40, 960, y + 46), fill=(170, 170, 176))
            xx = 546
            while xx < 950:
                bw = r.randint(16, 30)
                d.rectangle((xx, y + 40 - r.randint(18, 36), xx + bw, y + 40),
                            fill=r.choice([(230, 120, 30), (220, 40, 40), (250, 210, 60), (60, 120, 200), (120, 60, 160)]))
                xx += bw + 3
        d.rectangle((540, 80, 820, 170), fill=(232, 120, 30))                                # back-wall banner
        fit_text(d, (680, 125), "COFFEE · SNACKS", FONT_B, 250, 40, (255, 255, 255))
    elif kind == "barber":
        for i in range(3):
            x = 90 + i * 260
            d.rectangle((x, 110, x + 150, 250), fill=(190, 210, 220), outline=(80, 70, 60), width=6)       # mirror
            d.rectangle((x + 30, 270, x + 120, 330), fill=(30, 30, 34))                                       # chair back
            d.rectangle((x + 20, 330, x + 130, 370), fill=(150, 30, 30))
            d.rectangle((x + 65, 370, x + 85, 400), fill=(160, 160, 165))
        for y in range(40, 420, 28):                                                                         # pole stripes
            d.polygon([(w - 70, y), (w - 40, y + 14), (w - 40, y + 28), (w - 70, y + 14)], fill=(200, 30, 30))
        d.rectangle((w - 70, 40, w - 40, 420), outline=(240, 240, 240), width=4)
    elif kind == "donut":
        d.rectangle((60, 260, 760, 380), fill=(220, 220, 214))                                               # display case
        d.rectangle((70, 270, 750, 330), fill=(200, 226, 236))
        for i in range(16):
            x = 90 + i * 40
            c = r.choice([(214, 160, 90), (240, 150, 190), (120, 70, 40), (250, 240, 220)])
            d.ellipse((x, 290, x + 30, 318), fill=c); d.ellipse((x + 11, 300, x + 19, 308), fill=(200, 226, 236))
        d.rectangle((120, 60, 700, 180), fill=(60, 40, 30))                                                  # menu board
        for k in range(5):
            d.line((150, 85 + k * 20, 400 + r.randint(0, 200), 85 + k * 20), fill=(240, 220, 180), width=4)
    elif kind == "pharmacy":
        for row in range(4):                                                                                 # shelves
            y = 120 + row * 70
            d.rectangle((40, y + 50, 780, y + 56), fill=(170, 170, 176))
            x = 46
            while x < 770:
                bw = r.randint(14, 30)
                d.rectangle((x, y + 50 - r.randint(20, 46), x + bw, y + 50), fill=r.choice([(40, 120, 200), (230, 230, 236), (220, 80, 60), (90, 170, 90), (240, 190, 60)]))
                x += bw + 3
        d.rectangle((830, 60, 930, 160), fill=(30, 150, 80))                                                 # green cross sign
        d.rectangle((865, 75, 895, 145), fill=(240, 255, 240)); d.rectangle((845, 95, 915, 125), fill=(240, 255, 240))
    elif kind == "noodle":
        for i in range(4):                                                                                   # tables + stools
            x = 70 + i * 190
            d.rectangle((x, 300, x + 120, 312), fill=(60, 36, 24)); d.rectangle((x + 54, 312, x + 66, 372), fill=(40, 30, 24))
            for sx in (x - 10, x + 110):
                d.ellipse((sx, 330, sx + 30, 342), fill=(200, 40, 30)); d.rectangle((sx + 12, 342, sx + 18, 374), fill=(40, 40, 40))
        for i in range(5):                                                                                   # paper lanterns
            x = 90 + i * 170
            d.line((x + 25, 0, x + 25, 50), fill=(30, 30, 30), width=2)
            d.ellipse((x, 50, x + 50, 110), fill=(250, 200, 80)); d.ellipse((x + 6, 56, x + 44, 104), fill=(255, 226, 120))
    elif kind == "cafe":
        d.rectangle((60, 250, 700, 380), fill=(70, 50, 38))                                                  # counter
        d.rectangle((120, 190, 220, 250), fill=(180, 180, 186))                                              # espresso machine
        for i in range(6):
            d.rectangle((300 + i * 60, 220, 330 + i * 60, 250), fill=(240, 240, 236))                         # cups
        for k in range(4):
            d.rectangle((60 + k * 160, 70, 180 + k * 160, 150), fill=(50, 40, 34))                           # menu
            for j in range(3):
                d.line((70 + k * 160, 90 + j * 18, 160 + k * 160, 90 + j * 18), fill=(230, 220, 200), width=3)
    elif kind == "phone":
        for i in range(3):
            x = 60 + i * 260
            d.rectangle((x, 280, x + 200, 380), fill=(240, 240, 244))                                         # display tables
            for k in range(5):
                d.rounded_rectangle((x + 10 + k * 38, 250, x + 36 + k * 38, 300), 4, fill=(20, 20, 24))
        d.rectangle((60, 60, 760, 200), fill=(40, 120, 220))
    elif kind == "tailor":
        for i in range(4):
            x = 80 + i * 180
            d.ellipse((x + 40, 110, x + 80, 150), fill=(60, 50, 40))
            d.polygon([(x + 20, 160), (x + 100, 160), (x + 90, 330), (x + 30, 330)], fill=r.choice([(40, 50, 80), (90, 30, 30), (60, 60, 60), (120, 100, 70)]))
            d.rectangle((x + 56, 330, x + 64, 390), fill=(40, 40, 40))
    elif kind == "books":
        for row in range(5):
            y = 70 + row * 62
            d.rectangle((40, y + 52, 800, y + 58), fill=(60, 40, 28))
            x = 44
            while x < 790:
                bw = r.randint(8, 18)
                d.rectangle((x, y + 52 - r.randint(30, 50), x + bw, y + 52), fill=r.choice([(140, 40, 30), (40, 70, 120), (200, 180, 120), (60, 100, 60), (220, 220, 210)]))
                x += bw + 1
    elif kind == "pizza":
        d.rectangle((60, 260, 720, 380), fill=(60, 40, 30))                                                   # counter
        d.rounded_rectangle((420, 90, 700, 250), 60, fill=(150, 70, 40))                                     # brick oven
        d.ellipse((500, 160, 620, 250), fill=(40, 20, 10)); d.ellipse((520, 190, 600, 240), fill=(250, 150, 40))
        for i in range(3):
            x = 90 + i * 100
            d.ellipse((x, 210, x + 80, 250), fill=(230, 180, 90)); d.ellipse((x + 8, 214, x + 72, 246), fill=(200, 60, 40))
        d.rectangle((60, 60, 380, 170), fill=(30, 60, 30))
        for k in range(4):
            d.line((80, 80 + k * 22, 300 + r.randint(0, 60), 80 + k * 22), fill=(240, 230, 200), width=4)
    elif kind == "pets":
        for row in range(3):
            y = 100 + row * 90
            d.rectangle((40, y + 70, 560, y + 76), fill=(150, 150, 150))
            x = 50
            while x < 550:
                bw = r.randint(26, 50)
                d.rectangle((x, y + 70 - r.randint(30, 60), x + bw, y + 70), fill=r.choice([(220, 120, 40), (60, 140, 200), (240, 220, 80), (120, 180, 90)]))
                x += bw + 6
        d.rectangle((600, 150, 780, 300), fill=(120, 190, 230), outline=(80, 80, 80), width=6)            # fish tank
        for i in range(6):
            fx_, fy_ = r.randint(620, 750), r.randint(170, 280)
            d.ellipse((fx_, fy_, fx_ + 18, fy_ + 9), fill=r.choice([(250, 140, 30), (250, 220, 60), (230, 60, 60)]))
    elif kind == "games":
        for i in range(4):
            x = 60 + i * 180
            d.rectangle((x, 100, x + 140, 380), fill=(20, 20, 30), outline=(120, 60, 220), width=6)        # cabinets
            d.rectangle((x + 20, 130, x + 120, 220), fill=r.choice([(60, 200, 240), (240, 80, 160), (120, 240, 120), (250, 200, 60)]))
            d.rectangle((x + 30, 250, x + 110, 270), fill=(60, 60, 70))
            d.ellipse((x + 40, 252, x + 56, 268), fill=(230, 40, 40)); d.ellipse((x + 80, 252, x + 96, 268), fill=(40, 120, 230))
        d.rectangle((0, 20, w, 30), fill=(120, 60, 220))
    elif kind == "nails":
        for i in range(3):
            x = 80 + i * 240
            d.rectangle((x, 260, x + 180, 290), fill=(250, 250, 250)); d.rectangle((x + 80, 290, x + 100, 370), fill=(200, 200, 200))
            d.rounded_rectangle((x + 40, 180, x + 140, 260), 20, fill=(150, 110, 170))
        for k in range(30):                                                                                  # polish wall
            x, y = 60 + (k % 15) * 46, 70 + (k // 15) * 40
            d.rectangle((x, y, x + 14, y + 26), fill=r.choice([(220, 40, 80), (240, 120, 160), (180, 40, 140), (250, 200, 210), (200, 30, 30)]))
    elif kind == "dental":
        d.rectangle((60, 260, 420, 380), fill=(240, 244, 246))                                               # reception desk
        d.rectangle((60, 250, 420, 262), fill=(90, 170, 200))
        for i in range(4):
            x = 470 + i * 80
            d.rectangle((x, 300, x + 60, 340), fill=(90, 170, 200)); d.rectangle((x, 260, x + 60, 300), fill=(110, 190, 220))
        d.ellipse((120, 70, 220, 170), fill=(250, 250, 250), outline=(90, 170, 200), width=6)                # tooth-free logo disc
        d.rectangle((300, 80, 760, 180), fill=(240, 246, 248), outline=(180, 200, 210), width=4)
    elif kind == "tax":
        for i in range(3):
            x = 60 + i * 260
            d.rectangle((x, 260, x + 200, 300), fill=(110, 80, 60)); d.rectangle((x + 10, 300, x + 30, 380), fill=(90, 66, 50))
            d.rectangle((x + 60, 210, x + 140, 260), fill=(30, 30, 34)); d.rectangle((x + 66, 216, x + 134, 254), fill=(120, 170, 220))
        for i in range(5):
            d.rectangle((60 + i * 150, 60, 170 + i * 150, 150), fill=(190, 190, 184), outline=(150, 150, 146), width=3)
    elif kind == "shoes":
        for row in range(4):
            y = 90 + row * 70
            d.rectangle((40, y + 50, 780, y + 56), fill=(90, 60, 40))
            for i in range(10):
                x = 60 + i * 72
                d.polygon([(x, y + 50), (x + 50, y + 50), (x + 50, y + 34), (x + 20, y + 30), (x + 10, y + 20), (x, y + 20)],
                          fill=r.choice([(30, 30, 30), (120, 70, 40), (200, 200, 200), (160, 40, 40), (40, 60, 120)]))
    elif kind == "florist":
        for i in range(9):
            x = 50 + i * 85
            d.rectangle((x, 300, x + 60, 380), fill=(90, 110, 130))
            for k in range(7):
                cx, cy = x + r.randint(5, 55), 240 + r.randint(0, 60)
                d.line((x + 30, 300, cx, cy), fill=(60, 120, 50), width=3)
                d.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=r.choice([(230, 60, 80), (250, 200, 60), (240, 240, 240), (200, 90, 180), (250, 130, 60)]))
    # door on the right: frame, push bar, OPEN sign
    dx0 = w - 230 if kind != "barber" else w - 330
    d.rectangle((dx0, 40, dx0 + 190, h), outline=(70, 72, 76), width=12)
    d.rectangle((dx0 + 20, int(h * 0.55), dx0 + 170, int(h * 0.55) + 12), fill=(190, 190, 196))
    d.rounded_rectangle((dx0 + 40, 110, dx0 + 150, 160), 8, fill=(20, 20, 20))
    fit_text(d, (dx0 + 95, 136), "OPEN", FONT_B, 96, 34, (255, 60, 70))
    fit_text(d, (dx0 + 95, 200), "7 DAYS", FONT_B, 120, 18, (250, 250, 250))
    return glass_over(im, seed)


SHOPS = {   # set: (sign text, sign colours, interior kind)
    "A": [("QUICK CUTS", (20, 30, 60), (245, 245, 245), "barber"), ("GOLDEN CRUST DONUTS", (240, 196, 60), (90, 40, 20), "donut"),
          ("CORNER PHARMACY", (245, 245, 240), (20, 120, 70), "pharmacy"), ("JADE NOODLE HOUSE", (150, 24, 24), (250, 220, 120), "noodle")],
    "B": [("BEAN THERE CAFE", (60, 40, 30), (240, 220, 190), "cafe"), ("CELL CITY REPAIR", (30, 110, 210), (250, 250, 250), "phone"),
          ("MORALES TAILORING", (30, 30, 30), (220, 190, 120), "tailor"), ("SECOND CHAPTER BOOKS", (30, 70, 50), (240, 230, 200), "books")],
    "C": [("TONY'S PIZZA", (30, 90, 40), (250, 240, 220), "pizza"), ("HAPPY PAWS PET SUPPLY", (240, 140, 40), (255, 255, 255), "pets"),
          ("PIXEL ARCADE", (30, 20, 60), (120, 230, 255), "games"), ("LUXE NAILS", (240, 200, 214), (140, 40, 90), "nails")],
    "D": [("BRIGHT SMILE DENTAL", (240, 248, 250), (30, 120, 160), "dental"), ("ACE TAX & INSURANCE", (30, 50, 90), (250, 250, 250), "tax"),
          ("SOLE MATES SHOES", (120, 30, 40), (250, 230, 200), "shoes"), ("PETAL & STEM FLOWERS", (230, 240, 226), (60, 120, 60), "florist")],
}


def shop_sets(keys=None):
    for key, shops in SHOPS.items():
        if keys and key not in keys:
            continue
        fronts = Image.new("RGB", (1024, 1024))
        signs = Image.new("RGB", (1024, 512))
        sd = ImageDraw.Draw(signs)
        for i, (text, bg, fg, kind) in enumerate(shops):
            fronts.paste(shop_interior(kind, 400 + i + 10 * "ABCD".index(key)).resize((512, 512)), ((i % 2) * 512, (i // 2) * 512))
            y0 = i * 128
            sd.rectangle((0, y0, 1024, y0 + 128), fill=bg)
            sd.rectangle((10, y0 + 10, 1014, y0 + 118), outline=fg, width=4)
            fit_text(sd, (512, y0 + 66), text, FONT_B, 940, 78, fg)
        save(f"Storefronts{key}", fronts, 30)
        save(f"ShopSigns{key}", signs.filter(ImageFilter.GaussianBlur(0.5)), 140)


def awnings():
    """4 striped / plain canvas awnings side by side (UV quarter each)."""
    W, H = 1024, 256
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    specs = [((170, 30, 30), (240, 236, 226)), ((24, 90, 60), (236, 228, 200)), ((26, 40, 80), None), ((120, 30, 44), None)]
    for i, (a, b) in enumerate(specs):
        x0 = i * 256
        if b:
            for k in range(8):
                d.rectangle((x0 + k * 32, 0, x0 + k * 32 + 16, H), fill=a)
                d.rectangle((x0 + k * 32 + 16, 0, x0 + k * 32 + 32, H), fill=b)
        else:
            d.rectangle((x0, 0, x0 + 256, H), fill=a)
            d.rectangle((x0, H - 30, x0 + 256, H - 26), fill=(230, 220, 200))
    g = np.asarray(scan("Plaster001", size=W).convert("L").resize((W, H)), np.float32) / 255
    arr = np.asarray(im, np.float32) * (0.82 + 0.3 * (g[..., None] / g.mean() - 1) + 0.18)
    save("Awnings", Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), 200)


def lobby_door():
    w, h = 512, 768
    im = Image.new("RGB", (w, h), (40, 34, 30))
    d = ImageDraw.Draw(im)
    inner = shop_interior("tailor", 77, 400, 600)
    inner = Image.new("RGB", (400, 600), (180, 150, 110))
    di = ImageDraw.Draw(inner)
    di.rectangle((0, 470, 400, 600), fill=(120, 96, 70))
    for k in range(6):                                                # mailboxes on the lobby wall
        for j in range(3):
            di.rectangle((40 + k * 52, 200 + j * 50, 84 + k * 52, 240 + j * 50), fill=(170, 150, 90), outline=(90, 70, 40), width=3)
    di.rectangle((150, 20, 250, 40), fill=(255, 240, 210))
    im.paste(glass_over(inner, 5, 0.3), (56, 120))
    d.rectangle((56, 120, 456, 720), outline=(70, 56, 30), width=14)
    d.line((256, 120, 256, 720), fill=(70, 56, 30), width=12)
    for x in (226, 286):
        d.rectangle((x - 6, 380, x + 6, 470), fill=(200, 170, 80))
    d.rectangle((56, 20, 456, 110), fill=(30, 26, 22))
    fit_text(d, (256, 66), "1425", FONT_B, 300, 64, (220, 190, 110))
    save("LobbyDoor", im, 90)


def ghost_sign():
    """Faded painted wall ad (original wording), RGBA paint only: it lies over the side brick, so
    the bricks keep their real scale and show through the worn paint."""
    W, H = 1024, 512
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    d.rectangle((20, 20, W - 20, H - 20), fill=(232, 226, 204, 150))
    d.rectangle((44, 44, W - 44, H - 44), outline=(40, 60, 90, 190), width=12)
    fit_text(d, (W / 2, 150), "HALVORSEN & SONS", FONT_B, W - 140, 110, (40, 60, 90, 210))
    fit_text(d, (W / 2, 290), "FINE FURNITURE", FONT_B, W - 200, 96, (150, 40, 30, 200))
    fit_text(d, (W / 2, 400), "EST. 1931", FONT_B, 400, 60, (40, 60, 90, 190))
    # weathering: knock the paint out in a brick-like pattern and blotches (cut-out alpha)
    g = np.asarray(scan("Bricks085", size=1024).crop((0, 0, W, H)).convert("L"), np.float32)
    r = random.Random(3)
    blot = Image.new("L", (W // 32, H // 32))
    blot.putdata([r.randint(0, 255) for _ in range(blot.width * blot.height)])
    blot = np.asarray(blot.resize((W, H), Image.BICUBIC), np.float32)
    keep = (g > np.percentile(g, 35)) & (blot > 70)
    a = np.asarray(over.getchannel("A"), np.float32)
    a = np.where(keep & (a > 0), 255, 0).astype(np.uint8)
    rgb = Image.new("RGB", (W, H), (200, 190, 170))
    rgb.paste(over.convert("RGB"), mask=over.getchannel("A"))
    out = rgb.convert("RGBA")
    out.putalpha(Image.fromarray(a))
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, "GhostSign_Color.png"), optimize=True)
    Image.new("RGB", (W, H), (220, 220, 220)).save(os.path.join(OUT, "GhostSign_Roughness.png"))
    print("wrote GhostSign")


def brick_building():
    from tex_kit import glass_set
    real("BrickRed", "Bricks085", 1024)
    real("BrickBrown", "Bricks094", 1024)
    real("BrickTan", "Bricks101", 1024, tint=(196, 160, 120), gain=1.1)
    real("StoneTrim", "Concrete034", 512, tint=(214, 206, 188))
    real("RoofTar", "Concrete044D", 512, tint=(70, 70, 72), gain=0.8)
    real("TankWood", "Planks037A", 512) if os.path.exists(os.path.join(SRC, "Planks037A_Color.png")) else real("TankWood", "Planks023A", 512)
    paint("FireSteel", (34, 36, 34), grain="Metal029", strength=0.6)
    paint("HvacGrey", (168, 170, 166), grain="PaintedMetal012", strength=0.3)
    glass_set(lambda n, c, r=None: save(n, c, r), prefix="Glass", n=6, seed=940, kinds=("home",), size=(256, 256))
    shop_sets(); awnings(); lobby_door(); ghost_sign()


# ================================================================= Blue Comet Diner
def diner_interior(w=2048, h=512):
    """Through the diner's ribbon windows: red booths + tables at the glass, pendant lamps, the
    counter with stools behind, pie case, menu boards, checker floor."""
    r = random.Random(77)
    im = Image.new("RGB", (w, h), (238, 228, 206))
    d = ImageDraw.Draw(im)
    d.rectangle((0, int(h * 0.50), w, int(h * 0.72)), fill=(46, 96, 168))           # blue enamel wainscot
    for x in range(0, w, 6):
        d.line((x, int(h * 0.50), x, int(h * 0.72)), fill=(52, 104, 176))
    d.rectangle((0, int(h * 0.50) - 6, w, int(h * 0.50)), fill=(205, 208, 210))      # chrome rail
    cs = 24                                                                            # checker floor
    for y in range(int(h * 0.72), h, cs):
        for x in range(0, w, cs):
            if ((x // cs) + (y // cs)) % 2 == 0:
                d.rectangle((x, y, x + cs - 1, y + cs - 1), fill=(30, 30, 32))
            else:
                d.rectangle((x, y, x + cs - 1, y + cs - 1), fill=(226, 222, 212))
    # back counter: menu boards, pie case, coffee machines
    for i, x in enumerate(range(80, w - 80, 380)):
        d.rectangle((x, 40, x + 300, 150), fill=(30, 34, 36))
        d.rectangle((x + 6, 46, x + 294, 144), outline=(200, 190, 160), width=2)
        for k in range(4):
            yy = 64 + k * 20
            d.line((x + 20, yy, x + 20 + r.randint(120, 200), yy), fill=(236, 226, 200), width=4)
            d.line((x + 250, yy, x + 280, yy), fill=(236, 200, 90), width=4)
    d.rectangle((0, 200, w, 228), fill=(200, 202, 204))                               # counter top (chrome)
    d.rectangle((0, 228, w, int(h * 0.50) - 6), fill=(180, 40, 44))                    # counter front
    for x in range(0, w, 14):
        d.line((x, 232, x, int(h * 0.50) - 8), fill=(166, 34, 38))
    for x in range(140, w, 520):                                                      # pie case
        d.rectangle((x, 150, x + 160, 200), fill=(210, 226, 232), outline=(170, 176, 180), width=3)
        for k in range(4):
            d.ellipse((x + 10 + k * 38, 170, x + 40 + k * 38, 194), fill=(214, 168, 96))
    for x in range(60, w, 110):                                                      # stools
        d.rectangle((x - 3, int(h * 0.50) - 6, x + 3, int(h * 0.64)), fill=(190, 192, 194))
        d.ellipse((x - 26, int(h * 0.50) - 26, x + 26, int(h * 0.50) - 4), fill=(196, 36, 40), outline=(220, 222, 224), width=3)
    # booths at the window: red vinyl backs + white tables
    for x in range(0, w, 256):
        for bx in (x + 10, x + 170):
            d.rounded_rectangle((bx, int(h * 0.58), bx + 76, h - 10), 14, fill=(184, 30, 36))
            for k in range(4):
                d.line((bx + 8 + k * 18, int(h * 0.60), bx + 8 + k * 18, h - 16), fill=(160, 24, 30), width=3)
        d.rectangle((x + 92, int(h * 0.72), x + 164, int(h * 0.75)), fill=(236, 234, 228))
        d.rectangle((x + 124, int(h * 0.75), x + 132, h), fill=(170, 172, 174))
        d.ellipse((x + 104, int(h * 0.70), x + 118, int(h * 0.72) + 2), fill=(240, 240, 236))
        d.rectangle((x + 140, int(h * 0.69), x + 148, int(h * 0.72)), fill=(200, 60, 50))
    for x in range(128, w, 256):                                                      # pendant lamps
        d.line((x, 0, x, 120), fill=(60, 60, 60), width=2)
        d.pieslice((x - 34, 104, x + 34, 150), 180, 360, fill=(208, 48, 44))
        d.ellipse((x - 12, 120, x + 12, 136), fill=(255, 244, 200))
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    return glass_over(im, 78, amount=0.30)


def diner_steel():
    """Fluted stainless panel: brushed grain with vertical flutes (tiles every 1 m)."""
    g = np.asarray(scan("Metal029", size=512).convert("L"), np.float32)
    g = (g - g.mean()) * 0.35
    x = np.arange(512)[None, :]
    # 4 broad flutes per metre: finer ribs shimmered (moire) in game at a distance
    ph = (x / 512 * 4) % 1.0
    flute = 16 * np.cos(ph * 2 * math.pi) + 10 * (np.abs(ph - 0.5) < 0.03)
    v = np.clip(168 + g + flute, 0, 255)
    rgb = np.stack([v * 0.98, v, v * 1.02], -1)
    rough = Image.fromarray(np.clip(70 + g * 0.5, 0, 255).astype(np.uint8)).convert("RGB")
    save("DinerSteel", Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)), rough)


def diner_signs():
    """DinerSigns atlas 1024x1024: rows 0-511 pylon face, 512-767 OPEN 24 HOURS, 768-1023 roof DINER."""
    W = 1024
    im = Image.new("RGB", (W, W), (18, 30, 62))
    d = ImageDraw.Draw(im)
    r = random.Random(5)
    # pylon face: night-blue panel, stars, comet swoosh, script name, DINER plate
    for _ in range(70):
        x, y = r.randint(10, W - 10), r.randint(10, 500)
        s = r.choice((2, 2, 3, 4))
        d.ellipse((x - s, y - s, x + s, y + s), fill=(250, 236, 170))
    d.rectangle((6, 6, W - 7, 505), outline=(232, 236, 240), width=10)
    for k in range(12):
        d.arc((-420 + k * 6, 80 + k * 4, 900 - k * 6, 560 + k * 4), 200, 300, fill=(255, 196 - k * 6, 60), width=6)
    d.polygon([(860, 70), (884, 128), (946, 132), (898, 170), (914, 232), (860, 196), (806, 232), (822, 170),
               (774, 132), (836, 128)], fill=(255, 220, 90))
    fit_text(d, (W // 2 - 30, 200), "Blue Comet", "/usr/share/fonts/truetype/crosextra/Caladea-BoldItalic.ttf",
             760, 190, (120, 200, 255))
    d.rectangle((150, 330, W - 150, 470), fill=(214, 40, 44), outline=(250, 250, 250), width=6)
    fit_text(d, (W // 2, 402), "DINER", FONT_B, 640, 120, (255, 252, 240))
    # OPEN 24 HOURS
    d.rectangle((0, 512, W, 767), fill=(240, 236, 226))
    d.rectangle((10, 522, W - 11, 757), outline=(214, 40, 44), width=10)
    fit_text(d, (W // 2, 600), "OPEN 24 HOURS", FONT_B, 900, 110, (214, 40, 44))
    fit_text(d, (W // 2, 700), "BREAKFAST ALL DAY  ·  BURGERS  ·  SHAKES  ·  PIE", FONT_B, 900, 44, (30, 50, 110))
    # roof DINER letters (white on red, chrome edge)
    d.rectangle((0, 768, W, W), fill=(200, 34, 38))
    d.rectangle((8, 776, W - 9, W - 9), outline=(226, 230, 234), width=8)
    fit_text(d, (W // 2, 900), "BLUE COMET DINER", FONT_B, 940, 150, (255, 250, 236))
    rough = Image.new("RGB", (W, W), (90, 90, 90))
    save("DinerSigns", im, rough)


def glass_block():
    """Glass block wall at the entrance vestibule: 8x8 frosted blocks with mortar lines."""
    S = 256
    im = Image.new("RGB", (S, S), (196, 200, 198))
    d = ImageDraw.Draw(im)
    c = S // 4
    for i in range(4):
        for j in range(4):
            x, y = i * c, j * c
            d.rectangle((x + 4, y + 4, x + c - 4, y + c - 4), fill=(178, 210, 222))
            d.rectangle((x + 12, y + 12, x + c - 12, y + c - 12), fill=(196, 224, 232))
            d.line((x + 8, y + c // 2, x + c - 8, y + c // 2), fill=(214, 234, 240), width=2)
    save("GlassBlock", im.filter(ImageFilter.GaussianBlur(1.2)), Image.new("RGB", (S, S), (40, 40, 40)))


def diner_door():
    """Chrome-framed glass double door with push bars (explicit UVs)."""
    W, H = 512, 768
    inside = diner_interior().crop((900, 0, 1300, 512)).resize((W, H))
    im = Image.new("RGB", (W, H), (190, 194, 198))
    im.paste(inside.crop((40, 60, W - 40, H - 60)), (40, 60))
    d = ImageDraw.Draw(im)
    d.rectangle((W // 2 - 8, 0, W // 2 + 8, H), fill=(196, 200, 204))
    for x in (60, W // 2 + 30):
        d.rectangle((x, H // 2 - 12, x + W // 2 - 90, H // 2 + 12), fill=(220, 222, 226), outline=(150, 152, 156), width=2)
    d.rectangle((40, 60, W - 40, H - 60), outline=(150, 154, 158), width=6)
    save("DinerDoor", im)


def diner():
    diner_steel()
    paint("DinerBlue", (40, 92, 170), grain="PaintedMetal012", strength=0.25)
    paint("DinerRed", (196, 34, 40), grain="PaintedMetal012", strength=0.25)
    real("DinerTile", "Tiles107", 512, tint=(70, 96, 150), gain=1.05)
    real("KitchenBrick", "Bricks097", 1024, tint=(196, 186, 170), gain=1.1)
    save("DinerInterior", diner_interior(), Image.new("RGB", (2048, 512), (30, 30, 30)))
    diner_signs(); glass_block(); diner_door()
    # lot asphalt: the CC0 scan the Bellmont estates use (already checked for text)
    est = os.path.join(ROOT, "art", "blender", "estate", "tex")
    for k in ("Color", "Roughness"):
        shutil.copyfile(os.path.join(est, f"Asphalt_{k}.png"), os.path.join(OUT, f"LotAsphalt_{k}.png"))


# ================================================================= Hotel Solana
def hotel_lobby(w=2048, h=512):
    """Through the lobby glass: marble floor, walnut wall panels, reception desk, chandeliers,
    lounge chairs, potted palms, brass elevator doors."""
    r = random.Random(31)
    im = Image.new("RGB", (w, h), (120, 80, 52))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 128):                                                       # walnut panels
        d.rectangle((x + 4, 30, x + 124, int(h * 0.66)), fill=(132, 88, 58), outline=(98, 64, 40), width=3)
        for k in range(8):
            yy = 40 + k * 34
            d.line((x + 10, yy, x + 118, yy + r.randint(-2, 2)), fill=(124, 82, 54), width=2)
    for x in (300, 1650):                                                              # brass elevator doors
        d.rectangle((x, 80, x + 200, int(h * 0.66)), fill=(196, 160, 90), outline=(150, 118, 60), width=6)
        d.line((x + 100, 80, x + 100, int(h * 0.66)), fill=(140, 110, 60), width=4)
        d.rectangle((x + 70, 50, x + 130, 70), fill=(40, 30, 24))
    d.rectangle((850, 230, 1250, int(h * 0.66)), fill=(70, 46, 32))                   # reception desk
    d.rectangle((840, 220, 1260, 238), fill=(220, 214, 200))
    d.rectangle((850, 250, 1250, 256), fill=(200, 168, 96))
    d.rectangle((930, 60, 1170, 150), fill=(30, 24, 20), outline=(200, 168, 96), width=4)   # clock plaque, no text
    d.ellipse((1015, 70, 1085, 140), fill=(236, 228, 210), outline=(200, 168, 96), width=3)
    d.line((1050, 105, 1050, 80), fill=(30, 24, 20), width=3); d.line((1050, 105, 1068, 112), fill=(30, 24, 20), width=3)
    fy = int(h * 0.66)                                                                 # marble floor
    for y in range(fy, h, 28):
        for x in range(0, w, 56):
            c = (232, 228, 220) if ((x // 56) + (y // 28)) % 2 else (212, 206, 196)
            d.rectangle((x, y, x + 55, y + 27), fill=c)
    d.rectangle((600, fy + 30, 1500, h - 10), fill=(140, 30, 40))                      # rug
    d.rectangle((620, fy + 40, 1480, h - 20), outline=(210, 170, 90), width=4)
    for x in range(220, w, 520):                                                       # chandeliers
        d.line((x, 0, x, 60), fill=(150, 120, 70), width=3)
        for k in range(-3, 4):
            d.ellipse((x + k * 22 - 8, 70 + abs(k) * 6, x + k * 22 + 8, 86 + abs(k) * 6), fill=(255, 238, 190))
        d.arc((x - 80, 30, x + 80, 110), 0, 180, fill=(200, 168, 96), width=4)
    for x in (120, 760, 1340, 1900):                                                   # lounge chairs
        for dx in (0, 120):
            d.rounded_rectangle((x + dx, fy - 40, x + dx + 90, fy + 50), 12, fill=(36, 70, 72))
            d.rectangle((x + dx + 6, fy + 10, x + dx + 84, fy + 50), fill=(46, 88, 90))
        d.ellipse((x + 92, fy + 20, x + 118, fy + 40), fill=(200, 168, 96))
    for x in (40, 640, 1560, 2000):                                                    # potted palms
        d.rectangle((x - 20, fy + 20, x + 20, fy + 80), fill=(190, 180, 160))
        for k in range(9):
            a = math.radians(200 + k * 17)
            d.line((x, fy + 20, x + math.cos(a) * 90, fy + 20 + math.sin(a) * 140), fill=(50, 110, 50), width=10)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    return glass_over(im, 32, amount=0.32)


def hotel_signs():
    """HotelSigns atlas 1024: x 0-255 vertical blade HOTEL; right side rows: 0-255 SOLANA roof
    sign, 256-447 canopy fascia, 448-639 VALET, 640-1023 monument plaque."""
    W = 1024
    im = Image.new("RGB", (W, W), (24, 52, 56))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, W), fill=(150, 26, 34))
    d.rectangle((10, 10, 245, W - 11), outline=(246, 226, 180), width=8)
    for i, ch in enumerate("HOTEL"):
        fit_text(d, (128, 110 + i * 200), ch, FONT_B, 200, 170, (255, 244, 214))
    d.rectangle((256, 0, W, 255), fill=(22, 60, 64))
    d.rectangle((266, 10, W - 11, 245), outline=(240, 214, 150), width=8)
    fit_text(d, (640, 128), "SOLANA", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 680, 190, (250, 236, 200))
    d.rectangle((256, 256, W, 447), fill=(20, 22, 24))
    d.rectangle((262, 262, W - 7, 441), outline=(200, 168, 96), width=6)
    fit_text(d, (640, 352), "HOTEL  SOLANA", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 700, 120, (220, 190, 120))
    d.rectangle((256, 448, W, 639), fill=(240, 236, 226))
    d.rectangle((262, 454, W - 7, 633), outline=(150, 26, 34), width=8)
    fit_text(d, (640, 520), "VALET PARKING", FONT_B, 680, 80, (150, 26, 34))
    fit_text(d, (640, 590), "GUEST DROP-OFF", FONT_B, 600, 44, (40, 40, 44))
    d.rectangle((256, 640, W, W), fill=(206, 196, 176))
    d.rectangle((270, 654, W - 15, W - 15), outline=(150, 130, 96), width=6)
    fit_text(d, (640, 780), "HOTEL SOLANA", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 680, 110, (60, 50, 40))
    fit_text(d, (640, 900), "EST. 1928", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 400, 70, (120, 96, 60))
    save("HotelSigns", im, Image.new("RGB", (W, W), (90, 90, 90)))


def hotel():
    real("HotelStucco", "Plaster001", 1024, tint=(228, 208, 178), gain=1.05)
    real("Pavers", "Tiles107", 512, tint=(178, 162, 142))
    paint("HotelTeal", (34, 84, 88), grain="PaintedMetal012", strength=0.25)
    save("HotelLobby", hotel_lobby(), Image.new("RGB", (2048, 512), (30, 30, 30)))
    hotel_signs()


# ================================================================= Lindell Park + skatepark
def park_signs():
    """ParkSigns atlas 1024x512: top half LINDELL PARK (carved wood look), bottom SKATE PARK board."""
    W, H = 1024, 512
    wood = scan("Planks023A", size=1024).crop((0, 0, W, 256)).convert("RGB")
    wood = Image.fromarray(np.clip(np.asarray(wood, np.float32) * np.array([0.75, 0.55, 0.38]), 0, 255).astype(np.uint8))
    im = Image.new("RGB", (W, H), (30, 30, 30))
    im.paste(wood, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, W - 9, 247), outline=(232, 214, 170), width=6)
    fit_text(d, (W // 2, 110), "LINDELL PARK", "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf", 900, 130, (246, 232, 196))
    fit_text(d, (W // 2, 205), "OPEN DAWN TO DUSK", FONT_B, 600, 40, (232, 214, 170))
    d.rectangle((0, 256, W, H), fill=(28, 30, 34))
    d.rectangle((8, 264, W - 9, H - 9), outline=(250, 200, 40), width=8)
    fit_text(d, (W // 2, 350), "LINDELL SKATE PARK", FONT_B, 900, 100, (250, 200, 40))
    fit_text(d, (W // 2, 445), "HELMETS RECOMMENDED  ·  RIDE AT YOUR OWN RISK", FONT_B, 900, 40, (236, 236, 236))
    save("ParkSigns", im, Image.new("RGB", (W, H), (150, 150, 150)))


def park():
    # real scans (checked at full size: no text, logos or marks)
    real("ParkPavers", "PavingStones081", 1024)                                 # herringbone walks
    real("PlazaStone", "PavingStones128", 1024)                                 # fountain plaza slabs
    real("FountainStone", "Travertine009", 1024, tint=(222, 212, 192), gain=1.0)  # basin, column, bowls
    real("ParkWall", "Concrete025", 1024, tint=(150, 148, 142), gain=0.85)                                       # exposed-aggregate wall
    real("ParkCap", "Concrete016", 512, tint=(150, 148, 142), gain=0.9)        # wall caps, kerbs
    real("ParkLawn", "Grass004", 1024)
    real("ParkMulch", "WoodChips001", 1024, tint=(132, 96, 66), gain=1.0)
    # skate concrete: mid-grey poured concrete (Dev 2026-11-07: the light version glared white in game):
    # trowel cloud, fine grain, soft dark stains, wheel scuffs, saw-cut joints on the tile edge
    S_ = 1024
    gl = scan("Concrete042A", size=S_).convert("L")
    g = np.asarray(gl.filter(ImageFilter.GaussianBlur(4)), np.float32)
    v = 112 + (g - g.mean()) * 0.55
    fine = np.asarray(gl, np.float32)
    v += (fine - np.asarray(gl.filter(ImageFilter.GaussianBlur(3)), np.float32)) * 0.6
    rs = np.random.default_rng(11)
    yy, xx = np.mgrid[0:S_, 0:S_].astype(np.float32)
    for _ in range(9):                                                          # soft stains (wrap round: tiles)
        cx, cy, rad, amp = rs.uniform(0, S_), rs.uniform(0, S_), rs.uniform(40, 140), rs.uniform(8, 18)
        dx = np.minimum(abs(xx - cx), S_ - abs(xx - cx))
        dy = np.minimum(abs(yy - cy), S_ - abs(yy - cy))
        v -= amp * np.exp(-(dx * dx + dy * dy) / (2 * rad * rad))
    sc = Image.new("L", (S_, S_), 0)
    d = ImageDraw.Draw(sc)
    for _ in range(40):                                                         # wheel scuffs: long thin dark arcs
        cx, cy, R_ = rs.uniform(0, S_), rs.uniform(0, S_), rs.uniform(150, 600)
        a0 = rs.uniform(0, 360)
        d.arc((cx - R_, cy - R_, cx + R_, cy + R_), a0, a0 + rs.uniform(8, 25), fill=int(rs.uniform(60, 140)), width=2)
    scuff = np.asarray(sc.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
    v -= scuff * 22
    joint = (np.minimum(xx, S_ - 1 - xx) < 3) | (np.minimum(yy, S_ - 1 - yy) < 3)
    v = np.where(joint, v - 35, v)
    col = np.stack([v * 1.0, v * 0.99, v * 0.96], -1)
    r = np.where(joint, 235, 205 + (g - g.mean()) * 0.3 - scuff * 30)
    save("SkateCrete", Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)),
         Image.fromarray(np.clip(r, 0, 255).astype(np.uint8)))
    for n, c in (("PlayRed", (200, 50, 40)), ("PlayBlue", (40, 100, 190)), ("PlayYellow", (236, 186, 40)),
                 ("PlayGreen", (60, 150, 70))):
        paint(n, c, grain="PaintedMetal012", strength=0.25)
    park_signs()
    src = {"FxPool": "estate", "FxFall": "estate", "FxRipple": "estate"}
    for n, d_ in src.items():
        for k in ("Color", "Roughness"):
            sp = os.path.join(ROOT, "art", "blender", d_, "tex", f"{n}_{k}.png")
            if os.path.exists(sp):
                shutil.copyfile(sp, os.path.join(OUT, f"{n}_{k}.png"))


# ================================================================= Westgate Plaza strip mall
def mall():
    shop_sets("CD")
    real("MallStucco", "PaintedPlaster017", 1024, tint=(222, 206, 184), gain=1.05)
    paint("MallTrim", (120, 40, 36), grain="PaintedMetal012", strength=0.25)
    W, H = 1024, 512                                                          # pylon sign: name + 8 tenant panels
    im = Image.new("RGB", (W, H), (36, 40, 46))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 150), fill=(120, 40, 36))
    d.rectangle((8, 8, W - 9, 142), outline=(240, 220, 180), width=6)
    fit_text(d, (W // 2, 78), "WESTGATE PLAZA", FONT_B, 900, 100, (250, 240, 220))
    tenants = [t for k in "CD" for t in SHOPS[k]]
    for i, (text, bg, fg, _) in enumerate(tenants):
        x0, y0 = (i % 2) * 512, 160 + (i // 2) * 88
        d.rectangle((x0 + 8, y0, x0 + 504, y0 + 80), fill=bg, outline=(200, 200, 200), width=3)
        fit_text(d, (x0 + 256, y0 + 41), text, FONT_B, 470, 44, fg)
    save("MallPylon", im, Image.new("RGB", (W, H), (110, 110, 110)))


# ================================================================= Delgado Auto Repair
def auto():
    real("GarageMetal", "CorrugatedSteel005", 1024, tint=(176, 182, 186), gain=1.05)
    S_ = 512                                                                   # roll-up door: 8 broad ribs per tile (2 m)
    g = np.asarray(scan("PaintedMetal012", size=S_).convert("L"), np.float32)
    y = np.arange(S_)[:, None]
    ph = (y / S_ * 8) % 1.0
    v = 196 + (g - g.mean()) * 0.3 + 14 * np.cos(ph * 2 * math.pi) - 30 * (np.abs(ph - 0.97) < 0.03)
    save("RollDoor", Image.fromarray(np.clip(np.stack([v * 0.97, v, v * 1.03], -1), 0, 255).astype(np.uint8)))
    W, H = 1024, 512
    im = Image.new("RGB", (W, H), (200, 30, 34))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, W - 9, 247), outline=(255, 255, 255), width=8)
    fit_text(d, (W // 2, 92), "DELGADO", FONT_B, 900, 110, (255, 255, 255))
    fit_text(d, (W // 2, 196), "AUTO REPAIR", FONT_B, 700, 70, (255, 230, 120))
    d.rectangle((0, 256, W, H), fill=(28, 30, 34))
    d.rectangle((8, 264, W - 9, H - 9), outline=(255, 230, 120), width=6)
    fit_text(d, (W // 2, 330), "TIRES  ·  BRAKES  ·  OIL CHANGE", FONT_B, 920, 70, (255, 255, 255))
    fit_text(d, (W // 2, 430), "ALIGNMENT  ·  SMOG CHECK  ·  A/C", FONT_B, 920, 60, (255, 230, 120))
    save("AutoSigns", im, Image.new("RGB", (W, H), (110, 110, 110)))


# ================================================================= Sundial Fuel gas station
def fuel():
    real("FuelStucco", "PaintedPlaster017", 1024, tint=(214, 200, 176), gain=0.95)
    paint("FuelWhite", (226, 228, 228), grain="PaintedMetal012", strength=0.2)
    paint("FuelOrange", (226, 112, 28), grain="PaintedMetal012", strength=0.2)
    paint("PumpRed", (186, 40, 34), grain="PaintedMetal012", strength=0.25)
    save("MartInterior", shop_interior("mart", 77).resize((1024, 512)), 30)
    W = 1024
    im = Image.new("RGB", (W, W), (30, 30, 34))
    d = ImageDraw.Draw(im)
    ORG, WHT, DK = (232, 116, 26), (250, 250, 248), (26, 28, 32)

    def sun(cx, cy, r):
        for k in range(12):
            a_ = k / 12 * math.tau
            d.line((cx + math.cos(a_) * r * 1.2, cy + math.sin(a_) * r * 1.2, cx + math.cos(a_) * r * 1.7,
                    cy + math.sin(a_) * r * 1.7), fill=(255, 210, 60), width=max(2, int(r * 0.18)))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 200, 40))
    # A: canopy fascia (0..1024 x 0..256)
    d.rectangle((0, 0, W, 256), fill=WHT)
    d.rectangle((0, 196, W, 236), fill=ORG)
    d.rectangle((0, 236, W, 256), fill=(200, 40, 34))
    sun(150, 98, 54)
    fit_text(d, (590, 104), "SUNDIAL", FONT_B, 700, 150, ORG)
    # B: pylon (0..512 x 256..1024): logo head + three LED price rows
    d.rectangle((0, 256, 512, 1024), fill=DK)
    d.rectangle((10, 266, 502, 520), fill=WHT)
    sun(256, 350, 50)
    fit_text(d, (256, 466), "SUNDIAL", FONT_B, 440, 90, ORG)
    for i, (grade, price) in enumerate((("UNLEADED", "3.49"), ("PLUS", "3.79"), ("DIESEL", "3.99"))):
        y0 = 540 + i * 160
        d.rectangle((14, y0, 498, y0 + 146), fill=(12, 12, 14), outline=(90, 90, 96), width=4)
        fit_text(d, (256, y0 + 30), grade, FONT_B, 440, 36, WHT)
        fit_text(d, (236, y0 + 96), price, FONT_B, 360, 84, (255, 70, 50))
        fit_text(d, (440, y0 + 76), "9", FONT_B, 40, 36, (255, 70, 50))
    # C: kiosk sign (512..1024 x 256..512)
    d.rectangle((512, 256, 1024, 512), fill=ORG)
    d.rectangle((522, 266, 1014, 502), outline=WHT, width=6)
    fit_text(d, (768, 350), "SUNDIAL MART", FONT_B, 460, 96, WHT)
    fit_text(d, (768, 450), "SNACKS · COFFEE · TIRE AIR", FONT_B, 460, 40, (255, 240, 210))
    # D: pump face (512..1024 x 512..1024)
    d.rectangle((512, 512, 1024, 1024), fill=(196, 44, 36))
    d.rectangle((512, 512, 1024, 600), fill=WHT)
    fit_text(d, (768, 556), "SUNDIAL", FONT_B, 420, 64, ORG)
    d.rectangle((572, 630, 964, 800), fill=(20, 22, 26), outline=(160, 160, 166), width=6)       # display
    for k, t in enumerate(("$  24.80", "GAL  7.106")):
        fit_text(d, (768, 680 + k * 70), t, FONT_B, 360, 46, (120, 240, 140))
    for k, (g, c) in enumerate((("87", (60, 60, 64)), ("89", (60, 60, 64)), ("93", (60, 60, 64)))):
        x = 600 + k * 130
        d.rectangle((x, 840, x + 100, 940), fill=c, outline=WHT, width=4)
        fit_text(d, (x + 50, 890), g, FONT_B, 80, 50, WHT)
    save("FuelSigns", im, 120)
    # public parking signs (Westgate lot by Ironwood Arms): blue P panel + rates panel
    im = Image.new("RGB", (512, 512), (24, 70, 160))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, 503, 503), outline=(250, 250, 250), width=8)
    fit_text(d, (256, 190), "P", FONT_B, 300, 300, (255, 255, 255))
    fit_text(d, (256, 380), "PUBLIC PARKING", FONT_B, 440, 52, (255, 255, 255))
    fit_text(d, (256, 450), "$2 / HOUR  ·  PAY AT MACHINE", FONT_B, 440, 28, (220, 230, 255))
    save("LotSigns", im, 120)


STEPS = {"street": street, "brick": brick_building, "diner": diner, "hotel": hotel, "park": park, "mall": mall, "auto": auto, "fuel": fuel}

if __name__ == "__main__":
    fetch()
    for step in (sys.argv[1:] or list(STEPS)):
        STEPS[step]()
