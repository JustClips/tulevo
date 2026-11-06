"""Synthesise the storm and city ambience sounds (our own, no samples) -> art/sounds/*.ogg

  python3 tools/city_sounds.py && python3 tools/upload_sounds.py

Thunder (2D, stereo):     ThunderClose1-2 (crack + boom), ThunderFar1-3 (low rolling rumble)
City beds (loops):        CityDayLoop, CityNightLoop (distant traffic), CricketsLoop
City one-shots (mono, played at a point near the listener by Client/Ambience):
                          SirenWail, SirenHiLo, DogBark1-2, Birds1-3, CarHorn1-2

Loops are built on a circular timeline (FFT noise, events wrap round the end, circular
reverb), so they repeat with no seam. Everything distant goes through a little "street"
reverb and a low-pass so it sits behind the rain. Needs numpy + ffmpeg.
"""
import os
import subprocess

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "art", "sounds")
SR = 44100


# helpers --------------------------------------------------------------------
def fft_filter(x, shape):
    """Filter x (1D) by a gain curve shape(freq) in the frequency domain (circular)."""
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1 / SR), 1.0)
    return np.fft.irfft(spec * shape(f), n)


def lp(fc, slope=2.0):
    return lambda f: 1 / (1 + (f / fc) ** slope)


def hp(fc, slope=2.0):
    return lambda f: 1 / (1 + (fc / f) ** slope)


def band(lo, hi, slope=2.0):
    return lambda f: 1 / (1 + (lo / f) ** slope) / (1 + (f / hi) ** slope)


def peak(fc, q, gain):
    """Resonant bump (for formants): 1 + gain at fc, width fc/q."""
    return lambda f: 1 + gain / (1 + ((f - fc) / (fc / q)) ** 2)


def noise(n, rng, shape=None):
    x = rng.standard_normal(n)
    if shape:
        x = fft_filter(x, shape)
    return x / (np.abs(x).max() + 1e-9)


def osc(freq, rng=None, harmonics=(1.0,)):
    """Additive oscillator from a per-sample frequency array; harmonics = amplitudes of 1f, 2f, ..."""
    ph = 2 * np.pi * np.cumsum(freq) / SR
    if rng is not None:
        ph += rng.uniform(0, 6.28)
    out = np.zeros(len(freq))
    for k, a in enumerate(harmonics, 1):
        if a:
            out += a * np.sin(k * ph) * (k * freq < SR * 0.45)
    return out


def reverb(x, rng, seconds=1.4, tone=3500, wet=0.35, circular=False, early=()):
    """Street reverb: exponentially decaying noise impulse + a few discrete wall echoes."""
    m = int(seconds * SR)
    t = np.arange(m) / SR
    ir = rng.standard_normal(m) * np.exp(-t * 6.9 / seconds)
    ir = fft_filter(ir, lp(tone))
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    for delay, gain in early:
        i = int(delay * SR)
        if i < m:
            ir[i] += gain * np.abs(ir).max() * 4
    ir /= np.sqrt((ir ** 2).sum()) + 1e-9
    if circular:
        n = len(x)
        h = np.zeros(n)
        h[: min(m, n)] = ir[: min(m, n)]
        y = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(h), n)
    else:
        n = len(x) + m
        y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
        x = np.concatenate([x, np.zeros(m)])
    y *= np.abs(x).max() / (np.abs(y).max() + 1e-9)
    return x * (1 - wet) + y * wet * 1.6


def env_ar(n, attack, release):
    t = np.arange(n) / SR
    return (1 - np.exp(-t / max(attack, 1e-4))) * np.exp(-t / release)


def place(out, s, start, wrap=True, pan=None):
    """Add s into out at start (wrapping round for loops). out may be (n,) or (n,2)."""
    n = len(out)
    idx = (start + np.arange(len(s))) % n if wrap else start + np.arange(len(s))
    keep = idx < n
    if out.ndim == 1:
        out[idx[keep]] += s[keep]
    else:
        p = 0.5 if pan is None else pan
        out[idx[keep], 0] += s[keep] * np.cos(p * np.pi / 2)
        out[idx[keep], 1] += s[keep] * np.sin(p * np.pi / 2)


def trim(x, floor=0.002):
    a = np.abs(x if x.ndim == 1 else x.max(1))
    a = a / (a.max() + 1e-9)
    last = np.nonzero(a > floor)[0]
    end = (last[-1] if len(last) else len(x)) + int(0.05 * SR)
    x = x[:end].copy()
    fade = min(int(0.05 * SR), len(x))
    ramp = np.linspace(1, 0, fade)
    x[-fade:] *= ramp if x.ndim == 1 else ramp[:, None]
    return x


