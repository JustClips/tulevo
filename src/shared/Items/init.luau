--[[
	Item registry (shared by server and client): the one place every item is defined.

		local Items = require(ReplicatedStorage.Shared.Items)
		Items.get("Mead")        -> ItemDef
		Items.all()              -> { ItemDef }
		Items.useAction(def)     -> ActionDef?, the item's Use settings (Items/Actions.luau)
		Items.ammoFor("CarbineRifle") -> "RifleAmmo" (the ammo item a gun reloads from)

	Where items are written:
	  plain items  Items/Defs.luau            (food, kits, ammo, junk: one row each)
	  weapons      Shared/Weapons/Defs/*.luau (Weight, Cells, Model, Ammo, Description)
	  armor        Shared/Armor/init.luau     (Weight, Cells, Model, Description)
	Every item gets the same fields (ItemDef below), so the inventory, the ground, the quick
	slots and the server never need to know what kind of thing an item is.

	Use actions (eat, heal, take out, put on) are listed in Items/Actions.luau; the server
	runs them in Server/Inventory/ItemUse.luau.

	Inventory pictures: Shared.ItemIconIds[Id] (tools/item_icons/render.js renders the model at
	its Cells shape, tools/upload_icons.py --set items uploads it). Without one, the inventory
	shows the live 3D model from IconView / IconRoll, or the name.

	Mistakes in a definition (unknown Kind or action, Stack 0, missing Weight) stop the game
	with an error naming the item, so they show up on the first Play.
]]

local Shared = script.Parent
local Weapons = require(Shared:WaitForChild("Weapons"))
local Armor = require(Shared:WaitForChild("Armor"))
local Config = require(Shared:WaitForChild("Config"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local ItemIconIds = require(Shared:WaitForChild("ItemIconIds"))
local Actions = require(script:WaitForChild("Actions"))
local PlainDefs = require(script:WaitForChild("Defs"))

export type Kind = "Weapon" | "Armor" | "Consumable" | "Ammo" | "Misc"
export type UseDef = {
	Action: string, -- key in Items/Actions.luau
	Time: number?, -- seconds it takes (server actions); 0 / nil = instant
	Amount: number?, -- the action's number (HP healed...)
}
export type ItemDef = {
	Id: string,
	Name: string,
	Description: string?, -- one line under the name in the tooltip
	Kind: Kind,
	Weight: number, -- kg per item
	Cells: Vector2?, -- inventory cells it covers, wide x tall (default 1 x 1; R turns it while dragging)
	Stack: number, -- how many fit on one tile
	Model: string?, -- key in Shared.ModelIds
	ModelScale: number?, -- world size (dropped on the ground)
	Icon: string?, -- rbxassetid picture (filled in from Shared.ItemIconIds)
	-- inventory icon when there's no picture: the 3D model seen from IconView (a direction from
	-- the model's centre toward the camera, in model space), turned IconRoll degrees on screen
	IconView: Vector3?,
	IconRoll: number?,
	DropTilt: Vector3?, -- degrees (X, Y, Z) it's turned lying on the ground
	Use: UseDef?,
	Ammo: string?, -- weapons: the item id they reload from
}

local KINDS = { Weapon = true, Armor = true, Consumable = true, Ammo = true, Misc = true }

local Defs: { [string]: ItemDef } = {}

for id, row in PlainDefs do
	local def = table.clone(row) :: any
	def.Id = id
	Defs[id] = def
end

-- weapons: one per tile, the item fields from the weapon file
for _, w in Weapons.all() do
	local wd = w :: any
	assert(not Defs[w.Id], `item {w.Id}: a weapon and an item share this id`)
	Defs[w.Id] = {
		Id = w.Id,
		Name = w.Name,
		Description = wd.Description,
		Kind = "Weapon",
		Weight = w.Weight or 1,
		Stack = 1,
		Cells = w.Cells,
		Model = w.Model,
		ModelScale = Config.Weapons.GunScale or 1, -- exported in studs, shown like in the hand
		IconView = Vector3.new(1, 0.1, 0), -- side profile, muzzle to the right
		DropTilt = Vector3.new(0, 0, 90), -- on its side
		Use = { Action = "Equip" },
		Ammo = wd.Ammo,
	}
end

-- armor: the item fields from Shared/Armor
for id, a in Armor.Defs do
	local ad = a :: any
	assert(not Defs[id], `item {id}: armor and an item share this id`)
	Defs[id] = {
		Id = id,
		Name = ad.DisplayName or "Armor vest",
		Description = ad.Description,
		Kind = "Armor",
		Weight = a.Weight or 5,
		Cells = a.Cells,
		Stack = 1,
		Model = a.Model,
		ModelScale = 1, -- exported in studs
		IconView = Vector3.new(0.25, 0.15, -1), -- from the front (the vest faces -Z)
		DropTilt = Vector3.new(90, 0, 0), -- on its back
		Use = { Action = "Wear" },
	}
end

-- fill in pictures, check every definition
for id, def in Defs do
	local function bad(why: string)
		error(`Shared/Items: item {id}: {why}`, 0)
	end
	if typeof(def.Name) ~= "string" or def.Name == "" then
		bad("needs a Name")
	end
	if not KINDS[def.Kind] then
		bad(`Kind "{tostring(def.Kind)}" isn't one of Weapon, Armor, Consumable, Ammo, Misc`)
	end
	if typeof(def.Weight) ~= "number" or def.Weight < 0 then
		bad("needs a Weight in kg (0 or more)")
	end
	if typeof(def.Stack) ~= "number" or def.Stack < 1 or def.Stack % 1 ~= 0 then
		bad("Stack must be a whole number, 1 or more")
	end
	if def.Cells ~= nil and (typeof(def.Cells) ~= "Vector2" or def.Cells.X < 1 or def.Cells.Y < 1) then
		bad("Cells must be Vector2.new(wide, tall), at least 1 x 1")
	end
	if def.Use then
		if not Actions[def.Use.Action] then
			bad(`Use.Action "{tostring(def.Use.Action)}" isn't in Items/Actions.luau`)
		end
	end
	if def.Model and (ModelIds :: any)[def.Model] == nil then
		warn(`Shared/Items: item {id}: Model "{def.Model}" isn't in Shared.ModelIds yet (shown as a box)`)
	end
	def.Icon = def.Icon or (ItemIconIds :: any)[id]
end
for id, def in Defs do
	if def.Ammo and not (Defs[def.Ammo] and Defs[def.Ammo].Kind == "Ammo") then
		error(`Shared/Items: weapon {id}: Ammo "{def.Ammo}" isn't an Ammo item in Items/Defs.luau`, 0)
	end
end

local Items = {}
Items.Defs = Defs
Items.Actions = Actions

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

-- The item's use action (Items/Actions.luau), or nil if it can't be used.
function Items.useAction(def: ItemDef?): Actions.ActionDef?
	return if def and def.Use then Actions[def.Use.Action] else nil
end

-- The ammo item a weapon reloads from (nil: it keeps its own spare bullets).
function Items.ammoFor(weaponId: string?): string?
	local def = weaponId and Defs[weaponId]
	return def and def.Ammo or nil
end

return Items
