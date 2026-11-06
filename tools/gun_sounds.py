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
def limit(x, threshold, release=0.06):
    """Peak limiter (instant attack, smooth release): squashes the spike of the blast so the
    whole shot can be turned up. threshold = share of the peak that's kept."""
    x = x / (np.abs(x).max() + 1e-9)
    a = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    env = np.empty_like(a)
    k = np.exp(-1 / (release * SR))
    e = 0.0
    for i, v in enumerate(a):
        e = v if v > e else e * k + v * (1 - k)
        env[i] = e
    # 1 ms look-ahead so the gain is already down when the spike hits
    la = seconds(0.001)
    env = np.concatenate([env[la:], np.full(la, env[-1])])

    g = np.minimum(1, threshold / np.maximum(env, 1e-9))
    g = np.convolve(g, np.hanning(seconds(0.0015)) / np.hanning(seconds(0.0015)).sum(), mode="same")
    return x * (g[:, None] if x.ndim == 2 else g)


def big_shot(shot, rng):
    """GTA 5 style carbine, heard from the shooter's own position: dry, close and punchy.
    Echo is what makes a shot sound far away (Dev: v4/v5 sounded "400 m away"), so the
    recording's own echo is gated off after the blast and no reverb is added. Full top end
    (no low-pass), boom below 100 Hz cut, close-up low-mid weight, gently limited."""
    n = seconds(0.9)
    shot = pad(shot / (np.abs(shot).max() + 1e-9), n)
    t = np.arange(n) / SR
    gate = np.where(t < 0.08, 1.0, np.exp(-(t - 0.08) / 0.12))  # blast stays, echo dies fast
    mix = shot * gate[:, None]
    mix = fft_filter(mix, hp(100, 2))
    mix = fft_filter(mix, lambda f: 1 + 0.6 / (1 + ((f - 350) / 250) ** 2))   # close-up weight
    mix = fft_filter(mix, lambda f: 1 + 0.3 / (1 + ((f - 2800) / 1500) ** 2))  # clear crack
    mix = limit(mix, 0.45)
    return fade_out(mix, 0.3)


def gunshots(rng):
    near = load(os.path.join(SRC, "AR15_near.flac"))
    mid = load(os.path.join(SRC, "AR15_mid.flac"))
    near = fft_filter(near, hp(28, 4))  # rumble/handling noise below the blast
    mid = fft_filter(mid, hp(35, 4))

    for k, s in enumerate(onsets(near, 2), 1):
        write(f"CarbineShot{k}", big_shot(near[s:s + seconds(1.7)], rng))

    for k, s in enumerate(onsets(mid, 2), 1):
        shot = mid[s:s + seconds(2.6)]
        # distance eats the top end first
        distant = fft_filter(shot, lp(4200, 2))
        distant = fft_filter(distant, hp(120, 2))
        write(f"CarbineDistant{k}", fade_out(limit(distant, 0.5), 0.8))
        # far: mono, a dull pop, then a long low roll as the echo comes back off the city
        m = shot.mean(1)
        pop = fft_filter(m, lp(1300, 3)) * 1.0
        roll = reverb(fft_filter(m, lp(700, 2)), rng, length=2.4, tone=900, wet=0.9,
                      early=((0.21, 0.5), (0.47, 0.35), (0.83, 0.25), (1.3, 0.15)))
        far = pad(pop, len(roll)) * 0.6 + roll * 0.8
        far = limit(far[: seconds(3.2)] / (np.abs(far).max() + 1e-9), 0.4)
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
    return limit(out, 0.4)


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


# GTA-style impacts: short, punchy and loud. A sharp hit, the material's own "thock / ping",
# a quick puff of debris and a short slap off the street, then squashed so it cuts through.
def punchy(x, threshold=0.3):
    return limit(np.tanh(x / (np.abs(x).max() + 1e-9) * 1.8), threshold)


