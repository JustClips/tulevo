--[[
	City ambience: what the city sounds like around you, by the in-game clock and the weather.

	  * a distant traffic bed (busier by day, a quieter hum at night),
	  * crickets at night when it's dry,
	  * one-off sounds placed somewhere round you so they come from a direction:
	      birds    mornings most, a little through the day, never at night or in the rain
	      dogs     now and then, more at night, fewer in the rain
	      sirens   police wail or ambulance hi-lo far off, a bit more at night and in storms
	      horns    with the traffic, mostly by day
	  * everything is muffled under a roof (same idea as the rain sound).

	Volumes and how often things play: Config.Ambience. Sounds come from tools/city_sounds.py.
	Weather is read from Client/Weather (current blended weather), time from Shared/GameTime.
]]
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local Debris = game:GetService("Debris")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local GameTime = require(Shared:WaitForChild("GameTime"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))

local A = Config.Ambience
if not A or not A.Enabled then
	return
end

local Weather = nil
do
	local mod = script.Parent:FindFirstChild("Weather")
	if mod then
		local ok, m = pcall(require, mod)
		Weather = if ok then m else nil
	end
end

local function weatherNow(): { [string]: number }
	if Weather and Config.Weather and Config.Weather.Enabled then
		local ok, w = pcall(Weather.current)
		if ok and w then
			return w
		end
	end
	return { rain = 0, storm = 0 }
end

local function hourNow(): number
	local t = GameTime.now()
	return if t then t.clock else Lighting.ClockTime
end

