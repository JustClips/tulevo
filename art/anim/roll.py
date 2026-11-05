"""Combat rolls (forward, back, left, right) for the default R15 rig.

  python3 art/anim/roll.py [--preview]  -> art/out/anims/Tulevo_Roll{Forward,Back,Left,Right}

Like a real roll: a lunge step first with the feet planted (IK), hands reach for the ground,
drop onto the shoulder, roll across the back with the body loose (legs not together, arms
protecting), land on the feet in a staggered crouch (IK again) and stand. Forward/back rolls
go over one shoulder (tilted axis), not straight over the head like a wheel. In the air
phases every frame is shifted so the body just touches the ground.
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


def IK(drop=0.0, px=0.0, pz=0.0, feet=((1, 0.45, 0.0, 0), (-1, -0.45, 0.0, 0))):
    """Planted phase: pelvis offset and feet (leg side, x, z, foot pitch) on the ground."""
    return dict(drop=drop, px=px, pz=pz, feet=feet)


STANDING = IK()
ARMS_DOWN = dict(r_arm=(6, 4, 10), l_arm=(6, 4, 10))

# Forward shoulder roll (rolls over the right shoulder to the left hip).
FORWARD = [
    (0.0, K(), 0, STANDING),
    (0.14, K(torso=-30, head=-5, r_arm=(55, 10, 20), l_arm=(45, 10, 25)), 4,
     IK(0.7, pz=-0.25, feet=((1, 0.42, -1.05, 0), (-1, -0.45, 0.45, -35)))),
    (0.24, K(torso=-55, head=-35, head_turn=25, r_arm=(95, 12, 30), l_arm=(90, 15, 35)), 30,
     IK(0.95, pz=-0.45, feet=((1, 0.42, -1.05, 0), (-1, -0.45, 0.45, -45)))),
    (0.32, K(torso=-55, head=-45, head_turn=30, r_leg=(70, -80, 20), l_leg=(-5, -15, -40),
             r_arm=(100, 15, 60), l_arm=(95, 20, 50)), 95, None),
    (0.46, K(torso=-45, head=-40, head_turn=15, r_leg=(115, -135, 20), l_leg=(95, -120, 10),
             r_arm=(70, 25, 100), l_arm=(60, 30, 90)), 195, None),
    (0.58, K(torso=-45, head=-30, r_leg=(120, -140, 20), l_leg=(105, -130, 15),
             r_arm=(65, 30, 95), l_arm=(70, 20, 100)), 290, None),
    (0.7, K(torso=-40, head=-12, r_arm=(70, 12, 30), l_arm=(60, 15, 40)), 352,
     IK(0.95, feet=((1, 0.45, -0.25, 0), (-1, -0.45, 0.4, -30)))),
    (0.84, K(torso=-20, head=-2, r_arm=(30, 8, 25), l_arm=(25, 8, 25)), 360,
     IK(0.4, feet=((1, 0.45, -0.15, 0), (-1, -0.45, 0.2, -10)))),
    (1.0, K(**ARMS_DOWN), 360, IK(feet=((1, 0.45, 0.0, 0), (-1, -0.45, 0.05, 0)))),
]

# Back roll: step one foot back and sit down, rock onto the rounded back with the hands up
# by the ears, push the ground away over the shoulder, land crouched, stand.
BACK = [
    (0.0, K(), 0, STANDING),
    (0.14, K(torso=-15, head=-5, r_arm=(55, 10, 20), l_arm=(60, 10, 20)), 0,
     IK(0.8, pz=0.3, feet=((1, 0.45, -0.2, 0), (-1, -0.45, 0.95, -40)))),
    (0.26, K(torso=-30, head=-35, r_leg=(100, -125, 20), l_leg=(95, -120, 15),
             r_arm=(130, 15, 120), l_arm=(130, 15, 120)), 45, None),
    (0.4, K(torso=-40, head=-40, head_turn=-15, r_leg=(125, -140, 20), l_leg=(120, -138, 20),
            r_arm=(160, 15, 115), l_arm=(160, 15, 115)), 170, None),
    (0.54, K(torso=-38, head=-30, r_leg=(105, -125, 25), l_leg=(95, -120, 20),
             r_arm=(170, 12, 45), l_arm=(170, 12, 50)), 290, None),
    (0.68, K(torso=-35, head=-10, r_arm=(60, 8, 20), l_arm=(55, 8, 25)), 358,
     IK(0.95, feet=((1, 0.45, -0.1, 0), (-1, -0.45, 0.35, -25)))),
    (0.84, K(torso=-18, r_arm=(25, 6, 15), l_arm=(25, 6, 15)), 360,
     IK(0.4, feet=((1, 0.45, -0.05, 0), (-1, -0.45, 0.15, -8)))),
    (1.0, K(**ARMS_DOWN), 360, STANDING),
]


def side(s):
    """Side roll toward s (+1 right, -1 left): side lunge out with the lead leg, forearms tucked
    to the chest, drop onto the lead shoulder, roll across the back, come up staggered with
    the lead arm out for balance, stand."""
    tucked = (45, 0, 120)
    lead_up, other_up = (20, 50, 20), (35, 10, 30)
    r_up, l_up = (lead_up, other_up) if s > 0 else (other_up, lead_up)
    lead, trail = (1, -1) if s > 0 else (-1, 1)
    return [
        (0.0, K(), 0, STANDING),
        (0.14, K(torso=-20, head=-5, twist=8 * s, r_arm=tucked, l_arm=tucked), 12,
         IK(0.7, px=0.35 * s, feet=((lead, 1.3 * s, -0.05, 0), (trail, -0.45 * s, 0.1, -10)))),
        (0.24, K(torso=-35, head=-25, head_turn=-20 * s, r_arm=(50, 0, 125), l_arm=(50, 0, 125)), 55,
         IK(1.0, px=0.55 * s, feet=((lead, 1.3 * s, -0.05, 0), (trail, -0.45 * s, 0.1, -25)))),
        (0.34, K(torso=-35, head=-25, r_leg=(95, -120, 20), l_leg=(85, -110, 15),
                 r_arm=(50, 0, 125), l_arm=(55, 5, 120)), 110, None),
        (0.46, K(torso=-38, head=-25, r_leg=(115, -135, 20), l_leg=(105, -128, 20),
                 r_arm=(50, 5, 120), l_arm=(45, 0, 125)), 200, None),
        (0.58, K(torso=-35, head=-20, r_leg=(108, -130, 20), l_leg=(112, -132, 20),
                 r_arm=(45, 8, 112), l_arm=(48, 5, 115)), 290, None),
        (0.7, K(torso=-30, head=-5, r_arm=r_up, l_arm=l_up), 355,
         IK(0.9, feet=((lead, 0.5 * s, -0.15, 0), (trail, -0.45 * s, 0.25, -20)))),
        (0.84, K(torso=-15, r_arm=(15, 18, 15), l_arm=(15, 18, 15)), 360,
         IK(0.4, feet=((lead, 0.47 * s, -0.05, 0), (trail, -0.45 * s, 0.1, -5)))),
        (1.0, K(**ARMS_DOWN), 360, STANDING),
    ]


def axis_rot(axis, angle):
    a = np.asarray(axis, dtype=float)
    a /= np.linalg.norm(a)
    Kx = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(angle) * Kx + (1 - math.cos(angle)) * Kx @ Kx


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


def segment(keys, t):
    for i in range(len(keys) - 1):
        if keys[i][0] <= t <= keys[i + 1][0]:
            return i, (t - keys[i][0]) / max(1e-6, keys[i + 1][0] - keys[i][0])
    return len(keys) - 2, 1.0


def pose_key(keys, t):
    i, v = segment(keys, t)
    return A.mix(keys[i][1], keys[i + 1][1], L.smooth(v))


def angle_at(keys, t):
    i, v = segment(keys, t)
    return L.lerp(keys[i][2], keys[i + 1][2], v)


def ik_at(keys, t):
    """(weight, ik) where weight 1 = feet planted."""
    i, v = segment(keys, t)
    a, b = keys[i][3], keys[i + 1][3]
    u = L.smooth(v)
    w = L.lerp(1.0 if a else 0.0, 1.0 if b else 0.0, u)
    if a and b:
        ik = dict(drop=L.lerp(a["drop"], b["drop"], u), px=L.lerp(a["px"], b["px"], u), pz=L.lerp(a["pz"], b["pz"], u),
                  feet=tuple(tuple(L.lerp(x, y, u) for x, y in zip(fa, fb)) for fa, fb in zip(a["feet"], b["feet"])))
    else:
        ik = a or b
    return w, ik


def foot_ankle(x, z, pitch, side):
    rot = L.ry(-D(6) * side) @ L.rx(D(pitch))
    low = min((rot @ np.array([0, -L.SOLE, hz]))[1] for hz in (L.HEEL_Z, L.TOE_Z))
    return np.array([x, r15.GROUND - low, z]), rot


def blend(r_fk, r_ik, w):
    return r_fk @ L._partial(r_fk.T @ r_ik, w) if w > 0 else r_fk


def roll_frames(keys, axis, sign, fps=30):
    end = keys[-1][0]
    n = round(end * fps)
    frames = []
    for i in range(n + 1):
        t = end * i / n
        k = A.loosen(lambda tt: pose_key(keys, tt), t, end)
        poses = A.to_poses(k)
        rot = axis_rot(axis, sign * D(angle_at(keys, t)))
        poses["LowerTorso"] = ((0, 0, 0), rot)
        fk_shift = r15.GROUND - lowest(poses)
        w, ik = ik_at(keys, t)
        if w > 0:
            pos = (ik["px"] * w, L.lerp(fk_shift, -ik["drop"], w), ik["pz"] * w)
            poses["LowerTorso"] = (pos, rot)
            lt = L.lt_frame_of(pos, rot)
            for side, x, z, pitch in ik["feet"]:
                pre = "Right" if side > 0 else "Left"
                ankle, frot = foot_ankle(x, z, pitch, side)
                R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, frot, side)
                for part, r in ((pre + "UpperLeg", R_ul), (pre + "LowerLeg", R_ll), (pre + "Foot", R_f)):
                    poses[part] = ((0, 0, 0), blend(np.asarray(poses[part][1]), r, w))
        else:
            poses["LowerTorso"] = ((0, fk_shift, 0), rot)
        frames.append((t, poses))
    return frames


def main():
    os.makedirs(L.OUT, exist_ok=True)
    tilt = D(25)
    clips = {
        # forward: tip the top forward about X, axis turned so it goes over the right shoulder
        "Tulevo_RollForward": roll_frames(FORWARD, (math.cos(tilt), 0, -math.sin(tilt)), -1),
        "Tulevo_RollBack": roll_frames(BACK, (math.cos(tilt), 0, math.sin(tilt)), 1),
        "Tulevo_RollRight": roll_frames(side(1), (math.sin(D(12)), 0, math.cos(D(12))), -1),
        "Tulevo_RollLeft": roll_frames(side(-1), (-math.sin(D(12)), 0, math.cos(D(12))), 1),
    }
    for name, frames in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(L.sequence(name, frames, priority=1, loop=False))
        print(name, len(frames), "frames")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