def write(name, x, level=0.85):
    if x.ndim == 1:
        x = x[:, None]
    x = x / (np.abs(x).max() + 1e-9) * level
    raw = os.path.join(OUT, name + ".f32")
    x.astype("<f4").tofile(raw)
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(x.shape[1]),
                    "-i", raw, "-c:a", "libvorbis", "-q:a", "5", ogg], check=True)
    os.remove(raw)
    print(f"{ogg}  {len(x) / SR:.1f}s  {os.path.getsize(ogg) // 1024} KB")


# thunder --------------------------------------------------------------------
def thunder(rng, close: bool, seconds: float):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    if close:
        # the crack: a tearing burst of hundreds of tiny clicks over ~0.35 s, bright, then the boom
        crack = np.zeros(n)
        for _ in range(500):
            at = rng.exponential(0.09)
            if at > 0.6:
                continue
            i = int((0.03 + at) * SR)
            m = int(rng.uniform(0.001, 0.006) * SR)
            if i + m < n:
                crack[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (m / 3)) * rng.lognormal(0, 0.7)
        crack = fft_filter(crack, band(300, 9000, 1.2)) * np.exp(-t / 0.5)
        boom = noise(n, rng, band(25, 160, 2.5)) * env_ar(n, 0.02, 1.4) * 1.6
        body = noise(n, rng, band(60, 900, 1.5)) * env_ar(n, 0.05, 0.9) * 0.8
        mono = crack * 1.3 + boom + body
        # the roll after it: echoes of the boom off buildings and clouds
        for _ in range(7):
            at = rng.uniform(0.4, seconds * 0.55)
            m = n - int(at * SR)
            swell = noise(m, rng, band(30, rng.uniform(250, 500), 2)) * env_ar(m, rng.uniform(0.08, 0.4), rng.uniform(0.6, 1.6))
            place(mono, swell * rng.uniform(0.35, 0.8), int(at * SR), wrap=False)
        for c in range(2):
            out[:, c] = mono + noise(n, rng, band(40, 400, 2)) * env_ar(n, 0.3, 2.0) * 0.25
        out *= np.clip((seconds - t) / 1.5, 0, 1)[:, None]  # no hard stop under the tail
        out = reverb_st(out, rng, 2.2, 2500, 0.3)
    else:
        # far away: no crack, a low rolling rumble that grows, tumbles a few times, and dies away
        mono = np.zeros(n)
        k = rng.integers(4, 8)
        for j in range(k):
            at = rng.uniform(0, seconds * 0.5) if j else 0
            m = n - int(at * SR)
            swell = noise(m, rng, band(22, rng.uniform(120, 260), 2.5)) * env_ar(m, rng.uniform(0.25, 0.8), rng.uniform(0.8, 2.2))
            place(mono, swell * rng.uniform(0.4, 1.0), int(at * SR), wrap=False)
        mono *= 1 - np.exp(-t / 0.3)
        for c in range(2):
            out[:, c] = mono + noise(n, rng, band(25, 200, 2)) * env_ar(n, 0.6, 2.4) * 0.3
        out *= np.clip((seconds - t) / 2.0, 0, 1)[:, None]
        out = reverb_st(out, rng, 2.8, 900, 0.35)
    return trim(out)


def reverb_st(x, rng, seconds, tone, wet):
    return np.stack([reverb(x[:, c], rng, seconds, tone, wet) for c in range(2)], 1)


# city beds ------------------------------------------------------------------
def car_pass(rng, dur, near):
    """A car going by somewhere down the street: tyre roar + engine hum, swelling and fading."""
    m = int(dur * SR)
    t = np.arange(m) / SR
    shape = np.exp(-((t - dur / 2) / (dur / 5)) ** 2)
    tyre = noise(m, rng, band(250, 1600 if near else 900, 1.5))
    rpm = rng.uniform(35, 70) * (1 + 0.04 * np.tanh((dur / 2 - t) * 1.5))  # a touch of doppler
    engine = osc(rpm, rng, (1, 0.6, 0.4, 0.25, 0.15, 0.1)) * (0.5 + 0.5 * noise(m, rng, lp(30)))
    return (tyre * 0.7 + engine * 0.35) * shape


