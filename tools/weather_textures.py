"""Paint the weather textures (our own, procedural) -> art/weather/tex/*.png + art/weather/textures.json

  python3 tools/weather_textures.py && python3 tools/upload_textures.py

White images with alpha; the game tints them.
  RainStreak   one thin vertical rain streak (particles, FacingCameraWorldUp)
  RainSpray    a little spray of droplets for the splash particles
  RainSheet    soft vertical streaky haze for the distant rain curtains (tiles sideways)
  Cirrus       wispy high clouds, tiles both ways, scrolled across the sky layer
  Overcast     thick soft cloud deck for storms, tiles both ways
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


def main():
    os.makedirs(OUT, exist_ok=True)
    m = {
        "RainStreak": rain_streak(),
        "RainSpray": rain_spray(),
        "RainSheet": rain_sheet(),
        "Cirrus": cirrus(),
        "Overcast": overcast(),
    }
    json.dump(m, open(os.path.join(ROOT, "art", "weather", "textures.json"), "w"), indent=1)
    print("\n".join(m.values()))


if __name__ == "__main__":
    main()
