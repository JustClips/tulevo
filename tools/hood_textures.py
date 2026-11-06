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
from tex_kit import FONT_B, FONT_R, fit_text, font, glass_set, grime, noise_tile, saver, scratches, stucco, text_c  # noqa: E402

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
        save(f"Wall{name}", grime(stucco(col, len(name)), 0.12, len(name) + 1), 230)
    glass_set(save, seed=950)


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
    """Darker, realistic mowed lawn: soft colour drift, thousands of tiny blades, a few clover
    and dry tufts. Tileable (blades wrap at the edges); no big blotches."""
    import numpy as np
    from tex_kit import _wrap_noise
    W = 512
    big = np.asarray(_wrap_noise(W, W, 96, 31, 28), np.float32) / 255 - 0.5
    mid = np.asarray(_wrap_noise(W, W, 16, 32, 4), np.float32) / 255 - 0.5
    base = np.array((62, 84, 36), np.float32)
    dry = np.array((96, 98, 52), np.float32)
    t = np.clip(big * 1.1 + 0.25, 0, 1)[..., None] * 0.35
    img = base * (1 - t) + dry * t + (mid * 14)[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    rr = random.Random(505)
    for _ in range(26000):
        x, y = rr.uniform(0, W), rr.uniform(0, W)
        ln, ang = rr.uniform(2, 6), rr.uniform(-0.9, 0.9) - math.pi / 2
        dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
        g = rr.random()
        col = ((40, 58, 22, 150) if g < 0.35 else (88, 112, 48, 140) if g < 0.8 else (118, 132, 66, 120))
        for ox in (-W, 0, W):
            for oy in (-W, 0, W):
                if -8 < x + ox < W + 8 and -8 < y + oy < W + 8:
                    d.line([(x + ox, y + oy), (x + ox + dx, y + oy + dy)], fill=col, width=1)
    for _ in range(60):                      # clover / weeds
        x, y = rr.uniform(8, W - 8), rr.uniform(8, W - 8)
        for k in range(3):
            a = k * 2.1 + rr.random()
            d.ellipse([x + math.cos(a) * 2 - 2, y + math.sin(a) * 2 - 2, x + math.cos(a) * 2 + 2, y + math.sin(a) * 2 + 2],
                      fill=(70, 100, 44, 200))
    save("Lawn", im.filter(ImageFilter.GaussianBlur(0.35)), 245)


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
    """Worn asphalt: grain + soft tonal drift, a few small oil drips (no big dark blobs)."""
    im = noise_tile(512, 512, (58, 59, 61), 12, 11, 0.6)
    d = ImageDraw.Draw(im, "RGBA")
    rr = random.Random(611)
    for _ in range(5):
        x, y = rr.randint(40, 472), rr.randint(40, 472)
        for k in range(6):
            s = rr.randint(3, 9)
            ox, oy = rr.randint(-12, 12), rr.randint(-12, 12)
            d.ellipse([x + ox - s, y + oy - s, x + ox + s, y + oy + s], fill=(30, 30, 32, 40))
    for _ in range(2500):                         # loose aggregate specks
        x, y = rr.randint(0, 511), rr.randint(0, 511)
        c = rr.choice(((92, 92, 90, 140), (36, 36, 38, 140)))
        d.point((x, y), fill=c)
    save("Asphalt", im.filter(ImageFilter.GaussianBlur(0.4)), 235)


def clay_tile():
    """Spanish barrel roof tiles, rows of terracotta half-pipes (tile 2 m)."""
    W = 256
    im = Image.new("RGB", (W, W), (120, 52, 32))
    d = ImageDraw.Draw(im)
    rr = random.Random(712)
    rows, cols = 8, 8
    for j in range(rows):
        y0 = j * W // rows
        for i in range(cols):
            x0 = i * W // cols
            c = rr.randint(-18, 18)
            base = (170 + c, 82 + c // 2, 48 + c // 3)
            for k in range(W // cols):          # rounded shading across the tile
                t = math.sin(math.pi * (k + 0.5) / (W // cols))
                col = tuple(int(v * (0.55 + 0.5 * t)) for v in base)
                d.line([(x0 + k, y0), (x0 + k, y0 + W // rows - 3)], fill=col)
            d.line([(x0, y0 + W // rows - 3), (x0 + W // cols, y0 + W // rows - 3)], fill=(70, 30, 20), width=3)
    save("ClayTile", grime(im, 0.18, 12), 200)


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


# ---------------------------------------------------------------- Sunny's Market interior (no alcohol, no tobacco, no lotto)
DRINKS = [((220, 40, 40), "COLA"), ((40, 120, 220), "WATER"), ((250, 160, 30), "OJ"), ((60, 180, 80), "LIME"),
          ((240, 220, 60), "LEMON"), ((150, 60, 180), "GRAPE"), ((30, 30, 30), "ZAP"), ((240, 240, 240), "MILK"),
          ((230, 110, 160), "BERRY"), ((90, 200, 210), "ICE TEA")]
SNACKS = [((230, 60, 40), "CHIPS"), ((250, 200, 40), "CORN"), ((60, 110, 210), "PRETZEL"), ((140, 80, 40), "COOKIE"),
          ((80, 170, 70), "NUTS"), ((240, 140, 40), "CHEEZ"), ((200, 40, 120), "CANDY"), ((120, 60, 30), "CHOCO")]


def shop_floor():
    W = 256
    im = Image.new("RGB", (W, W))
    d = ImageDraw.Draw(im)
    for i in range(4):
        for j in range(4):
            c = (226, 224, 216) if (i + j) % 2 else (150, 154, 158)
            c = tuple(max(0, min(255, v + r.randint(-6, 6))) for v in c)
            d.rectangle([i * 64, j * 64, i * 64 + 63, j * 64 + 63], fill=c)
            d.line([(i * 64, j * 64), (i * 64 + 63, j * 64)], fill=(120, 120, 118), width=1)
            d.line([(i * 64, j * 64), (i * 64, j * 64 + 63)], fill=(120, 120, 118), width=1)
    save("ShopFloor", grime(scratches(im, 60, 41, (90, 90, 90), 40), 0.12, 42, streaks=False), 70)


def ceiling():
    W = 256
    im = noise_tile(W, W, (232, 230, 224), 6, 43)
    d = ImageDraw.Draw(im)
    for k in range(0, W, 64):
        d.line([(k, 0), (k, W)], fill=(190, 190, 186), width=4)
        d.line([(0, k), (W, k)], fill=(190, 190, 186), width=4)
    for _ in range(40):
        x, y = r.randint(0, W), r.randint(0, W)
        d.point((x, y), fill=(160, 158, 150))
    save("Ceiling", im, 240)


def bottle(d, x, y, w, h, col, label):
    d.rounded_rectangle([x, y + h * 0.18, x + w, y + h], 4, fill=col)
    d.rectangle([x + w * 0.3, y, x + w * 0.7, y + h * 0.2], fill=col)
    d.rectangle([x + w * 0.28, y - 4, x + w * 0.72, y + 3], fill=(240, 240, 240))
    d.rectangle([x + 1, y + h * 0.45, x + w - 1, y + h * 0.72], fill=(250, 250, 245))
    fit_text(d, (x + w / 2, y + h * 0.585), label, FONT_B, w - 2, 10, col)


def fridge_doors():
    """3 glass doors of a drinks cooler, 3.0 m x 2.2 m, cold-lit shelves of sodas, water, juice, milk."""
    W, H = 768, 576
    im = Image.new("RGB", (W, H), (200, 202, 206))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 60], fill=(30, 110, 200))
    fit_text(d, (W / 2, 30), "COLD DRINKS", FONT_B, W - 60, 40, (255, 255, 255))
    for k in range(3):
        x0 = 10 + k * 252
        d.rectangle([x0, 70, x0 + 238, H - 10], fill=(70, 74, 80))
        d.rectangle([x0 + 8, 78, x0 + 230, H - 18], fill=(214, 232, 244))
        for row in range(5):
            y = 100 + row * 92
            d.rectangle([x0 + 8, y + 74, x0 + 230, y + 80], fill=(150, 156, 160))
            for i in range(7):
                col, lab = DRINKS[(k * 11 + row * 3 + i) % len(DRINKS)]
                bottle(d, x0 + 14 + i * 31, y, 26, 72, col, lab)
        d.rectangle([x0 + 210, 250, x0 + 222, 400], fill=(200, 200, 204))                     # handle
        d.polygon([(x0 + 20, 78), (x0 + 90, 78), (x0 + 20, 260)], fill=(255, 255, 255))           # glare
    im = Image.blend(im, Image.new("RGB", (W, H), (210, 230, 245)), 0.12)
    save("FridgeDoors", im, 30)


def bag(d, x, y, w, h, col, label):
    d.polygon([(x, y + 6), (x + w, y), (x + w - 2, y + h), (x + 2, y + h - 4)], fill=col)
    d.ellipse([x + w * 0.2, y + h * 0.25, x + w * 0.8, y + h * 0.65], fill=(250, 240, 200))
    fit_text(d, (x + w / 2, y + h * 0.45), label, FONT_B, w * 0.6, 11, col)


def shelf_goods(name, seed):
    """One side of a 3 m x 1.6 m gondola shelf: 4 shelves of snack bags, cereal boxes and cans."""
    rr = random.Random(seed)
    W, H = 768, 410
    im = Image.new("RGB", (W, H), (236, 236, 232))
    d = ImageDraw.Draw(im)
    for row in range(4):
        y = 10 + row * 100
        d.rectangle([0, y + 88, W, y + 98], fill=(200, 200, 196))
        d.rectangle([0, y + 90, W, y + 94], fill=(230, 60, 50) if row % 2 else (40, 90, 180))     # price strip
        x = 6
        kind = rr.choice(("bag", "box", "can"))
        while x < W - 40:
            col, lab = rr.choice(SNACKS)
            if kind == "bag":
                bag(d, x, y + 10, 52, 76, col, lab); x += 56
            elif kind == "box":
                d.rectangle([x, y + 4, x + 44, y + 86], fill=col)
                d.rectangle([x + 4, y + 30, x + 40, y + 60], fill=(250, 245, 230))
                fit_text(d, (x + 22, y + 45), lab, FONT_B, 34, 10, col); x += 48
            else:
                c2 = rr.choice(((200, 60, 40), (60, 140, 60), (230, 180, 40), (120, 120, 130)))
                for k in range(2):
                    d.rounded_rectangle([x, y + 46 - k * 40, x + 30, y + 86 - k * 40], 3, fill=c2)
                    d.rectangle([x, y + 58 - k * 40, x + 30, y + 72 - k * 40], fill=(245, 240, 230))
                x += 33
    save(name, grime(im, 0.06, seed, streaks=False), 160)


def candy_rack():
    W, H = 512, 512
    im = Image.new("RGB", (W, H), (60, 60, 64))
    d = ImageDraw.Draw(im)
    for row in range(6):
        y = 10 + row * 84
        for i in range(10):
            col, lab = SNACKS[(row * 3 + i) % len(SNACKS)]
            d.rectangle([8 + i * 50, y, 50 + i * 50, y + 70], fill=col)
            d.rectangle([12 + i * 50, y + 22, 46 + i * 50, y + 46], fill=(250, 246, 236))
            fit_text(d, (29 + i * 50, y + 34), lab, FONT_B, 32, 9, col)
        d.rectangle([0, y + 72, W, y + 80], fill=(150, 150, 154))
    save("CandyRack", im, 160)


def faces():
    # ICE box front, register screen, coffee machine, ATM, freezer lid, news box, A/C grille, posters
    W, H = 512, 256
    im = Image.new("RGB", (W, H), (245, 246, 248))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 90], fill=(30, 110, 200))
    fit_text(d, (W / 2, 46), "ICE", FONT_B, 300, 70, (255, 255, 255))
    d.rectangle([20, 120, W - 20, H - 20], outline=(180, 184, 190), width=6)
    d.rectangle([W / 2 - 60, 140, W / 2 + 60, 160], fill=(150, 150, 156))
    save("IceFront", grime(im, 0.12, 44), 120)
    im = Image.new("RGB", (256, 256), (40, 42, 46))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, 236, 130], fill=(30, 60, 40))
    fit_text(d, (128, 60), "TOTAL", FONT_B, 180, 30, (120, 255, 140))
    fit_text(d, (128, 100), "$ 4.29", FONT_B, 180, 34, (120, 255, 140))
    for i in range(4):
        for j in range(3):
            d.rectangle([40 + j * 60, 145 + i * 26, 88 + j * 60, 165 + i * 26], fill=(200, 200, 204))
    save("Register", im, 80)
    im = Image.new("RGB", (256, 384), (40, 40, 44))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 256, 80], fill=(120, 60, 30))
    fit_text(d, (128, 40), "FRESH COFFEE", FONT_B, 230, 30, (255, 236, 200))
    for k in range(3):
        d.rectangle([20 + k * 76, 110, 80 + k * 76, 150], fill=(200, 200, 200))
        d.rectangle([30 + k * 76, 230, 70 + k * 76, 300], fill=(60, 30, 20))
    d.rectangle([10, 320, 246, 330], fill=(160, 160, 164))
    save("Coffee", im, 60)
    im = Image.new("RGB", (256, 384), (60, 64, 70))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 256, 60], fill=(30, 130, 80))
    fit_text(d, (128, 30), "ATM", FONT_B, 200, 40, (255, 255, 255))
    d.rectangle([40, 80, 216, 190], fill=(40, 90, 140))
    fit_text(d, (128, 135), "INSERT CARD", FONT_B, 160, 20, (220, 240, 255))
    for i in range(4):
        for j in range(3):
            d.rectangle([60 + j * 46, 210 + i * 30, 96 + j * 46, 232 + i * 30], fill=(190, 190, 196))
    d.rectangle([60, 340, 196, 352], fill=(20, 20, 20))
    save("AtmFace", im, 60)
    im = Image.new("RGB", (512, 256), (230, 238, 246))
    d = ImageDraw.Draw(im)
    for i in range(14):
        col = rr_c(i)
        d.rounded_rectangle([12 + i * 35, 40 + (i % 3) * 50, 42 + i * 35, 100 + (i % 3) * 50], 6, fill=col)
    d.rectangle([0, 0, 512, 30], fill=(60, 140, 220))
    fit_text(d, (256, 15), "ICE CREAM", FONT_B, 300, 22, (255, 255, 255))
    save("FreezerTop", Image.blend(im, Image.new("RGB", im.size, (220, 236, 250)), 0.2), 30)
    for name, bg, words, sub in (("PosterSoda", (210, 40, 40), "SODA", "2 FOR $3"), ("PosterSnack", (250, 180, 30), "SNACKS", "DEALS INSIDE"),
                                 ("PosterCoffee", (110, 60, 30), "HOT COFFEE", "$1.29 ANY SIZE"), ("PosterOpen", (30, 110, 200), "OPEN", "7 DAYS")):
        im = Image.new("RGB", (256, 320), bg)
        d = ImageDraw.Draw(im)
        fit_text(d, (128, 120), words, FONT_B, 230, 70, (255, 255, 255))
        fit_text(d, (128, 230), sub, FONT_B, 220, 30, (255, 250, 220))
        d.rectangle([6, 6, 250, 314], outline=(255, 255, 255), width=6)
        save(name, im, 120)
    im = Image.new("RGB", (256, 256), (200, 202, 204))
    d = ImageDraw.Draw(im)
    for y in range(12, 256, 14):
        d.rectangle([12, y, 244, y + 6], fill=(120, 124, 128))
    save("AcGrille", grime(im, 0.2, 45), 150)
    im = Image.new("RGB", (256, 256), (200, 40, 40))
    d = ImageDraw.Draw(im)
    d.rectangle([30, 30, 226, 140], fill=(40, 44, 50))
    d.rectangle([40, 40, 216, 130], fill=(230, 226, 214))
    fit_text(d, (128, 70), "DAILY", FONT_B, 160, 28, (30, 30, 30))
    fit_text(d, (128, 105), "NEWS", FONT_B, 160, 28, (30, 30, 30))
    d.rectangle([160, 170, 210, 220], fill=(160, 160, 164))
    save("NewsFace", grime(im, 0.2, 46), 150)


def rr_c(i):
    return ((240, 120, 160), (250, 220, 120), (140, 90, 60), (120, 200, 230), (250, 250, 240), (160, 220, 120))[i % 6]


walls()
for fn in (shop_floor, ceiling, fridge_doors, candy_rack, faces, bar_window, security_door, garage_door, shingles, clay_tile, lawn, concrete, asphalt, backboard, store_front, store_sign,
           store_door, plaza_pave, welcome_sign, shelter_ad, route_map, water, chain_link):
    fn()
shelf_goods("ShelfGoodsA", 61)
shelf_goods("ShelfGoodsB", 62)
court("CourtPaint", None)
for g, c in GANGS.items():
    court(f"CourtPaint{g}", c)
for i, (g, c) in enumerate(GANGS.items()):
    tag(f"Tag{g}", c, TAG_WORDS[g], i + 1)
tag("Tag", (60, 120, 220), "TULEVO", 4)
