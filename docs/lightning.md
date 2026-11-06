# Lightning

## Lightning (Storm weather)

New weather `Storm` (Shared/WeatherTypes, value `storm` = 1; HeavyRain has `storm` 0.2 so it
gets the odd far-off strike). Chat: `/weather storm`. F8 debug panel → World → **Lightning near me**.

| Where | What |
| --- | --- |
| `src/server/Lightning.luau` (+ `LightningRunner.server.luau`) | while `storm` is up, picks a strike every `MinGap`-`MaxGap` s (scaled by storm), sometimes two in a row. 12% land 25-90 studs from a player (Storm only), the rest 160-2200 studs away, 35% stay in the clouds. Of three spots close together the highest is hit, so towers get struck more. Fires `ReplicatedStorage.LightningStrike(pos, normal, kind, seed)`. No damage. `strikeNear(player)` for the debug panel. |
| `src/client/Lightning.client.luau` | bolt (Beams with branches, same shape for everyone from the seed, 2-4 flickers), screen flash (own ColorCorrection, stronger at night, softer under a roof), PointLight at the strike, impact VFX within `ImpactRange` (sparks, flare, shock ring, smoke, embers, scorch mark that fades after ~30 s), thunder delayed by distance (`SoundSpeed`), camera shake within `ShakeRange`. |

Settings: `Config.Lightning`.

The camera shake is applied at `RenderPriority.Last + 1` and taken off at `RenderPriority.First`
(only if the camera is still where it left it), the same pattern as Movement/FirstPersonCamera.

