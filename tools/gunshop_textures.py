"""Textures for the Ironwood Arms gun shop (thread "Build GTA-style gun shop", 2026-11-07).

  python3 tools/gunshop_textures.py        -> art/blender/gunshop/tex/<Name>_Color.png (+ _Roughness)

An original store in the style of a GTA gun shop: our own name (IRONWOOD ARMS) and mark (a
pine inside a sight ring on a shield). Real surfaces come from CC0 ambientCG scans (downloaded
once into the git-ignored art/gunshop/src), printed parts (sign, posters, targets, ammo boxes,
price cards, lane numbers) are drawn here with PIL.

Content rules: no alcohol, no gambling, no real brands or gun makers, no URLs, no credit text,
no watermarks. Calibre labels are generic (9MM, 5.56, 12 GA).
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
from tex_kit import FONT_B, FONT_M, FONT_R, fit_text, font, grime, stucco, surface  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "art", "gunshop", "src")
OUT = os.path.join(ROOT, "art", "blender", "gunshop", "tex")
UA = {"User-Agent": "Mozilla/5.0 (tulevo-build)"}
SCANS = ["Concrete034", "Concrete044D", "Concrete031", "PaintedPlaster017", "PaintedMetal012", "Metal029", "Planks023A", "Tiles107"]

AMBER = (232, 150, 30)
INK = (24, 26, 28)
PAPER = (238, 236, 228)


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


def scan(a, kind="Color", size=512):
    return Image.open(os.path.join(SRC, f"{a}_{kind}.png")).convert("RGB").resize((size, size), Image.LANCZOS)


def save(name, color, rough=None):
    os.makedirs(OUT, exist_ok=True)
    color.convert("RGB").save(os.path.join(OUT, f"{name}_Color.png"), optimize=True)
    if rough is not None:
        if isinstance(rough, (int, float)):
            rough = Image.new("L", color.size, int(rough))
        rough.convert("L").convert("RGB").save(os.path.join(OUT, f"{name}_Roughness.png"), optimize=True)
    print("wrote", name)


def tinted(a, rgb, keep=0.35, size=512, gain=1.0):
    """Scan detail carried over a colour: keep = how much of the scan's own colour stays."""
    arr = np.asarray(scan(a, size=size), np.float32)
    lum = arr.mean(axis=2, keepdims=True)
    out = arr * keep + lum / max(lum.mean(), 1e-3) * np.array(rgb, np.float32) * (1 - keep)
    return Image.fromarray(np.clip(out * gain, 0, 255).astype(np.uint8))


def paint(name, rgb, grain="PaintedMetal012", strength=0.35, size=256, rough=None):
    g = np.asarray(scan(grain, size=size).convert("L"), np.float32) / 255
    g = g / g.mean()
    arr = np.array(rgb, np.float32)[None, None, :] * (1 + (g[..., None] - 1) * strength)
    save(name, Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), scan(grain, "Roughness", size) if rough is None else rough)


# ---------------------------------------------------------------- brand mark
def mark(d, cx, cy, s, fg=AMBER, bg=INK, line=(240, 240, 236)):
    """Shield with a sight ring and a three-tier pine inside (our own mark)."""
    w, h = s, s * 1.15
    shield = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h * 0.05),
              (cx, cy + h / 2), (cx - w / 2, cy + h * 0.05)]
    d.polygon(shield, fill=fg)
    inset = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.86) for x, y in shield]
    d.polygon(inset, fill=bg)
    r = s * 0.3
    oy = cy - h * 0.06
    d.ellipse((cx - r, oy - r, cx + r, oy + r), outline=line, width=max(2, int(s * 0.035)))
    t = max(2, int(s * 0.025))
    for a, b in (((cx - r * 1.35, oy), (cx - r * 0.55, oy)), ((cx + r * 0.55, oy), (cx + r * 1.35, oy)),
                 ((cx, oy - r * 1.35), (cx, oy - r * 0.55))):
        d.line((a, b), fill=line, width=t)
    for k in range(3):                                   # pine tiers
        ty = oy - r * 0.5 + k * r * 0.32
        tw = r * (0.32 + k * 0.16)
        d.polygon([(cx, ty - r * 0.28), (cx + tw, ty + r * 0.16), (cx - tw, ty + r * 0.16)], fill=fg)
    d.rectangle((cx - r * 0.07, oy + r * 0.5, cx + r * 0.07, oy + r * 0.8), fill=fg)


