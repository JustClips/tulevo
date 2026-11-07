-- Finishes the city's Blender buildings: Models under workspace.City.Buildings with
-- attribute LiveSyncAsset (made by tools/build_city_map.py).
-- In Studio the LiveSync plugin (v5+) already loads each mesh in edit mode; if a model
-- is still empty here (older plugin, or a fresh server) it is loaded now the same way.
-- Then parts are anchored, kept streamed in so the skyline shows from anywhere, and
-- named parts get their Roblox look:
--   Light*     glowing strips -> Neon, no texture
--   Lamp*      canopy lamps -> Neon + a SurfaceLight shining down + a soft light-shaft Beam
--   ShopLamp   strip over a shop front -> Neon + a SurfaceLight shining down
--   PriceFace  printed price sign -> a small glow so it reads at night
--   Neon<Colour> (NeonPink, NeonCyan, NeonRed) coloured neon tubes / beacons + a coloured glow
--   Sconce     small porch lights -> warm Neon
-- Lamps get brighter and the light shafts show up as the in-game clock goes into night.
local InsertService = game:GetService("InsertService")
local Lighting = game:GetService("Lighting")
local RunService = game:GetService("RunService")

local LAMP_COLOR = Color3.fromRGB(255, 244, 222)
local NEON = {
	NeonPink = Color3.fromRGB(255, 70, 170),
	NeonCyan = Color3.fromRGB(60, 235, 255),
	NeonRed = Color3.fromRGB(255, 40, 30),
}
-- Textures with see-through pixels (chain-link fence, graffiti decals).
local ALPHA = {
	ChainLink = true,
	Tag = true,
	FxFall = true,
	FxRipple = true,
	-- Fort Halden army base
	RazorWire = true,
	CamoNet = true,
	Slide1Mesh = true,
	Slide2Mesh = true,
}
-- Small decor parts that should not collide.
local DECO = {
	Frame = true,
	Sill = true,
	WinIron = true,
	Pipe = true,
	Meter = true,
	CandyRack = true,
	FridgeDoors = true,
	Tag = true,
}
local lamps = {} -- { light = SurfaceLight, beam = Beam?, day = number, night = number }

local function hasParts(model: Model): boolean
	return model:FindFirstChildWhichIsA("BasePart", true) ~= nil
end

local function load(model: Model)
	local id = tonumber(model:GetAttribute("LiveSyncAsset"))
	if not id then
		return
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[City] could not load {model.Name} ({id}): {container}`)
		return
	end
	-- Drop the GLB's embedded SurfaceAppearances before they reach the place: every part gets
	-- its colour map from LiveSyncTextures, and in Studio these make PublishService try (and
	-- fail, rate-limited) to upload texture packs.
	for _, d in container:GetDescendants() do
		if d:IsA("SurfaceAppearance") then
			d:Destroy()
		end
	end
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	local center = model:GetAttribute("LiveSyncBoxCenter")
	if typeof(center) == "Vector3" then
		local box = model:GetBoundingBox()
		model:PivotTo(CFrame.new(center) * box:ToObjectSpace(model:GetPivot()))
	end
end

local function neon(part: BasePart)
	for _, c in part:GetChildren() do
		if c:IsA("SurfaceAppearance") then
			c:Destroy()
		end
	end
	if part:IsA("MeshPart") then
		part.TextureID = ""
	end
	part.Material = Enum.Material.Neon
	part.Color = LAMP_COLOR
	part.CastShadow = false
	part.CanCollide = false
end

local function downLight(part: BasePart, range: number, day: number, night: number): SurfaceLight
	local light = Instance.new("SurfaceLight")
	light.Face = Enum.NormalId.Bottom
	light.Angle = 120
	light.Range = range
	light.Color = LAMP_COLOR
	light.Shadows = true
	light.Brightness = day
	light.Parent = part
	table.insert(lamps, { light = light, day = day, night = night })
	return light
end

-- Light shaft: a camera-facing beam from the lamp to the ground, widening as it falls.
local function lightShaft(part: BasePart, model: Model)
	local params = RaycastParams.new()
	params.FilterDescendantsInstances = { model }
	params.FilterType = Enum.RaycastFilterType.Exclude
	local from = part.Position - Vector3.new(0, part.Size.Y / 2 + 0.05, 0)
	local hit = workspace:Raycast(from, Vector3.new(0, -60, 0), params)
	local groundY = if hit then hit.Position.Y else from.Y - 18
	local a0 = Instance.new("Attachment")
	a0.WorldPosition = from
	a0.Parent = part
	local a1 = Instance.new("Attachment")
	a1.WorldPosition = Vector3.new(from.X, groundY + 0.2, from.Z)
	a1.Parent = part
	local beam = Instance.new("Beam")
	beam.Attachment0, beam.Attachment1 = a0, a1
	beam.Width0 = math.max(part.Size.X, part.Size.Z)
	beam.Width1 = beam.Width0 * 2.4
	beam.FaceCamera = true
	beam.LightEmission = 1
	beam.LightInfluence = 0
	beam.Color = ColorSequence.new(LAMP_COLOR)
	beam.Transparency = NumberSequence.new(1)
	beam.Segments = 1
	beam.Parent = part
	lamps[#lamps].beam = beam
end

-- Colour textures uploaded as separate Images (tools/upload_textures.py): the model's
-- LiveSyncTextures attribute is JSON { part name: image id }. The GLB's own embedded
-- SurfaceAppearance images don't always show in game, so these replace them.
local HttpService = game:GetService("HttpService")

local function applyTextures(model: Model)
	local raw = model:GetAttribute("LiveSyncTextures")
	if type(raw) ~= "string" then
		return
	end
	local ok, map = pcall(HttpService.JSONDecode, HttpService, raw)
	if not ok then
		return
	end
	for _, d in model:GetDescendants() do
		local id = d:IsA("MeshPart") and map[d.Name]
		if id then
			for _, c in d:GetChildren() do
				if c:IsA("SurfaceAppearance") then
					c:Destroy()
				end
			end
			d.TextureID = `rbxassetid://{id}`
			d.Color = Color3.new(1, 1, 1)
		end
	end
