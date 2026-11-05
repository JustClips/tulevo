"""GTA-style jump, fall and landing clips for the default R15 rig.

  python3 art/anim/air.py [--preview]  -> art/out/anims/Tulevo_Jump / _Fall / _Land (.rbxmx, .gif)

Jump: running take-off (one knee driven up, back leg trailing, arms opposite), one-shot that
ends in the airborne pose. Fall: loop, legs bent, arms out for balance, small flail.
Land: one-shot, feet planted (IK) while the hips drop and spring back.
Key poses are joint angles in degrees: thigh/arm X + = forward, knee X - = bend,
elbow X + = bend, arm Z + = out to the side (mirrored for the left), torso X - = lean forward.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locomotion as L  # noqa: E402
import r15  # noqa: E402

D = math.radians


def key(torso=0.0, head=0.0, r_leg=(0, 0, 0), l_leg=(0, 0, 0), r_arm=(0, 0, 0), l_arm=(0, 0, 0), twist=0.0):
    """r_leg = (thigh, knee, foot); r_arm = (shoulder fwd, out, elbow)."""
    return dict(torso=torso, head=head, r_leg=r_leg, l_leg=l_leg, r_arm=r_arm, l_arm=l_arm, twist=twist)


def mix(a, b, u):
    out = {}
    for k in a:
        if isinstance(a[k], tuple):
            out[k] = tuple(L.lerp(x, y, u) for x, y in zip(a[k], b[k]))
        else:
            out[k] = L.lerp(a[k], b[k], u)
    return out


def to_poses(k):
    I = np.eye(3)
    poses = {
        "LowerTorso": ((0, 0, 0), L.ry(D(k["twist"]) * 0.5)),
        "UpperTorso": ((0, 0, 0), L.rx(D(k["torso"])) @ L.ry(-D(k["twist"]))),
        "Head": ((0, 0, 0), L.rx(D(k["head"] - k["torso"] * 0.6))),
    }
    for side, pre, leg, arm in ((1, "Right", k["r_leg"], k["r_arm"]), (-1, "Left", k["l_leg"], k["l_arm"])):
        poses[pre + "UpperLeg"] = ((0, 0, 0), L.rx(D(leg[0])) @ L.rz(D(3) * side))
        poses[pre + "LowerLeg"] = ((0, 0, 0), L.rx(D(leg[1])))
        poses[pre + "Foot"] = ((0, 0, 0), L.rx(D(leg[2])))
        poses[pre + "UpperArm"] = ((0, 0, 0), L.rz(D(arm[1]) * side) @ L.rx(D(arm[0])) @ L.ry(-D(8) * side))
        poses[pre + "LowerArm"] = ((0, 0, 0), L.rx(D(arm[2])))
        poses[pre + "Hand"] = ((0, 0, 0), I)
    return poses


def track(keys, fps=30):
    """keys: [(time, key)], eased between neighbours."""
    end = keys[-1][0]
    n = max(2, round(end * fps))
    frames = []
    for i in range(n + 1):
        t = end * i / n
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                frames.append((t, to_poses(mix(a, b, L.smooth((t - t0) / max(1e-6, t1 - t0))))))
                break
    return frames


# Full GTA-style jumps. Every clip moves the whole time: legs push off, drive, fold and reach
# for the ground; arms swing with the push and then open out and keep moving for balance.

# Standing: starts from the crouch of Tulevo_JumpPrep, explodes up with the arms thrown up,
# knees come up, arms open out, legs reach down again.
JUMP_STAND = [
    (0.0, key(torso=-22, head=10, r_leg=(55, -95, 38), l_leg=(55, -95, 38), r_arm=(-45, 8, 25), l_arm=(-45, 8, 25))),
    (0.1, key(torso=-4, head=2, r_leg=(4, -6, -35), l_leg=(4, -6, -35), r_arm=(105, 22, 15), l_arm=(105, 22, 15))),
    (0.28, key(torso=-6, head=0, r_leg=(62, -100, 8), l_leg=(56, -95, 8), r_arm=(45, 55, 30), l_arm=(45, 55, 30))),
    (0.5, key(torso=-3, head=0, r_leg=(22, -32, 2), l_leg=(18, -28, 2), r_arm=(20, 62, 25), l_arm=(20, 62, 25))),
]

# Walking / jogging: one-leg take-off. Right knee drives up, left leg pushes off the toes,
# left arm punches forward, then the legs scissor and the arms open out.
JUMP = [
    (0.0, key(torso=-12, head=5, r_leg=(70, -95, 10), l_leg=(-35, -6, -40), r_arm=(-50, 10, 20), l_arm=(80, 12, 60), twist=8)),
    (0.2, key(torso=-8, head=3, r_leg=(60, -40, 8), l_leg=(-25, -90, -25), r_arm=(-20, 50, 25), l_arm=(45, 45, 40), twist=5)),
    (0.4, key(torso=-5, head=1, r_leg=(40, -60, 4), l_leg=(10, -72, -10), r_arm=(5, 62, 25), l_arm=(25, 60, 30), twist=2)),
    (0.55, key(torso=-4, head=0, r_leg=(30, -40, 2), l_leg=(15, -36, -4), r_arm=(12, 52, 22), l_arm=(18, 52, 25))),
]

# Sprint: long split leap. Bigger knee drive, leg reaching far forward, back leg trailing.
JUMP_SPRINT = [
    (0.0, key(torso=-18, head=8, r_leg=(80, -92, 12), l_leg=(-40, -5, -45), r_arm=(-60, 12, 20), l_arm=(90, 14, 65), twist=10)),
    (0.22, key(torso=-14, head=6, r_leg=(75, -15, 12), l_leg=(-45, -60, -30), r_arm=(-30, 55, 20), l_arm=(40, 55, 35), twist=6)),
    (0.45, key(torso=-9, head=3, r_leg=(55, -40, 6), l_leg=(-10, -85, -20), r_arm=(0, 62, 22), l_arm=(25, 60, 30), twist=3)),
    (0.62, key(torso=-6, head=1, r_leg=(35, -40, 2), l_leg=(20, -45, -6), r_arm=(12, 52, 22), l_arm=(18, 52, 25))),
]


def squat_frames(duration, curve, upper, fps=30, feet=((1, -0.1), (-1, 0.12))):
    """Feet planted on the ground (IK) while the hips drop by curve(u) studs; upper(u) gives
    the torso/arms key."""
    n = max(2, round(duration * fps))
    frames = []
    for i in range(n + 1):
        u = i / n
        drop = curve(u)
        poses = to_poses(upper(u))
        pos, rot = (0, -drop, 0), np.eye(3)
        poses["LowerTorso"] = (pos, rot)
        lt = L.lt_frame_of(pos, rot)
        for side, z in feet:
            pre = "Right" if side > 0 else "Left"
            ankle = np.array([side * 0.45, r15.GROUND + L.SOLE, z])
            R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, L.ry(-D(8) * side), side)
            poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
            poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
            poses[pre + "Foot"] = ((0, 0, 0), R_f)
        frames.append((duration * u, poses))
    return frames


def prep_frames():
    """Standing jump wind-up: quick crouch, chest forward, arms swing back."""
    return squat_frames(
        0.16, lambda u: 0.55 * L.smooth(u),
        lambda u: key(torso=-22 * L.smooth(u), head=10 * L.smooth(u),
                      r_arm=(-45 * L.smooth(u), 8, 25 * L.smooth(u)), l_arm=(-45 * L.smooth(u), 8, 25 * L.smooth(u))),
        feet=((1, 0.0), (-1, 0.05)))

def fall_frames(duration=0.9, steps=18):
    frames = []
    for i in range(steps + 1):
        w = 2 * math.pi * i / steps
        s, c = math.sin(w), math.cos(w)
        # legs pedal, arms keep circling out to the sides for balance
        k = key(torso=-5 + 3 * s, head=0,
                r_leg=(35 + 20 * s, -60 - 25 * c, 4), l_leg=(35 - 20 * s, -60 + 25 * c, -6),
                r_arm=(15 + 22 * c, 58 + 12 * s, 25 + 10 * s), l_arm=(15 - 22 * c, 58 - 12 * s, 25 - 10 * s),
                twist=4 * s)
        frames.append((duration * i / steps, to_poses(k)))
    return frames


def land_frames():
    """Touch-down: hips dip and spring back, arms come down from the sides."""
    depth = 0.25
    curve = lambda u: depth * (L.smooth(u / 0.25) if u < 0.25 else 1 - L.smooth((u - 0.25) / 0.75))  # noqa: E731
    return squat_frames(0.32, curve, lambda u: key(
        torso=-3 - 8 * curve(u) / depth, head=1 + 4 * curve(u) / depth,
        r_arm=(10, 50 - 40 * u, 20), l_arm=(12, 50 - 40 * u, 20)))

def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        "Tulevo_JumpPrep": (prep_frames(), False),
        "Tulevo_Jump": (track(JUMP), False),
        "Tulevo_JumpStand": (track(JUMP_STAND), False),
        "Tulevo_JumpSprint": (track(JUMP_SPRINT), False),
        "Tulevo_Fall": (fall_frames(), True),
        "Tulevo_Land": (land_frames(), False),
    }
    for name, (frames, loop) in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(L.sequence(name, frames, priority=1, loop=loop))
        print(name, len(frames), "frames,", f"{frames[-1][0]:.2f}s", "loop" if loop else "once")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))
    L.check("Tulevo_Land", None, clips["Tulevo_Land"][0])


if __name__ == "__main__":
    main()
