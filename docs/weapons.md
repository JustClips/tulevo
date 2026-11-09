# Weapon system

Built to grow. Weapons are data, the classes they belong to decide how they're held and
which animations they need, and the server decides every hit.

## Layout

| Where | What |
|---|---|
| `src/shared/Weapons/Defs/*.luau` | One file per weapon: damage, fire rate, mag, spread, range... (data only) |
| `src/shared/Weapons/Classes.luau` | Weapon families (Melee, Pistol, SMG, Shotgun, Rifle): wheel slot, aim walk speed, animation list |
| `src/shared/Weapons/init.luau` | Registry: `Weapons.get(id)`, `Weapons.classOf(id)`, `Weapons.all()` |
| `src/server/Weapons/WeaponService.luau` | Inventories (one weapon per wheel slot), ammo, equip/fire/reload remotes, `give`/`take` |
| `src/server/Weapons/Hitscan.luau` | Server shot check: origin near the shooter, server-side spread, raycast, falloff, headshots |
| `src/client/Weapons/init.luau` | Controller: slot keys, fire/aim/reload, ammo prediction, facing the aim |
| `src/client/Weapons/AnimSet.luau` | Loads a class's animations from `Shared.AnimIds`; pose loops cross-fade by weight |
| `src/client/Weapons/GunPose.luau` | Bends every gun holder's waist to aim up/down and twist while strafing (replicated) |
| `src/server/Weapons/GunModel.luau` | Gun model welded in the right hand (equipped) or on the back (holstered) |
| `art/anim/gun.py` | Builds the rifle clips: places the gun, solves both arms with IK onto grip + handguard |
| `src/client/Weapons/Effects.luau` | Tracers, muzzle flash, bullet impacts on the world (holes, dust, chips, sparks; `Config.Weapons.Fx`, textures from `tools/bullet_hole_sprites.py`) |
| `src/client/Weapons/GunAudio.luau` | Gun sounds: shots by distance, bullet cracks, impacts (see Sounds below) |
| `src/client/Movement/Moves/Aim.luau` | Aiming slows you to the class's aim walk and beats Sprint; sprint key while aiming = side run up to `Config.Movement.AimSprintSpeed` (12), sideways only (part of the Movement system) |
| `Config.Weapons` | Studio test loadout, slot key order |

Add a weapon: copy a file in `Defs/`. Damage per hit = `Damage` x body-part multiplier (`BodyDamage` in the weapon, else `Config.Weapons.BodyDamage`) x distance falloff. The ammo counter (`src/client/AmmoHud.client.luau`) shows mag and spare bullets: top right while the gun is down, and as a panel floating right of the aim (trailing camera turns) while aiming / firing / reloading. Add a family: add a class in `Classes.luau` and its animations.

## Controls

1-3 use the inventory's quick slots (`Client/Inventory`, docs/inventory.md): a gun in that slot comes
out, the same key puts it on the back (gamepad D-pad left / up / right, the quick bar at the bottom of
the screen on phones); dragging a gun onto / off Active items in the inventory does the same. Q and V
were removed as holster/vest keys (Dev, 2026-11-06) · left click fire (R2) · right click aim (L2) · R reload (X)
· hold Q / E lean left / right, gun out or not (keyboard only for now; E still opens item prompts).
The lean is a body pose from `Client/Weapons/GunPose` (replicated as `GunLean`): hips tip a
little with the legs kept upright, the chest makes up the rest of `Config.Weapons.LeanAngle`
round the aim (barrel still on the crosshair), the head tilts back toward level. While aiming
the third-person camera slides out with it and first person tilts; the server tilts the shot origin the same way (`WeaponService` `shotOrigin`,
never through a wall) so you can shoot round a corner. No lean while sprinting, rolling, in the
air or driving. Holstering or switching mid-reload cuts the reload short (no refill;
the server puts the magazine back, `GunModel.cancelReload`).
Phones get Fire / Aim / Reload buttons while something is in hand. Dragging the vest out of / onto
the inventory's Armor slot takes the armor vest off / puts it back on (`Client/Vest.client.luau`,
`Server/Armor.server.luau`, clips from `art/anim/vest.py`): the gun goes on the back first and
comes back out after, the server moves the real vest with the hands on the clip's beats, and the
armor left is kept while it's off (Humanoid StoredArmorItem / StoredArmor). No weapon can be taken
out while dressing (`State.Dressing`); that lock always lifts at the end, on an error or a respawn.
Where the gun model sits is the gun's `On` attribute ("RightHand" / "UpperTorso"), set by
`Server/Weapons/GunModel`; client checks read that, not the welds. A character only ever has one
`Gun`: the model loads once (preloaded at server start, a second caller waits for the first load)
and an attach still waiting for the load is dropped if a newer attach / remove came in.
Everyone gets the Carbine Rifle (`Defs/CarbineRifle.luau`: damage, per-body-part multipliers, falloff, fire rate, mag size, spare ammo, reload time) and spawns holding it (`Config.Weapons.DefaultLoadout`,
`EquipOnSpawn`). Studio play tests can get extra weapons (`Config.Weapons.StudioLoadout`, empty for now: Bat, Pistol, SMG and Shotgun have no models or animations, and equipping them with 1-4 left the rifle on the back). `Config.Weapons.Debug` shows a weapon state readout (`Client/WeaponDebug`).

