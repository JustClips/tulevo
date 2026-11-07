"""Superbike rider animations for the default (blocky) R15 rig:

  python3 art/anim/bike.py [--dump DIR]
    -> art/out/anims/Tulevo_Bike<Clip>.rbxmx
  then python3 tools/upload_anims.py

Clips (Client/Vehicles/Bike plays them while you ride Shared/Vehicles/Defs/Superbike):
  Ride                 sport riding pose: hands on the clip-ons, balls of the feet on the pegs, chest down
  SteerLeft/Right      the same with the bars at full lock (blended in by how far the bars are turned)
  LeanLeft/Right       hanging off into a hard corner: hips off the seat to the inside, inside knee out,
                       head kept nearer level (blended in by the bike's lean)
  Tuck                 chin down behind the screen at speed
  Stop                 stopped: sitting up a little, feet stay on the pegs (blocky legs are too short for the ground)
  Mount / Dismount     hop on from the left side / step off to the left (Dismount = Mount backwards)

Everything is posed in HumanoidRootPart space. The server welds the HumanoidRootPart HRP_ABOVE_SEAT
studs above the seat point (VehicleService SeatWeld), so the Root joint (1 stud under the HRP centre)
sits exactly on the seat and the clips place the body from there. Bike points come from the model
(art/blender/superbike, meters, +X = bike's left, -Y = front, Z up) times S studs per meter, which
must match Defs/Superbike.luau.
"""
import json
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
FPS = 30

# ------------------------------------------------------------------ bike layout (meters, bike coords)
S = float(os.environ.get("BIKE_S", "4.4"))  # studs per meter (Defs/Superbike.luau S, same as the hypercar)
SEAT = np.array([0.0, 0.29, 0.845])       # where the rider sits (lowest point of the rider seat)
GRIP = np.array([0.312, -0.3365, 0.834])  # left grip centre (right = mirrored)
PEG = np.array([0.215, 0.312, 0.4545])    # left footpeg, top (ball of the foot rests here)
TANK_TOP = np.array([0.02, -0.04, 1.02])
RAKE = D(23.1)
STEER_AXIS_GROUND_Y = -0.8144             # steering axis meets the ground here
STEER_LOCK = 24.0                         # degrees of bar turn in SteerLeft/Right (Def Steering.MaxAngle)
STOP_LEAN = 0.0                           # the blocky rider's legs can't reach the ground: the bike stands upright
HRP_ABOVE_SEAT = 1.0                      # HRP centre above the seat point (Root joint = seat point)

# blocky R15 foot: the ball of the foot (front of the sole) in Foot space, and from the ankle
BALL_IN_FOOT = np.array([0.0, -0.156, -0.25])
ANKLE_TO_BALL = np.array([0.0, -0.262, -0.25])


def bike_to_hrp(p):
    """Bike point (meters) -> HRP space (studs, x right, y up, front = -Z)."""
    p = np.asarray(p, dtype=float)
    return np.array([-(p[0] - SEAT[0]) * S, (p[2] - SEAT[2]) * S - HRP_ABOVE_SEAT, (p[1] - SEAT[1]) * S])


def world_to_bike(w, y, h, lean):
    """A point beside the bike given in the ground frame (w = meters to the bike's left of the tyre
    line, y = bike y, h = height above the ground) -> bike coords, with the bike leaned `lean`
    degrees to its left (about the tyre contact line)."""
    c, s = math.cos(D(lean)), math.sin(D(lean))
    return np.array([w * c - h * s, y, w * s + h * c])


def W(w, y, h, lean=STOP_LEAN):
    return bike_to_hrp(world_to_bike(w, y, h, lean))


def upright(lean=STOP_LEAN):
    """Rotation that turns HRP-space 'up' into world up for a bike leaned `lean` deg left."""
    return rz(-D(lean))


def steer_rot(deg):
    """Bars turned `deg` degrees to the left, as a rotation in HRP space about the steering axis."""
    a = np.array([0.0, math.cos(RAKE), math.sin(RAKE)])  # axis in HRP space: up, tilted back
    return G.rotvec(a * D(deg))


def steer_point(p, deg):
    """A point on the bars, turned with them."""
    pivot = bike_to_hrp([0.0, STEER_AXIS_GROUND_Y, 0.0])
    return pivot + steer_rot(deg) @ (bike_to_hrp(p) - pivot)


