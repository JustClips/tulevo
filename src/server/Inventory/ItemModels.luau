--[[
	3D models of every item (Shared/Items), loaded once on the server and put in
	ReplicatedStorage.ItemModels (one Model per item id), so:
	  - clients draw inventory icons from them (ViewportFrames, Client/Inventory)
	  - dropped items on the ground are clones of them (Server/Inventory/InventoryService)

	Each model is scaled to its item's ModelScale (world size), anchored, with no collisions,
	and its pivot is the centre of its bounding box.
]]

local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local Items = require(Shared:WaitForChild("Items"))

local folder = Instance.new("Folder")
folder.Name = "ItemModels"
folder.Parent = ReplicatedStorage

local ItemModels = {}

local loading: { [string]: boolean } = {}

local function build(id: string): Model?
	local def = Items.get(id)
	local assetId = def and def.Model and ModelIds[def.Model]
	if not def or not assetId then
		return nil
	end
	local ok, container = pcall(InsertService.LoadAsset, InsertService, assetId)
	if not ok then
		warn(`[ItemModels] could not load {id} ({assetId}): {container}`)
		return nil
	end
	local model = Instance.new("Model")
	model.Name = id
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanTouch = false
			d.CanQuery = true
			d.CastShadow = true
		elseif
			d:IsA("Script")
			or d:IsA("LocalScript")
			or d:IsA("JointInstance")
			or d:IsA("WeldConstraint")
			or d:IsA("ProximityPrompt")
		then
			d:Destroy()
		end
	end
	local box = model:GetBoundingBox()
	model.WorldPivot = box
	local scale = def.ModelScale or 1
	if scale ~= 1 then
		model:ScaleTo(scale)
	end
	return model
end

-- The model for an item (nil if it has none or it failed to load). Yields the first time.
function ItemModels.get(id: string): Model?
	while loading[id] do
		task.wait()
	end
	local m = folder:FindFirstChild(id)
	if m then
		return m :: Model
	end
	loading[id] = true
	local ok, model = pcall(build, id)
	loading[id] = nil
	if not ok then
		warn(`[ItemModels] {id}: {model}`)
		return nil
	end
	if model then
		model.Parent = folder
	end
	return model
end

function ItemModels.loadAll()
	for _, def in Items.all() do
		if def.Model then
			task.spawn(ItemModels.get, def.Id)
		end
	end
end

return ItemModels
