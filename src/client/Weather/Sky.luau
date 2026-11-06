-- GTA-style sky and light: a key per time of day (deep blue noon, warm hazy golden hour,
-- orange sunset, blue dusk, dark night), blended by the in-game clock, then pulled toward
-- flat grey light by the weather's "gloom" (rain, overcast).
-- Writes Lighting, its Atmosphere and Sky (made if missing) and our own ColorCorrection +
-- SunRays ("WeatherGrade", "WeatherSunRays"). Only on this client; nothing replicates.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local GameTime = require(Shared:WaitForChild("GameTime"))

local Sky = {}

local function rgb(r, g, b)
	return Color3.fromRGB(r, g, b)
end

-- hour, then the look at that hour. cloud = colour the cloud meshes are tinted.
local KEYS = {
	{
		h = 0,
		amb = rgb(18, 20, 30),
		out = rgb(48, 54, 80),
		bright = 0.6,
		exp = 0.15,
		atmo = rgb(58, 68, 98),
		decay = rgb(18, 22, 42),
		haze = 0.6,
		glare = 0,
		dens = 0.32,
		cloud = rgb(46, 52, 72),
		sat = -0.05,
		rays = 0,
	},
	{
		h = 5.0,
		amb = rgb(22, 24, 36),
		out = rgb(60, 62, 92),
		bright = 0.7,
		exp = 0.15,
		atmo = rgb(72, 78, 112),
		decay = rgb(28, 30, 56),
		haze = 0.8,
		glare = 0,
		dens = 0.33,
		cloud = rgb(60, 62, 88),
		sat = -0.05,
		rays = 0,
	},
	{
		h = 6.2,
		amb = rgb(70, 58, 60),
		out = rgb(160, 122, 112),
		bright = 1.8,
		exp = 0.05,
		atmo = rgb(255, 186, 148),
		decay = rgb(150, 92, 96),
		haze = 2.0,
		glare = 0.7,
		dens = 0.36,
		cloud = rgb(255, 196, 168),
		sat = 0.1,
		rays = 0.12,
	},
	{
		h = 8.0,
		amb = rgb(82, 82, 92),
		out = rgb(140, 140, 152),
		bright = 2.6,
		exp = 0,
		atmo = rgb(214, 222, 236),
		decay = rgb(112, 132, 172),
		haze = 1.3,
		glare = 0.35,
		dens = 0.3,
		cloud = rgb(255, 250, 244),
		sat = 0.08,
		rays = 0.06,
	},
	{
		h = 12.5,
		amb = rgb(86, 88, 96),
		out = rgb(150, 150, 156),
		bright = 3.0,
		exp = 0,
		atmo = rgb(198, 214, 236),
		decay = rgb(98, 124, 172),
		haze = 1.0,
		glare = 0.2,
		dens = 0.28,
		cloud = rgb(255, 255, 255),
		sat = 0.06,
		rays = 0.04,
	},
	{
		h = 16.5,
		amb = rgb(90, 84, 80),
		out = rgb(156, 142, 128),
		bright = 2.8,
		exp = 0,
		atmo = rgb(232, 212, 190),
		decay = rgb(134, 112, 120),
		haze = 1.5,
		glare = 0.45,
		dens = 0.3,
		cloud = rgb(255, 238, 216),
		sat = 0.12,
		rays = 0.08,
	},
	{
		h = 18.3,
		amb = rgb(92, 66, 62),
		out = rgb(168, 112, 98),
		bright = 2.0,
		exp = 0.05,
		atmo = rgb(255, 156, 108),
		decay = rgb(142, 70, 82),
		haze = 2.3,
		glare = 0.9,
		dens = 0.36,
		cloud = rgb(255, 164, 124),
		sat = 0.16,
		rays = 0.14,
	},
	{
		h = 19.4,
		amb = rgb(40, 38, 58),
		out = rgb(76, 68, 104),
		bright = 1.0,
		exp = 0.1,
		atmo = rgb(116, 94, 134),
		decay = rgb(42, 36, 74),
		haze = 1.1,
		glare = 0.1,
		dens = 0.34,
		cloud = rgb(112, 92, 124),
		sat = 0.02,
		rays = 0,
	},
	{
		h = 20.6,
		amb = rgb(18, 20, 30),
		out = rgb(48, 54, 80),
		bright = 0.6,
		exp = 0.15,
		atmo = rgb(58, 68, 98),
		decay = rgb(18, 22, 42),
		haze = 0.6,
		glare = 0,
		dens = 0.32,
		cloud = rgb(46, 52, 72),
		sat = -0.05,
		rays = 0,
	},
	{
		h = 24,
		amb = rgb(18, 20, 30),
		out = rgb(48, 54, 80),
		bright = 0.6,
		exp = 0.15,
		atmo = rgb(58, 68, 98),
		decay = rgb(18, 22, 42),
		haze = 0.6,
		glare = 0,
		dens = 0.32,
		cloud = rgb(46, 52, 72),
		sat = -0.05,
		rays = 0,
	},
}

