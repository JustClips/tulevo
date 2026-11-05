"""Aiming strafe: legs-only side-step cycles for walking left / right while the body keeps
facing the aim (GTA style). The hips stay square (no hip turn) so the shouldered rifle doesn't
swing; feet travel sideways in two lanes (left foot a little forward like a rifle stance, right
foot back), so when they pass each other they cross without clipping.

  python3 art/anim/strafe.py [--preview]  -> art/out/anims/Tulevo_StrafeLeft/Right.rbxmx

Only the LowerTorso and legs are keyed (parents with Weight 0), so the upper body comes from
the Aim pose. The game blends these with the forward/back walk by how sideways you move
(src/client/Movement/Gait.luau) and plays them at speed / Natural (src/shared/Gaits.luau
StrafeNatural).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gun as G  # noqa: E402
import locomotion as L  # noqa: E402
import r15  # noqa: E402

D = math.radians

STRAFE = dict(
    L.WALK, duration=0.8, stance=0.6,
    front=-0.72, back=0.78,      # travel along the movement direction while planted
    lift=0.26, toe_out=4,
    heel_pitch=8, toe_pitch=-18, swing_pitch=-4,
    bob=0.035, sway=0.0, hip_yaw=0, hip_roll=2,
)
LANE = {1: (0.45, 0.32), -1: (-0.45, -0.32)}  # side -> (base x, z): left foot forward, right back


def foot_world_strafe(dirn):
    def fw(p, s, side):
        z_plan, lift, pitch, planted = L.foot_plan(p, s)
        bx, bz = LANE[side]
        rot = L.ry(-D(s["toe_out"]) * side) @ L.rz(-D(pitch) * 0.6 * dirn)
        corners = [rot @ np.array([sx, -L.SOLE, sz]) for sx in (-0.3, 0.3) for sz in (L.HEEL_Z, L.TOE_Z)]
        low = min(q[1] for q in corners)
        ankle = np.array([bx - z_plan * dirn, r15.GROUND + lift - low, bz])
        return ankle, rot, planted
    return fw


def build(dirn, steps=24):
    s = STRAFE
    orig = L.foot_world
    L.foot_world = foot_world_strafe(dirn)
    try:
        drop = L.find_drop(s)
        frames = []
        for i in range(steps + 1):
            p = i / steps
            pos, rot = L.pelvis(p, s, drop)
            poses = {"LowerTorso": (tuple(pos), rot)}
            lt = L.lt_frame_of(pos, rot)
            for side, ph, pre in ((1, p, "Right"), (-1, (p + 0.5) % 1, "Left")):
                ankle, frot, _ = L.foot_world(ph, s, side)
                R_ul, R_ll, R_f, _ = L.leg_ik(lt, ankle, frot, side)
                poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
                poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
                poses[pre + "Foot"] = ((0, 0, 0), R_f)
            frames.append((s["duration"] * p, poses))
    finally:
        L.foot_world = orig
    return frames, drop


KEYED = ["LowerTorso", "RightUpperLeg", "RightLowerLeg", "RightFoot", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot"]


def main():
    os.makedirs(L.OUT, exist_ok=True)
    nat = L.natural_speed(STRAFE)
    for name, dirn in (("Tulevo_StrafeRight", 1), ("Tulevo_StrafeLeft", -1)):
        frames, drop = build(dirn)
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, frames, KEYED, True, priority=1))
        print(f"{name}: natural speed {nat:.3f} studs/s, hips sit {drop:.3f} lower")
        if "--preview" in sys.argv:
            fine, _ = build(dirn, 40)
            L.preview(name, fine, os.path.join(L.OUT, f"{name}.gif"))
    print(f"StrafeNatural = {nat:.3f}")


if __name__ == "__main__":
    main()
