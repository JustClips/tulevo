"""Synthesise the rain ambience loops (our own, no samples) -> art/sounds/*.ogg

  python3 tools/weather_sounds.py

Everything is built on a circular timeline (FFT noise, drops wrap round the end), so each
file loops with no seam. Needs numpy + ffmpeg.
"""
import os
import subprocess

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "sounds")
SR = 44100


def shaped_noise(n, rng, shape):
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= shape(np.maximum(f, 1.0))
    x = np.fft.irfft(spec, n)
    return x / np.abs(x).max()


def band(f, lo, hi, slope=2.0):
    return 1 / (1 + (lo / f) ** slope) / (1 + (f / hi) ** slope)


def drops(n, rng, rate, amp, flo, fhi, dlo, dhi):
    """Lots of tiny wet ticks: a short noise burst, band-passed with a one-pole resonator."""
    out = np.zeros(n)
    count = int(rate * n / SR)
    for _ in range(count):
        dur = rng.uniform(dlo, dhi)
        m = int(dur * SR)
        t = np.arange(m) / SR
        fr = np.exp(rng.uniform(np.log(flo), np.log(fhi)))
        env = np.exp(-t / (dur / 5)) * (1 - np.exp(-t * 4000))
        tone = np.sin(2 * np.pi * fr * t * (1 + 0.6 * np.exp(-t * 300))) * 0.55 + rng.standard_normal(m) * 0.45
        s = tone * env * amp * rng.lognormal(0, 0.6)
        start = rng.integers(0, n)
        idx = (start + np.arange(m)) % n
        out[idx] += s
    return out


def stereo(fn, seed_l, seed_r):
    return np.stack([fn(np.random.default_rng(seed_l)), fn(np.random.default_rng(seed_r))], 1)


def write(name, x):
    x = x / np.abs(x).max() * 0.85
    raw = os.path.join(OUT, name + ".f32")
    x.astype("<f4").tofile(raw)
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]),
                    "-i", raw, "-c:a", "libvorbis", "-q:a", "5", ogg], check=True)
    os.remove(raw)
    print(ogg, os.path.getsize(ogg) // 1024, "KB")


def rain(rng, n):
    hiss = shaped_noise(n, rng, lambda f: band(f, 900, 9000, 1.6)) * 0.38
    wash = shaped_noise(n, rng, lambda f: band(f, 120, 900, 2)) * 0.16
    # slow swells so the loop breathes (whole cycles over the file, so it still loops)
    t = np.arange(n) / n
    swell = 1 + 0.12 * np.sin(2 * np.pi * 3 * t + rng.uniform(0, 6)) + 0.06 * np.sin(2 * np.pi * 7 * t)
    fine = drops(n, rng, 900, 0.05, 2500, 9000, 0.002, 0.008)
    near = drops(n, rng, 45, 0.22, 900, 4000, 0.006, 0.03)  # splats on pavement close by
    tin = drops(n, rng, 6, 0.18, 2200, 5200, 0.05, 0.12)  # odd drip on metal (car roof, sign)
    return (hiss + wash) * swell + fine + near + tin


def rain_heavy(rng, n):
    roar = shaped_noise(n, rng, lambda f: band(f, 400, 7000, 1.4)) * 0.55
    low = shaped_noise(n, rng, lambda f: band(f, 60, 500, 2)) * 0.22
    t = np.arange(n) / n
    swell = 1 + 0.18 * np.sin(2 * np.pi * 2 * t + rng.uniform(0, 6)) + 0.08 * np.sin(2 * np.pi * 5 * t)
    fine = drops(n, rng, 1600, 0.05, 2000, 9000, 0.002, 0.009)
    near = drops(n, rng, 90, 0.2, 700, 3500, 0.008, 0.035)
    return (roar + low) * swell + fine + near


def main():
    os.makedirs(OUT, exist_ok=True)
    n = SR * 24
    write("RainLoop", stereo(lambda r: rain(r, n), 11, 12))
    write("RainHeavyLoop", stereo(lambda r: rain_heavy(r, n), 21, 22))


if __name__ == "__main__":
    main()