def grip(side, deg=0.0):
    """HRP-space grip centre for side (+1 right hand, -1 left hand)."""
    g = GRIP * np.array([-side, 1, 1])   # bike +X is the left
    return steer_point(g, deg)


def peg(side):
    return bike_to_hrp(PEG * np.array([-side, 1, 1]))


def hand_rot(side, fingers_down=35.0, yaw=0.0, roll=0.0):
    """Hand on a bar running sideways: palm down over the grip, fingers wrapped forward and down."""
    f = np.array([0.0, -math.sin(D(fingers_down)), -math.cos(D(fingers_down))])   # wrist -> fingertips
    up_back = np.array([0.0, math.cos(D(fingers_down)), -math.sin(D(fingers_down))])
    x = up_back * side           # right hand: back of the hand up (+X); left: mirrored
    y = -f
    z = np.cross(x, y)
    m = np.column_stack([x, y, z])
    return ry(D(yaw)) @ rz(D(roll)) @ m


def foot_rot(side, pitch=-8.0, out=8.0, base=None):
    """Toes forward (a touch out), pitched `pitch` deg (negative = toes down)."""
    m = ry(-D(out) * side) @ rx(D(pitch))
    return (base if base is not None else np.eye(3)) @ m


# ------------------------------------------------------------------ IK
THIGH, SHIN = L.THIGH, L.SHIN


def leg_ik(lt_frame, ball, frot, side, knee_dir):
    """Two-bone leg IK for a ball-of-foot target. knee_dir = which way the knee points (HRP space).
    Returns (R_upperleg, R_lowerleg, R_foot, miss)."""
    ankle = ball - frot @ ANKLE_TO_BALL
    hip = (lt_frame @ np.array([side * 0.5, -0.2, 0, 1]))[:3]
    R_lt = lt_frame[:3, :3]
    d = ankle - hip
    dist = np.linalg.norm(d)
    Ld = min(dist, (THIGH + SHIN) * 0.999)
    miss = max(0.0, dist - Ld)
    dh = d / dist
    cos_b = (THIGH ** 2 + Ld ** 2 - SHIN ** 2) / (2 * THIGH * Ld)
    b = math.acos(max(-1, min(1, cos_b)))
    pole = np.asarray(knee_dir, dtype=float)
    pole = pole - pole.dot(dh) * dh
    pole /= np.linalg.norm(pole)
    knee = hip + THIGH * (math.cos(b) * dh + math.sin(b) * pole)
    u_w = (knee - hip) / THIGH
    v_w = (hip + dh * Ld - knee) / SHIN
    u = R_lt.T @ u_w
    pl = R_lt.T @ pole
    zc = -(pl - pl.dot(u) * u)
    zc /= np.linalg.norm(zc)
    yc = -u
    xc = np.cross(yc, zc)
    R_ul = np.column_stack([xc, yc, zc])
    vl = R_ul.T @ R_lt.T @ v_w
    knee_a = math.atan2(-vl[2], -vl[1])
    R_ll = rx(knee_a)
    R_foot = (R_lt @ R_ul @ R_ll).T @ frot
    return R_ul, R_ll, R_foot, miss


def lt_frame_of(pos, rot):
    return r15.T(0, -1.0, 0) @ r15.T(*pos) @ r15.R(rot) @ r15.T(0, 0.2, 0)


# ------------------------------------------------------------------ poses
SIDES = {1: "Right", -1: "Left"}


def body_rot(pitch=0.0, yaw=0.0, roll=0.0, base=None):
    m = rz(D(roll)) @ ry(D(yaw)) @ rx(D(pitch))
    return (base if base is not None else np.eye(3)) @ m


SEEDS = [np.array(v, dtype=float) for v in ([-1.2, 0, 0, 0.6, 0, 0, 0], [-1.6, 0, 0, 1.2, 0, 0, 0], [-0.8, 0, 0, 0.3, 0, 0, 0],
                                             [-1.4, 0.3, 0, 1.0, 0, 0, 0], [-1.4, -0.3, 0, 1.0, 0, 0, 0])]


