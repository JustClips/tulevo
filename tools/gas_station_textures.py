"""Draws the detailed texture sheets for the Kestrel gas station (PIL, no Blender needed).

  python3 tools/gas_station_textures.py

Writes art/blender/gas_station/tex/*.png. build_gas_station.py maps them onto the pump faces,
price sign, forecourt, shop and canopy, so the printed details (screens, keypads, grade
buttons, stickers, prices, posters, stains) live in the texture instead of floating geometry.
Each sheet has a _Color and a _Roughness map. Brand: KESTREL (ours), teal / white / amber.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "blender", "gas_station", "tex")
os.makedirs(OUT, exist_ok=True)

TEAL = (8, 92, 98)
TEAL_D = (5, 62, 66)
AMBER = (250, 160, 28)
WHITE = (236, 237, 234)
BLACK = (14, 14, 16)
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
rng = random.Random(7)


def font(path, size):
    return ImageFont.truetype(path, size)


def text_c(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def wing(d, cx, cy, s, fill):
    """Brand mark: three swept feathers (same shape as the 3D one)."""
    for k in range(3):
        w = s * (1 - k * 0.22)
        off = k * s * 0.26
        pts = [(-w * 0.5, off), (w * 0.5, -w * 0.30 + off), (w * 0.5, -w * 0.12 + off), (-w * 0.25, off + w * 0.12)]
        d.polygon([(cx + x, cy + y) for x, y in pts], fill=fill)


def grime(img, amount=0.10, seed=1, streaks=True):
    """Soft dirt: low-frequency blotches, darker toward the bottom, vertical drip streaks."""
    r = random.Random(seed)
    w, h = img.size
    noise = Image.new("L", (w // 16 + 1, h // 16 + 1))
    noise.putdata([r.randint(0, 255) for _ in range(noise.width * noise.height)])
    noise = noise.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w / 60))
    grad = Image.linear_gradient("L").resize((w, h))
    mask = Image.blend(noise, grad, 0.45)
    if streaks:
        sd = ImageDraw.Draw(mask)
        for _ in range(int(w / 12)):
            x = r.randint(0, w)
            y0 = r.randint(0, h // 2)
            sd.line([(x, y0), (x + r.randint(-3, 3), y0 + r.randint(h // 8, h // 2))], fill=255, width=r.randint(1, 3))
        mask = mask.filter(ImageFilter.GaussianBlur(1.5))
    dark = Image.new("RGB", (w, h), (40, 36, 30))
    mask = mask.point(lambda v: int(max(0, v - 128) * 2 * amount))
    return Image.composite(dark, img, mask)


def scratches(img, n=80, seed=2, color=(250, 250, 250), alpha=50):
    r = random.Random(seed)
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    w, h = img.size
    for _ in range(n):
        x, y = r.randint(0, w), r.randint(0, h)
        a = r.uniform(0, math.pi)
        L = r.randint(6, 40)
        d.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], fill=(*color, alpha), width=1)
    return Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")


def save(name, color, rough):
    color.save(os.path.join(OUT, f"{name}_Color.png"))
    rough.convert("L").convert("RGB").save(os.path.join(OUT, f"{name}_Roughness.png"))
    print("wrote", name)


# ------------------------------------------------------------------ pump face (512 x 1024)
def pump_face():
    W, H = 512, 1024
    im = Image.new("RGB", (W, H), WHITE)
    rough = Image.new("L", (W, H), 90)
    d, rd = ImageDraw.Draw(im), ImageDraw.Draw(rough)
    # header band: teal with brand
    d.rectangle([0, 0, W, 170], fill=TEAL)
    d.rectangle([0, 160, W, 170], fill=AMBER)
    wing(d, 92, 86, 90, AMBER)
    text_c(d, (300, 86), "KESTREL", font(FONT_B, 66), WHITE)
    # bezel round the screen + card reader area
    d.rectangle([40, 210, W - 40, 600], fill=(40, 44, 48))
    d.rectangle([60, 230, W - 60, 420], fill=(10, 36, 46))           # screen
    rd.rectangle([60, 230, W - 60, 420], fill=20)
    f_s, f_b = font(FONT_R, 22), font(FONT_M, 46)
    text_c(d, (84, 262), "SALE", f_s, (120, 200, 220), "lm")
    text_c(d, (W - 84, 262), "$", f_s, (120, 200, 220), "rm")
    text_c(d, (W - 84, 302), "0.00", f_b, (150, 235, 250), "rm")
    text_c(d, (84, 352), "GALLONS", f_s, (120, 200, 220), "lm")
    text_c(d, (W - 84, 382), "0.000", f_b, (150, 235, 250), "rm")
    # card reader + receipt slot
    d.rectangle([70, 440, 230, 520], fill=(22, 22, 24))
    d.rectangle([90, 470, 210, 480], fill=(70, 200, 90))
    text_c(d, (150, 500), "INSERT CARD", font(FONT_R, 14), (200, 200, 200))
    d.rectangle([70, 535, 230, 548], fill=(5, 5, 6))
    text_c(d, (150, 566), "RECEIPT", font(FONT_R, 13), (180, 180, 180))
    # keypad 4x3
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "X", "0", "OK"]
    f_k = font(FONT_B, 22)
    for i, k in enumerate(keys):
        cx, cy = 290 + (i % 3) * 52, 455 + (i // 3) * 36
        col = (200, 60, 50) if k == "X" else (60, 170, 80) if k == "OK" else (190, 192, 195)
        d.rectangle([cx - 22, cy - 15, cx + 22, cy + 15], fill=col)
        text_c(d, (cx, cy), k, f_k, BLACK if k not in ("X", "OK") else WHITE)
    # grade buttons
    grades = [("87", "REGULAR", (40, 150, 70)), ("89", "PLUS", (30, 110, 190)), ("93", "PREMIUM", (190, 50, 50))]
    for i, (oct_, name, col) in enumerate(grades):
        x0 = 40 + i * 150
        d.rectangle([x0, 630, x0 + 132, 760], fill=col)
        d.rectangle([x0 + 8, 638, x0 + 124, 752], outline=WHITE, width=3)
        text_c(d, (x0 + 66, 680), oct_, font(FONT_B, 54), WHITE)
        text_c(d, (x0 + 66, 730), name, font(FONT_B, 18), WHITE)
        text_c(d, (x0 + 66, 778), "OCTANE", font(FONT_R, 13), (90, 90, 90))
    # stickers
    d.rectangle([40, 810, 240, 900], fill=(250, 210, 40))
    text_c(d, (140, 838), "NO SMOKING", font(FONT_B, 22), BLACK)
    text_c(d, (140, 872), "TURN OFF ENGINE", font(FONT_B, 17), BLACK)
    d.rectangle([272, 810, 472, 900], fill=WHITE, outline=(200, 40, 40), width=6)
    text_c(d, (372, 840), "PAY AT PUMP", font(FONT_B, 21), (200, 40, 40))
    text_c(d, (372, 872), "OR PAY INSIDE", font(FONT_R, 17), BLACK)
    # kick plate
    d.rectangle([0, 930, W, H], fill=(28, 30, 32))
    rd.rectangle([0, 930, W, H], fill=170)
    for x in range(0, W, 24):
        d.line([(x, 940), (x + 14, H)], fill=(40, 42, 44), width=4)
    im = scratches(grime(im, 0.25, 3), 120, 4)
    save("PumpFace", im, rough)


# ------------------------------------------------------------------ pump side (256 x 1024)
def pump_side():
    W, H = 256, 1024
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 170], fill=TEAL)
    d.rectangle([0, 160, W, 170], fill=AMBER)
    for i, col in enumerate(((40, 150, 70), (30, 110, 190), (190, 50, 50))):
        d.rectangle([30, 260 + i * 60, W - 30, 300 + i * 60], fill=col)
    text_c(d, (W // 2, 520), "UNLEADED", font(FONT_B, 24), (60, 60, 60))
    text_c(d, (W // 2, 552), "10% ETHANOL", font(FONT_R, 16), (90, 90, 90))
    d.rectangle([60, 640, W - 60, 700], outline=(120, 120, 120), width=3)
    text_c(d, (W // 2, 670), "PUMP 1-4", font(FONT_B, 18), (90, 90, 90))
    d.rectangle([0, 930, W, H], fill=(28, 30, 32))
    im = scratches(grime(im, 0.25, 5), 60, 6)
    save("PumpSide", im, Image.new("L", (W, H), 95))


# ------------------------------------------------------------------ price sign face (512 x 1024)
def price_sign():
    W, H = 512, 1024
    im = Image.new("RGB", (W, H), TEAL)
    rough = Image.new("L", (W, H), 80)
    d = ImageDraw.Draw(im)
    # brand panel (top 40%)
    d.rectangle([14, 14, W - 14, 400], outline=WHITE, width=6)
    wing(d, W // 2, 150, 200, AMBER)
    text_c(d, (W // 2, 300), "KESTREL", font(FONT_B, 92), WHITE)
    d.rectangle([60, 360, W - 60, 368], fill=AMBER)
    # price board (black, lit digits)
    d.rectangle([14, 420, W - 14, 900], fill=(8, 8, 9))
    rows = [("REGULAR", "3.49"), ("PLUS", "3.79"), ("PREMIUM", "4.09"), ("DIESEL", "4.29")]
    for i, (g, p) in enumerate(rows):
        y = 480 + i * 108
        text_c(d, (40, y), g, font(FONT_B, 30), WHITE, "lm")
        text_c(d, (W - 70, y), p, font(FONT_M, 76), AMBER, "rm")
        text_c(d, (W - 40, y - 18), "9", font(FONT_M, 34), AMBER, "rm")
        d.line([(30, y + 52), (W - 30, y + 52)], fill=(40, 40, 42), width=2)
    # footer: services
    d.rectangle([14, 916, W - 14, H - 14], fill=WHITE)
    text_c(d, (W // 2, 966), "MART  ·  ATM  ·  AIR", font(FONT_B, 34), TEAL_D)
    im = grime(im, 0.15, 8, streaks=True)
    save("PriceSign", im, rough)


# ------------------------------------------------------------------ forecourt concrete (1024, tiles every 6 m)
def forecourt():
    W = 1024
    r = random.Random(11)
    base = Image.new("L", (W // 8, W // 8))
    base.putdata([r.randint(0, 255) for _ in range(base.width * base.height)])
    base = base.resize((W, W), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    fine = Image.effect_noise((W, W), 40).filter(ImageFilter.GaussianBlur(0.6))
    lum = Image.blend(base, fine, 0.35)
    im = Image.merge("RGB", [lum.point(lambda v, o=o: int(118 + o + (v - 128) * 0.18)) for o in (6, 4, 0)])
    rough = Image.new("L", (W, W), 215)
    d, rd = ImageDraw.Draw(im, "RGBA"), ImageDraw.Draw(rough)
    # saw-cut joints on the tile edge + a hairline crack or two
    for p in (0, W - 2):
        d.line([(p, 0), (p, W)], fill=(60, 58, 55, 255), width=3)
        d.line([(0, p), (W, p)], fill=(60, 58, 55, 255), width=3)
    for _ in range(3):
        x, y = r.randint(0, W), r.randint(0, W)
        pts = [(x, y)]
        for _ in range(12):
            x += r.randint(-30, 30); y += r.randint(8, 40)
            pts.append((x, y))
        d.line(pts, fill=(70, 66, 62, 200), width=1)
    # oil drips and stains (dark, glossier)
    for _ in range(9):
        cx, cy, rad = r.randint(80, W - 80), r.randint(80, W - 80), r.randint(14, 70)
        for k in range(6):
            rr = rad * (1 - k / 7)
            d.ellipse([cx - rr * 1.3, cy - rr, cx + rr * 1.3, cy + rr], fill=(30, 26, 22, 26))
        rd.ellipse([cx - rad, cy - rad * 0.8, cx + rad, cy + rad * 0.8], fill=150)
    # tyre marks: long soft dark arcs
    for _ in range(4):
        x0, y0 = r.randint(0, W), r.randint(0, W)
        a = r.uniform(0, math.pi)
        for side in (-14, 14):
            pts = []
            for t in range(40):
                aa = a + t * 0.012
                pts.append((x0 + math.cos(aa) * t * 18 + side * math.sin(a), y0 + math.sin(aa) * t * 18 - side * math.cos(a)))
            d.line(pts, fill=(25, 24, 23, 20), width=9)
    im = im.filter(ImageFilter.GaussianBlur(0.4))
    save("Forecourt", im, rough)


# ------------------------------------------------------------------ shop wall: split-face block (512, tiles every 3 m)
def shop_wall():
    W = 512
    r = random.Random(21)
    im = Image.new("RGB", (W, W), (200, 196, 186))
    d = ImageDraw.Draw(im)
    rows, cols = 15, 8  # 20 cm x 40 cm blocks
    bh, bw = W / rows, W / cols
    for j in range(rows):
        off = (bw / 2) if j % 2 else 0
        for i in range(-1, cols + 1):
            x0, y0 = i * bw + off, j * bh
            c = r.randint(-12, 10)
            d.rectangle([x0 + 2, y0 + 2, x0 + bw - 2, y0 + bh - 2], fill=(204 + c, 199 + c, 188 + c))
    # teal accent course near the bottom (row 13)
    d.rectangle([0, 13 * bh + 2, W, 14 * bh - 2], fill=(30, 100, 104))
    im = Image.blend(im, Image.merge("RGB", [Image.effect_noise((W, W), 30)] * 3).point(lambda v: v), 0.06)
    im = grime(im, 0.18, 22)
    rough = Image.new("L", (W, W), 225)
    save("ShopWall", im, rough)


# ------------------------------------------------------------------ shop window: panes with posters + shelves (1024 x 512, 3 panes)
def shop_glass():
    W, H = 1024, 512
    im = Image.new("RGB", (W, H))
    g = Image.linear_gradient("L").resize((W, H))
    im = Image.merge("RGB", [g.point(lambda v, a=a, b=b: int(a + (b - a) * v / 255)) for a, b in ((120, 50), (140, 62), (148, 70))])
    d = ImageDraw.Draw(im, "RGBA")
    rough = Image.new("L", (W, H), 18)
    rd = ImageDraw.Draw(rough)
    # warm shelves inside
    for k in range(4):
        y = 230 + k * 62
        d.rectangle([0, y, W, y + 8], fill=(200, 170, 110, 110))
        for x in range(0, W, 22):
            col = rng.choice(((220, 60, 50), (60, 120, 200), (240, 200, 60), (80, 170, 90), (240, 240, 240)))
            d.rectangle([x + 3, y - 34 + rng.randint(0, 10), x + 18, y], fill=(*col, 70))
    # posters on two panes
    posters = [(40, 250, "COLD", "DRINKS", (20, 110, 200)), (W // 3 + 60, 260, "HOT", "COFFEE", (150, 70, 30)),
               (2 * W // 3 + 50, 250, "OPEN", "24/7", (200, 40, 40))]
    for x, y, a, b, col in posters:
        d.rectangle([x, y, x + 180, y + 200], fill=(*col, 235))
        text_c(d, (x + 90, y + 70), a, font(FONT_B, 48), WHITE)
        text_c(d, (x + 90, y + 135), b, font(FONT_B, 40), (255, 220, 120))
        rd.rectangle([x, y, x + 180, y + 200], fill=160)
    # aluminium frames: 3 panes per tile, transom
    for i in range(4):
        x = int(i * W / 3)
        d.rectangle([x - 8, 0, x + 8, H], fill=(30, 31, 33, 255))
        rd.rectangle([x - 8, 0, x + 8, H], fill=110)
    d.rectangle([0, 0, W, 10], fill=(30, 31, 33, 255))
    d.rectangle([0, H - 14, W, H], fill=(30, 31, 33, 255))
    d.rectangle([0, 90, W, 100], fill=(30, 31, 33, 255))
    save("ShopGlass", im, rough)


# ------------------------------------------------------------------ canopy ceiling panels (512, 2 x 2 panels per tile)
def ceiling():
    W = 512
    im = Image.new("RGB", (W, W), (214, 216, 216))
    d = ImageDraw.Draw(im)
    for p in (0, W // 2):
        d.rectangle([p - 3, 0, p + 3, W], fill=(150, 152, 154))
        d.rectangle([0, p - 3, W, p + 3], fill=(150, 152, 154))
    for x in range(0, W, 16):  # fine ribs
        d.line([(x, 0), (x, W)], fill=(200, 202, 202), width=2)
    im = grime(im, 0.12, 31, streaks=False)
    save("CanopyUnder", im, Image.new("L", (W, W), 140))


# ------------------------------------------------------------------ fascia band (1024 x 256, tiles along the band every 6 m)
def fascia():
    W, H = 1024, 256
    im = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(H * 0.62), W, int(H * 0.80)], fill=WHITE)
    d.rectangle([0, int(H * 0.84), W, int(H * 0.89)], fill=AMBER)
    for x in range(0, W, W // 4):  # panel seams
        d.line([(x, 0), (x, H)], fill=TEAL_D, width=3)
    im = grime(im, 0.2, 41)
    save("Fascia", im, Image.new("L", (W, H), 90))


# ------------------------------------------------------------------ painted island kerb: yellow / black safety bands (256)
def island_kerb():
    W = 256
    im = Image.new("RGB", (W, W), (226, 180, 30))
    d = ImageDraw.Draw(im)
    for k in range(-W, W * 2, 64):
        d.polygon([(k, 0), (k + 32, 0), (k + 32 - W, W), (k - W, W)], fill=(24, 24, 24))
    im = scratches(grime(im, 0.3, 51), 160, 52, (120, 110, 100), 90)
    save("IslandKerb", im, Image.new("L", (W, W), 170))


for fn in (pump_face, pump_side, price_sign, forecourt, shop_wall, shop_glass, ceiling, fascia, island_kerb):
    fn()


# ------------------------------------------------------------------ printed signs (Roblox drops the caps of 3D font
# meshes, so every lettered sign is a flat textured panel instead)
def sign_strip(name, W, H, words, mark=True, line=True, size=None):
    im = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(im)
    f = font(FONT_B, size or int(H * 0.55))
    tw = d.textlength(words, font=f)
    mark_w = H * 0.9 if mark else 0
    x0 = (W - tw - mark_w) / 2
    if mark:
        wing(d, x0 + mark_w * 0.45, H * 0.5, H * 0.75, AMBER)
    text_c(d, (x0 + mark_w + tw / 2, H * 0.5), words, f, WHITE)
    if line:
        d.rectangle([0, int(H * 0.9), W, int(H * 0.94)], fill=AMBER)
    im = grime(im, 0.12, len(name), streaks=False)
    save(name, im, Image.new("L", (W, H), 90))


def label(name, W, H, words, bg, fg):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    size = int(H * 0.6)
    while size > 8 and d.textlength(words, font=font(FONT_B, size)) > W * 0.9:  # shrink to fit the panel
        size -= 2
    text_c(d, (W / 2, H / 2), words, font(FONT_B, size), fg)
    save(name, grime(im, 0.15, 9, streaks=False), Image.new("L", (W, H), 120))


sign_strip("ShopSign", 2048, 168, "KESTREL  MART")
sign_strip("FasciaBrand", 1024, 112, "KESTREL")
label("IceLabel", 512, 192, "ICE", (226, 238, 248), (20, 90, 170))
label("AirLabel", 256, 128, "AIR · WATER", (8, 92, 98), WHITE)


# ------------------------------------------------------------------ v4 detail pass: door, vending machine, ATM, column
# numbers, propane cage label, staff door (all original designs and brands)
def door_glass():
    W, H = 256, 512
    g = Image.linear_gradient("L").resize((W, H))
    im = Image.merge("RGB", [g.point(lambda v, a=a, b=b: int(a + (b - a) * v / 255)) for a, b in ((105, 40), (125, 50), (135, 58))])
    d = ImageDraw.Draw(im, "RGBA")
    rough = Image.new("L", (W, H), 15)
    rd = ImageDraw.Draw(rough)
    d.polygon([(30, 0), (90, 0), (10, 200), (0, 200), (0, 80)], fill=(255, 255, 255, 28))   # sky reflection streak
    for k in range(3):  # shelves glimpsed inside
        y = 300 + k * 50
        d.rectangle([0, y, W, y + 6], fill=(200, 170, 110, 90))
    d.rectangle([0, 0, W, 14], fill=(28, 29, 31, 255)); d.rectangle([0, H - 30, W, H], fill=(28, 29, 31, 255))
    d.rectangle([0, 0, 12, H], fill=(28, 29, 31, 255)); d.rectangle([W - 12, 0, W, H], fill=(28, 29, 31, 255))
    d.rectangle([W // 2 - 4, 0, W // 2 + 4, H], fill=(28, 29, 31, 255))
    for x0 in (12, W // 2 + 4):  # push bars + kick plates
        d.rounded_rectangle([x0 + 10, 236, x0 + 104, 250], 6, fill=(190, 192, 196, 255))
        d.rectangle([x0, H - 74, x0 + 120, H - 30], fill=(160, 162, 166, 255))
        rd.rectangle([x0 + 10, 236, x0 + 104, 250], fill=70)
    d.rectangle([24, 120, 110, 176], fill=(236, 237, 234, 230))
    text_c(d, (67, 136), "OPEN", font(FONT_B, 18), TEAL)
    text_c(d, (67, 160), "24 HOURS", font(FONT_B, 13), BLACK)
    text_c(d, (W // 2 + 64, 216), "PUSH", font(FONT_B, 16), (236, 237, 234, 200))
    text_c(d, (64, 216), "PUSH", font(FONT_B, 16), (236, 237, 234, 200))
    wing(d, W // 2 + 64, 150, 50, (*AMBER, 230))
    save("DoorGlass", im, rough)


def vending():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (176, 26, 34))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 70], fill=(140, 18, 26))
    text_c(d, (W / 2, 38), "ICY FIZZ", font(FONT_B, 34), WHITE)
    # window with rows of cans
    d.rectangle([16, 84, 176, 380], fill=(18, 20, 24))
    cols = ((220, 40, 40), (40, 110, 210), (250, 200, 40), (60, 170, 80), (240, 240, 240), (240, 120, 30))
    for j in range(6):
        y = 96 + j * 47
        d.rectangle([20, y + 36, 172, y + 40], fill=(120, 120, 126))
        for i in range(6):
            x = 24 + i * 25
            d.rounded_rectangle([x, y + 4, x + 18, y + 36], 4, fill=cols[(i + j) % len(cols)])
            d.rectangle([x + 3, y + 8, x + 6, y + 30], fill=(255, 255, 255))
    d.polygon([(16, 84), (60, 84), (16, 200)], fill=(70, 74, 82))
    # button column + coin slot + bill reader
    d.rectangle([188, 84, 244, 380], fill=(30, 30, 34))
    for k in range(6):
        d.rectangle([198, 96 + k * 34, 234, 120 + k * 34], fill=(220, 220, 220))
    d.rectangle([200, 316, 232, 330], fill=(10, 10, 10)); d.rectangle([206, 340, 226, 368], fill=(80, 200, 110))
    # dispenser bay
    d.rectangle([30, 404, 226, 470], fill=(16, 16, 18)); d.rectangle([30, 404, 226, 414], fill=(60, 60, 64))
    text_c(d, (W / 2, 492), "PUSH", font(FONT_B, 16), (255, 220, 120))
    im = grime(im, 0.12, 61)
    rough = Image.new("L", (W, H), 70)
    ImageDraw.Draw(rough).rectangle([16, 84, 176, 380], fill=12)
    save("Vending", im, rough)


def atm():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (120, 124, 128))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 80], fill=TEAL)
    text_c(d, (W / 2, 42), "CASH", font(FONT_B, 40), WHITE)
    d.rectangle([20, 100, W - 20, 270], fill=(40, 42, 46))
    d.rectangle([34, 112, W - 34, 214], fill=(30, 110, 150))
    text_c(d, (W / 2, 140), "WELCOME", font(FONT_B, 20), WHITE)
    text_c(d, (W / 2, 176), "INSERT CARD", font(FONT_R, 14), (220, 240, 250))
    for k in range(4):
        d.rectangle([24, 120 + k * 24, 32, 130 + k * 24], fill=(200, 200, 200))
        d.rectangle([W - 32, 120 + k * 24, W - 24, 130 + k * 24], fill=(200, 200, 200))
    d.rectangle([150, 236, 230, 250], fill=(10, 10, 10)); d.rectangle([150, 252, 230, 256], fill=(60, 200, 90))
    for j in range(4):
        for i in range(3):
            x, y = 40 + i * 34, 290 + j * 34
            d.rectangle([x, y, x + 26, y + 26], fill=(210, 212, 214))
            text_c(d, (x + 13, y + 13), "123456789*0#"[j * 3 + i], font(FONT_B, 14), BLACK)
    for k, c in enumerate(((200, 40, 40), (230, 190, 40), (40, 160, 70))):
        d.rectangle([160, 290 + k * 40, 220, 316 + k * 40], fill=c)
    d.rectangle([40, 440, 216, 456], fill=(12, 12, 12))
    text_c(d, (W / 2, 480), "24 HR ATM", font(FONT_B, 18), WHITE)
    im = grime(im, 0.12, 62)
    save("Atm", im, Image.new("L", (W, H), 80))


def pump_numbers():
    W = 512
    im = Image.new("RGB", (W, W), WHITE)
    d = ImageDraw.Draw(im)
    for k in range(4):
        x0, y0 = (k % 2) * 256, (k // 2) * 256
        d.rectangle([x0 + 6, y0 + 6, x0 + 250, y0 + 250], outline=TEAL, width=10)
        d.ellipse([x0 + 48, y0 + 30, x0 + 208, y0 + 190], fill=TEAL)
        text_c(d, (x0 + 128, y0 + 110), str(k + 1), font(FONT_B, 110), WHITE)
        text_c(d, (x0 + 128, y0 + 220), "PUMP", font(FONT_B, 30), TEAL)
    im = grime(im, 0.12, 63, streaks=False)
    save("PumpNumber", im, Image.new("L", (W, W), 110))


def staff_door():
    W, H = 256, 512
    im = Image.new("RGB", (W, H), (96, 100, 102))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], outline=(50, 52, 54), width=12)
    d.rectangle([20, H - 80, W - 20, H - 14], fill=(140, 142, 146))
    d.rectangle([W - 60, 230, W - 30, 260], fill=(190, 192, 196))
    d.rectangle([50, 120, 206, 190], fill=(236, 237, 234))
    text_c(d, (128, 142), "EMPLOYEES", font(FONT_B, 22), (180, 30, 30))
    text_c(d, (128, 172), "ONLY", font(FONT_B, 22), (180, 30, 30))
    im = scratches(grime(im, 0.25, 64), 120, 65, (170, 170, 170), 70)
    save("StaffDoor", im, Image.new("L", (W, H), 120))


for fn in (door_glass, vending, atm, pump_numbers, staff_door):
    fn()
label("PropaneLabel", 512, 128, "PROPANE EXCHANGE", (196, 36, 36), WHITE)
label("BinLabel", 384, 140, "THANK YOU", (8, 92, 98), WHITE)
