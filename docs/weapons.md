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

## Rifle poses

| Clip | When |
|---|---|
| Hold | low ready, standing / walking / crouching |
| Sprint | rifle across the chest while sprinting |
| Aim | right click, and for 0.6 s after a hip-fire shot; chest + head keyed, waist bent to the camera pitch |
| Fire | recoil kick on top of Aim |
| Tuck | during rolls (Ctrl + Space) |
| Air | jumps and falls |
| Lowered | a wall within `Config.Weapons.LowerNearWalls` studs in front |
| Reload | R: mag out, fresh mag from the vest, slap it in, charging handle |
| Equip | taking the gun out |

While the gun is up you face the camera. Moving sideways turns the hips toward the stick (up to
60 deg) and the waist twists the chest back to the target; moving backwards plays the walk/run
in reverse. Rebuild the clips with `python3 art/anim/gun.py --preview && python3 tools/upload_anims.py`
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
| Rifle | Hold, Aim, Fire, Reload, Equip |

## Still to do

Models and animations for the other classes, GTA weapon wheel UI, over-the-shoulder
aim camera + crosshair, sounds and muzzle flash, pickups/shop, friendly fire and wanted level.
