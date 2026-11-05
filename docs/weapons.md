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
| `src/client/Weapons/AnimSet.luau` | Loads a class's animations from `Shared.AnimIds` |
| `src/client/Weapons/Effects.luau` | Tracers now; flash, sounds, impacts later |
| `src/client/Movement/Moves/Aim.luau` | Aiming slows you and beats Sprint (part of the Movement system) |
| `Config.Weapons` | Studio test loadout, slot key order |

Add a weapon: copy a file in `Defs/`. Add a family: add a class in `Classes.luau` and its animations.

## Controls

1-5 pick a slot (same key or Q holsters) · left click fire (R2) · right click aim (L2) · R reload (X).
Phones get Fire / Aim / Reload buttons while something is in hand.
In Studio play tests everyone gets Bat, Pistol, SMG, Shotgun and Rifle.

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

Weapon models in hand (weld at a Grip attachment), GTA weapon wheel UI, over-the-shoulder
aim camera + crosshair, sounds and muzzle flash, pickups/shop, friendly fire and wanted level.
