-- Moving sky, GTA style: clouds are volumetric renders from Blender
-- (art/blender/weather/render_weather_fx.py -> TextureIds.Weather.Cloud_<Name>, list in
-- Shared/CloudSprites) shown on big cards that always face the camera, so they read as soft
-- lit clouds from any side. They drift with the wind and slowly swell and shrink; two huge
-- textured layers scroll overhead too: thin cirrus (fair weather) and a grey overcast deck.
--
-- The cards live in a FIELD x FIELD square that wraps round the camera, and their place
-- comes from the server clock, so every player sees the same clouds in the same spots.
-- Clouds fade out toward the edge of the square, so the wrap is never seen.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))
local CloudSprites = require(Shared:WaitForChild("CloudSprites"))

local Clouds = {}

local FIELD = 7000 -- studs; the wrapping square around the camera
local FADE_START = 0.3 * FIELD -- clouds start fading this far from the camera...
local FADE_END = 0.48 * FIELD -- ...and are gone here
local N_CUMULUS = 70
local N_STRATO = 60
local PART_MAX = 2048 -- biggest size a part can have
local LAYER_GRID = 7 -- sky layers are 7 x 7 parts (14,336 studs across)

type Cloud = {
	part: Part,
	decal: Decal,
	base: Vector2, -- start spot in the field
	alt: number, -- height of the cloud's base
	size: Vector3, -- card size
	gate: number, -- 0-1: shows when the weather's share is above this
	speed: number,
	breathe: number, -- breathing phase
	strato: boolean,
	shown: number, -- 0-1, eased toward the target
}

local clouds: { Cloud } = {}
local folder: Folder
local cirrus: Layer
local overcast: Layer
local parts: { BasePart } = {}
local cframes: { CFrame } = {}

-- parts can't be bigger than PART_MAX on any side: shrink evenly if needed
local function fit(size: Vector3): Vector3
	local m = math.max(size.X, size.Y, size.Z)
	return if m > PART_MAX - 8 then size * ((PART_MAX - 8) / m) else size
end

local function wrap(v: number, center: number): number
	return center + ((v - center + FIELD / 2) % FIELD) - FIELD / 2
end

-- A sky layer: a GRID x GRID sheet of 2048-stud parts (the biggest a part can be) with the
-- same Texture on their undersides. The tile size divides 2048, so the pattern runs on
-- across the parts with one shared offset, and the sheet can jump by whole parts to follow
-- the camera without the pattern moving.
type Layer = { model: Model, textures: { Texture }, alt: number, tile: number }

local function layer(name: string, image: number?, alt: number, tile: number): Layer
	local model = Instance.new("Model")
	model.Name = name
	local list = {}
	for i = 0, LAYER_GRID - 1 do
		for j = 0, LAYER_GRID - 1 do
			local p = Instance.new("Part")
			p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
			p.Transparency = 1
			p.Size = Vector3.new(PART_MAX, 1, PART_MAX)
			p.CFrame = CFrame.new((i - (LAYER_GRID - 1) / 2) * PART_MAX, 0, (j - (LAYER_GRID - 1) / 2) * PART_MAX)
			if image then
				local t = Instance.new("Texture")
				t.Texture = `rbxassetid://{image}`
				t.Face = Enum.NormalId.Bottom
				t.StudsPerTileU = tile
				t.StudsPerTileV = tile
				t.Transparency = 1
				t.Parent = p
				table.insert(list, t)
			end
			p.Parent = model
		end
	end
	model.Parent = folder
	return { model = model, textures = list, alt = alt, tile = tile }
end

