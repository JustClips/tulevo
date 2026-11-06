"""Rifle animations (CarbineRifle) for the default R15 rig, built from code.

  python3 art/anim/gun.py [--preview]  -> art/out/anims/Weapon_Rifle_*.rbxmx (+ .png/.gif previews)

The gun is welded to the right hand (server: Weapons/GunModel, same HAND_TO_GUN offset as
here), so every clip is "where should the gun be?": each frame places the gun, then both arms
are solved with IK so the right hand holds the pistol grip and the left hand cups the
handguard. Arms-only clips (Hold, Sprint, Tuck, Air, Lowered, Reload, Equip, Fire) only key
the arms, so the legs, hips and chest keep doing what the Movement system plays (walk, roll,
jump...). Aim also keys the chest and head (shouldered rifle, bladed stance); the game turns
the waist on top of that to aim up/down and to strafe.

Gun space: studs, origin = pistol grip hold point, muzzle toward -Z, top = +Y, +X = the
shooter's right (as the model imports into Roblox; measured on asset 108772838491349).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locomotion as L  # noqa: E402
import r15  # noqa: E402

D = math.radians
rx, ry, rz = L.rx, L.ry, L.rz

# In-game the model is scaled by this (Config.Weapons.GunScale). The carbine is exported at
# x3.6 studs per meter; blocky R15 bodies are wide and chunky, so at 1.0 it reads small in hand.
GUN_SCALE = 1.7
_P = {  # gun points at scale 1 (from the imported model + art/models/CarbineRifle/meta.json)
    "Muzzle": (0, 0.269, -1.634),
    "Grip2": (0, 0.192, -1.062),     # support hand under the handguard (front)
    "Support": (0, 0.200, -0.60),    # where our left hand actually holds (handguard, back half)
    "MagWell": (0, 0.211, -0.475),
    "MagBottom": (0, -0.30, -0.52),
    "MagCenter": (0, -0.042, -0.502),  # Magazine part centre (the mag is its own part)
    "Sight": (0, 0.494, -0.030),
    "Butt": (0, 0.22, 0.683),
    "Charge": (0, 0.42, 0.25),       # charging handle
}
P = {k: np.array(v) * GUN_SCALE for k, v in _P.items()}

# Hand -> gun: the grip point sits in the fist (RightGripAttachment, 0.158 below the hand
# centre). Fingers (hand -Y) point roughly along the barrel, the grip runs up out of the top
# of the fist (hand -Z), tilted 22 deg like an AR-15 pistol grip. Gun +X = hand +X.
_up = np.array([0, math.cos(D(22)), -math.sin(D(22))])   # up the grip, in gun space
_gx = np.array([1.0, 0, 0])
_gw = np.cross(_gx, _up)
_hand_basis = np.column_stack([[1, 0, 0], [0, 0, -1], [0, 1, 0]]).astype(float)
G_IN_HAND = _hand_basis @ np.column_stack([_gx, _up, _gw]).T   # gun axes -> hand axes
GRIP_OFFSET = np.array([0, -0.158, 0])
HAND_TO_GUN = r15.T(*GRIP_OFFSET) @ r15.R(G_IN_HAND)


def hand_to_gun_cframe():
    """The Weld C0 (RightHand -> gun origin) as Roblox CFrame components."""
    m = HAND_TO_GUN
    return [*m[:3, 3], *m[:3, :3].flatten()]


# ----------------------------------------------------------------------------- IK
def rotvec(v):
    a = np.linalg.norm(v)
    if a < 1e-9:
        return np.eye(3)
    k = v / a
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def log_rot(m):
    c = max(-1.0, min(1.0, (np.trace(m) - 1) / 2))
    a = math.acos(c)
    if a < 1e-6:
        return np.zeros(3)
    v = np.array([m[2, 1] - m[1, 2], m[0, 2] - m[2, 0], m[1, 0] - m[0, 1]])
    return v * a / (2 * math.sin(a))


ARM_PARTS = {1: ("RightUpperArm", "RightLowerArm", "RightHand"), -1: ("LeftUpperArm", "LeftLowerArm", "LeftHand")}


def arm_frames(base_poses, side, x):
    poses = dict(base_poses)
    up, low, hand = ARM_PARTS[side]
    poses[up] = ((0, 0, 0), rotvec(x[0:3]))
    poses[low] = ((0, 0, 0), rx(x[3]))
    poses[hand] = ((0, 0, 0), rotvec(x[4:7]))
    return r15.solve(poses), poses


_INV = {}


def _inv_t(c):
    if c not in _INV:
        _INV[c] = np.linalg.inv(r15.T(*c))
    return _INV[c]


def fast_arm(ut, side, x):
    """Upper arm, lower arm and hand frames for arm params x, given the UpperTorso frame."""
    up, low, hand = ARM_PARTS[side]
    out = {}
    parent = ut
    for part, rot in ((up, rotvec(x[0:3])), (low, rx(x[3])), (hand, rotvec(x[4:7]))):
        _, c0, c1 = r15.JOINTS[part]
        parent = parent @ r15.T(*c0) @ r15.R(rot) @ _inv_t(c1)
        out[part] = parent
    return out


def solve_arm(base_poses, side, target, x0, rot_w=1.0, pole=None):
    """Levenberg-Marquardt on (shoulder rotvec, elbow hinge, wrist rotvec) so the hand's grip
    point/orientation reach target (4x4, HRP space). pole = world point the elbow leans toward."""
    up, low, hand = ARM_PARTS[side]
    ut = r15.solve(base_poses)["UpperTorso"]

    def residual(x):
        f = fast_arm(ut, side, x)
        h = f[hand] @ r15.T(*GRIP_OFFSET)
        r = [(h[:3, 3] - target[:3, 3]) * 12.0, log_rot(target[:3, :3].T @ h[:3, :3]) * rot_w]
        if pole is not None:
            elbow = (f[low] @ np.array([0, 0.275, 0, 1]))[:3]
            r.append((elbow - pole) * 0.35)
        r.append(x[4:7] * 0.08)                                 # relaxed wrist
        r.append(np.array([min(0, x[3]), max(0, x[3] - D(150))]) * 10)  # elbow only bends one way
        return np.concatenate(r)

    x = np.array(x0, dtype=float)
    lam = 1e-2
    cur = residual(x)
    for _ in range(120):
        J = np.zeros((len(cur), len(x)))
        for i in range(len(x)):
            dx = np.zeros(len(x))
            dx[i] = 1e-5
            J[:, i] = (residual(x + dx) - cur) / 1e-5
        A = J.T @ J
        step = np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-6), -J.T @ cur)
        nxt = residual(x + step)
        if nxt @ nxt < cur @ cur:
            x, cur, lam = x + step, nxt, lam * 0.3
            if np.linalg.norm(step) < 1e-6:
                break
        else:
            lam *= 4
    f = fast_arm(ut, side, x)
    err = np.linalg.norm((f[hand] @ r15.T(*GRIP_OFFSET))[:3, 3] - target[:3, 3])
    return x, err


# ------------------------------------------------------------------------- gun placement
def gun_frame(pos, pitch=0.0, yaw=0.0, roll=0.0):
    """Gun origin (grip point) at pos; muzzle pitched up / yawed left / rolled (degrees)."""
    return r15.T(*pos) @ r15.R(ry(D(yaw)) @ rx(D(pitch)) @ rz(D(roll)))


def support_target(gun, point="Support"):
    """Left hand: palm up under the handguard, fingers wrapping round to the right side,
    forearm coming in from below-left."""
    p = gun @ np.array([*P[point], 1])
    rot = gun[:3, :3] @ np.column_stack([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]).astype(float) @ rz(D(-25)) @ rx(D(-20))
    t = np.eye(4)
    t[:3, :3] = rot
    t[:3, 3] = p[:3] - gun[:3, 1] * 0.09  # hand sits just under the handguard
    return t


def ut_frame(poses):
    return r15.solve(poses)["UpperTorso"]


def gun_pose(base, gun_ut, left_point="Support", left_target=None, warm=None, poles=True):
    """Solve both arms for a gun placed in UpperTorso space. Returns (poses, errors, x)."""
    ut = ut_frame(base)
    gun = ut @ gun_ut
    rt = gun @ np.linalg.inv(r15.R(G_IN_HAND))  # target for the hand's grip point frame
    lt = left_target(gun, ut) if left_target else support_target(gun, left_point)
    warm = warm or {}
    # elbows hang down and a little out
    rpole = (ut @ np.array([1.6, -1.2, 0.3, 1]))[:3] if poles else None
    lpole = (ut @ np.array([-1.5, -1.3, 0.0, 1]))[:3] if poles else None
    xr, er = solve_arm(base, 1, rt, warm.get(1, [D(60), 0, 0, D(60), 0, 0, 0]), 20.0, rpole)
    xl, el = solve_arm(base, -1, lt, warm.get(-1, [D(60), 0, 0, D(60), 0, 0, 0]), 0.35, lpole)
    _, poses = arm_frames(base, 1, xr)
    _, poses = arm_frames(poses, -1, xl)
    return poses, (er, el), {1: xr, -1: xl}


# ------------------------------------------------------------------------------- clips
ARMS = ["RightUpperArm", "RightLowerArm", "RightHand", "LeftUpperArm", "LeftLowerArm", "LeftHand"]
AIM_KEYS = ARMS + ["UpperTorso", "Head"]


def base_pose(torso=None, head=None):
    b = {}
    if torso is not None:
        b["UpperTorso"] = ((0, 0, 0), torso)
    if head is not None:
        b["Head"] = ((0, 0, 0), head)
    return b


# Low ready (GTA rifle idle/walk): grip by the right hip, muzzle forward and down, angled a
# little across the body.
HOLD = dict(pos=(0.28, -0.02, -1.0), pitch=-18, yaw=48, roll=-15)
# Shouldered: chest bladed (right shoulder back), head turned back to the sights and leaning
# onto the stock.
AIM_TORSO = ry(D(-48)) @ rx(D(-4))
AIM_HEAD = ry(D(40)) @ rz(D(-10)) @ rx(D(-8))
# in UpperTorso space: butt in the right shoulder pocket, yaw undoes the chest turn so the
# rifle points straight ahead of the character
def _grip_from_butt(butt, pitch, yaw, roll=0.0):
    rot = ry(D(yaw)) @ rx(D(pitch)) @ rz(D(roll))
    return tuple(np.array(butt) - rot @ P["Butt"])


# yaw/pitch/roll are exactly AIM_TORSO undone (decomposed as ry @ rx @ rz), so once GunPose locks
# the chest to the aim the barrel points dead along the camera with the sights level: first-person
# aiming puts the eye on the sight line and the sights must sit on the crosshair.
AIM = dict(pos=_grip_from_butt((0.55, 0.8, -0.45), 2.675, 48.069, 2.975), pitch=2.675, yaw=48.069, roll=2.975)
# Sprint: low ready like the walk carry but pulled in and tipped further down (the sprint lean
# points it down the way you run). Not "port arms" (muzzle up-left) - Dev found that odd.
# A more forward muzzle isn't possible: below ~46 deg yaw either the stock runs into the chest
# or the left hand can't reach the handguard.
SPRINT = dict(pos=(0.25, 0.05, -0.95), pitch=-32, yaw=48, roll=0)
# Roll / falling tuck: rifle pulled in tight, muzzle up.
TUCK = dict(pos=(0.30, -0.30, -1.05), pitch=58, yaw=34, roll=-20)
# Near a wall: muzzle down steeply, close to the body.
# Crouched, not aiming: rifle carried up at a high ready (the crouch leans the chest forward,
# so in the world the muzzle ends up pointing a little down the way you're going)
CROUCH_READY = dict(pos=(0.35, 0.3, -0.95), pitch=0, yaw=46, roll=-8)
LOWERED = dict(pos=(0.28, 0.32, -0.82), pitch=-58, yaw=36, roll=-10)


def placed(d, **over):
    d = dict(d, **over)
    return gun_frame(d["pos"], d["pitch"], d["yaw"], d["roll"])


def lerp_d(a, b, u):
    out = {}
    for k in a:
        if isinstance(a[k], tuple):
            out[k] = tuple(L.lerp(x, y, u) for x, y in zip(a[k], b[k]))
        else:
            out[k] = L.lerp(a[k], b[k], u)
    return out


def sway(t, period, amp_pos=0.015, amp_rot=0.8, phase=0.0):
    w = 2 * math.pi * t / period
    return dict(dp=(amp_pos * 0.6 * math.sin(w * 2 + phase), amp_pos * math.sin(w + phase), amp_pos * 0.5 * math.sin(w * 3 + 1)),
                dpitch=amp_rot * math.sin(w + 0.7 + phase), dyaw=amp_rot * 0.6 * math.sin(2 * w + phase))


def with_sway(d, s):
    return dict(d, pos=tuple(a + b for a, b in zip(d["pos"], s["dp"])), pitch=d["pitch"] + s["dpitch"], yaw=d["yaw"] + s["dyaw"])


def loop_clip(d, period, steps, torso=None, head=None, amp_pos=0.015, amp_rot=0.8, bob=None):
    frames, warm, worst = [], None, 0
    for i in range(steps + 1):
        t = period * i / steps
        dd = with_sway(d, sway(t, period, amp_pos, amp_rot))
        if bob:
            dd = bob(dd, t / period)
        poses, err, warm = gun_pose(base_pose(torso, head), placed(dd), warm=warm)
        worst = max(worst, *err)
        frames.append((t, poses))
    return frames, worst


def keyed_clip(keys, fps=30, torso=None, head=None, left=None):
    """keys: [(time, gun dict)], smooth between keys. left(t, gun, ut) -> optional left-hand
    target override (reload)."""
    end = keys[-1][0]
    n = max(2, round(end * fps))
    frames, warm, worst = [], None, 0
    for i in range(n + 1):
        t = end * i / n
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                d = lerp_d(a, b, L.smooth((t - t0) / max(1e-6, t1 - t0)))
                break
        lt = (lambda gun, ut, t=t: left(t, gun, ut)) if left else None
        poses, err, warm = gun_pose(base_pose(torso, head), placed(d), left_target=lt, warm=warm)
        worst = max(worst, *err)
        frames.append((t, poses))
    return frames, worst


# Reload timeline (seconds at playback speed 1). The server moves the real parts on the same
# beats (src/server/Weapons/GunModel.luau RELOAD_BEATS), so keep them in sync:
#   grab     left hand has the old mag (weld to the hand, MAG_IN_HAND)
#   drop     old mag falls away
#   flap     the pouch flap starts to open (tweened over FLAP_TIME), the hand flicks it up
#   take     hand on the mag top in the pouch (PouchMag piece follows the hand)
#   swap     piece pulled 0.33 up: the full mag takes its place in the hand (MAG_DRAW_IN_HAND)
#            (the rest of it is still inside the closed pouch box, so nothing pops)
#   partial  mag pushed into the well, PARTIAL short of seated: it stays in the gun, the hand
#            drops under it
#   seated   the palm slaps it home
RELOAD = dict(grab=0.40, out=0.60, drop=0.70, flap=0.90, take=1.10, swap=1.20, partial=1.58,
              seated=1.74, length=2.45)
FLAP_TIME = 0.1
PARTIAL = 0.2           # studs the new mag sits short of seated before the slap
SWAP_LIFT = 0.33        # how far the piece is pulled up when the full mag takes over

# Rifle mag pouches on the vest front (art/models/ArmorVest/meta.json, Server/Armor places the
# vest box centre at BOX_OFFSET): the mag top (MagWell point) standing in each pouch, in
# UpperTorso space. 1 = wearer's left, 2 = centre, 3 = wearer's right. The mags stand with the
# gun's muzzle direction pointing to the wearer's right (POUCH_ROT: gun axes -> torso axes),
# so their left side faces out.
POUCH_MAGS = {1: (-0.5525, -0.47, -0.7688), 2: (-0.0125, -0.47, -0.785), 3: (0.5275, -0.47, -0.7688)}
POUCH_FRONT = {1: -0.894, 2: -0.91, 3: -0.894}   # front of each closed flap (z)
POUCH_ROT = ry(D(-90))
# The left hand reloads from pouches 1 and 2. Pouch 3 is out of reach: the blocky arm is ~2
# studs long and that mag is ~2.15 from the left shoulder (the IK missed by 0.25).
RELOAD_POUCHES = (1, 2)
# no vest (or an old vest without pouch parts): the mag comes from the left hip
POCKET_MAG = (-0.95, -0.55, -0.45)


def mag_grip_in_gun():
    """Left hand palming the magazine from below (grip-point frame, gun space)."""
    rot = np.column_stack([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]).astype(float) @ rz(D(-25)) @ rx(D(-20))
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = P["MagBottom"] + np.array([0, -0.1, 0])
    return m


def mag_draw_grip_in_gun():
    """Left hand on the left side of the magazine's top part (how it comes out of a pouch and
    goes into the well), grip-point frame in gun space."""
    m = mag_grip_in_gun()
    m[:3, 3] = P["MagWell"] + np.array([0, -0.26, 0])
    return m


def mag_in_hand(grip=None):
    """Magazine part frame relative to the LeftHand while it's held (for the Weld C0)."""
    return r15.T(*GRIP_OFFSET) @ np.linalg.inv(grip if grip is not None else mag_grip_in_gun()) @ r15.T(*P["MagCenter"])


