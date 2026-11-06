"""Using items (arms + head), for the default R15 rig:

  python3 art/anim/use_items.py [--preview]
    -> art/out/anims/Tulevo_DrinkBottle.rbxmx  (mead: 2.0 s)
       art/out/anims/Tulevo_DrinkCan.rbxmx     (chaser: 1.5 s)
       art/out/anims/Tulevo_Medkit.rbxmx       (first-aid kit: 4.0 s)
       src/shared/Items/Holds.luau             (where the real item model sits in the hand)
  then python3 tools/upload_anims.py

The real item model (ReplicatedStorage.ItemModels, pivot = its bounding-box centre, +Y up) is
welded to the hand for the whole use (Server/Inventory/InventoryService, C0 from Holds.luau),
so the clips only have to move the hands; the IK places the hand where the prop should be.
Each clip is as long as the item's Use.Time; the client plays it at length / Time anyway.

  Drink: the bottle / can comes up from the hip, tips back to the mouth with the head tilted
         back, a few gulps, then back down.
  Medkit: the left hand holds the kit up by its handle in front of the belly, the right hand
          takes something out, presses and rubs it on the chest twice, then the kit goes down.

Prop sizes (studs, x3.6 from art/models/*/meta.json): Mead 0.28 x 0.945 tall, Chaser 0.24 x
0.418 tall, FirstAidKit 1.10 wide x 0.89 tall x 0.385 deep.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gun as G  # noqa: E402
import locomotion as L  # noqa: E402
import r15  # noqa: E402
import vest as V  # noqa: E402

D = math.radians
rx, ry, rz = L.rx, L.ry, L.rz
FPS = 30
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ------------------------------------------------------------------ props in the hand
# Grip frame = the hand's grip point (0.158 below the hand centre) with the hand's rotation.
# The fist's hole runs along hand Z (thumb side = -Z, like the carbine's pistol grip).


def frame(rot, pos):
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = pos
    return m


# upright in the fist: prop +Y (up) out of the thumb side (hand -Z)
UPRIGHT = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)
# hanging by its handle: handle (prop X) through the fist (hand Z), prop up = hand +Y
BY_HANDLE = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], dtype=float)

PROPS = {
    # name: (prop frame in grip space, hand, height for the drink maths)
    "Mead": (frame(UPRIGHT, (0, 0, -0.14)), "RightHand", 0.945),
    "Chaser": (frame(UPRIGHT, (0, 0, -0.02)), "RightHand", 0.418),
    "FirstAidKit": (frame(BY_HANDLE, (0, -0.49, 0)), "LeftHand", 0.89),
}


def hand_c0(name):
    """Weld C0: hand part -> prop pivot."""
    return r15.T(*G.GRIP_OFFSET) @ PROPS[name][0]


def grip_for(prop_ut, name):
    """Hand grip target (UT space) that puts the prop at prop_ut."""
    return prop_ut @ np.linalg.inv(PROPS[name][0])


# ------------------------------------------------------------------ head / mouth
NECK = r15.T(0, 0.849, 0)          # UpperTorso -> neck
HEAD_UP = r15.T(0, 0.576, 0)       # neck -> head centre
MOUTH = np.array([0, -0.24, -0.62, 1])  # on the front of the blocky head


def mouth_at(tilt):
    """Mouth position (UT space) with the head tilted back by tilt radians."""
    return (NECK @ r15.R(rx(tilt)) @ HEAD_UP @ MOUTH)[:3]


# ------------------------------------------------------------------ keys + solving
def path(keys):
    """keys [(t, 4x4)] -> 4x4 at t (smooth position + slerp)."""
    def at(t):
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = L.smooth((t - t0) / (t1 - t0))
                m = np.eye(4)
                m[:3, 3] = L.lerp(a[:3, 3], b[:3, 3], u)
                m[:3, :3] = G._slerp(a[:3, :3], b[:3, :3], u)
                return m
        return keys[-1][1]
    return at


def scalar(keys):
    def at(t):
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                return L.lerp(a, b, L.smooth((t - t0) / (t1 - t0)))
        return keys[-1][1]
    return at


def solve(length, targets, head_tilt, rest_in, rest_out):
    """targets {side: fn(t) -> (4x4 UT target, rot weight)}; head_tilt fn(t) -> radians.
    Arms blend up from hanging over rest_in and back down over rest_out."""
    n = round(length * FPS)
    base = G.base_pose()
    ut = G.ut_frame(base)
    xs = {s: [D(40), 0, 0, D(60), 0, 0, 0] for s in targets}
    poles = {1: (ut @ np.array([1.6, -1.0, 0.2, 1]))[:3], -1: (ut @ np.array([-1.6, -1.0, 0.2, 1]))[:3]}
    frames, worst = [], 0.0
    for i in range(n + 1):
        t = length * i / n
        tt = min(max(t, rest_in[1]), rest_out[0])
        k = 1.0
        if t < rest_in[1]:
            k = L.smooth(max(0.0, (t - rest_in[0]) / (rest_in[1] - rest_in[0])))
        if t > rest_out[0]:
            k = 1 - L.smooth(min(1.0, (t - rest_out[0]) / (rest_out[1] - rest_out[0])))
        poses = dict(base)
        for side, fn in targets.items():
            target, rw = fn(tt)
            x, err = G.solve_arm(base, side, ut @ target, xs[side], rw, poles[side])
            xs[side] = x
            if t == tt:
                worst = max(worst, err)
            _, poses = G.arm_frames(poses, side, np.array(x) * k)
        poses["Head"] = ((0, 0, 0), rx(head_tilt(t)))
        frames.append((t, poses))
    return frames, worst


def keyed_parts(sides):
    parts = ["Head"]
    for s in sides:
        parts += list(G.ARM_PARTS[s])
    return parts


# ------------------------------------------------------------------ drinks
def drink(name, length):
    h = PROPS[name][2]
    up_t, mouth_t, off_t, down_t = 0.12 * length, 0.33 * length, 0.78 * length, 0.92 * length
    tilt = D(22)
    chest = frame(np.eye(3), (0.42, -0.2, -0.8))                  # upright in front of the chest

    def at_mouth(tip, head):
        # tipped back so the neck points into the mouth, bottom up in front
        rot = rx(D(tip))
        neck_dir = rot @ np.array([0, 1, 0])
        top = mouth_at(head) + np.array([0, 0, -0.04])
        return frame(rot, top - neck_dir * (h / 2) + np.array([0.06, 0, 0]))

    gulps = [(mouth_t, at_mouth(118, tilt))]
    n_g = 3
    for g in range(n_g):
        a = mouth_t + (off_t - mouth_t) * (g + 0.5) / n_g
        b = mouth_t + (off_t - mouth_t) * (g + 1) / n_g
        gulps += [(a, at_mouth(128, tilt + D(4))), (b, at_mouth(118, tilt))]
    prop = path([(up_t, chest), (mouth_t - 0.1 * length, frame(rx(D(60)), (0.32, 0.45, -0.95)))] + gulps
                + [(off_t + 0.06 * length, frame(rx(D(40)), (0.38, 0.2, -0.95))), (down_t, chest)])
    head = scalar([(0, 0.0), (mouth_t - 0.06 * length, 0.0), (mouth_t, tilt), (off_t, tilt + D(3)),
                   (off_t + 0.08 * length, 0.0), (length, 0.0)])

    def right(t):
        return grip_for(prop(t), name), 20.0
    return solve(length, {1: right}, head, rest_in=(0.0, up_t), rest_out=(down_t, length)), [1]


# ------------------------------------------------------------------ first-aid kit
def medkit(length=4.0):
    up_t, down_t = 0.45, 3.55
    kit_rot = ry(D(70))                                  # handle runs forward, kit beside the belly
    held = frame(kit_rot, (-0.55, -0.62, -0.95))
    kit = path([(up_t, held), (1.6, frame(kit_rot, (-0.5, -0.58, -0.95))), (down_t, held)])
    kit_top = lambda t: (kit(t) @ np.array([0.1, 0.38, 0, 1]))[:3]  # noqa: E731  # open top, by the handle

    # right hand: palm toward the body
    palm_in = rx(D(80)) @ ry(D(-20))
    chest = np.array([-0.25, 0.25, -0.7])
    belly = np.array([0.05, -0.15, -0.72])

    def rub(c, t0, t1, r=0.07, turns=2.0):
        out = []
        steps = 10
        for i in range(steps + 1):
            u = i / steps
            a = u * turns * 2 * math.pi
            out.append((t0 + (t1 - t0) * u, tuple(c + np.array([math.cos(a) * r, math.sin(a) * r, 0]))))
        return out

    keys = ([(up_t, None), (0.75, "kit"), (0.95, "kit"), (1.15, tuple(chest))] + rub(chest, 1.2, 2.0)
            + [(2.25, "kit"), (2.45, "kit"), (2.7, tuple(belly))] + rub(belly, 2.75, 3.3, 0.06, 1.5)
            + [(down_t, None)])

    def right_pos(t):
        pts = []
        for tk, p in keys:
            if p == "kit":
                p = tuple(kit_top(tk))
            elif p is None:
                p = (0.35, -0.55, -0.6)
            pts.append((tk, p))
        return V.lerp_keys(pts, t)

    def left(t):
        return grip_for(kit(t), "FirstAidKit"), 20.0

    def right(t):
        return frame(palm_in, right_pos(t)), 0.3
    head = scalar([(0, 0.0), (0.6, D(-18)), (3.4, D(-18)), (3.8, 0.0), (length, 0.0)])  # looks down at it
    return solve(length, {1: right, -1: left}, head, rest_in=(0.0, up_t), rest_out=(down_t, length)), [1, -1]


# ------------------------------------------------------------------ output
def cframe_lua(m):
    p, r = m[:3, 3], m[:3, :3]
    v = [*p, *r.flatten()]
    return "CFrame.new(" + ", ".join(f"{x:.4f}" for x in v) + ")"


def write_holds():
    lines = ["-- Generated by art/anim/use_items.py. Where each item's model sits in the hand while it's",
             "-- used (Weld C0: hand part -> the model's pivot, its bounding-box centre).", "return {"]
    for name, (_, hand, _) in PROPS.items():
        lines.append(f'\t{name} = {{ Part = "{hand}", C0 = {cframe_lua(hand_c0(name))} }},')
    lines.append("}")
    path_ = os.path.join(ROOT, "src", "shared", "Items", "Holds.luau")
    open(path_, "w").write("\n".join(lines) + "\n")


def main():
    os.makedirs(L.OUT, exist_ok=True)
    clips = {
        "Tulevo_DrinkBottle": drink("Mead", 2.0),
        "Tulevo_DrinkCan": drink("Chaser", 1.5),
        "Tulevo_Medkit": medkit(4.0),
    }
    for name, ((frames, worst), sides) in clips.items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(G.sequence(name, frames, keyed_parts(sides), False, priority=3))
        print(f"{name}: {len(frames)} frames {frames[-1][0]:.2f}s  worst hand miss {worst:.3f} studs")
        if "--preview" in sys.argv:
            L.preview(name, frames + [frames[-1]], os.path.join(L.OUT, f"{name}.gif"))
    write_holds()


if __name__ == "__main__":
    main()
