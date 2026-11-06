--[[
	Every plain item in the game (food, drinks, kits, ammo, junk). Weapons and armor are items
	too, but their item fields live in their own files (Shared/Weapons/Defs/*.luau,
	Shared/Armor/init.luau) so each thing is configured in one place; Items/init.luau merges
	them in.

	Adding an item = adding a row here:

		Bandage = {
			Name = "Bandage",
			Description = "Stops the bleeding. Heals 15 HP.",
			Kind = "Consumable",        -- Consumable | Ammo | Misc (Weapon / Armor come from their files)
			Weight = 0.1,               -- kg per item
			Cells = Vector2.new(1, 1),  -- inventory cells, wide x tall (default 1 x 1)
			Stack = 10,                 -- how many fit on one tile
			Model = "Bandage",          -- key in Shared.ModelIds (optional: no model = a small box on the ground)
			ModelScale = 3.6,           -- props exported in meters use 3.6
			Use = { Action = "Heal", Amount = 15, Time = 2, Anim = "Tulevo_Medkit" }, -- optional, see Items/Actions.luau
		},

	Use.Anim = a clip in Shared.AnimIds played while it's used (stretched to Use.Time). While it
	plays the item's model is held in the hand: where exactly comes from Items/Holds.luau
	(made by art/anim/use_items.py, which also makes the clips).

	The inventory picture comes from Shared.ItemIconIds[Id] (tools/item_icons/render.js renders
	the model, tools/upload_icons.py --set items uploads it). Until there is one the 3D model is
	shown, or the name.
]]

return {
	Mead = {
		Name = "Mead",
		Description = "Sweet honey wine. Heals 5 HP.",
		Kind = "Consumable",
		Weight = 0.6,
		Cells = Vector2.new(1, 2),
		Stack = 5,
		Model = "Mead",
		ModelScale = 3.6,
		IconView = Vector3.new(0.3, 0.25, -1),
		Use = { Action = "Drink", Amount = 5, Time = 2, Anim = "Tulevo_DrinkBottle" },
	},
	Chaser = {
		Name = "Chaser",
		Description = "A cold can to wash it down. Heals 3 HP.",
		Kind = "Consumable",
		Weight = 0.35,
		Cells = Vector2.new(1, 2),
		Stack = 5,
		Model = "Chaser",
		ModelScale = 3.6,
		IconView = Vector3.new(0.3, 0.25, -1),
		Use = { Action = "Drink", Amount = 3, Time = 1.5, Anim = "Tulevo_DrinkCan" },
	},
	FirstAidKit = {
		Name = "First-aid kit",
		Description = "Patches you up. Heals 40 HP.",
		Kind = "Consumable",
		Weight = 0.8,
		Cells = Vector2.new(2, 2),
		Stack = 3,
		Model = "FirstAidKit",
		ModelScale = 3.6,
		IconView = Vector3.new(0.45, 0.55, -1),
		Use = { Action = "Heal", Amount = 40, Time = 4, Anim = "Tulevo_Medkit" },
	},
	RifleAmmo = {
		Name = "Rifle ammo",
		Description = "5.56 rounds. Rifles reload from these.",
		Kind = "Ammo",
		Weight = 0.012,
		Cells = Vector2.new(1, 1),
		Stack = 90,
	},
}
