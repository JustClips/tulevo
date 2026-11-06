--[[
	The one place damage is dealt. Weapons (and anything else that hurts players) call
	Damage.apply instead of Humanoid:TakeDamage so armor is counted. Server only: the amount
	always comes from server data (weapon defs), never from a client.

	Damage.apply(humanoid, amount, partName?) -> (healthDamage, armorDamage)
	  partName is the body part that was hit (nil = unknown, treated as covered).
	Damage.setArmor(humanoid, itemName) gives a fresh armor item (full armor).
	Damage.addArmor(humanoid, amount) tops armor up, capped at MaxArmor.
]]

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Armor = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Armor"))

local Damage = {}

local function hasForceField(humanoid: Humanoid): boolean
	local character = humanoid.Parent
	return character ~= nil and character:FindFirstChildOfClass("ForceField") ~= nil
end

function Damage.getArmor(humanoid: Humanoid): (number, number)
	return humanoid:GetAttribute("Armor") or 0, humanoid:GetAttribute("MaxArmor") or 0
end

function Damage.setArmor(humanoid: Humanoid, itemName: string?)
	local def = Armor.get(itemName)
	humanoid:SetAttribute("ArmorItem", if def then def.Name else nil)
	humanoid:SetAttribute("MaxArmor", if def then def.MaxArmor else 0)
	humanoid:SetAttribute("Armor", if def then def.MaxArmor else 0)
end

function Damage.addArmor(humanoid: Humanoid, amount: number)
	local armor, max = Damage.getArmor(humanoid)
	humanoid:SetAttribute("Armor", math.clamp(armor + amount, 0, max))
end

function Damage.apply(humanoid: Humanoid, amount: number, partName: string?): (number, number)
	if
		typeof(amount) ~= "number"
		or amount ~= amount
		or amount <= 0
		or humanoid.Health <= 0
		or hasForceField(humanoid)
	then
		return 0, 0
	end
	local armorDamage = 0
	local armor = humanoid:GetAttribute("Armor") or 0
	local def = Armor.get(humanoid:GetAttribute("ArmorItem"))
	local covered = def ~= nil and not (partName and def.Unprotected and def.Unprotected[partName])
	if armor > 0 and covered and def then
		armorDamage = math.min(armor, amount * (def.Absorb or 1))
		humanoid:SetAttribute("Armor", armor - armorDamage)
	end
	local healthDamage = amount - armorDamage
	if healthDamage > 0 then
		humanoid:TakeDamage(healthDamage)
	end
	return healthDamage, armorDamage
end

return Damage