def shop_sign():
    W, H = 2048, 256
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    for y in range(H):                                   # brushed dark panel, lighter at the top
        t = y / H
        d.line((0, y, W, y), fill=(int(34 - 12 * t), int(36 - 12 * t), int(40 - 12 * t)))
    d.rectangle((0, 0, W - 1, H - 1), outline=(90, 92, 96), width=8)
    d.rectangle((0, H - 34, W, H - 18), fill=AMBER)
    mark(d, 150, 118, 170)
    fit_text(d, (1060, 108), "IRONWOOD ARMS", FONT_B, 1500, 150, (244, 242, 236))
    fit_text(d, (1060, 205), "FIREARMS   ·   AMMUNITION   ·   INDOOR RANGE", FONT_B, 1300, 40, AMBER)
    mark(d, W - 150, 118, 170)
    save("ShopSign", grime(img, 0.06, seed=3, streaks=False), 90)


def blade_sign():
    """Two-sided projecting blade sign by the door: mark + ARMS + RANGE."""
    W, H = 256, 768
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W - 1, H - 1), outline=AMBER, width=10)
    mark(d, W / 2, 140, 170)
    for i, ch in enumerate("ARMS"):
        fit_text(d, (W / 2, 300 + i * 92), ch, FONT_B, 200, 96, (244, 242, 236))
    d.rectangle((30, 660, W - 30, 670), fill=AMBER)
    fit_text(d, (W / 2, 712), "RANGE", FONT_B, 190, 48, AMBER)
    save("BladeSign", img, 90)


def poster(name, title, lines, accent, pic=None, seed=1):
    W, H = 384, 576
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 120), fill=accent)
    fit_text(d, (W / 2, 62), title, FONT_B, W - 40, 60, (250, 250, 248))
    y = 150
    if pic == "rifle":
        silhouette_rifle(d, 40, 210, W - 80, INK)
        y = 300
    elif pic == "mark":
        mark(d, W / 2, 230, 150)
        y = 340
    elif pic == "vest":
        d.rounded_rectangle((120, 150, 264, 320), radius=18, fill=(70, 74, 60))
        d.rectangle((150, 150, 234, 185), fill=PAPER)
        for k in range(3):
            d.rectangle((136 + k * 40, 250, 168 + k * 40, 305), fill=(52, 56, 44))
        y = 345
    for ln in lines:
        fit_text(d, (W / 2, y), ln, FONT_B if ln.isupper() else FONT_R, W - 50, 30, INK)
        y += 44
    d.rectangle((0, H - 46, W, H), fill=INK)
    fit_text(d, (W / 2, H - 23), "IRONWOOD ARMS", FONT_B, W - 60, 26, AMBER)
    save(name, grime(img, 0.05, seed=seed, streaks=False), 200)


def silhouette_rifle(d, x, y, w, fill):
    s = w / 300
    P = lambda pts: [(x + px * s, y + py * s) for px, py in pts]
    d.polygon(P([(0, 18), (40, 10), (60, 6), (215, 6), (215, 20), (60, 24), (45, 40), (0, 40)]), fill=fill)   # stock + body
    d.rectangle(P([(215, 9), (300, 15)])[0] + P([(215, 9), (300, 15)])[1], fill=fill)                          # barrel
    d.polygon(P([(110, 20), (125, 20), (122, 52), (108, 50)]), fill=fill)                                       # magazine
    d.polygon(P([(82, 22), (94, 22), (88, 44), (78, 42)]), fill=fill)                                           # grip
    d.rectangle(P([(95, 0), (150, 6)])[0] + P([(95, 0), (150, 6)])[1], fill=fill)                              # rail


def target():
    """Paper range target: our own silhouette, scoring rings, numbers."""
    W, H = 512, 768
    img = Image.new("RGB", (W, H), (236, 232, 218))
    d = ImageDraw.Draw(img)
    sil = (40, 46, 54)
    d.ellipse((186, 70, 326, 230), fill=sil)                                   # head
    d.polygon([(256, 210), (420, 280), (450, 740), (62, 740), (92, 280)], fill=sil)
    for k, r in enumerate((150, 112, 76, 42)):
        cy = 430
        d.ellipse((256 - r, cy - r * 1.2, 256 + r, cy + r * 1.2), outline=(236, 232, 218), width=4)
        fit_text(d, (256, cy - r * 1.2 + 18), str(7 + k), FONT_B, 40, 22, (236, 232, 218))
    d.ellipse((236, 130, 276, 170), outline=(236, 232, 218), width=4)
    fit_text(d, (256, 430), "X", FONT_B, 40, 30, (236, 232, 218))
    r = random.Random(4)
    for _ in range(9):                                                          # a few holes
        hx, hy = r.gauss(256, 60), r.gauss(420, 90)
        d.ellipse((hx - 4, hy - 4, hx + 4, hy + 4), fill=(20, 18, 16))
    fit_text(d, (256, 30), "LANE TARGET  ·  T-2", FONT_B, 400, 26, (60, 60, 60))
    save("Target", img, 230)


