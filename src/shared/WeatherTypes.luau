-- What each weather looks like. Every value is a number from 0 to 1 so two weathers can be
-- blended smoothly (Client/Weather mixes them while the server's weather changes).
--   cumulus   share of the puffy cumulus clouds that are out
--   strato    long low grey cloud banks
--   cirrus    thin wispy high cloud layer
--   overcast  solid grey deck covering the sky
--   gloom     how grey and dark the light, air and clouds get
--   rain      rain amount (streaks, splashes, sound); 0 = dry
--   heavy     how much of the rain sound is the heavy loop
local WeatherTypes = {
	Clear = { cumulus = 0.45, strato = 0, cirrus = 0.8, overcast = 0, gloom = 0, rain = 0, heavy = 0 },
	Cloudy = { cumulus = 0.85, strato = 0.55, cirrus = 0.35, overcast = 0.45, gloom = 0.35, rain = 0, heavy = 0 },
	Rain = { cumulus = 0.6, strato = 1, cirrus = 0, overcast = 0.9, gloom = 0.7, rain = 0.55, heavy = 0.15 },
	HeavyRain = { cumulus = 0.5, strato = 1, cirrus = 0, overcast = 1, gloom = 0.9, rain = 1, heavy = 1 },
}

return WeatherTypes
