--[[
	Motorbike physics (Def.Kind == "Bike"), shared by server and client like Vehicles/Physics:
	the rider's client runs it while riding, the server while the bike is parked.

	Two ray-cast wheels on the bike's centre line (front F, rear R), each with one VectorForce
	for spring + damper, engine / brakes and tyre grip, like the cars. A bike can't stand on two
	wheels by itself, so an AlignOrientation ("Upright", made by Server/Vehicles/BikeBuilder)
	only rolls the chassis back to the ground's up; yaw and pitch stay free. The lean you see is
	visual (Client/Vehicles/Bike), worked out from speed and turn rate.

	Steering: at walking pace the bars turn up to Steering.MaxAngle. Faster, the turn is capped so
	it never needs more lean than Lean.Max, i.e. sideways acceleration <= Gravity * tan(Lean.Max).

		local rig = BikePhysics.new(model, def)
		rig:step(dt, { Throttle = -1..1, Steer = -1..1, Handbrake = bool })
		rig.Steer, rig.Speed, rig.Grounded, rig.Wheels[1 = F, 2 = R].Distance  (same as Physics)
		BikePhysics.leanFor(def, speed, yawRate) -> degrees (+ = leaning left)
]]

local Physics = require(script.Parent:WaitForChild("Physics"))

local BikePhysics = {}
BikePhysics.__index = BikePhysics

BikePhysics.WHEELS = { "F", "R" }

function BikePhysics.new(model: Model, def)
	local chassis = model.PrimaryPart :: BasePart
	local upright = chassis:WaitForChild("Upright") :: Attachment
	local self = setmetatable({
		Model = model,
		Def = def,
		Chassis = chassis,
		Align = upright:WaitForChild("AlignOrientation") :: AlignOrientation,
		Wheels = {},
		Steer = 0,
		Speed = 0,
		Grounded = 0,
		flipTimer = 0,
	}, BikePhysics)
	for _, name in BikePhysics.WHEELS do
		local mount = chassis:WaitForChild(`Wheel{name}`) :: Attachment
		local forceAt = chassis:WaitForChild(`Force{name}`) :: Attachment
		table.insert(self.Wheels, {
			Name = name,
			Mount = mount,
			Force = forceAt:WaitForChild("VectorForce") :: VectorForce,
			ForceAt = forceAt,
			Front = name == "F",
			Drive = name == "R",
			Radius = if name == "F" then def.Wheels.Radius else def.Wheels.RearRadius,
			Compression = 0,
			Distance = def.Suspension.Length,
			Hit = nil :: RaycastResult?,
		})
	end
	return self
end

-- Sideways acceleration a turn may need at most (studs/s^2).
local function maxSideAccel(def): number
	return workspace.Gravity * math.tan(math.rad(def.Lean.Max))
end

-- Lean (degrees, + = left) that balances turning at yawRate (rad/s, + = turning left) at speed.
function BikePhysics.leanFor(def, speed: number, yawRate: number): number
	local a = speed * yawRate
	return math.clamp(math.deg(math.atan(a / workspace.Gravity)), -def.Lean.Max, def.Lean.Max)
end

-- Largest wheel angle (radians) at this speed.
function BikePhysics.maxSteer(def, speed: number): number
	local wheelbase = def.Rig.Wheelbase * def.Rig.Scale
	local v = math.max(math.abs(speed), 1)
	return math.min(math.rad(def.Steering.MaxAngle), math.atan(wheelbase * maxSideAccel(def) / (v * v)))
end

function BikePhysics:release()
	for _, w in self.Wheels do
		w.Force.Force = Vector3.zero
	end
end

