"""Shared PIL helpers for the building texture scripts (tools/*_textures.py)."""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def saver(out):
    os.makedirs(out, exist_ok=True)

    def save(name, color, rough=None):
        color.convert("RGB").save(os.path.join(out, f"{name}_Color.png"))
        if rough is not None:
            (rough if not isinstance(rough, int) else Image.new("L", color.size, rough)).convert("L").convert("RGB").save(
                os.path.join(out, f"{name}_Roughness.png"))
        print("wrote", name)
    return save




def fit_text(d, xy, s, path, max_w, size, fill, anchor="mm"):
    while size > 8 and d.textlength(s, font=font(path, size)) > max_w:
        size -= 2
    d.text(xy, s, font=font(path, size), fill=fill, anchor=anchor)


def noise_tile(w, h, base, amp, seed, blur=1.0):
    """Flat colour with soft noise (stucco, concrete)."""
    r = random.Random(seed)
    n = Image.new("L", (w, h))
    n.putdata([r.randint(0, 255) for _ in range(w * h)])
    n = n.filter(ImageFilter.GaussianBlur(blur))
    big = Image.new("L", (w // 8, h // 8))
    big.putdata([r.randint(0, 255) for _ in range(big.width * big.height)])
    big = big.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(w / 40))
    im = Image.new("RGB", (w, h), base)
    px = im.load(); a = n.load(); b = big.load()
    for y in range(h):
        for x in range(w):
            k = (a[x, y] - 128) / 128 * amp + (b[x, y] - 128) / 128 * amp * 0.8
            px[x, y] = tuple(max(0, min(255, int(c + k))) for c in base)
    return im
