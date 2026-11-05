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
GUN_SCALE = 1.2
_P = {  # gun points at scale 1 (from the imported model + art/models/CarbineRifle/meta.json)
    "Muzzle": (0, 0.269, -1.634),
    "Grip2": (0, 0.192, -1.062),     # support hand under the handguard (front)
    "Support": (0, 0.200, -0.74),    # where our left hand actually holds (handguard, back half)
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
HOLD = dict(pos=(0.36, -0.17, -0.95), pitch=-22, yaw=48, roll=-15)
# Shouldered: chest bladed (right shoulder back), head turned back to the sights and leaning
# onto the stock.
AIM_TORSO = ry(D(-48)) @ rx(D(-4))
AIM_HEAD = ry(D(40)) @ rz(D(-10)) @ rx(D(-8))
# in UpperTorso space: butt in the right shoulder pocket, yaw undoes the chest turn so the
# rifle points straight ahead of the character
def _grip_from_butt(butt, pitch, yaw, roll=0.0):
    rot = ry(D(yaw)) @ rx(D(pitch)) @ rz(D(roll))
    return tuple(np.array(butt) - rot @ P["Butt"])


AIM = dict(pos=_grip_from_butt((0.55, 0.85, -0.55), 3, 48), pitch=3, yaw=48, roll=0)
# Sprint "port arms": rifle across the chest, muzzle up and to the left.
SPRINT = dict(pos=(0.36, -0.40, -0.95), pitch=38, yaw=48, roll=-40)
# Roll / falling tuck: rifle pulled in tight, muzzle up.
TUCK = dict(pos=(0.34, -0.30, -0.95), pitch=58, yaw=34, roll=-20)
# Near a wall: muzzle down steeply, close to the body.
LOWERED = dict(pos=(0.36, 0.1, -0.72), pitch=-58, yaw=36, roll=-10)


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


# Reload timeline (seconds at playback speed 1). The server moves the real Magazine part on
# the same beats (src/server/Weapons/GunModel.luau, RELOAD_BEATS), so keep them in sync.
RELOAD = dict(grab=0.45, out=0.68, drop=0.8, new=1.12, seated=1.62, length=2.3)


def mag_grip_in_gun():
    """Left hand palming the magazine from below (grip-point frame, gun space)."""
    rot = np.column_stack([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]).astype(float) @ rz(D(-25)) @ rx(D(-20))
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = P["MagBottom"] + np.array([0, -0.1, 0])
    return m


def mag_in_hand():
    """Magazine part frame relative to the LeftHand while it's held (for the Weld C0)."""
    return r15.T(*GRIP_OFFSET) @ np.linalg.inv(mag_grip_in_gun()) @ r15.T(*P["MagCenter"])


def reload_clip():
    """Rifle tilts so the mag faces you; left hand grabs the mag, pulls it straight down out of
    the well and tosses it, takes a fresh one from the vest, lines it up under the well and
    pushes it up in, slaps the bottom, racks the charging handle, back on the handguard."""
    r = RELOAD
    tilt = dict(HOLD, pos=(0.34, -0.05, -0.95), pitch=2, yaw=40, roll=-35)
    keys = [(0.0, HOLD), (0.3, tilt), (1.85, tilt), (2.1, HOLD), (r["length"], HOLD)]
    vest = np.array([-0.35, -0.3, -0.62, 1])  # spare mag pouch on the chest, left of centre
    grip = mag_grip_in_gun()

    def at(gun, down=0.0, back=0.0, side=0.0):
        m = gun @ grip
        m[:3, 3] += gun[:3, :3] @ np.array([side, -down, back])
        return m

    def left(t, gun, ut):
        hand = support_target(gun)
        seated = at(gun)
        out = at(gun, down=0.75 * GUN_SCALE)
        toss = at(gun, down=1.0 * GUN_SCALE, side=-0.5)
        pouch = np.eye(4)
        pouch[:3, :3] = ut[:3, :3] @ rx(D(80)) @ rz(D(-20))
        pouch[:3, 3] = (ut @ vest)[:3]
        below = at(gun, down=0.55 * GUN_SCALE)
        slap = at(gun, down=-0.03)
        charge = support_target(gun)
        charge[:3, 3] = (gun @ np.array([*(P["Charge"] + np.array([-0.15, 0.1, 0])), 1]))[:3]
        charge_back = charge.copy()
        charge_back[:3, 3] += gun[:3, 2] * 0.35
        path = [(0.0, hand), (0.3, hand), (r["grab"], seated), (r["out"], out), (r["drop"], toss),
                (r["new"] - 0.1, pouch), (r["new"], pouch), (1.42, below), (r["seated"], seated),
                (1.68, slap), (1.74, seated), (1.86, charge), (1.95, charge_back), (2.02, charge),
                (2.2, hand), (r["length"], hand)]
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
    kick = dict(AIM, pos=(AIM["pos"][0], AIM["pos"][1] + 0.02, AIM["pos"][2] + 0.13), pitch=5)
    return keyed_clip([(0.0, AIM), (0.03, kick), (0.13, AIM)], fps=60, torso=AIM_TORSO, head=AIM_HEAD)


def equip_clip():
    """Bring the rifle up from hanging at the right side to the low ready."""
    hang = dict(LOWERED, pitch=-64)
    mid = dict(pos=(0.37, -0.12, -0.8), pitch=-40, yaw=44, roll=-12)
    return keyed_clip([(0.0, hang), (0.18, mid), (0.4, HOLD)])


def sprint_bob(d, u):
    w = 2 * math.pi * u * 2  # two bounces per sprint cycle (one per step)
    return dict(d, pos=(d["pos"][0] + 0.05 * math.sin(w / 2), d["pos"][1] + 0.06 * math.sin(w), d["pos"][2]),
                yaw=d["yaw"] + 6 * math.sin(w / 2), pitch=d["pitch"] + 3 * math.cos(w))


def air_bob(d, u):
    w = 2 * math.pi * u
    return dict(d, pos=(d["pos"][0] + 0.04 * math.sin(w), d["pos"][1] + 0.08 * math.sin(w + 1), d["pos"][2]),
                pitch=d["pitch"] + 6 * math.sin(w), roll=d["roll"] + 5 * math.sin(w + 2))


def build():
    clips = {
        "Weapon_Rifle_Hold": (*loop_clip(HOLD, 3.0, 30), True, ARMS),
        "Weapon_Rifle_Aim": (*loop_clip(AIM, 2.4, 24, AIM_TORSO, AIM_HEAD, amp_pos=0.006, amp_rot=0.35), True, AIM_KEYS),
        "Weapon_Rifle_Sprint": (*loop_clip(SPRINT, 0.8, 16, amp_pos=0, amp_rot=0, bob=sprint_bob), True, ARMS),
        "Weapon_Rifle_Tuck": (*loop_clip(TUCK, 1.0, 10, amp_pos=0.01, amp_rot=0.5), True, ARMS),
        "Weapon_Rifle_Air": (*loop_clip(dict(HOLD, pos=(0.40, -0.12, -0.9), pitch=-10), 0.9, 18, amp_pos=0, amp_rot=0, bob=air_bob), True, ARMS),
        "Weapon_Rifle_Lowered": (*loop_clip(LOWERED, 3.0, 15), True, ARMS),
        "Weapon_Rifle_Fire": (*fire_clip(), False, ARMS),
        "Weapon_Rifle_Reload": (*reload_clip(), False, ARMS),
        "Weapon_Rifle_Equip": (*equip_clip(), False, ARMS),
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


def sequence(name, frames, keyed, loop, priority=2):
    """priority 2 = Action (looping holds) / the game re-sets it per track anyway."""
    Ref.n = 0
    kfs = []
    for t, poses in frames:
        root, sub = next(iter(L.TREE.items()))
        kfs.append(f'<Item class="Keyframe" referent="{_ref()}"><Properties><string name="Name">Keyframe</string>'
                   f'<float name="Time">{t:.4f}</float></Properties>{pose_xml(root, sub, poses, set(keyed))}</Item>')
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
    m = mag_in_hand()
    print("MAG_IN_HAND C0:", ", ".join(f"{v:.4f}" for v in [*m[:3, 3], *m[:3, :3].flatten()]))
    print("RELOAD beats:", RELOAD)


if __name__ == "__main__":
    main()
