--[[
	Weapon registry (shared by server and client). Data only, no behaviour.

	Every weapon is one module in Weapons/Defs. A weapon belongs to a Class
	(Weapons/Classes.luau), and the class decides the wheel slot, how it's held and
	which animations it needs, so ten rifles share one rifle animation set.

		local Weapons = require(ReplicatedStorage.Shared.Weapons)
		Weapons.get("Pistol")      -> WeaponDef (with .Class filled in)
		Weapons.classOf("Pistol")  -> ClassDef
		Weapons.all()              -> { WeaponDef }

	Adding a weapon: copy a file in Defs, change Id/Name/stats. Adding a class: add it to
	Classes.luau and make its animations (docs/weapons.md lists them).
]]

local Types = require(script:WaitForChild("Types"))
local Classes = require(script:WaitForChild("Classes"))

export type WeaponDef = Types.WeaponDef
export type ClassDef = Types.ClassDef

local Weapons = {}

local byId: { [string]: Types.WeaponDef } = {}
for _, mod in script:WaitForChild("Defs"):GetChildren() do
	if mod:IsA("ModuleScript") then
		local def = require(mod) :: Types.WeaponDef
		assert(def.Id and not byId[def.Id], `weapon {mod.Name}: missing or duplicate Id`)
		assert(Classes[def.ClassName], `weapon {def.Id}: unknown class {def.ClassName}`)
		def.Class = Classes[def.ClassName]
		byId[def.Id] = def
	end
end

function Weapons.get(id: string): Types.WeaponDef?
	return byId[id]
end

function Weapons.classOf(id: string): Types.ClassDef?
	local def = byId[id]
	return def and def.Class
end

function Weapons.all(): { Types.WeaponDef }
	local list = {}
	for _, def in byId do
		table.insert(list, def)
	end
	table.sort(list, function(a, b)
		return a.Id < b.Id
	end)
	return list
end

Weapons.Classes = Classes

return Weapons
