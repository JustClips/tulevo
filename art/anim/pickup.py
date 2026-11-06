"""Picking something up off the ground (whole body), for the default R15 rig:

  python3 art/anim/pickup.py [--preview]
    -> art/out/anims/Tulevo_Pickup.rbxmx      (right hand, empty hands: 1.2 s)
       art/out/anims/Tulevo_PickupLeft.rbxmx  (left hand, a gun in the right: 1.2 s)
  then python3 tools/upload_anims.py

GTA-style: the item is on the ground a step in front (PICK_SPOT, a little to the grabbing
side). The near foot steps forward, the knees bend into a deep squat with the feet planted
(leg IK), the back bends over, the head looks down at the item, the hand reaches it (arm IK),
grabs, and the body stands back up with the hand bringing the item up to the belly before the
arm drops back to the side. Client/Movement/Moves/Pickup walks the character to the spot
first and asks the server to take the item at GRAB_AT (printed below, also in Pickup.luau).

The other arm rests over the knee on the way down. In the left-hand clip the right arm isn't
keyed at all, so the rifle's hold clip keeps the gun in the right hand (it bends with the chest).
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
import roll as RL  # noqa: E402

D = math.radians
K = A.key
FPS = 30
LENGTH = 1.2
GRAB_AT = 0.5        # seconds: the hand closes on the item (the server takes it then)
DOWN_AT = 0.42       # lowest point of the reach
# Where the item lies, HRP space (x right, front = -Z), for the right hand; mirrored for the left.
PICK_SPOT = (0.42, r15.GROUND + 0.16, -1.1)


def keys(s):
    """s = +1 right hand grabs, -1 left. Key = (t, body key, hip pitch deg, foot IK).
    Feet: (leg side, x, z, foot pitch); the grabbing side's foot steps forward."""
    near, far = (1, -1) if s > 0 else (-1, 1)
    stand = RL.IK(feet=((1, 0.45, 0.0, 0), (-1, -0.45, 0.0, 0)))

    def feet(step, back, heel):
        f = {near: (near, 0.48 * near, -step, 0), far: (far, 0.42 * far, back, heel)}
        return (f[1], f[-1])

    rest = (6, 4, 10)
    knee_arm = (55, 6, 70)  # the free hand comes down over the knee
    r_low, l_low = (knee_arm, rest) if s < 0 else (rest, knee_arm)
    return [
        (0.0, K(r_arm=rest, l_arm=rest), 0, stand),
        (0.16, K(torso=-12, head=-12, r_arm=rest, l_arm=rest), 8, RL.IK(0.25, pz=-0.05, feet=feet(0.3, 0.1, -8))),
        (DOWN_AT, K(torso=-46, head=-34, twist=-12 * s, r_arm=r_low, l_arm=l_low), 30,
         RL.IK(1.08, pz=0.05, feet=feet(0.42, 0.3, -34))),
        (GRAB_AT + 0.06, K(torso=-44, head=-32, twist=-10 * s, r_arm=r_low, l_arm=l_low), 29,
         RL.IK(1.04, pz=0.05, feet=feet(0.42, 0.3, -34))),
        (0.85, K(torso=-10, head=-14, r_arm=rest, l_arm=rest), 6, RL.IK(0.22, pz=-0.05, feet=feet(0.25, 0.12, -6))),
        (LENGTH, K(r_arm=rest, l_arm=rest), 0, stand),
    ]


def hand_path(s):
    """(t, HRP-space grip point, IK weight) for the grabbing hand: hangs, reaches down to the
    item, closes on it, brings it up to the belly, lets the arm drop."""
    spot = np.array([PICK_SPOT[0] * s, PICK_SPOT[1], PICK_SPOT[2]])
    above = spot + np.array([0.0, 0.35, 0.05])
    belly = np.array([0.32 * s, -0.55, -0.85])
    return [
        (0.1, above + np.array([0.0, 1.1, 0.25]), 0.0),
        (0.32, above, 1.0),
        (DOWN_AT, spot, 1.0),
        (GRAB_AT + 0.06, spot + np.array([0, 0.03, 0]), 1.0),
        (0.72, spot + np.array([0.0, 0.9, 0.2]), 1.0),
        (0.9, belly, 1.0),
        (1.0, belly + np.array([0.0, -0.15, 0.1]), 0.8),
        (LENGTH, belly + np.array([0.0, -0.6, 0.4]), 0.0),
    ]


