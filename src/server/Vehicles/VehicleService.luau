--[[
	Server side of the vehicle system: spawns cars, seats drivers, hands the car's physics to
	the driver's client, and keeps parked cars standing on their wheels.

		VehicleService.spawn("Sedan", cframe) -> Model
		VehicleService.despawn(model)
		VehicleService.driverOf(model) -> Player?

	Getting in: the "Drive" prompt at the driver's door (F, gamepad Y, tap on phones).
	Getting out: client fires VehicleRemotes.Exit (F / Y / phone Exit button).

	While driving, the driver's client owns the car (network owner) and runs Shared.Vehicles
	.Physics itself, so steering has no lag. Parked cars are simulated here.
	The model attribute "DriverId" (UserId) says who is driving, for every client.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local Physics = require(Shared:WaitForChild("Vehicles"):WaitForChild("Physics"))
local Builder = require(script.Parent:WaitForChild("Builder"))

local VehicleService = {}

local remotes = Instance.new("Folder")
remotes.Name = "VehicleRemotes"
local ExitRemote = Instance.new("RemoteEvent")
ExitRemote.Name = "Exit"
ExitRemote.Parent = remotes
remotes.Parent = ReplicatedStorage

local folder = Instance.new("Folder")
folder.Name = "Vehicles"
folder.Parent = workspace

type Car = { model: Model, def: any, rig: any, seat: VehicleSeat, prompt: ProximityPrompt, driver: Player? }
local cars: { [Model]: Car } = {}

local PARKED = { Throttle = 0, Steer = 0, Handbrake = false } -- Physics holds a stopped car still

local function setOwner(car: Car, player: Player?)
	local chassis = car.model.PrimaryPart
	if chassis and chassis:IsDescendantOf(workspace) and chassis:CanSetNetworkOwnership() then
		chassis:SetNetworkOwner(player)
	end
end

local function onOccupant(car: Car)
	local humanoid = car.seat.Occupant
	local player = humanoid and Players:GetPlayerFromCharacter(humanoid.Parent)
	if humanoid and not player then
		-- NPCs or loose humanoids don't drive (yet): kick them out
		local w = car.seat:FindFirstChild("SeatWeld")
		if w then
			w:Destroy()
		end
		return
	end
	car.driver = player
	car.model:SetAttribute("DriverId", player and player.UserId or nil)
	car.prompt.Enabled = player == nil
	if player then
		setOwner(car, player)
	else
		-- driver left: the server takes the car back and parks it
		setOwner(car, nil)
	end
end

local function enter(car: Car, player: Player)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not humanoid or not root or humanoid.Health <= 0 or humanoid.SeatPart then
		return
	end
	if car.seat.Occupant or not car.model.Parent then
		return
	end
	-- the prompt already checks range on the client; check again with some slack
	local door = car.model.PrimaryPart:FindFirstChild("DoorPrompt") :: Attachment
	if (root.Position - door.WorldPosition).Magnitude > car.prompt.MaxActivationDistance + 6 then
		return
	end
	car.seat:Sit(humanoid)
end

-- Where the driver stands after getting out: beside their door, else the other side, else on top.
local function exitSpot(car: Car): CFrame
	local chassis = car.model.PrimaryPart :: BasePart
	local cf = chassis.CFrame
	local s = car.def.Size
	local seatPos = car.seat.Position
	local flat = Vector3.new(cf.LookVector.X, 0, cf.LookVector.Z)
	flat = if flat.Magnitude > 0.1 then flat.Unit else Vector3.new(0, 0, -1)
	local params = Physics.rayParams(car.model)
	for _, side in { car.def.ExitSide, -car.def.ExitSide } do
		local spot = (cf * CFrame.new(side * (s.X / 2 + 2), 0, car.def.DriverSeat.Z)).Position
		spot = Vector3.new(spot.X, math.max(spot.Y, seatPos.Y) + 1.5, spot.Z)
		if not workspace:Raycast(seatPos, spot - seatPos, params) then
			return CFrame.lookAt(spot, spot + flat)
		end
	end
	local top = cf.Position + Vector3.new(0, s.Y + 5, 0)
	return CFrame.lookAt(top, top + flat)
end

local function exit(player: Player)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not humanoid then
		return
	end
	for _, car in cars do
		if car.seat.Occupant == humanoid then
			local spot = exitSpot(car)
			local w = car.seat:FindFirstChild("SeatWeld")
			if w then
				w:Destroy()
			end
			humanoid.Sit = false
			character:PivotTo(spot)
			return
		end
	end
end

function VehicleService.spawn(id: string, cframe: CFrame): Model
	local def = Vehicles.get(id)
	assert(def, `unknown vehicle {id}`)
	local model = Builder.build(def)
	model:PivotTo(cframe)
	model.Parent = folder

	local car: Car = {
		model = model,
		def = def,
		rig = Physics.new(model, def),
		seat = model:FindFirstChild("DriverSeat") :: VehicleSeat,
		prompt = model.PrimaryPart:FindFirstChild("DoorPrompt"):FindFirstChild("Drive") :: ProximityPrompt,
		driver = nil,
	}
	cars[model] = car
	setOwner(car, nil)

	car.prompt.Triggered:Connect(function(player)
		enter(car, player)
	end)
	car.seat:GetPropertyChangedSignal("Occupant"):Connect(function()
		onOccupant(car)
	end)
	model.Destroying:Connect(function()
		cars[model] = nil
	end)
	return model
end

function VehicleService.despawn(model: Model)
	cars[model] = nil
	model:Destroy()
end

function VehicleService.driverOf(model: Model): Player?
	local car = cars[model]
	return car and car.driver
end

function VehicleService.start()
	ExitRemote.OnServerEvent:Connect(exit)

	-- parked cars: keep their suspension working (the driver's client runs driven ones)
	RunService.PreSimulation:Connect(function(dt)
		for _, car in cars do
			if not car.driver then
				car.rig:step(dt, PARKED)
			end
		end
	end)
end

return VehicleService