## Hits, cheats and lag

The client only sends a shot direction. The server shoots from its own copy of the head, checks
the direction matches where the body visibly aims (else the shot is dropped and `AimFlags` goes
up), adds spread, and raycasts. Players are hit where the shooter saw them
(`Server/Weapons/LagComp`: 20 Hz hitbox history, rewind = ping + 0.05 s, max 0.25 s, ray-vs-box
maths only); the map is never rewound, so cover always blocks. No shooting while rolling, winding up
a jump or in the air (`Movement.busy()` on the client; the server also drops shots from anyone
more than 2.5 studs off the ground). `Config.Weapons.LagComp.Debug`
shows the rewound hitboxes in Studio.

## Sounds

`Client/Weapons/GunAudio`, every number in `Config.Weapons.Sound`. Files come from `tools/gun_sounds.py`
(then `tools/upload_sounds.py` uploads them and writes `Shared/SoundIds`).

- Shots are real AR-15 recordings from The Free Firearm Sound Library (freefirearmsfx.com, CC0),
  in `art/sounds/source/`. A weapon's `Sound` field picks the set (`Carbine` = CarbineShot /
  CarbineDistant / CarbineFar).
- Your own shot plays flat in both ears the moment you fire. Someone else's plays from their
  muzzle: close-up shot under `NearRange`, distant shot up to `DistantRange`, a far pop past
  that, nothing past `MaxRange`, delayed by distance / `SpeedOfSound` (so far away the bullets land first).
- The server's `Shot` remote now also sends what each bullet hit (`"Body"`, a material name, or
  `""` for nothing), so every client plays the right impact: concrete, metal, wood, dirt, glass or
  a person (a hit on you plays flat and close). Concrete/metal sometimes ricochet.
- A bullet passing within `CrackRadius` of you cracks past (supersonic snap + street echo), and
  within `WhizRadius` also whizzes. These and impacts don't depend on how far the shooter is.

## Rifle poses

