-- Aiming a weapon (or the gun is up after a hip-fire shot): slows you to the class's AimWalkSpeed and beats Sprint. Legs keep the
-- normal walk layer; the weapon's Aim animation (Weapons/AnimSet) drives the upper body.
-- Holding sprint while aiming gives a side run: moving sideways speeds up toward
-- Config.Movement.AimSprintSpeed (not full sprint), forward and back stay at the aim walk.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Weapons = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Weapons"))
local State = require(Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Client"):WaitForChild("Weapons"):WaitForChild("State"))

-- how sideways you're moving relative to where you aim: 0 straight forward/back, 1 pure side
local function sideways(ctx): number
	local move = ctx.Humanoid.MoveDirection
	local camera = workspace.CurrentCamera
	if move.Magnitude < 0.1 or not camera then
		return 0
	end
	local look = camera.CFrame.LookVector
	local flat = Vector3.new(look.X, 0, look.Z)
	if flat.Magnitude < 0.01 then
		return 0
	end
	flat = flat.Unit
	local right = flat:Cross(Vector3.yAxis)
	local x, z = math.abs(move:Dot(right)), math.abs(move:Dot(flat))
	return if x + z > 0 then x / (x + z) else 0
end

return {
	Name = "Aim",
	Priority = 12,
	CanStart = function()
		return State.Raised and State.Equipped ~= nil
	end,
	Speed = function(ctx)
		local m = ctx.Config.Movement
		local class = State.Equipped and Weapons.classOf(State.Equipped)
		local walk = if class then class.AimWalkSpeed else m.WalkSpeed
		local side = m.AimSprintSpeed
		if side and side > walk and ctx.Input.isDown("Sprint") then
			return walk + (side - walk) * sideways(ctx)
		end
		return walk
	end,
}
