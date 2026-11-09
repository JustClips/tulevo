-- Shot effects (client only): muzzle flash, muzzle smoke, bullet tracers.
--
-- All the art is rendered in Blender (art/blender/weapons/render_muzzle_fx.py ->
-- tools/weapon_fx_sprites.py -> TextureIds.WeaponFx); numbers are in Config.Weapons.Fx.
--
-- Flash: one frame or two of burning gas, like GTA. A camera-facing Beam along the barrel shows
-- the side view (MuzzleSide1-4, a random one per shot); a star sprite (MuzzleFront1-2) fades
-- in as you look down the barrel, where the side view would be edge-on. A short warm light and
-- a thin puff of smoke that drifts off.
--
-- Tracer: a thin bright streak (Tracer.png, white-hot head fading to the tail) that flies from
-- the muzzle to the hit at bullet-ish speed and is gone, like GTA's. Its width follows the
-- camera distance so it stays a fine line a few pixels wide near and far.
--
-- Impact: where a bullet hits the world (the server's hit point + material, from the Shot
-- remote) there's a bullet hole decal for the material (tools/bullet_hole_sprites.py), a puff
-- of dust in the wall's colour, a few flying chips and, on metal, sparks with a quick flash.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local FX = Config.Weapons.Fx
local tex = TextureIds.WeaponFx or {}

local function asset(name: string): string?
	local id = tex[name]
	return if id then `rbxassetid://{id}` else nil
end

local function list(prefix: string, n: number): { string }
	local out = {}
	for i = 1, n do
		local a = asset(`{prefix}{i}`)
		if a then
			table.insert(out, a)
		end
	end
	return out
end

local SIDE = list("MuzzleSide", 4)
local FRONT = list("MuzzleFront", 2)
local SMOKE = list("MuzzleSmoke", 2)
local TRACER = asset("Tracer")

-- where the muzzle sits in the side render: x -0.12..1.48, height 1.2 (render units)
local SIDE_BACK, SIDE_FRONT, SIDE_HEIGHT = 0.12, 1.48, 1.2

local Effects = {}

-- ------------------------------------------------------------------ muzzle flash

type Rig = {
	a0: Attachment,
	a1: Attachment,
	side: Beam?,
	front: ParticleEmitter?,
	smoke: ParticleEmitter?,
	light: PointLight,
	token: number,
}
local rigs: { [Attachment]: Rig } = setmetatable({}, { __mode = "k" }) :: any

local function rigFor(muzzle: Attachment): Rig
	local rig = rigs[muzzle]
	if rig and rig.a0.Parent then
		return rig
	end
	local holder = muzzle.Parent
	local a0 = Instance.new("Attachment")
	a0.Name = "FlashBack"
	a0.Parent = holder
	local a1 = Instance.new("Attachment")
	a1.Name = "FlashFront"
	a1.Parent = holder

	local side: Beam? = nil
	if #SIDE > 0 then
		local b = Instance.new("Beam")
		b.Name = "MuzzleFlash"
		b.Attachment0 = a0
		b.Attachment1 = a1
		b.FaceCamera = true
		b.Segments = 1
		b.LightEmission = 1
		b.LightInfluence = 0
		b.Brightness = FX.FlashBrightness
		b.TextureMode = Enum.TextureMode.Stretch
		b.TextureLength = 1
		b.TextureSpeed = 0
		b.Enabled = false
		b.Parent = holder
		side = b
	end

	local front: ParticleEmitter? = nil
	if #FRONT > 0 then
		local e = Instance.new("ParticleEmitter")
		e.Name = "MuzzleStar"
		e.Rate = 0
		e.Speed = NumberRange.new(0)
		e.LockedToPart = true
		e.Orientation = Enum.ParticleOrientation.FacingCamera
		e.LightEmission = 1
		e.LightInfluence = 0
		e.Brightness = FX.FlashBrightness
		e.Lifetime = NumberRange.new(FX.FlashTime)
		e.Rotation = NumberRange.new(0, 360)
		e.ZOffset = 0.2
		e.Parent = muzzle
		front = e
	end

	local smoke: ParticleEmitter? = nil
	if #SMOKE > 0 then
		local e = Instance.new("ParticleEmitter")
		e.Name = "MuzzleSmoke"
		e.Rate = 0
		e.EmissionDirection = Enum.NormalId.Front -- the muzzle's -Z
		e.SpreadAngle = Vector2.new(12, 12)
		e.Speed = NumberRange.new(2.5, 5)
		e.Drag = 4
		e.Acceleration = Vector3.new(0, 1.2, 0)
		e.Lifetime = NumberRange.new(0.5, 0.9)
		e.Size = NumberSequence.new({
			NumberSequenceKeypoint.new(0, FX.SmokeSize * 0.25),
			NumberSequenceKeypoint.new(1, FX.SmokeSize),
		})
		e.Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1),
			NumberSequenceKeypoint.new(0.08, 1 - FX.SmokeOpacity),
			NumberSequenceKeypoint.new(1, 1),
		})
		e.Rotation = NumberRange.new(0, 360)
		e.RotSpeed = NumberRange.new(-40, 40)
		e.LightInfluence = 1
		e.Parent = muzzle
		smoke = e
	end

	local light = Instance.new("PointLight")
	light.Name = "MuzzleLight"
	light.Color = Color3.fromRGB(255, 190, 110)
	light.Range = FX.LightRange
	light.Brightness = FX.LightBrightness
	light.Shadows = false
	light.Enabled = false
	light.Parent = muzzle

	rig = { a0 = a0, a1 = a1, side = side, front = front, smoke = smoke, light = light, token = 0 }
	rigs[muzzle] = rig
	return rig
