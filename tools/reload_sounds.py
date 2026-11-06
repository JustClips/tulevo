"""Rifle reload sounds -> art/sounds/*.ogg

  python3 tools/reload_sounds.py && python3 tools/upload_sounds.py

Cut from real CC0 recordings (art/sounds/source/foley, SOURCES.md). Server/Weapons/GunModel
plays each one on the beat it belongs to (RELOAD_BEATS), from the gun, so everyone nearby
hears them and a cancelled reload stops where it is:

  ReloadMagOut     mag release click, empty mag out    (grab)
  ReloadMagSeat    new mag clacks home                 (seated)

GTA style: two clean clicks, nothing else.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from gun_sounds import fade_out, fft_filter, hp, limit, load, seconds, write  # noqa: E402

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


def treat(x):
    """Clean: just the click, no rumble, no hiss, nothing else."""
    x = fft_filter(x, hp(250, 2))
    return limit(x, 0.55)


def main():
    # GTA style: simple and clean. Mag out click, then the new mag clacks home. (Dev 2026-11-06:
    # the full set with ground clatter, velcro and charging handle was too much.)
    write("ReloadMagOut", treat(cut("rifle_reload", 0.22, 0.36)))
    write("ReloadMagSeat", treat(cut("rifle_reload", 1.26, 1.42)))


if __name__ == "__main__":
    main()