def ammo_wall():
    """Shelf face of stacked ammo boxes, 4 rows. Generic calibres, our own colour code."""
    W, H = 1024, 512
    img = Image.new("RGB", (W, H), (40, 40, 42))
    d = ImageDraw.Draw(img)
    kinds = [("9MM", (40, 70, 140)), ("5.56", (60, 90, 50)), ("12 GA", (150, 30, 30)), (".45", (200, 140, 30)),
             ("7.62", (90, 60, 40)), (".22", (30, 120, 130))]
    r = random.Random(11)
    for row in range(4):
        y0 = row * 128 + 10
        x = 6
        while x < W - 60:
            name, col = kinds[r.randrange(len(kinds))]
            bw = r.randint(70, 110)
            bh = r.randint(70, 104)
            for k in range(r.randint(1, 3)):        # a small stack of the same box
                if x + bw > W - 4:
                    break
                c = tuple(max(0, min(255, v + r.randint(-12, 12))) for v in col)
                d.rectangle((x, y0 + 112 - bh, x + bw, y0 + 112), fill=c, outline=(15, 15, 15), width=2)
                d.rectangle((x + 6, y0 + 112 - bh + 10, x + bw - 6, y0 + 112 - bh + 40), fill=(240, 238, 230))
                fit_text(d, (x + bw / 2, y0 + 112 - bh + 25), name, FONT_B, bw - 18, 24, INK)
                fit_text(d, (x + bw / 2, y0 + 112 - 18), f"{r.choice((20, 25, 50, 100))} RDS", FONT_B, bw - 14, 15, (240, 238, 230))
                x += bw + 3
            x += 8
        d.rectangle((0, y0 + 112, W, y0 + 118), fill=(140, 142, 145))          # shelf lip
        for k in range(10):
            px = 40 + k * 100
            d.rectangle((px, y0 + 104, px + 44, y0 + 118), fill=(250, 250, 250))
            fit_text(d, (px + 22, y0 + 111), f"${r.choice((18, 24, 29, 35, 42, 55))}", FONT_B, 40, 12, INK)
    save("AmmoWall", img, 170)


def case_felt():
    """Floor of the glass counter cases: dark felt with little price cards."""
    W, H = 1024, 256
    base = surface("rubber", (34, 30, 30), seed=5, size=256).resize((W, H))
    d = ImageDraw.Draw(base)
    r = random.Random(3)
    for k in range(8):
        x = 40 + k * 124
        d.rectangle((x, 200, x + 70, 236), fill=(250, 250, 246))
        fit_text(d, (x + 35, 211), f"${r.choice((450, 520, 600, 680, 750, 900))}", FONT_B, 64, 18, INK)
        fit_text(d, (x + 35, 228), "9MM", FONT_R, 60, 12, (80, 80, 80))
    save("CaseFelt", base, 230)


def lane_numbers():
    W, H = 1280, 256
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    for k in range(5):
        x0 = k * 256
        d.rectangle((x0 + 8, 8, x0 + 248, 248), fill=AMBER)
        d.rectangle((x0 + 20, 20, x0 + 236, 236), fill=INK)
        fit_text(d, (x0 + 128, 128), str(k + 1), FONT_B, 180, 170, (244, 242, 236))
    save("LaneNumbers", img, 120)


def range_sign():
    W, H = 1024, 192
    img = Image.new("RGB", (W, H), (190, 30, 26))
    d = ImageDraw.Draw(img)
    d.rectangle((6, 6, W - 7, H - 7), outline=(250, 250, 248), width=6)
    fit_text(d, (W / 2, 70), "RANGE", FONT_B, 700, 90, (250, 250, 248))
    fit_text(d, (W / 2, 150), "EYES AND EARS REQUIRED PAST THIS DOOR", FONT_B, 900, 34, (250, 250, 248))
    save("RangeSign", img, 140)


