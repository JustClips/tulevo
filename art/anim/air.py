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


def key(torso=0.0, head=0.0, r_leg=(0, 0, 0), l_leg=(0, 0, 0), r_arm=(0, 0, 0), l_arm=(0, 0, 0), twist=0.0,
        r_hand=(0, 0), l_hand=(0, 0), head_turn=0.0):
    """r_leg = (thigh, knee, foot); r_arm = (shoulder fwd, out, elbow); r_hand = (wrist bend, wrist side)."""
    return dict(torso=torso, head=head, r_leg=r_leg, l_leg=l_leg, r_arm=r_arm, l_arm=l_arm, twist=twist,
                r_hand=r_hand, l_hand=l_hand, head_turn=head_turn)


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
        "Head": ((0, 0, 0), L.rx(D(k["head"] - k["torso"] * 0.6)) @ L.ry(D(k.get("head_turn", 0)))),
    }
    for side, pre, leg, arm, hand in ((1, "Right", k["r_leg"], k["r_arm"], k.get("r_hand", (0, 0))),
                                      (-1, "Left", k["l_leg"], k["l_arm"], k.get("l_hand", (0, 0)))):
        poses[pre + "UpperLeg"] = ((0, 0, 0), L.rx(D(leg[0])) @ L.rz(D(3) * side))
        poses[pre + "LowerLeg"] = ((0, 0, 0), L.rx(D(leg[1])))
        poses[pre + "Foot"] = ((0, 0, 0), L.rx(D(leg[2])))
        poses[pre + "UpperArm"] = ((0, 0, 0), L.rz(D(arm[1]) * side) @ L.rx(D(arm[0])) @ L.ry(-D(8) * side))
        poses[pre + "LowerArm"] = ((0, 0, 0), L.rx(D(arm[2])))
        poses[pre + "Hand"] = ((0, 0, 0), L.rx(D(hand[0])) @ L.rz(D(hand[1]) * side) if hand != (0, 0) else I)
    return poses


# --- Loose body: overlap and follow-through -------------------------------------------
# Real bodies don't move as one rigid block: the big joints lead and the ends follow
# (shoulder -> elbow -> wrist, hip -> knee -> ankle, chest -> head), the two sides are never
# perfectly in sync, and nothing ever freezes. loosen() takes any pose-over-time function
# and builds each frame from the joints sampled a little in the past, plus floppy wrists
# and a slow, small drift so held poses still breathe.
LAG = {"elbow": 0.035, "wrist": 0.07, "knee": 0.02, "ankle": 0.045, "head": 0.05}
LEFT_LAG = 0.025  # the left side trails the right a touch


def loosen(sampler, t, end, drift=1.0):
    def at(dt):
        return sampler(min(end, max(0.0, t - dt)))

    now = at(0)
    out = dict(now)
    for side, leg_k, arm_k, hand_k, off in (("r", "r_leg", "r_arm", "r_hand", 0.0), ("l", "l_leg", "l_arm", "l_hand", LEFT_LAG)):
        base = at(off)
        leg = (base[leg_k][0], at(off + LAG["knee"])[leg_k][1], at(off + LAG["ankle"])[leg_k][2])
        elbow_now = base[arm_k][2]
        elbow_late = at(off + LAG["elbow"])[arm_k][2]
        swing = base[arm_k][0] - at(off + LAG["wrist"])[arm_k][0]  # how fast the arm is swinging
        ph = 1.7 if side == "r" else 2.3
        w = 2 * math.pi * t
        arm = (base[arm_k][0] + 2.5 * drift * math.sin(w * 0.9 + ph),
               base[arm_k][1] + 3.0 * drift * math.sin(w * 1.3 + ph),
               elbow_late + 4.0 * drift * math.sin(w * 1.1 + ph * 2))
        # wrists relax (bent a little) and flop against the swing; they flick when the elbow snaps
        wrist = (-12 - 0.45 * swing + 0.25 * (elbow_now - elbow_late), 6 + 3 * math.sin(w * 0.7 + ph))
        out[leg_k], out[arm_k], out[hand_k] = leg, arm, wrist
    out["head"] = at(LAG["head"])["head"] + 2.0 * drift * math.sin(2 * math.pi * t * 0.8)
    out["head_turn"] = 3.0 * drift * math.sin(2 * math.pi * t * 0.6 + 0.4)
    out["torso"] = now["torso"] + 1.5 * drift * math.sin(2 * math.pi * t * 1.2)
    return out


def track(keys, fps=30):
    """keys: [(time, key)], eased between neighbours, with loose overlap (see loosen)."""
    end = keys[-1][0]
    n = max(2, round(end * fps))

    def sampler(t):
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                return mix(a, b, L.smooth((t - t0) / max(1e-6, t1 - t0)))
        return keys[-1][1]

    return [(end * i / n, to_poses(loosen(sampler, end * i / n, end))) for i in range(n + 1)]


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

