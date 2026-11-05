--[[
	Driving physics, shared by server and client. Whoever simulates the car runs it:
	the driver's client while someone drives, the server while it's parked.

	Ray-cast wheels: each wheel shoots a ray down from its suspension mount. The hit sets
	how squashed the spring is, and one VectorForce per wheel pushes the car with
	spring + damper (up), engine/brake (forward) and grip (sideways). No wheel constraints,
	so cars stay stable at high speed and every number lives in the vehicle's Def.

		local rig = Physics.new(model, def)
		rig:step(dt, { Throttle = -1..1, Steer = -1..1, Handbrake = bool })
		rig.Steer         -- current wheel angle (radians, + = left), for the wheel visuals
		rig.Speed         -- forward speed in studs/s (negative = reversing)
		rig.Grounded      -- how many wheels touch the ground

	Model layout it expects (Vehicles/Builder makes it): PrimaryPart "Chassis" with
	Attachments Wheel<FL|FR|RL|RR> (suspension tops) and Force<FL|...> (each with a VectorForce).
]]

local Players = game:GetService("Players")

local Vehicles = require(script.Parent)

local Physics = {}
Physics.__index = Physics

-- Characters are never "ground" for wheels (cars don't ride up on people).
local characters: { Instance } = {}
local function trackCharacters()
	table.clear(characters)
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(characters, p.Character)
		end
	end
end
local function watch(p: Player)
	p.CharacterAdded:Connect(trackCharacters)
	p.CharacterRemoving:Connect(function()
		task.defer(trackCharacters)
	end)
end
Players.PlayerAdded:Connect(watch)
Players.PlayerRemoving:Connect(function()
	task.defer(trackCharacters)
end)
for _, p in Players:GetPlayers() do
	watch(p)
end
trackCharacters()

local function rayParams(model: Model): RaycastParams
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	local list = table.clone(characters)
	table.insert(list, model)
	params.FilterDescendantsInstances = list
	params.RespectCanCollide = true
	return params
end
Physics.rayParams = rayParams

function Physics.new(model: Model, def)
	local chassis = model.PrimaryPart :: BasePart
	local self = setmetatable({
		Model = model,
		Def = def,
		Chassis = chassis,
		Wheels = {},
		Steer = 0,
		Speed = 0,
		Grounded = 0,
		flipTimer = 0,
	}, Physics)
	for _, name in Vehicles.WHEELS do
		local mount = chassis:WaitForChild(`Wheel{name}`) :: Attachment
		local forceAt = chassis:WaitForChild(`Force{name}`) :: Attachment
		table.insert(self.Wheels, {
			Name = name,
			Mount = mount,
			Force = forceAt:WaitForChild("VectorForce") :: VectorForce,
			ForceAt = forceAt,
			Front = name:sub(1, 1) == "F",
			Left = name:sub(2, 2) == "L",
			Drive = def.Engine.Drive == "All" or (def.Engine.Drive == "Front") == (name:sub(1, 1) == "F"),
			Compression = 0, -- 0..1 of the suspension travel
			Distance = def.Suspension.Length, -- mount -> hub, for the visuals
			Hit = nil :: RaycastResult?,
		})
	end
	return self
end

local function lerp(a: number, b: number, t: number): number
	return a + (b - a) * t
end

-- Clears every wheel force (car goes limp), e.g. before handing it to another simulator.
function Physics:release()
	for _, w in self.Wheels do
		w.Force.Force = Vector3.zero
	end
end

function Physics:step(dt: number, input)
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
	local radius = def.Wheels.Radius

	local cf = chassis.CFrame
	local up = cf.UpVector
	local mass = chassis.AssemblyMass
	local wheelMass = mass / 4
	local omega = 2 * math.pi * sus.Frequency
	local k = wheelMass * omega * omega -- spring per unit of travel (studs)
	local c = 2 * sus.Damping * omega * wheelMass
	local vel = chassis.AssemblyLinearVelocity
	local forwardSpeed = vel:Dot(cf.LookVector)
	local speedFrac = math.clamp(math.abs(forwardSpeed) / eng.MaxSpeed, 0, 1)
	self.Speed = forwardSpeed

	-- steering: the stick sets a target angle that shrinks with speed
	local maxAngle = math.rad(lerp(def.Steering.MaxAngle, def.Steering.TopSpeedAngle, speedFrac))
	local target = -steerIn * maxAngle
	local rate = if math.abs(target) < math.abs(self.Steer) then def.Steering.ReturnSpeed else def.Steering.Speed
	local diff = target - self.Steer
	self.Steer += math.clamp(diff, -rate * dt, rate * dt)

	-- 1) suspension rays
	local params = rayParams(self.Model)
	local reach = sus.Length + radius
	local grounded = 0
	for _, w in self.Wheels do
		local origin = (cf * CFrame.new(w.Mount.Position)).Position
		local hit = workspace:Raycast(origin, -up * reach, params)
		w.Hit = hit
		if hit then
			grounded += 1
			w.Distance = math.max(0, hit.Distance - radius)
			w.Compression = 1 - w.Distance / sus.Length
		else
			w.Distance = sus.Length
			w.Compression = 0
		end
	end
	self.Grounded = grounded

	-- anti-roll: each side gets extra push from how much more it's squashed than the other
	local antiRoll = {}
	for _, w in self.Wheels do
		for _, o in self.Wheels do
			if o ~= w and o.Front == w.Front then
				antiRoll[w] = (w.Compression - o.Compression) * sus.Length * k * sus.AntiRoll
			end
		end
	end

	-- 2) per-wheel forces
	local driven = 0
	for _, w in self.Wheels do
		if w.Drive then
			driven += 1
		end
	end
	for _, w in self.Wheels do
		local force = Vector3.zero
		local hit = w.Hit
		if hit then
			local normal = hit.Normal
			local at = w.ForceAt.WorldPosition
			local pointVel = chassis:GetVelocityAtPosition(at)

			-- spring + damper
			local x = w.Compression * sus.Length
			local closing = -pointVel:Dot(up)
			local load = math.max(0, k * x + c * closing + antiRoll[w])
			force += up * load

			-- wheel directions along the ground
			local look = if w.Front then (cf * CFrame.Angles(0, self.Steer, 0)).LookVector else cf.LookVector
			local fwd = look - normal * look:Dot(normal)
			if fwd.Magnitude > 1e-3 then
				fwd = fwd.Unit
				local right = fwd:Cross(normal)
				local vFwd = pointVel:Dot(fwd)
				local vSide = pointVel:Dot(right)

				-- engine / brake / coast (forward)
				local long = 0
				local stopCap = wheelMass * math.abs(vFwd) / dt -- never push past standstill
				if throttle > 0.05 and forwardSpeed < -1 or throttle < -0.05 and forwardSpeed > 1 then
					-- pressing against the motion = brake
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Brake * math.abs(throttle), stopCap)
				elseif math.abs(throttle) > 0.05 then
					if w.Drive then
						local top = if throttle > 0 then eng.MaxSpeed else eng.ReverseSpeed
						local frac = math.clamp(math.abs(forwardSpeed) / top, 0, 1)
						local accel = eng.Accel * (if throttle > 0 then 1 else 0.6) * (1 - frac * frac)
						long = math.sign(throttle) * mass * accel * math.abs(throttle) / driven
					end
				elseif math.abs(forwardSpeed) < 1.5 then
					long = -vFwd * wheelMass * math.min(10, 0.9 / dt) -- hold still when parked
				else
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Coast, stopCap)
				end

				-- grip (sideways)
				local g = if w.Front then grip.Front else grip.Rear
				if handbrake and not w.Front then
					g *= grip.Handbrake
					long = -math.sign(vFwd) * math.min(wheelMass * eng.Brake * 0.5, stopCap)
				end
				local side = -vSide * wheelMass * math.min(grip.Rate, 0.9 / dt) * g
				local maxSide = grip.Friction * load * g
				side = math.clamp(side, -maxSide, maxSide)

				force += fwd * long + right * side
			end
		end
		w.Force.Force = force
	end

	-- 3) flipped and stuck for a moment: put it back on its wheels
	if up.Y < 0.2 and vel.Magnitude < 4 then
		self.flipTimer += dt
		if self.flipTimer > 2 then
			self.flipTimer = 0
			local pos = chassis.Position + Vector3.new(0, 4, 0)
			local look = Vector3.new(cf.LookVector.X, 0, cf.LookVector.Z)
			if look.Magnitude < 0.1 then
				look = Vector3.new(0, 0, -1)
			end
			chassis.CFrame = CFrame.lookAt(pos, pos + look.Unit) -- moves the whole welded car
			chassis.AssemblyLinearVelocity = Vector3.zero
			chassis.AssemblyAngularVelocity = Vector3.zero
		end
	else
		self.flipTimer = 0
	end
end

return Physics