def city_bed(rng, seconds, cars_per_min, hum, near_share):
    n = int(seconds * SR)
    t = np.arange(n) / n
    out = np.zeros((n, 2))
    # the city's constant low roar (traffic everywhere far away) + a faint airy layer
    for c in range(2):
        out[:, c] = noise(n, rng, band(30, 450, 1.6)) * hum + noise(n, rng, band(500, 3000, 2)) * hum * 0.12
    out *= (1 + 0.1 * np.sin(2 * np.pi * 2 * t + rng.uniform(0, 6)))[:, None]
    for _ in range(int(cars_per_min * seconds / 60)):
        near = rng.random() < near_share
        dur = rng.uniform(3, 5) if near else rng.uniform(5, 9)
        s = car_pass(rng, dur, near) * (rng.uniform(0.35, 0.6) if near else rng.uniform(0.12, 0.3))
        place(out, s, rng.integers(0, n), pan=rng.uniform(0.15, 0.85))
    return np.stack([reverb(out[:, c], rng, 1.6, 2500, 0.3, circular=True) for c in range(2)], 1)


def crickets(rng, seconds):
    n = int(seconds * SR)
    out = np.zeros((n, 2))
    for _ in range(9):
        f = rng.uniform(3800, 5200)
        pulse_hz = rng.uniform(25, 45)
        pulses = rng.integers(2, 5)
        gap = rng.uniform(0.35, 0.9)
        amp = rng.uniform(0.15, 1.0) ** 2
        pan = rng.uniform(0.1, 0.9)
        m = int((pulses / pulse_hz + 0.02) * SR)
        tt = np.arange(m) / SR
        gate = np.clip(np.sin(np.pi * tt * pulse_hz), 0, 1) ** 3 * (tt < pulses / pulse_hz)
        chirp = np.sin(2 * np.pi * f * tt) * gate * amp
        at = rng.uniform(0, gap)
        while at < seconds:
            if rng.random() > 0.08:  # skip one now and then so it isn't a metronome
                place(out, chirp * rng.uniform(0.8, 1.0), int(at * SR), pan=pan)
            at += gap * rng.uniform(0.95, 1.05)
    out += noise(n, rng, band(2000, 8000, 2))[:, None] * 0.01
    return np.stack([reverb(out[:, c], rng, 1.0, 6000, 0.25, circular=True) for c in range(2)], 1)


# one-shots ------------------------------------------------------------------
def distant(x, rng, tone=3000, rev=1.6, wet=0.4):
    """Far away down the street: high end gone, echoes off the buildings."""
    x = fft_filter(np.concatenate([x, np.zeros(int(0.1 * SR))]), lp(tone, 2.5))
    early = [(rng.uniform(0.05, 0.12), 0.5), (rng.uniform(0.15, 0.3), 0.35), (rng.uniform(0.3, 0.5), 0.2)]
    return trim(reverb(x, rng, rev, tone, wet, early=early))


def siren_wail(rng, seconds=11):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    sweep = 0.5 - 0.5 * np.cos(2 * np.pi * t / 4.2)  # slow up-down wail
    f = 620 + 820 * sweep
    drive = np.exp(-((t - seconds * 0.5) / (seconds * 0.32)) ** 2)  # comes closer, goes away
    dopp = 1 + 0.02 * np.tanh((seconds * 0.5 - t) * 0.8)
    tone = osc(f * dopp, rng, (1, 0, 0.33, 0, 0.2, 0, 0.12)) * drive  # squarish horn
    tone *= np.clip(t / 0.5, 0, 1) * np.clip((seconds - t) / 0.5, 0, 1)
    return distant(tone, rng, 2600, 2.0, 0.45)


def siren_hilo(rng, seconds=10):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    hi = (np.floor(t / 0.65) % 2 == 0)
    f = np.where(hi, 950.0, 770.0)
    f = fft_filter(f - f.mean(), lp(40)) + f.mean()  # soften the jumps
    drive = np.exp(-((t - seconds * 0.45) / (seconds * 0.3)) ** 2)
    tone = osc(f, rng, (1, 0.15, 0.3, 0.05, 0.15)) * drive
    tone *= np.clip(t / 0.4, 0, 1) * np.clip((seconds - t) / 0.4, 0, 1)
    return distant(tone, rng, 2800, 1.8, 0.45)


def bark(rng, f0=None, length=None):
    """One 'woof': a buzzy voice with a fast pitch rise-and-fall through dog-mouth formants."""
    length = length or rng.uniform(0.13, 0.22)
    m = int(length * SR)
    tt = np.arange(m) / SR
    f0 = f0 or rng.uniform(280, 420)
    pitch = f0 * (0.8 + 0.55 * np.sin(np.pi * np.clip(tt / length, 0, 1)) ** 0.7)
    voice = osc(pitch, rng, [1 / k for k in range(1, 18)])  # sawtooth-ish glottal buzz
    rough = noise(m, rng, band(400, 4000)) * 0.35
    x = voice + rough
    pad = int(0.05 * SR)
    x = np.concatenate([x, np.zeros(pad)])
    f1, f2, f3 = rng.uniform(550, 750), rng.uniform(1100, 1500), rng.uniform(2300, 2800)
    x = fft_filter(x, lambda f: peak(f1, 3, 6)(f) * peak(f2, 4, 4)(f) * peak(f3, 5, 2)(f) * band(200, 5000)(f))
    e = np.zeros(m + pad)
    e[:m] = (1 - np.exp(-tt / 0.006)) * np.exp(-tt / (length * 0.45))
    return x * e


