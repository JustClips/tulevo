"""Texture sheets for The Marlowe apartments (original name and design), PIL only.

  python3 tools/apartment_textures.py   ->  art/blender/apartments/tex/*.png

Window bays (two curtain/lighting variants), balcony sliding doors, laundromat front, lobby
glass, garage roll-up gate, signs, stucco, solar panels.
"""
import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, grime, noise_tile, saver, scratches, text_c  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
save = saver(os.path.join(ROOT, "art", "blender", "apartments", "tex"))
r = random.Random(21)
PEACH = (222, 178, 146)
WHITE = (238, 236, 230)
FRAME = (52, 54, 58)


def wall():
    save("AptWall", grime(noise_tile(256, 256, PEACH, 9, 31), 0.12, 32), 230)


def window_pane(d, x0, y0, x1, y1, lit, curtain, blinds):
    d.rectangle([x0 - 10, y0 - 10, x1 + 10, y1 + 14], fill=WHITE)
    d.rectangle([x0, y0, x1, y1], fill=FRAME)
    inner = (250, 210, 150) if lit else (54, 62, 72)
    d.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], fill=inner)
    if blinds:
        for y in range(y0 + 8, int(y0 + (y1 - y0) * blinds), 7):
            d.line([(x0 + 6, y), (x1 - 6, y)], fill=(236, 232, 220), width=4)
    if curtain:
        w = (x1 - x0) // 4
        for xa in (x0 + 6, x1 - 6 - w):
            d.rectangle([xa, y0 + 6, xa + w, y1 - 6], fill=curtain)
    if not lit:
        d.polygon([(x0 + 6, y0 + 6), (x0 + 60, y0 + 6), (x0 + 6, y0 + 70)], fill=(120, 136, 150))
    d.rectangle([(x0 + x1) // 2 - 3, y0, (x0 + x1) // 2 + 3, y1], fill=FRAME)


def window_bay(name, seed):
    rr = random.Random(seed)
    W, H = 800, 512               # 5 m x 3.2 m
    im = noise_tile(W, H, PEACH, 9, seed)
    d = ImageDraw.Draw(im)
    for x0 in (90, 450):
        window_pane(d, x0, 110, x0 + 260, 360, rr.random() < 0.45, rr.choice([None, (190, 70, 60), (60, 90, 150), (220, 200, 160)]),
                    rr.choice([0, 0.3, 0.6]))
        d.rectangle([x0 - 16, 372, x0 + 276, 386], fill=(214, 210, 200))
    save(name, grime(im, 0.15, seed), 225)


def balcony_bay(name, seed):
    rr = random.Random(seed)
    W, H = 800, 512
    im = noise_tile(W, H, PEACH, 9, seed)
    d = ImageDraw.Draw(im)
    # sliding glass door (left two thirds) + a window
    d.rectangle([70, 60, 480, H], fill=WHITE)
    d.rectangle([80, 70, 470, H], fill=FRAME)
    lit = rr.random() < 0.5
    for x0, x1 in ((88, 272), (278, 462)):
        d.rectangle([x0, 78, x1, H - 4], fill=(240, 205, 150) if lit else (50, 58, 68))
    if rr.random() < 0.6:
        d.rectangle([88, 78, 200, H - 4], fill=rr.choice([(200, 190, 170), (150, 60, 60), (70, 100, 140)]))
    d.polygon([(278, 78), (360, 78), (278, 220)], fill=(130, 146, 160))
    window_pane(d, 560, 110, 740, 330, rr.random() < 0.4, None, 0.5)
    save(name, grime(im, 0.15, seed), 225)


def laundromat():
    W, H = 1024, 384               # 20 m x 4.4 m front, printed glass + sign band
    im = Image.new("RGB", (W, H), (34, 36, 40))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 70], fill=(30, 110, 180))
    fit_text(d, (W / 2, 36), "SUDS & SPIN  ·  COIN LAUNDRY  ·  OPEN 6AM - 11PM", FONT_B, W - 60, 40, (255, 255, 255))
    d.rectangle([0, 78, W, H], fill=(196, 214, 222))
    for k in range(12):             # front-loading washers row inside
        x = 30 + k * 82
        d.rectangle([x, 230, x + 70, 330], fill=(236, 238, 240))
        d.ellipse([x + 14, 248, x + 56, 290], fill=(70, 90, 110))
        d.ellipse([x + 20, 254, x + 50, 284], fill=(140, 170, 190))
    for k in range(6):              # dryers stacked behind
        x = 60 + k * 160
        d.rectangle([x, 110, x + 120, 200], fill=(210, 212, 214))
        d.ellipse([x + 36, 124, x + 84, 172], fill=(60, 64, 70))
    d.rounded_rectangle([800, 100, 980, 160], 10, fill=(20, 10, 14))
    text_c(d, (890, 130), "OPEN", font(FONT_B, 40), (255, 60, 110))
    for i in range(6):              # mullions
        x = int(i * W / 5)
        d.rectangle([x - 6, 70, x + 6, H], fill=FRAME)
    d.rectangle([0, H - 20, W, H], fill=FRAME)
    rough = Image.new("L", (W, H), 18)
    ImageDraw.Draw(rough).rectangle([0, 0, W, 70], fill=90)
    save("Laundromat", im, rough)


