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


# ---------------------------------------------------------------- facade detail (2026-11-06)
def _wrap_noise(w, h, cell, seed, blur):
    """Tileable value noise: random grid repeated 3x3, blurred, centre cut out."""
    r = random.Random(seed)
    gw, gh = max(1, w // cell), max(1, h // cell)
    g = Image.new("L", (gw, gh))
    g.putdata([r.randint(0, 255) for _ in range(gw * gh)])
    g = g.resize((w, h), Image.BICUBIC)
    big = Image.new("L", (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            big.paste(g, (i * w, j * h))
    big = big.filter(ImageFilter.GaussianBlur(blur))
    return big.crop((w, h, 2 * w, 2 * h))


def stucco(base, seed, size=512, contrast=1.0, cracks=6, patches=3):
    """Tileable sprayed stucco: trowel blotches + fine sand grain + hairline cracks + repaired
    patches + rain stains. Much more visible than noise_tile at game distance."""
    import numpy as np
    r = random.Random(seed)
    w = h = size
    big = np.asarray(_wrap_noise(w, h, 64, seed, 18), np.float32) / 255 - 0.5
    mid = np.asarray(_wrap_noise(w, h, 12, seed + 1, 3), np.float32) / 255 - 0.5
    fine = np.asarray(_wrap_noise(w, h, 2, seed + 2, 0.6), np.float32) / 255 - 0.5
    k = (big * 26 + mid * 16 + fine * 22) * contrast
    img = np.clip(np.array(base, np.float32)[None, None, :] + k[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    for _ in range(patches):                     # patched repairs: slightly different tone, soft edge
        x, y, pw, ph = r.randint(0, w), r.randint(0, h), r.randint(40, 120), r.randint(30, 90)
        tone = r.choice((-14, -9, 8, 12))
        for dx in (-w, 0, w):
            for dy in (-h, 0, h):
                d.rounded_rectangle([x + dx, y + dy, x + dx + pw, y + dy + ph], 12,
                                    fill=(*[max(0, min(255, c + tone)) for c in base], 90))
    for _ in range(cracks):                      # hairline cracks (wander, branch once)
        x, y = r.randint(0, w), r.randint(0, h)
        a = r.uniform(0, math.tau)
        for _seg in range(r.randint(6, 14)):
            a += r.uniform(-0.6, 0.6)
            nx, ny = x + math.cos(a) * r.randint(5, 14), y + math.sin(a) * r.randint(5, 14)
            for dx in (-w, 0, w):
                for dy in (-h, 0, h):
                    d.line([(x + dx, y + dy), (nx + dx, ny + dy)], fill=(60, 54, 46, 120), width=1)
            x, y = nx, ny
    return im


def glass_pane(w, h, seed, kind="home", lit=None):
    """Window glass seen from outside: sky reflection gradient, room interior (blinds, curtains,
    furniture shapes, lamp glow when lit), dust in the corners, a bright diagonal glint.
    kind: home | bath (frosted) | shop | office."""
    r = random.Random(seed)
    lit = (r.random() < 0.35) if lit is None else lit
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im, "RGBA")
    # interior
    if kind == "bath":
        im.paste((196, 206, 210), (0, 0, w, h))
        for y in range(0, h, 3):
            d.line([(0, y), (w, y)], fill=(255, 255, 255, r.randint(10, 40)))
    else:
        back = (236, 196, 140) if lit else r.choice(((44, 50, 58), (52, 56, 62), (38, 44, 54)))
        im.paste(back, (0, 0, w, h))
        if kind in ("home", "office"):
            for _ in range(3):              # furniture silhouettes / shelves / lamp
                x0, x1 = sorted((r.randint(0, w), r.randint(0, w)))
                y0 = r.randint(h // 2, h - 10)
                d.rectangle([x0, y0, x1, h], fill=(*[int(c * 0.55) for c in back], 255))
            if lit:
                cx, cy = r.randint(w // 4, 3 * w // 4), r.randint(h // 5, h // 2)
                for rad in range(int(w * 0.5), 4, -6):
                    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(255, 230, 170, 10))
        if kind == "office":
            for y in range(int(h * 0.12), h, max(6, h // 20)):
                d.line([(0, y), (w, y)], fill=(200, 200, 196, 120), width=2)
        style = r.choice(("blinds", "curtains", "curtains", "none", "sheet")) if kind == "home" else "none"
        if style == "blinds":
            drop = r.uniform(0.25, 0.85)
            for y in range(0, int(h * drop), 6):
                d.line([(0, y), (w, y)], fill=(232, 228, 214, 255), width=4)
            d.line([(0, int(h * drop)), (w, int(h * drop))], fill=(150, 146, 136, 255), width=3)
        elif style == "curtains":
            col = r.choice(((176, 64, 56), (70, 96, 140), (214, 198, 160), (120, 150, 110), (200, 170, 120)))
            cw = int(w * r.uniform(0.18, 0.32))
            for xa in (0, w - cw):
                for k in range(xa, xa + cw, 8):
                    d.rectangle([k, 0, k + 5, h], fill=(*col, 255))
                    d.line([(k + 6, 0), (k + 6, h)], fill=(*[int(c * 0.7) for c in col], 255), width=2)
        elif style == "sheet":                    # foil / sheet taped over the glass
            d.rectangle([w * 0.05, h * 0.05, w * 0.95, h * 0.95], fill=(206, 206, 196, 230))
    # sky reflection + reflected buildings + glints, blended over the interior with numpy
    import numpy as np
    base = np.asarray(im.convert("RGB"), np.float32)
    ys = np.linspace(0, 1, h)[:, None]
    sky = np.stack([190 - 70 * ys, 214 - 70 * ys, 232 - 60 * ys], -1) * np.ones((1, w, 1))
    a = np.ones((h, w, 1)) * ((0.42 if not lit else 0.22) * (1 - 0.45 * ys))[..., None]
    sil = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(sil)
    for _ in range(3):
        bx = r.randint(-w // 4, w)
        sd.rectangle([bx, h - r.randint(h // 5, h // 2), bx + r.randint(w // 6, w // 2), h], fill=255)
    silm = np.asarray(sil, np.float32)[..., None] / 255
    sky = sky * (1 - 0.55 * silm)
    out = base * (1 - a) + sky * a
    gl = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(gl)
    g = r.uniform(0.2, 0.7)
    gd.polygon([(w * g, 0), (w * (g + 0.16), 0), (w * (g - 0.24), h), (w * (g - 0.40), h)], fill=36)
    gd.polygon([(w * (g + 0.22), 0), (w * (g + 0.26), 0), (w * (g - 0.14), h), (w * (g - 0.18), h)], fill=28)
    gl = np.asarray(gl.filter(ImageFilter.GaussianBlur(2)), np.float32)[..., None] / 255
    out = out * (1 - gl) + 255 * gl
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.minimum(np.minimum(xx, w - 1 - xx) / w, np.minimum(yy, h - 1 - yy) / h)
    dust = np.clip(1 - dist / 0.12, 0, 1)[..., None] * 0.35          # grime along the frame edge
    out = out * (1 - dust) + np.array((120, 112, 96), np.float32) * dust
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
    return im.convert("RGB")


def glass_set(save, prefix="Glass", n=6, seed=900, kinds=("home",), size=(256, 256)):
    """n glass sheets <prefix>A.. (+ <prefix>Frost, a frosted bathroom one). Roughness low."""
    for i in range(n):
        save(f"{prefix}{chr(65 + i)}", glass_pane(*size, seed + i, kinds[i % len(kinds)]), 25)
    save(f"{prefix}Frost", glass_pane(*size, seed + 99, "bath"), 80)


def surface(kind, base, seed=1, size=256):
    """Tileable realistic surface sheet: wood, laminate, metal (brushed), paint, plastic, granite,
    block (CMU), rubber, gravel, drywall. base = (r, g, b)."""
    import numpy as np
    w = h = size
    b = np.array(base, np.float32)
    big = np.asarray(_wrap_noise(w, h, 48, seed, 10), np.float32) / 255 - 0.5
    mid = np.asarray(_wrap_noise(w, h, 8, seed + 1, 2), np.float32) / 255 - 0.5
    fine = np.asarray(_wrap_noise(w, h, 1, seed + 2, 0.5), np.float32) / 255 - 0.5
    y, x = np.mgrid[0:h, 0:w] / size
    if kind in ("wood", "laminate"):
        n = 10 if kind == "wood" else 22
        warp = big * 0.8 + mid * 0.15
        g = np.sin(2 * np.pi * (n * y + warp * 3)) * 0.5 + 0.5
        g = g ** 3
        k = (g * -22 + big * 14 + fine * (10 if kind == "wood" else 5))[..., None]
        img = b + k * np.array([1.0, 0.85, 0.7])
        if kind == "wood":                                  # plank seams
            for yy in range(0, h, h // 4):
                img[yy:yy + 2] *= 0.55
    elif kind == "metal":
        streak = np.asarray(_wrap_noise(w, h, 1, seed + 3, 0.4).resize((w, h)), np.float32) / 255 - 0.5
        streak = np.repeat(streak.mean(axis=1, keepdims=True), w, axis=1) * 0.6 + fine * 0.4
        img = b + (streak * 26 + big * 10)[..., None]
    elif kind == "paint":
        img = b + (big * 10 + mid * 6 + fine * 6)[..., None]
    elif kind == "plastic":
        img = b + (big * 8 + fine * 5)[..., None]
    elif kind == "granite":
        img = b + (big * 14 + mid * 18 + fine * 40)[..., None]
        rr = np.random.default_rng(seed)
        dots = rr.random((h, w)) < 0.05
        img[dots] = img[dots] * 0.45
        light = rr.random((h, w)) < 0.03
        img[light] = np.minimum(255, img[light] * 1.3)
    elif kind == "block":
        img = b + (big * 12 + mid * 10 + fine * 26)[..., None]
        joint = (np.abs((y * 2) % 1.0) < 0.025) | (np.abs(((x + (np.floor(y * 2) % 2) * 0.5) * 1) % 1.0) < 0.012)
        img[joint] = img[joint] * 0.62
    elif kind == "rubber":
        bumps = (np.sin(2 * np.pi * 24 * x) * np.sin(2 * np.pi * 24 * y)) * 0.5
        img = b + (bumps * 10 + fine * 8 + big * 6)[..., None]
    elif kind == "gravel":
        rr = np.random.default_rng(seed)
        img = b + (big * 10 + mid * 30 + fine * 50)[..., None]
        sp = rr.random((h, w)) < 0.12
        img[sp] = img[sp] * rr.uniform(0.6, 1.35, (sp.sum(), 1))
    else:   # drywall / default
        img = b + (big * 6 + fine * 4)[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
