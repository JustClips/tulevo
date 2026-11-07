"""Looping flipbook frames for the spawn-plaza fountain water (numpy + PIL, all tileable).

  python3 tools/fountain_fx_textures.py  ->  art/fx/fountain/*.png + textures.json

Pool0..15   caustic water surface (pool and bowls), tiles both ways, loops over 16 frames
Fall0..7    falling water sheet: streaks running down (v), alpha, loops over 8 frames
Ripple0..7  impact ripple band: rings moving outward along v (u = around), alpha
Client/FountainFx swaps MeshPart.TextureID through the frames (TextureIds.Fountain).
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "fx", "fountain")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)
listing = {}


def save(name, arr, mode):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode).save(os.path.join(OUT, f"{name}.png"))
    listing[name] = f"art/fx/fountain/{name}.png"


# ---------------------------------------------------------------- pool caustics
N, S = 16, 256
y, x = np.mgrid[0:S, 0:S] / S
waves = [(rng.integers(-4, 5), rng.integers(-4, 5), rng.integers(1, 3) * rng.choice([-1, 1]), rng.uniform(0, 6.28)) for _ in range(9)]
waves = [w for w in waves if (w[0], w[1]) != (0, 0)]
for f in range(N):
    t = f / N
    h = sum(np.sin(2 * np.pi * (kx * x + ky * y + kt * t) + ph) for kx, ky, kt, ph in waves) / len(waves)
    h2 = sum(np.sin(2 * np.pi * (2 * kx * x - ky * y - kt * t) + ph * 1.7) for kx, ky, kt, ph in waves) / len(waves)
    c = (1 - np.abs(np.sin(5.5 * h))) ** 6 * 0.7 + (1 - np.abs(np.sin(4.0 * h2))) ** 8 * 0.5
    base = np.stack([20 + 30 * h, 120 + 25 * h, 160 + 20 * h], -1)
    rgb = base + c[..., None] * np.array([150, 130, 95])
    save(f"Pool{f}", rgb, "RGB")

# ---------------------------------------------------------------- falling sheet
FN, FW, FH = 8, 128, 256
u = np.arange(FW) / FW
cols = np.zeros(FW)
for k in range(1, 24):   # periodic random column brightness (tileable in u)
    cols += rng.normal() / k ** 0.8 * np.cos(2 * np.pi * (k * u) + rng.uniform(0, 6.28))
cols = (cols - cols.min()) / (cols.max() - cols.min())
streak_ph = rng.uniform(0, 1, FW)
vv = np.arange(FH)[:, None] / FH
for f in range(FN):
    t = f / FN
    s = np.sin(2 * np.pi * (3 * (vv + t) + streak_ph[None, :])) * 0.5 + 0.5
    s2 = np.sin(2 * np.pi * (7 * (vv + t) + streak_ph[None, ::-1] * 2)) * 0.5 + 0.5
    a = 0.1 + 0.5 * cols[None, :] ** 1.5 * (0.5 + 0.5 * s) + 0.1 * s2
    bright = 170 + 80 * (cols[None, :] * s)
    rgba = np.stack([bright * 0.86, bright * 0.95, bright, np.clip(a, 0, 1) * 255], -1)
    save(f"Fall{f}", rgba, "RGBA")

# ---------------------------------------------------------------- ripple band
RN, RW, RH = 8, 256, 64
uu, vr = np.meshgrid(np.arange(RW) / RW, np.arange(RH) / RH)
wob = sum(np.sin(2 * np.pi * (k * uu) + rng.uniform(0, 6.28)) / k for k in (3, 5, 8)) * 0.04
for f in range(RN):
    t = f / RN
    rings = (np.sin(2 * np.pi * (4 * (vr + wob) - t * 4 / 4 * 1)) * 0.5 + 0.5) ** 4
    fade = np.sin(np.pi * vr) ** 1.5
    foam = (rng.random((RH, RW)) < 0.03) * (1 - vr) * 0.6
    a = np.clip(rings * fade * 0.85 + foam, 0, 1)
    rgba = np.stack([np.full_like(a, 235), np.full_like(a, 245), np.full_like(a, 255), a * 255], -1)
    save(f"Ripple{f}", rgba, "RGBA")

json.dump(listing, open(os.path.join(OUT, "textures.json"), "w"), indent=1)
print("wrote", len(listing), "frames")