def lobby_glass():
    W, H = 512, 384
    im = Image.new("RGB", (W, H), FRAME)
    d = ImageDraw.Draw(im)
    d.rectangle([12, 12, W - 12, H - 12], fill=(70, 80, 88))
    d.rectangle([12, 200, W - 12, H - 12], fill=(200, 170, 120))          # lit lobby inside
    d.rectangle([160, 230, 352, 330], fill=(160, 120, 80))                # mailboxes wall
    for j in range(4):
        for i in range(8):
            d.rectangle([166 + i * 23, 236 + j * 23, 184 + i * 23, 254 + j * 23], fill=(190, 160, 90))
    d.rectangle([W // 2 - 4, 12, W // 2 + 4, H], fill=FRAME)
    for x0 in (60, W // 2 + 30):
        d.rectangle([x0, 190, x0 + 120, 202], fill=(200, 200, 204))
    text_c(d, (W // 2, 120), "1840", font(FONT_B, 70), (236, 224, 190))
    save("LobbyGlass", im, 20)


def garage_gate():
    W, H = 512, 384
    im = Image.new("RGB", (W, H), (120, 124, 128))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 12):
        d.rectangle([0, y, W, y + 9], fill=(138, 142, 146))
        d.line([(0, y + 10), (W, y + 10)], fill=(90, 92, 96), width=2)
    d.rectangle([0, H - 24, W, H], fill=(70, 72, 76))
    # yellow clearance sign + a bit of tagging (generic scribbles)
    d.rectangle([150, 30, 362, 80], fill=(240, 200, 40))
    text_c(d, (256, 55), "CLEARANCE 7'0\"", font(FONT_B, 24), (20, 20, 20))
    for _ in range(3):
        x, y = r.randint(40, 380), r.randint(140, 300)
        pts = [(x + r.randint(-6, 6) + k * 14, y + r.randint(-18, 18)) for k in range(9)]
        d.line(pts, fill=r.choice([(40, 40, 40), (180, 40, 120), (40, 90, 200)]), width=6)
    im = scratches(grime(im, 0.3, 41), 200, 42, (170, 170, 170), 70)
    save("GarageGate", im, 140)


def sign(name, words, bg, fg, W=1024, H=192):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    fit_text(d, (W / 2, H / 2), words, FONT_B, W - 60, int(H * 0.6), fg)
    save(name, grime(im, 0.08, len(words), streaks=False), 90)


def solar():
    W = 256
    im = Image.new("RGB", (W, W), (24, 36, 70))
    d = ImageDraw.Draw(im)
    for k in range(0, W, 32):
        d.line([(k, 0), (k, W)], fill=(160, 170, 190), width=2)
        d.line([(0, k), (W, k)], fill=(160, 170, 190), width=2)
    save("Solar", im, 40)


def back_windows():
    W, H = 640, 512
    im = noise_tile(W, H, (210, 170, 140), 9, 51)
    d = ImageDraw.Draw(im)
    for x0 in (80, 380):
        window_pane(d, x0, 140, x0 + 180, 330, r.random() < 0.3, None, 0.7)
    save("AptBack", grime(im, 0.25, 52), 230)


wall()
window_bay("AptWindowA", 61)
window_bay("AptWindowB", 62)
balcony_bay("AptBalcony", 63)
laundromat()
lobby_glass()
garage_gate()
sign("AptSign", "THE MARLOWE", (238, 236, 230), (40, 60, 70))
solar()
back_windows()
