# Weather and sky

Server picks the weather, every client draws it. All looks are our own (procedural textures,
Blender meshes, synthesised sound).

## Pieces

| Where | What |
| --- | --- |
| `src/shared/Config.luau` → `Weather` | on/off, start weather, cycle length, chances, fade time, admins, wind, rain volume |
| `src/shared/WeatherTypes.luau` | each weather as 0-1 numbers (cumulus, strato, cirrus, overcast, gloom, rain, heavy) |
| `src/server/Weather.luau` (+ `WeatherRunner.server.luau`) | picks weather, sets `Weather` / `WeatherFrom` / `WeatherSince` on ReplicatedStorage.Shared, loads the meshes into ReplicatedStorage.WeatherMeshes, `/weather` command; `list()` / `set(name)` used by the F8 debug panel |
| `src/client/Weather/init.luau` | blends old → new weather over `FadeSeconds`, runs the three parts every frame |
| `src/client/Weather/Sky.luau` | time-of-day keys (night, dawn, morning, noon, golden hour, sunset, dusk) → Lighting, Atmosphere, Sky, colour grade, sun rays; gloom pulls everything to grey |
| `src/client/Weather/Clouds.luau` | 64 cumulus + 26 stratocumulus meshes drifting on the server clock (same for everyone), slowly turning and breathing; scrolling cirrus and overcast layers |
| `src/client/Weather/Footprints.luau` | ground gets wet while it rains (dries ~2.5 min after), then everyone's steps leave fading shoe prints (not under roofs) with a small splash; `TOE_FLIP` turns prints round if they point backwards |
| `src/client/Weather/Rain.luau` | 7x7 streak emitters over the camera that stop at roofs, mesh splash crowns + ripples + spray, mist sheets, rain sound muffled under roofs |

## Weathers

`Clear`, `Cloudy`, `Rain`, `HeavyRain`, `Storm` (lightning, see `docs/lightning.md`). Add one by adding a row to WeatherTypes and a chance in
Config.Weather.Chances.

Chat (admins in Config.Weather.Admins, or anyone in a Studio play test):
`/weather clear | cloudy | rain | heavyrain | storm` (stays until `/weather auto`).

## Assets

- Meshes: `art/blender/weather/build_weather.py` → `art/models/WeatherMeshes/WeatherMeshes.glb`
  (Cumulus1-5, Congestus, Strato1-2, RainCrown, RainRipple), uploaded by `tools/upload_models.py`
  as `ModelIds.WeatherMeshes`. Run with Blender 5.2 or `pip install bpy==5.2.3`.
- Textures: `tools/weather_textures.py` → `art/weather/tex/*.png` (RainStreak, RainSpray,
  RainSheet, Cirrus, Overcast, FootprintL/R), uploaded by `tools/upload_textures.py` → `TextureIds.Weather`.
- Sound: `tools/weather_sounds.py` → `art/sounds/RainLoop.ogg`, `RainHeavyLoop.ogg` (numpy +
  ffmpeg, seamless loops), uploaded by `tools/upload_sounds.py` → `SoundIds`.

## Notes

- Parts max out at 2048 studs, so the sky layers are 7x7 grids of 2048 parts and clouds are
  shrunk to fit.
- Vector2/Vector3 are 32-bit; anything that multiplies by server time is done in plain numbers.
- Roblox's own Terrain clouds are switched off on the client so they don't fight the meshes.
