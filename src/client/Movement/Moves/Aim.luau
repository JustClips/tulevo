-- Aiming a weapon: slows you to the class's AimWalkSpeed and beats Sprint. Legs keep the
-- normal walk layer; the weapon's Aim animation (Weapons/AnimSet) drives the upper body.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Weapons = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Weapons"))
local State = require(Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Client"):WaitForChild("Weapons"):WaitForChild("State"))

return {
	Name = "Aim",
	Priority = 12,
	CanStart = function()
		return State.Aiming and State.Equipped ~= nil
	end,
	Speed = function(ctx)
		local class = State.Equipped and Weapons.classOf(State.Equipped)
		return if class then class.AimWalkSpeed else ctx.Config.Movement.WalkSpeed
	end,
}