def pouch_mag(top, rot=None):
    """Where the gun would be (torso space) if the magazine stood with its top at `top`."""
    rot = POUCH_ROT if rot is None else rot
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = np.array(top) - rot @ P["MagWell"]
    return m


def reload_clip(pouch=None, flap_closed=True):
    """Rifle tilts so the mag faces you; left hand grabs the mag, pulls it straight down out of
    the well and tosses it. Then (pouch 1-3) flicks the pouch flap open (unless it's open
    already), takes the mag out of the pouch, or (pouch None) takes one from the left hip;
    pushes it up into the well, lets go, slaps it home, racks the charging handle and goes
    back to the handguard."""
    r = RELOAD
    tilt = dict(HOLD, pos=(0.2, 0.12, -0.9), pitch=2, yaw=40, roll=-35)
    keys = [(0.0, HOLD), (0.25, tilt), (1.9, tilt), (2.2, HOLD), (r["length"], HOLD)]
    grip = mag_grip_in_gun()
    draw = mag_draw_grip_in_gun()
    if pouch:
        store = pouch_mag(POUCH_MAGS[pouch])
    else:
        store = pouch_mag(POCKET_MAG, ry(D(-90)) @ rz(D(15)))

    def at(gun, down=0.0, back=0.0, side=0.0):
        m = gun @ grip
        m[:3, 3] += gun[:3, :3] @ np.array([side, -down, back])
        return m

    def drawn(gun, down):
        """Draw grip on a mag lined up under the well, `down` studs short of seated."""
        return gun @ r15.T(0, -down, 0) @ draw

    def stored(ut, up=0.0, fwd=0.0):
        """Draw grip on the mag in its pouch, moved up / forward (torso space)."""
        return ut @ r15.T(0, up, -fwd) @ store @ draw

    def left(t, gun, ut):
        hand = support_target(gun)
        seated = at(gun)
        out = at(gun, down=0.62 * GUN_SCALE)
        toss = at(gun, down=0.8 * GUN_SCALE, side=-0.5)
        charge = support_target(gun)
        charge[:3, 3] = (gun @ np.array([*(P["Charge"] + np.array([-0.15, 0.1, 0])), 1]))[:3]
        charge_back = charge.copy()
        charge_back[:3, 3] += gun[:3, 2] * 0.35
        path = [(0.0, hand), (0.25, hand), (r["grab"], seated), (r["out"], out), (r["drop"], toss)]
        if pouch and flap_closed:
            front = POUCH_MAGS[pouch][2] - POUCH_FRONT[pouch]  # mag centre -> flap front
            # fingers under the front of the lid, then up and back over the top: it flips open
            path += [(r["flap"] - 0.02, stored(ut, up=0.02, fwd=front + 0.06)),
                     (r["flap"] + FLAP_TIME, stored(ut, up=0.36, fwd=0.04))]
        else:
            path += [(r["flap"] + 0.02, stored(ut, up=0.28, fwd=0.12))]
        path += [(r["take"], stored(ut)), (r["swap"], stored(ut, up=SWAP_LIFT)),
                 (1.32, stored(ut, up=0.95, fwd=0.05)), (1.48, drawn(gun, 0.42)), (r["partial"], drawn(gun, PARTIAL)),
                 (1.66, at(gun, down=PARTIAL + 0.25)), (r["seated"], at(gun, down=-0.03)), (1.80, seated),
                 (1.92, charge), (2.01, charge_back), (2.08, charge), (2.3, hand), (r["length"], hand)]
        for (t0, a), (t1, b) in zip(path, path[1:]):
            if t0 <= t <= t1:
                u = L.smooth((t - t0) / max(1e-6, t1 - t0))
                m = np.eye(4)
                m[:3, 3] = L.lerp(a[:3, 3], b[:3, 3], u)
                m[:3, :3] = a[:3, :3] @ rotvec(log_rot(a[:3, :3].T @ b[:3, :3]) * u)
                return m
        return hand

    return keyed_clip(keys, left=left)


