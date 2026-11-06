"""Texture sheets for the neighborhood buildings (houses, corner store, court, spawn plaza), PIL only.

  python3 tools/hood_textures.py   ->  art/blender/hood/tex/*.png

Gang looks are texture variants of the same meshes: house wall paint (PALETTES), the court
paint (CourtPaint<Gang>) and the graffiti tags (Tag<Gang>, with alpha). tools/build_city_map.py
picks a variant per placed building. Names and art are our own.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, grime, noise_tile, saver, scratches, text_c  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "blender", "hood", "tex")
save = saver(OUT)
r = random.Random(77)

# original gang names (no real-world gangs): red, yellow and green
GANGS = {"RedCrowns": (200, 30, 36), "Vipers": (240, 196, 30), "GroveKings": (40, 160, 70)}
TAG_WORDS = {"RedCrowns": "CROWNS", "Vipers": "VIPERS", "GroveKings": "KINGS"}
# wall paint per neighborhood (3 each) + neutral
PALETTES = {
    "Cream": (226, 214, 190), "Sand": (208, 186, 150), "Sky": (170, 196, 210),
    "Rose": (214, 150, 140), "Brick": (176, 96, 80), "Blush": (230, 190, 180),
    "Butter": (232, 210, 140), "Tan": (196, 160, 110), "Peach": (230, 180, 130),
    "Mint": (170, 206, 170), "Sage": (150, 170, 130), "Teal": (110, 170, 160),
}
IRON = (24, 24, 26)


def walls():
    for name, col in PALETTES.items():
        save(f"Wall{name}", grime(noise_tile(256, 256, col, 10, len(name)), 0.16, len(name) + 1), 230)


def bar_window():
    W, H = 384, 384
    im = Image.new("RGB", (W, H), (236, 232, 222))
    d = ImageDraw.Draw(im)
    d.rectangle([24, 24, W - 24, H - 40], fill=(60, 64, 70))
    lit = r.random() < 0.3
    d.rectangle([34, 34, W - 34, H - 50], fill=(240, 205, 150) if lit else (56, 64, 74))
    d.rectangle([34, 34, 120, H - 50], fill=(196, 180, 150))            # curtain
    d.polygon([(130, 34), (200, 34), (130, 140)], fill=(120, 134, 146))
    d.rectangle([W // 2 - 3, 34, W // 2 + 3, H - 50], fill=(200, 200, 200))
    for x in range(44, W - 34, 26):                                     # iron security bars
        d.rectangle([x, 24, x + 6, H - 40], fill=IRON)
    for y in (60, H // 2, H - 70):
        d.rectangle([24, y, W - 24, y + 6], fill=IRON)
    d.rectangle([14, H - 40, W - 14, H - 24], fill=(214, 210, 200))     # sill
    save("BarWindow", grime(im, 0.15, 3), 160)


def security_door():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (236, 232, 222))
    d = ImageDraw.Draw(im)
    d.rectangle([16, 16, W - 16, H], fill=(120, 70, 50))                # wooden door behind
    d.rectangle([24, 24, W - 24, H], fill=IRON)                         # iron screen door frame
    d.rectangle([34, 34, W - 34, H - 10], fill=(110, 64, 46))
    for x in range(40, W - 34, 14):
        d.line([(x, 34), (x, H - 10)], fill=IRON, width=4)
    for y in range(34, H, 60):
        d.line([(34, y), (W - 34, y)], fill=IRON, width=5)
    for k in range(4):                                                  # scroll work
        d.arc([60, 80 + k * 100, W - 60, 150 + k * 100], 0, 360, fill=IRON, width=5)
    d.rectangle([W - 60, 250, W - 44, 290], fill=(200, 170, 90))
    save("SecurityDoor", grime(im, 0.2, 4), 150)


def garage_door():
    W, H = 512, 384
    im = Image.new("RGB", (W, H), (226, 222, 210))
    d = ImageDraw.Draw(im)
    for j in range(4):
        for i in range(4):
            x0, y0 = 16 + i * 120, 16 + j * 90
            d.rectangle([x0, y0, x0 + 110, y0 + 80], outline=(190, 186, 176), width=6)
    d.rectangle([0, H - 12, W, H], fill=(120, 116, 110))
    save("GarageDoor", scratches(grime(im, 0.3, 5), 80, 6, (150, 150, 150), 60), 180)


def shingles():
    W = 256
    im = Image.new("RGB", (W, W), (70, 66, 64))
    d = ImageDraw.Draw(im)
    for j in range(10):
        y = j * W // 10
        off = r.randint(0, 20)
        for i in range(-1, 9):
            x = i * 32 + off
            c = r.randint(-14, 14)
            d.rectangle([x + 1, y + 1, x + 30, y + W // 10 - 2], fill=(78 + c, 72 + c, 68 + c))
        d.line([(0, y + W // 10 - 1), (W, y + W // 10 - 1)], fill=(36, 34, 33), width=3)
    save("Shingles", grime(im, 0.2, 7), 230)


def lawn():
    W = 256
    im = noise_tile(W, W, (110, 128, 60), 22, 8, 1.2)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(8):  # dry patches
        x, y, s = r.randint(0, W), r.randint(0, W), r.randint(16, 50)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(170, 150, 90, 110))
    save("Lawn", im.filter(ImageFilter.GaussianBlur(0.6)), 250)


def concrete():
    im = grime(noise_tile(256, 256, (172, 170, 164), 12, 9), 0.2, 10)
    d = ImageDraw.Draw(im)
    d.line([(0, 0), (256, 0)], fill=(120, 118, 112), width=3)
    d.line([(0, 0), (0, 256)], fill=(120, 118, 112), width=3)
    for _ in range(3):
        x, y = r.randint(0, 256), r.randint(0, 256)
        d.line([(x, y), (x + r.randint(-40, 40), y + r.randint(20, 60))], fill=(110, 108, 104), width=2)
    save("Concrete", im, 220)


def asphalt():
    im = noise_tile(512, 512, (54, 55, 57), 12, 11, 0.6)
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(6):
        x, y, s = r.randint(0, 512), r.randint(0, 512), r.randint(20, 70)
        d.ellipse([x - s, y - s // 2, x + s, y + s // 2], fill=(20, 20, 22, 70))
    save("Asphalt", im, 235)


def court(name, key):
    """Full court, 28 m x 15 m on a 1024 x 548 sheet, team colour key + centre circle."""
    W, H = 1024, 548
    base = (70, 72, 76) if key is None else tuple(int(c * 0.35 + 70 * 0.65) for c in key)
    im = noise_tile(W, H, (78, 80, 84), 10, 12, 0.6)
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([20, 20, W - 20, H - 20], fill=(*base, 255))
    line = (236, 236, 230, 255)
    d.rectangle([20, 20, W - 20, H - 20], outline=line, width=6)
    d.line([(W // 2, 20), (W // 2, H - 20)], fill=line, width=6)
    kc = key or (110, 110, 116)
    d.ellipse([W // 2 - 66, H // 2 - 66, W // 2 + 66, H // 2 + 66], fill=(*kc, 255), outline=line, width=6)
    for side in (0, 1):
        x0 = 20 if side == 0 else W - 20
        s = 1 if side == 0 else -1
        d.rectangle(sorted([x0, x0 + s * 210]) and [min(x0, x0 + s * 210), H // 2 - 90, max(x0, x0 + s * 210), H // 2 + 90], fill=(*kc, 255),
                    outline=line, width=6)
        d.arc([x0 + s * 210 - 66, H // 2 - 66, x0 + s * 210 + 66, H // 2 + 66], 90 if side else 270, 270 if side else 90, fill=line, width=6)
        cx = x0 + s * 58
        d.arc([cx - 248, H // 2 - 248, cx + 248, H // 2 + 248], -80 if side == 0 else 100, 80 if side == 0 else 260, fill=line, width=6)
        for y in (H // 2 - 246, H // 2 + 246):
            d.line([(x0, y), (x0 + s * 50, y)], fill=line, width=6)
    if key:
        name_ = {v: k for k, v in GANGS.items()}[key]
        fit_text(d, (W // 2, 70), TAG_WORDS[name_], FONT_B, 300, 46, (*key, 220))
    im = grime(im, 0.18, 13, streaks=False)
    save(name, im, 200)


def backboard():
    W, H = 256, 160
    im = Image.new("RGB", (W, H), (236, 236, 232))
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, W - 4, H - 4], outline=(200, 40, 30), width=8)
    d.rectangle([W // 2 - 50, H - 90, W // 2 + 50, H - 20], outline=(200, 40, 30), width=6)
    save("Backboard", scratches(grime(im, 0.2, 14, streaks=False), 60, 15, (120, 120, 120), 70), 120)


def tag(name, color, words, seed):
    """Graffiti tag with transparent background (RGBA): outlined bubble letters + drips + crown/arrow."""
    rr = random.Random(seed)
    W, H = 1024, 384
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(FONT_B, 150)
    x = 60
    for ch in words:
        y = 110 + rr.randint(-26, 26)
        ang = rr.uniform(-12, 12)
        layer = Image.new("RGBA", (220, 260), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.text((110, 130), ch, font=f, fill=(*color, 255), anchor="mm", stroke_width=12, stroke_fill=(20, 20, 20, 255))
        layer = layer.rotate(ang, resample=Image.BICUBIC)
        im.alpha_composite(layer, (x - 40, y - 80))
        w = d.textlength(ch, font=f)
        for _ in range(2):                                              # drips
            dx = x + rr.randint(0, int(w))
            d.line([(dx, y + 110), (dx, y + 110 + rr.randint(20, 70))], fill=(*color, 230), width=6)
        x += max(int(w * 0.82), 70)   # narrow letters (I) need room or the next one covers them
    d.line([(40, H - 40), (x + 30, H - 60)], fill=(*color, 255), width=10)      # underline swoosh
    d.polygon([(x + 30, H - 80), (x + 70, H - 62), (x + 30, H - 40)], fill=(*color, 255))
    im = im.resize((W, H))
    im.save(os.path.join(OUT, f"{name}_Color.png"))
    print("wrote", name)


def store_front():
    W, H = 1024, 384
    im = Image.new("RGB", (W, H), (40, 42, 46))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], fill=(200, 196, 186))
    for k, x0 in enumerate((30, 360, 690)):
        d.rectangle([x0, 40, x0 + 300, H - 30], fill=(60, 64, 70))
        d.rectangle([x0 + 8, 48, x0 + 292, H - 38], fill=(230, 200, 140))      # lit shop inside
        for j in range(4):
            y = 110 + j * 52
            d.rectangle([x0 + 8, y, x0 + 292, y + 6], fill=(160, 120, 70))
            for i in range(12):
                c = r.choice(((200, 50, 40), (40, 100, 190), (230, 190, 40), (60, 150, 70), (240, 240, 240), (120, 60, 30)))
                d.rectangle([x0 + 14 + i * 23, y - 30, x0 + 30 + i * 23, y], fill=c)
        poster = [("SODA", (30, 80, 170)), ("SNACKS", (200, 40, 40)), ("ATM", (30, 130, 80))][k]
        d.rectangle([x0 + 20, 60, x0 + 150, 150], fill=poster[1])
        fit_text(d, (x0 + 85, 105), poster[0], FONT_B, 120, 40, (255, 255, 255))
        for x in range(x0 + 6, x0 + 300, 22):                                  # bars
            d.rectangle([x, 40, x + 6, H - 30], fill=IRON)
        for y in (80, 200, 320):
            d.rectangle([x0, y, x0 + 300, y + 6], fill=IRON)
    save("StoreFront", grime(im, 0.18, 16), 120)


def store_sign():
    W, H = 2048, 256
    im = Image.new("RGB", (W, H), (190, 30, 34))
    d = ImageDraw.Draw(im)
    d.rectangle([0, H - 24, W, H], fill=(250, 210, 60))
    fit_text(d, (W / 2, H / 2 - 8), "SUNNY'S MARKET  ·  GROCERY  ·  SNACKS  ·  DRINKS", FONT_B, W - 80, 150, (255, 244, 220))
    save("StoreSign", grime(im, 0.12, 17, streaks=False), 90)


def store_door():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), IRON)
    d = ImageDraw.Draw(im)
    d.rectangle([14, 14, W - 14, H - 14], fill=(220, 190, 130))
    for x in range(20, W - 14, 18):
        d.rectangle([x, 14, x + 5, H - 14], fill=IRON)
    d.rectangle([30, 120, W - 30, 200], fill=(240, 240, 236))
    text_c(d, (W // 2, 145), "OPEN", font(FONT_B, 30), (200, 30, 30))
    text_c(d, (W // 2, 180), "7AM - 2AM", font(FONT_B, 20), (30, 30, 30))
    save("StoreDoor", grime(im, 0.15, 18), 140)


def plaza_pave():
    W = 512
    im = Image.new("RGB", (W, W), (196, 186, 170))
    d = ImageDraw.Draw(im)
    for j in range(8):
        for i in range(8):
            c = r.randint(-12, 10)
            tone = (196 + c, 186 + c, 170 + c) if (i + j) % 4 else (170 + c, 120 + c, 96 + c)
            d.rectangle([i * 64 + 2, j * 64 + 2, i * 64 + 61, j * 64 + 61], fill=tone)
    save("PlazaPave", grime(im, 0.12, 19, streaks=False), 210)


def welcome_sign():
    W, H = 1536, 384
    im = Image.new("RGB", (W, H), (34, 40, 46))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], outline=(242, 160, 32), width=14)
    fit_text(d, (W / 2, 130), "WELCOME TO", FONT_B, W - 200, 90, (236, 232, 222))
    fit_text(d, (W / 2, 260), "TULEVO", FONT_B, W - 200, 170, (242, 160, 32))
    save("WelcomeSign", im, 90)


def shelter_ad():
    W, H = 384, 640
    im = Image.new("RGB", (W, H), (20, 110, 160))
    d = ImageDraw.Draw(im)
    d.ellipse([60, 80, 324, 344], fill=(250, 200, 60))
    fit_text(d, (W / 2, 420), "COAST FM", FONT_B, W - 40, 70, (255, 255, 255))
    fit_text(d, (W / 2, 490), "98.4  ·  ALL HITS", FONT_B, W - 40, 34, (255, 230, 150))
    fit_text(d, (W / 2, 580), "tune in, tulevo", FONT_R, W - 60, 30, (220, 240, 255))
    save("ShelterAd", im, 30)


def route_map():
    W, H = 512, 512
    im = Image.new("RGB", (W, H), (236, 234, 226))
    d = ImageDraw.Draw(im)
    fit_text(d, (W / 2, 40), "TULEVO CITY MAP", FONT_B, W - 40, 34, (30, 30, 30))
    for x in (130, 256, 382):
        d.line([(x, 80), (x, 480)], fill=(150, 150, 150), width=12)
    for y in (140, 290, 440):
        d.line([(30, y), (480, y)], fill=(150, 150, 150), width=12)
    for (x, y, c) in ((420, 120, (240, 196, 30)), (90, 460, (40, 160, 70)), (420, 460, (200, 30, 36))):
        d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=c)
    d.ellipse([244, 200, 268, 224], fill=(30, 120, 220))
    text_c(d, (256, 240), "YOU ARE HERE", font(FONT_B, 16), (30, 120, 220))
    save("RouteMap", im, 120)


def water():
    W = 256
    im = Image.new("RGB", (W, W), (50, 140, 180))
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(80):
        x, y, s = r.randint(0, W), r.randint(0, W), r.randint(8, 30)
        d.arc([x - s, y - s // 2, x + s, y + s // 2], r.randint(0, 180), r.randint(180, 360), fill=(200, 240, 255, 130), width=2)
    save("Water", im.filter(ImageFilter.GaussianBlur(0.7)), 10)


def chain_link():
    """Chain-link fence mesh with alpha (holes see-through)."""
    W = 128
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(-W, W * 2, 16):
        d.line([(k, 0), (k + W, W)], fill=(170, 172, 176, 255), width=2)
        d.line([(k, W), (k + W, 0)], fill=(170, 172, 176, 255), width=2)
    im.save(os.path.join(OUT, "ChainLink_Color.png"))
    print("wrote ChainLink")


walls()
for fn in (bar_window, security_door, garage_door, shingles, lawn, concrete, asphalt, backboard, store_front, store_sign,
           store_door, plaza_pave, welcome_sign, shelter_ad, route_map, water, chain_link):
    fn()
court("CourtPaint", None)
for g, c in GANGS.items():
    court(f"CourtPaint{g}", c)
for i, (g, c) in enumerate(GANGS.items()):
    tag(f"Tag{g}", c, TAG_WORDS[g], i + 1)
tag("Tag", (60, 120, 220), "TULEVO", 4)
