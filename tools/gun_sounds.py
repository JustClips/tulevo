"""Carbine rifle sounds -> art/sounds/*.ogg

  python3 tools/gun_sounds.py && python3 tools/upload_sounds.py

Gunshots are real recordings: an AR-15 (5.56) from The Free Firearm Sound Library
(freefirearmsfx.com, CC0, no credit needed), kept in art/sounds/source/:
  AR15_near.flac  near mic, beside the shooter (two shots)
  AR15_mid.flac   mic down range at mid distance (two shots, more echo)

  CarbineShot1-2      what the shooter hears / anyone close (stereo, ~1.6 s with the echo)
  CarbineDistant1-2   heard from a street or two away: thinner crack, longer echo
  CarbineFar1-2       far away: a dull pop and a low roll off the buildings

Bullet sounds are built from the physics (a supersonic bullet's crack is an N-shaped pressure
wave a fraction of a millisecond long; impacts are a sharp hit plus the material's own ring /
debris). Mono, played at a point in the world by Client/Weapons/GunAudio:
  BulletCrack1-3      a bullet passing close: the snap, its ground bounce and the street slap
  BulletWhiz1-3       a very close pass: the short tearing whizz of the air behind it
  Ricochet1-2         a glancing hit on something hard: the whine of a tumbling bullet
  ImpactConcrete1-3, ImpactMetal1-3, ImpactWood1-2, ImpactDirt1-2, ImpactGlass1-2,
  ImpactBody1-3 (a hit on a person)

Needs numpy + ffmpeg.
"""
import os
import subprocess

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "sounds")
SRC = os.path.join(OUT, "source")
SR = 44100


# helpers --------------------------------------------------------------------
def fft_filter(x, shape):
    n = len(x)
    spec = np.fft.rfft(x, axis=0)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 1.0)
    g = shape(f)
    if x.ndim == 2:
        g = g[:, None]
    return np.fft.irfft(spec * g, n, axis=0)


def lp(fc, slope=2.0):
    return lambda f: 1 / (1 + (f / fc) ** slope)


def hp(fc, slope=2.0):
    return lambda f: 1 / (1 + (fc / f) ** slope)


def band(lo, hi, slope=2.0):
    return lambda f: 1 / (1 + (lo / f) ** slope) / (1 + (f / hi) ** slope)


def shelf(fc, gain_db):
    """High shelf: gain_db above fc, smooth."""
    g = 10 ** (gain_db / 20)
    return lambda f: 1 + (g - 1) / (1 + (fc / f) ** 2)


def seconds(s):
    return int(round(s * SR))


def pad(x, n):
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros((n - len(x),) + x.shape[1:])])


def add(out, x, at):
    i = seconds(at) if isinstance(at, float) else at
    if i >= len(out):
        return
    m = min(len(x), len(out) - i)
    out[i:i + m] += x[:m]


def decay(n, tau, attack=0.0):
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    if attack > 0:
        e *= 1 - np.exp(-t / attack)
    return e


def fade_out(x, s):
    n = min(len(x), seconds(s))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n)[:, None] if x.ndim == 2 else np.linspace(1, 0, n)
    return x


def reverb(x, rng, length=0.9, tone=4000, wet=0.25, early=()):
    """Outdoor street reverb: a few wall slaps + a soft diffuse tail."""
    m = seconds(length)
    ir = rng.standard_normal(m) * decay(m, length / 6.9)
    ir = fft_filter(ir, lp(tone))
    ir[: seconds(0.01)] *= np.linspace(0, 1, seconds(0.01))
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    for delay, gain in early:
        i = seconds(delay)
        if i < m:
            ir[i] += gain
    y = np.convolve(x, ir)[: len(x) + m]
    return pad(x, len(y)) * (1 - wet * 0.5) + y * wet


def write(name, x, level=0.89):
    if x.ndim == 1:
        x = x[:, None]
    # trim trailing silence, short fade so nothing clicks
    a = np.abs(x).max(1)
    last = np.nonzero(a > a.max() * 0.0015)[0]
    end = min(len(x), (last[-1] if len(last) else len(x)) + seconds(0.02))
    x = fade_out(x[:end], 0.03)
    x = x / (np.abs(x).max() + 1e-9) * level
    raw = os.path.join(OUT, name + ".f32")
    x.astype("<f4").tofile(raw)
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]),
                    "-i", raw, "-c:a", "libvorbis", "-q:a", "6", ogg], check=True)
    os.remove(raw)
    print(f"{name:18s} {len(x) / SR:4.2f}s  {x.shape[1]}ch  {os.path.getsize(ogg) // 1024} KB")


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ar", str(SR), "-f", "f32le", "-ac", "2", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def onsets(x, count):
    """Start sample of the `count` loudest shots (1 s apart at least)."""
    a = np.abs(x).max(1)
    found = []
    order = np.argsort(a)[::-1]
    for i in order:
        if all(abs(i - j) > SR for j in found):
            found.append(i)
            if len(found) == count:
                break
    out = []
    for i in sorted(found):
        # walk back to where the shot starts rising out of the noise
        w = a[max(0, i - seconds(0.02)):i + 1]
        j = i - len(w) + 1 + int(np.argmax(w > a[i] * 0.02))
        out.append(max(0, j - seconds(0.0015)))
    return out