def fire_clip():
    """One shot while aiming: the rifle kicks back into the shoulder and the muzzle climbs, then
    settles (0.13 s, arms only, on top of Aim)."""
    kick = dict(AIM, pos=(AIM["pos"][0], AIM["pos"][1] + 0.02, AIM["pos"][2] + 0.13), pitch=AIM["pitch"] + 2)
    return keyed_clip([(0.0, AIM), (0.03, kick), (0.13, AIM)], fps=60, torso=AIM_TORSO, head=AIM_HEAD)


def equip_clip():
    """Bring the rifle up from hanging at the right side to the low ready."""
    hang = dict(LOWERED, pitch=-64)
    mid = dict(pos=(0.3, 0.05, -0.9), pitch=-40, yaw=44, roll=-12)
    return keyed_clip([(0.0, hang), (0.18, mid), (0.4, HOLD)])


def sprint_bob(d, u):
    w = 2 * math.pi * u * 2  # two bounces per sprint cycle (one per step)
    return dict(d, pos=(d["pos"][0] + 0.03 * math.sin(w / 2), d["pos"][1] + 0.06 * math.sin(w), d["pos"][2]),
                yaw=d["yaw"] + 3 * math.sin(w / 2), pitch=d["pitch"] + 2 * math.cos(w))