end

function Effects.flash(muzzle: Attachment)
	local rig = rigFor(muzzle)
	local size = FX.FlashSize * (0.85 + math.random() * 0.3)
	-- place the beam ends along the barrel (in the holder part's space, so they ride the gun)
	rig.a0.CFrame = muzzle.CFrame * CFrame.new(0, 0, SIDE_BACK * size)
	rig.a1.CFrame = muzzle.CFrame * CFrame.new(0, 0, -SIDE_FRONT * size)

	-- how much we look down the barrel: 0 side on, 1 straight down it (toward us or away)
	local cam = workspace.CurrentCamera
	local look = muzzle.WorldCFrame.LookVector
	local facing = 0
	if cam then
		local toCam = (cam.CFrame.Position - muzzle.WorldPosition).Unit
		facing = math.clamp((math.abs(look:Dot(toCam)) - 0.55) / 0.4, 0, 1)
	end

	if rig.side then
		rig.side.Texture = SIDE[math.random(#SIDE)]
		rig.side.Width0 = SIDE_HEIGHT * size
		rig.side.Width1 = SIDE_HEIGHT * size
		rig.side.Transparency = NumberSequence.new(0.85 * facing)
		rig.side.Enabled = true
	end
	if rig.front and facing > 0 then
		rig.front.Texture = FRONT[math.random(#FRONT)]
		rig.front.Size = NumberSequence.new(FX.StarSize * (0.85 + math.random() * 0.3))
		rig.front.Transparency = NumberSequence.new(1 - facing)
		rig.front:Emit(1)
	end
	if rig.smoke then
		rig.smoke.Texture = SMOKE[math.random(#SMOKE)]
		rig.smoke:Emit(1)
	end
	rig.light.Enabled = true

	rig.token += 1
	local token = rig.token
	task.delay(FX.FlashTime, function()
		if rig.token == token then
			if rig.side then
				rig.side.Enabled = false
			end
			rig.light.Enabled = false
		end
	end)
end

-- ------------------------------------------------------------------ tracers

type Tracer = { a0: Attachment, a1: Attachment, beam: Beam, from: Vector3, dir: Vector3, length: number, t: number }
local pool: { Tracer } = {}
local live: { Tracer } = {}
local stepConn: RBXScriptConnection? = nil

local function newTracer(): Tracer
	local terrain = workspace.Terrain
	local a0 = Instance.new("Attachment")
	a0.Name = "TracerTail"
	a0.Parent = terrain
	local a1 = Instance.new("Attachment")
	a1.Name = "TracerHead"
	a1.Parent = terrain
	local b = Instance.new("Beam")
	b.Name = "Tracer"
	b.Attachment0 = a0 -- tail (texture's faded left end)
	b.Attachment1 = a1 -- head (white-hot right end)
	if TRACER then
		b.Texture = TRACER
		b.Color = ColorSequence.new(Color3.new(1, 1, 1))
		b.Transparency = NumberSequence.new(0)
	else
		-- no sprite uploaded yet: a plain warm line, faded toward the tail
		b.Color = ColorSequence.new(Color3.fromRGB(255, 225, 170))
		b.Transparency = NumberSequence.new(0.9, 0.15)
	end
	b.TextureMode = Enum.TextureMode.Stretch
	b.TextureLength = 1
	b.FaceCamera = true
	b.Segments = 1
	b.LightEmission = 1
	b.LightInfluence = 0
	b.Brightness = FX.TracerBrightness
	b.Enabled = false
	b.Parent = terrain
	return { a0 = a0, a1 = a1, beam = b, from = Vector3.zero, dir = Vector3.zAxis, length = 0, t = 0 }
end

-- world width that shows as `px` pixels at this point
local function pixelWidth(cam: Camera, p: Vector3, px: number): number
	local d = (p - cam.CFrame.Position).Magnitude
	return 2 * d * math.tan(math.rad(cam.FieldOfView) / 2) / math.max(cam.ViewportSize.Y, 1) * px
end

local function step(dt: number)
	local cam = workspace.CurrentCamera
	for i = #live, 1, -1 do
		local tr = live[i]
		tr.t += dt
		local head = FX.TracerStart + FX.TracerSpeed * tr.t
		local tail = head - FX.TracerLength
		if tail >= tr.length then
			tr.beam.Enabled = false
			table.remove(live, i)
			table.insert(pool, tr)
		else
			head = math.min(head, tr.length)
			tail = math.clamp(tail, FX.TracerStart, head)
			local hp = tr.from + tr.dir * head
			local tp = tr.from + tr.dir * tail
			tr.a1.WorldPosition = hp
			tr.a0.WorldPosition = tp
			if cam then
				tr.beam.Width1 = math.max(FX.TracerMinWidth, pixelWidth(cam, hp, FX.TracerPixels))
				tr.beam.Width0 = math.max(FX.TracerMinWidth, pixelWidth(cam, tp, FX.TracerPixels))
			end
			tr.beam.Enabled = head - tail > 0.05
		end
	end
	if #live == 0 and stepConn then
		stepConn:Disconnect()
		stepConn = nil
	end
end

function Effects.tracer(from: Vector3, to: Vector3)
	if math.random() > FX.TracerChance then
		return
	end
	local length = (to - from).Magnitude
	if length < FX.TracerStart + 1 then
		return
	end
	local tr = table.remove(pool) or newTracer()
	tr.from = from
	tr.dir = (to - from) / length
	tr.length = length
	tr.t = 0
	-- first frame: draw it already a frame along, so even a close hit shows a streak
	table.insert(live, tr)
	step(1 / 60)
	if not stepConn then
		stepConn = RunService.RenderStepped:Connect(step)
	end
end

-- ------------------------------------------------------------------ impacts

-- Enum.Material name -> impact look (same groups as GunAudio's sounds). Anything else = concrete.
local SURFACE = {
	Metal = "Metal",
	DiamondPlate = "Metal",
	CorrodedMetal = "Metal",
	Foil = "Metal",
	Wood = "Wood",
	WoodPlanks = "Wood",
	Cardboard = "Wood",
	Glass = "Glass",
	Ice = "Glass",
	Grass = "Dirt",
	LeafyGrass = "Dirt",
	Ground = "Dirt",
	Mud = "Dirt",
	Sand = "Dirt",
	Snow = "Dirt",
	Salt = "Dirt",
	Pebble = "Dirt",
	Fabric = "Soft",
	Carpet = "Soft",
	Rubber = "Soft",
	Water = "Water",
}

local HOLES = {
	Concrete = list("BulletHoleConcrete", 3),
	Metal = list("BulletHoleMetal", 2),
	Wood = list("BulletHoleWood", 1),
	Glass = list("BulletHoleGlass", 2),
}
-- grass, ground, fabric...: the stone hole, tinted dark by the surface (placeHole's tint)
HOLES.Dirt = HOLES.Concrete
HOLES.Soft = HOLES.Concrete
local DEBRIS = asset("ImpactDebris")

-- dust / chip colour when the surface's own colour isn't known
local DUST = {
	Concrete = Color3.fromRGB(170, 165, 155),
	Metal = Color3.fromRGB(120, 118, 115),
	Wood = Color3.fromRGB(170, 140, 100),
	Glass = Color3.fromRGB(220, 230, 235),
	Dirt = Color3.fromRGB(120, 100, 75),
	Soft = Color3.fromRGB(140, 135, 130),
	Water = Color3.fromRGB(200, 215, 225),
}

local holeFolder: Folder? = nil
local function holes(): Folder
	if not holeFolder or not holeFolder.Parent then
		local f = Instance.new("Folder")
		f.Name = "BulletHoles" -- client only, never on the server
		f.Parent = workspace
		holeFolder = f
	end
	return holeFolder :: Folder
end

type Hole = { part: Part, decal: Decal, token: number }
local holePool: { Hole } = {}
local nextHole = 1

local function newHole(): Hole
	local p = Instance.new("Part")
	p.Name = "BulletHole"
	p.Transparency = 1
	p.CanCollide = false
	p.CanQuery = false
	p.CanTouch = false
	p.CastShadow = false
	p.Massless = true
	p.Anchored = true
	local d = Instance.new("Decal")
	d.Face = Enum.NormalId.Front
	d.Parent = p
	return { part = p, decal = d, token = 0 }
end

-- the oldest hole slot (or a new one while under MaxHoles)
local function takeHole(): Hole
	local h = holePool[nextHole]
	if not h or h.part.Parent == nil then -- (a hole on a car that got deleted goes with it)
		h = newHole()
		holePool[nextHole] = h
	end
	nextHole = nextHole % FX.MaxHoles + 1
	h.token += 1
	local weld = h.part:FindFirstChildOfClass("WeldConstraint")
	if weld then
		weld:Destroy()
	end
	h.part.Anchored = true
	return h
end

-- doors and gates move on their own (Client/CityDoors), a hole would hang in the air
local function isDoor(inst: Instance): boolean
	for _, n in { inst.Name, inst.Parent and inst.Parent.Name or "" } do
		if string.match(n, "^Swing%d") or string.match(n, "^Slide%d") or string.match(n, "^Lift%d") then
			return true
		end
	end
	return false
end

local function placeHole(set: string, pos: Vector3, normal: Vector3, inst: BasePart, tint: Color3)
	local textures = HOLES[set]
	if not textures or #textures == 0 or isDoor(inst) then
		return
	end
	local h = takeHole()
	local size = (FX.HoleSize[set] or 0.4) * (0.85 + math.random() * 0.3)
	h.part.Size = Vector3.new(size, size, 0.02)
	local up = if math.abs(normal.Y) > 0.98 then Vector3.xAxis else Vector3.yAxis
	-- a hair off the wall, a little different each time so overlapping holes don't flicker
	local at = pos + normal * (0.02 + math.random() * 0.015)
	h.part.CFrame = CFrame.lookAt(at, at + normal, up) * CFrame.Angles(0, 0, math.random() * 2 * math.pi)
	h.decal.Texture = textures[math.random(#textures)]
	h.decal.Color3 = tint
	h.decal.Transparency = 0
	if not inst.Anchored then
		-- cars and loose props: the hole rides along
		h.part.Anchored = false
		local w = Instance.new("WeldConstraint")
		w.Part0 = h.part
		w.Part1 = inst
		w.Parent = h.part
	end
	h.part.Parent = holes()

	local token = h.token
	task.delay(FX.HoleLife, function()
		if h.token == token then
			TweenService:Create(h.decal, TweenInfo.new(FX.HoleFade), { Transparency = 1 }):Play()
		end
	end)
end

-- Particle rigs: changing an emitter's colour recolours its live particles too, so each hit
-- takes the next of a few rigs (round robin) instead of sharing one.
type ImpactRig = {
	at: Attachment,
	dust: ParticleEmitter?,
	chips: ParticleEmitter?,
	sparks: ParticleEmitter?,
	light: PointLight,
	token: number,
}
local impactRigs: { ImpactRig } = {}
local nextRig = 1
local RIGS = 16

local function newImpactRig(): ImpactRig
	local at = Instance.new("Attachment")
	at.Name = "BulletImpact"
	at.Parent = workspace.Terrain

	local dust: ParticleEmitter? = nil
	if #SMOKE > 0 then
		local e = Instance.new("ParticleEmitter")
		e.Name = "Dust"
		e.Rate = 0
		e.EmissionDirection = Enum.NormalId.Top -- the attachment's up = the wall's normal
		e.SpreadAngle = Vector2.new(30, 30)
		e.Speed = NumberRange.new(4, 9)
		e.Drag = 5
		e.Acceleration = Vector3.new(0, -1.5, 0)
		e.Lifetime = NumberRange.new(0.8, 1.5)
		e.Size = NumberSequence.new({
			NumberSequenceKeypoint.new(0, FX.DustSize * 0.2),
			NumberSequenceKeypoint.new(1, FX.DustSize),
		})
		e.Transparency = NumberSequence.new({
			NumberSequenceKeypoint.new(0, 1),
			NumberSequenceKeypoint.new(0.05, 1 - FX.DustOpacity),
			NumberSequenceKeypoint.new(1, 1),
		})
		e.Rotation = NumberRange.new(0, 360)
		e.RotSpeed = NumberRange.new(-60, 60)
		e.LightInfluence = 1
		e.Parent = at
		dust = e
	end

	local chips: ParticleEmitter? = nil
	local sparks: ParticleEmitter? = nil
	if DEBRIS then
		local e = Instance.new("ParticleEmitter")
		e.Name = "Chips"
		e.Texture = DEBRIS
		e.Rate = 0
		e.EmissionDirection = Enum.NormalId.Top
		e.SpreadAngle = Vector2.new(45, 45)
		e.Speed = NumberRange.new(9, 20)
		e.Drag = 1.5
		e.Acceleration = Vector3.new(0, -70, 0)
		e.Lifetime = NumberRange.new(0.35, 0.8)
		e.Size = NumberSequence.new(0.07, 0.05)
		e.Rotation = NumberRange.new(0, 360)
		e.RotSpeed = NumberRange.new(-720, 720)
		e.LightInfluence = 1
		e.Parent = at
		chips = e

		local s = Instance.new("ParticleEmitter")
		s.Name = "Sparks"
		s.Texture = DEBRIS
		s.Rate = 0
		s.EmissionDirection = Enum.NormalId.Top
		s.SpreadAngle = Vector2.new(60, 60)
		s.Speed = NumberRange.new(18, 40)
		s.Drag = 3
		s.Acceleration = Vector3.new(0, -60, 0)
		s.Lifetime = NumberRange.new(0.1, 0.3)
		s.Size = NumberSequence.new(0.06, 0.02)
		s.Color = ColorSequence.new(Color3.fromRGB(255, 230, 170), Color3.fromRGB(255, 140, 50))
		s.LightEmission = 1
		s.LightInfluence = 0
		s.Brightness = 4
		s.Parent = at
		sparks = s
	end

	local light = Instance.new("PointLight")
	light.Color = Color3.fromRGB(255, 190, 110)
	light.Range = 5
	light.Brightness = 3
	light.Shadows = false
	light.Enabled = false
	light.Parent = at

	return { at = at, dust = dust, chips = chips, sparks = sparks, light = light, token = 0 }
end

local function takeRig(): ImpactRig
	local r = impactRigs[nextRig]
	if not r or not r.at.Parent then
		r = newImpactRig()
		impactRigs[nextRig] = r
	end
	nextRig = nextRig % RIGS + 1
	return r
end

local function burst(set: string, pos: Vector3, normal: Vector3, color: Color3)
	local rig = takeRig()
	-- attachment up (+Y) along the normal, so Top emission flies off the wall
	local up = if math.abs(normal.Y) > 0.98 then Vector3.xAxis else Vector3.yAxis
	rig.at.WorldCFrame = CFrame.lookAt(pos + normal * 0.05, pos + normal, up) * CFrame.Angles(-math.pi / 2, 0, 0)

	if rig.dust and set ~= "Glass" then
		rig.dust.Texture = SMOKE[math.random(#SMOKE)]
		rig.dust.Color = ColorSequence.new(color)
		rig.dust:Emit(if set == "Metal" then 1 else math.random(2, 3))
	end
	if rig.chips and set ~= "Soft" and set ~= "Water" then
		rig.chips.Color = ColorSequence.new(color)
		if set == "Glass" then
			rig.chips.Transparency = NumberSequence.new(0.35)
			rig.chips.LightEmission = 0.4
			rig.chips:Emit(FX.Chips * 2)
		else
			rig.chips.Transparency = NumberSequence.new(0)
			rig.chips.LightEmission = 0
			rig.chips:Emit(FX.Chips)
		end
	end
	if set == "Metal" then
		if rig.sparks then
			rig.sparks:Emit(FX.Sparks)
		end
		rig.light.Enabled = true
		rig.token += 1
		local token = rig.token
		task.delay(0.04, function()
			if rig.token == token then
				rig.light.Enabled = false
			end
		end)
	end
end

-- The surface a bullet hit, as this client sees it. The server's bullets hit the invisible
-- collision boxes (Server/CityBuildings), which sit near but not exactly on the visible walls,
-- and the visible city meshes are in collision group CityVisual, which a normal raycast skips.
-- So cast twice: once for the visible city meshes only (group CityVisualQuery) and once for
-- everything else (terrain, plain parts, cars), and take the nearer real surface. If neither
-- finds one (a prop whose mesh can't be raycast), use the collision box the bullet hit.
local function surfaceCast(origin: Vector3, hit: Vector3): (RaycastResult?, boolean)
	local dir = hit - origin
	local dist = dir.Magnitude
	if dist < 0.01 then
		return nil, false
	end
	dir /= dist
	local skip: { Instance } = { holes() }
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(skip, p.Character)
		end
	end
	-- start a little before the server's hit point (it may be behind a fence we can see through)
	local from = origin + dir * math.max(0, dist - 4)
	local reach = hit + dir * 2 - from

	local best: RaycastResult? = nil
	local box: RaycastResult? = nil

	local visual = RaycastParams.new()
	visual.FilterType = Enum.RaycastFilterType.Exclude
	visual.FilterDescendantsInstances = skip
	if pcall(function()
		visual.CollisionGroup = "CityVisualQuery"
	end) then
		for _ = 1, 4 do
			local r = workspace:Raycast(from, reach, visual)
			if not r or r.Instance.Transparency < 0.95 then
				best = r
				break
			end
			visual:AddToFilter(r.Instance)
		end
	end

	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = skip
	for _ = 1, 6 do
		local r = workspace:Raycast(from, reach, params)
		if not r then
			break
		end
		if r.Instance.Transparency < 0.95 then
			if not best or (r.Position - from).Magnitude < (best.Position - from).Magnitude then
				best = r
			end
			break
		end
		-- an invisible collision box: remember the first, keep looking for the visible surface
		box = box or r
		params:AddToFilter(r.Instance)
	end

	if best and (best.Position - hit).Magnitude < 4 then
		return best, false
	end
	if box and (box.Position - hit).Magnitude < 1 then
		return box, true
	end
	return nil, false
end

-- One bullet hitting the world: kind is the material name the server sent (Hitscan.fire).
function Effects.impact(origin: Vector3, hit: Vector3, kind: string)
	if not FX.Impacts or kind == "" or kind == "Body" then
		return
	end
	local set = SURFACE[kind] or "Concrete"
	local cam = workspace.CurrentCamera
	if cam and (cam.CFrame.Position - hit).Magnitude > FX.HoleRange * 1.5 then
		return
	end
	-- show it when the tracer gets there
	local delayTime = math.max(0, ((hit - origin).Magnitude - FX.TracerStart) / FX.TracerSpeed)
	task.delay(delayTime, function()
		local r, onBox = surfaceCast(origin, hit)
		local pos, normal = hit, (origin - hit).Unit
		local color = DUST[set]
		if r then
			pos, normal = r.Position, r.Normal
			local inst = r.Instance
			local tint = Color3.new(1, 1, 1)
			if not onBox then
				-- dust in the wall's own colour, a bit greyed (powder is paler than paint)
				color = inst.Color:Lerp(DUST[set], 0.5)
				if set == "Concrete" or set == "Wood" then
					tint = Color3.new(1, 1, 1):Lerp(inst.Color, 0.25)
				elseif set == "Dirt" or set == "Soft" then
					tint = inst.Color:Lerp(Color3.new(0.35, 0.3, 0.25), 0.5)
				end
			elseif set == "Dirt" or set == "Soft" then
				tint = Color3.fromRGB(110, 95, 75)
			end
			local camNow = workspace.CurrentCamera
			if not camNow or (camNow.CFrame.Position - pos).Magnitude < FX.HoleRange then
				placeHole(set, pos, normal, inst, tint)
			end
		end
		burst(set, pos, normal, color)
	end)
end

return Effects
