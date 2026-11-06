# City ambience

`src/client/Ambience.client.luau`, settings `Config.Ambience`.

- Beds: `CityDayLoop` (traffic, by daylight), `CityNightLoop` (quiet hum), `CricketsLoop`
  (night, dry only). Rain turns the traffic down a little.
- One-offs placed 20-180 studs round you so they have a direction: birds (mornings, never at
  night or in rain), dogs (more at night), sirens (police wail / ambulance hi-lo, more at night
  and in storms), car horns (mostly by day). `Every` = average seconds between each.
- Everything is muffled under a roof (EQ on the `Ambience` SoundGroup).

## Sounds

All synthesised by `tools/city_sounds.py` (numpy + ffmpeg, no samples; loops are seamless) →
`art/sounds/*.ogg`, uploaded by `tools/upload_sounds.py` → `Shared/SoundIds`:
ThunderClose1-2, ThunderFar1-3, CityDayLoop, CityNightLoop, CricketsLoop, SirenWail, SirenHiLo,
DogBark1-2, Birds1-3, CarHorn1-2.
