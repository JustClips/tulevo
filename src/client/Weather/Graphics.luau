-- GTA-style post look on top of Sky.luau (docs/graphics.md, values in Config.Graphics).
-- Sky sets the time-of-day / weather light; this adds the "film" layer GTA V has:
--   Haze    stronger distance haze, morning mist, a bit more in rain (scales Sky's Atmosphere)
--   Blur    soft far-distance blur only (DepthOfField, nothing near the player), more in rain
--   Grade   extra contrast/colour, warm sun by day, cool blue at night ("GtaGrade")
--   Bloom   soft glow on bright sky by day, strong glow on street lights / neon at night
--   Shadows crisper sun shadows
-- Quality: High (all), Medium (no blur, lighter bloom), Low (grade + haze only). Auto picks
-- Medium on phones/tablets and Low when the player's Roblox graphics level is low.
-- Only on this client; nothing replicates. F8 Graphics tab tunes it live through get/set.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))

local Graphics = {}

local cfg = Config.Graphics or {}

-- live values (start from Config, F8 changes them for this session)
local values = {
	Quality = cfg.Quality or "Auto",
	Haze = cfg.Haze or 1.15,
	MorningFog = cfg.MorningFog or 1,
	Blur = cfg.Blur or 0.14,
	BlurStart = cfg.BlurStart or 200,
	Bloom = cfg.Bloom or 1,
	Contrast = cfg.Contrast or 0.08,
	Saturation = cfg.Saturation or 0.06,
	Warmth = cfg.Warmth or 1,
	ShadowSoftness = cfg.ShadowSoftness or 0.12,
}
local defaults = table.clone(values)

-- what each quality turns on
local PRESETS = {
	High = { Blur = true, Bloom = true, BloomScale = 1, SunRays = true },
	Medium = { Blur = false, Bloom = true, BloomScale = 0.7, SunRays = true },
	Low = { Blur = false, Bloom = false, BloomScale = 0, SunRays = false },
}
Graphics.QUALITIES = { "Auto", "High", "Medium", "Low" }

local bloom: BloomEffect
local blur: DepthOfFieldEffect
local grade: ColorCorrectionEffect

local function own(className: string, name: string)
	local obj = Lighting:FindFirstChild(name)
	if not obj or obj.ClassName ~= className then
		obj = Instance.new(className)
		obj.Name = name
		obj.Parent = Lighting
	end
	return obj
end

-- the place's default Bloom / DepthOfField / SunRays would stack with ours
local OURS = { GtaBloom = true, GtaDistanceBlur = true, WeatherSunRays = true }
local function quietStrays()
	for _, c in Lighting:GetChildren() do
		if (c:IsA("BloomEffect") or c:IsA("DepthOfFieldEffect") or c:IsA("SunRaysEffect")) and not OURS[c.Name] then
			c.Enabled = false
		end
	end
end

-- the quality actually in use ("Auto" resolved)
function Graphics.quality(): string
	local q = values.Quality
	if q ~= "Auto" then
		return q
	end
	local ok, level = pcall(function()
		return UserSettings():GetService("UserGameSettings").SavedQualityLevel
	end)
	if ok and level ~= Enum.SavedQualitySetting.Automatic and level.Value <= 3 then
		return "Low"
	end
	if UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled then
		return "Medium"
	end
	return "High"
end

function Graphics.get(key: string): any
	return values[key]
end

function Graphics.set(key: string, value: any)
	values[key] = value
end

function Graphics.reset(key: string)
	values[key] = defaults[key]
end

function Graphics.start()
	bloom = own("BloomEffect", "GtaBloom") :: BloomEffect
	blur = own("DepthOfFieldEffect", "GtaDistanceBlur") :: DepthOfFieldEffect
	grade = own("ColorCorrectionEffect", "GtaGrade") :: ColorCorrectionEffect
	blur.NearIntensity = 0
	quietStrays()
	Lighting.ChildAdded:Connect(function()
		task.defer(quietStrays)
	end)
end

local function smoothBump(h: number, a: number, b: number, c: number, d: number): number
	-- 0 before a, ramps to 1 by b, stays 1 to c, back to 0 by d
	if h <= a or h >= d then
		return 0
	elseif h < b then
		return (h - a) / (b - a)
	elseif h <= c then
		return 1
	end
	return 1 - (h - c) / (d - c)
end

-- runs every frame right after Sky.update. w = blended weather, night = Sky.night()
function Graphics.update(w, night: number)
	if not bloom then
		return
	end
	local p = PRESETS[Graphics.quality()] or PRESETS.High
	local driveSky = Config.Weather.DriveSky
	local hour = Lighting.ClockTime % 24
	local wet = math.max(w.rain, w.gloom * 0.6)

	-- haze: scale what Sky set, plus a low mist around sunrise (GTA mornings)
	local atmosphere = Lighting:FindFirstChildOfClass("Atmosphere")
	if atmosphere and driveSky then
		local mist = smoothBump(hour, 4.5, 6, 7.5, 9.5) * (1 - w.gloom) * 0.07 * values.MorningFog
		atmosphere.Density = math.clamp(atmosphere.Density * values.Haze + mist, 0, 0.6)
		atmosphere.Haze = math.clamp(atmosphere.Haze * (0.85 + 0.15 * values.Haze) + mist * 10, 0, 3)
	end

	-- far-only blur; Roblox caps FocusDistance at 200 and InFocusRadius at 50
	blur.Enabled = p.Blur and values.Blur > 0
	if blur.Enabled then
		local start = math.clamp(values.BlurStart, 50, 250)
		blur.InFocusRadius = math.clamp(start * 0.25, 10, 50)
		blur.FocusDistance = math.clamp(start - blur.InFocusRadius, 0, 200)
		blur.FarIntensity = math.clamp(values.Blur * (1 + 0.9 * wet), 0, 1)
		blur.NearIntensity = 0
	end

	-- bloom: gentle by day, street lights and neon glow at night, wet streets glow more
	bloom.Enabled = p.Bloom and values.Bloom > 0
	if bloom.Enabled then
		local s = values.Bloom * p.BloomScale
		bloom.Intensity = math.clamp((0.3 + 0.5 * night + 0.15 * wet) * s, 0, 1)
		bloom.Size = math.floor(22 + 14 * night)
		bloom.Threshold = 1.5 - 0.65 * night - 0.15 * wet
	end

	-- sun rays (Sky sets the strength; we only switch them off on Low)
	local rays = Lighting:FindFirstChild("WeatherSunRays")
	if rays then
		rays.Enabled = p.SunRays
	end

	-- grade: warm sun by day, cool blue at night, flatter in grey weather
	local warm = values.Warmth * (1 - w.gloom)
	local day = Color3.fromRGB(255, 246, 232)
	local nightTint = Color3.fromRGB(226, 234, 255)
	local tint = day:Lerp(nightTint, night)
	grade.TintColor = Color3.new(1, 1, 1):Lerp(tint, math.clamp(warm, 0, 1))
	grade.Contrast = values.Contrast * (1 - 0.4 * w.gloom)
	grade.Saturation = values.Saturation * (1 - 0.6 * w.gloom)
	grade.Brightness = 0

	if driveSky then
		Lighting.ShadowSoftness = values.ShadowSoftness + 0.35 * w.gloom -- overcast = soft shadows
	end
end

return Graphics