| Clip | When |
|---|---|
| Hold | low ready, standing / walking / crouching |
| Sprint | low ready while sprinting: pulled in, muzzle down across the body (no longer muzzle-up port arms) |
| Aim | right click, and for 0.3 s after a hip-fire shot (not after shots while aiming, so letting go drops it at once); chest + head keyed, waist bent to the camera pitch |
| Fire | recoil kick on top of Aim |
| Tuck | during rolls (Space while aiming, like GTA 5) |
| Air | in the air (loop) |
| JumpPrep / JumpUp / Land | jump wind-up (gun dips with the knees), take-off spring, landing bounce; played on the Movement Prep/TakeOff/Land events |
| Lowered | a wall within `Config.Weapons.LowerNearWalls` studs in front; no shooting while it's down (`State.Lowered`) |
| Reload | R: mag out and tossed, no vest: fresh mag off the left hip, push it in, slap it home, charging handle |
| ReloadPouch1/2 (+Open) | Same, but the fresh mag comes out of the next vest pouch: the hand flicks the lid open (it stays open; ...Open = it already is), pulls the mag out and pushes it in. `Shared/Armor/Pouches` picks the pouch (1 wearer's left, then 2 centre, round again; 3 is out of the left arm's reach), `GunModel.reloadMag` opens the lid and moves the mag on the clip's beats (`art/anim/gun.py` RELOAD). Lids and mags reset when the vest is put on again |
| Equip | taking the gun out (spawn, or a gun that wasn't on the back) |
| Holster / Draw | Putting it away lifts the rifle muzzle-up, flips it back over the right shoulder and slides it down onto the back (muzzle down toward the left hip, stock up behind the right shoulder, grip on the right shoulder blade, so the hand reaches it over the shoulder with the elbow up); the quick slot key does it backwards. The server moves the weld when the hand is on the back (`GunModel.HolsterSwap` / `DrawSwap`, from gun.py `HOLSTER`); no firing until the draw ends |
| CrouchHold | crouched, not aiming: high ready |

While the gun is up your whole body faces the camera (GTA). A/D blend in side-step clips
(`art/anim/strafe.py`, Tulevo_StrafeLeft/Right; with Shift the side run Tulevo_StrafeRunLeft/Right
blends in as you speed up toward `AimSprintSpeed`; there's no forward sprint while aiming),
S plays the walk in reverse, and
`Client/Weapons/GunPose` locks the chest to the aim yaw + pitch every frame after the
animations (so walking never wobbles the rifle), for every player via GunUp/GunPitch.
Aiming while standing still, the feet stay planted as the body turns and a turn step
(`art/anim/steps.py` Tulevo_TurnStepLeft/Right) plays once the body is `Config.Weapons.AimStep`
degrees off them (GunPlant attribute + the replicated step clip keep it in sync for others).
GunPose also turns the hips and legs into a bladed rifle stance
(`Config.Weapons.AimStance`: 38 degrees right of the aim standing, 20 moving) so the whole body
turns, not just the chest; the side-step blend is worked out relative to those turned hips.
Only on Motor6D rigs: this game's characters have AnimationConstraint joints (Avatar Joint
Upgrade), and there GunPose leaves the Root and hip joints alone, so no stance and the lean is
all chest. It finds joints with `Shared/Joints` and poses them by writing C0 (on an
AnimationConstraint, its Attachment0 CFrame). Each frame starts again from the joint's own C0,
which is only read while GunPose hasn't changed it (a read-back never matches exactly, and
taking it as the new start made characters spin). A joint asked to turn more than 150 degrees
switches posing off for that character with a `[GunPose]` warning; `Config.Weapons.BodyPose =
false` turns all of it off.
Gun loops play at Action2 and one-shots at Action3, so the full-body jump wind-up (Action)
never pulls the hands off the gun.

First person: arms and gun stay visible and the body faces the view carrying the rifle at the
shoulder (Aim pose).
First-person camera (`Client/Movement/FirstPersonCamera`): the camera sits at the eyes on the
animated head (crouching and walking follow). With the gun shouldered the eye is pinned to the gun
(rifle low right, it never swims while you walk), and aiming down sights puts it on the gun's own
sight line just behind the rear `Sight` (gun.py `AIM` keeps the barrel exactly along the aim, so
rear aperture, front post and crosshair line up), and tumbles with the hips through rolls (`Config.Movement.FirstPersonRollCamera`).
It is undone before the camera script each frame, so anything aiming reads `Movement.view()`
(eye position, look without the tumble) instead of `CurrentCamera.CFrame`.

Rebuild the clips with `python3 art/anim/gun.py --preview && python3 tools/upload_anims.py`
(`GUN_SCALE` there must match `Config.Weapons.GunScale`, and `HAND_TO_GUN` must match GunModel).

## Animations needed

Named `Weapon_<Class>_<Slot>` in `src/shared/AnimIds.luau`. Until one exists, that slot
just doesn't play. Hold and Aim loop and drive the upper body over the walk/run legs.

| Class | Slots |
|---|---|
| Melee | Hold, Attack1, Attack2, Attack3, Equip |
| Pistol | Hold, Aim, Fire, Reload, Equip |
| SMG | Hold, Aim, Fire, Reload, Equip |
| Shotgun | Hold, Aim, Fire, Reload, Equip |
| Rifle | Hold, Aim, Fire, Reload, Equip, Sprint, Tuck, Air, Lowered, JumpPrep, JumpUp, Land, Holster, Draw, CrouchHold, ReloadPouch1, ReloadPouch1Open, ReloadPouch2, ReloadPouch2Open |

## Still to do

Models and animations for the other classes, GTA weapon wheel UI, sounds and muzzle flash, pickups/shop, friendly fire and wanted level.

## Armor

- Defs in `Shared.Armor` (`ArmorVest` = 50 armor, covers every hit). Players wear `Armor.Default` on spawn (`Server/Armor.server.luau`).
- All weapon damage goes through `Server.Damage.apply(humanoid, amount, partName)`. While armor is left, every weapon hit, headshots included, is split: `Absorb` share (vest 0.7) drains armor and the rest still hurts health (GTA 5 style, not a second health bar).
- Armor is stored on the Humanoid as attributes `Armor`, `MaxArmor`, `ArmorItem`; the HUD's blue half reads them. Use `Damage.setArmor` / `Damage.addArmor` for pickups.