def make_pose(k, warm):
    """k: one sampled key (dict of arrays). warm: previous arm solutions per side (updated)."""
    root_rot = body_rot(*k["root_rot"], base=upright(k["upright"]) if k["upright"] else None)
    poses = {
        "LowerTorso": (tuple(k["root_pos"]), root_rot),
        "UpperTorso": ((0, 0, 0), body_rot(*k["chest"])),
        "Head": ((0, 0, 0), body_rot(*k["head"])),
    }
    lt = lt_frame_of(k["root_pos"], root_rot)
    misses = {}
    for side, pre in SIDES.items():
        ball = k[f"foot{side}"]
        frot = foot_rot(side, k[f"foot{side}_pitch"], k[f"foot{side}_out"],
                        base=upright(k["upright"]) if k[f"foot{side}_flat"] else None)
        R_ul, R_ll, R_ft, miss = leg_ik(lt, ball, frot, side, k[f"knee{side}"])
        poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
        poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
        poses[pre + "Foot"] = ((0, 0, 0), R_ft)
        misses["foot" + pre] = miss
    for side, pre in SIDES.items():
        target = r15.T(*k[f"hand{side}"]) @ r15.R(hand_rot(side, *k[f"hand{side}_rot"]))
        x, err = G.solve_arm(poses, side, target, warm[side], rot_w=0.35, pole=k[f"elbow{side}"])
        if err > 0.03:   # the solver can stall in a bad bend: retry from a few relaxed starts
            for seed in SEEDS:
                x2, e2 = G.solve_arm(poses, side, target, seed, rot_w=0.35, pole=k[f"elbow{side}"])
                if e2 < err:
                    x, err = x2, e2
        warm[side] = x
        up, low, hand = G.ARM_PARTS[side]
        poses[up] = ((0, 0, 0), G.rotvec(x[0:3]))
        poses[low] = ((0, 0, 0), rx(x[3]))
        poses[hand] = ((0, 0, 0), G.rotvec(x[4:7]))
        misses["hand" + pre] = err
    return poses, misses


def key(**kw):
    """A key: every field a number or vector, so keys can be blended and interpolated."""
    k = dict(RIDE)
    k.update(kw)
    return {n: np.array(v, dtype=float) if isinstance(v, (tuple, list, np.ndarray)) else float(v) for n, v in k.items()}


# blocky arms are short (shoulder->grip about 1.5 studs), so the rider sits forward against the tank
# with the chest well down, like a real sport-bike rider
RIDE_POS = (0.0, 0.0, -0.45)
RIDE_PITCH, RIDE_CHEST, RIDE_HEAD = -28.0, -26.0, 50.0


def _ride():
    d = dict(
        upright=0.0,                         # >0: body/feet are world-upright for a bike leaned this much
        root_pos=RIDE_POS, root_rot=(RIDE_PITCH, 0.0, 0.0),
        chest=(RIDE_CHEST, 0.0, 0.0), head=(RIDE_HEAD, 0.0, 0.0),
    )
    for side in (1, -1):
        d[f"hand{side}"] = grip(side)
        d[f"hand{side}_rot"] = (35.0, 0.0, 0.0)
        d[f"elbow{side}"] = bike_to_hrp([-side * 0.55, -0.05, 0.86])   # elbows out and down
        d[f"foot{side}"] = peg(side)
        d[f"foot{side}_pitch"] = -6.0
        d[f"foot{side}_out"] = 6.0
        d[f"foot{side}_flat"] = 0.0
        d[f"knee{side}"] = (side * 0.35, 0.25, -1.0)                  # knees forward against the tank
    return d


RIDE = _ride()


def steer_key(deg):
    s = 1 if deg > 0 else -1
    return key(hand1=grip(1, deg), **{"hand-1": grip(-1, deg)},
               hand1_rot=(35.0, deg * 0.9, 0.0), **{"hand-1_rot": (35.0, deg * 0.9, 0.0)},
               chest=(RIDE_CHEST, deg * 0.35, 0.0), head=(RIDE_HEAD, deg * 0.4, 0.0),
               root_rot=(RIDE_PITCH, deg * 0.15, s * 2.0))


