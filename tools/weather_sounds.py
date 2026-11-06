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


def lowpass(x, cutoff):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec /= 1 + (f / cutoff) ** 4
    return np.fft.irfft(spec, len(x))


def thunder_crack(rng, n):
    """Close strike: a ripping crack (a few ms bursts, broadband), a hard boom, then a long
    rolling rumble that wanders and fades. Not a loop."""
    t = np.arange(n) / SR
    out = np.zeros(n)
    # rip: 25-40 tiny bursts over the first ~0.25 s
    for _ in range(rng.integers(25, 40)):
        st = rng.uniform(0, 0.25)
        m = int(rng.uniform(0.002, 0.012) * SR)
        i = int(st * SR)
        burst = rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 3)) * rng.uniform(0.4, 1.0)
        out[i:i + m] += burst
    # boom
    boom = lowpass(rng.standard_normal(n), 180) * np.exp(-t / 0.5) * 4.5
    # rumble: low noise with slow random swells
    env = np.exp(-np.maximum(t - 0.3, 0) / 2.4) * (t > 0.15)
    swell = lowpass(rng.standard_normal(n), 2.5)
    swell = 0.6 + 0.8 * (swell - swell.min()) / (np.ptp(swell) + 1e-9)
    rumble = lowpass(rng.standard_normal(n), 140) * env * swell * 6
    mid = lowpass(rng.standard_normal(n), 900) * np.exp(-t / 0.9) * 0.5
    return out * 0.9 + boom + rumble + mid


def thunder_rumble(rng, n):
    """Far strike: no crack, a soft onset and a long low roll."""
    t = np.arange(n) / SR
    att = np.clip(t / 0.6, 0, 1) ** 2
    env = att * np.exp(-np.maximum(t - 0.6, 0) / 2.8)
    swell = lowpass(rng.standard_normal(n), 1.8)
    swell = 0.4 + 1.0 * (swell - swell.min()) / (np.ptp(swell) + 1e-9)
    return lowpass(rng.standard_normal(n), 110) * env * swell


def fade_tail(x):
    k = int(0.4 * SR)
    x[-k:] *= np.linspace(1, 0, k)[:, None]
    return x


def main():
    os.makedirs(OUT, exist_ok=True)
    n = SR * 24
    write("RainLoop", stereo(lambda r: rain(r, n), 11, 12))
    write("RainHeavyLoop", stereo(lambda r: rain_heavy(r, n), 21, 22))
    for i in (1, 2):
        write(f"ThunderCrack{i}", fade_tail(stereo(lambda r: thunder_crack(r, SR * 8), 30 + i, 40 + i)))
        write(f"ThunderRumble{i}", fade_tail(stereo(lambda r: thunder_rumble(r, SR * 9), 50 + i, 60 + i)))


if __name__ == "__main__":
    main()
