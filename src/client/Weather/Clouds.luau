-- Moving sky: Blender cloud meshes (ReplicatedStorage.WeatherMeshes, from
-- art/blender/weather/build_weather.py) that drift with the wind, slowly turn and breathe,
-- plus two huge textured layers that scroll overhead: thin cirrus (fair weather) and a grey
-- overcast deck (cloudy / rain).
--
-- The clouds live in a FIELD x FIELD square that wraps round the camera, and their place
-- comes from the server clock, so every player sees the same clouds in the same spots.
-- Clouds fade out toward the edge of the square, so the wrap is never seen.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local Clouds = {}

local FIELD = 7000 -- studs; the wrapping square around the camera
local FADE_START = 0.3 * FIELD -- clouds start fading this far from the camera...
local FADE_END = 0.48 * FIELD -- ...and are gone here
local CUMULUS = { "Cumulus1", "Cumulus2", "Cumulus3", "Cumulus4", "Cumulus5", "Congestus" }
local STRATO = { "Strato1", "Strato2" }
local N_CUMULUS = 64
local N_STRATO = 26
local PART_MAX = 2048 -- biggest size a part can have
local LAYER_GRID = 7 -- sky layers are 7 x 7 parts (14,336 studs across)

type Cloud = {
	part: MeshPart,
	base: Vector2, -- start spot in the field
	alt: number,
	size: Vector3, -- full size
	gate: number, -- 0-1: shows when the weather's share is above this
	speed: number,
	yaw: number,
	spin: number, -- radians per second
	breathe: number, -- breathing phase
	strato: boolean,
	shown: number, -- 0-1, eased toward the target
	lastT: number,
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

	task.spawn(function()
		local meshes = ReplicatedStorage:WaitForChild("WeatherMeshes", 60)
		if not meshes then
			warn("[Weather] no WeatherMeshes in ReplicatedStorage, so no mesh clouds")
			return
		end
		local rng = Random.new(1717) -- same seed for everyone = same sky
		local function add(names: { string }, strato: boolean, i: number)
			local src = meshes:FindFirstChild(names[rng:NextInteger(1, #names)]) :: MeshPart?
			if not src then
				return
			end
			local part = src:Clone()
			part.Anchored, part.CanCollide, part.CanQuery, part.CanTouch, part.CastShadow =
				true, false, false, false, false
			part.Material = Enum.Material.SmoothPlastic
			part.Color = Color3.new(1, 1, 1)
			part.Transparency = 1
			part.Name = `Cloud{i}`
			local scale = if strato then rng:NextNumber(90, 150) else rng:NextNumber(38, 95)
			local size = src.Size * scale
			if not strato then
				size *= Vector3.new(1, rng:NextNumber(0.8, 1.1), 1)
			end
			size = fit(size)
			part.Size = size
			part.Parent = folder
			table.insert(clouds, {
				part = part,
				base = Vector2.new(rng:NextNumber(0, FIELD), rng:NextNumber(0, FIELD)),
				alt = if strato then rng:NextNumber(560, 760) else rng:NextNumber(750, 1150),
				size = size,
				gate = rng:NextNumber(0, 0.98),
				speed = Config.Weather.CloudSpeed * rng:NextNumber(0.75, 1.3) * (if strato then 1.25 else 1),
				yaw = rng:NextNumber(0, math.pi * 2),
				spin = rng:NextNumber(-1, 1) * 0.0025,
				breathe = rng:NextNumber(0, math.pi * 2),
				strato = strato,
				shown = 0,
				lastT = -1,
			})
		end
		for i = 1, N_CUMULUS do
			add(CUMULUS, false, i)
		end
		for i = 1, N_STRATO do
			add(STRATO, true, N_CUMULUS + i)
		end
	end)
end

local sizeClock = 0

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
	local function scroll(l: Layer, speed: number, alpha: number, color: Color3)
		local snap = CFrame.new(
			math.floor(camPos.X / PART_MAX + 0.5) * PART_MAX,
			l.alt,
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
	scroll(cirrus, Config.Weather.CloudSpeed * 1.6, 0.75 * w.cirrus, tint)
	scroll(overcast, Config.Weather.CloudSpeed * 1.2, 0.92 * w.overcast, tint:Lerp(Color3.new(0.45, 0.47, 0.5), 0.25))

	-- mesh clouds
	sizeClock += dt
	local resize = sizeClock > 0.25
	if resize then
		sizeClock = 0
	end
	local recolor = resize
	local stratoTint =
		tint:Lerp(Color3.new(0.42, 0.44, 0.48):Lerp(Color3.new(0.1, 0.11, 0.14), 1 - tint.G), 0.3 + 0.4 * gloom)
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
		local part = c.part
		local tr = if alpha < 0.02 then 1 else 1 - alpha * (if c.strato then 0.93 else 0.97)
		if math.abs(part.Transparency - tr) > 0.01 then
			part.Transparency = tr
		end
		if tr < 1 then
			-- rain clouds sink a little lower and spread
			local low = gloom * (if c.strato then 180 else 120)
			local breathe = 1 + 0.07 * math.sin(t / 47 + c.breathe)
			if resize then
				local s = c.size * Vector3.new(breathe * (1 + 0.25 * gloom), 1 / breathe ^ 0.5, breathe)
				part.Size = fit(s)
			end
			local cf = CFrame.new(x, c.alt - low, z) * CFrame.Angles(0, c.yaw + (c.spin * t) % (math.pi * 2), 0)
			n += 1
			parts[n] = part
			cframes[n] = cf
			if recolor then
				part.Color = if c.strato then stratoTint else tint
			end
		end
	end
	if n > 0 then
		workspace:BulkMoveTo(parts, cframes, Enum.BulkMoveMode.FireCFrameChanged)
	end
end

return Clouds