def lean_key(s):
    """s = +1 hanging off to the left (inside of a left turn), -1 to the right."""
    inside = -s   # HRP x of the inside (left = -X)
    return key(root_pos=(inside * 0.42, -0.04, RIDE_POS[2]), root_rot=(RIDE_PITCH - 2.0, -s * 6.0, s * 8.0),
               chest=(RIDE_CHEST - 2.0, s * 6.0, s * 10.0), head=(RIDE_HEAD + 4.0, s * 8.0, -s * 24.0),
               **{f"knee{-s}": (inside * 1.6, 0.0, -0.7), f"knee{s}": (-inside * 0.1, 0.25, -1.0),
                  f"foot{-s}_out": 18.0},
               **{f"elbow{-s}": bike_to_hrp([s * 0.62, -0.10, 0.70])})


TUCK = key(root_pos=(0.0, -0.02, 0.22), root_rot=(-30.0, 0.0, 0.0), chest=(-32.0, 0.0, 0.0), head=(56.0, 0.0, 0.0),
           elbow1=bike_to_hrp([-0.40, -0.10, 0.78]), **{"elbow-1": bike_to_hrp([0.40, -0.10, 0.78])},
           knee1=(0.1, 0.25, -1.0), **{"knee-1": (-0.1, 0.25, -1.0)})

# stopped: sitting up, feet stay on the pegs (blocky legs are far too short to reach the ground)
STOP = key(root_pos=(0.0, 0.0, -0.20), root_rot=(-28.0, 0.0, 0.0), chest=(-24.0, 0.0, 0.0), head=(42.0, 0.0, 0.0))


def mount_keys():
    """Hop on from the bike's left side: stand by the tank with the left hand on the left grip and
    the right hand on the tank, dip, jump up and swing the right leg over the tail, land on the seat."""
    tank = bike_to_hrp(TANK_TOP)
    seat_front = bike_to_hrp([0.02, 0.16, SEAT[2] + 0.03])
    stand_l, stand_r = W(0.70, 0.02, 0.0), W(0.40, 0.08, 0.0)
    hip_h = 2.19 / S                                   # standing hip height (m)
    on_ground = {"foot1": stand_r, "foot1_flat": 1.0, "foot1_pitch": 0.0, "foot1_out": -8.0, "knee1": (0.0, 0.0, -1.0),
                 "foot-1": stand_l, "foot-1_flat": 1.0, "foot-1_pitch": 0.0, "foot-1_out": 8.0, "knee-1": (0.0, 0.0, -1.0)}
    hands = {"hand1": seat_front, "hand1_rot": (80.0, -40.0, 0.0), "elbow1": W(0.30, 0.20, 0.75),
             "elbow-1": W(0.85, -0.10, 0.75)}
    k0 = key(root_pos=W(0.55, 0.04, hip_h) - bike_to_hrp(SEAT), root_rot=(-6.0, -20.0, 0.0),
             chest=(-4.0, -6.0, 0.0), head=(4.0, -10.0, 0.0), **on_ground, **hands)
    k1 = key(root_pos=W(0.54, 0.05, hip_h - 0.06) - bike_to_hrp(SEAT), root_rot=(-14.0, -20.0, 0.0),
             chest=(-8.0, -6.0, 0.0), head=(12.0, -10.0, 0.0), **on_ground, **hands)
    k2 = key(root_pos=W(0.18, 0.22, SEAT[2] + 0.10) - bike_to_hrp(SEAT), root_rot=(-30.0, -4.0, 6.0),
             chest=(-18.0, -4.0, 0.0), head=(30.0, -6.0, 0.0),
             foot1=W(-0.02, 0.62, SEAT[2] + 0.20), foot1_pitch=-50.0, foot1_out=0.0, knee1=(0.6, 0.6, 0.6),
             **{"foot-1": W(0.36, 0.18, SEAT[2] - 0.38), "foot-1_pitch": -40.0, "foot-1_out": 8.0,
                "knee-1": (-0.3, 0.1, -1.0)},
             hand1=(tank + grip(1)) / 2 + np.array([0, 0.25, 0]), hand1_rot=(50.0, -10.0, 0.0),
             elbow1=W(-0.30, 0.0, 0.9), **{"elbow-1": W(0.70, -0.10, 0.85)})
    k3 = key(root_pos=STOP["root_pos"], root_rot=(-28.0, 0.0, 2.0),
             chest=(-22.0, 0.0, 0.0), head=(36.0, 0.0, 0.0),
             foot1=peg(1) + np.array([0.25, 0.30, -0.10]), foot1_pitch=-25.0,
             **{"foot-1": peg(-1) + np.array([-0.15, 0.10, -0.10]), "foot-1_pitch": -15.0})
    return [(0.0, k0), (0.20, k1), (0.46, k2), (0.70, k3), (0.92, STOP), (1.05, STOP)]