def impact_concrete(rng):
    out = np.zeros(seconds(0.6))
    add(out, click(rng, 12000, 0.0005) * 1.0, 0)
    # the "thock": a short mid knock of the wall itself
    add(out, modes(rng, [420 + 120 * rng.random(), 910, 1650], [0.012, 0.008, 0.005], [1, 0.6, 0.4], 0.1) * 0.8, 0)
    add(out, thud(rng, 150, 1400, 0.01) * 0.7, 0)
    # a quick puff of chips
    add(out, grains(rng, 0.09, 3000, 0.025, 1500, 9000, 0.0018) * 0.45, 0.002)
    out = reverb(out, rng, length=0.35, tone=4500, wet=0.22, early=((0.025, 0.35),))
    return punchy(out)


def impact_metal(rng):
    out = np.zeros(seconds(0.6))
    add(out, click(rng, 14000, 0.0003) * 1.0, 0)
    base = 1900 + 900 * rng.random()
    add(out, modes(rng, base * np.array([1.0, 1.47, 2.09, 2.76, 3.4]), [0.09, 0.06, 0.045, 0.03, 0.02],
                   [0.8, 0.6, 0.45, 0.3, 0.2], 0.4) * 0.7, 0)
    add(out, modes(rng, [380 + 150 * rng.random(), 780], [0.02, 0.012], [1, 0.5], 0.1) * 0.6, 0)
    add(out, thud(rng, 200, 2000, 0.008) * 0.4, 0)
    out = reverb(out, rng, length=0.4, tone=6000, wet=0.18, early=((0.025, 0.3),))
    return punchy(out, 0.35)


def impact_wood(rng):
    out = np.zeros(seconds(0.45))
    add(out, click(rng, 9000, 0.0007) * 0.9, 0)
    base = 230 + 120 * rng.random()
    add(out, modes(rng, base * np.array([1, 2.3, 3.9]), [0.025, 0.015, 0.01], [1, 0.55, 0.3], 0.15) * 0.9, 0)
    add(out, grains(rng, 0.06, 2000, 0.02, 1000, 6000, 0.003) * 0.4, 0.002)
    out = reverb(out, rng, length=0.3, tone=4000, wet=0.18)
    return punchy(out)


def impact_dirt(rng):
    out = np.zeros(seconds(0.5))
    add(out, thud(rng, 70, 700, 0.018, 0.15) * 1.0, 0)
    add(out, click(rng, 5000, 0.001) * 0.5, 0)
    add(out, grains(rng, 0.12, 2200, 0.035, 500, 5000, 0.004) * 0.55, 0.003)
    out = reverb(out, rng, length=0.3, tone=3000, wet=0.15)
    return punchy(out)


def impact_glass(rng):
    out = np.zeros(seconds(0.7))
    add(out, click(rng, 15000, 0.0003) * 1.0, 0)
    add(out, grains(rng, 0.05, 7000, 0.012, 2500, 15000, 0.001) * 0.8, 0.0)
    shards = np.zeros(seconds(0.6))
    t = 0.01
    while t < 0.45:
        t += rng.exponential(1 / (300 * np.exp(-t / 0.12) + 6))
        f = 3000 + rng.random() * 6500
        g = modes(rng, [f, f * 1.73], [0.02, 0.012], [1, 0.4], 0.06)
        add(shards, g * rng.random() ** 1.5 * np.exp(-t / 0.18), seconds(t))
    add(out, shards / (np.abs(shards).max() + 1e-9) * 0.5, 0.005)
    out = reverb(out, rng, length=0.35, tone=7000, wet=0.18)
    return punchy(out, 0.35)


def impact_body(rng):
    """A hit on a person, GTA style: a meaty, slapping punch, no ring."""
    out = np.zeros(seconds(0.35))
    n = seconds(0.2)
    t = np.arange(n) / SR
    f = 70 + 90 * np.exp(-t / 0.02)
    add(out, np.sin(2 * np.pi * np.cumsum(f) / SR) * decay(n, 0.045, 0.001) * 0.9, 0)
    add(out, thud(rng, 120, 900, 0.02, 0.15) * 0.8, 0)
    slap = fft_filter(rng.standard_normal(seconds(0.04)), band(900, 4500, 2)) * decay(seconds(0.04), 0.005, 0.0004)
    add(out, slap / (np.abs(slap).max() + 1e-9) * 0.7, 0)
    add(out, grains(rng, 0.05, 1200, 0.015, 500, 3000, 0.004) * 0.2, 0.006)
    return punchy(out, 0.32)


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