end

-- Walk-in buildings (corner store): every part that shares a mesh with pieces both outside
-- and inside (door mats, frames, lights, trim) would make an invisible wall across the door,
-- so only the real solid pieces collide.
local WALK_IN_SOLID = {
	"^Wall",
	"^Parapet",
	"^Cooler",
	"^Gondola",
	"^Counter",
	"^Freezer",
	"^Atm",
	"^ShopFloor",
	"^Asphalt",
	"^Concrete",
	"^Flat",
}
-- Plants never block walking.
local PLANTS = {
	Leaf = true,
	LeafB = true,
	LeafC = true,
	LeafD = true,
	LeafE = true,
	LeafF = true,
	CamoNet = true,
	Palm = true,
	Shrub = true,
	Hedge = true,
	Soil = true,
	FlowerR = true,
	FlowerY = true,
	FlowerW = true,
}

local function solidInWalkIn(name: string): boolean
	for _, pat in WALK_IN_SOLID do
		if name:match(pat) then
			return true
		end
	end
	return false
end

local function style(model: Model)
	applyTextures(model)
	local walkIn = model:FindFirstChild("WallF1", true) ~= nil
	for _, d in model:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
			if DECO[d.Name] or d.Name:match("^Poster") or d.Name:match("^ShelfGoods") or d.Name:match("^Deco") then
				-- Thin dressing: never blocks walking or bullets.
				d.CanCollide = false
				d.CanQuery = false
			end
			if PLANTS[d.Name] or (walkIn and not solidInWalkIn(d.Name)) then
				d.CanCollide = false
			end
			if d.Name:match("^Fx") then
				-- fountain water (Client/FountainFx animates it): walk through, no shadows
				d.CanCollide = false
				d.CanQuery = false
				d.CastShadow = false
				if d.Name == "FxJet" then
					d.Transparency = 0.45
				elseif d.Name == "FxPool" then
					d.Transparency = 0.12
				end
			end
			if ALPHA[d.Name] then
				-- A texture's transparent pixels only cut through when the part itself is
				-- a hair transparent.
				d.Transparency = 0.02
			elseif d.Name:match("^ClearGlass") then
				d.Material = Enum.Material.Glass
				d.Transparency = 0.6
				d.CastShadow = false
			elseif d.Name:match("^LightCeil") then
				neon(d)
				downLight(d, 18, 0.6, 1.5)
			elseif d.Name:match("^Light") then
				neon(d)
			elseif d.Name:match("^Lamp%d") then
				neon(d)
				downLight(d, 26, 0.6, 3)
				lightShaft(d, model)
			elseif d.Name == "ShopLamp" then
				neon(d)
				downLight(d, 16, 0.4, 2)
			elseif NEON[d.Name] then
				neon(d)
				d.Color = NEON[d.Name]
				local glow = Instance.new("PointLight")
				glow.Range, glow.Brightness, glow.Color = 12, 0, NEON[d.Name]
				glow.Parent = d
				table.insert(lamps, { light = glow, day = 0, night = 1.5 })
			elseif d.Name == "Sconce" then
				neon(d)
				d.Color = Color3.fromRGB(255, 226, 170)
			elseif d.Name == "PriceFace" then
				local glow = Instance.new("PointLight")
				glow.Range, glow.Brightness, glow.Color = 14, 0, Color3.fromRGB(255, 220, 170)
				glow.Parent = d
				table.insert(lamps, { light = glow, day = 0, night = 1.2 })
			end
		end
	end
	model.ModelStreamingMode = Enum.ModelStreamingMode.Persistent
end

local city = workspace:WaitForChild("City", 10)
local buildings = city and city:WaitForChild("Buildings", 10)
if not buildings then
	warn("[City] workspace.City.Buildings not found")
	return
end
for _, model in buildings:GetChildren() do
	if model:IsA("Model") and model:GetAttribute("LiveSyncAsset") then
		if not hasParts(model) then
			load(model)
		end
		style(model)
		print(`[City] {model.Name} ready`)
	end
end

-- Day/night: 0 by day, 1 at night, fading over an hour at dusk and dawn.
local function nightness(clock: number): number
	if clock >= 19 or clock < 5 then
		return 1
	elseif clock >= 18 then
		return clock - 18
	elseif clock < 6 then
		return 6 - clock
	end
	return 0
end

local last = -1
RunService.Heartbeat:Connect(function()
	local n = math.floor(nightness(Lighting.ClockTime) * 20 + 0.5) / 20
	if n == last then
		return
	end
	last = n
	for _, l in lamps do
		l.light.Brightness = l.day + (l.night - l.day) * n
		if l.beam then
			l.beam.Transparency = NumberSequence.new({
				NumberSequenceKeypoint.new(0, 1 - 0.22 * n),
				NumberSequenceKeypoint.new(1, 1),
			})
		end
	end
end)
