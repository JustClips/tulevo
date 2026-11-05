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
K = A.key

# Each roll is a list of (time, pose key, roll angle in degrees). Pose and angle are eased
# between keys separately, so the body can be mid-tuck while the turn speeds up.

# Forward (shoulder) roll, like in real life: crouch and reach both hands to the ground in
# front, plant them and bend the elbows, tuck the chin, roll over the rounded back with the
# knees hugged in, land on the feet low with the arms reaching forward, then stand up.
FORWARD = [
    (0.0, K(), 0),
    (0.12, K(torso=-40, head=-10, r_leg=(70, -100, 30), l_leg=(66, -96, 30), r_arm=(70, 8, 10), l_arm=(70, 8, 10)), 15),
    (0.22, K(torso=-55, head=-45, r_leg=(85, -110, 25), l_leg=(82, -108, 25), r_arm=(110, 10, 55), l_arm=(110, 10, 55)), 70),
    (0.36, K(torso=-45, head=-40, r_leg=(120, -140, 20), l_leg=(118, -140, 20), r_arm=(70, 5, 110), l_arm=(70, 5, 110)), 180),
    (0.5, K(torso=-45, head=-35, r_leg=(122, -140, 20), l_leg=(120, -140, 20), r_arm=(75, 5, 105), l_arm=(75, 5, 105)), 290),
    (0.62, K(torso=-40, head=-15, r_leg=(100, -130, 30), l_leg=(98, -128, 30), r_arm=(80, 8, 30), l_arm=(80, 8, 30)), 350),
    (0.75, K(torso=-25, head=0, r_leg=(55, -80, 20), l_leg=(52, -78, 20), r_arm=(40, 8, 25), l_arm=(40, 8, 25)), 360),
    (0.92, K(r_arm=(6, 4, 10), l_arm=(6, 4, 10)), 360),
]

# Back roll: sit down low with the arms forward for balance, rock back onto the rounded back,
# bring the hands up beside the ears (palms back), roll over the shoulders and push the
# ground away with the hands, land on the feet crouched, stand.
BACK = [
    (0.0, K(), 0),
    (0.12, K(torso=-12, head=-5, r_leg=(85, -110, 25), l_leg=(85, -110, 25), r_arm=(60, 8, 20), l_arm=(60, 8, 20)), 0),
    (0.24, K(torso=-35, head=-40, r_leg=(110, -130, 20), l_leg=(110, -130, 20), r_arm=(150, 15, 130), l_arm=(150, 15, 130)), 70),
    (0.4, K(torso=-40, head=-40, r_leg=(125, -140, 20), l_leg=(125, -140, 20), r_arm=(160, 15, 110), l_arm=(160, 15, 110)), 200),
    (0.55, K(torso=-38, head=-30, r_leg=(100, -125, 25), l_leg=(100, -125, 25), r_arm=(170, 12, 40), l_arm=(170, 12, 40)), 300),
    (0.68, K(torso=-35, head=-10, r_leg=(90, -120, 30), l_leg=(90, -120, 30), r_arm=(60, 8, 20), l_arm=(60, 8, 20)), 360),
    (0.8, K(torso=-20, r_leg=(50, -75, 15), l_leg=(50, -75, 15), r_arm=(25, 6, 15), l_arm=(25, 6, 15)), 360),
    (0.95, K(r_arm=(6, 4, 10), l_arm=(6, 4, 10)), 360),
]


def side(sign):
    """Sideways combat roll toward sign (+1 right, -1 left): drop low and lean in with the
    forearms tucked to the chest, put the shoulder down, roll across the back with the knees
    tucked, come up on the feet with the leading arm out for balance, stand."""
    lead_out = (20, 55, 20)
    tucked = (45, 0, 120)
    r_up = lead_out if sign > 0 else (30, 8, 25)
    l_up = lead_out if sign < 0 else (30, 8, 25)
    return [
        (0.0, K(), 0),
        (0.12, K(torso=-25, head=-5, twist=10 * sign, r_leg=(70, -100, 25), l_leg=(70, -100, 25), r_arm=tucked, l_arm=tucked), 20),
        (0.24, K(torso=-35, head=-20, r_leg=(100, -125, 20), l_leg=(100, -125, 20), r_arm=(50, 0, 125), l_arm=(50, 0, 125)), 95),
        (0.4, K(torso=-38, head=-25, r_leg=(115, -135, 20), l_leg=(115, -135, 20), r_arm=(50, 0, 125), l_arm=(50, 0, 125)), 200),
        (0.54, K(torso=-35, head=-20, r_leg=(110, -132, 20), l_leg=(110, -132, 20), r_arm=(45, 5, 115), l_arm=(45, 5, 115)), 290),
        (0.66, K(torso=-30, head=-5, r_leg=(90, -120, 30), l_leg=(90, -120, 30), r_arm=r_up, l_arm=l_up), 355),
        (0.8, K(torso=-15, r_leg=(45, -70, 15), l_leg=(45, -70, 15), r_arm=(15, 20, 15), l_arm=(15, 20, 15)), 360),
        (0.95, K(r_arm=(6, 4, 10), l_arm=(6, 4, 10)), 360),
    ]


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


def sample(keys, t):
    for (t0, a, g0), (t1, b, g1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = L.smooth((t - t0) / max(1e-6, t1 - t0))
            # angle eases linearly between keys so the turn keeps its speed through the roll
            v = (t - t0) / max(1e-6, t1 - t0)
            return A.mix(a, b, u), L.lerp(g0, g1, v)
    return keys[-1][1], keys[-1][2]


def roll_frames(keys, axis, sign, fps=30):
    end = keys[-1][0]
    n = round(end * fps)
    frames = []
    for i in range(n + 1):
        t = end * i / n
        k, ang = sample(keys, t)
        poses = A.to_poses(k)
        a = sign * D(ang)
        rot = L.rx(a) if axis == "x" else L.rz(a)
        poses["LowerTorso"] = ((0, 0, 0), rot)
        shift = r15.GROUND - lowest(poses)  # body (feet, back or shoulders) just touches the ground
        poses["LowerTorso"] = ((0, shift, 0), rot)
        frames.append((t, poses))
    return frames


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        # Rx(-) tips the top forward, Rz(-) tips it to the right
        "Tulevo_RollForward": roll_frames(FORWARD, "x", -1),
        "Tulevo_RollBack": roll_frames(BACK, "x", 1),
        "Tulevo_RollRight": roll_frames(side(1), "z", -1),
        "Tulevo_RollLeft": roll_frames(side(-1), "z", 1),
    }
    for name, frames in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(L.sequence(name, frames, priority=1, loop=False))
        print(name, len(frames), "frames")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
