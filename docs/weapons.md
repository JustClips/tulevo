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
| `src/client/Weapons/Effects.luau` | Tracers now; flash, sounds, impacts later |
| `src/client/Movement/Moves/Aim.luau` | Aiming slows you and beats Sprint (part of the Movement system) |
| `Config.Weapons` | Studio test loadout, slot key order |

Add a weapon: copy a file in `Defs/`. Damage per hit = `Damage` x body-part multiplier (`BodyDamage` in the weapon, else `Config.Weapons.BodyDamage`) x distance falloff. The ammo counter (top right, `src/client/AmmoHud.client.luau`) shows mag and spare bullets. Add a family: add a class in `Classes.luau` and its animations.

## Controls

1-5 pick a slot (same key or Q holsters) · left click fire (R2) · right click aim (L2) · R reload (X).
Phones get Fire / Aim / Reload buttons while something is in hand.
Everyone gets the Carbine Rifle (`Defs/CarbineRifle.luau`: damage, per-body-part multipliers, falloff, fire rate, mag size, spare ammo, reload time) and spawns holding it (`Config.Weapons.DefaultLoadout`,
`EquipOnSpawn`). Studio play tests also get Bat, Pistol, SMG and Shotgun (no models yet).

## Hits, cheats and lag

The client only sends a shot direction. The server shoots from its own copy of the head, checks
the direction matches where the body visibly aims (else the shot is dropped and `AimFlags` goes
up), adds spread, and raycasts. Players are hit where the shooter saw them
(`Server/Weapons/LagComp`: 20 Hz hitbox history, rewind = ping + 0.05 s, max 0.25 s, ray-vs-box
maths only); the map is never rewound, so cover always blocks. `Config.Weapons.LagComp.Debug`
shows the rewound hitboxes in Studio.

## Rifle poses

| Clip | When |
|---|---|
| Hold | low ready, standing / walking / crouching |
| Sprint | rifle across the chest while sprinting |
| Aim | right click, and for 0.6 s after a hip-fire shot; chest + head keyed, waist bent to the camera pitch |
| Fire | recoil kick on top of Aim |
| Tuck | during rolls (Space while aiming, like GTA 5) |
| Air | in the air (loop) |
| JumpPrep / JumpUp / Land | jump wind-up (gun dips with the knees), take-off spring, landing bounce; played on the Movement Prep/TakeOff/Land events |
| Lowered | a wall within `Config.Weapons.LowerNearWalls` studs in front |
| Reload | R: mag out, fresh mag from the vest, slap it in, charging handle |
| Equip | taking the gun out |

While the gun is up your whole body faces the camera (GTA). A/D blend in side-step clips
(`art/anim/strafe.py`, Tulevo_StrafeLeft/Right), S plays the walk in reverse, and
`Client/Weapons/GunPose` locks the chest to the aim yaw + pitch every frame after the
animations (so walking never wobbles the rifle), for every player via GunUp/GunPitch.
Gun loops play at Action2 and one-shots at Action3, so the full-body jump wind-up (Action)
never pulls the hands off the gun.

First person: arms and gun stay visible, the body faces the view and carries the rifle at the
shoulder (Aim pose); right click moves the camera behind the gun's `Sight` attachment (ADS).
Rolls in first person tumble the view with the body (`Client/Movement/RollCamera`, turns with
the hips, rides with the head, `Config.Movement.FirstPersonRollCamera`). The tumble is undone
before the camera script each frame, so anything aiming reads `Movement.view()` (the camera
without the tumble) instead of `CurrentCamera.CFrame`.

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
| Rifle | Hold, Aim, Fire, Reload, Equip, Sprint, Tuck, Air, Lowered, JumpPrep, JumpUp, Land |

## Still to do

Models and animations for the other classes, GTA weapon wheel UI, sounds and muzzle flash, pickups/shop, friendly fire and wanted level.

## Armor

- Defs in `Shared.Armor` (`ArmorVest` = 50 armor, head not covered). Players wear `Armor.Default` on spawn (`Server/Armor.server.luau`).
- All weapon damage goes through `Server.Damage.apply(humanoid, amount, partName)`. While armor is left, hits on covered parts take armor first and the rest goes to health (GTA style). Headshots skip the vest.
- Armor is stored on the Humanoid as attributes `Armor`, `MaxArmor`, `ArmorItem`; the HUD's blue half reads them. Use `Damage.setArmor` / `Damage.addArmor` for pickups.
