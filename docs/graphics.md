# Graphics (GTA-style look)

`src/client/Weather/Graphics.luau` adds a GTA V style post layer on top of `Weather/Sky.luau`
(which already sets light, atmosphere and a colour grade per time of day and weather).
It runs every frame right after `Sky.update`, on the client only.

| Part | What it does | Lighting object |
| --- | --- | --- |
| Haze | scales Sky's Atmosphere density/haze (`Haze`), adds low mist around sunrise (`MorningFog`) | Atmosphere |
| Far blur | soft blur only far away (from `BlurStart` studs), stronger in rain; nothing near you | `GtaDistanceBlur` (DepthOfField) |
| Bloom | soft by day, street lights and neon glow at night, a bit more on wet streets | `GtaBloom` |
| Grade | extra contrast + colour, warm sun by day, cool blue at night, flatter in grey weather | `GtaGrade` (ColorCorrection) |
| Shadows | crisp sun shadows, soft when overcast | `Lighting.ShadowSoftness` |

The place's default `Bloom`, `DepthOfField` and `SunRays` effects are switched off so they
don't stack with ours. `Lighting.Technology` can't be set by scripts, so
`default.project.json` sets it to `Future`; if Studio still shows something else, set
Lighting > Technology to Future by hand and save.

## Quality

| Quality | Far blur | Bloom | Sun rays |
| --- | --- | --- | --- |
| High | on | full | on |
| Medium | off | 70% | on |
| Low | off | off | off |

`Auto` (default) picks Medium on phones/tablets, Low when the player's Roblox graphics
level is 1-3, otherwise High. Haze and the grade are on at every level (they cost nothing).

## Tuning

F8 > Graphics: quality buttons and +/- for every value, live for this session only. Copy the
values you like into `Config.Graphics`. Set `Config.Weather.DriveSky = false` to leave
Lighting as set in Studio (haze and shadow tweaks then stop too; blur, bloom and grade still run).
