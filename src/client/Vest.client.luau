--[[
	Armor vest off / on, from the inventory window (Client/Inventory): drag the vest out of
	the Armor slot / drop one on it. (No key: Dev removed V.)

	Plays Tulevo_VestOff / Tulevo_VestOn (art/anim/vest.py) and tells the server, which moves
	the real vest model with the hands on the same beats and takes the armor off / puts it
	back (Server/Armor.server.luau). A gun in hand goes on the back first (both hands are
	needed) and comes back out when you're done. Taken off, the vest goes into the inventory
	with the armor it had left. Weapons can't be taken out meanwhile (Weapons/State.Dressing), and that lock always
	lifts at the end, even on an error or a respawn.
]]

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
	return gun ~= nil and gun:GetAttribute("On") == "RightHand" -- Server/Weapons/GunModel
end

local token = 0 -- bumps on every toggle and respawn, so a stale one never unlocks a newer one

local function dress(c: Model, h: Humanoid, animator: Animator, wearing: boolean, uid: string?, where: { any }?)
	-- both hands are needed: the gun goes on the back first
	if WeaponState.Equipped then
		Weapons.equip(nil)
		task.wait(1.0) -- the holster clip (art/anim/gun.py HOLSTER length 1.05)
	end
	local start = os.clock()
	while gunInHand(c) and os.clock() - start < 2 do
		task.wait(0.05)
	end
	if h.Health <= 0 or h.Parent ~= c or gunInHand(c) then
		return
	end
	local name = if wearing then "Tulevo_VestOff" else "Tulevo_VestOn"
	local t = clip(animator, name)
	local w = where or {}
	Remotes.Vest:FireServer(uid, w[1], w[2], w[3])
	if t then
		t:Play(0.1, 1, 1)
	end
	task.wait(LENGTH[name])
end

-- uid: put on this vest from the inventory (dragged onto the Armor slot); nil = take off.
-- to, slot, rot: where the vest taken off goes (dragged out of the Armor slot).
local function toggle(uid: string?, to: string?, slot: number?, rot: boolean?)
	local c = player.Character
	local h = c and c:FindFirstChildOfClass("Humanoid")
	local animator = h and h:FindFirstChildOfClass("Animator")
	if busy or not c or not h or not animator or h.Health <= 0 or h.SeatPart or WeaponState.InVehicle or Movement.busy() then
		return
	end
	local wearing = h:GetAttribute("ArmorItem") ~= nil
	if uid and wearing then
		return -- already wearing one
	end
	if not wearing and player:GetAttribute("SpareArmor") == nil then
		return -- no vest in the inventory (Server/Inventory sets SpareArmor)
	end
	busy = true
	WeaponState.Dressing = true
	token += 1
	local mine = token
	local had = WeaponState.Equipped
	task.spawn(function()
		local ok, err = pcall(dress, c, h, animator, wearing, uid, { to, slot, rot })
		if not ok then
			warn(`[Vest] {err}`)
		end
		if token ~= mine then
			return -- respawned meanwhile (already unlocked)
		end
		-- always unlock, even if something above failed
		WeaponState.Dressing = false
		busy = false
		-- and the gun you had comes back out
		if had and player.Character == c and h.Health > 0 and not h.SeatPart and not WeaponState.InVehicle and not WeaponState.Equipped then
			Weapons.equip(had)
		end
	end)
end

player.CharacterAdded:Connect(function()
	token += 1
	busy = false
	WeaponState.Dressing = false
end)

-- the inventory window (Client/Inventory) takes the vest off / puts one on through this
local toggleEvent = Instance.new("BindableEvent")
toggleEvent.Name = "VestToggle"
toggleEvent.Event:Connect(toggle)
toggleEvent.Parent = script

