-- Thunderstorm lightning on this client. The server picks every strike (Server/Weather ->
-- WeatherRemotes.Strike: position, seed, kind) so everyone sees the same bolt.
--   bolt   a Blender-rendered branching bolt (art/blender/weather/render_lightning.py ->
--          TextureIds.Weather.LightningBolt01..08) on a tall card from the clouds to the hit
--          point (roof, tower, street), always turned to the camera; a rendered impact flash
--          flipbook at the hit; a flickering flash that lights the sky, clouds and city, a light at the
--          hit, sparks + smoke, then thunder: a crack when close, a rumble when far, late by
--          the distance (sound is slower than light)
--   sheet  a flash inside the clouds and a far rumble, no bolt
-- A bolt close to the camera also whites out the screen for a moment and shakes the camera.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local SoundService = game:GetService("SoundService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local Sky = require(script.Parent:WaitForChild("Sky"))

local Lightning = {}

local BOLT_COLOR = Color3.fromRGB(222, 230, 255)
local CLOUD_HEIGHT = 620 -- bolts start about here
local SOUND_SPEED = 1150 -- studs per second (1 m = 3.6 studs)

local folder: Folder
local overlay: Frame
local sparks: ParticleEmitter
local smoke: ParticleEmitter
local fxAt: Attachment
local impact: ParticleEmitter?
local shake = 0 -- current shake strength (degrees)
local shakeT = 0

-- jagged line from a to b by midpoint displacement
local function zigzag(rng: Random, a: Vector3, b: Vector3, depth: number, jitter: number, out: { Vector3 })
	if depth == 0 then
		table.insert(out, b)
		return
	end
	local mid = (a + b) / 2
	local len = (b - a).Magnitude
	mid += Vector3.new(rng:NextNumber(-1, 1), rng:NextNumber(-0.3, 0.3), rng:NextNumber(-1, 1)) * len * jitter
	zigzag(rng, a, mid, depth - 1, jitter, out)
	zigzag(rng, mid, b, depth - 1, jitter, out)
end

local function segment(p0: Vector3, p1: Vector3, width: number, model: Model)
	local len = (p1 - p0).Magnitude
	if len < 0.05 then
		return
	end
	local p = Instance.new("Part")
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
	p.Material = Enum.Material.Neon
	p.Color = BOLT_COLOR
	p.Size = Vector3.new(width, width, len + width * 0.5)
	p.CFrame = CFrame.lookAt((p0 + p1) / 2, p1)
	p.Parent = model
end

local function buildBolt(rng: Random, top: Vector3, hit: Vector3, width: number): Model
	local model = Instance.new("Model")
	model.Name = "Bolt"
	local pts = { top }
	zigzag(rng, top, hit, 6, 0.22, pts)
	for i = 1, #pts - 1 do
		segment(pts[i], pts[i + 1], width, model)
	end
	-- branches that fork off and die out in the air
	for _ = 1, rng:NextInteger(3, 7) do
		local i = rng:NextInteger(2, math.max(2, math.floor(#pts * 0.7)))
		local from = pts[i]
		local dir = (pts[math.min(i + 1, #pts)] - from).Unit
		local side = Vector3.new(rng:NextNumber(-1, 1), 0, rng:NextNumber(-1, 1)).Unit
		local reach = (top.Y - hit.Y) * rng:NextNumber(0.08, 0.25)
		local to = from + (dir * 0.6 + side * 0.8).Unit * reach
		local bp = { from }
		zigzag(rng, from, to, 4, 0.3, bp)
		for j = 1, #bp - 1 do
			segment(bp[j], bp[j + 1], width * 0.45, model)
		end
	end
	-- glow round the main channel
	local glow = Instance.new("PointLight")
	glow.Color = BOLT_COLOR
	glow.Range = 60
	glow.Brightness = 10
	glow.Shadows = true
	local holder = Instance.new("Part")
	holder.Anchored, holder.CanCollide, holder.CanQuery, holder.CanTouch = true, false, false, false
	holder.Transparency = 1
	holder.Size = Vector3.new(1, 1, 1)
	holder.Position = hit + Vector3.new(0, 12, 0)
	glow.Parent = holder
	holder.Parent = model
	model.Parent = folder
	return model
end

local tex = TextureIds.Weather or {}
local boltIds = {}
for i = 1, 8 do
	local id = tex[string.format("LightningBolt%02d", i)]
	if id then
		table.insert(boltIds, id)
	end
end

-- rendered bolt on a card (the render's bottom edge is the hit point)
local function spriteBolt(rng: Random, top: Vector3, hit: Vector3): Model
	local model = Instance.new("Model")
	model.Name = "Bolt"
	local h = (top.Y - hit.Y) * 1.03
	local width = math.min(h * 0.5, 2040)
	h = math.min(h, 2040)
	local card = Instance.new("Part")
	card.Name = "Card"
	card.Anchored, card.CanCollide, card.CanQuery, card.CanTouch, card.CastShadow = true, false, false, false, false
	card.Transparency = 1
	card.Size = Vector3.new(width, h, 0.2)
	card:SetAttribute("Centre", Vector3.new(hit.X, hit.Y + h / 2 - h * 0.012, hit.Z))
	local decal = Instance.new("Decal")
	decal.Texture = `rbxassetid://{boltIds[rng:NextInteger(1, #boltIds)]}`
	decal.Face = Enum.NormalId.Front
	decal.Color3 = Color3.new(1, 1, 1)
	decal.Parent = card
	card.Parent = model
	local glow = Instance.new("PointLight")
	glow.Color = BOLT_COLOR
	glow.Range = 60
	glow.Brightness = 10
	glow.Shadows = true
	local holder = Instance.new("Part")
	holder.Anchored, holder.CanCollide, holder.CanQuery, holder.CanTouch = true, false, false, false
	holder.Transparency = 1
	holder.Size = Vector3.new(1, 1, 1)
	holder.Position = hit + Vector3.new(0, 12, 0)
	glow.Parent = holder
	holder.Parent = model
	model.Parent = folder
	return model
end

-- keep sprite bolts turned to the camera (upright, turning round the vertical only)
local liveCards: { BasePart } = {}

local function setBolt(model: Model, tr: number)
	for _, p in model:GetChildren() do
		local decal = p:FindFirstChildOfClass("Decal")
		if decal then
			decal.Transparency = tr
		elseif p:IsA("BasePart") then
			local light = p:FindFirstChildOfClass("PointLight")
			if light then
				light.Enabled = tr < 0.9
			else
				p.Transparency = tr
			end
		end
	end
end

local function playSound(id: number?, volume: number, delay: number)
	if not id then
		return
	end
	task.delay(delay, function()
		local s = Instance.new("Sound")
		s.SoundId = `rbxassetid://{id}`
		s.Volume = volume
		s.PlaybackSpeed = 0.9 + math.random() * 0.2
		s.Parent = SoundService
		s:Play()
		s.Ended:Once(function()
			s:Destroy()
		end)
		task.delay(12, function()
			if s.Parent then
				s:Destroy()
			end
		end)
	end)
end

local function thunder(dist: number, close: boolean)
	local delay = math.min(dist / SOUND_SPEED, 7)
	local pick = math.random(1, 2)
	if close then
		playSound(SoundIds["ThunderCrack" .. pick], 1.4, delay)
	else
		playSound(SoundIds["ThunderRumble" .. pick], math.clamp(1.3 - dist / 3000, 0.35, 1.1), delay)
	end
end

-- flicker: a few quick pulses of light, like a real return stroke
local function flicker(strength: number, model: Model?)
	local pulses = { { 0, 1 }, { 0.07, 0 }, { 0.12, 0.8 }, { 0.2, 0 }, { 0.26, 0.5 } }
	for _, p in pulses do
		task.delay(p[1], function()
			if p[2] > 0 then
				Sky.addFlash(strength * p[2])
			end
			if model then
				setBolt(model, if p[2] > 0 then 0 else 0.85)
			end
		end)
	end
end

local function onStrike(pos: Vector3, seed: number, kind: string)
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local rng = Random.new(seed)
	local L = Config.Weather.Lightning
	if kind == "sheet" then
		local dist = (Vector3.new(pos.X, camPos.Y, pos.Z) - camPos).Magnitude
		flicker(math.clamp(0.9 - dist / 4000, 0.25, 0.7), nil)
		thunder(dist + 600, false)
		return
	end
	local dist = (pos - camPos).Magnitude
	local top = Vector3.new(
		pos.X + rng:NextNumber(-140, 140),
		math.max(CLOUD_HEIGHT, pos.Y + 150),
		pos.Z + rng:NextNumber(-140, 140)
	)
	-- thicker when far so it still reads on screen
	local width = math.clamp(dist / 260, 0.7, 5)
	local model = if #boltIds > 0 then spriteBolt(rng, top, pos) else buildBolt(rng, top, pos, width)
	local card = model:FindFirstChild("Card") :: BasePart?
	if card then
		table.insert(liveCards, card)
	end
	local strength = math.clamp(1.4 - dist / 2500, 0.45, 1.3)
	flicker(strength, model)
	task.delay(0.32, function()
		-- afterglow fade, then gone
		for i = 1, 8 do
			setBolt(model, 0.3 + i * 0.09)
			task.wait(0.03)
		end
		if card then
			local i = table.find(liveCards, card)
			if i then
				table.remove(liveCards, i)
			end
		end
		model:Destroy()
	end)
	-- impact
	if dist < 1200 then
		fxAt.WorldPosition = pos + Vector3.new(0, 0.5, 0)
		if impact then
			impact.Size = NumberSequence.new(math.clamp(18 + dist / 40, 18, 40))
			fxAt.WorldPosition = pos + Vector3.new(0, 6, 0)
			impact:Emit(1)
			fxAt.WorldPosition = pos + Vector3.new(0, 0.5, 0)
		end
		sparks:Emit(45)
		smoke:Emit(8)
	end
	local close = dist < L.ShakeRadius
	thunder(dist, dist < 450)
	if close then
		local k = 1 - dist / L.ShakeRadius
		overlay.BackgroundTransparency = 1 - 0.75 * k
		shake = math.max(shake, 0.6 + 1.6 * k)
		shakeT = 0
	end
end

function Lightning.start()
	folder = Instance.new("Folder")
	folder.Name = "WeatherLightning"
	folder.Parent = workspace

	fxAt = Instance.new("Attachment")
	fxAt.Name = "LightningImpact"
	fxAt.Parent = workspace.Terrain
	if tex.LightningImpact then
		local e = Instance.new("ParticleEmitter")
		e.Texture = `rbxassetid://{tex.LightningImpact}`
		e.FlipbookLayout = Enum.ParticleFlipbookLayout.Grid4x4
		e.FlipbookMode = Enum.ParticleFlipbookMode.OneShot
		e.Orientation = Enum.ParticleOrientation.FacingCamera
		e.LightEmission = 1
		e.LightInfluence = 0
		e.Speed = NumberRange.new(0)
		e.Lifetime = NumberRange.new(0.55)
		e.Rate = 0
		e.Parent = fxAt
		impact = e
	end
	sparks = Instance.new("ParticleEmitter")
	sparks.Texture = `rbxassetid://{tex.Spray or tex.RainSpray}`
	sparks.Color = ColorSequence.new(Color3.fromRGB(235, 240, 255), Color3.fromRGB(255, 190, 120))
	sparks.LightEmission = 1
	sparks.LightInfluence = 0
	sparks.Size = NumberSequence.new(0.5, 0.1)
	sparks.Speed = NumberRange.new(25, 60)
	sparks.SpreadAngle = Vector2.new(80, 80)
	sparks.EmissionDirection = Enum.NormalId.Top
	sparks.Acceleration = Vector3.new(0, -90, 0)
	sparks.Lifetime = NumberRange.new(0.3, 0.8)
	sparks.Drag = 2
	sparks.Rate = 0
	sparks.Parent = fxAt
	smoke = Instance.new("ParticleEmitter")
	smoke.Texture = `rbxassetid://{tex.RainSheet}`
	smoke.Color = ColorSequence.new(Color3.fromRGB(110, 110, 115))
	smoke.Size = NumberSequence.new(4, 14)
	smoke.Transparency = NumberSequence.new(0.5, 1)
	smoke.Speed = NumberRange.new(4, 9)
	smoke.SpreadAngle = Vector2.new(40, 40)
	smoke.Lifetime = NumberRange.new(1.5, 2.5)
	smoke.Rate = 0
	smoke.Parent = fxAt

	local gui = Instance.new("ScreenGui")
	gui.Name = "LightningFlash"
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 50
	gui.ResetOnSpawn = false
	overlay = Instance.new("Frame")
	overlay.Size = UDim2.fromScale(1, 1)
	overlay.BackgroundColor3 = Color3.fromRGB(235, 240, 255)
	overlay.BackgroundTransparency = 1
	overlay.BorderSizePixel = 0
	overlay.Parent = gui
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")

	-- screen flash fade + camera shake, after the camera scripts have placed the camera
	RunService:BindToRenderStep("WeatherLightning", Enum.RenderPriority.Camera.Value + 1, function(dt)
		local camNow = workspace.CurrentCamera
		if camNow and #liveCards > 0 then
			local cp = camNow.CFrame.Position
			for _, card in liveCards do
				local c = card:GetAttribute("Centre") :: Vector3
				card.CFrame = CFrame.lookAt(c, Vector3.new(cp.X, c.Y, cp.Z))
			end
		end
		if overlay.BackgroundTransparency < 1 then
			overlay.BackgroundTransparency = math.min(1, overlay.BackgroundTransparency + dt * 2.6)
		end
		if shake > 0.01 then
			shakeT += dt
			local cam = workspace.CurrentCamera
			local a = math.rad(shake)
			local n = shakeT * 28
			cam.CFrame *= CFrame.Angles(math.noise(n, 0.3) * a, math.noise(0.7, n) * a, math.noise(n, 5.1) * a * 0.5)
			shake *= math.exp(-dt * 4.5)
		else
			shake = 0
		end
	end)

	local remotes = ReplicatedStorage:WaitForChild("WeatherRemotes", 30)
	local remote = remotes and remotes:WaitForChild("Strike", 10) :: RemoteEvent?
	if remote then
		remote.OnClientEvent:Connect(onStrike)
	end
end

return Lightning
