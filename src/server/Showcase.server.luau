-- Shows new 3D models next to the spawn so they can be checked in play tests.
-- Models come from Roblox (ids in Shared.ModelIds, made by tools/upload_models.py).
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local ModelIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ModelIds"))
local TextureIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("TextureIds"))

-- Superbike wheel paint (part name -> look); the tyres get their colour map from TextureIds.
local BIKE_WHEEL_LOOKS = {
	Tyre = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic },
	Rim = { Color = Color3.fromRGB(24, 24, 26), Material = Enum.Material.SmoothPlastic, Reflectance = 0.06 },
	Valve = { Color = Color3.fromRGB(168, 170, 176), Material = Enum.Material.SmoothPlastic, Reflectance = 0.2 },
	Rotor = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.12 },
	Carrier = { Color = Color3.fromRGB(62, 64, 68), Material = Enum.Material.SmoothPlastic, Reflectance = 0.08 },
	Caliper = { Color = Color3.fromRGB(32, 74, 168), Material = Enum.Material.SmoothPlastic, Reflectance = 0.05 },
	Pad = { Color = Color3.fromRGB(46, 43, 40), Material = Enum.Material.SmoothPlastic },
	Bracket = { Color = Color3.fromRGB(56, 58, 62), Material = Enum.Material.SmoothPlastic, Reflectance = 0.05 },
	Sprocket = { Color = Color3.fromRGB(38, 38, 40), Material = Enum.Material.SmoothPlastic, Reflectance = 0.06 },
}

-- Superbike exhaust paint; the pipes, silencer and carbon shield get colour maps from TextureIds.
local BIKE_EXHAUST_LOOKS = {
	Headers = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.1 },
	Collector = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.1 },
	PreSilencer = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.08 },
	LinkPipe = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.1 },
	Silencer = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.12 },
	HeatShield = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.05 },
	EndCap = { Color = Color3.fromRGB(30, 30, 33), Material = Enum.Material.SmoothPlastic },
	Hardware = { Color = Color3.fromRGB(165, 168, 174), Material = Enum.Material.SmoothPlastic, Reflectance = 0.15 },
	Valve = { Color = Color3.fromRGB(38, 38, 42), Material = Enum.Material.SmoothPlastic },
	Sensors = { Color = Color3.fromRGB(110, 110, 116), Material = Enum.Material.SmoothPlastic },
}

-- Superbike chain paint; the plates get their brushed, oily colour maps from TextureIds.
local BIKE_CHAIN_LOOKS = {
	OuterPlates = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.1 },
	InnerPlates = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.05 },
	Rollers = { Color = Color3.fromRGB(92, 92, 96), Material = Enum.Material.SmoothPlastic, Reflectance = 0.06 },
	Pins = { Color = Color3.fromRGB(178, 180, 186), Material = Enum.Material.SmoothPlastic, Reflectance = 0.15 },
	Seals = { Color = Color3.fromRGB(24, 24, 26), Material = Enum.Material.SmoothPlastic },
	FrontSprocket = { Color = Color3.fromRGB(118, 119, 124), Material = Enum.Material.SmoothPlastic, Reflectance = 0.08 },
	SprocketNut = { Color = Color3.fromRGB(160, 162, 168), Material = Enum.Material.SmoothPlastic, Reflectance = 0.12 },
}

-- Superbike seats: leather colour maps (grain, perforated pleats, stitching) come from TextureIds.
local BIKE_SEAT_LOOKS = {
	RiderTop = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.02 },
	RiderSides = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.02 },
	PillionTop = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.02 },
	PillionSides = { Color = Color3.fromRGB(255, 255, 255), Material = Enum.Material.SmoothPlastic, Reflectance = 0.02 },
	RiderPiping = { Color = Color3.fromRGB(30, 30, 32), Material = Enum.Material.SmoothPlastic, Reflectance = 0.03 },
	PillionPiping = { Color = Color3.fromRGB(30, 30, 32), Material = Enum.Material.SmoothPlastic, Reflectance = 0.03 },
	RiderBase = { Color = Color3.fromRGB(20, 20, 22), Material = Enum.Material.SmoothPlastic },
	PillionBase = { Color = Color3.fromRGB(20, 20, 22), Material = Enum.Material.SmoothPlastic },
	SeatLatch = { Color = Color3.fromRGB(160, 162, 168), Material = Enum.Material.SmoothPlastic, Reflectance = 0.12 },
}

-- Blender meters -> studs. Roblox characters are about 5 studs tall, so real sizes x3.6.
local SCALE = 3.6

