-- Starts the weapon system (Server.Weapons). Everyone gets Config.Weapons.DefaultLoadout
-- (the carbine rifle); Studio play tests also get Config.Weapons.StudioLoadout.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local WeaponService = require(script.Parent:WaitForChild("Weapons"):WaitForChild("WeaponService"))

local function loadout(player: Player)
	for _, id in Config.Weapons.DefaultLoadout do
		WeaponService.give(player, id)
	end
	if RunService:IsStudio() then
		for _, id in Config.Weapons.StudioLoadout do
			WeaponService.give(player, id)
		end
	end
end
Players.PlayerAdded:Connect(loadout)
for _, p in Players:GetPlayers() do
	loadout(p)
end