def rules_board():
    W, H = 512, 640
    img = Image.new("RGB", (W, H), (244, 242, 236))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 110), fill=(190, 30, 26))
    fit_text(d, (W / 2, 56), "RANGE RULES", FONT_B, W - 50, 64, (250, 250, 248))
    rules = ["1. TREAT EVERY GUN AS LOADED", "2. MUZZLE DOWNRANGE ALWAYS", "3. FINGER OFF THE TRIGGER",
             "4. NEVER PASS THE FIRING LINE", "5. CEASE FIRE MEANS STOP", "6. EYES AND EARS ON", "7. ASK STAFF FOR HELP"]
    for i, s in enumerate(rules):
        fit_text(d, (36, 150 + i * 62), s, FONT_B, W - 70, 30, INK, anchor="lm")
    d.rectangle((0, H - 60, W, H), fill=INK)
    fit_text(d, (W / 2, H - 30), "IRONWOOD ARMS RANGE", FONT_B, W - 60, 30, AMBER)
    save("RulesBoard", img, 200)


def door_decal():
    """Glass door sticker (Swing1Sign): hours + rules."""
    W, H = 256, 160
    img = Image.new("RGB", (W, H), (245, 245, 242))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 44), fill=INK)
    fit_text(d, (W / 2, 22), "OPEN 9 - 9", FONT_B, W - 30, 28, AMBER)
    fit_text(d, (W / 2, 72), "NO LOADED GUNS", FONT_B, W - 30, 22, INK)
    fit_text(d, (W / 2, 102), "PAST THIS DOOR", FONT_B, W - 30, 22, INK)
    fit_text(d, (W / 2, 138), "ALL VISITORS ON CAMERA", FONT_R, W - 30, 16, (80, 80, 80))
    save("Swing1Sign", img, 200)


def register():
    W, H = 256, 192
    img = Image.new("RGB", (W, H), (16, 18, 22))
    d = ImageDraw.Draw(img)
    d.rectangle((10, 10, W - 10, H - 10), fill=(20, 60, 90))
    d.rectangle((10, 10, W - 10, 44), fill=(30, 90, 130))
    fit_text(d, (W / 2, 27), "POINT OF SALE", FONT_B, W - 40, 22, (230, 240, 250))
    for i, s in enumerate(("CARBINE    2400", "RIFLE AMMO   60", "TOTAL     2460")):
        fit_text(d, (24, 70 + i * 34), s, FONT_M, W - 40, 22, (220, 236, 250), anchor="lm")
    save("Register", img, 60)


