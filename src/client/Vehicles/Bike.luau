--[[
	Motorbikes, client side (Def.Kind == "Bike", built by Server/Vehicles/BikeBuilder).

	Every bike in view (purely visual, like Vehicles/Wheels and Cockpit):
	  - the whole bike and its rider lean into turns (Weld "Lean"), from speed x turn rate
	  - the bars and forks turn about the steering axis, the forks slide with the front suspension,
	    the swingarm swings with the rear one, both wheels spin
	  - a parked bike drops its side stand and rests on it
	The bike you ride uses its physics rig (exact steer + suspension); other bikes get a ray per
	wheel and a steer worked out from how fast they turn.

	Your own rider (the clips replicate to everyone): Mount when you get on, then a blend of
	Ride / Stop / Tuck / SteerLeft / SteerRight / LeanLeft / LeanRight from speed, bars and lean,
	and Dismount before getting off (Bike.dismount, called by Vehicles/init).
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local BikeRig = require(Shared:WaitForChild("Vehicles"):WaitForChild("BikeRig"))
local BikePhysics = require(Shared:WaitForChild("Vehicles"):WaitForChild("BikePhysics"))
local Physics = require(Shared:WaitForChild("Vehicles"):WaitForChild("Physics"))
local AnimIds = require(Shared:WaitForChild("AnimIds"))

local Bike = {}

local VIEW_RANGE = 300

type State = {
	welds: { [string]: Weld },
	lean: number, -- degrees, + = left
	steer: number, -- radians, + = left
	front: number, -- suspension distance (mount -> hub)
	rear: number,
	spinF: number,
	spinR: number,
	stand: number, -- 0 = up, 1 = down
	yaw: number?,
	yawRate: number,
}

local states: { [Model]: State } = {}
local localRigs: { [Model]: any } = {}

function Bike.setRig(model: Model, rig: any?)
	localRigs[model] = rig
end

function Bike.isBike(model: Model?): boolean
	return model ~= nil and model:GetAttribute("Bike") == true
end

-- Current lean (degrees, + = left) and steer (radians, + = left) of a bike in view, for the rider.
function Bike.state(model: Model): (number, number)
	local st = states[model]
	if not st then
		return 0, 0
	end
	return st.lean, st.steer
end

local function approach(x: number, target: number, rate: number): number
	return x + math.clamp(target - x, -rate, rate)
end

local function findWelds(model: Model): { [string]: Weld }
	local out = {}
	for weldName, partName in
		{
			Lean = "BodyRoot",
			Steer = "SteerRoot",
			Fork = "ForkRoot",
			SpinF = "FrontHub",
			Swing = "SwingRoot",
			SpinR = "RearHub",
			Stand = "StandRoot",
		}
	do
		local p = model:FindFirstChild(partName)
		local w = p and p:FindFirstChild(if weldName:sub(1, 4) == "Spin" then "Spin" else weldName)
		if w and w:IsA("Weld") then
			out[weldName] = w
		end
	end
	return out
end

local function update(model: Model, dt: number, camPos: Vector3)
	local chassis = model.PrimaryPart
	local def = Vehicles.get(model:GetAttribute("VehicleId"))
	if not chassis or not def or not def.Rig then
		return
	end
	local cf = chassis.CFrame
	if (cf.Position - camPos).Magnitude > VIEW_RANGE then
		return
	end
	local pts = BikeRig.points(def)
	local st = states[model]
	if not st then
		st = {
			welds = findWelds(model),
			lean = 0,
			steer = 0,
			front = def.Suspension.Length,
			rear = def.Suspension.Length,
			spinF = 0,
			spinR = 0,
			stand = 0,
			yaw = nil,
			yawRate = 0,
		}
		states[model] = st
	end
	local welds = st.welds
	if not welds.Lean then
		st.welds = findWelds(model)
		welds = st.welds
		if not welds.Lean then
			return
		end
	end

	local look = cf.LookVector
	local speed = chassis.AssemblyLinearVelocity:Dot(look)
	-- turn rate from how the heading changes (works the same for every client)
	local yaw = math.atan2(-look.X, -look.Z)
	if st.yaw and dt > 0 then
		local d = (yaw - st.yaw + math.pi) % (2 * math.pi) - math.pi
		st.yawRate += (d / dt - st.yawRate) * math.min(1, dt * 10)
	end
	st.yaw = yaw

	local rig = localRigs[model]
	local ridden = model:GetAttribute("DriverId") ~= nil or rig ~= nil

	-- steer: the rig's, or the angle that makes this turn (bicycle: tan(steer) = wheelbase x rate / speed)
	local steer
	if rig then
		steer = rig.Steer
	elseif math.abs(speed) > 2 then
		local wheelbase = def.Rig.Wheelbase * def.Rig.Scale
		steer = math.clamp(
			math.atan(wheelbase * st.yawRate / speed),
			-math.rad(def.Steering.MaxAngle),
			math.rad(def.Steering.MaxAngle)
		)
	else
		steer = st.steer
	end
	st.steer = approach(st.steer, steer, dt * 6)

	-- lean into the turn; a parked bike rests on its stand
	local parked = not ridden and math.abs(speed) < 1
	local lean = if parked then def.Lean.Parked else BikePhysics.leanFor(def, speed, st.yawRate)
	st.lean = approach(st.lean, lean, dt * def.Lean.Rate)
	st.stand = approach(st.stand, if parked then 1 else 0, dt * 3)

	-- suspension
	local length = def.Suspension.Length
	local params = nil
	for i, name in { "F", "R" } do
		local distance
		if rig then
			distance = rig.Wheels[i].Distance
		else
			local attach = chassis:FindFirstChild(`Wheel{name}`) :: Attachment?
			if not attach then
				continue
			end
			params = params or Physics.rayParams(model)
			local radius = if name == "F" then def.Wheels.Radius else def.Wheels.RearRadius
			local hit = workspace:Raycast(attach.WorldPosition, -cf.UpVector * (length + radius), params)
			distance = if hit then math.max(0, hit.Distance - radius) else length
		end
		if name == "F" then
			st.front = approach(st.front, distance, dt * 30)
		else
			st.rear = approach(st.rear, distance, dt * 30)
		end
	end
	st.spinF = (st.spinF - speed / def.Wheels.Radius * dt) % (2 * math.pi)
	st.spinR = (st.spinR - speed / def.Wheels.RearRadius * dt) % (2 * math.pi)

	-- welds (positions are chassis space, see Shared/Vehicles/BikeRig)
	local pivot = CFrame.new(0, def.Rig.Ground, 0) -- lean about the tyres' contact line
	welds.Lean.C0 = pivot * CFrame.Angles(0, 0, math.rad(st.lean)) * pivot:Inverse()
	if welds.Steer then
		welds.Steer.C0 = CFrame.new(pts.Hinge) * CFrame.fromAxisAngle(pts.Axis, st.steer)
	end
	local restF = def.Wheels.F.Y - pts.FrontAxle.Y -- mount -> hub at rest
	local restR = def.Wheels.R.Y - pts.RearAxle.Y
	if welds.Fork then
		-- the hub moves up by (rest - distance); the forks slide that much along the tilted axis
		local slide = math.clamp((restF - st.front) / pts.CosRake, -0.5 * length, length)
		welds.Fork.C0 = CFrame.new(pts.Axis * slide)
	end
	if welds.SpinF then
		welds.SpinF.C0 = CFrame.new(pts.FrontAxle - pts.Hinge) * CFrame.Angles(st.spinF, 0, 0)
	end
	if welds.Swing then
		local arm = pts.RearAxle - pts.SwingPivot
		local len = Vector3.new(0, arm.Y, arm.Z).Magnitude
		local rise = math.clamp(restR - st.rear, -0.5 * length, length)
		local a0 = math.asin(math.clamp(arm.Y / len, -1, 1))
		local a1 = math.asin(math.clamp((arm.Y + rise) / len, -1, 1))
		-- axle behind the pivot (+Z): turning about +X by -a lifts it
		welds.Swing.C0 = CFrame.new(pts.SwingPivot) * CFrame.Angles(-(a1 - a0), 0, 0)
	end
	if welds.SpinR then
		welds.SpinR.C0 = CFrame.new(pts.RearAxle - pts.SwingPivot) * CFrame.Angles(st.spinR, 0, 0)
	end
	if welds.Stand then
		local t = st.stand * st.stand * (3 - 2 * st.stand)
		welds.Stand.C0 = CFrame.new(pts.StandPivot) * CFrame.Angles(math.rad(def.Rig.StandAngle) * t, 0, 0)
	end
end

-- ------------------------------------------------------------------ your rider

local LOOP = { "Ride", "Stop", "Tuck", "SteerLeft", "SteerRight", "LeanLeft", "LeanRight" }

type Rider = {
	model: Model,
	def: any,
	tracks: { [string]: AnimationTrack },
	busy: number, -- os.clock() until which Mount / Dismount is playing (no driving)
	conn: RBXScriptConnection?,
}
local rider: Rider? = nil

local function load(animator: Animator, name: string?): AnimationTrack?
	local id = name and (AnimIds :: any)[name]
	if not id then
		return nil
	end
	local a = Instance.new("Animation")
	a.AnimationId = id
	local ok, t = pcall(animator.LoadAnimation, animator, a)
	return if ok then t else nil
end

-- Clip weights from the bike's state: stop <-> ride, then tuck at speed, bars, lean on top.
local function weights(def, speed: number, throttle: number, steer: number, lean: number): { [string]: number }
	local w = {}
	local stop = math.clamp(1 - (math.abs(speed) - 2) / 10, 0, 1)
	local tuck = math.clamp((speed - 0.55 * def.Engine.MaxSpeed) / (0.3 * def.Engine.MaxSpeed), 0, 1)
		* (if throttle > 0.3 then 1 else 0.4)
	local leanF = math.clamp(math.abs(lean) / (def.Lean.Max * 0.8), 0, 1)
	local steerF = math.clamp(math.abs(steer) / math.rad(def.Steering.MaxAngle), 0, 1) * (1 - leanF)
	tuck *= 1 - leanF
	local rest = 1 - leanF - steerF
	local base = rest * (1 - tuck)
	w.Tuck = rest * tuck
	w.Stop = base * stop
	w.Ride = base * (1 - stop)
	w.SteerLeft = if steer > 0 then steerF else 0
	w.SteerRight = if steer < 0 then steerF else 0
	w.LeanLeft = if lean > 0 then leanF else 0
	w.LeanRight = if lean < 0 then leanF else 0
	return w
end

function Bike.stopRider()
	local r = rider
	if not r then
		return
	end
	rider = nil
	if r.conn then
		r.conn:Disconnect()
	end
	for name, t in r.tracks do
		-- the step-off clip ends where the server puts you: drop it at once
		t:Stop(if name == "Dismount" or name == "Mount" then 0 else 0.15)
	end
end

-- You just sat on a bike: hop on, then ride. read() -> the current inputs.
function Bike.startRider(model: Model, character: Model, read: () -> any)
	Bike.stopRider()
	local def = Vehicles.get(model:GetAttribute("VehicleId"))
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local animator = humanoid and humanoid:FindFirstChildOfClass("Animator")
	if not def or not def.Anims or not animator then
		return
	end
	local tracks = {}
	for _, name in LOOP do
		local t = load(animator, def.Anims[name])
		if t then
			t.Priority = Enum.AnimationPriority.Action
			t.Looped = true
			tracks[name] = t
		end
	end
	for _, name in { "Mount", "Dismount" } do
		local t = load(animator, def.Anims[name])
		if t then
			t.Priority = Enum.AnimationPriority.Action3
			t.Looped = false
			tracks[name] = t
		end
	end
	local r: Rider = { model = model, def = def, tracks = tracks, busy = 0, conn = nil }
	rider = r
	for _, name in LOOP do
		local t = tracks[name]
		if t then
			t:Play(0, if name == "Stop" then 1 else 0.001)
		end
	end
	local mount = tracks.Mount
	if mount then
		mount:Play(0)
		r.busy = os.clock() + (if mount.Length > 0 then mount.Length else 1.05)
	end
	r.conn = RunService.RenderStepped:Connect(function()
		if rider ~= r then
			return
		end
		local chassis = model.PrimaryPart
		if not chassis or not model.Parent then
			return
		end
		local lean, steer = Bike.state(model)
		local input = read()
		local speed = chassis.AssemblyLinearVelocity:Dot(chassis.CFrame.LookVector)
		for name, w in weights(def, speed, input.Throttle or 0, steer, lean) do
			local t = tracks[name]
			if t then
				t:AdjustWeight(math.max(w, 0.001), 0.12)
			end
		end
	end)
end

-- True while hopping on or off (the bike holds still).
function Bike.busy(): boolean
	return rider ~= nil and os.clock() < rider.busy
end

-- Step off to the left, then done() (fires the Exit remote). Too fast for that: done() at once.
function Bike.dismount(done: () -> ())
	local r = rider
	local chassis = r and r.model.PrimaryPart
	if not r or not chassis or Bike.busy() then
		if not r then
			done()
		end
		return
	end
	local speed = chassis.AssemblyLinearVelocity.Magnitude
	local clip = r.tracks.Dismount
	if not clip or speed > 6 then
		done()
		return
	end
	local length = if clip.Length > 0 then clip.Length else 1.05
	r.busy = os.clock() + length + 0.5
	clip:Play(0.1)
	task.delay(length - 0.05, function()
		if rider == r then
			clip:AdjustSpeed(0) -- hold the standing pose until the server moves you off the seat
			done()
		end
	end)
end

function Bike.start()
	RunService.RenderStepped:Connect(function(dt)
		local camPos = workspace.CurrentCamera.CFrame.Position
		for _, model in CollectionService:GetTagged(Vehicles.TAG) do
			if model:IsA("Model") and model:GetAttribute("Bike") and model:IsDescendantOf(workspace) then
				update(model, dt, camPos)
			end
		end
	end)
	CollectionService:GetInstanceRemovedSignal(Vehicles.TAG):Connect(function(model)
		states[model] = nil
		localRigs[model] = nil
	end)
end

return Bike