def air_bob(d, u):
    w = 2 * math.pi * u
    return dict(d, pos=(d["pos"][0] + 0.04 * math.sin(w), d["pos"][1] + 0.08 * math.sin(w + 1), d["pos"][2]),
                pitch=d["pitch"] + 6 * math.sin(w), roll=d["roll"] + 5 * math.sin(w + 2))


# --- jumping with the rifle -------------------------------------------------------------
# One-shots synced to the both-feet jump (Movement): the gun dips with the knee bend, lags
# behind on take-off then springs up past the air pose and settles, and on landing the
# impact pushes it down and it bounces back. The springy part is the follow-through: arms
# and hands keep moving a little after the body stops.
AIR_POSE = dict(HOLD, pos=(HOLD["pos"][0], HOLD["pos"][1] + 0.06, HOLD["pos"][2]), pitch=-10)
DIP = dict(HOLD, pos=(HOLD["pos"][0] - 0.03, HOLD["pos"][1] - 0.08, HOLD["pos"][2] + 0.12), pitch=HOLD["pitch"] - 8, roll=HOLD["roll"] - 4)


def func_clip(fn, duration, fps=30):
    n = max(2, round(duration * fps))
    frames, warm, worst = [], None, 0
    for i in range(n + 1):
        t = duration * i / n
        poses, err, warm = gun_pose(base_pose(), placed(fn(t)), warm=warm)
        worst = max(worst, *err)
        frames.append((t, poses))
    return frames, worst