def dog(rng):
    out = np.zeros(int(6 * SR))
    at = 0.1
    f0 = rng.uniform(260, 400)
    for _ in range(rng.integers(3, 6)):
        b = bark(rng, f0 * rng.uniform(0.92, 1.08))
        place(out, b * rng.uniform(0.7, 1.0), int(at * SR), wrap=False)
        at += rng.uniform(0.32, 0.6) if rng.random() < 0.75 else rng.uniform(0.9, 1.4)
    return distant(trim(out), rng, 2400, 1.5, 0.45)


def bird_note(rng, kind):
    d = {"chip": rng.uniform(0.03, 0.06), "sweep": rng.uniform(0.08, 0.16), "trill": rng.uniform(0.25, 0.45)}[kind]
    m = int(d * SR)
    tt = np.arange(m) / SR
    if kind == "chip":
        f = np.linspace(rng.uniform(5000, 6500), rng.uniform(3200, 4200), m)
    elif kind == "sweep":
        a, b = rng.uniform(2800, 4000), rng.uniform(4500, 7000)
        f = a + (b - a) * np.sin(np.pi * tt / d) if rng.random() < 0.5 else np.linspace(b, a, m)
    else:
        base = rng.uniform(3500, 5000)
        f = base + 900 * np.sign(np.sin(2 * np.pi * rng.uniform(18, 28) * tt))
        f = fft_filter(f - base, lp(120)) + base
    x = osc(f, rng, (1, 0.12))
    return x * np.sin(np.pi * tt / d) ** 1.5


def birds(rng):
    out = np.zeros(int(4 * SR))
    at = 0.05
    song = [rng.choice(["chip", "sweep", "trill"], p=[0.45, 0.4, 0.15]) for _ in range(rng.integers(4, 9))]
    for kind in song:
        s = bird_note(rng, kind)
        place(out, s * rng.uniform(0.6, 1.0), int(at * SR), wrap=False)
        at += len(s) / SR + rng.uniform(0.04, 0.22)
    # a second bird answering further off
    if rng.random() < 0.7:
        at += rng.uniform(0.2, 0.5)
        for _ in range(rng.integers(2, 5)):
            s = bird_note(rng, rng.choice(["chip", "sweep"]))
            place(out, s * 0.35, int(at * SR), wrap=False)
            at += len(s) / SR + rng.uniform(0.05, 0.2)
    return distant(trim(out), rng, 9000, 0.9, 0.25)


def horn(rng):
    out = np.zeros(int(3 * SR))
    fa, fb = rng.uniform(380, 440), rng.uniform(470, 530)
    at = 0.05
    for length in ([0.18, 0.55] if rng.random() < 0.5 else [0.9]):
        m = int(length * SR)
        f = np.ones(m)
        tt = np.arange(m) / SR
        h = (1, 0.5, 0.45, 0.3, 0.25, 0.15, 0.1)
        x = osc(f * fa, rng, h) + osc(f * fb, rng, h)
        x *= np.clip(tt / 0.01, 0, 1) * np.clip((length - tt) / 0.03, 0, 1)
        place(out, x, int(at * SR), wrap=False)
        at += length + 0.12
    return distant(trim(out), rng, 2200, 1.6, 0.45)


def main():
    os.makedirs(OUT, exist_ok=True)
    r = np.random.default_rng
    write("ThunderClose1", thunder(r(101), True, 7.5))
    write("ThunderClose2", thunder(r(102), True, 8.5))
    write("ThunderFar1", thunder(r(111), False, 8))
    write("ThunderFar2", thunder(r(112), False, 9))
    write("ThunderFar3", thunder(r(113), False, 7))
    write("CityDayLoop", city_bed(r(201), 40, 22, 0.32, 0.35))
    write("CityNightLoop", city_bed(r(202), 40, 7, 0.22, 0.25))
    write("CricketsLoop", crickets(r(203), 20))
    write("SirenWail", siren_wail(r(301)))
    write("SirenHiLo", siren_hilo(r(302)))
    write("DogBark1", dog(r(311)))
    write("DogBark2", dog(r(312)))
    write("Birds1", birds(r(321)))
    write("Birds2", birds(r(322)))
    write("Birds3", birds(r(323)))
    write("CarHorn1", horn(r(331)))
    write("CarHorn2", horn(r(332)))


if __name__ == "__main__":
    main()
