--[[
	Lightning on the client. The server (Server/Lightning) picks every strike and fires
	ReplicatedStorage.LightningStrike(pos, normal, kind, seed) to everyone; this draws it:

	  * the bolt: a jagged glowing line with side branches (Beams), flickering 2-4 times, the
	    same shape for every player (built from the seed),
	  * the flash: the whole screen brightens (stronger at night, softer under a roof) and a
	    light at the strike lights up the buildings round it,
	  * the impact (ground strikes within Config.Lightning.ImpactRange): sparks, a white flare,
	    a shock ring, smoke, a few embers and a scorch mark that fades after half a minute,
	  * thunder after the flash, later the further away (Config.Lightning.SoundSpeed): a sharp
	    crack close by, a low rolling rumble far away, muffled under a roof,
	  * camera shake when it hits near you (Config.Lightning.ShakeRange), harder the closer.

	"cloud" strikes stay inside the clouds: a soft flash and a far rumble, no bolt.
	The shake is put on after the camera scripts and taken off again at the start of the next
	frame (same pattern as Movement/FirstPersonCamera), so mouse look and aiming never drift.
]]
local Debris = game:GetService("Debris")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")
local TweenService = game:GetService("TweenService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))

local L = Config.Lightning
if not L or not L.Enabled then
	return
end

-- how dark it is (0 day .. 1 night) from the weather's sky, if it's running
local Sky = nil
do
	local weather = script.Parent:FindFirstChild("Weather")
	local mod = weather and weather:FindFirstChild("Sky")
	if mod then
		local ok, m = pcall(require, mod)
		Sky = if ok then m else nil
	end
end
local function night(): number
	if Sky and Sky.night then
		return Sky.night()
	end
	local h = Lighting.ClockTime
	return if h < 6 or h > 19.5 then 1 else 0
end

local BOLT_CORE = Color3.fromRGB(245, 248, 255)
local BOLT_GLOW = Color3.fromRGB(150, 170, 255)
local LIGHT_COLOR = Color3.fromRGB(200, 212, 255)
local TINT = Color3.fromRGB(222, 230, 255)

local SPARK_TEX = "rbxasset://textures/particles/sparkles_main.dds"
local SMOKE_TEX = "rbxasset://textures/particles/smoke_main.dds"
local FIRE_TEX = "rbxasset://textures/particles/fire_main.dds"

-- pieces ----------------------------------------------------------------------
local function invisiblePart(name: string, cf: CFrame): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Transparency = 1
	p.Size = Vector3.one
	p.CFrame = cf
	return p
end

local function rayParams(): RaycastParams
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
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = ignore
	return params
end

local function underRoof(pos: Vector3): boolean
	return workspace:Raycast(pos, Vector3.new(0, 150, 0), rayParams()) ~= nil
end

-- flash timeline: a few flickers over ~0.7 s, the same for everyone (from the seed) ----
local function flickers(rng: Random): { { number } }
	local keys = { { 0, 0 }, { 0.02, 1 }, { 0.07, 0.35 } }
	local t = 0.07
	for _ = 1, rng:NextInteger(1, 3) do
		t += rng:NextNumber(0.04, 0.12)
		table.insert(keys, { t, 0.15 })
		t += 0.02
		table.insert(keys, { t, rng:NextNumber(0.55, 0.95) })
		t += rng:NextNumber(0.04, 0.08)
		table.insert(keys, { t, 0.3 })
	end
	table.insert(keys, { t + 0.25, 0 })
	return keys
end

local function level(keys: { { number } }, t: number): number
	for i = 2, #keys do
		local a, b = keys[i - 1], keys[i]
		if t <= b[1] then
			local f = (t - a[1]) / math.max(b[1] - a[1], 1e-4)
			return a[2] + (b[2] - a[2]) * f
		end
	end
	return 0
end

-- bolt shape ------------------------------------------------------------------
local function jag(a: Vector3, b: Vector3, depth: number, rough: number, rng: Random): { Vector3 }
	local pts = { a, b }
	for _ = 1, depth do
		local nxt = { pts[1] }
		for i = 2, #pts do
			local p, q = pts[i - 1], pts[i]
			local seg = q - p
			local len = seg.Magnitude
			local dir = seg / math.max(len, 1e-3)
			local r = Vector3.new(rng:NextNumber(-1, 1), rng:NextNumber(-1, 1), rng:NextNumber(-1, 1))
			r -= dir * r:Dot(dir) -- sideways only
			table.insert(nxt, (p + q) / 2 + r * len * rough)
			table.insert(nxt, q)
		end
		pts = nxt
	end
	return pts
end

-- strands: { points, width } ; branches peel off the main channel and fade out in the air
local function boltShape(pos: Vector3, rng: Random): { { any } }
	local top = pos + Vector3.new(rng:NextNumber(-180, 180), rng:NextNumber(650, 850), rng:NextNumber(-180, 180))
	local main = jag(top, pos, 6, 0.24, rng)
	local strands = { { main, 1 } }
	for _ = 1, rng:NextInteger(3, 6) do
		local i = rng:NextInteger(4, math.floor(#main * 0.7))
		local from = main[i]
		local down = (main[math.min(i + 6, #main)] - from).Unit
		local side = Vector3.new(rng:NextNumber(-1, 1), 0, rng:NextNumber(-1, 1)).Unit
		local len = rng:NextNumber(70, 240)
		local to = from + (down * 0.6 + side * 0.8).Unit * len
		table.insert(strands, { jag(from, to, 4, 0.3, rng), 0.45 })
	end
	return strands
end

-- draws the bolt; returns a function(level) that sets how bright it is
local function drawBolt(holder: Part, strands: { { any } }, scale: number): (number) -> ()
	local beams: { { any } } = {}
	for _, strand in strands do
		local pts, width = strand[1], strand[2]
		local atts = table.create(#pts)
		for i, p in pts do
			local a = Instance.new("Attachment")
			a.Parent = holder
			a.WorldPosition = p
			atts[i] = a
		end
		for i = 2, #atts do
			-- branches thin out towards their tips
			local taper = if width < 1 then 1 - (i / #atts) * 0.8 else 1
			for layer = 1, 2 do
				local b = Instance.new("Beam")
				b.Attachment0, b.Attachment1 = atts[i - 1], atts[i]
				b.FaceCamera = true
				b.Segments = 1
				b.LightEmission = 1
				b.LightInfluence = 0
				local w = if layer == 1 then 0.7 * width * taper * scale else 5 * width * taper * scale
				b.Width0, b.Width1 = w, w
				b.Color = ColorSequence.new(if layer == 1 then BOLT_CORE else BOLT_GLOW)
				b.Transparency = NumberSequence.new(1)
				pcall(function()
					(b :: any).Brightness = if layer == 1 then 6 else 2
				end)
				b.Parent = holder
				table.insert(beams, { b, layer, width })
			end
		end
	end
	return function(lv: number)
		for _, e in beams do
			local b, layer, width = e[1], e[2], e[3]
			local t = if layer == 1 then 1 - lv else 1 - lv * (if width < 1 then 0.25 else 0.45)
			if width < 1 then
				t = 1 - (1 - t) * math.clamp(lv * 1.4 - 0.2, 0, 1) -- branches drop out first
			end
			b.Transparency = NumberSequence.new(math.clamp(t, 0, 1))
		end
	end
end

-- impact on the ground ----------------------------------------------------------
local function emitter(parent: Instance, props: { [string]: any }): ParticleEmitter
	local e = Instance.new("ParticleEmitter")
	e.Rate = 0
	e.EmissionDirection = Enum.NormalId.Top
	for k, v in props do
		(e :: any)[k] = v
	end
	e.Parent = parent
	return e
end

local function flatCylinder(name: string, cf: CFrame, color: Color3, material: Enum.Material): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Shape = Enum.PartType.Cylinder
	p.Anchored = true
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Material = material
	p.Color = color
	p.CFrame = cf
	return p
end

local function impact(pos: Vector3, normal: Vector3)
	normal = if normal.Magnitude > 0.5 then normal.Unit else Vector3.yAxis
	local ref = if math.abs(normal.Y) < 0.9 then Vector3.yAxis else Vector3.xAxis
	local right = normal:Cross(ref).Unit
	-- a frame with Up = surface normal (emitters fire "Top" = away from the surface)
	local upCF = CFrame.fromMatrix(pos, right, normal)
	-- cylinders lie along their X axis, so this one has X = normal (a flat disc on the surface)
	local discCF = CFrame.fromMatrix(pos, normal, right)

	local holder = invisiblePart("LightningImpact", upCF + normal * 0.3)
	holder.Parent = workspace
	Debris:AddItem(holder, 6)

	emitter(holder, {
		Texture = SPARK_TEX,
		Color = ColorSequence.new(Color3.fromRGB(255, 246, 215), Color3.fromRGB(255, 160, 70)),
		LightEmission = 1,
		Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.7), NumberSequenceKeypoint.new(1, 0) }),
		Lifetime = NumberRange.new(0.3, 1),
		Speed = NumberRange.new(25, 60),
		SpreadAngle = Vector2.new(80, 80),
		Acceleration = Vector3.new(0, -90, 0),
		Drag = 1.5,
	}):Emit(80)

	emitter(holder, {
		Texture = SMOKE_TEX,
		Color = ColorSequence.new(Color3.fromRGB(70, 68, 66), Color3.fromRGB(120, 118, 115)),
		Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 3), NumberSequenceKeypoint.new(1, 15) }),
		Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 0.35),
			NumberSequenceKeypoint.new(1, 1),
		}),
		Lifetime = NumberRange.new(2, 4),
		Speed = NumberRange.new(4, 11),
		SpreadAngle = Vector2.new(70, 70),
		Acceleration = Vector3.new(0, 3, 0),
		Drag = 1,
		Rotation = NumberRange.new(0, 360),
		RotSpeed = NumberRange.new(-40, 40),
		LightInfluence = 0.6,
	}):Emit(18)

	local embers = emitter(holder, {
		Texture = FIRE_TEX,
		Color = ColorSequence.new(Color3.fromRGB(255, 190, 90), Color3.fromRGB(255, 90, 30)),
		LightEmission = 1,
		Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1.6), NumberSequenceKeypoint.new(1, 0) }),
		Lifetime = NumberRange.new(0.35, 0.8),
		Speed = NumberRange.new(2, 5),
		SpreadAngle = Vector2.new(25, 25),
		Rate = 30,
	})
	task.delay(1.4, function()
		embers.Rate = 0
	end)

	-- white-hot flare at the point it hit
	local flare = Instance.new("Part")
	flare.Shape = Enum.PartType.Ball
	flare.Anchored, flare.CanCollide, flare.CanQuery, flare.CanTouch = true, false, false, false
	flare.CastShadow = false
	flare.Material = Enum.Material.Neon
	flare.Color = BOLT_CORE
	flare.Size = Vector3.one * 3
	flare.CFrame = CFrame.new(pos + normal)
	flare.Parent = workspace
	TweenService:Create(flare, TweenInfo.new(0.3, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
		Size = Vector3.one * 12,
		Transparency = 1,
	}):Play()
	Debris:AddItem(flare, 0.4)

	-- shock ring spreading over the ground
	local ring = flatCylinder("LightningRing", discCF + normal * 0.15, BOLT_GLOW, Enum.Material.Neon)
	ring.Size = Vector3.new(0.15, 2, 2)
	ring.Transparency = 0.2
	ring.Parent = workspace
	TweenService:Create(ring, TweenInfo.new(0.45, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
		Size = Vector3.new(0.15, 40, 40),
		Transparency = 1,
	}):Play()
	Debris:AddItem(ring, 0.5)

	-- scorch mark, fades away after a while
	local scorch =
		flatCylinder("LightningScorch", discCF + normal * 0.04, Color3.fromRGB(24, 21, 19), Enum.Material.SmoothPlastic)
	scorch.Size = Vector3.new(0.05, 8, 8)
	scorch.Transparency = 0.2
	scorch.Parent = workspace
	task.delay(25, function()
		if scorch.Parent then
			TweenService:Create(scorch, TweenInfo.new(10), { Transparency = 1 }):Play()
		end
	end)
	Debris:AddItem(scorch, 36)
