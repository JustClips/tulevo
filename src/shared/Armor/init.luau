--[[
	Armor items. GTA 5 style: armor is not a second health bar. While a player has armor,
	every weapon hit (any body part, headshots too) is split: Absorb share comes off the
	armor, the rest still hits health. Once the armor is empty, hits go fully to health.
	Unprotected can list body parts an item does not cover; the vest covers everything.

	Armor lives on the Humanoid as attributes so the client HUD can read it:
	  Armor (current), MaxArmor, ArmorItem (def name).
	The server owns them; see Server/Damage.luau.
]]

export type ArmorDef = {
	Name: string,
	MaxArmor: number, -- armor points when freshly worn
	Weight: number, -- kg in the inventory (Shared/Items)
	Model: string?, -- key in Shared.ModelIds for the worn model
	Absorb: number?, -- share of each hit the armor takes, the rest goes to health (default 1)
	Unprotected: { [string]: boolean }?, -- body parts the armor does not cover
}

local Defs: { [string]: ArmorDef } = {
	ArmorVest = {
		Name = "ArmorVest",
		MaxArmor = 50,
		Weight = 5, -- kg in the inventory
		Model = "ArmorVest",
		Absorb = 0.7, -- 70% of each hit drains armor, 30% still hurts health
	},
}

local Armor = {}
Armor.Defs = Defs
Armor.Default = "ArmorVest" -- worn on spawn

function Armor.get(name: string?): ArmorDef?
	return if name then Defs[name] else nil
end

return Armor
