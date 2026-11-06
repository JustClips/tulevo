-- Server lightning (ModuleScript; Server/LightningRunner starts it). While the weather's `storm`
-- value (Shared/WeatherTypes) is up, picks strikes and tells every client through
-- ReplicatedStorage.LightningStrike:FireAllClients(pos, normal, kind, seed):
--   kind "ground"  a bolt down to pos (normal = surface it hit) - flash, impact, thunder
--   kind "cloud"   a flash inside the clouds above pos, no bolt - flash and a far rumble
--   seed           same number for everyone, so every client draws the same bolt shape
-- Strikes are looks and sound only: nobody is hurt. Tall things get hit more often (of three
-- spots near each other the highest one wins). Client/Lightning.client draws it.
-- The debug panel uses Lightning.strikeNear(player).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local WeatherTypes = require(Shared:WaitForChild("WeatherTypes"))

local L = Config.Lightning
local Lightning = {}

local remote: RemoteEvent

-- same blend as Client/Weather.current(), only the storm value
local function stormLevel(): number
	local to = WeatherTypes[Shared:GetAttribute("Weather") or "Clear"] or WeatherTypes.Clear
	local from = WeatherTypes[Shared:GetAttribute("WeatherFrom") or "Clear"] or to
	local since = Shared:GetAttribute("WeatherSince") or 0
	local fade = math.max(Config.Weather.FadeSeconds, 0.01)
	local a = math.clamp((workspace:GetServerTimeNow() - since) / fade, 0, 1)
	a = a * a * (3 - 2 * a)
	local f, t = from.storm or 0, to.storm or 0
	return f + (t - f) * a
end

local function rayParams(): RaycastParams
	local ignore = {}
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(ignore, p.Character)
		end
	end
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = ignore
	params.IgnoreWater = false
	return params
end

-- the top surface at x, z (roof or ground), or nil if there's nothing there
local function surface(x: number, z: number, params: RaycastParams): RaycastResult?
	return workspace:Raycast(Vector3.new(x, 3000, z), Vector3.new(0, -6000, 0), params)
end

local function fire(pos: Vector3, normal: Vector3, kind: string)
	remote:FireAllClients(pos, normal, kind, math.random(1, 2 ^ 30))
end

-- a ground strike around (x, z): of three spots close together, the highest is hit
local function groundStrike(x: number, z: number, spread: number): boolean
	local params = rayParams()
	local best: RaycastResult? = nil
	for i = 1, 3 do
		local ox = if i == 1 then 0 else (math.random() * 2 - 1) * spread
		local oz = if i == 1 then 0 else (math.random() * 2 - 1) * spread
		local hit = surface(x + ox, z + oz, params)
		if hit and (not best or hit.Position.Y > best.Position.Y) then
			best = hit
		end
	end
	if not best then
		return false
	end
	fire(best.Position, best.Normal, "ground")
	return true
end

local function cloudFlash(x: number, z: number)
	fire(Vector3.new(x, 900 + math.random() * 400, z), Vector3.yAxis, "cloud")
end

local function randomAround(center: Vector3, minR: number, maxR: number): (number, number)
	local ang = math.random() * math.pi * 2
	local r = minR + math.random() * (maxR - minR)
	return center.X + math.cos(ang) * r, center.Z + math.sin(ang) * r
end

local function randomPlayerPos(): Vector3?
	local list = {}
	for _, p in Players:GetPlayers() do
		local root = p.Character and p.Character:FindFirstChild("HumanoidRootPart")
		if root then
			table.insert(list, (root :: BasePart).Position)
		end
	end
	return if #list > 0 then list[math.random(#list)] else nil
end

local function strike(storm: number)
	local center = randomPlayerPos()
	if not center then
		return
	end
	if math.random() < L.CloudChance then
		cloudFlash(randomAround(center, 200, 2500))
		return
	end
	-- near strikes only in a proper storm, never in a heavy shower
	local near = storm > 0.7 and math.random() < L.NearChance
	local x, z
	if near then
		x, z = randomAround(center, 25, 90)
	else
		x, z = randomAround(center, 160, 2200)
	end
	if not groundStrike(x, z, if near then 15 else 60) then
		cloudFlash(x, z)
	end
end

-- debug: a ground strike 25-45 studs from this player
function Lightning.strikeNear(player: Player): (boolean, string)
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
	if not root then
		return false, "No character"
	end
	local x, z = randomAround((root :: BasePart).Position, 25, 45)
	if groundStrike(x, z, 4) then
		return true, "Lightning strike next to you"
	end
	return false, "Nothing to hit there"
end

function Lightning.start()
	if remote or not L or not L.Enabled then
		return
	end
	remote = Instance.new("RemoteEvent")
	remote.Name = "LightningStrike"
	remote.Parent = ReplicatedStorage
	task.spawn(function()
		local untilNext = 3
		while true do
			task.wait(0.5)
			local storm = stormLevel()
			if storm > 0.05 then
				untilNext -= 0.5 * storm
				if untilNext <= 0 then
					strike(storm)
					untilNext = L.MinGap + math.random() * (L.MaxGap - L.MinGap)
					-- sometimes a second strike right after (storms come in bursts)
					if storm > 0.7 and math.random() < 0.2 then
						untilNext = 0.6 + math.random() * 1.5
					end
				end
			end
		end
	end)
end

return Lightning
