-- Client weather: mixes the server's current weather (attributes on ReplicatedStorage.Shared,
-- set by Server/Weather) with the one before it over Config.Weather.FadeSeconds, then hands
-- the blended look to:
--   Sky     lighting, atmosphere, colour grading by time of day + weather (GTA-style)
--   Clouds  drifting mesh clouds + scrolling cirrus / overcast layers
--   Rain    rain streaks that stop at roofs, splashes, ripples, mist and the rain sound
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local WeatherTypes = require(Shared:WaitForChild("WeatherTypes"))

local Sky = require(script:WaitForChild("Sky"))
local Clouds = require(script:WaitForChild("Clouds"))
local Rain = require(script:WaitForChild("Rain"))

local Weather = {}

local function smooth(t: number): number
	t = math.clamp(t, 0, 1)
	return t * t * (3 - 2 * t)
end

-- the blended weather right now: same keys as WeatherTypes entries
function Weather.current()
	local to = WeatherTypes[Shared:GetAttribute("Weather") or "Clear"] or WeatherTypes.Clear
	local from = WeatherTypes[Shared:GetAttribute("WeatherFrom") or "Clear"] or to
	local since = Shared:GetAttribute("WeatherSince") or 0
	local a = smooth((workspace:GetServerTimeNow() - since) / math.max(Config.Weather.FadeSeconds, 0.01))
	local mix = {}
	for k, v in to do
		local f = from[k] or v
		mix[k] = f + (v - f) * a
	end
	return mix
end

function Weather.start()
	local W = Config.Weather
	if not W or not W.Enabled then
		return
	end
	Sky.start()
	Clouds.start()
	Rain.start()
	RunService.RenderStepped:Connect(function(dt)
		local mix = Weather.current()
		Sky.update(mix, dt)
		Clouds.update(mix, dt, Sky.cloudTint())
		Rain.update(mix, dt)
	end)
end

return Weather