def spring(t, amp, k, w, phase=0.0):
    return amp * math.exp(-k * t) * math.sin(w * t + phase)


def jump_prep_clip():
    def fn(t):
        return lerp_d(HOLD, DIP, L.smooth(min(1, t / 0.12)))
    return func_clip(fn, 0.12)


def jump_up_clip():
    def fn(t):
        d = lerp_d(DIP, AIR_POSE, L.smooth(min(1, t / 0.22)))
        dy = -spring(t, 0.13, 5.5, 13, 1.2)       # lags low as the body shoots up, then overshoots
        dx = spring(t, 0.04, 5, 9)
        return dict(d, pos=(d["pos"][0] + dx, d["pos"][1] + dy, d["pos"][2]),
                    pitch=d["pitch"] + spring(t, 9, 5.5, 13, 0.6), roll=d["roll"] + spring(t, 5, 5, 10, 2.0))
    return func_clip(fn, 0.6)


def land_clip():
    def fn(t):
        d = lerp_d(AIR_POSE, HOLD, L.smooth(min(1, t / 0.3)))
        dy = -spring(t, 0.16, 6, 13)             # impact pushes it down, bounces back up, settles
        return dict(d, pos=(d["pos"][0] + spring(t, 0.03, 6, 11, 1), d["pos"][1] + dy, d["pos"][2] - spring(t, 0.05, 6, 13)),
                    pitch=d["pitch"] - spring(t, 8, 6, 13, 0.4), roll=d["roll"] + spring(t, 4, 6, 9, 1.5))
    return func_clip(fn, 0.5)


