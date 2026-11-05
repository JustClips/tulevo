--[[
	Item registry (shared by server and client): everything that can sit in the inventory.

		local Items = require(ReplicatedStorage.Shared.Items)
		Items.get("Mead")   -> ItemDef
		Items.all()         -> { ItemDef }

	Every item has a Weight in kg; the inventory and the backpack have weight limits
	(Config.Inventory). Weapons and armor are items too, and their weight lives in their own
	files so each thing is configured in one place:
	  weapons  Shared/Weapons/Defs/*.luau  (Weight = ...)
	  armor    Shared/Armor/init.luau      (Weight = ...)
	  the rest Defs below

	Every item also has Cells = Vector2.new(wide, tall): how many inventory cells it covers
	(vest 2 x 2, carbine 4 x 2; R turns an item while you drag it). Missing = 1 x 1.
	Items/Grid.luau does the placing maths.

	Adding an item: add a row to Defs (Model = its key in Shared.ModelIds, ModelScale = how big
	it's shown in the world: props exported in meters use 3.6).
]]

local Shared = script.Parent
local Weapons = require(Shared:WaitForChild("Weapons"))
local Armor = require(Shared:WaitForChild("Armor"))
local Config = require(Shared:WaitForChild("Config"))

export type ItemDef = {
	Id: string,
	Name: string,
	Kind: "Weapon" | "Armor" | "Consumable" | "Misc",
	Weight: number, -- kg per item
	Cells: Vector2?, -- inventory cells it covers, wide x tall (default 1 x 1; R turns it while dragging)
	Stack: number, -- how many fit in one slot
	Model: string?, -- key in Shared.ModelIds
	ModelScale: number?, -- world size (dropped on the ground)
	-- inventory icon: the 3D model seen from IconView (a direction from the model's centre
	-- toward the camera, in model space), turned IconRoll degrees on screen
	IconView: Vector3?,
	IconRoll: number?,
}

local Defs: { [string]: ItemDef } = {
	Mead = {
		Id = "Mead",
		Name = "Mead",
		Kind = "Consumable",
		Weight = 0.6,
		Cells = Vector2.new(1, 1),
		Stack = 5,
		Model = "Mead",
		ModelScale = 3.6,
		IconView = Vector3.new(0.3, 0.25, -1),
	},
	Chaser = {
		Id = "Chaser",
		Name = "Chaser",
		Kind = "Consumable",
		Weight = 0.35,
		Cells = Vector2.new(1, 1),
		Stack = 5,
		Model = "Chaser",
		ModelScale = 3.6,
		IconView = Vector3.new(0.3, 0.25, -1),
	},
	FirstAidKit = {
		Id = "FirstAidKit",
		Name = "First-aid kit",
		Kind = "Consumable",
		Weight = 0.8,
		Cells = Vector2.new(1, 1),
		Stack = 3,
		Model = "FirstAidKit",
		ModelScale = 3.6,
		IconView = Vector3.new(0.45, 0.55, -1),
	},
}

-- weapons: one per slot, their weight from the weapon file
for _, w in Weapons.all() do
	Defs[w.Id] = {
		Id = w.Id,
		Name = w.Name,
		Kind = "Weapon",
		Weight = w.Weight or 1,
		Stack = 1,
		Cells = w.Cells,
		Model = w.Model,
		ModelScale = Config.Weapons.GunScale or 1, -- exported in studs, shown like in the hand
		IconView = Vector3.new(1, 0.1, 0), -- side profile, muzzle to the right
	}
end

-- armor: weight from Shared/Armor
for id, a in Armor.Defs do
	Defs[id] = {
		Id = id,
		Name = "Armor vest",
		Kind = "Armor",
		Weight = a.Weight or 5,
		Cells = a.Cells,
		Stack = 1,
		Model = a.Model,
		ModelScale = 1, -- exported in studs
		IconView = Vector3.new(0.25, 0.15, -1), -- from the front (the vest faces -Z)
	}
end

local Items = {}
Items.Defs = Defs

function Items.get(id: string?): ItemDef?
	return if id then Defs[id] else nil
end

function Items.all(): { ItemDef }
	local list = {}
	for _, def in Defs do
		table.insert(list, def)
	end
	table.sort(list, function(a, b)
		return a.Id < b.Id
	end)
	return list
end

return Items
