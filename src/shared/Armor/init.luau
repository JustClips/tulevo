--[[
	Armor items. GTA 5 style: while a player has armor, every weapon hit (any body part,
	headshots too) takes armor first and only the leftover goes to health.
	Unprotected can list body parts an item does not cover; the vest covers everything.

	Armor lives on the Humanoid as attributes so the client HUD can read it:
	  Armor (current), MaxArmor, ArmorItem (def name).
	The server owns them; see Server/Damage.luau.
]]

export type ArmorDef = {
	Name: string,
	MaxArmor: number, -- armor points when freshly worn
	Model: string?, -- key in Shared.ModelIds for the worn model
	Absorb: number?, -- share of a covered hit the armor takes (1 = all of it), default 1
	Unprotected: { [string]: boolean }?, -- body parts the armor does not cover
}

local Defs: { [string]: ArmorDef } = {
	ArmorVest = {
		Name = "ArmorVest",
		MaxArmor = 50,
		Model = "ArmorVest",
		Absorb = 1,
	},
}

local Armor = {}
Armor.Defs = Defs
Armor.Default = "ArmorVest" -- worn on spawn

function Armor.get(name: string?): ArmorDef?
	return if name then Defs[name] else nil
end

return Armor
