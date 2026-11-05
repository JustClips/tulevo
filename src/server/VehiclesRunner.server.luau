-- Starts the vehicle system (Server.Vehicles) and parks the test cars from
-- Config.Vehicles.TestCars next to the spawn.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local Vehicles = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Vehicles"))
local VehicleService = require(script.Parent:WaitForChild("Vehicles"):WaitForChild("VehicleService"))

VehicleService.start()

local spawnPart = workspace:FindFirstChild("Spawn", true)
local origin = if spawnPart and spawnPart:IsA("BasePart") then spawnPart.Position else Vector3.zero

local params = RaycastParams.new()
params.RespectCanCollide = true

for _, entry in Config.Vehicles.TestCars do
	local def = Vehicles.get(entry.Id)
	if not def then
		warn(`[Vehicles] unknown test car {entry.Id}`)
		continue
	end
	local at = origin + entry.Offset
	local hit = workspace:Raycast(at + Vector3.new(0, 60, 0), Vector3.new(0, -200, 0), params)
	local groundY = if hit then hit.Position.Y else at.Y
	-- drop it from just above ride height; the suspension settles it
	local height = def.Wheels.Radius + def.Suspension.Length * 0.5 - def.Wheels.FL.Y + 0.5
	local pos = Vector3.new(at.X, groundY + height, at.Z)
	VehicleService.spawn(entry.Id, CFrame.new(pos) * CFrame.Angles(0, math.rad(entry.Yaw or 0), 0))
	print(`[Vehicles] {entry.Id} parked near the spawn`)
end
