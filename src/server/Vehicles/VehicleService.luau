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
local Config = require(Shared:WaitForChild("Config"))
local Guard = require(script.Parent.Parent:WaitForChild("Guard"))

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

type Car = {
	model: Model,
	def: any,
	rig: any,
	seat: VehicleSeat,
	prompt: ProximityPrompt,
	driver: Player?,
	allowed: Humanoid?, -- the one humanoid enter() just let in (anyone else in the seat is thrown out)
	lastPos: Vector3?, -- speed check while driven: where it was at the last check
	goodPos: Vector3?, -- and the last spot that passed
	strikes: number,
}
local cars: { [Model]: Car } = {}

local PARKED = { Throttle = 0, Steer = 0, Handbrake = false } -- Physics holds a stopped car still

local function setOwner(car: Car, player: Player?)
	local chassis = car.model.PrimaryPart
	if chassis and chassis:IsDescendantOf(workspace) and chassis:CanSetNetworkOwnership() then
		chassis:SetNetworkOwner(player)
	end
end

local function kickOut(car: Car)
	local w = car.seat:FindFirstChild("SeatWeld")
	if w then
		w:Destroy()
	end
end

local function onOccupant(car: Car)
	local humanoid = car.seat.Occupant
	local player = humanoid and Players:GetPlayerFromCharacter(humanoid.Parent)
	if humanoid and not player then
		-- NPCs or loose humanoids don't drive (yet): kick them out
		kickOut(car)
		return
	end
	if humanoid and humanoid ~= car.allowed then
		-- sat down without the Drive prompt (touching the seat, or a cheat firing its touch):
		-- only enter() seats drivers
		if player then
			Guard.flag(player, "sat in a car without the Drive prompt")
		end
		kickOut(car)
		return
	end
	car.allowed = humanoid
	car.lastPos, car.goodPos, car.strikes = nil, nil, 0
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
	if not Guard.alive(player) or not humanoid or not root or humanoid.SeatPart then
		return
	end
	if car.seat.Occupant or not car.model.Parent then
		return
	end
	-- the prompt already checks range on the client; check again with some slack
	local door = car.model.PrimaryPart:FindFirstChild("DoorPrompt") :: Attachment
	if (root.Position - door.WorldPosition).Magnitude > car.prompt.MaxActivationDistance + 6 then
		Guard.flag(player, "used a car door from too far away")
		return
	end
	car.allowed = humanoid
	car.seat:Sit(humanoid)
	if car.seat.Occupant ~= humanoid then
		task.delay(1, function()
			if car.allowed == humanoid and car.seat.Occupant ~= humanoid then
				car.allowed = nil -- Sit didn't take
			end
		end)
	end
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
	if not Guard.rate(player, "CarExit", 2, 2) then
		return
	end
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
			car.allowed = nil
			Guard.allowTeleport(player, 1)
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
		allowed = nil,
		lastPos = nil,
		goodPos = nil,
		strikes = 0,
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

-- The driver's client moves the car, so a cheat could teleport or speed it up. Twice a
-- second the server checks the driven car's speed against its MaxSpeed (x CarSpeedFactor for
-- crashes and ramps); a teleport or two fast checks in a row put it back where it was.
local CAR_CHECK = 0.5
local function checkCars()
	local factor = (Config.AntiCheat and Config.AntiCheat.CarSpeedFactor) or 1.6
	for _, car in cars do
		local chassis = car.model.PrimaryPart
		if not car.driver or not chassis then
			car.lastPos, car.goodPos, car.strikes = nil, nil, 0
			continue
		end
		local pos = chassis.Position
		local last, good = car.lastPos, car.goodPos
		car.lastPos = pos
		if not last or not good then
			car.goodPos = pos
			continue
		end
		local max = ((car.def.Engine and car.def.Engine.MaxSpeed) or 120) * factor
		local moved = Vector3.new(pos.X - last.X, 0, pos.Z - last.Z).Magnitude
		if moved > max * CAR_CHECK * 3 then
			Guard.flag(car.driver, `car teleported {math.floor(moved)} studs`)
		elseif moved > max * CAR_CHECK then
			car.strikes += 1
			if car.strikes < 2 then
				continue -- one fast check (a crash) is let go
			end
			Guard.flag(car.driver, `car too fast ({math.floor(moved / CAR_CHECK)} studs/s)`)
		else
			car.strikes = 0
			car.goodPos = pos
			continue
		end
		-- put it back and stop it; the server holds the car for a moment so the driver's
		-- client can't move it straight back
		car.strikes = 0
		car.lastPos = good
		local driver = car.driver
		setOwner(car, nil)
		car.model:PivotTo(CFrame.new(good) * chassis.CFrame.Rotation)
		chassis.AssemblyLinearVelocity = Vector3.zero
		chassis.AssemblyAngularVelocity = Vector3.zero
		task.delay(0.5, function()
			if car.driver == driver and driver then
				setOwner(car, driver)
			end
		end)
	end
end

function VehicleService.start()
	ExitRemote.OnServerEvent:Connect(exit)
	task.spawn(function()
		while true do
			task.wait(CAR_CHECK)
			local ok, err = pcall(checkCars)
			if not ok then
				warn("[Vehicles] car check:", err)
			end
		end
	end)

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
