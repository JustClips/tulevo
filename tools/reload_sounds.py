"""Rifle reload sounds -> art/sounds/*.ogg

  python3 tools/reload_sounds.py && python3 tools/upload_sounds.py

Cut from real CC0 recordings (art/sounds/source/foley, SOURCES.md). Server/Weapons/GunModel
plays each one on the beat it belongs to (RELOAD_BEATS), from the gun, so everyone nearby
hears them and a cancelled reload stops where it is:

  ReloadMagOut     mag release pressed, empty mag slides out       (grab)
  ReloadMagDrop    the empty mag clatters on the ground            (when it lands)
  ReloadPouch      vest pouch lid ripped open (velcro)             (flap)
  ReloadMagIn      full mag pushed up into the well                (just before partial)
  ReloadMagSeat    slapped home, click                             (seated)
  ReloadCharge     charging handle pulled back and let go          (1.97 s)

Same muffled treatment as the carbine shot (GTA 5 feel): no hiss, a bit of metal body.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from gun_sounds import SR, add, fade_out, fft_filter, hp, limit, load, lp, seconds, write  # noqa: E402

FOLEY = os.path.join(os.path.dirname(__file__), "..", "art", "sounds", "source", "foley")
_cache = {}


def src(name):
    if name not in _cache:
        _cache[name] = load(os.path.join(FOLEY, name + ".flac")).mean(1)
    return _cache[name]


def cut(name, a, b):
    x = src(name)[seconds(a):seconds(b)].copy()
    n = min(len(x) // 4, seconds(0.004))
    x[:n] *= np.linspace(0, 1, n)
    return fade_out(x, min(0.04, (b - a) / 3))


def treat(x, tone=5500):
    x = fft_filter(x, hp(120, 2))
    x = fft_filter(x, lp(tone, 2))
    x = x + 0.6 * fft_filter(x, lambda f: 1 / (1 + ((f - 700) / 400) ** 2))  # metal body
    return limit(x, 0.5)


def main():
    write("ReloadMagOut", treat(cut("rifle_reload", 0.13, 0.46)))
    write("ReloadMagIn", treat(cut("rifle_reload", 1.025, 1.22)))
    write("ReloadMagSeat", treat(cut("rifle_reload", 1.22, 1.56)))
    drop = cut("equipment_clicks", 3.72, 4.15)
    write("ReloadMagDrop", treat(drop, 3500))
    pouch = load(os.path.join(FOLEY, "velcro_03.flac")).mean(1)
    write("ReloadPouch", treat(fade_out(pouch[: seconds(0.35)], 0.06), 7000))
    charge = np.zeros(seconds(0.45))
    add(charge, cut("equipment_clicks", 2.04, 2.13), 0.04)   # pulled back (2.01)
    add(charge, cut("equipment_clicks", 2.37, 2.56), 0.11)   # slams forward (2.08)
    write("ReloadCharge", treat(charge))


if __name__ == "__main__":
    main()
