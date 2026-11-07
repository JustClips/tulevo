"""Pushing a door open with one hand (arms only), for the default R15 rig:

  python3 art/anim/door_push.py [--preview]
    -> art/out/anims/Tulevo_DoorPush.rbxmx      (right hand, empty hands: 0.9 s)
       art/out/anims/Tulevo_DoorPushLeft.rbxmx  (left hand, a gun in the right: 0.9 s)
  then python3 tools/upload_anims.py

Client/CityDoors plays it when you walk up to a closed Swing door or gate you're facing. The
hand comes up flat, palm forward and fingers up, meets the push bar about CONTACT_AT seconds in
(the door starts swinging then), keeps pressing while you walk through and drops back to the
side. Only the pushing arm is keyed, so walking and the gun hold keep the rest of the body.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gun as G  # noqa: E402
import locomotion as L  # noqa: E402
import use_items as U  # noqa: E402

D = math.radians
LENGTH = 0.9
CONTACT_AT = 0.2
# Palm forward (-Z), fingers up, in UpperTorso space; one per side.
PALM = {1: np.array([[0, 0, 1], [0, -1, 0], [1, 0, 0]], dtype=float),
        -1: np.array([[0, 0, -1], [0, -1, 0], [-1, 0, 0]], dtype=float)}


def clip(s):
    """Hand path in UpperTorso space (x right, y up, front = -Z): reach to the bar at chest
    height, a short press as the door gives, a held push, then the arm drops."""
    keys = [
        (CONTACT_AT, U.frame(PALM[s], (0.72 * s, 0.22, -1.42))),
        (0.32, U.frame(PALM[s], (0.70 * s, 0.2, -1.58))),
        (0.5, U.frame(PALM[s], (0.70 * s, 0.18, -1.52))),
        (0.6, U.frame(PALM[s], (0.74 * s, 0.1, -1.4))),
    ]
    hand = U.path(keys)

    def target(t):
        return hand(t), 0.4
    return U.solve(LENGTH, {s: target}, lambda t: 0.0, rest_in=(0.0, CONTACT_AT), rest_out=(0.6, LENGTH))


def main():
    os.makedirs(L.OUT, exist_ok=True)
    for name, s in (("Tulevo_DoorPush", 1), ("Tulevo_DoorPushLeft", -1)):
        frames, worst = clip(s)
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, frames, list(G.ARM_PARTS[s]), False, priority=3))
        print(f"{name}: {len(frames)} frames {frames[-1][0]:.2f}s  contact at {CONTACT_AT}s  worst hand miss {worst:.3f} studs")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
