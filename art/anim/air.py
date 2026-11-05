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


# Arms stay close to the body (small "out" angles) and swing forward/back like a sprint
# stride, the way GTA does it. No wide balance arms.
PUSH = key(torso=-12, head=4, r_leg=(38, -45, 8), l_leg=(-22, -12, -38),
           r_arm=(-30, 4, 35), l_arm=(40, 4, 70), twist=5)
TUCK = key(torso=-8, head=3, r_leg=(68, -85, 14), l_leg=(-14, -72, -30),
           r_arm=(-22, 5, 45), l_arm=(42, 5, 80), twist=4)
AIR = key(torso=-5, head=2, r_leg=(45, -60, 6), l_leg=(-4, -55, -18),
          r_arm=(-10, 6, 50), l_arm=(28, 6, 70), twist=2)

JUMP = [(0.0, PUSH), (0.16, TUCK), (0.42, AIR)]


def fall_frames(duration=1.0, steps=20):
    frames = []
    for i in range(steps + 1):
        w = 2 * math.pi * i / steps
        s, c = math.sin(w), math.cos(w)
        k = key(torso=-4 + 2 * s, head=0,
                r_leg=(32 + 6 * s, -50 - 6 * c, 4), l_leg=(8 - 6 * s, -55 + 6 * c, -10),
                r_arm=(8 + 6 * c, 9 + 3 * s, 50), l_arm=(14 - 6 * c, 9 - 3 * s, 55), twist=2 * s)
        frames.append((duration * i / steps, to_poses(k)))
    return frames


def land_frames(duration=0.3, fps=30):
    """Feet planted; hips drop fast then spring back up. Arms/torso from key poses."""
    n = round(duration * fps)
    frames = []
    for i in range(n + 1):
        t = duration * i / n
        u = t / duration
        # hips: down to 0.6 by u=0.22, back up by the end
        DEPTH = 0.22
        drop = DEPTH * (L.smooth(u / 0.25) if u < 0.25 else 1 - L.smooth((u - 0.25) / 0.75))
        f = drop / DEPTH
        k = key(torso=-3 - 7 * f, head=1 + 4 * f,
                r_arm=(6 + 8 * f, 5, 20 + 15 * f), l_arm=(4 + 8 * f, 5, 18 + 15 * f))
        poses = to_poses(k)
        pos, rot = (0, -drop, 0), np.eye(3)
        poses["LowerTorso"] = (pos, rot)
        lt = L.lt_frame_of(pos, rot)
        for side, pre, z in ((1, "Right", -0.1), (-1, "Left", 0.12)):
            ankle = np.array([side * 0.45, r15.GROUND + L.SOLE, z])
            frot = L.ry(-D(8) * side)
            R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, frot, side)
            poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
            poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
            poses[pre + "Foot"] = ((0, 0, 0), R_f)
        frames.append((t, poses))
    return frames


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        "Tulevo_Jump": (track(JUMP), False),
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
