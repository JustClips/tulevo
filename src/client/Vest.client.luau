--[[
	Armor vest off / on: V (gamepad D-pad up, phone "Vest" button).

	Plays Tulevo_VestOff / Tulevo_VestOn (art/anim/vest.py) and tells the server, which moves
	the real vest model with the hands on the same beats and takes the armor off / puts it
	back (Server/Armor.server.luau). A gun in hand goes on the back first (both hands are
	needed). The armor you had is kept while the vest is off.
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local AnimIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("AnimIds"))
local Remotes = ReplicatedStorage:WaitForChild("ArmorRemotes")
local Weapons = require(script.Parent:WaitForChild("Weapons"))
local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))
local Movement = require(script.Parent:WaitForChild("Movement"))

local player = Players.LocalPlayer
local LENGTH = { Tulevo_VestOn = 1.75, Tulevo_VestOff = 1.35 }

local tracks: { [Animator]: { [string]: AnimationTrack } } = {}
local busy = false

local function clip(animator: Animator, name: string): AnimationTrack?
	local set = tracks[animator]
	if not set then
		set = {}
		tracks[animator] = set
		animator.Destroying:Connect(function()
			tracks[animator] = nil
		end)
	end
	if not set[name] then
		local id = (AnimIds :: any)[name]
		if not id then
			return nil
		end
		local a = Instance.new("Animation")
		a.AnimationId = id
		local t = animator:LoadAnimation(a)
		t.Priority = Enum.AnimationPriority.Action2 -- over the walk and jump arms
		t.Looped = false
		set[name] = t
	end
	return set[name]
end

local function gunInHand(c: Model): boolean
	local gun = c:FindFirstChild("Gun")
	local weld = gun and gun:FindFirstChild("GunWeld", true)
	return weld ~= nil and weld:IsA("Weld") and weld.Part0 ~= nil and weld.Part0.Name == "RightHand"
end

local function toggle()
	local c = player.Character
	local h = c and c:FindFirstChildOfClass("Humanoid")
	local animator = h and h:FindFirstChildOfClass("Animator")
	if busy or not c or not h or not animator or h.Health <= 0 or h.SeatPart or WeaponState.InVehicle or Movement.busy() then
		return
	end
	local wearing = h:GetAttribute("ArmorItem") ~= nil
	if not wearing and h:GetAttribute("StoredArmorItem") == nil then
		return -- no vest
	end
	busy = true
	WeaponState.Dressing = true
	task.spawn(function()
		-- both hands are needed: the gun goes on the back first
		if WeaponState.Equipped then
			Weapons.equip(nil)
			local start = os.clock()
			task.wait(0.9)
			while gunInHand(c) and os.clock() - start < 2 do
				task.wait(0.05)
			end
		end
		if h.Health > 0 and h.Parent == c then
			local name = if wearing then "Tulevo_VestOff" else "Tulevo_VestOn"
			local t = clip(animator, name)
			Remotes.Vest:FireServer()
			if t then
				t:Play(0.1, 1, 1)
			end
			task.wait(LENGTH[name])
		end
		WeaponState.Dressing = false
		busy = false
	end)
end

ContextActionService:BindAction("ArmorVest", function(_, state)
	if state == Enum.UserInputState.Begin then
		toggle()
	end
	return Enum.ContextActionResult.Sink
end, true, Enum.KeyCode.V, Enum.KeyCode.DPadUp)
ContextActionService:SetTitle("ArmorVest", "Vest")
