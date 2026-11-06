# Server checks (anti-cheat)

The server decides damage, money and items. Clients only ask; every remote handler checks the
request before doing anything. Shared helpers live in `src/server/Guard.luau`, limits in
`Config.AntiCheat`.

## Rules for new code

- Never take an amount, a position, a target or a hit from a client. The client says what it
  wants ("fire toward here", "move item from slot 3 to slot 7"); the server works out the rest.
- Check every remote argument's type first (`typeof`), then its range (`Guard.number`).
- Things a knocked-down player can't do start with `Guard.alive(player)`.
- Rate-limit every remote with `Guard.rate(player, key, perSecond, burst)`.
- When the server moves a player on purpose (teleports, getting out of a car), call
  `Guard.allowTeleport(player)` first so the movement check doesn't pull them back.
- Report clear cheats with `Guard.flag(player, reason)`: it counts on the player's
  `CheatFlags` attribute and warns in the server log (first time per reason, then every 10th).
  Shot direction cheats still use `AimFlags` (WeaponService).

## What is checked

| Area | Remote / entry | Server check |
| --- | --- | --- |
| Shots | WeaponRemotes.Fire | direction only; origin = server head; aim must match the visible body aim; not mid-air; not knocked; fire rate per gun (token bucket, 1.5 shots of burst); ammo, range, spread, line of sight and damage all on the server (Hitscan + LagComp) |
| Equip / Reload | WeaponRemotes.Equip / Reload | must carry the gun; not knocked; 4 swaps/s |
| Pose | WeaponRemotes.Pose | real numbers only, clamped; 40/s |
| Damage | Damage.apply | server only, amount must be a real positive number; knocked = Health 0 = no more damage |
| Money | none (no remote) | server only; NaN / inf / huge amounts refused; bad saved values ignored |
| Inventory | InventoryRemotes.Move / Request | slot numbers checked; weight and grid on the server; not knocked; 15 moves/s, 2 snapshots/s |
| Pickups | Move from Ground + "Pick up" prompt | within `Config.Inventory.PickupRange` of the server's copy of the player; not knocked |
| Vest | ArmorRemotes.Vest | standing, not seated, hands free, one at a time; armor points come from the server |
| Knocked | KnockedRemotes.Reset / GiveUp / WaitHelp | Reset once per 5 s; GiveUp after GiveUpDelay |
| Revive | "Поднять" prompt | helper standing and within reach on the server, and held E for at least 80% of ReviveHold |
| Cars | "Drive" prompt, VehicleRemotes.Exit | only the Drive prompt can seat a driver (touching the seat gets you thrown out); door distance; exit 2/s |

## Movement (`src/server/MovementGuard.server.luau`)

Clients move their own characters and the car they drive, so the server checks positions
every `CheckEvery` (0.5 s):

- On foot: a jump of more than `TeleportStuds` in one check, or more than `MaxFootSpeed`
  studs/s for `Strikes` checks in a row, pulls the player back to the last good spot. Falling
  doesn't count (only horizontal movement). Standing on a car and sitting are skipped.
- Knocked down: the body may slide `KnockedDrift` studs from where it fell.
- Cars (VehicleService): driven cars may go `CarSpeedFactor` x their `MaxSpeed`; a teleport or
  two fast checks in a row put the car back and the server holds it for half a second.

If legit play gets pulled back (a new fast move, a launch pad), raise the limits in
`Config.AntiCheat` or call `Guard.allowTeleport` from that feature.

## Not done yet

- Noclip (walking through walls) and fly checks.
- Kicking or banning: flags only warn for now (admin/logs is a separate job).
- Saving inventory (only money saves today).