# ---------------------------------------------------------------- holster / draw
# Gun on the back, in UpperTorso space: must equal BACK in src/server/Weapons/GunModel.luau.
# Muzzle DOWN toward the left hip, stock up behind the right shoulder, lying flat (gun's right
# side facing out), so the pistol grip sits high on the right shoulder blade: the right hand
# reaches it over the shoulder with the elbow up (a grip low on the back twisted the arm round
# behind the back, Dev 2026-11-05). Out at z 0.95 so it sits on the vest's back plate.
SLING_TILT = D(25)  # from vertical
SLUNG = np.eye(4)
SLUNG[:3, 0] = [0, 0, 1]                                                  # gun right side: out
SLUNG[:3, 1] = [math.cos(SLING_TILT), -math.sin(SLING_TILT), 0]           # top: down-right
SLUNG[:3, 2] = [math.sin(SLING_TILT), math.cos(SLING_TILT), 0]            # butt: up-right
SLUNG[:3, 3] = [0.45, 0.6, 0.95]

# Holster timeline (seconds). The right hand lifts the rifle muzzle-up in front of the right
# shoulder, flips it back over the shoulder (muzzle swings back and down behind you), and
# slides it down onto the back; it waits there while the server welds it to the back (swap),
# then the hand comes back over the shoulder and drops to the side. Draw is the same motion
# backwards and a bit quicker. GunModel.luau has the same beats for the weld swaps.
HOLSTER = dict(release=0.12, slung=0.56, swap=0.58, letgo=0.78, length=1.05)
DRAW_TIME = 0.8  # draw plays the holster frames reversed, squeezed to this share of the time


def _slerp(a, b, u):
    return a @ rotvec(log_rot(a.T @ b) * u)


def _catmull(p0, p1, p2, p3, u):
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


def _gun_at(pos, rot):
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = pos
    return m


def holster_path():
    """Gun frames (UpperTorso space) from the low ready to the back, by progress 0..1."""
    hold = placed(HOLD)
    raise_ = gun_frame((0.85, 0.15, -0.8), 80, 20, 0)                  # muzzle up, front right
    over = _gun_at([1.15, 1.2, -0.15], raise_[:3, :3] @ rx(D(90)))       # hand by the ear, muzzle pointing back
    behind = _gun_at(SLUNG[:3, 3] + np.array([0.2, 0.55, 0.0]), SLUNG[:3, :3])  # above its place
    keys = [hold, raise_, over, behind, SLUNG]
    us = [0.0, 0.3, 0.55, 0.8, 1.0]

    def at(u):
        for i in range(len(keys) - 1):
            if us[i] <= u <= us[i + 1]:
                v = (u - us[i]) / (us[i + 1] - us[i])
                p = [k[:3, 3] for k in keys]
                p0 = p[max(0, i - 1)]
                p3 = p[min(len(p) - 1, i + 2)]
                m = np.eye(4)
                m[:3, 3] = _catmull(p0, p[i], p[i + 1], p3, v)
                m[:3, :3] = _slerp(keys[i][:3, :3], keys[i + 1][:3, :3], v)
                return m
        return SLUNG.copy()
    return at


def holster_frames(fps=30):
    h = HOLSTER
    path = holster_path()
    n = round(h["length"] * fps)
    base = base_pose()
    ut = ut_frame(base)
    frames, worst = [], 0
    xr = [D(60), 0, 0, D(60), 0, 0, 0]
    xl = [D(60), 0, 0, D(60), 0, 0, 0]
    xl_release = None
    xr_letgo = None
    low_pole, high_pole = np.array([1.6, -1.2, 0.3]), np.array([1.4, 1.8, -0.3])
    lpole = (ut @ np.array([-1.5, -1.3, 0.0, 1]))[:3]
    for i in range(n + 1):
        t = h["length"] * i / n
        u = L.smooth(min(1.0, t / h["slung"]))
        gun = ut @ path(u)
        if t <= h["letgo"]:
            rt = gun @ np.linalg.inv(r15.R(G_IN_HAND))
            # elbow hangs low at the front, comes up as the rifle goes over the shoulder
            k = L.smooth(min(1.0, max(0.0, (u - 0.15) / 0.35)))
            rpole = (ut @ np.array([*(low_pole + (high_pole - low_pole) * k), 1]))[:3]
            xr, er = solve_arm(base, 1, rt, xr, 20.0, rpole)
            if er > 0.05:
                print(f"  holster t={t:.2f}: right hand misses the grip by {er:.3f}")
            worst = max(worst, er)
            xr_letgo = np.array(xr)
            xr_now = xr
            grip_off = rt[:3, 3].copy()
        elif t <= h["letgo"] + 0.12:
            # let go: the hand comes up off the grip and back over the right shoulder
            v = L.smooth((t - h["letgo"]) / 0.12)
            tgt = np.eye(4)
            tgt[:3, :3] = rt[:3, :3]
            tgt[:3, 3] = grip_off + ((ut @ np.array([1.2, 1.5, 0.15, 1]))[:3] - grip_off) * v
            xr, _ = solve_arm(base, 1, tgt, xr, 0.3, rpole)
            xr_lift = np.array(xr)
            xr_now = xr
        else:
            # ...and drops down past the side of the shoulder to hang
            v = (t - h["letgo"] - 0.12) / (h["length"] - h["letgo"] - 0.12)
            if v < 0.6:
                w = L.smooth(v / 0.6)
                a, b = np.array([1.2, 1.5, 0.15]), np.array([1.75, 0.2, 0.05])
                tgt = np.eye(4)
                tgt[:3, :3] = rt[:3, :3]
                tgt[:3, 3] = (ut @ np.array([*(a + (b - a) * w), 1]))[:3]
                xr, _ = solve_arm(base, 1, tgt, xr, 0.05, (ut @ np.array([2.2, 0.8, 0.6, 1]))[:3])
                xr_side = np.array(xr)
                xr_now = xr
            else:
                xr_now = xr_side * (1 - L.smooth((v - 0.6) / 0.4))
        if t <= h["release"]:
            xl, el = solve_arm(base, -1, support_target(gun), xl, 0.35, lpole)
            worst = max(worst, el)
            xl_release = np.array(xl)
            xl_now = xl
        else:
            v = L.smooth(min(1.0, (t - h["release"]) / 0.3))
            xl_now = xl_release * (1 - v)
        _, poses = arm_frames(base, 1, xr_now)
        _, poses = arm_frames(poses, -1, xl_now)
        frames.append((t, poses))
    return frames, worst