def cctv():
    W, H = 256, 160
    img = Image.new("RGB", (W, H), (10, 10, 12))
    d = ImageDraw.Draw(img)
    for i in range(4):
        x0, y0 = (i % 2) * 128 + 4, (i // 2) * 80 + 4
        d.rectangle((x0, y0, x0 + 120, y0 + 72), fill=(60 + i * 8, 66 + i * 6, 64))
        d.rectangle((x0 + 30, y0 + 30, x0 + 90, y0 + 72), fill=(40, 44, 42))
        fit_text(d, (x0 + 6, y0 + 10), f"CAM {i + 1}", FONT_M, 70, 12, (230, 230, 230), anchor="lm")
    save("Cctv", img, 60)


def pegboard():
    """Grey pegboard with a hole grid (tile = 2 x 2 ft)."""
    W = 256
    base = surface("paint", (150, 146, 138), seed=9, size=W)
    d = ImageDraw.Draw(base)
    step = W // 8
    for y in range(step // 2, W, step):
        for x in range(step // 2, W, step):
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(38, 36, 34))
    save("Pegboard", base, 200)


def slatwall():
    """Dark slat wall behind the counter (grooves every 3 in)."""
    W = 256
    base = surface("paint", (52, 54, 58), seed=12, size=W)
    d = ImageDraw.Draw(base)
    for y in range(0, W, W // 8):
        d.rectangle((0, y, W, y + 5), fill=(18, 18, 20))
        d.line((0, y + 6, W, y + 6), fill=(90, 92, 96), width=1)
    save("Slatwall", base, 150)


def acoustic():
    """Range side walls: quilted grey acoustic panels."""
    W = 256
    base = surface("rubber", (112, 114, 118), seed=14, size=W)
    d = ImageDraw.Draw(base)
    for y in range(0, W, W // 2):
        d.rectangle((0, y, W, y + 3), fill=(70, 72, 76))
    for x in range(0, W, W // 2):
        d.rectangle((x, 0, x + 3, W), fill=(70, 72, 76))
    for y in range(W // 8, W, W // 4):
        for x in range(W // 8, W, W // 4):
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(55, 57, 60))
    save("Acoustic", base.filter(ImageFilter.GaussianBlur(0.6)), 245)


def backstop():
    """Rubber backstop at the end of the lanes: black, scuffed, impact pocks."""
    W = 512
    base = surface("rubber", (26, 26, 27), seed=16, size=W)
    d = ImageDraw.Draw(base)
    r = random.Random(16)
    for _ in range(260):
        x, y = r.randint(0, W), r.randint(int(W * 0.25), int(W * 0.8))
        s = r.randint(2, 6)
        d.ellipse((x - s, y - s, x + s, y + s), fill=(12, 12, 12))
        d.arc((x - s - 2, y - s - 2, x + s + 2, y + s + 2), 200, 340, fill=(60, 60, 58), width=1)
    save("Backstop", base, 250)


def ceiling():
    W = 256
    base = surface("paint", (226, 224, 218), seed=20, size=W)
    arr = np.asarray(base, np.float32)
    rr = np.random.default_rng(3).random(arr.shape[:2]) < 0.08
    arr[rr] *= 0.9
    base = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(base)
    d.rectangle((0, 0, W, 5), fill=(200, 200, 198))
    d.rectangle((0, 0, 5, W), fill=(200, 200, 198))
    save("Ceiling", base, 240)


def floor_tiles():
    """Store floor: grey/charcoal 12 in vinyl tiles in a checker (tile = 2 x 2 tiles)."""
    W = 512
    c = np.asarray(tinted("Concrete034", (150, 150, 148), keep=0.15, size=W), np.float32)
    y, x = np.mgrid[0:W, 0:W]
    chk = ((x // (W // 2)) + (y // (W // 2))) % 2 == 1
    c[chk] *= 0.78
    joint = (x % (W // 2) < 3) | (y % (W // 2) < 3)
    c[joint] *= 0.7
    save("ShopFloor", Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)), 120)


def surfaces():
    save("ExtWall", stucco((176, 166, 148), seed=31, size=512, contrast=1.0), 220)
    save("ExtBand", tinted("Concrete031", (64, 66, 70), keep=0.25), scan("Concrete031", "Roughness"))
    save("InWall", tinted("PaintedPlaster017", (205, 203, 196), keep=0.2), scan("PaintedPlaster017", "Roughness"))
    save("RangeFloor", tinted("Concrete044D", (128, 128, 126), keep=0.4), scan("Concrete044D", "Roughness"))
    save("Asphalt", tinted("Concrete031", (52, 53, 55), keep=0.2, gain=0.9), 235)
    save("Walk", tinted("Concrete034", (160, 158, 152), keep=0.4), scan("Concrete034", "Roughness"))
    save("WoodTop", tinted("Planks023A", (110, 74, 46), keep=0.5), scan("Planks023A", "Roughness"))
    save("Block", surface("block", (110, 110, 108), seed=40, size=256), 235)
    paint("GunMetal", (36, 37, 40), strength=0.25)
    paint("Polymer", (26, 26, 28), strength=0.15)
    paint("Tan", (150, 128, 96), strength=0.2)
    paint("Steel", (150, 152, 156), grain="Metal029", strength=0.3)
    paint("CaseMetal", (60, 62, 66), strength=0.2)
    paint("Shutter", (120, 122, 124), grain="Metal029", strength=0.35)
    save("Stock", surface("wood", (122, 74, 40), seed=44, size=256), 120)
    save("Cardboard", surface("paint", (170, 136, 92), seed=46, size=256), 230)


if __name__ == "__main__":
    fetch()
    surfaces()
    shop_sign(); blade_sign(); target(); ammo_wall(); case_felt(); lane_numbers(); range_sign()
    rules_board(); door_decal(); register(); cctv(); pegboard(); slatwall(); acoustic(); backstop()
    ceiling(); floor_tiles()
    poster("PosterSafety", "SAFETY FIRST", ["Every gun is loaded", "Point it downrange", "Ask our staff"], (190, 30, 26), pic="mark", seed=1)
    poster("PosterStock", "NEW IN STOCK", ["CARBINE RIFLES", "Ammo by the box", "Ask at the counter"], (30, 34, 40), pic="rifle", seed=2)
    poster("PosterArmor", "BODY ARMOR", ["PLATE CARRIERS", "Ready to wear", "Fitted in store"], (60, 70, 50), pic="vest", seed=3)
    poster("PosterRange", "RANGE OPEN", ["5 LANES", "Hourly lane hire", "Eyes and ears on"], (232, 150, 30), pic="mark", seed=4)