# Walking / jogging: two-footed like real life. Starts from the dip of Tulevo_JumpPrepMove
# (both knees bent, one foot a little ahead), both legs push off through the toes while the
# arms swing forward and up, then both knees come up (one slightly higher) and the arms open
# out, then the legs reach down for the ground.
JUMP = [
    (0.0, key(torso=-18, head=8, r_leg=(50, -80, 30), l_leg=(28, -70, 20), r_arm=(-35, 8, 25), l_arm=(-30, 8, 25))),
    (0.11, key(torso=-8, head=3, r_leg=(12, -8, -35), l_leg=(-6, -6, -38), r_arm=(75, 20, 25), l_arm=(70, 20, 25))),
    (0.3, key(torso=-6, head=1, r_leg=(58, -88, 8), l_leg=(42, -80, 4), r_arm=(30, 55, 30), l_arm=(25, 55, 30))),
    (0.55, key(torso=-4, head=0, r_leg=(30, -38, 2), l_leg=(20, -34, -2), r_arm=(14, 55, 22), l_arm=(12, 55, 22))),
]

# Sprint: same two-footed push but a long, stretched leap: body leans into it, legs trail
# out behind after the push, then swing through to land.
JUMP_SPRINT = [
    (0.0, key(torso=-22, head=10, r_leg=(55, -80, 30), l_leg=(30, -72, 22), r_arm=(-45, 10, 25), l_arm=(-40, 10, 25))),
    (0.12, key(torso=-14, head=6, r_leg=(-5, -10, -40), l_leg=(-18, -10, -42), r_arm=(85, 25, 25), l_arm=(80, 25, 25))),
    (0.32, key(torso=-12, head=5, r_leg=(30, -70, -10), l_leg=(5, -85, -20), r_arm=(40, 60, 30), l_arm=(35, 60, 30))),
    (0.62, key(torso=-6, head=1, r_leg=(38, -42, 4), l_leg=(26, -40, -2), r_arm=(14, 55, 22), l_arm=(12, 55, 22))),
]

def squat_frames(duration, curve, upper, fps=30, feet=((1, -0.1), (-1, 0.12))):
    """Feet planted on the ground (IK) while the hips drop by curve(u) studs; upper(u) gives
    the torso/arms key."""
    n = max(2, round(duration * fps))
    frames = []
    for i in range(n + 1):
        u = i / n
        drop = curve(u)
        poses = to_poses(loosen(lambda tt: upper(tt / duration), duration * u, duration))
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


def prep_move_frames():
    """Moving jump wind-up: a fast two-footed dip, one foot a little ahead."""
    return squat_frames(
        0.1, lambda u: 0.42 * L.smooth(u),
        lambda u: key(torso=-18 * L.smooth(u), head=8 * L.smooth(u),
                      r_arm=(-35 * L.smooth(u), 8, 25 * L.smooth(u)), l_arm=(-30 * L.smooth(u), 8, 25 * L.smooth(u))),
        feet=((1, -0.3), (-1, 0.3)))


def prep_frames():
    """Standing jump wind-up: quick crouch, chest forward, arms swing back."""
    return squat_frames(
        0.16, lambda u: 0.55 * L.smooth(u),
        lambda u: key(torso=-22 * L.smooth(u), head=10 * L.smooth(u),
                      r_arm=(-45 * L.smooth(u), 8, 25 * L.smooth(u)), l_arm=(-45 * L.smooth(u), 8, 25 * L.smooth(u))),
        feet=((1, 0.0), (-1, 0.05)))

def fall_frames(duration=0.9, steps=18):
    def at(tt):
        w = 2 * math.pi * (tt % duration) / duration
        s, c = math.sin(w), math.cos(w)
        # legs pedal, arms keep circling out to the sides for balance
        return key(torso=-5 + 3 * s, head=0,
                   r_leg=(35 + 20 * s, -60 - 25 * c, 4), l_leg=(35 - 20 * s, -60 + 25 * c, -6),
                   r_arm=(15 + 22 * c, 58 + 12 * s, 25 + 10 * s), l_arm=(15 - 22 * c, 58 - 12 * s, 25 - 10 * s),
                   twist=4 * s)

    # sampled one cycle in, so the lag looks back into the previous cycle; no drift keeps the
    # loop seamless
    return [(duration * i / steps, to_poses(loosen(at, duration * (1 + i / steps), 10 * duration, drift=0)))
            for i in range(steps + 1)]


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
        "Tulevo_JumpPrepMove": (prep_move_frames(), False),
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