def holster_clip():
    return holster_frames()


def draw_clip():
    frames, worst = holster_frames()
    end = HOLSTER["length"]
    return [((end - t) * DRAW_TIME, p) for t, p in reversed(frames)], worst


def draw_beats():
    """Draw beats (seconds): when the hand has the grip on the back (weld to hand) and the end."""
    h = HOLSTER
    return dict(swap=round((h["length"] - h["letgo"]) * DRAW_TIME + 0.04, 3), length=round(h["length"] * DRAW_TIME, 3))


def build():
    clips = {
        "Weapon_Rifle_Hold": (*loop_clip(HOLD, 3.0, 30), True, ARMS),
        "Weapon_Rifle_Aim": (*loop_clip(AIM, 2.4, 24, AIM_TORSO, AIM_HEAD, amp_pos=0.003, amp_rot=0.12), True, AIM_KEYS),
        "Weapon_Rifle_Sprint": (*loop_clip(SPRINT, 0.8, 16, amp_pos=0, amp_rot=0, bob=sprint_bob), True, ARMS),
        "Weapon_Rifle_Tuck": (*loop_clip(TUCK, 1.0, 10, amp_pos=0.01, amp_rot=0.5), True, ARMS),
        "Weapon_Rifle_Air": (*loop_clip(AIR_POSE, 0.9, 18, amp_pos=0, amp_rot=0, bob=air_bob), True, ARMS),
        "Weapon_Rifle_JumpPrep": (*jump_prep_clip(), False, ARMS),
        "Weapon_Rifle_JumpUp": (*jump_up_clip(), False, ARMS),
        "Weapon_Rifle_Land": (*land_clip(), False, ARMS),
        "Weapon_Rifle_Lowered": (*loop_clip(LOWERED, 3.0, 15), True, ARMS),
        "Weapon_Rifle_CrouchHold": (*loop_clip(CROUCH_READY, 3.0, 15, amp_pos=0.01, amp_rot=0.5), True, ARMS),
        "Weapon_Rifle_Fire": (*fire_clip(), False, ARMS),
        "Weapon_Rifle_Reload": (*reload_clip(), False, ARMS),
        # from the vest's rifle mag pouches (Client/Weapons picks the next one): flap shut ->
        # the hand flicks it open first; ...Open: it's open already
        **{f"Weapon_Rifle_ReloadPouch{k}{'' if shut else 'Open'}": (*reload_clip(k, shut), False, ARMS)
           for k in RELOAD_POUCHES for shut in (True, False)},
        "Weapon_Rifle_Equip": (*equip_clip(), False, ARMS),
        "Weapon_Rifle_Holster": (*holster_clip(), False, ARMS),
        "Weapon_Rifle_Draw": (*draw_clip(), False, ARMS),
    }
    return clips


# ---------------------------------------------------------------------------- output
class Ref:
    n = 0


def _ref():
    Ref.n += 1
    return f"RBX{Ref.n}"


def pose_xml(name, tree, poses, keyed):
    """Keyed joints get Weight 1; parents that only hold the hierarchy get Weight 0 so they
    don't override other animations (same as the Roblox Animation Editor writes them)."""
    kids = "".join(pose_xml(k, sub, poses, keyed) for k, sub in tree.items() if _has_key(k, sub, keyed))
    pos, rot = poses.get(name, ((0, 0, 0), np.eye(3)))
    weight = 1 if name in keyed else 0
    return (f'<Item class="Pose" referent="{_ref()}"><Properties><string name="Name">{name}</string>'
            f'{L.cframe_xml(pos, np.asarray(rot))}<token name="EasingDirection">0</token>'
            f'<token name="EasingStyle">0</token><float name="Weight">{weight}</float></Properties>{kids}</Item>')


def _has_key(name, sub, keyed):
    return name in keyed or any(_has_key(k, s, keyed) for k, s in sub.items())


def _start(tree, keyed):
    """Smallest subtree holding every keyed part, like Roblox's own clips (an arms-only clip
    starts at an unkeyed UpperTorso). If that node is keyed itself, start at its parent."""
    name, sub = next(iter(tree.items()))
    parent = None
    while True:
        if name in keyed:
            return parent or (name, sub)
        kids = [(k, v) for k, v in sub.items() if _has_key(k, v, keyed)]
        if len(kids) != 1:
            return name, sub
        parent = (name, sub)
        name, sub = kids[0]


