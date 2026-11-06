"""Item-use and phone sounds -> art/sounds/*.ogg

  python3 tools/use_sounds.py && python3 tools/upload_sounds.py

Built from real CC0 recordings in art/sounds/source/foley/ (see SOURCES.md there), laid out on
the use animation's beats (art/anim/use_items.py) so they line up with what the hands do:

  UseDrinkBottle   mead, 2.0 s: cap twisted off, bottle lifted, gulps while it's at the mouth
  UseDrinkCan      chaser, 1.5 s: can cracked open (fizz), gulps
  UseMedkit        first-aid kit, 4.0 s: zip open, bandage packet torn, bandage wrapped round
                   (cloth rubbing in time with the hand), strap pressed shut
  PhoneOpen / PhoneClose   phone out of the pocket + a soft two-note chime (up / down)

If an item's Use.Time changes, re-time its layout here too.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from gun_sounds import SR, add, band, decay, fade_out, fft_filter, hp, limit, load, lp, seconds, write  # noqa: E402

FOLEY = os.path.join(os.path.dirname(__file__), "..", "art", "sounds", "source", "foley")


def clip(name, start=None, length=None, gain=1.0):
    """A recording (mono), starting just before its first loud bit, RMS-normalised."""
    x = load(os.path.join(FOLEY, name + ".flac")).mean(1)
    x = fft_filter(x, hp(60, 3))
    a = np.abs(x)
    if start is None:
        first = np.nonzero(a > a.max() * 0.05)[0]
        start = max(0, (first[0] if len(first) else 0) / SR - 0.01)
    x = x[seconds(start):]
    if length is not None:
        x = fade_out(x[: seconds(length)], min(0.08, length / 4))
    rms = np.sqrt((x ** 2).mean()) + 1e-9
    return x / rms * 0.08 * gain


def finish(out, threshold=0.45):
    return limit(out, threshold)


def drink_bottle():
    out = np.zeros(seconds(2.0))
    add(out, clip("bottle_open_04", gain=0.9), 0.0)          # cap twisted off
    add(out, clip("bottle_shake_04", length=0.35, gain=0.35), 0.3)  # liquid moves as it tips up
    add(out, clip("swallow_02", gain=1.0), 0.68)             # 0.33 of the clip: at the mouth
    add(out, clip("swallow_04", gain=0.9), 1.2)
    return finish(out)


def can_open(rng):
    """Ring-pull crack + fizz (made here: no CC0 recording of a can)."""
    n = seconds(0.6)
    out = np.zeros(n)
    k = rng.standard_normal(seconds(0.012)) * decay(seconds(0.012), 0.0012)
    add(out, fft_filter(k, band(1500, 9000)) * 3.0, 0.0)
    k2 = rng.standard_normal(seconds(0.02)) * decay(seconds(0.02), 0.002)
    add(out, fft_filter(k2, band(800, 6000)) * 2.0, 0.035)
    fizz = rng.standard_normal(n) * decay(n, 0.12, 0.004)
    fizz *= 1 + 0.6 * (rng.random(n) < 0.002)  # bubbles popping
    add(out, fft_filter(fizz, band(3000, 12000)) * 0.6, 0.03)
    return out / (np.abs(out).max() + 1e-9) * 0.35


def drink_can(rng):
    out = np.zeros(seconds(1.5))
    add(out, can_open(rng), 0.0)
    add(out, clip("swallow_03", gain=1.0), 0.5)
    add(out, clip("swallow_01", gain=0.9), 0.95)
    return finish(out)


def medkit():
    out = np.zeros(seconds(4.0))
    add(out, clip("zipper", gain=0.8), 0.35)                 # kit unzipped as it comes up
    add(out, clip("paper_rip", length=0.5, gain=0.9), 1.0)   # bandage packet torn
    # wrapping: cloth rubbing while the hand circles the chest (rub beats 1.2 - 3.4 s)
    add(out, clip("cloth_01", length=0.9, gain=0.9), 1.3)
    add(out, clip("cloth_03", length=0.8, gain=0.85), 2.05)
    add(out, clip("cloth_02", length=0.7, gain=0.8), 2.7)
    add(out, clip("velcro_03", length=0.45, gain=0.55), 3.4)  # strap / tape pressed shut
    return finish(out)


def chime(notes, gap):
    n = seconds(0.5)
    out = np.zeros(n)
    for i, f in enumerate(notes):
        m = seconds(0.3)
        t = np.arange(m) / SR
        tone = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t) + 0.08 * np.sin(2 * np.pi * 3 * f * t)
        add(out, tone * decay(m, 0.07, 0.003) * (0.8 if i else 1.0), i * gap)
    return fft_filter(out, lp(7000))


def whoosh(rng, up):
    n = seconds(0.3)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    env = np.sin(np.pi * np.clip(t / 0.28, 0, 1)) ** 2
    blocks = 12
    out = np.zeros(n)
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        frac = b / (blocks - 1)
        fc = 600 + 2200 * (frac if up else 1 - frac)
        out[a:z] = fft_filter(x, band(fc * 0.6, fc * 1.6))[a:z]
    return out * env


def phone(rng, opening):
    out = np.zeros(seconds(0.7))
    add(out, clip("cloth_05", length=0.3, gain=0.5), 0.0)  # out of / into the pocket
    w = whoosh(rng, opening)
    add(out, w / (np.abs(w).max() + 1e-9) * 0.12, 0.05)
    # E6 -> B6 opening, B5 -> E5 closing
    c = chime([1318.5, 1975.5] if opening else [987.8, 659.3], 0.07)
    add(out, c / (np.abs(c).max() + 1e-9) * 0.2, 0.16 if opening else 0.1)
    return finish(out, 0.6)


def main():
    rng = np.random.default_rng(42)
    write("UseDrinkBottle", drink_bottle())
    write("UseDrinkCan", drink_can(rng))
    write("UseMedkit", medkit())
    write("PhoneOpen", phone(rng, True))
    write("PhoneClose", phone(rng, False))


if __name__ == "__main__":
    main()