# real gunshots --------------------------------------------------------------
def gunshots(rng):
    near = load(os.path.join(SRC, "AR15_near.flac"))
    mid = load(os.path.join(SRC, "AR15_mid.flac"))
    near = fft_filter(near, hp(28, 4))  # rumble/handling noise below the blast
    mid = fft_filter(mid, hp(35, 4))

    for k, s in enumerate(onsets(near, 2), 1):
        shot = near[s:s + seconds(1.7)]
        # a touch more body: low shelf-ish bump under the blast, keep the crack bright
        shot = shot + 0.35 * fft_filter(shot, band(70, 220)) * decay(len(shot), 0.12)[:, None]
        write(f"CarbineShot{k}", fade_out(shot, 0.5))

    for k, s in enumerate(onsets(mid, 2), 1):
        shot = mid[s:s + seconds(2.6)]
        # distance eats the top end first
        distant = fft_filter(shot, lp(5500, 2))
        write(f"CarbineDistant{k}", fade_out(distant, 0.8))
        # far: mono, a dull pop, then a long low roll as the echo comes back off the city
        m = shot.mean(1)
        pop = fft_filter(m, lp(1300, 3)) * 1.0
        roll = reverb(fft_filter(m, lp(700, 2)), rng, length=2.4, tone=900, wet=0.9,
                      early=((0.21, 0.5), (0.47, 0.35), (0.83, 0.25), (1.3, 0.15)))
        far = pad(pop, len(roll)) * 0.6 + roll * 0.8
        far = far[: seconds(3.2)]
        write(f"CarbineFar{k}", fade_out(far, 1.0))


# bullet crack / whizz / ricochet ----------------------------------------------
def n_wave(width):
    """Supersonic bullet shock: jump up, straight line down past zero, jump back. ~0.2-0.5 ms."""
    n = max(4, seconds(width))
    w = np.linspace(1, -1, n)
    # slight rounding by the air (a few samples of rise)
    return np.convolve(np.concatenate([[0, 0], w, [0, 0]]), np.hanning(5) / np.hanning(5).sum())


def crack(rng, k):
    out = np.zeros(seconds(1.1))
    w = n_wave(0.00030 + 0.00012 * rng.random())
    snap = np.zeros(seconds(0.02))
    snap[: len(w)] = w
    # the snap rings a little in the ear / gear: short bright tail of noise
    tail = rng.standard_normal(seconds(0.02)) * decay(seconds(0.02), 0.0025)
    snap += 0.18 * fft_filter(tail, band(2500, 9000))
    add(out, snap, 0)
    # ground bounce ~2-4 ms later (duller), then the street slaps back the snap
    add(out, -0.55 * fft_filter(pad(snap, seconds(0.05)), lp(6000)), 0.002 + 0.002 * rng.random())
    for d, g in ((0.035, 0.22), (0.07, 0.15), (0.12, 0.1), (0.19, 0.07)):
        d *= 0.8 + 0.5 * rng.random()
        add(out, g * fft_filter(pad(snap, seconds(0.06)), lp(3500 - d * 8000)), d)
    out = reverb(out, rng, length=0.8, tone=3200, wet=0.35)
    # air carries a faint low "thump" with it from the mach cone hitting things around you
    thump = fft_filter(rng.standard_normal(seconds(0.08)), band(90, 300)) * decay(seconds(0.08), 0.015, 0.002)
    add(out, 0.25 * thump / (np.abs(thump).max() + 1e-9), 0.001)
    return out


def whiz(rng):
    """A very close pass: a short, tearing hiss that sweeps down (doppler) over ~0.15 s."""
    dur = 0.22 + 0.06 * rng.random()
    n = seconds(dur)
    t = np.arange(n) / SR
    mid = dur * (0.3 + 0.1 * rng.random())
    # loudness peaks at closest approach, falls off fast both sides
    env = 1 / (1 + ((t - mid) / 0.018) ** 2)
    out = np.zeros(n)
    # noise band whose centre slides from high to low through the pass
    noise = rng.standard_normal(n)
    hi, lo = 5200 + 1500 * rng.random(), 1300 + 500 * rng.random()
    blocks = 24
    edges = np.linspace(0, n, blocks + 1).astype(int)
    for b in range(blocks):
        a, z = edges[b], edges[b + 1]
        tc = (a + z) / 2 / SR
        fc = lo + (hi - lo) / (1 + np.exp((tc - mid) / 0.02))
        seg = fft_filter(noise, band(fc * 0.6, fc * 1.5, 3))[a:z]
        out[a:z] = seg
    # smooth block joins
    out = fft_filter(out, lp(9000))
    # tumbling flutter
    out *= 1 + 0.3 * np.sin(2 * np.pi * (180 + 80 * rng.random()) * t)
    return out * env