function BikePhysics:step(dt: number, input)
	local def = self.Def
	local chassis = self.Chassis
	if not chassis.Parent or chassis.Anchored then
		return
	end
	dt = math.clamp(dt, 1 / 240, 1 / 20)
	local throttle = math.clamp(input.Throttle or 0, -1, 1)
	local steerIn = math.clamp(input.Steer or 0, -1, 1)
	local handbrake = input.Handbrake == true

	local sus = def.Suspension
	local eng = def.Engine
	local grip = def.Grip

	local cf = chassis.CFrame
	local up = cf.UpVector
	local mass = chassis.AssemblyMass
	local wheelMass = mass / 2
	local omega = 2 * math.pi * sus.Frequency
	local k = wheelMass * omega * omega
	local c = 2 * sus.Damping * omega * wheelMass
	local vel = chassis.AssemblyLinearVelocity
	local forwardSpeed = vel:Dot(cf.LookVector)
	self.Speed = forwardSpeed

	-- steering (+ = left), capped by the lean limit at speed
	local target = -steerIn * BikePhysics.maxSteer(def, forwardSpeed)
	local rate = if math.abs(target) < math.abs(self.Steer) then def.Steering.ReturnSpeed else def.Steering.Speed
	self.Steer += math.clamp(target - self.Steer, -rate * dt, rate * dt)

	-- 1) suspension rays
	local params = Physics.rayParams(self.Model)
	local grounded = 0
	local normal = Vector3.zero
	for _, w in self.Wheels do
		local origin = (cf * CFrame.new(w.Mount.Position)).Position
		local hit = workspace:Raycast(origin, -up * (sus.Length + w.Radius), params)
		w.Hit = hit
		if hit then
			grounded += 1
			normal += hit.Normal
			w.Distance = math.max(0, hit.Distance - w.Radius)
			w.Compression = 1 - w.Distance / sus.Length
		else
			w.Distance = sus.Length
			w.Compression = 0
		end
	end
	self.Grounded = grounded

	-- 2) stay upright: roll the chassis to the ground's up (world up in the air), pitch left free
	local goal = if grounded > 0 then normal.Unit else Vector3.yAxis
	local look = cf.LookVector
	goal -= look * goal:Dot(look)
	if goal.Magnitude > 1e-3 then
		self.Align.PrimaryAxis = goal.Unit
	end

	-- 3) per-wheel forces
	for _, w in self.Wheels do
		local force = Vector3.zero
		local hit = w.Hit
		if hit then
			local n = hit.Normal
			local pointVel = chassis:GetVelocityAtPosition(w.ForceAt.WorldPosition)

			local x = w.Compression * sus.Length
			local load = math.max(0, k * x + c * -pointVel:Dot(up))
			force += up * load

			local dir = if w.Front then (cf * CFrame.Angles(0, self.Steer, 0)).LookVector else look
			local fwd = dir - n * dir:Dot(n)
			if fwd.Magnitude > 1e-3 then
				fwd = fwd.Unit
				local right = fwd:Cross(n)
				local vFwd = pointVel:Dot(fwd)
				local vSide = pointVel:Dot(right)

				local long = 0
				local stopCap = wheelMass * math.abs(vFwd) / dt
				if throttle > 0.05 and forwardSpeed < -1 or throttle < -0.05 and forwardSpeed > 1 then
					-- pressing against the motion = brakes (front and back)
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Brake * math.abs(throttle), stopCap)
				elseif math.abs(throttle) > 0.05 then
					if w.Drive then
						local top = if throttle > 0 then eng.MaxSpeed else eng.ReverseSpeed
						local frac = math.clamp(math.abs(forwardSpeed) / top, 0, 1)
						local accel = eng.Accel * (if throttle > 0 then 1 else 0.5) * (1 - frac * frac)
						long = math.sign(throttle) * mass * accel * math.abs(throttle)
					end
				elseif math.abs(forwardSpeed) < 1.5 then
					long = -vFwd * wheelMass * math.min(10, 0.9 / dt) -- hold still when stopped
				else
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Coast, stopCap)
				end

				local g = if w.Front then grip.Front else grip.Rear
				if handbrake and not w.Front then
					g *= grip.Handbrake
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Brake * 0.6, stopCap)
				end
				local side = -vSide * wheelMass * math.min(grip.Rate, 0.9 / dt) * g
				local maxSide = grip.Friction * load * g
				side = math.clamp(side, -maxSide, maxSide)

				force += fwd * long + right * side
			end
		end
		w.Force.Force = force
	end

	-- 4) knocked over and stuck (the upright pull lost to a crash): stand it back up
	if up.Y < 0.3 and vel.Magnitude < 4 then
		self.flipTimer += dt
		if self.flipTimer > 1.5 then
			self.flipTimer = 0
			local pos = chassis.Position + Vector3.new(0, 3, 0)
			local flat = Vector3.new(look.X, 0, look.Z)
			if flat.Magnitude < 0.1 then
				flat = Vector3.new(0, 0, -1)
			end
			chassis.CFrame = CFrame.lookAt(pos, pos + flat.Unit)
			chassis.AssemblyLinearVelocity = Vector3.zero
			chassis.AssemblyAngularVelocity = Vector3.zero
		end
	else
		self.flipTimer = 0
	end
end

return BikePhysics