def sequence(name, frames, keyed, loop, priority=2):
    """priority 2 = Action (looping holds) / the game re-sets it per track anyway."""
    Ref.n = 0
    kfs = []
    keyed = set(keyed)
    for t, poses in frames:
        root, sub = _start(L.TREE, keyed)
        kfs.append(f'<Item class="Keyframe" referent="{_ref()}"><Properties><string name="Name">Keyframe</string>'
                   f'<float name="Time">{t:.4f}</float></Properties>{pose_xml(root, sub, poses, keyed)}</Item>')
    return ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" version="4">'
            f'<Item class="KeyframeSequence" referent="RBX0"><Properties><string name="Name">{name}</string>'
            f'<bool name="Loop">{"true" if loop else "false"}</bool><token name="Priority">{priority}</token></Properties>'
            f'{"".join(kfs)}</Item></roblox>')


def gun_lines(f):
    """World points of the gun for a solved frame set (for previews)."""
    gun = f["RightHand"] @ HAND_TO_GUN
    pts = {k: (gun @ np.array([*v, 1]))[:3] for k, v in P.items()}
    return [(pts["Butt"], pts["Muzzle"]), (np.array(pts["MagWell"]), np.array(pts["MagBottom"])),
            ((gun @ np.array([0, 0, 0, 1]))[:3], (gun @ np.array([0, 0.27 * GUN_SCALE, -0.1, 1]))[:3])]


def render(frames, path, title):
    from PIL import Image, ImageDraw
    bones = [("LowerTorso", "UpperTorso"), ("UpperTorso", "Head"), ("RightUpperArm", "RightLowerArm"),
             ("RightLowerArm", "RightHand"), ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"),
             ("RightUpperArm", "LeftUpperArm")]
    imgs = []
    W, H, sc = 780, 300, 52
    for t, poses in frames:
        f = r15.solve({k: (v[0], np.asarray(v[1])) for k, v in poses.items()})
        im = Image.new("RGB", (W, H), (245, 245, 240))
        d = ImageDraw.Draw(im)
        for ox, view in ((130, "side"), (390, "front"), (650, "top")):
            def Pp(v):
                if view == "side":
                    return (ox - v[2] * sc, 150 - (v[1] - 0.2) * sc)
                if view == "front":
                    return (ox + v[0] * sc, 150 - (v[1] - 0.2) * sc)
                return (ox + v[0] * sc, 150 + (v[2] + 0.5) * sc)

            def jp(name):
                if name in ("Head", "RightHand", "LeftHand", "UpperTorso", "LowerTorso"):
                    return f[name][:3, 3]
                parent, c0, c1 = r15.JOINTS[name]
                return (f[parent] @ np.array([*c0, 1]))[:3]
            # torso box outline
            ut = f["UpperTorso"]
            corners = [(ut @ np.array([x, y, 0, 1]))[:3] for x, y in ((-1, 0.8), (1, 0.8), (1, -0.8), (-1, -0.8), (-1, 0.8))]
            d.line([Pp(c) for c in corners], fill=(150, 150, 150), width=2)
            hp = Pp(f["Head"][:3, 3])
            d.ellipse([hp[0] - 0.6 * sc, hp[1] - 0.6 * sc, hp[0] + 0.6 * sc, hp[1] + 0.6 * sc], outline=(90, 90, 90), width=2)
            nose = Pp((f["Head"] @ np.array([0, 0, -0.75, 1]))[:3])
            d.line([hp, nose], fill=(90, 90, 90), width=2)
            for a, b in bones:
                col = (60, 110, 200) if "Left" in b else ((200, 70, 60) if "Right" in b else (40, 40, 40))
                d.line([Pp(jp(a)), Pp(jp(b))], fill=col, width=5)
            for a, b in gun_lines(f):
                d.line([Pp(a), Pp(b)], fill=(20, 20, 20), width=4)
            d.text((ox - 110, 8), f"{title} {view} t={t:.2f}", fill=(0, 0, 0))
        imgs.append(im)
    if path.endswith(".gif"):
        dt = max(20, int(1000 * (frames[1][0] - frames[0][0])))
        imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=dt, loop=0)
    else:
        imgs[0].save(path)


def main():
    os.makedirs(L.OUT, exist_ok=True)
    for name, (frames, worst, loop, keyed) in build().items():
        with open(os.path.join(L.OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(sequence(name, frames, keyed, loop))
        print(f"{name}: {len(frames)} frames {frames[-1][0]:.2f}s {'loop' if loop else 'once'}  worst hand miss {worst:.3f} studs")
        if "--preview" in sys.argv:
            render(frames[:: max(1, len(frames) // 24)], os.path.join(L.OUT, f"{name}.gif"), name)
            render(frames[:1], os.path.join(L.OUT, f"{name}.png"), name)
    print("HAND_TO_GUN C0:", ", ".join(f"{v:.4f}" for v in hand_to_gun_cframe()))
    for label, m in (("MAG_IN_HAND", mag_in_hand()), ("MAG_DRAW_IN_HAND", mag_in_hand(mag_draw_grip_in_gun()))):
        print(f"{label} C0:", ", ".join(f"{v:.4f}" for v in [*m[:3, 3], *m[:3, :3].flatten()]))
    print("RELOAD beats:", RELOAD)
    print("HOLSTER beats:", dict(swap=HOLSTER["swap"], length=HOLSTER["length"]), "DRAW beats:", draw_beats())


if __name__ == "__main__":
    main()
