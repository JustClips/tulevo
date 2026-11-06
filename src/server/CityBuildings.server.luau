-- Places the city's Blender buildings listed in Shared.CityLayout.
-- Parts are anchored, tagged Building for the radar/full map, and kept streamed in
-- so the skyline shows from anywhere. Part-name rules give the right look in Roblox:
--   Light*  glowing strips -> Neon, no texture
--   *Glass  keep the PBR texture (metal/rough makes the reflections), no shadows inside
local CollectionService = game:GetService("CollectionService")
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local CityLayout = require(Shared:WaitForChild("CityLayout"))

local folder = workspace:FindFirstChild("CityBuildings") or Instance.new("Folder")
folder.Name = "CityBuildings"
folder.Parent = workspace

local function styleParts(model: Model)
	for _, d in model:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
			if d.Name:match("^Light") then
				for _, c in d:GetChildren() do
					if c:IsA("SurfaceAppearance") then
						c:Destroy()
					end
				end
				if d:IsA("MeshPart") then
					d.TextureID = ""
				end
				d.Material = Enum.Material.Neon
				d.Color = Color3.fromRGB(225, 238, 255)
				d.CastShadow = false
				d.CanCollide = false
			elseif d.Name:match("Glass$") then
				d.CastShadow = true
			end
		end
	end
end

for _, entry in CityLayout do
	local id = ModelIds[entry.Model]
	if not id then
		warn(`[City] {entry.Name}: model {entry.Model} is not uploaded yet`)
		continue
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[City] could not load {entry.Name} ({id}): {container}`)
		continue
	end
	local model = Instance.new("Model")
	model.Name = entry.Name
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	styleParts(model)
	if entry.Scale and entry.Scale ~= 1 then
		model:ScaleTo(entry.Scale)
	end
	-- move so the bounding-box centre sits where the Blender origin + BoxCenter should be
	local turn = CFrame.Angles(0, math.rad(entry.Yaw or 0), 0)
	local box = model:GetBoundingBox()
	local want = CFrame.new(entry.At) * turn * CFrame.new(entry.BoxCenter * (entry.Scale or 1))
	model:PivotTo(want * box:ToObjectSpace(model:GetPivot()))
	model.ModelStreamingMode = Enum.ModelStreamingMode.Persistent
	CollectionService:AddTag(model, "Building")
	model.Parent = folder
	print(`[City] {entry.Name} placed`)
end
