-- Starts the weapon system (Server.Weapons). In Studio play tests everyone gets
-- Config.Weapons.StudioLoadout so the system can be tried before weapons are buyable.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local WeaponService = require(script.Parent:WaitForChild("Weapons"):WaitForChild("WeaponService"))

if RunService:IsStudio() then
	local function loadout(player: Player)
		for _, id in Config.Weapons.StudioLoadout do
			WeaponService.give(player, id)
		end
	end
	Players.PlayerAdded:Connect(loadout)
	for _, p in Players:GetPlayers() do
		loadout(p)
	end
end