local function smooth(a: number, b: number, x: number): number
	local t = math.clamp((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)
end

-- 1 in daylight, 0 at night, smooth through dawn (5:30-7:30) and dusk (19:30-21:30)
local function daylight(h: number): number
	return smooth(5.5, 7.5, h) * (1 - smooth(19.5, 21.5, h))
end

-- sound group with a muffler for indoors -----------------------------------------
local group = Instance.new("SoundGroup")
group.Name = "Ambience"
group.Volume = A.Volume or 1
group.Parent = SoundService
local muffle = Instance.new("EqualizerSoundEffect")
muffle.HighGain, muffle.MidGain, muffle.LowGain = 0, 0, 0
muffle.Parent = group

local function loop(name: string, id: number?): Sound
	local s = Instance.new("Sound")
	s.Name = name
	s.SoundId = if id then `rbxassetid://{id}` else ""
	s.Looped = true
	s.Volume = 0
	s.SoundGroup = group
	s.Parent = SoundService
	return s
end

local dayLoop = loop("CityDay", SoundIds.CityDayLoop)
local nightLoop = loop("CityNight", SoundIds.CityNightLoop)
local crickets = loop("Crickets", SoundIds.CricketsLoop)

-- one-offs ---------------------------------------------------------------------------
-- dist: how far away they're placed (studs); rolloff: distance where they start to fade
local KINDS = {
	Birds = {
		ids = { SoundIds.Birds1, SoundIds.Birds2, SoundIds.Birds3 },
		dist = { 20, 55 },
		up = { 8, 25 },
		rolloff = 40,
		weight = function(h, day, w)
			local morning = 1 - smooth(10, 12, h) * 0.7 -- busy mornings, quieter later
			return day * morning * (1 - w.rain) ^ 2
		end,
	},
	Dogs = {
		ids = { SoundIds.DogBark1, SoundIds.DogBark2 },
		dist = { 50, 110 },
		up = { 0, 4 },
		rolloff = 70,
		weight = function(_h, day, w)
			return (0.5 + 0.7 * (1 - day)) * (1 - 0.6 * w.rain)
		end,
	},
	Sirens = {
		ids = { SoundIds.SirenWail, SoundIds.SirenHiLo },
		dist = { 90, 180 },
		up = { 0, 10 },
		rolloff = 150,
		weight = function(_h, day, w)
			return 0.8 + 0.4 * (1 - day) + 0.4 * (w.storm or 0)
		end,
	},
	Horns = {
		ids = { SoundIds.CarHorn1, SoundIds.CarHorn2 },
		dist = { 60, 140 },
		up = { 0, 4 },
		rolloff = 80,
		weight = function(_h, day, w)
			return 0.25 + 0.75 * day + 0.2 * w.rain
		end,
	},
}
local cooldown: { [string]: number } = {}
local busy: { [string]: boolean } = {}

local function playOneShot(kind: string, camPos: Vector3)
	local k = KINDS[kind]
	local id = k.ids[math.random(1, #k.ids)]
	if not id then
		return
	end
	local ang = math.random() * math.pi * 2
	local d = k.dist[1] + math.random() * (k.dist[2] - k.dist[1])
	local up = k.up[1] + math.random() * (k.up[2] - k.up[1])
	local at = Instance.new("Attachment")
	at.Name = "Ambience" .. kind
	at.Parent = workspace.Terrain
	at.WorldPosition = camPos + Vector3.new(math.cos(ang) * d, up, math.sin(ang) * d)
	local s = Instance.new("Sound")
	s.SoundId = `rbxassetid://{id}`
	s.Volume = (A[kind] or 0.3) * math.random(85, 115) / 100
	s.PlaybackSpeed = math.random(94, 106) / 100
	s.RollOffMode = Enum.RollOffMode.InverseTapered
	s.RollOffMinDistance = k.rolloff
	s.RollOffMaxDistance = 1500
	s.SoundGroup = group
	s.Parent = at
	s:Play()
	busy[kind] = true
	s.Ended:Once(function()
		busy[kind] = false
		at:Destroy()
	end)
	Debris:AddItem(at, 20)
	task.delay(20, function()
		busy[kind] = false
	end)
end

-- main loop ----------------------------------------------------------------------------
local indoor, indoorTarget, roofClock = 0, 0, 0
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude

local function approach(cur: number, target: number, dt: number, rate: number): number
	return cur + (target - cur) * math.min(dt * rate, 1)
end

RunService.Heartbeat:Connect(function(dt)
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local w = weatherNow()
	local rain = math.clamp(w.rain or 0, 0, 1)
	local h = hourNow()
	local day = daylight(h)

	roofClock -= dt
	if roofClock <= 0 then
		roofClock = 0.3
		local ignore: { Instance } = {}
		for _, p in Players:GetPlayers() do
			if p.Character then
				table.insert(ignore, p.Character)
			end
		end
		local sky = workspace:FindFirstChild("WeatherSky")
		if sky then
			table.insert(ignore, sky)
		end
		params.FilterDescendantsInstances = ignore
		indoorTarget = if workspace:Raycast(camPos, Vector3.new(0, 150, 0), params) then 1 else 0
	end
	indoor = approach(indoor, indoorTarget, dt, 3)
	muffle.HighGain = -22 * indoor
	muffle.MidGain = -8 * indoor
	group.Volume = (A.Volume or 1) * (1 - 0.35 * indoor)

	-- beds (rain covers some of the traffic; crickets hide from the rain)
	dayLoop.Volume = approach(dayLoop.Volume, A.DayTraffic * day * (1 - 0.3 * rain), dt, 1)
	nightLoop.Volume = approach(nightLoop.Volume, A.NightTraffic * (1 - day) * (1 - 0.3 * rain), dt, 1)
	crickets.Volume = approach(crickets.Volume, A.Crickets * (1 - day) * (1 - rain) ^ 2, dt, 0.5)
	for _, s in { dayLoop, nightLoop, crickets } do
		if s.Volume > 0.002 and not s.IsPlaying then
			s:Play()
		elseif s.Volume <= 0.002 and s.IsPlaying then
			s:Stop()
		end
	end

	-- one-offs: each has an average gap (Config.Ambience.Every) scaled by how likely it is now
	local now = os.clock()
	for kind, k in KINDS do
		local every = A.Every and A.Every[kind]
		if every and not busy[kind] and now >= (cooldown[kind] or 0) then
			local weight = math.max(k.weight(h, day, w), 0)
			if weight > 0 and math.random() < dt / every * weight then
				cooldown[kind] = now + every * 0.25
				playOneShot(kind, camPos)
			end
		end
	end
end)
