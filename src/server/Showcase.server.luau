-- Shows new 3D models next to the spawn so they can be checked in play tests.
-- Models come from Roblox (ids in Shared.ModelIds, made by tools/upload_models.py).
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local ModelIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("ModelIds"))

-- Blender meters -> studs. Roblox characters are about 5 studs tall, so real sizes x3.6.
local SCALE = 3.6

-- What to show and where, relative to the spawn (spawn center, Y = floor).
local SHOWCASE = {
	{ Name = "Carbine", Offset = Vector3.new(5, 3.2, -3) },
	{ Name = "CarbineRifle", Offset = Vector3.new(-5, 3.2, -3) },
	{ Name = "ArmorVest", Offset = Vector3.new(0, 3.5, -7), Scale = 1 },
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
	model:ScaleTo(item.Scale or SCALE)
	model.Parent = folder
	local center = base + item.Offset
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
