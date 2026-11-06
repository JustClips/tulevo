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
-- Lamps get brighter and the light shafts show up as the in-game clock goes into night.
local InsertService = game:GetService("InsertService")
local Lighting = game:GetService("Lighting")
local RunService = game:GetService("RunService")

local LAMP_COLOR = Color3.fromRGB(255, 244, 222)
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

local function style(model: Model)
	for _, d in model:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
			if d.Name:match("^Light") then
				neon(d)
			elseif d.Name:match("^Lamp%d") then
				neon(d)
				downLight(d, 26, 0.6, 3)
				lightShaft(d, model)
			elseif d.Name == "ShopLamp" then
				neon(d)
				downLight(d, 16, 0.4, 2)
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