end

-- thunder -----------------------------------------------------------------------
local group = Instance.new("SoundGroup")
group.Name = "Thunder"
group.Volume = 1
group.Parent = SoundService
local muffle = Instance.new("EqualizerSoundEffect")
muffle.HighGain, muffle.MidGain, muffle.LowGain = 0, 0, 0
muffle.Parent = group

local CLOSE = { SoundIds.ThunderClose1, SoundIds.ThunderClose2 }
local FAR = { SoundIds.ThunderFar1, SoundIds.ThunderFar2, SoundIds.ThunderFar3 }

local function thunder(dist: number, kind: string, rng: Random)
	local close = kind == "ground" and dist < L.CloseRange
	local list = if close then CLOSE else FAR
	local id = list[rng:NextInteger(1, #list)]
	if not id then
		return
	end
	local vol, speed
	if close then
		vol = 1.6 * (1 - 0.45 * dist / L.CloseRange)
		speed = rng:NextNumber(0.95, 1.05)
	else
		local f = math.clamp((dist - L.CloseRange) / 2500, 0, 1)
		vol = 1.1 + (0.35 - 1.1) * f
		speed = 1 - 0.15 * f + rng:NextNumber(-0.05, 0.05)
		if kind == "cloud" then
			vol *= 0.8
		end
	end
	task.delay(dist / L.SoundSpeed, function()
		local cam = workspace.CurrentCamera
		local indoor = cam and underRoof(cam.CFrame.Position)
		muffle.HighGain = if indoor then -20 else 0
		muffle.MidGain = if indoor then -6 else 0
		local s = Instance.new("Sound")
		s.Name = "Thunder"
		s.SoundId = `rbxassetid://{id}`
		s.Volume = vol * (L.ThunderVolume or 1) * (if indoor then 0.7 else 1)
		s.PlaybackSpeed = speed
		s.SoundGroup = group
		s.Parent = SoundService
		s:Play()
		Debris:AddItem(s, 16)
	end)
end

-- camera shake --------------------------------------------------------------------
local shakes: { { number } } = {} -- { start, duration, strength }
local shakeApplied = false
local shakenCF, unshakenCF = CFrame.identity, CFrame.identity

local function addShake(strength: number, duration: number)
	table.insert(shakes, { os.clock(), duration, strength })
end

RunService:BindToRenderStep("LightningShakeUndo", Enum.RenderPriority.First.Value, function()
	local cam = workspace.CurrentCamera
	-- only if nobody else (first-person camera undo) has already put the camera back
	if shakeApplied and cam and cam.CFrame == shakenCF then
		cam.CFrame = unshakenCF
	end
	shakeApplied = false
end)

RunService:BindToRenderStep("LightningShake", Enum.RenderPriority.Last.Value + 1, function()
	if #shakes == 0 then
		return
	end
	local now = os.clock()
	local amount = 0
	for i = #shakes, 1, -1 do
		local s = shakes[i]
		local age = (now - s[1]) / s[2]
		if age >= 1 then
			table.remove(shakes, i)
		else
			amount += s[3] * (1 - age) ^ 2
		end
	end
	local cam = workspace.CurrentCamera
	if amount < 0.002 or not cam then
		return
	end
	amount = math.min(amount, 1.5)
	local deg = math.rad(L.ShakeDegrees) * amount
	local t = now * 22
	local rot = CFrame.Angles(math.noise(t, 0.3) * deg * 2, math.noise(t, 4.1) * deg * 2, math.noise(t, 7.7) * deg)
	local move = Vector3.new(math.noise(t, 11.3), math.noise(t, 13.9), 0) * 0.5 * amount
	unshakenCF = cam.CFrame
	shakenCF = unshakenCF * CFrame.new(move) * rot
	cam.CFrame = shakenCF
	shakeApplied = true
end)

-- screen flash ------------------------------------------------------------------------
local flash = Instance.new("ColorCorrectionEffect")
flash.Name = "LightningFlash"
flash.Brightness = 0
flash.Parent = Lighting

local active: { { any } } = {} -- { start, keys, strength, setBolt?, light? }

RunService.RenderStepped:Connect(function()
	if #active == 0 then
		return
	end
	local now = os.clock()
	local total = 0
	for i = #active, 1, -1 do
		local a = active[i]
		local keys = a[2]
		local t = now - a[1]
		local lv = level(keys, t)
		if t > keys[#keys][1] then
			if a[4] then
				a[4](0)
			end
			if a[5] then
				a[5].Brightness = 0
			end
			table.remove(active, i)
		else
			total += lv * a[3]
			if a[4] then
				a[4](lv)
			end
			if a[5] then
				a[5].Brightness = 14 * lv
			end
		end
	end
	total = math.min(total, 0.75)
	flash.Brightness = total
	flash.Contrast = -0.15 * total
	flash.TintColor = Color3.new(1, 1, 1):Lerp(TINT, math.min(total * 2, 1))
end)

-- one strike ------------------------------------------------------------------------------
local function onStrike(pos: Vector3, normal: Vector3, kind: string, seed: number)
	local cam = workspace.CurrentCamera
	if not cam or typeof(pos) ~= "Vector3" then
		return
	end
	local rng = Random.new(seed)
	local camPos = cam.CFrame.Position
	local dist = (pos - camPos).Magnitude
	local keys = flickers(rng)
	local indoor = underRoof(camPos)

	-- how much the screen lights up
	local strength
	if kind == "ground" then
		strength = 0.55 + (0.12 - 0.55) * math.clamp(dist / 2500, 0, 1)
	else
		strength = 0.12
	end
	strength *= (L.FlashStrength or 1) * (0.6 + 0.6 * night()) * (if indoor then 0.45 else 1)

	local setBolt, light = nil, nil
	if kind == "ground" then
		local holder = invisiblePart("LightningBolt", CFrame.new(pos))
		holder.Parent = workspace
		setBolt = drawBolt(holder, boltShape(pos, rng), math.max(1, dist / 250))
		local glow = invisiblePart(
			"LightningGlow",
			CFrame.new(pos + (if typeof(normal) == "Vector3" then normal else Vector3.yAxis) * 8)
		)
		glow.Parent = holder
		local p = Instance.new("PointLight")
		p.Range = 60
		p.Color = LIGHT_COLOR
		p.Shadows = true
		p.Brightness = 0
		p.Parent = glow
		light = p
		Debris:AddItem(holder, keys[#keys][1] + 0.2)

		if dist < L.ImpactRange then
			impact(pos, if typeof(normal) == "Vector3" then normal else Vector3.yAxis)
		end
		if dist < L.ShakeRange then
			addShake((1 - dist / L.ShakeRange) ^ 1.4, 0.9)
		end
	end
	table.insert(active, { os.clock(), keys, strength, setBolt, light })
	thunder(dist, kind, rng)
end

local remote = ReplicatedStorage:WaitForChild("LightningStrike") :: RemoteEvent
remote.OnClientEvent:Connect(onStrike)
