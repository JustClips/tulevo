"""Footwork clips: turn-in-place steps while aiming, the sprint skid-stop and the quick-turn pivot.

  python3 art/anim/steps.py [--preview]  -> art/out/anims/Tulevo_TurnStep{Left,Right},
                                            Tulevo_SprintStop, Tulevo_Pivot

TurnStep: legs only (the hips and upper body come from the idle and the aim). While you aim
standing still the feet stay planted as the body turns (Client/Weapons/GunPose counter-turns
the hips); past a threshold the game plays a step and lets the hips catch up, so one foot
lifts and the other pivots, like GTA. Left = turning left, the left foot steps first.

SprintStop: letting go of the stick mid-sprint plants the front heel, sits the hips down and
leans back while the body skids, then stands (Client/Movement/Moves/SprintStop).

Pivot: reversing direction while running plants, dips and drives off the other way; the game
turns the body round during it (Client/Movement/Moves/Pivot).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import air as A  # noqa: E402
import gun as G  # noqa: E402
import locomotion as L  # noqa: E402
import r15  # noqa: E402

D = math.radians
K = A.key
LEGS = ["RightUpperLeg", "RightLowerLeg", "RightFoot", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot"]
FULL = ["LowerTorso", "UpperTorso", "Head", *G.ARMS, *LEGS]


def foot(side, x, z, pitch=0.0, lift=0.0):
    """Ankle position + foot rotation for a foot at (x, z) on the ground, raised by lift."""
    rot = L.ry(-D(6) * side) @ L.rx(D(pitch))
    low = min((rot @ np.array([0, -L.SOLE, hz]))[1] for hz in (L.HEEL_Z, L.TOE_Z))
    return np.array([x, r15.GROUND - low + lift, z]), rot


def legs_into(poses, pos, rot, feet):
    lt = L.lt_frame_of(pos, rot)
    for side, x, z, pitch, lift in feet:
        pre = "Right" if side > 0 else "Left"
        ankle, frot = foot(side, x, z, pitch, lift)
        R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, frot, side)
        poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
        poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
        poses[pre + "Foot"] = ((0, 0, 0), R_f)


def bump(t, t0, t1):
    """0 -> 1 -> 0 over [t0, t1] (smooth)."""
    if t <= t0 or t >= t1:
        return 0.0
    return math.sin(math.pi * (t - t0) / (t1 - t0)) ** 2


# ------------------------------------------------------------------------- turn steps
TURN_TIME = 0.42


def turn_step(lead, fps=30):
    """lead = +1 right foot first (turning right), -1 left foot first (turning left)."""
    n = round(TURN_TIME * fps)
    frames = []
    for i in range(n + 1):
        t = TURN_TIME * i / n
        a = bump(t, 0.0, 0.25)          # lead foot
        b = bump(t, 0.15, TURN_TIME)    # trail foot
        feet = []
        for side in (1, -1):
            up = a if side == lead else b
            # the stepping foot lifts on its toes first and swings a touch out
            feet.append((side, side * (0.5 + 0.06 * up), -0.04 * up, -12 * up, 0.2 * up))
        poses = {}
        legs_into(poses, (0, 0, 0), np.eye(3), feet)
        frames.append((t, poses))
    return frames


# ------------------------------------------------------------------------- sprint stop
def keyed(keys, fps=30):
    """keys: [(t, upper key, drop, lean_back_deg, feet[(side, x, z, pitch, lift)])]."""
    end = keys[-1][0]
    n = max(2, round(end * fps))

    def at(t):
        t = min(max(t, 0.0), end)
        for (t0, *a), (t1, *b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = L.smooth((t - t0) / max(1e-6, t1 - t0))
                up = A.mix(a[0], b[0], u)
                drop = L.lerp(a[1], b[1], u)
                feet = [tuple(L.lerp(x, y, u) for x, y in zip(fa, fb)) for fa, fb in zip(a[2], b[2])]
                return up, drop, feet
        k = keys[-1]
        return k[1], k[2], k[3]

    frames = []
    for i in range(n + 1):
        t = end * i / n
        _, drop, feet = at(t)
        poses = A.to_poses(A.loosen(lambda tt: at(tt)[0], t, end))
        pos = (0, -drop, 0)
        poses["LowerTorso"] = (pos, np.eye(3))
        legs_into(poses, pos, np.eye(3), feet)
        frames.append((t, poses))
    return frames


ARMS_DOWN = dict(r_arm=(6, 4, 10), l_arm=(6, 4, 10))
STAND_FEET = [(1, 0.5, 0.0, 0, 0), (-1, -0.5, 0.05, 0, 0)]

SPRINT_STOP = [
    # still going: leaning into the sprint, right foot reaching forward
    (0.0, K(torso=-14, head=6, r_arm=(-25, 8, 70), l_arm=(45, 8, 85)), 0.12,
     [(1, 0.45, -0.55, 12, 0.08), (-1, -0.45, 0.55, -25, 0.0)]),
    # heel digs in: hips sit down, chest leans back, arms come forward for balance
    (0.12, K(torso=8, head=-4, r_arm=(40, 22, 45), l_arm=(55, 22, 40)), 0.42,
     [(1, 0.5, -0.8, 22, 0.0), (-1, -0.5, 0.6, -30, 0.0)]),
    # skid
    (0.32, K(torso=5, head=-2, r_arm=(30, 18, 40), l_arm=(42, 18, 38)), 0.36,
     [(1, 0.5, -0.72, 14, 0.0), (-1, -0.5, 0.55, -24, 0.0)]),
    # stand up, back foot comes in
    (0.48, K(torso=-2, r_arm=(12, 8, 22), l_arm=(14, 8, 22)), 0.1,
     [(1, 0.5, -0.25, 0, 0.0), (-1, -0.5, 0.2, -6, 0.06)]),
    (0.62, K(**ARMS_DOWN), 0.0, STAND_FEET),
]

PIVOT = [
    # running into the plant
    (0.0, K(torso=-14, head=6, r_arm=(35, 8, 80), l_arm=(-20, 8, 70)), 0.1,
     [(1, 0.5, -0.3, 6, 0.0), (-1, -0.5, 0.4, -20, 0.05)]),
    # plant wide and low, arms out as the body swings round
    (0.12, K(torso=-22, head=4, r_arm=(25, 45, 40), l_arm=(25, 45, 40), twist=-6), 0.45,
     [(1, 0.62, -0.2, 0, 0.0), (-1, -0.62, 0.3, -18, 0.0)]),
    # drive off the other way
    (0.26, K(torso=-26, head=8, r_arm=(-20, 10, 70), l_arm=(45, 10, 85), twist=4), 0.32,
     [(1, 0.55, 0.25, -25, 0.0), (-1, -0.5, -0.45, 10, 0.18)]),
    (0.4, K(torso=-16, head=6, r_arm=(-15, 8, 75), l_arm=(35, 8, 80)), 0.12,
     [(1, 0.5, 0.45, -28, 0.08), (-1, -0.5, -0.5, 8, 0.0)]),
]


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        "Tulevo_TurnStepLeft": (turn_step(-1), LEGS),
        "Tulevo_TurnStepRight": (turn_step(1), LEGS),
        "Tulevo_SprintStop": (keyed(SPRINT_STOP), FULL),
        "Tulevo_Pivot": (keyed(PIVOT), FULL),
    }
    for name, (frames, keys) in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, frames, keys, False, priority=1))
        print(f"{name}: {len(frames)} frames {frames[-1][0]:.2f}s")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
