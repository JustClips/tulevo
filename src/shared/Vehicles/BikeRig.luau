--[[
	Where a bike's moving parts hinge, in chassis space (studs), from its Def.Rig (Blender meters).
	Server/Vehicles/BikeBuilder welds the model on these points and Client/Vehicles/Bike moves
	the welds around them, so both must use this.

		local p = BikeRig.points(def)
		p.Hinge, p.Axis        steering axis (a point on it at the ground, unit direction up the axis)
		p.FrontAxle, p.RearAxle, p.SwingPivot, p.StandPivot, p.Seat

	Weld chain the builder makes (each "Root" is an invisible massless part):
		Chassis -Lean-> BodyRoot -Steer-> SteerRoot -Fork-> ForkRoot -Spin-> FrontHub
		                BodyRoot -Swing-> SwingRoot -Spin-> RearHub
		                BodyRoot -Stand-> StandRoot
]]

local BikeRig = {}

-- Blender meters (X = bike's left, Y = back, Z = up) -> chassis space studs.
function BikeRig.toCar(rig, v: Vector3): Vector3
	return Vector3.new(-v.X, v.Z, v.Y) * rig.Scale + Vector3.new(0, rig.Ground, 0)
end

local cache = {}

function BikeRig.points(def)
	local p = cache[def]
	if p then
		return p
	end
	local rig = def.Rig
	local rake = math.rad(rig.Rake)
	p = {
		Hinge = BikeRig.toCar(rig, Vector3.new(0, rig.SteerGroundY, 0)),
		Axis = Vector3.new(0, math.cos(rake), math.sin(rake)), -- up the steering axis (tilted back)
		CosRake = math.cos(rake),
		FrontAxle = BikeRig.toCar(rig, rig.FrontAxle),
		RearAxle = BikeRig.toCar(rig, rig.RearAxle),
		SwingPivot = BikeRig.toCar(rig, rig.SwingPivot),
		StandPivot = BikeRig.toCar(rig, rig.StandPivot),
		Seat = BikeRig.toCar(rig, rig.Seat),
	}
	cache[def] = p
	return p
end

-- Which group root a part rides on (nil = the rigid body).
function BikeRig.groupOf(def): { [string]: string }
	local out = {}
	for group, names in def.Rig.Groups do
		for _, n in names do
			out[n] = group
		end
	end
	return out
end

return BikeRig
