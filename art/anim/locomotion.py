"""GTA-style walk and run cycles for the default R15 rig, written as KeyframeSequence .rbxmx.

Original animation, built from code: feet follow a planned path (heel strike, roll, toe-off,
swing), the legs are solved with two-bone IK so planted feet never slide, and the upper body
adds the relaxed street walk (hip sway, shoulders counter-turning, loose arms, steady head).

  python3 art/anim/locomotion.py            -> art/out/anims/Tulevo_Walk.rbxmx, Tulevo_Run.rbxmx
  python3 art/anim/locomotion.py --preview  -> also art/out/anims/*.gif (side + front stick view)

It also prints each clip's "natural speed" (studs per second at playback speed 1). The game
plays the clip at actual_speed / natural_speed, so the feet match the ground at any WalkSpeed.
Axes are HumanoidRootPart space: X right, Y up, front = -Z. Ground = r15.GROUND.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r15  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "anims")
D = math.radians
THIGH, SHIN = 0.92, 1.009        # hip->knee, knee->ankle (from r15.JOINTS)
SOLE = 0.262                     # ankle height above the sole
HEEL_Z, TOE_Z = 0.42, -0.5       # heel / toe along the foot, from the ankle


def rx(a):
    return r15.angles(a, 0, 0)


def ry(a):
    return r15.angles(0, a, 0)


def rz(a):
    return r15.angles(0, 0, a)


def smooth(u):
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


# Each style: timings in cycle phase (0..1, right heel strike at 0), lengths in studs,
# angles in degrees.
WALK = dict(
    duration=1.0, stance=0.62,
    front=-0.86, back=0.98,        # planted foot z at heel strike / toe-off
    lift=0.30, width=0.43, toe_out=9,
    heel_pitch=16, toe_pitch=-34, swing_pitch=-8,
    bob=0.05, sway=0.06, hip_yaw=7, hip_roll=5,
    lean=-4, chest_yaw=-11, chest_roll=-2, head_follow=0.85,
    arm_swing=21, arm_fwd=-3, arm_out=7, elbow=16, elbow_swing=16,
    shoulder_roll=3, kick=0.0, peak=0.3,
)
RUN = dict(
    duration=0.72, stance=0.36,
    front=-0.5, back=1.2,
    lift=0.55, width=0.36, toe_out=4,
    heel_pitch=8, toe_pitch=-42, swing_pitch=-38,
    bob=0.12, sway=0.04, hip_yaw=10, hip_roll=4,
    lean=-13, chest_yaw=-15, chest_roll=-2, head_follow=0.7,
    arm_swing=40, arm_fwd=6, arm_out=9, elbow=78, elbow_swing=14,
    shoulder_roll=4, kick=0.55, peak=0.43,
)
SPRINT = dict(
    duration=0.6, stance=0.31,
    front=-0.35, back=1.12,
    lift=0.8, width=0.33, toe_out=2,
    heel_pitch=4, toe_pitch=-48, swing_pitch=-50,
    bob=0.15, sway=0.03, hip_yaw=12, hip_roll=4,
    lean=-20, chest_yaw=-17, chest_roll=-2, head_follow=0.6,
    arm_swing=58, arm_fwd=10, arm_out=7, elbow=88, elbow_swing=10,
    shoulder_roll=5, kick=0.85, peak=0.42,
)
# Stealth crouch (GTA-style sneak): hips sit low, chest bent over, hands held in close.
CROUCH_WALK = dict(
    duration=1.15, stance=0.64,
    front=-0.62, back=0.72,
    lift=0.26, width=0.5, toe_out=12,
    heel_pitch=8, toe_pitch=-30, swing_pitch=-6,
    bob=0.04, sway=0.07, hip_yaw=6, hip_roll=4,
    lean=-26, chest_yaw=-7, chest_roll=-2, head_follow=0.9,
    arm_swing=9, arm_fwd=30, arm_out=10, elbow=78, elbow_swing=8,
    shoulder_roll=2, kick=0.0, peak=0.3, sit=0.75, thigh_lean=0,
)
CROUCH_IDLE = dict(
    CROUCH_WALK, duration=3.0, stance=0.999, front=0.0, back=0.0, lift=0.0, width=0.55,
    heel_pitch=0, toe_pitch=0, bob=0.025, sway=0.015, hip_yaw=1.5, hip_roll=1,
    chest_yaw=-1.5, arm_swing=2, elbow_swing=3, peak=0.25,
)
GAITS = (("Walk", "Tulevo_Walk", WALK, 24), ("Jog", "Tulevo_Run", RUN, 18), ("Sprint", "Tulevo_Sprint", SPRINT, 16))
GAITS_LUA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src", "shared", "Gaits.luau")


def foot_plan(p, s):
    """Right foot at phase p: (z, extra lift, pitch degrees, planted?)."""
    st = s["stance"]
    if p < st:
        u = p / st
        z = lerp(s["front"], s["back"], u)
        if u < 0.16:  # heel strike, rolling down onto the sole
            pitch = s["heel_pitch"] * (1 - smooth(u / 0.16))
        elif u < 0.6:
            pitch = 0.0
        else:  # heel peels off, weight rolls onto the toes
            pitch = s["toe_pitch"] * smooth((u - 0.6) / 0.4) * 0.75
        return z, 0.0, pitch, True
    u = (p - st) / (1 - st)
    z = lerp(s["back"], s["front"], smooth(u))
    # back kick (heel up toward the seat) early in the swing for the run
    z += s["kick"] * math.sin(math.pi * min(1, u / 0.6)) * (1 - u)
    lift = s["lift"] * math.sin(math.pi * u ** 0.85)
    if u < 0.35:
        pitch = lerp(s["toe_pitch"] * 0.75, s["swing_pitch"], smooth(u / 0.35))
    elif u < 0.8:
        pitch = lerp(s["swing_pitch"], 4, smooth((u - 0.35) / 0.45))
    else:
        pitch = lerp(4, s["heel_pitch"], smooth((u - 0.8) / 0.2))
    return z, lift, pitch, False


def foot_world(p, s, side):
    """Ankle position and foot rotation (HRP space) for one foot."""
    z, lift, pitch, planted = foot_plan(p, s)
    yaw = -D(s["toe_out"]) * side           # toes point a little outward
    rot = ry(yaw) @ rx(D(pitch))
    pts = [rot @ np.array([0, -SOLE, HEEL_Z]), rot @ np.array([0, -SOLE, TOE_Z])]
    low = min(q[1] for q in pts)            # lowest of heel and toe touches the ground
    ankle = np.array([side * s["width"], r15.GROUND + lift - low, z])
    return ankle, rot, planted


def pelvis(p, s, drop):
    """LowerTorso joint pose: small up/down, side sway over the planted foot, hip turn and drop."""
    w = 2 * math.pi * p
    y = -drop - s.get("sit", 0) + s["bob"] * math.cos(2 * (w - 2 * math.pi * s["peak"]))  # highest at s["peak"]
    x = s["sway"] * math.sin(w - 0.6)       # over the right foot during its stance
    yaw = D(s["hip_yaw"]) * math.cos(w)     # right hip forward at right heel strike
    roll = D(s["hip_roll"]) * math.sin(w - 0.5)
    return np.array([x, y, 0.0]), ry(yaw) @ rz(roll)


def leg_ik(lt_frame, ankle, foot_rot, side):
    """Two-bone IK: hip pose, knee pose and foot pose (all local) for an ankle target."""
    hip = (lt_frame @ np.array([side * 0.5, -0.2, 0, 1]))[:3]
    R_lt = lt_frame[:3, :3]
    d = ankle - hip
    L = min(np.linalg.norm(d), (THIGH + SHIN) * 0.9995)
    dh = d / np.linalg.norm(d)
    cos_b = (THIGH ** 2 + L ** 2 - SHIN ** 2) / (2 * THIGH * L)
    b = math.acos(max(-1, min(1, cos_b)))
    fwd = R_lt @ np.array([side * 0.12, 0, -1.0])   # knees point forward, a touch outward
    pole = fwd - fwd.dot(dh) * dh
    pole /= np.linalg.norm(pole)
    knee = hip + THIGH * (math.cos(b) * dh + math.sin(b) * pole)
    u_w = (knee - hip) / THIGH
    v_w = (hip + dh * L - knee) / SHIN
    # thigh rotation in LowerTorso space: -Y along the thigh, -Z toward the knee's front
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
    R_foot = (R_lt @ R_ul @ R_ll).T @ foot_rot
    return R_ul, R_ll, R_foot, L


def reach(lt_frame, ankle, side):
    hip = (lt_frame @ np.array([side * 0.5, -0.2, 0, 1]))[:3]
    return np.linalg.norm(ankle - hip)


def lt_frame_of(pos, rot):
    return r15.T(0, -1.0, 0) @ r15.T(*pos) @ r15.R(rot) @ r15.T(0, 0.2, 0)


def find_drop(s, n=96):
    """How far the hips sit down so the planted leg is never over-stretched."""
    drop = 0.0
    for i in range(n):
        p = i / n
        for side, ph in ((1, p), (-1, (p + 0.5) % 1)):
            ankle, _, _ = foot_world(ph, s, side)
            while True:
                pos, rot = pelvis(p, s, drop)
                if reach(lt_frame_of(pos, rot), ankle, side) <= (THIGH + SHIN) * 0.975:
                    break
                drop += 0.005
    return drop


def pose_at(p, s, drop):
    w = 2 * math.pi * p
    pos, rot = pelvis(p, s, drop)
    poses = {"LowerTorso": (tuple(pos), rot)}
    lt = lt_frame_of(pos, rot)
    for side, ph, pre in ((1, p, "Right"), (-1, (p + 0.5) % 1, "Left")):
        ankle, frot, _ = foot_world(ph, s, side)
        R_ul, R_ll, R_f, _ = leg_ik(lt, ankle, frot, side)
        poses[pre + "UpperLeg"] = ((0, 0, 0), R_ul)
        poses[pre + "LowerLeg"] = ((0, 0, 0), R_ll)
        poses[pre + "Foot"] = ((0, 0, 0), R_f)
    # chest turns against the hips, leans forward, rolls a little with each step
    hip_yaw = D(s["hip_yaw"]) * math.cos(w)
    chest_yaw = D(s["chest_yaw"]) * math.cos(w) - hip_yaw * 0.4
    chest = rx(D(s["lean"])) @ ry(chest_yaw) @ rz(D(s["chest_roll"]) * math.sin(w))
    poses["UpperTorso"] = ((0, 0, 0), chest)
    # head undoes most of the hip + chest turn, so it stays level and looks ahead
    poses["Head"] = ((0, 0, 0), _partial((rot @ chest).T, s["head_follow"]))
    # arms swing against the legs; elbows bend more on the forward swing
    for side, pre, ph in ((1, "Right", p), (-1, "Left", (p + 0.5) % 1)):
        sw = -math.cos(2 * math.pi * ph)            # +1 when this arm is forward
        a = D(s["arm_fwd"] + s["arm_swing"] * sw)
        out = D(s["arm_out"]) * side
        twist = -D(8) * side                        # palms turn toward the thighs
        poses[pre + "UpperArm"] = ((0, 0, 0), rz(out) @ rx(a) @ ry(twist) @ rz(D(s["shoulder_roll"]) * side * sw * 0.5))
        elbow = s["elbow"] + s["elbow_swing"] * max(0, sw)
        poses[pre + "LowerArm"] = ((0, 0, 0), rx(D(elbow)))
        poses[pre + "Hand"] = ((0, 0, 0), rz(-D(6) * side) @ rx(D(4)))
    return poses


def _partial(rot, f):
    """Rotation rot scaled by f (axis-angle)."""
    ang = math.acos(max(-1, min(1, (np.trace(rot) - 1) / 2)))
    if ang < 1e-6:
        return np.eye(3)
    axis = np.array([rot[2, 1] - rot[1, 2], rot[0, 2] - rot[2, 0], rot[1, 0] - rot[0, 1]]) / (2 * math.sin(ang))
    a = ang * f
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def natural_speed(s):
    """Studs per second the body travels at playback speed 1 (planted foot speed)."""
    return (s["back"] - s["front"]) / (s["stance"] * s["duration"])


# --- KeyframeSequence XML -------------------------------------------------------------
TREE = {
    "HumanoidRootPart": {
        "LowerTorso": {
            "UpperTorso": {
                "Head": {},
                "RightUpperArm": {"RightLowerArm": {"RightHand": {}}},
                "LeftUpperArm": {"LeftLowerArm": {"LeftHand": {}}},
            },
            "RightUpperLeg": {"RightLowerLeg": {"RightFoot": {}}},
            "LeftUpperLeg": {"LeftLowerLeg": {"LeftFoot": {}}},
        }
    }
}


class Ref:
    n = 0

    @classmethod
    def next(cls):
        cls.n += 1
        return f"RBX{cls.n}"


def cframe_xml(pos, rot):
    vals = {"X": pos[0], "Y": pos[1], "Z": pos[2]}
    for i in range(3):
        for j in range(3):
            vals[f"R{i}{j}"] = rot[i][j]
    return '<CoordinateFrame name="CFrame">' + "".join(f"<{k}>{v:.5f}</{k}>" for k, v in vals.items()) + "</CoordinateFrame>"


def pose_xml(name, tree, poses):
    pos, rot = poses.get(name, ((0, 0, 0), np.eye(3)))
    kids = "".join(pose_xml(k, sub, poses) for k, sub in tree.items())
    return (f'<Item class="Pose" referent="{Ref.next()}"><Properties><string name="Name">{name}</string>'
            f'{cframe_xml(pos, np.asarray(rot))}<token name="EasingDirection">0</token>'
            f'<token name="EasingStyle">0</token><float name="Weight">1</float></Properties>{kids}</Item>')


def sequence(name, frames, priority=1):
    """Priority 1 = Movement: above the default Animate script (Core), below Action."""
    Ref.n = 0
    kfs = []
    for t, poses in frames:
        root, sub = next(iter(TREE.items()))
        kfs.append(f'<Item class="Keyframe" referent="{Ref.next()}"><Properties><string name="Name">Keyframe</string>'
                   f'<float name="Time">{t:.4f}</float></Properties>{pose_xml(root, sub, poses)}</Item>')
    return ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" version="4">'
            f'<Item class="KeyframeSequence" referent="RBX0"><Properties><string name="Name">{name}</string>'
            f'<bool name="Loop">true</bool><token name="Priority">{priority}</token></Properties>'
            f'{"".join(kfs)}</Item></roblox>')


def build(s, steps):
    drop = find_drop(s)
    frames = [(s["duration"] * i / steps, pose_at(i / steps, s, drop)) for i in range(steps + 1)]
    return frames, drop


# --- checks + preview -------------------------------------------------------------------
def check(name, s, frames):
    """Lowest sole point per frame (should touch 0, never below) and planted-foot slip."""
    lows, slips = [], []
    prev = None
    for t, poses in frames:
        f = r15.solve({k: (v[0], np.asarray(v[1])) for k, v in poses.items()})
        y = []
        for foot in ("RightFoot", "LeftFoot"):
            corners = [f[foot] @ np.array([sx, -0.156, sz, 1]) for sx in (-0.3, 0.3) for sz in (HEEL_Z, TOE_Z)]
            y.append(min(c[1] for c in corners) - r15.GROUND)
        lows.append(min(y))
        cur = (f["RightFoot"][:3, 3], f["LeftFoot"][:3, 3])
        if prev is not None:
            slips.append(cur)
        prev = cur
    print(f"{name}: lowest sole {min(lows):+.3f}, highest 'lowest' {max(lows):+.3f} studs above ground")


def preview(name, frames, path):
    from PIL import Image, ImageDraw
    bones = [("LowerTorso", "UpperTorso"), ("UpperTorso", "Head"), ("RightUpperArm", "LeftUpperArm"),
             ("RightUpperLeg", "LeftUpperLeg"), ("RightUpperArm", "RightLowerArm"), ("RightLowerArm", "RightHand"),
             ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"),
             ("RightUpperLeg", "RightLowerLeg"), ("RightLowerLeg", "RightFoot"),
             ("LeftUpperLeg", "LeftLowerLeg"), ("LeftLowerLeg", "LeftFoot")]
    imgs = []
    W, H, sc = 520, 300, 48
    for t, poses in frames[:-1]:
        f = r15.solve({k: (v[0], np.asarray(v[1])) for k, v in poses.items()})
        im = Image.new("RGB", (W, H), (245, 245, 240))
        d = ImageDraw.Draw(im)
        for ox, view in ((130, "side"), (390, "front")):
            gy = H - 20
            d.line([(ox - 110, gy), (ox + 110, gy)], fill=(120, 120, 120), width=2)

            def P(v):
                x = -v[2] if view == "side" else v[0]
                return (ox + x * sc, gy - (v[1] - r15.GROUND) * sc)

            def jpt(name):
                # joint point (where the part hangs from its parent); hands/head use part centres
                if name in ("Head", "RightHand", "LeftHand", "RightFoot", "LeftFoot", "UpperTorso"):
                    return f[name][:3, 3]
                parent, c0, _ = r15.JOINTS[name]
                return (f[parent] @ np.array([*c0, 1]))[:3]
            for a, b in bones:
                left = "Left" in b
                col = (60, 110, 200) if left else ((200, 70, 60) if "Right" in b else (40, 40, 40))
                d.line([P(jpt(a)), P(jpt(b))], fill=col, width=5)
            for foot in ("RightFoot", "LeftFoot"):
                heel = f[foot] @ np.array([0, -0.156, HEEL_Z, 1])
                toe = f[foot] @ np.array([0, -0.156, TOE_Z, 1])
                d.line([P(heel), P(toe)], fill=(200, 70, 60) if foot[0] == "R" else (60, 110, 200), width=4)
            hp = P(jpt("Head") + np.array([0, 0.2, 0]))
            d.ellipse([hp[0] - 14, hp[1] - 14, hp[0] + 14, hp[1] + 14], outline=(40, 40, 40), width=3)
            d.text((ox - 100, 8), f"{name} {view}", fill=(0, 0, 0))
        imgs.append(im)
    dt = int(1000 * (frames[1][0] - frames[0][0]))
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=dt, loop=0)


def main():
    os.makedirs(OUT, exist_ok=True)
    lua = ["-- Generated by art/anim/locomotion.py. Foot-cycle clips, slowest first.",
           "-- Natural = studs/s the clip covers at playback speed 1 (play at speed / Natural).", "return {"]
    for gait, name, s, steps in GAITS:
        lua.append(f'\t{{ Name = "{gait}", Clip = "{name}", Natural = {natural_speed(s):.3f} }},')
        frames, drop = build(s, steps)
        with open(os.path.join(OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(sequence(name, frames))
        print(f"{name}: natural speed {natural_speed(s):.2f} studs/s, hips sit {drop:.3f} lower")
        check(name, s, frames)
        if "--preview" in sys.argv:
            fine, _ = build(s, 40)
            preview(name, [(t * 1.0, p) for t, p in fine], os.path.join(OUT, f"{name}.gif"))
    lua.append("}")
    for name, s_, steps in (("Tulevo_CrouchWalk", CROUCH_WALK, 24), ("Tulevo_CrouchIdle", CROUCH_IDLE, 12)):
        frames, drop = build(s_, steps)
        with open(os.path.join(OUT, f"{name}.rbxmx"), "w") as fh:
            fh.write(sequence(name, frames))
        print(f"{name}: natural speed {natural_speed(s_):.2f} studs/s, hips sit {drop + s_['sit']:.3f} lower")
        check(name, s_, frames)
        if "--preview" in sys.argv:
            fine, _ = build(s_, 40)
            preview(name, fine, os.path.join(OUT, f"{name}.gif"))
    with open(GAITS_LUA, "w") as fh:
        fh.write("\n".join(lua) + "\n")


if __name__ == "__main__":
    main()