# ------------------------------------------------------------------ sampling + output
def interp(keys, t):
    """Catmull-Rom through the keys (clamped at the ends)."""
    times = [kt for kt, _ in keys]
    if t <= times[0]:
        return keys[0][1]
    if t >= times[-1]:
        return keys[-1][1]
    i = max(j for j in range(len(times) - 1) if times[j] <= t)
    t0, t1 = times[i], times[i + 1]
    u = (t - t0) / (t1 - t0)
    p0 = keys[max(0, i - 1)][1]
    p1, p2 = keys[i][1], keys[i + 1][1]
    p3 = keys[min(len(keys) - 1, i + 2)][1]
    out = {}
    for n in p1:
        a, b, c, d = p0[n], p1[n], p2[n], p3[n]
        if n == "upright" or n.endswith("_flat"):
            out[n] = b + (c - b) * (u * u * (3 - 2 * u))
            continue
        out[n] = 0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
    return out


def clip_frames(keys, loop=False):
    warm = {1: np.array([-1.2, 0.0, 0.0, 0.6, 0, 0, 0]), -1: np.array([-1.2, 0.0, 0.0, 0.6, 0, 0, 0])}
    end = keys[-1][0]
    n = max(1, int(round(end * FPS)))
    frames, worst = [], {}
    for i in range(n + 1):
        t = end * i / n
        poses, miss = make_pose(interp(keys, t), warm)
        frames.append((t, poses))
        for k, v in miss.items():
            worst[k] = max(worst.get(k, 0.0), v)
    return frames, worst


def pose_frames(k, length=1.0):
    """A held pose as a short looping clip (two identical keys)."""
    return clip_frames([(0.0, k), (length, k)])


ALL = list(r15.ORDER)


def clips():
    out = {
        "Ride": pose_frames(key()),
        "SteerLeft": pose_frames(steer_key(STEER_LOCK)),
        "SteerRight": pose_frames(steer_key(-STEER_LOCK)),
        "LeanLeft": pose_frames(lean_key(1)),
        "LeanRight": pose_frames(lean_key(-1)),
        "Tuck": pose_frames(TUCK),
        "Stop": pose_frames(STOP),
    }
    mount, worst = clip_frames(mount_keys())
    out["Mount"] = (mount, worst)
    end = mount[-1][0]
    out["Dismount"] = ([(end - t, p) for t, p in reversed(mount)], worst)
    return out


def dump(path, frames_by_clip):
    """Part frames (HRP space) per clip for the Blender preview."""
    data = {}
    for name, (frames, _) in frames_by_clip.items():
        data[name] = [{"t": t, "parts": {p: r15.solve(poses)[p].tolist() for p in ALL}} for t, poses in frames]
    json.dump({"S": S, "seat": SEAT.tolist(), "hrp_above_seat": HRP_ABOVE_SEAT, "stop_lean": STOP_LEAN,
               "steer_lock": STEER_LOCK, "clips": data}, open(path, "w"))


def main():
    os.makedirs(L.OUT, exist_ok=True)
    loops = {"Mount": False, "Dismount": False}
    all_clips = clips()
    for name, (frames, worst) in all_clips.items():
        full = f"Tulevo_Bike{name}"
        with open(os.path.join(L.OUT, f"{full}.rbxmx"), "w") as fh:
            fh.write(G.sequence(full, frames, ALL, loops.get(name, True), priority=2))
        print(f"{full}: {len(frames)} frames {frames[-1][0]:.2f}s  misses " +
              " ".join(f"{k}={v:.2f}" for k, v in worst.items() if v > 0.02))
    if "--dump" in sys.argv:
        dump(sys.argv[sys.argv.index("--dump") + 1], all_clips)


if __name__ == "__main__":
    main()
