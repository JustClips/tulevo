"""Printed signs for the Arkwell Bank tower (our own brand), PIL only.

  python3 tools/bank_textures.py   ->  art/blender/bank_tower/tex/*.png

Roblox drops the cap faces of 3D font meshes (letters show as outlines), so the tower and
podium signs are printed panels. Also the ATM wall on the podium.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, grime, saver, text_c  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
save = saver(os.path.join(ROOT, "art", "blender", "bank_tower", "tex"))
AMBER = (242, 160, 32)
WHITE = (240, 240, 236)
DARK = (22, 26, 30)


def chevrons(d, cx, cy, s, fill):
    for k, off in enumerate((0.0, 0.42)):
        w = s * (1 - k * 0.25)
        t = w * 0.22
        y = cy - off * s + s * 0.2
        pts = [(-w / 2, w * 0.3), (0, -w * 0.3), (w / 2, w * 0.3), (w / 2 - t, w * 0.3), (0, -w * 0.3 + t * 1.25), (-w / 2 + t, w * 0.3)]
        d.polygon([(cx + x, y + z) for x, z in pts], fill=fill)


def sign(name, words, W, H, bg):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    chevrons(d, H * 0.75, H * 0.5, H * 0.75, AMBER)
    fit_text(d, (H * 1.4, H / 2), words, FONT_B, W - H * 1.6, int(H * 0.62), WHITE, anchor="lm")
    save(name, im, 80)


sign("TowerSign", "ARKWELL", 1024, 176, DARK)
sign("PodiumSign", "ARKWELL BANK", 1536, 128, DARK)


def atm_wall():
    W, H = 512, 384
    im = Image.new("RGB", (W, H), (60, 64, 68))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 64], fill=DARK)
    chevrons(d, 40, 32, 44, AMBER)
    fit_text(d, (W / 2 + 20, 32), "ARKWELL  ·  24 HR ATM", FONT_B, W - 100, 30, WHITE)
    for x0 in (40, 280):
        d.rectangle([x0, 90, x0 + 190, 360], fill=(150, 154, 158))
        d.rectangle([x0 + 20, 110, x0 + 170, 200], fill=(20, 90, 130))
        text_c(d, (x0 + 95, 145), "WELCOME", font(FONT_B, 20), WHITE)
        text_c(d, (x0 + 95, 175), "insert card", font(FONT_R, 14), (200, 230, 240))
        d.rectangle([x0 + 110, 214, x0 + 170, 224], fill=(10, 10, 10))
        for j in range(4):
            for i in range(3):
                d.rectangle([x0 + 24 + i * 26, 230 + j * 26, x0 + 44 + i * 26, 250 + j * 26], fill=(220, 220, 222))
        d.rectangle([x0 + 30, 340, x0 + 160, 350], fill=(10, 10, 10))
    save("AtmWall", grime(im, 0.12, 3, streaks=False), 90)


atm_wall()