def ricochet(rng):
    """Bullet glances off and tumbles away: hit click, then a falling whine with flutter."""
    dur = 0.9 + 0.3 * rng.random()
    n = seconds(dur)
    t = np.arange(n) / SR
    f0 = 2600 + 900 * rng.random()
    f1 = f0 * (0.45 + 0.1 * rng.random())
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.45))
    # a tumbling bullet never holds a clean pitch
    wob = fft_filter(rng.standard_normal(n), lp(25))
    f = f * (1 + 0.04 * wob / (np.abs(wob).max() + 1e-9))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.2 * np.sin(2 * ph + 0.7)
    flutter = 1 + 0.55 * np.sin(2 * np.pi * (35 + 20 * rng.random()) * t + rng.random() * 6)
    env = decay(n, dur * 0.32, 0.006) * flutter
    breath = fft_filter(rng.standard_normal(n), band(1800, 6000)) * decay(n, dur * 0.25, 0.004)
    out = tone * env * 0.35 + breath / (np.abs(breath).max() + 1e-9) * 0.45 * flutter
    hit = fft_filter(rng.standard_normal(seconds(0.03)), band(1500, 10000)) * decay(seconds(0.03), 0.003)
    out = pad(out, n)
    add(out, hit / (np.abs(hit).max() + 1e-9) * 1.2, 0)
    # it moves away: gets duller as it goes
    lo = fft_filter(out, lp(1800))
    mix = np.clip(t / dur, 0, 1)
    out = out * (1 - mix) + lo * mix
    return reverb(out, rng, length=0.8, tone=4000, wet=0.25)


# impacts --------------------------------------------------------------------
def click(rng, bright=7000, width=0.0008):
    n = seconds(0.02)
    c = rng.standard_normal(n) * decay(n, width)
    c = fft_filter(c, band(700, bright, 2))
    return c / (np.abs(c).max() + 1e-9)


def grains(rng, dur, rate, tau_rate, lo, hi, grain=0.004, amp_tau=None):
    """Debris: lots of tiny bits landing/scattering. rate = grains/s at the start."""
    n = seconds(dur)
    out = np.zeros(n)
    t = 0.0
    while True:
        r = rate * np.exp(-t / tau_rate)
        if r < 3:
            break
        t += rng.exponential(1 / r)
        if t >= dur:
            break
        g = max(8, seconds(grain * (0.4 + rng.random())))
        b = rng.standard_normal(g) * decay(g, grain / 3)
        a = rng.random() ** 2 * (np.exp(-t / amp_tau) if amp_tau else 1)
        add(out, b * a, seconds(t))
    out = fft_filter(out, band(lo, hi, 2))
    return out / (np.abs(out).max() + 1e-9)


def modes(rng, freqs, decays, amps, dur, jitter=0.03):
    n = seconds(dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f, d, a in zip(freqs, decays, amps):
        f *= 1 + jitter * (rng.random() * 2 - 1)
        out += a * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t / d)
    return out


def thud(rng, lo, hi, tau, dur=0.15):
    n = seconds(dur)
    x = fft_filter(rng.standard_normal(n), band(lo, hi, 3)) * decay(n, tau, 0.0015)
    return x / (np.abs(x).max() + 1e-9)


def impact_concrete(rng):
    out = np.zeros(seconds(1.0))
    add(out, click(rng, 11000, 0.0006) * 1.0, 0)
    add(out, thud(rng, 120, 900, 0.012) * 0.55, 0.0)
    # chips and dust spraying off the wall, then grit pattering down
    add(out, grains(rng, 0.25, 2200, 0.05, 1800, 9000, 0.002, 0.08) * 0.55, 0.002)
    add(out, grains(rng, 0.5, 220, 0.15, 1200, 7000, 0.003, 0.25) * 0.16, 0.06)
    return reverb(out, rng, length=0.7, tone=5000, wet=0.3, early=((0.03, 0.4), (0.075, 0.25)))