function Clouds.start()
	folder = Instance.new("Folder")
	folder.Name = "WeatherSky"
	folder.Parent = workspace
	local tex = TextureIds.Weather or {}
	cirrus = layer("Cirrus", tex.Cirrus, 1700, 2048)
	overcast = layer("Overcast", tex.Overcast, 1300, 1024)

	local cumulus, strato = {}, {}
	for _, sp in CloudSprites do
		if tex["Cloud_" .. sp.name] then
			table.insert(if sp.kind == "St" then strato else cumulus, sp)
		end
	end
	if #cumulus == 0 then
		warn("[Weather] no cloud sprites uploaded yet (tools/weather_sprites.py), so no clouds")
		return
	end
	if #strato == 0 then
		strato = cumulus
	end
	local rng = Random.new(1717) -- same seed for everyone = same sky
	local function add(list, isStrato: boolean, i: number)
		local sp = list[rng:NextInteger(1, #list)]
		local width = if isStrato then rng:NextNumber(1500, 2040) else rng:NextNumber(550, 1350)
		local size = fit(Vector3.new(width, width / sp.aspect, 1))
		local part = Instance.new("Part")
		part.Name = `Cloud{i}`
		part.Anchored, part.CanCollide, part.CanQuery, part.CanTouch, part.CastShadow = true, false, false, false, false
		part.Transparency = 1
		part.Size = size
		local decal = Instance.new("Decal")
		decal.Texture = `rbxassetid://{tex["Cloud_" .. sp.name]}`
		decal.Face = Enum.NormalId.Front
		decal.Transparency = 1
		decal.Parent = part
		part.Parent = folder
		table.insert(clouds, {
			part = part,
			decal = decal,
			base = Vector2.new(rng:NextNumber(0, FIELD), rng:NextNumber(0, FIELD)),
			alt = if isStrato then rng:NextNumber(520, 720) else rng:NextNumber(700, 1050),
			size = size,
			gate = rng:NextNumber(0, 0.98),
			speed = Config.Weather.CloudSpeed * rng:NextNumber(0.75, 1.3) * (if isStrato then 1.25 else 1),
			breathe = rng:NextNumber(0, math.pi * 2),
			strato = isStrato,
			shown = 0,
		})
	end
	for i = 1, N_CUMULUS do
		add(cumulus, false, i)
	end
	for i = 1, N_STRATO do
		add(strato, true, N_CUMULUS + i)
	end
end

local sizeClock = 0
local lastTint = Color3.new(1, 1, 1)

function Clouds.update(w, dt: number, tint: Color3)
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local t = workspace:GetServerTimeNow()
	-- Vector2/Vector3 hold 32-bit floats, far too coarse for (speed x server time), so the
	-- drift is worked out in plain numbers and wrapped before it goes into a vector
	local windDir = Config.Weather.WindDirection.Unit
	local wx, wz = windDir.X, windDir.Y
	local gloom = w.gloom
	-- scrolling layers: follow the camera in whole-part steps; the texture drifts with the wind
	local function scroll(l: Layer, alt: number, speed: number, alpha: number, color: Color3)
		local snap = CFrame.new(
			math.floor(camPos.X / PART_MAX + 0.5) * PART_MAX,
			alt,
			math.floor(camPos.Z / PART_MAX + 0.5) * PART_MAX
		)
		if l.model:GetPivot().Position ~= snap.Position then
			l.model:PivotTo(snap)
		end
		local u, v = (wx * speed * t) % l.tile, (wz * speed * t) % l.tile
		local tr = 1 - alpha
		for _, tex in l.textures do
			tex.OffsetStudsU = u
			tex.OffsetStudsV = v
			if tex.Transparency ~= tr then
				tex.Transparency = tr
			end
			if tex.Color3 ~= color then
				tex.Color3 = color
			end
		end
	end
	scroll(cirrus, cirrus.alt, Config.Weather.CloudSpeed * 1.6, 0.75 * w.cirrus, tint)
	-- the grey deck drops down to a low storm ceiling in rain, so bolts come out of it
	scroll(
		overcast,
		overcast.alt - 800 * gloom,
		Config.Weather.CloudSpeed * 1.2,
		0.92 * w.overcast,
		tint:Lerp(Color3.new(0.45, 0.47, 0.5), 0.25)
	)

	-- cloud cards
	sizeClock += dt
	local resize = sizeClock > 0.25
	if resize then
		sizeClock = 0
	end
	local stratoTint =
		tint:Lerp(Color3.new(0.42, 0.44, 0.48):Lerp(Color3.new(0.1, 0.11, 0.14), 1 - tint.G), 0.25 + 0.45 * gloom)
	-- rain darkens cumulus bases too
	local cuTint = tint:Lerp(stratoTint, 0.5 * gloom)
	-- recolour 4x a second, or every frame while the tint jumps (lightning)
	local jump = math.abs(tint.R - lastTint.R) + math.abs(tint.G - lastTint.G) + math.abs(tint.B - lastTint.B)
	local recolor = resize or jump > 0.03
	if recolor then
		lastTint = tint
	end
	local n = 0
	table.clear(parts)
	table.clear(cframes)
	local ease = math.min(dt * 0.6, 1)
	for _, c in clouds do
		local share = if c.strato then w.strato else w.cumulus
		local target = math.clamp((share - c.gate) * 6, 0, 1)
		c.shown += (target - c.shown) * ease
		local x = wrap(c.base.X + (wx * c.speed * t) % FIELD, camPos.X)
		local z = wrap(c.base.Y + (wz * c.speed * t) % FIELD, camPos.Z)
		local d = Vector2.new(x - camPos.X, z - camPos.Z).Magnitude
		local edge = 1 - math.clamp((d - FADE_START) / (FADE_END - FADE_START), 0, 1)
		local alpha = c.shown * edge
		local tr = if alpha < 0.02 then 1 else 1 - alpha
		if math.abs(c.decal.Transparency - tr) > 0.01 then
			c.decal.Transparency = tr
		end
		if tr < 1 then
			-- rain clouds sink lower and spread; every card swells and shrinks slowly
			local low = gloom * (if c.strato then 220 else 110)
			local breathe = 1 + 0.06 * math.sin(t / 53 + c.breathe)
			local size = c.size * (breathe * (1 + 0.2 * gloom))
			if resize then
				c.part.Size = fit(Vector3.new(size.X, size.Y, 1))
			end
			if recolor then
				c.decal.Color3 = if c.strato then stratoTint else cuTint
			end
			local pos = Vector3.new(x, c.alt - low + size.Y * 0.45, z)
			n += 1
			parts[n] = c.part
			cframes[n] = CFrame.lookAt(pos, camPos) -- the Front face (the decal) looks at the camera
		end
	end
	if n > 0 then
		workspace:BulkMoveTo(parts, cframes, Enum.BulkMoveMode.FireCFrameChanged)
	end
end

return Clouds
