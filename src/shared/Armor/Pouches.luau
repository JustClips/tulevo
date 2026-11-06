--[[
	Rifle mag pouches on the vest front (art/models/ArmorVest: MagFlap1-3 lids, PouchMag1-3
	mag tops sticking out of the pouches under the lids).

	A rifle reload takes the next mag from them: the left hand flicks the lid open (it stays
	open), pulls the mag out and pushes it into the gun (Weapon_Rifle_ReloadPouch<k>, or
	...Open when that lid is open already; Server/Weapons/GunModel moves the parts on the
	clip's beats). Only pouches 1 (wearer's left) and 2 (centre) are used: pouch 3, on the
	wearer's right, is out of reach of the blocky left arm (art/anim/gun.py RELOAD_POUCHES).

	State lives on the worn vest model (character.ArmorVest), set by the server:
	  NextPouch  number  pouch the next reload uses (Order[1] if unset)
	  Open<k>    bool    lid k is open
	  Taken<k>   bool    the mag in pouch k has been taken out
	A fresh vest (spawning, putting it back on) has every lid shut and every pouch full. After
	both pouches are used the reloads go round them again (the pouches count as refilled).
]]

local Pouches = {}

Pouches.Order = { 1, 2 }

-- Does this weapon class reload from the vest pouches? (it has the clips for it)
function Pouches.forClass(class): boolean
	return class ~= nil and table.find(class.Anims, "ReloadPouch1") ~= nil
end

-- The pouch the next reload takes from: (k, lid already open), or nil when the character
-- has no vest with pouches.
function Pouches.next(character: Model): (number?, boolean)
	local vest = character:FindFirstChild("ArmorVest")
	if not vest then
		return nil, false
	end
	local k = vest:GetAttribute("NextPouch")
	if typeof(k) ~= "number" or not table.find(Pouches.Order, k) then
		k = Pouches.Order[1]
	end
	if not (vest:FindFirstChild(`MagFlap{k}`, true) and vest:FindFirstChild(`PouchMag{k}`, true)) then
		return nil, false -- an older vest model without separate pouch parts
	end
	return k, vest:GetAttribute(`Open{k}`) == true
end

-- The pouch after k.
function Pouches.after(k: number): number
	local i = table.find(Pouches.Order, k) or 0
	return Pouches.Order[i % #Pouches.Order + 1]
end

-- Weapon_<Class>_<slot> clip for this character's next reload.
function Pouches.reloadSlot(character: Model, class): string
	if not Pouches.forClass(class) then
		return "Reload"
	end
	local k, open = Pouches.next(character)
	if not k then
		return "Reload"
	end
	return `ReloadPouch{k}{if open then "Open" else ""}`
end

return Pouches
