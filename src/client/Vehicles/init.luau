--[[
	Client vehicle controller. Get in with the "Drive" prompt at a car's driver door
	(F / gamepad Y / tap). While you're in the driver's seat this client owns the car and
	runs Shared.Vehicles.Physics with your inputs every physics step. F / Y / Exit gets out.

		Vehicles/Input   driving controls (gas, brake/reverse, steer, handbrake)
		Vehicles/Wheels  wheel visuals for every car (suspension, steering, spin)
		Vehicles/Bike    motorbikes: lean, bars, forks, wheels, side stand, and your rider's clips
		                 (hop on, ride / lean / tuck, step off before the Exit remote)

	Weapons are put away while driving (Weapons/State.InVehicle). The Movement system's
	Seated move takes over the character while sitting.
]]

local Players = game:GetService("Players")
local ProximityPromptService = game:GetService("ProximityPromptService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Vehicles = require(Shared:WaitForChild("Vehicles"))
local Physics = require(Shared:WaitForChild("Vehicles"):WaitForChild("Physics"))
local BikePhysics = require(Shared:WaitForChild("Vehicles"):WaitForChild("BikePhysics"))
local Input = require(script:WaitForChild("Input"))
local Wheels = require(script:WaitForChild("Wheels"))
local Cockpit = require(script:WaitForChild("Cockpit"))
local Bike = require(script:WaitForChild("Bike"))
local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local Remotes = ReplicatedStorage:WaitForChild("VehicleRemotes")

local player = Players.LocalPlayer

local Controller = {}

local driving: { model: Model, rig: any, conn: RBXScriptConnection }? = nil

local PARKED = { Throttle = 0, Steer = 0, Handbrake = false }

function Controller.current(): Model?
	return driving and driving.model
end

local heldBeforeDriving: string? = nil

local function stopDriving()
	local d = driving
	if not d then
		return
	end
	driving = nil
	d.conn:Disconnect()
	-- leave parked forces in place until the server takes the car back
	d.rig:step(1 / 60, PARKED)
	Input.unbind()
	Wheels.setRig(d.model, nil)
	Bike.setRig(d.model, nil)
	Bike.stopRider()
	Cockpit.setDriver(nil)
	WeaponState.InVehicle = false
	ProximityPromptService.Enabled = true
	-- take the gun back out after getting out
	if heldBeforeDriving then
		local id = heldBeforeDriving
		heldBeforeDriving = nil
		require(script.Parent:WaitForChild("Weapons")).equip(id)
	end
end

local function startDriving(model: Model)
	stopDriving()
	local def = Vehicles.get(model:GetAttribute("VehicleId"))
	if not def or not model.PrimaryPart then
		return
	end
	-- put the gun away (the weapon controller refuses to equip while InVehicle)
	WeaponState.InVehicle = true
	heldBeforeDriving = WeaponState.Equipped
	if WeaponState.Equipped then
		require(script.Parent:WaitForChild("Weapons")).equip(nil)
	end

	-- F gets you out, so other cars' "Drive" prompts stay hidden while you drive
	ProximityPromptService.Enabled = false

	local isBike = def.Kind == "Bike"
	local rig = (if isBike then BikePhysics else Physics).new(model, def)
	local seat = model:FindFirstChild("DriverSeat") :: VehicleSeat?
	local last = PARKED
	local function read()
		return last
	end
	if isBike then
		Bike.setRig(model, rig)
		Bike.startRider(model, player.Character :: Model, read)
	else
		Wheels.setRig(model, rig)
		Cockpit.setDriver(model, read)
	end
	Input.bind(function()
		if isBike then
			-- step off first (the bike holds still), then get out
			Bike.dismount(function()
				Remotes.Exit:FireServer()
			end)
		else
			Remotes.Exit:FireServer()
		end
	end)
	driving = {
		model = model,
		rig = rig,
		conn = RunService.PreSimulation:Connect(function(dt)
			if model.Parent then
				-- no riding off while hopping on or off a bike
				last = if isBike and Bike.busy() then PARKED else Input.read()
				rig:step(dt, last)
				-- other players see the steering wheel and pedals move from these
				if seat then
					seat.ThrottleFloat = last.Throttle
					seat.SteerFloat = last.Steer
				end
			end
		end),
	}
end

local function bind(character: Model)
	stopDriving()
	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	local function check()
		local seat = humanoid.SeatPart
		local model = seat and seat.Name == "DriverSeat" and Vehicles.modelOf(seat)
		if model then
			if not driving or driving.model ~= model then
				startDriving(model)
			end
		else
			stopDriving()
		end
	end
	humanoid:GetPropertyChangedSignal("SeatPart"):Connect(check)
	humanoid.Died:Connect(stopDriving)
	check()
end

function Controller.start()
	Wheels.start()
	Cockpit.start()
	Bike.start()
	player.CharacterAdded:Connect(bind)
	if player.Character then
		task.spawn(bind, player.Character)
	end
end

return Controller
