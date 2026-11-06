--[[
	Gun sounds (client). Volumes and ranges: Config.Weapons.Sound. Sound files: tools/gun_sounds.py
	(real AR-15 recordings for the shots, the bullet sounds built from the physics).

	Your own shot: the close-up recording, flat in both ears (2D).
	Someone else's shot, by how far the shooter is from you:
		close             the same close-up shot, from where the gun is
		a street or two   the distant recording (thinner crack, longer echo)
		far away          a dull pop and a low roll, or nothing at all past MaxRange
		The bang arrives late the further you are (speed of sound), so from far away the
		bullets land before you hear the gun.
	Every bullet:
		passes close to you     a supersonic crack (and a whizz if it's very close)
		hits something          an impact for what it hit: concrete, metal, wood, dirt, glass,
		                        a person; hard surfaces sometimes ricochet
	Impacts and cracks don't depend on how far the shooter is, so being shot at from far away
	is mostly the bullets smacking into things around you.
]]

local ContentProvider = game:GetService("ContentProvider")
local Debris = game:GetService("Debris")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local SoundService = game:GetService("SoundService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))

local player = Players.LocalPlayer
local GunAudio = {}

local function cfg()
	return Config.Weapons.Sound
end

local BULLET_SPEED = 3200 -- studs/s (~900 m/s, a 5.56 round)

-- Enum.Material name -> impact sound set. Anything not listed sounds like concrete (the city).
local MATERIAL = {
	Concrete = "Concrete",
	Brick = "Concrete",
	Cobblestone = "Concrete",
	Pavement = "Concrete",
	Asphalt = "Concrete",
	Slate = "Concrete",
	Granite = "Concrete",
	Marble = "Concrete",
	Rock = "Concrete",
	Basalt = "Concrete",
	Limestone = "Concrete",
	Sandstone = "Concrete",
	CrackedLava = "Concrete",
	Plaster = "Concrete",
	Metal = "Metal",
	DiamondPlate = "Metal",
	CorrodedMetal = "Metal",
	Foil = "Metal",
	Wood = "Wood",
	WoodPlanks = "Wood",
	Cardboard = "Wood",
	Grass = "Dirt",
	LeafyGrass = "Dirt",
	Ground = "Dirt",
	Mud = "Dirt",
	Sand = "Dirt",
	Snow = "Dirt",
	Salt = "Dirt",
	Pebble = "Dirt",
	Fabric = "Dirt",
	Carpet = "Dirt",
	Rubber = "Dirt",
	Water = "Dirt",
	Glass = "Glass",
	Ice = "Glass",
	Glacier = "Glass",
}
local HARD = { Concrete = true, Metal = true }

-- every sound name -> how many variations (Name1..NameN in Shared.SoundIds)
local variants: { [string]: number } = {}
for name in SoundIds do
	local base, n = string.match(name, "^(.-)(%d+)$")
	if base and n then
		variants[base] = math.max(variants[base] or 0, tonumber(n) :: number)
	end
end

local group = Instance.new("SoundGroup")
group.Name = "Guns"
group.Parent = SoundService

local function pick(base: string): number?
	local n = variants[base]
	return n and SoundIds[base .. math.random(1, n)]
end

local function new(id: number, volume: number): Sound
	local s = Instance.new("Sound")
	s.SoundId = "rbxassetid://" .. id
	s.Volume = volume * cfg().Volume
	s.PlaybackSpeed = 1 + (math.random() * 2 - 1) * cfg().PitchJitter
	s.SoundGroup = group
	-- we set the distance loudness ourselves (per layer), so the engine only pans
	s.RollOffMode = Enum.RollOffMode.Inverse
	s.RollOffMinDistance = 5000
	s.RollOffMaxDistance = 10000
	return s
end

-- Play a sound at a point in the world after `delay` seconds.
local function at(base: string, pos: Vector3, volume: number, delay: number?)
	local id = pick(base)
	if not id or volume < 0.005 then
		return
	end
	local function go()
		local a = Instance.new("Attachment")
		a.WorldPosition = pos
		a.Parent = workspace.Terrain
		local s = new(id, volume)
		s.Parent = a
		s:Play()
		Debris:AddItem(a, 4)
	end
	if delay and delay > 0.01 then
		task.delay(delay, go)
	else
		go()
	end
end

-- Play a sound flat in both ears (your own gun).
local function flat(base: string, volume: number)
	local id = pick(base)
	if not id then
		return
	end
	local s = new(id, volume)
	s.Parent = SoundService
	s:Play()
	Debris:AddItem(s, 4)
end

local function listener(): Vector3
	local cam = workspace.CurrentCamera
	return if cam then cam.CFrame.Position else Vector3.zero
end

local function smooth(a: number, b: number, x: number): number
	local t = math.clamp((x - a) / (b - a), 0, 1)
	return t * t * (3 - 2 * t)
end

local function soundSet(def): string
	return def.Sound or "Carbine"
end

-- Your own shot (called the moment you fire, before the server answers).
function GunAudio.ownShot(def)
	local c = cfg()
	if not c.Enabled then
		return
	end
	flat(soundSet(def) .. "Shot", c.OwnShot)
end

-- Someone else's gun going off at `origin`.
local function report(def, origin: Vector3, ear: Vector3)
	local c = cfg()
	local d = (origin - ear).Magnitude
	if d > c.MaxRange then
		return
	end
	local gain = c.Shot * (c.ShotRef / math.max(d, c.ShotRef)) ^ c.ShotFalloff
	gain *= 1 - smooth(c.MaxRange * 0.6, c.MaxRange, d)
	local toDistant = smooth(c.NearRange * 0.6, c.NearRange * 1.4, d)
	local toFar = smooth(c.DistantRange * 0.7, c.DistantRange * 1.3, d)
	local delay = d / c.SpeedOfSound
	local set = soundSet(def)
	at(set .. "Shot", origin, gain * (1 - toDistant), delay)
	at(set .. "Distant", origin, gain * toDistant * (1 - toFar) * c.DistantBoost, delay)
	at(set .. "Far", origin, gain * toFar * c.FarBoost, delay)
end

-- One bullet from origin to hit: crack/whizz if it passes you, then the impact.
local function bullet(origin: Vector3, hit: Vector3, kind: string, ear: Vector3, mine: boolean)
	local c = cfg()
	local path = hit - origin
	local len = path.Magnitude
	if len < 0.5 then
		return
	end
	local dir = path / len
	-- closest the bullet came to you, and how far along the path that was
	local along = math.clamp((ear - origin):Dot(dir), 0, len)
	local miss = (origin + dir * along - ear).Magnitude
	if not mine and along > 3 and along < len - 2 and miss < c.CrackRadius then
		local close = origin + dir * along
		local t = along / BULLET_SPEED
		at("BulletCrack", close, c.Crack * math.min(1, c.CrackRef / math.max(miss, 1)) ^ 0.8, t)
		if miss < c.WhizRadius then
			at("BulletWhiz", close, c.Whiz * (1 - miss / c.WhizRadius), t)
		end
	end

	if kind == "" then
		return -- flew out of range
	end
	local d = (hit - ear).Magnitude
	if d > c.ImpactRange then
		return
	end
	local t = len / BULLET_SPEED + d / c.SpeedOfSound
	if kind == "Body" then
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
		if root and (root.Position - hit).Magnitude < 4 then
			flat("ImpactBody", c.BodyOnYou) -- you got hit
			return
		end
		at("ImpactBody", hit, c.Body * c.ImpactRef / math.max(d, c.ImpactRef), t)
		return
	end
	local set = MATERIAL[kind] or "Concrete"
	local gain = c.Impact * c.ImpactRef / math.max(d, c.ImpactRef)
	at("Impact" .. set, hit, gain, t)
	if HARD[set] and math.random() < c.RicochetChance then
		at("Ricochet", hit, gain * c.Ricochet, t + 0.01)
	end
end

-- A shot the server confirmed (Shot remote): everyone's, yours included (yours plays no bang
-- here, that already played in ownShot).
function GunAudio.shot(def, shooter: Player, origin: Vector3, hits: { Vector3 }, kinds: { string }?)
	local c = cfg()
	if not c.Enabled then
		return
	end
	local ear = listener()
	local mine = shooter == player
	if not mine then
		report(def, origin, ear)
	end
	for i, pos in hits do
		bullet(origin, pos, if kinds then kinds[i] or "" else "Concrete", ear, mine)
	end
end

-- load every gun sound up front so the first shot isn't silent
task.spawn(function()
	local list = {}
	for base in variants do
		if
			string.find(base, "^Carbine")
			or string.find(base, "^Bullet")
			or string.find(base, "^Impact")
			or base == "Ricochet"
		then
			for k = 1, variants[base] do
				local s = Instance.new("Sound")
				s.SoundId = "rbxassetid://" .. SoundIds[base .. k]
				table.insert(list, s)
			end
		end
	end
	pcall(function()
		ContentProvider:PreloadAsync(list)
	end)
end)

return GunAudio
