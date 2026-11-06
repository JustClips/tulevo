"""Paint the weather textures (our own, procedural) -> art/weather/tex/*.png + art/weather/textures.json

  python3 tools/weather_textures.py && python3 tools/upload_textures.py

White images with alpha; the game tints them.
  RainStreak   one thin vertical rain streak (particles, FacingCameraWorldUp)
  RainSpray    a little spray of droplets for the splash particles
  RainSheet    soft vertical streaky haze for the distant rain curtains (tiles sideways)
  Cirrus       wispy high clouds, tiles both ways, scrolled across the sky layer
  Overcast     thick soft cloud deck for storms, tiles both ways
  FootprintL/R a wet shoe print (sole + heel with tread lines), left and its mirror
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "weather", "tex")
rng = np.random.default_rng(7)


def save(name, alpha):
    a = np.clip(alpha, 0, 1)
    img = np.zeros(a.shape + (4,), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, name + ".png"))
    return f"art/weather/tex/{name}.png"


def periodic_noise(h, w, power, aniso=(1.0, 1.0)):
    """Tileable fractal noise from filtered white noise (1/f^power spectrum)."""
    spec = np.fft.fft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * aniso[0]
    fx = np.fft.fftfreq(w)[None, :] * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    x = np.real(np.fft.ifft2(spec / f ** power))
    return (x - x.mean()) / x.std()


def rain_streak():
    n = 256
    y, x = np.mgrid[0:n, 0:n] / (n - 1)
    core = np.exp(-((x - 0.5) * n / 1.6) ** 2)
    ends = np.clip(np.sin(np.pi * y), 0, 1) ** 0.8 * (0.35 + 0.65 * y)  # brighter at the leading (bottom) end
    return save("RainStreak", core * ends * 0.9)


def rain_spray():
    n = 128
    a = np.zeros((n, n))
    yy, xx = np.mgrid[0:n, 0:n]
    for _ in range(26):
        ang = rng.uniform(0, 2 * np.pi)
        r = rng.uniform(0.05, 0.42) * n
        cx, cy = n / 2 + np.cos(ang) * r, n / 2 + np.sin(ang) * r * 0.8
        s = rng.uniform(1.2, 3.2)
        a = np.maximum(a, np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s)) * rng.uniform(0.5, 1))
    return save("RainSpray", a)


def rain_sheet():
    h, w = 512, 512
    streaks = periodic_noise(h, w, 1.0, aniso=(1.0, 0.06))  # long streaks up and down
    soft = periodic_noise(h, w, 1.6)
    a = np.clip(0.45 + 0.22 * streaks + 0.2 * soft, 0, 1)
    y = np.linspace(0, 1, h)[:, None]
    fade = np.clip(y / 0.25, 0, 1) * np.clip((1 - y) / 0.1, 0, 1)  # thin at the top, soft at the bottom
    return save("RainSheet", a * fade * 0.8)


def cirrus():
    n = 1024
    base = periodic_noise(n, n, 1.35, aniso=(0.18, 1.0))  # long wisps along X
    detail = periodic_noise(n, n, 0.9, aniso=(0.3, 1.0))
    v = base + 0.35 * detail
    a = np.clip((v - 0.15) / 1.9, 0, 1) ** 1.2
    return save("Cirrus", a * 0.85)


def overcast():
    n = 1024
    v = periodic_noise(n, n, 1.5) + 0.3 * periodic_noise(n, n, 0.9)
    a = np.clip(0.55 + v * 0.28, 0, 1)
    return save("Overcast", a)


def footprints():
    h, w = 256, 128
    y, x = np.mgrid[0:h, 0:w].astype(float)
    x = (x - w / 2) / (w / 2)  # -1..1 across
    y = y / h  # 0 = toe, 1 = heel
    # left shoe: half-width along the length (toe at the top), centre leaning to the big-toe side
    ys = np.array([0.03, 0.1, 0.28, 0.45, 0.6, 0.75, 0.88, 0.97])
    ws = np.array([0.0, 0.62, 0.86, 0.72, 0.56, 0.62, 0.58, 0.0])
    half = np.interp(y, ys, ws)
    # round toe and heel caps instead of points
    toe = 0.7 * np.sqrt(np.clip(1 - ((0.16 - y) / 0.13) ** 2, 0, 1))
    heel = 0.6 * np.sqrt(np.clip(1 - ((y - 0.84) / 0.13) ** 2, 0, 1))
    half = np.where(y < 0.16, toe, np.where(y > 0.84, heel, half))
    centre = np.interp(y, [0, 0.3, 0.6, 1], [-0.14, -0.08, 0.06, 0.0])
    inside = half - np.abs(x - centre)
    sole = np.clip(inside * 9, 0, 1) * (y > 0.02) * (y < 0.98)
    lines = np.where(y < 0.5, np.sin(y * 170), np.sin(y * 120 + x * 4))
    tread = 0.72 + 0.28 * (lines > -0.3)
    arch = np.clip(1 - np.exp(-((y - 0.6) / 0.07) ** 2) * np.clip((x - centre + 0.1) * 3, 0, 1), 0.25, 1)
    tread = tread * arch
    mottle = 0.85 + 0.15 * periodic_noise(h, w, 1.2) / 3
    a = np.clip(sole * tread * mottle, 0, 1) * 0.9
    return save("FootprintL", a), save("FootprintR", a[:, ::-1])


def main():
    os.makedirs(OUT, exist_ok=True)
    m = {
        "RainStreak": rain_streak(),
        "RainSpray": rain_spray(),
        "RainSheet": rain_sheet(),
        "Cirrus": cirrus(),
        "Overcast": overcast(),
    }
    m["FootprintL"], m["FootprintR"] = footprints()
    json.dump(m, open(os.path.join(ROOT, "art", "weather", "textures.json"), "w"), indent=1)
    print("\n".join(m.values()))


if __name__ == "__main__":
    main()