def sample(path, t):
    if t <= path[0][0]:
        return path[0][1], path[0][2]
    for (t0, a, wa), (t1, b, wb) in zip(path, path[1:]):
        if t0 <= t <= t1:
            u = L.smooth((t - t0) / (t1 - t0))
            return L.lerp(a, b, u), L.lerp(wa, wb, u)
    return path[-1][1], path[-1][2]


def frames(s):
    ks = keys(s)
    hp = hand_path(s)
    side_parts = G.ARM_PARTS[s]
    x = [D(40), 0, 0, D(60), 0, 0, 0]
    n = round(LENGTH * FPS)
    out, worst = [], 0.0
    for i in range(n + 1):
        t = LENGTH * i / n
        k = A.loosen(lambda tt: RL.pose_key(ks, tt), t, LENGTH, drift=0.5)
        poses = A.to_poses(k)
        pitch = RL.angle_at(ks, t)
        w, ik = RL.ik_at(ks, t)
        rot = L.rx(-D(pitch)) @ np.asarray(poses["LowerTorso"][1])
        pos = (ik["px"] * w, -ik["drop"] * w, ik["pz"] * w)
        poses["LowerTorso"] = (pos, rot)
        lt = L.lt_frame_of(pos, rot)
        for side, fx, fz, fp in ik["feet"]:
            pre = "Right" if side > 0 else "Left"
            ankle, frot = RL.foot_ankle(fx, fz, fp, side)
            R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, frot, side)
            poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
            poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
            poses[pre + "Foot"] = ((0, 0, 0), R_f)
        # grabbing arm: IK to the hand path (palm down, fingers forward), blended over the FK arm
        target_p, aw = sample(hp, t)
        if aw > 0:
            ut = r15.solve(poses)["UpperTorso"]
            target = np.eye(4)
            target[:3, :3] = L.rx(D(-25))
            target[:3, 3] = target_p
            pole = (ut @ np.array([1.4 * s, -0.4, 0.9, 1]))[:3]
            x, err = G.solve_arm(poses, s, target, x, 0.25, pole)
            if aw > 0.99:
                worst = max(worst, err)
            _, solved = G.arm_frames(poses, s, x)
            for part in side_parts:
                poses[part] = ((0, 0, 0), RL.blend(np.asarray(poses[part][1]), np.asarray(solved[part][1]), aw))
        out.append((t, poses))
    return out, worst


def grip_at(frames_, s, t):
    """Where the grabbing hand's grip point is at time t (for checking the reach)."""
    f = min(frames_, key=lambda fr: abs(fr[0] - t))[1]
    hand = G.ARM_PARTS[s][2]
    return (r15.solve(f)[hand] @ np.array([*G.GRIP_OFFSET, 1]))[:3]


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {"Tulevo_Pickup": 1, "Tulevo_PickupLeft": -1}
    for name, s in clips.items():
        fr, worst = frames(s)
        parts = list(r15.ORDER)
        if s < 0:
            parts = [p for p in parts if p not in G.ARM_PARTS[1]]  # the gun's hold clip owns the right arm
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, fr, parts, False, priority=4))
        g = grip_at(fr, s, GRAB_AT)
        lows = [RL.lowest(p) - r15.GROUND for _, p in fr]
        print(f"{name}: {len(fr)} frames {LENGTH:.2f}s grab at {GRAB_AT}s, hand miss {worst:.3f}, "
              f"grip at grab {np.round(g, 2)} (ground {r15.GROUND}), lowest point {min(lows):+.3f}")
        if "--preview" in sys.argv:
            L.preview(name, fr + [fr[-1]], os.path.join(L.OUT, f"{name}.gif"))


if __name__ == "__main__":
    main()