local function lerp(a, b, t)
	if typeof(a) == "Color3" then
		return a:Lerp(b, t)
	end
	return a + (b - a) * t
end

local function sample(hour: number)
	for i = 1, #KEYS - 1 do
		local a, b = KEYS[i], KEYS[i + 1]
		if hour >= a.h and hour <= b.h then
			local t = (hour - a.h) / (b.h - a.h)
			t = t * t * (3 - 2 * t)
			local out = {}
			for k, v in a do
				out[k] = lerp(v, b[k], t)
			end
			return out
		end
	end
	return KEYS[1]
end

local function grey(c: Color3, amount: number, dim: number): Color3
	local l = (c.R * 0.3 + c.G * 0.55 + c.B * 0.15) * dim
	return c:Lerp(Color3.new(l * 0.96, l * 0.99, l * 1.06), amount)
end

local atmosphere: Atmosphere
local grade: ColorCorrectionEffect
local rays: SunRaysEffect
local skyObj: Sky
local tint = Color3.new(1, 1, 1)
local nightness = 0
local flash = 0 -- lightning: 0 none .. 1 full white-blue flash (decays fast)
local FLASH_COLOR = Color3.fromRGB(205, 215, 255)

local function find(className: string, name: string?)
	for _, c in Lighting:GetChildren() do
		if c.ClassName == className and (not name or c.Name == name) then
			return c
		end
	end
	local obj = Instance.new(className)
	if name then
		obj.Name = name
	end
	obj.Parent = Lighting
	return obj
end

function Sky.start()
	atmosphere = find("Atmosphere") :: Atmosphere
	skyObj = find("Sky") :: Sky
	skyObj.CelestialBodiesShown = true
	skyObj.SunAngularSize = 12
	skyObj.MoonAngularSize = 9
	skyObj.StarCount = 3000
	grade = find("ColorCorrectionEffect", "WeatherGrade") :: ColorCorrectionEffect
	rays = find("SunRaysEffect", "WeatherSunRays") :: SunRaysEffect
	rays.Spread = 0.7
	-- Roblox's own volumetric clouds would fight our mesh clouds
	local clouds = workspace.Terrain:FindFirstChildOfClass("Clouds")
	if clouds then
		clouds.Enabled = false
	end
end

-- colour for the cloud meshes this frame (time of day + weather)
function Sky.cloudTint(): Color3
	return tint
end

-- lightning lights up the sky, the city and the clouds for a moment
function Sky.addFlash(amount: number)
	flash = math.min(1.5, flash + amount)
end

-- 0 by day, 1 at night (used by Rain for how bright streaks are)
function Sky.night(): number
	return nightness
end

function Sky.update(w, dt: number)
	local hour = Lighting.ClockTime
	if Config.Time.DriveLighting then
		local t = GameTime.now()
		if t then
			hour = t.clock
			Lighting.ClockTime = hour -- every frame here, so the sun glides instead of stepping
		end
	end
	local k = sample(hour % 24)
	nightness = math.clamp(1 - (k.bright - 0.6) / 1.4, 0, 1)
	local g = w.gloom
	local dim = 1 - 0.35 * g
	flash *= math.exp(-dt * 14)
	if flash < 0.005 then
		flash = 0
	end
	local f = math.min(flash, 1)
	tint = grey(k.cloud, g * 0.85, 1 - 0.45 * g):Lerp(FLASH_COLOR, f * 0.85)
	if not Config.Weather.DriveSky then
		return
	end
	Lighting.Ambient = grey(k.amb, g, dim):Lerp(FLASH_COLOR, f * 0.5)
	Lighting.OutdoorAmbient = grey(k.out, g * 0.9, dim):Lerp(FLASH_COLOR, f * 0.85)
	Lighting.Brightness = k.bright * (1 - 0.55 * g) + 3 * f
	Lighting.ExposureCompensation = k.exp - 0.15 * g + 0.9 * f
	Lighting.EnvironmentDiffuseScale = 1
	Lighting.EnvironmentSpecularScale = 0.6 + 0.4 * w.rain -- wet streets shine
	atmosphere.Color = grey(k.atmo, g, 1 - 0.3 * g):Lerp(FLASH_COLOR, f * 0.7)
	atmosphere.Decay = grey(k.decay, g, 1 - 0.2 * g)
	atmosphere.Haze = k.haze + (1.8 - k.haze) * g
	atmosphere.Glare = k.glare * (1 - g)
	-- kept fairly low so the storm clouds overhead still show through the rain
	atmosphere.Density = k.dens + (0.36 - k.dens) * g + 0.02 * w.rain
	atmosphere.Offset = 0.1
	grade.Saturation = k.sat - 0.22 * g
	grade.Contrast = 0.06 - 0.03 * g
	grade.Brightness = 0
	grade.TintColor = Color3.new(1, 1, 1):Lerp(Color3.fromRGB(226, 232, 244), g)
	rays.Intensity = k.rays * (1 - g)
	skyObj.StarCount = math.floor(3000 * (1 - g))
end

return Sky