def impact_metal(rng):
    out = np.zeros(seconds(1.2))
    add(out, click(rng, 12000, 0.0004) * 1.0, 0)
    base = 900 + 700 * rng.random()
    ratios = np.array([1.0, 1.59, 2.14, 2.83, 3.61, 4.52, 5.4])
    ring = modes(rng, base * ratios, [0.11, 0.08, 0.06, 0.045, 0.035, 0.025, 0.02],
                 [0.5, 0.45, 0.35, 0.3, 0.25, 0.2, 0.12], 1.0)
    add(out, ring * 0.55, 0)
    # the sheet/plate body thunks under it
    add(out, thud(rng, 150, 1200, 0.02) * 0.4, 0)
    add(out, grains(rng, 0.08, 1200, 0.02, 3000, 11000, 0.0015) * 0.2, 0.001)
    return reverb(out, rng, length=0.8, tone=5000, wet=0.25, early=((0.03, 0.3),))


def impact_wood(rng):
    out = np.zeros(seconds(0.8))
    add(out, click(rng, 8000, 0.0009) * 0.9, 0)
    base = 260 + 150 * rng.random()
    add(out, modes(rng, base * np.array([1, 2.3, 3.9, 5.6]), [0.03, 0.02, 0.012, 0.008],
                   [0.8, 0.5, 0.35, 0.2], 0.3) * 0.7, 0)
    # splinters
    add(out, grains(rng, 0.12, 1600, 0.03, 900, 6000, 0.003, 0.05) * 0.45, 0.002)
    return reverb(out, rng, length=0.6, tone=4000, wet=0.25, early=((0.03, 0.3),))


def impact_dirt(rng):
    out = np.zeros(seconds(0.9))
    add(out, thud(rng, 60, 600, 0.02, 0.2) * 1.0, 0)
    add(out, click(rng, 4000, 0.0012) * 0.35, 0)
    # spray of soil, then bits raining back down
    add(out, grains(rng, 0.2, 1800, 0.05, 500, 4500, 0.004, 0.07) * 0.6, 0.003)
    add(out, grains(rng, 0.5, 120, 0.2, 700, 5000, 0.004, 0.3) * 0.18, 0.12)
    return reverb(out, rng, length=0.5, tone=3000, wet=0.2)


def impact_glass(rng):
    out = np.zeros(seconds(1.3))
    add(out, click(rng, 14000, 0.0004) * 1.0, 0)
    # crack: bright snap spreading through the pane
    add(out, grains(rng, 0.06, 6000, 0.015, 2500, 14000, 0.0012) * 0.7, 0.0)
    # shards: lots of little ringing pieces falling and tinkling
    n = seconds(1.1)
    shards = np.zeros(n)
    t = 0.02
    while t < 0.9:
        t += rng.exponential(1 / (220 * np.exp(-t / 0.25) + 8))
        f = 2500 + rng.random() * 7000
        g = modes(rng, [f, f * 1.73, f * 2.41], [0.025, 0.018, 0.012], [1, 0.5, 0.3], 0.08)
        add(shards, g * rng.random() ** 1.5 * np.exp(-t / 0.4), seconds(t))
    add(out, shards / (np.abs(shards).max() + 1e-9) * 0.55, 0.01)
    return reverb(out, rng, length=0.8, tone=7000, wet=0.25, early=((0.03, 0.3),))


def impact_body(rng):
    """A hit on a person: a deep, wet punch into cloth and flesh, no ring."""
    out = np.zeros(seconds(0.5))
    add(out, thud(rng, 55, 380, 0.035, 0.25) * 1.0, 0)
    # cloth tear / slap on top
    slap = fft_filter(rng.standard_normal(seconds(0.05)), band(700, 3500, 2)) * decay(seconds(0.05), 0.006, 0.0005)
    add(out, slap / (np.abs(slap).max() + 1e-9) * 0.55, 0)
    # a small wet tail
    wet = grains(rng, 0.08, 900, 0.02, 400, 2500, 0.004) * 0.18
    add(out, wet, 0.008)
    return reverb(out, rng, length=0.35, tone=2500, wet=0.12)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(556)
    gunshots(rng)
    for k in range(1, 4):
        write(f"BulletCrack{k}", crack(rng, k))
        write(f"BulletWhiz{k}", whiz(rng), level=0.8)
    for k in range(1, 3):
        write(f"Ricochet{k}", ricochet(rng), level=0.75)
    for name, fn, count in (("ImpactConcrete", impact_concrete, 3), ("ImpactMetal", impact_metal, 3),
                            ("ImpactWood", impact_wood, 2), ("ImpactDirt", impact_dirt, 2),
                            ("ImpactGlass", impact_glass, 2), ("ImpactBody", impact_body, 3)):
        for k in range(1, count + 1):
            write(f"{name}{k}", fn(rng))


if __name__ == "__main__":
    main()
