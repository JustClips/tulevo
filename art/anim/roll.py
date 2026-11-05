"""Combat rolls (forward, back, left, right) for the default R15 rig.

  python3 art/anim/roll.py [--preview]  -> art/out/anims/Tulevo_Roll{Forward,Back,Left,Right}

Dive low, tuck into a ball (knees to chest, chin in, arms wrapped), turn a full circle about
the roll axis, unfold and come up standing. The whole body is turned at the root joint, and
every frame is shifted up/down so the lowest point of the body just touches the ground.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import air as A  # noqa: E402
import locomotion as L  # noqa: E402
import r15  # noqa: E402

D = math.radians
DURATION = 0.75

STAND = A.key()
TUCK = A.key(torso=-35, head=-25, r_leg=(115, -135, 20), l_leg=(110, -130, 20),
             r_arm=(70, 10, 100), l_arm=(70, 10, 100))
SIDE_TUCK = A.key(torso=-25, head=-15, r_leg=(100, -125, 15), l_leg=(95, -120, 15),
                  r_arm=(55, 5, 110), l_arm=(55, 5, 110))


def tuck_amount(u):
    if u < 0.2:
        return L.smooth(u / 0.2)
    if u < 0.7:
        return 1.0
    return 1 - L.smooth((u - 0.7) / 0.3)


def spin(u):
    """Roll angle progress 0..1: slow start (dive), fast middle, settles at the end."""
    return L.smooth(min(1, max(0, (u - 0.05) / 0.8)))


def lowest(poses):
    f = r15.solve({k: (v[0], np.asarray(v[1])) for k, v in poses.items()})
    pts = []
    for foot in ("RightFoot", "LeftFoot"):
        for sx in (-0.3, 0.3):
            for sz in (L.HEEL_Z, L.TOE_Z):
                pts.append((f[foot] @ np.array([sx, -0.156, sz, 1]))[1])
    for part, r in (("Head", 0.6), ("UpperTorso", 0.8), ("LowerTorso", 0.5), ("RightHand", 0.2),
                    ("LeftHand", 0.2), ("RightLowerLeg", 0.35), ("LeftLowerLeg", 0.35),
                    ("RightUpperArm", 0.4), ("LeftUpperArm", 0.4), ("RightUpperLeg", 0.4), ("LeftUpperLeg", 0.4)):
        pts.append(f[part][1, 3] - r)
    return min(pts)


def roll_frames(axis, sign, tuck, fps=30):
    n = round(DURATION * fps)
    frames = []
    for i in range(n + 1):
        u = i / n
        k = A.mix(STAND, tuck, L.smooth(tuck_amount(u)))
        poses = A.to_poses(k)
        a = sign * 2 * math.pi * spin(u)
        rot = L.rx(a) if axis == "x" else L.rz(a)
        poses["LowerTorso"] = ((0, 0, 0), rot)
        shift = r15.GROUND - lowest(poses)
        # never float above standing height
        shift = min(shift, 0.0) if u < 0.02 or u > 0.98 else shift
        poses["LowerTorso"] = ((0, shift, 0), rot)
        frames.append((DURATION * u, poses))
    return frames


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        # Rx(-) tips the top forward, Rz(-) tips it to the right
        "Tulevo_RollForward": roll_frames("x", -1, TUCK),
        "Tulevo_RollBack": roll_frames("x", 1, TUCK),
        "Tulevo_RollRight": roll_frames("z", -1, SIDE_TUCK),
        "Tulevo_RollLeft": roll_frames("z", 1, SIDE_TUCK),
    }
    for name, frames in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(L.sequence(name, frames, priority=1, loop=False))
        print(name, len(frames), "frames")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
