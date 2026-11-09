"""Bullet hole decals + impact debris sprite for gun hits on the world (Client/Weapons/Effects).

  python3 tools/bullet_hole_sprites.py [--preview OUT.png] && python3 tools/upload_textures.py

Everything is drawn from noise here (no photos, no text): a height map per hole (crater, chipped
rim, cracks) lit from the upper left, so the decal reads as a dent in the wall, not a black dot.
Writes art/weapons/fx/BulletHole*.png + ImpactDebris.png and adds them to textures.json.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST = os.path.join(ROOT, "art", "weapons", "fx")
N = 256


def value_noise(rng, n, cells):
    """Smooth value noise in 0..1, size n x n, `cells` lattice cells across (tiles)."""
    g = rng.random((cells + 1, cells + 1))
    g[-1, :] = g[0, :]
    g[:, -1] = g[:, 0]
    t = np.linspace(0, cells, n, endpoint=False)
    i = t.astype(int)
    f = t - i
    f = f * f * (3 - 2 * f)
    a = g[i][:, i]
    b = g[i][:, i + 1]
    c = g[i + 1][:, i]
    d = g[i + 1][:, i + 1]
    fx, fy = f[None, :], f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(rng, n, base=4, octaves=5):
    out = np.zeros((n, n))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        out += value_noise(rng, n, base * 2 ** o) * amp
        total += amp
        amp *= 0.5
    return out / total


def polar(n):
    y, x = np.mgrid[0:n, 0:n]
    x = (x + 0.5) / n * 2 - 1
    y = (y + 0.5) / n * 2 - 1
    return x, y, np.sqrt(x * x + y * y), np.arctan2(y, x)


def angular(rng, theta, lobes=(3, 5, 9, 17), amp=0.18):
    """A wobbly radius multiplier around the circle, so holes are never perfect circles."""
    w = np.ones_like(theta)
    for k in lobes:
        w += amp / math.sqrt(k / 3) * np.sin(k * theta + rng.random() * 6.28) * rng.random()
    return w


def shade(h, light=(-0.6, -0.7, 0.55), strength=6.0):
    """Lambert shading of a height map, light from the upper left; 1 = flat."""
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    l = np.array(light) / np.linalg.norm(light)
    flat = l[2]
    return (nx * l[0] + ny * l[1] + nz * l[2]) / ln / flat


def cracks(rng, x, y, count, reach, width, wander=0.7):
    """Thin jagged lines from the centre out; returns 0..1 crack mask."""
    m = np.zeros_like(x)
    for _ in range(count):
        a = rng.random() * 2 * math.pi
        px, py = 0.0, 0.0
        length = reach * (0.5 + 0.5 * rng.random())
        steps = 14
        for s in range(steps):
            a += (rng.random() - 0.5) * wander
            seg = length / steps
            qx, qy = px + math.cos(a) * seg, py + math.sin(a) * seg
            # distance to segment
            dx, dy = qx - px, qy - py
            t = np.clip(((x - px) * dx + (y - py) * dy) / (dx * dx + dy * dy), 0, 1)
            d = np.sqrt((x - px - t * dx) ** 2 + (y - py - t * dy) ** 2)
            w = width * (1 - s / steps * 0.8)
            m = np.maximum(m, np.clip(1 - d / w, 0, 1))
            px, py = qx, qy
    return m


def save(name, rgb, alpha):
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    a = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(os.path.join(DST, f"{name}.png"))


def stone_hole(name, seed):
    """Concrete / brick / plaster: a dark punched hole in a chipped crater of fresh, paler stone,
    a ring of grey powder and a couple of hairline cracks."""
    rng = np.random.default_rng(seed)
    x, y, r, th = polar(N)
    grain = fbm(rng, N, 6, 5)
    rr = r / angular(rng, th, lobes=(4, 7, 13, 23), amp=0.09) + (grain - 0.5) * 0.12
    hole_r, crater_r, rim_r = 0.11, 0.30 + rng.random() * 0.05, 0.46
    # height: deep at the hole, bowl up through the crater, small lip at the rim
    h = np.where(rr < hole_r, -1.0, 0.0)
    bowl = np.clip((rr - hole_r) / (crater_r - hole_r), 0, 1)
    h = np.where((rr >= hole_r) & (rr < crater_r), -0.55 * (1 - bowl) ** 1.6, h)
    h += (grain - 0.5) * 0.25 * (rr < crater_r)
    crack = cracks(rng, x, y, rng.integers(0, 3), 0.6, 0.009, 0.45) * 0.6
    h -= crack * 0.15
    light = shade(h, strength=5.0)
    fresh = np.array([168, 164, 156])  # broken stone is paler than a weathered wall
    rgb = fresh[None, None, :] * (0.75 + 0.5 * grain[..., None]) * light[..., None]
    deep = np.clip((hole_r * 1.6 - rr) / (hole_r * 0.8), 0, 1)
    rgb = rgb * (1 - deep[..., None]) + np.array([18, 16, 14]) * deep[..., None]
    soot = np.clip(1 - (rr - crater_r) / (rim_r - crater_r), 0, 1) * (rr >= crater_r)
    rgb = rgb * (1 - 0.25 * soot[..., None])
    rgb = rgb * (1 - 0.6 * crack[..., None])
    alpha = np.where(rr < crater_r, 1.0, 0.0)
    # chipped rim: noisy edge + loose speckles of powder further out
    speck = fbm(rng, N, 24, 2)
    powder = np.clip((rim_r + 0.35 - rr) / 0.35, 0, 1) * np.clip((speck - 0.55) * 3, 0, 1) * 0.55
    edge = np.clip((crater_r + 0.05 - rr) / 0.05, 0, 1)
    alpha = np.maximum(np.maximum(alpha, edge), np.maximum(powder, crack * 0.8 * (r < 0.95)))
    rgb = np.where((rr >= crater_r)[..., None] & (crack < 0.3)[..., None], fresh * 0.95 * (0.8 + 0.3 * speck[..., None]), rgb)
    rgb = rgb * (1 - 0.6 * crack[..., None])
    save(name, rgb, alpha * np.clip((1 - r) / 0.08, 0, 1))


def metal_hole(name, seed):
    """Sheet metal: a clean round hole with a dark torn edge, a bright scuffed ring where the
    paint came off, and a faint burnt ring."""
    rng = np.random.default_rng(seed)
    x, y, r, th = polar(N)
    grain = fbm(rng, N, 8, 4)
    rr = r / angular(rng, th, lobes=(5, 11), amp=0.06) + (grain - 0.5) * 0.06
    hole_r, bare_r = 0.13, 0.32
    h = np.where(rr < hole_r, -1.0, -0.3 * np.clip(1 - (rr - hole_r) / (bare_r - hole_r), 0, 1) ** 2)
    light = shade(h, strength=6.0)
    bare = np.array([168, 170, 174])
    # brushed scratches round the hole
    brushed = 0.9 + 0.2 * (grain - 0.5)
    rgb = bare[None, None, :] * brushed[..., None] * light[..., None]
    deep = np.clip((hole_r * 1.25 - rr) / (hole_r * 0.3), 0, 1)
    rgb = rgb * (1 - deep[..., None]) + np.array([10, 10, 12]) * deep[..., None]
    burn_r = bare_r + 0.18
    burn = np.clip(1 - np.abs(rr - (bare_r + 0.07)) / 0.11, 0, 1) * (rr > bare_r)
    rgb = np.where((rr > bare_r)[..., None], np.array([40, 34, 30]) * (0.8 + 0.4 * grain[..., None]), rgb)
    alpha = np.where(rr < bare_r, 1.0, 0.0) + burn * 0.55 * (0.6 + 0.4 * grain)
    alpha *= np.clip((burn_r - rr) / 0.06, 0, 1) + (rr < bare_r)
    save(name, rgb, np.clip(alpha, 0, 1) * np.clip((1 - r) / 0.08, 0, 1))


def wood_hole(name, seed):
    """Wood: a dark hole with pale torn fibres splintering along the grain (left-right)."""
    rng = np.random.default_rng(seed)
    x, y, r, th = polar(N)
    grain = fbm(rng, N, 5, 4)
    # stretch along x: splinters run with the grain
    streak = value_noise(rng, N, 6)[:, :1] * 0 + fbm(rng, N, 3, 3)
    sx = x / (1.3 + 1.2 * streak)
    rr = np.sqrt(sx * sx + y * y) / angular(rng, th, lobes=(5, 9, 17), amp=0.12)
    hole_r, torn_r = 0.11, 0.34
    h = np.where(rr < hole_r, -1.0, -0.4 * np.clip(1 - (rr - hole_r) / (torn_r - hole_r), 0, 1))
    fib = 0.8 + 0.3 * np.repeat(fbm(rng, N, 40, 2)[:, :1], N, axis=1) * (0.7 + 0.6 * grain)
    h += (fib - 1) * 0.15 * (rr < torn_r)
    light = shade(h, strength=8.0)
    torn = np.array([186, 156, 112])  # fresh wood under the finish
    rgb = torn[None, None, :] * fib[..., None] * light[..., None]
    deep = np.clip((hole_r * 1.5 - rr) / (hole_r * 0.6), 0, 1)
    rgb = rgb * (1 - deep[..., None]) + np.array([26, 18, 12]) * deep[..., None]
    edge = np.clip((torn_r + 0.04 - rr) / 0.04, 0, 1)
    save(name, rgb, edge * np.clip((1 - r) / 0.08, 0, 1))


def glass_hole(name, seed):
    """Glass: a small frosted crater with a spider web of radial and ring cracks, white so it
    shows on dark and bright windows."""
    rng = np.random.default_rng(seed)
    x, y, r, th = polar(N)
    rr = r / angular(rng, th, lobes=(5, 9, 15), amp=0.15)
    radial = cracks(rng, x, y, 9 + rng.integers(0, 5), 0.95, 0.007, 0.25)
    rings = np.zeros_like(r)
    for ring_r in (0.22, 0.38, 0.55):
        wob = ring_r * angular(rng, th, lobes=(4, 7, 11), amp=0.07)
        rings = np.maximum(rings, np.clip(1 - np.abs(r - wob) / 0.007, 0, 1) * (rng.random() < 0.9))
    # ring cracks only show between the radial ones, in broken pieces
    gaps = fbm(rng, N, 10, 2) > 0.45
    rings *= gaps
    frost = np.clip((0.12 - rr) / 0.05, 0, 1)
    hole = np.clip((0.045 - rr) / 0.02, 0, 1)
    alpha = np.maximum.reduce([radial * 0.9 * np.clip((1 - r) / 0.4, 0.2, 1), rings * 0.7, frost * 0.9])
    rgb = np.ones((N, N, 3)) * 235
    rgb = rgb * (1 - hole[..., None]) + np.array([30, 32, 36]) * hole[..., None]
    alpha = np.maximum(alpha, hole)
    save(name, rgb, alpha * np.clip((1 - r) / 0.08, 0, 1))


def debris(name, seed):
    """A few sharp-edged chips on transparent, for flying bits (tinted per material in game)."""
    rng = np.random.default_rng(seed)
    n = 64
    y, x = np.mgrid[0:n, 0:n] / n * 2 - 1
    pts = rng.random((6, 2)) * 1.2 - 0.6
    pts = pts[np.argsort(np.arctan2(pts[:, 1], pts[:, 0]))]
    # convex-ish polygon chip
    inside = np.ones_like(x, dtype=bool)
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        inside &= (bx - ax) * (y - ay) - (by - ay) * (x - ax) >= 0
    gy, gx = np.mgrid[0:n, 0:n]
    lit = 0.75 + 0.35 * ((gx - gy) / n)
    rgb = np.ones((n, n, 3)) * 230 * lit[..., None]
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), (inside * 255).astype(np.uint8)]), "RGBA").save(
        os.path.join(DST, f"{name}.png"))


NAMES = ["BulletHoleConcrete1", "BulletHoleConcrete2", "BulletHoleConcrete3", "BulletHoleMetal1",
         "BulletHoleMetal2", "BulletHoleWood1", "BulletHoleGlass1", "BulletHoleGlass2", "ImpactDebris"]


def main():
    os.makedirs(DST, exist_ok=True)
    stone_hole("BulletHoleConcrete1", 11)
    stone_hole("BulletHoleConcrete2", 23)
    stone_hole("BulletHoleConcrete3", 37)
    metal_hole("BulletHoleMetal1", 5)
    metal_hole("BulletHoleMetal2", 9)
    wood_hole("BulletHoleWood1", 4)
    glass_hole("BulletHoleGlass1", 3)
    glass_hole("BulletHoleGlass2", 8)
    debris("ImpactDebris", 2)
    lp = os.path.join(DST, "textures.json")
    listing = json.load(open(lp)) if os.path.exists(lp) else {}
    for n in NAMES:
        listing[n] = f"art/weapons/fx/{n}.png"
    json.dump(listing, open(lp, "w"), indent=1)
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        cell = 200
        sheet = Image.new("RGB", (cell * len(NAMES), cell * 3))
        for row, bg in enumerate(((120, 118, 112), (196, 186, 170), (60, 70, 80))):
            for i, n in enumerate(NAMES):
                im = Image.open(os.path.join(DST, f"{n}.png")).resize((cell, cell), Image.LANCZOS)
                base = Image.new("RGBA", (cell, cell), (*bg, 255))
                base.alpha_composite(im)
                sheet.paste(base.convert("RGB"), (i * cell, row * cell))
        sheet.save(out)
        print("preview ->", out)


if __name__ == "__main__":
    main()
