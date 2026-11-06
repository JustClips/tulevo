--[[
	What "using" an item does. An item opts in with Use = { Action = "<name>", ... } in its
	definition (Items/Defs.luau, or a weapon / armor file). The extra fields are the action's
	settings (Amount, Time...).

	Label: shown in the tooltip ("Right-click: Drink").
	Client: done on the player's own client (drawing a gun, the vest animation). Everything
	else is done by the server (Server/Inventory/ItemUse.luau has one function per action),
	which takes one of the item when the use finishes.

	Time (seconds) on any server action = how long it takes; a bar shows it, and it is
	cancelled if you get knocked down or the item leaves your bag. 0 / missing = instant.

	Adding an action: add a row here, and (unless Client) a function with the same name in
	Server/Inventory/ItemUse.luau.
]]

export type ActionDef = {
	Label: string,
	Client: boolean?,
}

return {
	Heal = { Label = "Use" }, -- Amount = HP back, refused at full health
	Drink = { Label = "Drink" }, -- Amount = HP back (works at full health too)
	Equip = { Label = "Take out", Client = true }, -- weapons: in your hands / on your back
	Wear = { Label = "Put on", Client = true }, -- armor: the vest animation
} :: { [string]: ActionDef }
