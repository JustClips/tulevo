--[[
	Moving parts of real car models, for every car in view (purely visual, like Wheels):
	  - the steering wheel turns with the steering
	  - the gas and brake pedals press with the throttle / brake
	  - the body leans out of turns and dips under braking (Weld "Lean" on BodyRoot)

	The car you drive uses your own inputs (Cockpit.setDriver); other cars read the
	VehicleSeat's ThrottleFloat / SteerFloat, which the driver's client keeps up to date.
	Hinges and limits come from the Def's Rig table (see Defs/Hypercar.luau).
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Vehicles = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Vehicles"))
local Joints = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Joints"))

local Cockpit = {}

local VIEW_RANGE = 250

type State = {
	steer: number,
	gas: number,
	brake: number,
	vel: Vector3?,
	accel: Vector3,
	roll: number,
	pitch: number,
	welds: { [string]: Weld }?,
}

local states: { [Model]: State } = {}
local driver: { model: Model, read: () -> any }? = nil
local kneeWritten: { [Instance]: CFrame } = setmetatable({}, { __mode = "k" }) :: any

-- The car this client drives: read() returns the current { Throttle, Steer, Handbrake }.
function Cockpit.setDriver(model: Model?, read: (() -> any)?)
	driver = if model and read then { model = model, read = read } else nil
end

local function toCarDir(v: Vector3): Vector3
	return Vector3.new(-v.X, v.Z, v.Y).Unit
end

local function toCar(rig, v: Vector3): Vector3
	return Vector3.new(-v.X, v.Z, v.Y) * rig.Scale + Vector3.new(0, rig.Ground, 0)
end

local function approach(x: number, target: number, rate: number): number
	return x + math.clamp(target - x, -rate, rate)
end

local function findWelds(model: Model, rig): { [string]: Weld }
	local out = {}
	local root = model:FindFirstChild("BodyRoot")
	local lean = root and root:FindFirstChild("Lean")
	if lean then
		out.Lean = lean :: Weld
	end
	local body = model:FindFirstChild("Body")
	local function rigWeld(partName: string?)
		local p = partName and body and body:FindFirstChild(partName)
		local w = p and p:FindFirstChild("Rig")
		return w and w:IsA("Weld") and w or nil
	end
	out.Steer = rigWeld(rig.SteeringWheel and rig.SteeringWheel.Part)
	out.Gas = rigWeld(rig.Pedals and rig.Pedals.Gas and rig.Pedals.Gas.Part)
	out.Brake = rigWeld(rig.Pedals and rig.Pedals.Brake and rig.Pedals.Brake.Part)
	return out
end

local function update(model: Model, dt: number, camPos: Vector3)
	if not model:GetAttribute("RealModel") then
		return
	end
	local chassis = model.PrimaryPart
	local def = Vehicles.get(model:GetAttribute("VehicleId"))
	local rig = def and def.Rig
	if not chassis or not rig then
		return
	end
	local cf = chassis.CFrame
	if (cf.Position - camPos).Magnitude > VIEW_RANGE then
		return
	end
	local st = states[model]
	if not st then
		st = { steer = 0, gas = 0, brake = 0, accel = Vector3.zero, roll = 0, pitch = 0 }
		states[model] = st
	end
	local welds = st.welds
	if not welds or not welds.Lean then
		welds = findWelds(model, rig)
		st.welds = welds
	end

	-- inputs: steer (+ = right), throttle (+ = forward)
	local steerIn, throttle = 0, 0
	if driver and driver.model == model then
		local input = driver.read()
		steerIn, throttle = input.Steer or 0, input.Throttle or 0
	else
		local seat = model:FindFirstChild("DriverSeat")
		if seat and seat:IsA("VehicleSeat") and seat.Occupant then
			steerIn, throttle = seat.SteerFloat, seat.ThrottleFloat
		end
	end
	local vel = chassis.AssemblyLinearVelocity
	local speed = vel:Dot(cf.LookVector)
	-- pressing against the motion is braking, otherwise it's gas (forward or reverse)
	local gas, brake = 0, 0
	if throttle > 0.05 then
		if speed < -1 then brake = throttle else gas = throttle end
	elseif throttle < -0.05 then
		if speed > 1 then brake = -throttle else gas = -throttle end
	end
	st.steer = approach(st.steer, math.clamp(steerIn, -1, 1), dt * 5)
	st.gas = approach(st.gas, gas, dt * 8)
	st.brake = approach(st.brake, brake, dt * 8)

	if welds.Steer and rig.SteeringWheel then
		local sw = rig.SteeringWheel
		local axis = toCarDir(sw.Axis)
		-- turning left is counter-clockwise as the driver sees it (+ around the axis toward them)
		welds.Steer.C0 = CFrame.new(toCar(rig, sw.Center)) * CFrame.fromAxisAngle(axis, -st.steer * math.rad(sw.MaxTurn))
	end
	local pedals = rig.Pedals
	if pedals then
		local travel = math.rad(pedals.Travel or 20)
		if welds.Gas then
			welds.Gas.C0 = CFrame.new(toCar(rig, pedals.Gas.Pivot)) * CFrame.Angles(st.gas * travel, 0, 0)
		end
		if welds.Brake then
			welds.Brake.C0 = CFrame.new(toCar(rig, pedals.Brake.Pivot)) * CFrame.Angles(st.brake * travel, 0, 0)
		end
	end

	-- low cars: the default sit pose would push the driver's feet through the floor, so
	-- straighten the knees (applied after the animator each frame, visual only)
	if rig.KneeLift then
		local seat = model:FindFirstChild("DriverSeat")
		local hum = seat and seat:IsA("VehicleSeat") and seat.Occupant
		local character = hum and hum.Parent
		if character then
			for _, joint in { "RightKnee", "LeftKnee" } do
				-- Motor6D or AnimationConstraint (Avatar Joint Upgrade), both have Transform
				local m = Joints.find(character, if joint == "RightKnee" then "RightLowerLeg" else "LeftLowerLeg", joint)
				-- only on top of a fresh animator pose (never stack it frame after frame)
				if m and m.Transform ~= kneeWritten[m] then
					m.Transform *= CFrame.Angles(math.rad(rig.KneeLift), 0, 0)
					kneeWritten[m] = m.Transform
				end
			end
		end
	end

	-- body lean from the car's acceleration (smoothed), in car space
	local lean = rig.Lean
	if welds.Lean and lean then
		local a = Vector3.zero
		if st.vel and dt > 0 then
			a = (vel - st.vel) / dt
		end
		st.vel = vel
		st.accel = st.accel:Lerp(a, math.min(1, dt * 6))
		local side = st.accel:Dot(cf.RightVector)
		local long = st.accel:Dot(cf.LookVector)
		local grounded = math.abs(st.accel:Dot(cf.UpVector)) < 400 -- ignore landings / crashes
		local roll = if grounded then math.clamp(side * lean.RollPerAccel, -lean.Roll, lean.Roll) else 0
		local pitch = if grounded then math.clamp(long * lean.PitchPerAccel, -lean.Pitch, lean.Pitch) else 0
		st.roll = approach(st.roll, roll, dt * 20)
		st.pitch = approach(st.pitch, pitch, dt * 20)
		-- tilt around a point low in the car (roughly the roll centre)
		local pivot = CFrame.new(0, rig.Ground + 0.3 * rig.Scale, 0)
		welds.Lean.C0 = pivot * CFrame.Angles(math.rad(st.pitch), 0, math.rad(st.roll)) * pivot:Inverse()
	end
end

function Cockpit.start()
	RunService.RenderStepped:Connect(function(dt)
		local camPos = workspace.CurrentCamera.CFrame.Position
		for _, model in CollectionService:GetTagged(Vehicles.TAG) do
			if model:IsA("Model") and model:IsDescendantOf(workspace) then
				update(model, dt, camPos)
			end
		end
	end)
	CollectionService:GetInstanceRemovedSignal(Vehicles.TAG):Connect(function(model)
		states[model] = nil
	end)
end

return Cockpit
