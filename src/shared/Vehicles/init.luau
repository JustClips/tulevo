--[[
	Vehicle registry (shared by server and client). Data only.

	Every vehicle is one module in Vehicles/Defs: size, wheels, suspension, engine, grip.
	The same driving code (Vehicles/Physics) runs every vehicle, so a new car is a new Def
	file plus, later, its own model (docs/vehicles.md).

		local Vehicles = require(ReplicatedStorage.Shared.Vehicles)
		Vehicles.get("Sedan")   -> VehicleDef
		Vehicles.all()          -> { VehicleDef }
		Vehicles.TAG            -- CollectionService tag on every spawned vehicle model
]]

local Vehicles = {}

Vehicles.TAG = "Vehicle"
Vehicles.WHEELS = { "FL", "FR", "RL", "RR" } -- front-left, front-right, rear-left, rear-right

local byId = {}
for _, mod in script:WaitForChild("Defs"):GetChildren() do
	if mod:IsA("ModuleScript") then
		local def = require(mod)
		assert(def.Id and not byId[def.Id], `vehicle {mod.Name}: missing or duplicate Id`)
		byId[def.Id] = def
	end
end

function Vehicles.get(id: string)
	return byId[id]
end

function Vehicles.all()
	local out = {}
	for _, def in byId do
		table.insert(out, def)
	end
	return out
end

-- The vehicle model a part belongs to (or nil).
function Vehicles.modelOf(inst: Instance?): Model?
	while inst and inst ~= workspace do
		if inst:IsA("Model") and inst:GetAttribute("VehicleId") then
			return inst
		end
		inst = inst.Parent
	end
	return nil
end

return Vehicles
