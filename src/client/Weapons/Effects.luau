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
local RunService = game:GetService("RunService")
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

return Effects