-- What to show and where, relative to the spawn (spawn center, Y = floor).
local SHOWCASE = {
	{ Name = "Carbine", Offset = Vector3.new(5, 3.2, -3) },
	{ Name = "CarbineRifle", Offset = Vector3.new(-5, 3.2, -3), Scale = 1 }, -- exported in studs
	{ Name = "ArmorVest", Offset = Vector3.new(0, 3.5, -7), Scale = 1 },
	{ Name = "Mead", Offset = Vector3.new(-3, 2.6, -7) },
	{ Name = "Chaser", Offset = Vector3.new(-4.5, 2.6, -7) },
	{ Name = "FirstAidKit", Offset = Vector3.new(3.2, 2.6, -7) },
	-- Realistic human test (static posed mesh, built in studs). Stands on the floor, faces the spawn.
	{ Name = "Human", Offset = Vector3.new(9, 0, 6), Scale = 1, Stand = true, Yaw = 225 },
	-- Superbike wheels (art/blender/superbike/wheels.py), built in studs.
	{ Name = "BikeWheelFront", Offset = Vector3.new(-9, 2.6, 2), Scale = 1, Looks = BIKE_WHEEL_LOOKS },
	{ Name = "BikeWheelRear", Offset = Vector3.new(-9, 2.6, 6), Scale = 1, Looks = BIKE_WHEEL_LOOKS },
	-- Superbike exhaust (art/blender/superbike/exhaust.py), headers to silencer, built in studs.
	{ Name = "BikeExhaust", Offset = Vector3.new(-9, 2.8, 10.5), Scale = 1, Looks = BIKE_EXHAUST_LOOKS },
	-- Superbike drive chain, 116 links + front sprocket (art/blender/superbike/chain.py), built in studs.
	{ Name = "BikeChain", Offset = Vector3.new(-9, 2.6, 14.5), Scale = 1, Looks = BIKE_CHAIN_LOOKS },
	-- Superbike rider + passenger seats (art/blender/superbike/seats.py), built in studs.
	{ Name = "BikeSeats", Offset = Vector3.new(-9, 2.6, 18.5), Scale = 1, Looks = BIKE_SEAT_LOOKS },
}

local function findSpawn(): BasePart?
	local spawn = workspace:FindFirstChild("Spawn", true)
	if spawn and spawn:IsA("BasePart") then
		return spawn
	end
	return workspace:FindFirstChildWhichIsA("SpawnLocation", true)
end

local folder = Instance.new("Folder")
folder.Name = "Showcase"
folder.Parent = workspace

local spinning = {}

local spawnPart = findSpawn()
local base = spawnPart and (spawnPart.Position - Vector3.new(0, spawnPart.Size.Y / 2, 0)) or Vector3.zero

for _, item in SHOWCASE do
	local id = ModelIds[item.Name]
	if not id then
		continue -- not uploaded yet
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[Showcase] could not load {item.Name} ({id}): {container}`)
		continue
	end
	local model = Instance.new("Model")
	model.Name = item.Name
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CastShadow = true
		elseif d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		end
	end
	local textures = TextureIds[item.Name]
	for _, d in model:GetDescendants() do
		if d:IsA("MeshPart") then
			-- front-wheel parts come in pairs (RotorL / RotorR ...): look them up without the side letter
			local look = item.Looks and (item.Looks[d.Name] or item.Looks[(string.gsub(d.Name, "[LR]$", ""))])
			if look then
				d.Color = look.Color
				d.Material = look.Material
				d.Reflectance = look.Reflectance or 0
			end
			if textures and textures[d.Name] then
				d.TextureID = `rbxassetid://{textures[d.Name]}`
			end
		end
	end
	model:ScaleTo(item.Scale or SCALE)
	model.Parent = folder
	local center = base + item.Offset
	if item.Stand then
		-- No spin: turn to Yaw and put the feet on the floor.
		model:PivotTo(CFrame.new(center) * CFrame.Angles(0, math.rad(item.Yaw or 0), 0))
		local boxCf, size = model:GetBoundingBox()
		model:PivotTo(model:GetPivot() + Vector3.new(0, center.Y - (boxCf.Position.Y - size.Y / 2), 0))
		for _, d in model:GetDescendants() do
			if d:IsA("BasePart") then
				d.CanCollide = true
				d.CanQuery = true
			end
		end
		print(`[Showcase] {item.Name} standing next to the spawn`)
		continue
	end
	model:PivotTo(CFrame.new(center))
	-- Rotate around the bounding box center, not the import pivot.
	local boxCf = model:GetBoundingBox()
	table.insert(spinning, { Model = model, Center = center, Fix = boxCf:ToObjectSpace(model:GetPivot()) })
	print(`[Showcase] {item.Name} placed next to the spawn`)
end

local angle = 0
RunService.Heartbeat:Connect(function(dt)
	angle += dt * 0.6
	for _, s in spinning do
		s.Model:PivotTo(CFrame.new(s.Center) * CFrame.Angles(0, angle, 0) * s.Fix)
	end
end)
