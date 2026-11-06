# Knocked down instead of dying

Health 0 no longer kills a player. They fall over as a ragdoll and lie on the floor with the
"ВЫ РАНЕНЫ" screen (world goes black and white).

- **Ожидать помощи**: stay down. The button turns into a wait timer and the character gets the
  attribute `WaitingHelp = true` (for medics / first-aid kits later).
- **Потерять сознание**: respawn (after `Config.Knocked.GiveUpDelay`).

## Files

- `src/server/Knocked.luau`: turns the Dead state off, sets the character attribute `Knocked`,
  swaps every body joint (AnimationConstraint or Motor6D) for a limited BallSocket (root part is
  welded to the lower torso). `Knocked.revive(character, health?)` puts it all back and stands
  the player up. Remotes in `ReplicatedStorage.KnockedRemotes` (GiveUp, WaitHelp).
- `src/client/Knocked.client.luau`: Dead state off on the owning client, Physics humanoid state,
  stops all animations, random push so bodies land differently, camera out of first person,
  the screen itself.
- `src/server/CharacterSetup.server.luau`: calls `Knocked.attach` for every character. A real
  death (falling out of the map) still respawns after `Players.RespawnTime`.
- `Config.Knocked`: Enabled (false = old die-and-respawn), GiveUpDelay, ReviveHealth, FallPush,
  CameraMinZoom.

Knocked players have Health 0, so everything that already checks `Health <= 0` (shooting, being
shot, movement, vest, inventory drops, cars) treats them as down.
