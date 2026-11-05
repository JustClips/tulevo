--[[
	Wheel visuals for every car in view: each wheel follows the ground (suspension), the
	front ones steer, and all of them spin with the car's speed. Purely visual, runs on
	every client. The car you drive uses its own physics rig (exact steer + suspension);
	other cars get a ray per wheel and the steer from their VehicleSeat.
]]

local CollectionService = game:GetService("CollectionService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Vehicles = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Vehicles"))
local Physics = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Vehicles"):WaitForChild("Physics"))

local Wheels = {}

local VIEW_RANGE = 400 -- studs; farther cars keep their last wheel pose

local spin: { [Model]: number } = {}
local localRigs: { [Model]: any } = {}

-- The car the local player drives: use its rig for steer + suspension.
function Wheels.setRig(model: Model, rig: any?)
	localRigs[model] = rig
end

local function update(model: Model, dt: number, camPos: Vector3)
	local chassis = model.PrimaryPart
	local def = Vehicles.get(model:GetAttribute("VehicleId"))
	local folder = model:FindFirstChild("Wheels")
	if not chassis or not def or not folder then
		return
	end
	local cf = chassis.CFrame
	if (cf.Position - camPos).Magnitude > VIEW_RANGE then
		return
	end
	local radius = def.Wheels.Radius
	local length = def.Suspension.Length
	local rig = localRigs[model]

	local speed = chassis.AssemblyLinearVelocity:Dot(cf.LookVector)
	local angle = (spin[model] or 0) - speed / radius * dt
	spin[model] = angle % (2 * math.pi)

	local steer
	if rig then
		steer = rig.Steer
	else
		local seat = model:FindFirstChild("DriverSeat")
		local s = if seat and seat:IsA("VehicleSeat") then seat.SteerFloat else 0
		steer = -s * math.rad(def.Steering.MaxAngle) * 0.6
	end

	local params = nil
	for i, name in Vehicles.WHEELS do
		local tire = folder:FindFirstChild(`Wheel_{name}`)
		local mount = tire and tire:FindFirstChild("Mount")
		local attach = chassis:FindFirstChild(`Wheel{name}`)
		if not mount or not attach then
			continue
		end
		local distance
		if rig then
			distance = rig.Wheels[i].Distance
		else
			params = params or Physics.rayParams(model)
			local origin = attach.WorldPosition
			local hit = workspace:Raycast(origin, -cf.UpVector * (length + radius), params)
			distance = if hit then math.max(0, hit.Distance - radius) else length
		end
		local pose = CFrame.new(attach.Position - Vector3.new(0, distance, 0))
		if name:sub(1, 1) == "F" then
			pose *= CFrame.Angles(0, steer, 0)
		end
		local weld = mount :: Weld
		weld.C0 = pose * CFrame.Angles(angle, 0, 0)
		-- brake calipers (real models) follow the wheel but don't spin
		local caliper = folder:FindFirstChild(`Caliper_{name}`)
		local cmount = caliper and caliper:FindFirstChild("Mount")
		if cmount then
			(cmount :: Weld).C0 = pose
		end
	end
end

function Wheels.start()
	RunService.RenderStepped:Connect(function(dt)
		local camPos = workspace.CurrentCamera.CFrame.Position
		for _, model in CollectionService:GetTagged(Vehicles.TAG) do
			if model:IsA("Model") and model:IsDescendantOf(workspace) then
				update(model, dt, camPos)
			end
		end
	end)
	CollectionService:GetInstanceRemovedSignal(Vehicles.TAG):Connect(function(model)
		spin[model] = nil
		localRigs[model] = nil
	end)
end

return Wheels
