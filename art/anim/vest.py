"""Armor vest on / off (arms only), for the default R15 rig.

  python3 art/anim/vest.py [--preview]  -> art/out/anims/Tulevo_VestOn.rbxmx, Tulevo_VestOff.rbxmx

The vest model is rigid, so while it's carried it is welded to the right hand (VEST_IN_HAND,
printed below) and both hands hold its shoulder straps; the server (src/server/Armor.server.luau)
moves the weld on the same beats (VEST_ON / VEST_OFF):

  On:  hands come up, the vest appears held in front (appear), goes up and over the head and
       down onto the shoulders (worn: welded to the UpperTorso, armor on), then the hands rip
       open and slap shut the side straps and pat the front plate.
  Off: rip the side straps open, grab the shoulder straps (lift: welded to the hand, armor
       off), lift it up off the shoulders, over the head and down in front (stow: gone).

Vest box frame = the vest's bounding box centre, in UpperTorso space WORN when worn
(art/models/ArmorVest/meta.json: box centre 0.1025 below and 0.0275 in front of the torso
centre; Armor.server.luau BOX_OFFSET).
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
rx, ry, rz = L.rx, L.ry, L.rz

WORN = r15.T(0, -0.1025, -0.0275)
FRONT = r15.T(0, -0.05, -1.35)     # held out in front by the shoulder straps
RAISED = r15.T(0, 0.75, -0.95)     # up in front of the face
OVER = r15.T(0, 0.75, -0.03)       # right above the shoulders, head through the neck hole

# Hands on the shoulder straps (vest box space): grip point and hand rotation (fingers forward,
# palm down on the strap).
GRIP = {1: np.array([0.6, 1.1, -0.15]), -1: np.array([-0.6, 1.1, -0.15])}
HOLD_ROT = {1: ry(D(-30)) @ rz(D(90)) @ rx(D(90)), -1: ry(D(30)) @ rz(D(-90)) @ rx(D(90))}

VEST_ON = dict(appear=0.15, worn=0.85, length=1.75)
VEST_OFF = dict(lift=0.5, stow=1.1, length=1.35)

# free-hand spots (UpperTorso space): side straps (cummerbund), pulled open, front plate
SIDE = {1: (1.36, -0.42, 0.0), -1: (-1.36, -0.42, 0.0)}
SIDE_OUT = {1: (1.62, -0.42, -0.06), -1: (-1.62, -0.42, -0.06)}
PLATE = {1: (0.35, 0.15, -1.02), -1: (-0.35, 0.15, -1.02)}
PLATE_IN = {1: (0.35, 0.12, -0.95), -1: (-0.35, 0.12, -0.95)}


def grip_frame(vest, side):
    m = np.eye(4)
    m[:3, :3] = vest[:3, :3] @ HOLD_ROT[side]
    m[:3, 3] = (vest @ np.array([*GRIP[side], 1]))[:3]
    return m


def vest_in_hand():
    """Vest box frame relative to the RightHand while carried (Weld C0)."""
    g = np.eye(4)
    g[:3, :3] = HOLD_ROT[1]
    g[:3, 3] = GRIP[1]
    return r15.T(*G.GRIP_OFFSET) @ np.linalg.inv(g)


def path(keys):
    """keys [(t, 4x4 vest frame)] -> vest frame at t (Catmull-Rom position, slerp rotation)."""
    def at(t):
        if t <= keys[0][0]:
            return keys[0][1]
        for i in range(len(keys) - 1):
            (t0, a), (t1, b) = keys[i], keys[i + 1]
            if t0 <= t <= t1:
                u = L.smooth((t - t0) / (t1 - t0))
                p = [k[1][:3, 3] for k in keys]
                m = np.eye(4)
                m[:3, 3] = G._catmull(p[max(0, i - 1)], p[i], p[i + 1], p[min(len(p) - 1, i + 2)], u)
                m[:3, :3] = G._slerp(a[:3, :3], b[:3, :3], u)
                return m
        return keys[-1][1]
    return at


def free_target(pos, rot):
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = pos
    return m


def lerp_keys(keys, t):
    """keys [(t, (x, y, z))] -> smoothly interpolated point."""
    if t <= keys[0][0]:
        return np.array(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return L.lerp(np.array(a), np.array(b), L.smooth((t - t0) / (t1 - t0)))
    return np.array(keys[-1][1])


def solve_clip(length, target_at, rest_in=None, rest_out=None, fps=30):
    """target_at(t, side) -> (4x4 target in UT space, rot weight). rest_in = (t0, t1): arms come
    up from hanging to the first solved pose; rest_out = (t0, t1): they drop back to hanging."""
    n = round(length * fps)
    base = G.base_pose()
    ut = G.ut_frame(base)
    xs = {1: [D(40), 0, 0, D(60), 0, 0, 0], -1: [D(40), 0, 0, D(60), 0, 0, 0]}
    poles = {1: (ut @ np.array([1.6, -0.6, -0.4, 1]))[:3], -1: (ut @ np.array([-1.6, -0.6, -0.4, 1]))[:3]}
    solved = []
    worst = 0
    for i in range(n + 1):
        t = length * i / n
        tt = t
        if rest_in and t < rest_in[1]:
            tt = rest_in[1]
        if rest_out and t > rest_out[0]:
            tt = rest_out[0]
        out = {}
        for side in (1, -1):
            target, rw = target_at(tt, side)
            x, err = G.solve_arm(base, side, ut @ target, xs[side], rw, poles[side])
            xs[side] = x
            out[side] = np.array(x)
            if (not rest_in or t >= rest_in[1]) and (not rest_out or t <= rest_out[0]):
                worst = max(worst, err)
        solved.append((t, out))
    frames = []
    for t, out in solved:
        k = 1.0
        if rest_in and t < rest_in[1]:
            k = L.smooth(max(0.0, (t - rest_in[0]) / (rest_in[1] - rest_in[0])))
        if rest_out and t > rest_out[0]:
            k = 1 - L.smooth(min(1.0, (t - rest_out[0]) / (rest_out[1] - rest_out[0])))
        _, poses = G.arm_frames(base, 1, out[1] * k)
        _, poses = G.arm_frames(poses, -1, out[-1] * k)
        frames.append((t, poses))
    return frames, worst


def vest_on():
    b = VEST_ON
    carry = path([(b["appear"], FRONT), (0.45, RAISED), (0.65, OVER), (b["worn"], WORN)])
    # after the vest is on: shoulder straps -> side straps, rip open, slap shut -> pat the plate
    free = {s: [(0.95, tuple(grip_frame(WORN, s)[:3, 3])), (1.12, SIDE[s]), (1.2, SIDE_OUT[s]),
                (1.28, SIDE[s]), (1.42, PLATE[s]), (1.48, PLATE_IN[s]), (1.54, PLATE[s])] for s in (1, -1)}

    def target(t, side):
        if t <= 0.95:
            return grip_frame(carry(min(t, b["worn"])), side), (20.0 if side > 0 else 0.35)
        rot = grip_frame(WORN, side)[:3, :3]
        rw = (20.0 if side > 0 else 0.35) * math.exp(-(t - 0.95) * 25)
        return free_target(lerp_keys(free[side], t), rot), max(rw, 0.02)
    return solve_clip(b["length"], target, rest_in=(0.0, b["appear"]), rest_out=(1.54, b["length"]))


def vest_off():
    b = VEST_OFF
    carry = path([(b["lift"], WORN), (0.7, OVER), (0.9, RAISED), (b["stow"], FRONT)])
    free = {s: [(0.0, SIDE[s]), (0.18, SIDE[s]), (0.27, SIDE_OUT[s]), (0.33, SIDE_OUT[s]),
                (b["lift"] - 0.04, tuple(grip_frame(WORN, s)[:3, 3]))] for s in (1, -1)}

    def target(t, side):
        if t < b["lift"] - 0.04:
            rot = grip_frame(WORN, side)[:3, :3]
            rw = (20.0 if side > 0 else 0.35) * math.exp(-(b["lift"] - 0.04 - t) * 25)
            return free_target(lerp_keys(free[side], t), rot), max(rw, 0.02)
        return grip_frame(carry(max(t, b["lift"])), side), (20.0 if side > 0 else 0.35)
    return solve_clip(b["length"], target, rest_in=(0.0, 0.18), rest_out=(b["stow"], b["length"]))


def main():
    os.makedirs(L.OUT, exist_ok=True)
    for name, (frames, worst) in (("Tulevo_VestOn", vest_on()), ("Tulevo_VestOff", vest_off())):
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, frames, G.ARMS, False, priority=3))
        print(f"{name}: {len(frames)} frames {frames[-1][0]:.2f}s  worst hand miss {worst:.3f} studs")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))
    m = vest_in_hand()
    print("VEST_IN_HAND C0:", ", ".join(f"{v:.4f}" for v in [*m[:3, 3], *m[:3, :3].flatten()]))
    print("VEST_ON beats:", VEST_ON, "VEST_OFF beats:", VEST_OFF)


if __name__ == "__main__":
    main()
