"""Texture sheets for the Arkwell ATM (art/blender/atm/build_atm.py), PIL + numpy only.

  python3 tools/atm_textures.py   ->  art/blender/atm/tex/*.png

Our own brand only (Arkwell chevrons, amber/white on charcoal). No URLs, no real bank or
card-network logos, no watermarks.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
from tex_kit import FONT_B, FONT_R, fit_text, font, saver, text_c  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
save = saver(os.path.join(ROOT, "art", "blender", "atm", "tex"))
AMBER = (242, 160, 32)
WHITE = (240, 240, 236)
DARK = (22, 26, 30)
rng = np.random.default_rng(11)


def chevrons(d, cx, cy, s, fill):
    """Arkwell mark: two stacked upward chevrons (same as tools/bank_textures.py)."""
    for k, off in enumerate((0.0, 0.42)):
        w = s * (1 - k * 0.25)
        t = w * 0.22
        y = cy - off * s + s * 0.2
        pts = [(-w / 2, w * 0.3), (0, -w * 0.3), (w / 2, w * 0.3), (w / 2 - t, w * 0.3), (0, -w * 0.3 + t * 1.25), (-w / 2 + t, w * 0.3)]
        d.polygon([(cx + x, y + z) for x, z in pts], fill=fill)


def brushed(w, h, base, amp, streak=90, seed=1):
    """Tileable brushed metal: noise smeared along x (wrap-around box blur), faint cross grain."""
    r = np.random.default_rng(seed)
    n = r.random((h, w))
    k = np.ones(streak) / streak
    sm = np.real(np.fft.ifft(np.fft.fft(n, axis=1) * np.fft.fft(k, w)[None, :], axis=1))
    sm = (sm - sm.mean()) / (sm.std() + 1e-6)
    fine = (r.random((h, w)) - 0.5) * 0.6
    low = np.asarray(Image.fromarray((r.random((h // 32, w // 32)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32)
    low = (low / 255 - 0.5)
    v = sm * amp + fine * amp * 0.5 + low * amp * 1.2
    out = np.clip(np.array(base, np.float32)[None, None, :] + v[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def powder(w, h, base, amp, seed):
    """Powder-coat / textured plastic: fine speckle + very soft blotches."""
    r = np.random.default_rng(seed)
    n = Image.fromarray((r.random((h, w)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    low = Image.fromarray((r.random((h // 16, w // 16)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    v = (np.asarray(n, np.float32) / 255 - 0.5) * amp + (np.asarray(low, np.float32) / 255 - 0.5) * amp * 0.8
    out = np.clip(np.array(base, np.float32)[None, None, :] + v[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


# ---------------------------------------------------------------- materials
save("AtmSteel", brushed(512, 512, (176, 179, 182), 14, seed=1), 90)            # fascia, trims
save("AtmSteelDark", brushed(512, 512, (118, 121, 125), 10, seed=2), 110)       # canopy underside, coping
save("AtmShell", powder(256, 256, (46, 49, 54), 16, seed=3), 150)               # surround (anthracite)
save("AtmBlack", powder(128, 128, (20, 21, 23), 10, seed=4), 170)               # bezels, shroud, slot lips
save("AtmRubber", powder(64, 64, (12, 12, 13), 6, seed=5), 230)                 # cash shutter brush strips
save("AtmMirror", brushed(256, 64, (150, 160, 168), 6, streak=40, seed=6), 20)  # rear-view mirror strip

# ---------------------------------------------------------------- keypad legends (4 x 4 atlas)
# cells: row 0: 1 2 3 CANCEL / row 1: 4 5 6 CLEAR / row 2: 7 8 9 ENTER / row 3: blank 0 blank blank
C = 128
keys = Image.new("RGB", (C * 4, C * 4))
steel = brushed(C, C, (190, 192, 195), 12, streak=30, seed=7)
for row, labels in enumerate((("1", "2", "3", "CANCEL"), ("4", "5", "6", "CLEAR"), ("7", "8", "9", "ENTER"), ("", "0", "", ""))):
    for col, s in enumerate(labels):
        x0, y0 = col * C, row * C
        colr = {"CANCEL": (200, 40, 36), "CLEAR": (236, 186, 30), "ENTER": (40, 150, 70)}.get(s)
        cell = steel.copy() if not colr else powder(C, C, colr, 14, seed=row * 4 + col)
        d = ImageDraw.Draw(cell)
        d.rectangle([0, 0, C - 1, C - 1], outline=(70, 72, 76), width=5)
        if s and not colr:
            text_c(d, (C / 2, C / 2 + 2), s, font(FONT_B, 76), (18, 18, 20))
            if s == "5":   # tactile dot
                d.ellipse([C / 2 - 6, C - 22, C / 2 + 6, C - 10], fill=(18, 18, 20))
        elif colr:
            fit_text(d, (C / 2, C / 2), s, FONT_B, C - 18, 30, (250, 250, 250) if s != "CLEAR" else (20, 20, 20))
        keys.paste(cell, (x0, y0))
save("AtmKeys", keys, 120)

# ---------------------------------------------------------------- labels atlas (4 x 2 cells of 256 x 128)
LW, LH = 256, 128
lab = Image.new("RGB", (LW * 4, LH * 2), (176, 179, 182))
d = ImageDraw.Draw(lab)


def cell(i, j):
    return i * LW, j * LH


# (0,0) ARKWELL brand plate (dark)
x, y = cell(0, 0)
d.rectangle([x, y, x + LW, y + LH], fill=DARK)
chevrons(d, x + 40, y + LH / 2, 44, AMBER)
fit_text(d, (x + 72, y + LH / 2), "ARKWELL", FONT_B, LW - 86, 46, WHITE, anchor="lm")
# (1,0) CARD with a card + arrow pictogram
x, y = cell(1, 0)
d.rectangle([x, y, x + LW, y + LH], fill=(28, 30, 33))
d.rounded_rectangle([x + 22, y + 30, x + 92, y + 98], 6, outline=(90, 220, 120), width=6)
d.rectangle([x + 30, y + 44, x + 84, y + 54], fill=(90, 220, 120))
d.polygon([(x + 57, y + 6), (x + 45, y + 22), (x + 69, y + 22)], fill=(90, 220, 120))
fit_text(d, (x + 110, y + LH / 2), "CARD", FONT_B, LW - 120, 50, WHITE, anchor="lm")
# (2,0) CASH
x, y = cell(2, 0)
d.rectangle([x, y, x + LW, y + LH], fill=(28, 30, 33))
d.rectangle([x + 20, y + 36, x + 100, y + 92], outline=(90, 220, 120), width=6)
d.ellipse([x + 48, y + 52, x + 72, y + 76], outline=(90, 220, 120), width=5)
fit_text(d, (x + 116, y + LH / 2), "CASH", FONT_B, LW - 126, 50, WHITE, anchor="lm")
# (3,0) RECEIPT
x, y = cell(3, 0)
d.rectangle([x, y, x + LW, y + LH], fill=(28, 30, 33))
d.polygon([(x + 30, y + 24), (x + 80, y + 24), (x + 80, y + 104), (x + 72, y + 96), (x + 64, y + 104), (x + 56, y + 96),
           (x + 48, y + 104), (x + 40, y + 96), (x + 30, y + 104)], outline=(90, 220, 120), width=5)
for k in range(3):
    d.line([(x + 40, y + 44 + k * 16), (x + 70, y + 44 + k * 16)], fill=(90, 220, 120), width=4)
fit_text(d, (x + 96, y + LH / 2), "RECEIPT", FONT_B, LW - 104, 44, WHITE, anchor="lm")
# (0,1) "24 HR" amber tag
x, y = cell(0, 1)
d.rectangle([x, y, x + LW, y + LH], fill=AMBER)
fit_text(d, (x + LW / 2, y + LH / 2), "24 HR", FONT_B, LW - 30, 70, DARK)
# (1,1) function-key arrow (left side) / (2,1) arrow (right side)
for i, flip in ((1, False), (2, True)):
    x, y = cell(i, 1)
    d.rectangle([x, y, x + LW, y + LH], fill=(28, 30, 33))
    pts = [(40, 64), (120, 24), (120, 104)] if not flip else [(216, 64), (136, 24), (136, 104)]
    d.polygon([(x + a, y + b) for a, b in pts], fill=(160, 166, 172))
# (3,1) lock cylinder / service plate
x, y = cell(3, 1)
d.rectangle([x, y, x + LW, y + LH], fill=(150, 153, 156))
d.ellipse([x + LW / 2 - 40, y + LH / 2 - 40, x + LW / 2 + 40, y + LH / 2 + 40], fill=(110, 112, 116), outline=(60, 62, 66), width=6)
d.rectangle([x + LW / 2 - 6, y + LH / 2 - 26, x + LW / 2 + 6, y + LH / 2 + 26], fill=(30, 30, 32))
save("AtmLabels", lab, 120)

# ---------------------------------------------------------------- idle screen (4:3)
SW, SH = 800, 600
scr = Image.new("RGB", (SW, SH))
g = np.linspace(0, 1, SH)[:, None, None]
top, bot = np.array((12, 40, 70), np.float32), np.array((6, 18, 34), np.float32)
scr = Image.fromarray(np.broadcast_to(top * (1 - g) + bot * g, (SH, SW, 3)).astype(np.uint8), "RGB")
d = ImageDraw.Draw(scr)
d.rectangle([0, 0, SW, 86], fill=DARK)
chevrons(d, 60, 43, 50, AMBER)
fit_text(d, (100, 43), "ARKWELL BANK", FONT_B, 420, 40, WHITE, anchor="lm")
fit_text(d, (SW - 30, 43), "24 HR ATM", FONT_R, 200, 28, (200, 210, 220), anchor="rm")
d.rectangle([0, 86, SW, 92], fill=AMBER)
text_c(d, (SW / 2, 210), "Welcome", font(FONT_B, 92), WHITE)
text_c(d, (SW / 2, 290), "Please insert your card", font(FONT_R, 38), (190, 214, 236))
# card-slot hint: arrow pointing to the right, where the reader is
d.polygon([(SW - 70, 290), (SW - 110, 266), (SW - 110, 314)], fill=AMBER)
# soft option buttons on the left / right edges (line up with the function keys)
opts = (("Withdraw", "Balance"), ("Deposit", "Transfer"))
for side, (a, b) in enumerate(opts):
    for k, s in enumerate((a, b)):
        yy = 364 + k * 132   # centres line up with the two lower function keys (z 4.2 / 3.85)
        if side == 0:
            d.rectangle([0, yy, 260, yy + 66], fill=(24, 74, 120))
            d.rectangle([0, yy, 10, yy + 66], fill=AMBER)
            fit_text(d, (30, yy + 33), s, FONT_B, 220, 34, WHITE, anchor="lm")
        else:
            d.rectangle([SW - 260, yy, SW, yy + 66], fill=(24, 74, 120))
            d.rectangle([SW - 10, yy, SW, yy + 66], fill=AMBER)
            fit_text(d, (SW - 30, yy + 33), s, FONT_B, 220, 34, WHITE, anchor="rm")
text_c(d, (SW / 2, SH - 24), "Cover the keypad when you enter your PIN", font(FONT_R, 22), (130, 150, 170))
# a hint of screen glare
glare = Image.new("L", (SW, SH), 0)
ImageDraw.Draw(glare).polygon([(0, 0), (SW * 0.45, 0), (SW * 0.15, SH), (0, SH)], fill=22)
scr = Image.composite(Image.new("RGB", (SW, SH), (255, 255, 255)), scr, glare.filter(ImageFilter.GaussianBlur(40)))
save("AtmScreen", scr, 30)

# ---------------------------------------------------------------- header sign over the machines (lit box face)
W, H = 1024, 256
im = Image.new("RGB", (W, H), DARK)
d = ImageDraw.Draw(im)
d.rectangle([0, H - 18, W, H], fill=AMBER)
chevrons(d, 110, H / 2 - 8, 130, AMBER)
fit_text(d, (205, H / 2 - 8), "ARKWELL", FONT_B, 470, 120, WHITE, anchor="lm")
d.rectangle([700, 64, 704, H - 70], fill=(90, 96, 104))
fit_text(d, (860, H / 2 - 30), "24 HR", FONT_B, 260, 66, AMBER)
fit_text(d, (860, H / 2 + 34), "ATM", FONT_B, 260, 66, WHITE)
save("AtmSign", im, 80)
