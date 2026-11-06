-- Finishes the city's Blender buildings: Models under workspace.City.Buildings with
-- attribute LiveSyncAsset (made by tools/build_city_map.py).
-- In Studio the LiveSync plugin (v5+) already loads each mesh in edit mode; if a model
-- is still empty here (older plugin, or a fresh server) it is loaded now the same way.
-- Then parts are anchored, kept streamed in so the skyline shows from anywhere, and
-- named parts get their Roblox look:
--   Light*  glowing strips -> Neon, no texture
local InsertService = game:GetService("InsertService")

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

local function style(model: Model)
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
