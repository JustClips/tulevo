--[[
	Picking an item up off the ground (GTA style): bend the knees, reach down, grab it, stand
	back up. Clips Tulevo_Pickup (right hand) and Tulevo_PickupLeft (left hand, used while a gun
	is in the right hand) from art/anim/pickup.py.

	Press E (no hold) on a dropped item (Client/Inventory): the character first walks up to it (Humanoid:MoveTo,
	so pushing the stick cancels the walk), turns to face it, plays the clip and asks the server
	to take the item at GRAB_AT, when the hand closes on it. Too far away after the walk (or
	cancelled): the item is taken straight away with no animation. Dragging an item out of the
	inventory's Ground list only plays the clip (the item has already moved).

	The player is rooted while it plays (Locked: no moving or jumping, Speed 0); weapons can't fire
	meanwhile (Movement.busy).
	Fades in and out over Config.Movement.BlendTime like every other move.

	Other scripts: require this module and call Pickup.request(position, grab?, walk?).
]]

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

-- Client/Weapons/State (plain state table, no requires back into Movement)
local WeaponState = require(script.Parent.Parent.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local LENGTH = 1.2 -- clip length (art/anim/pickup.py LENGTH)
local GRAB_AT = 0.5 -- the hand closes on the item (pickup.py GRAB_AT)
local REACH = 1.15 -- the clip's hand lands this far in front of the root (pickup.py PICK_SPOT)
local WALK_TIMEOUT = 1.6 -- seconds to walk up to it before giving up
local PLAY_RANGE = 3.2 -- flat studs: further than this when the walk ends -> no animation
local TURN_TIME = 0.15

type Pending = { pos: Vector3, grab: (() -> ())?, ready: boolean, at: number }

local pending: Pending? = nil
local walkToken = 0

local function grabNow(p: Pending)
	local grab = p.grab
	p.grab = nil
	if grab then
		task.spawn(grab)
	end
end

local function flatDistance(a: Vector3, b: Vector3): number
	return Vector3.new(a.X - b.X, 0, a.Z - b.Z).Magnitude
end

local Pickup = {
	Name = "Pickup",
	Priority = 25, -- over Aim / Air, under Roll
	UsesGait = false,
	Locked = true, -- Dev 2026-11-06: can't move or jump until the clip is over
}

-- Start a pickup of something lying at pos. grab (optional) runs once, when the hand reaches
-- it (or right away if the clip can't play). walk = walk up to it first.
function Pickup.request(pos: Vector3, grab: (() -> ())?, walk: boolean?)
	if pending and pending.grab then
		grabNow(pending) -- a pickup still waiting: don't lose it
	end
	local p: Pending = { pos = pos, grab = grab, ready = false, at = os.clock() }
	pending = p
	walkToken += 1
	local token = walkToken
	local character = Players.LocalPlayer.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not humanoid or not root or humanoid.Health <= 0 or humanoid.SeatPart then
		pending = nil
		grabNow(p)
		return
	end
	local function close(): boolean
		return flatDistance(root.Position, pos) <= REACH + 0.45
	end
	if not walk or close() then
		p.ready = true
		return
	end
	task.spawn(function()
		local flat = Vector3.new(pos.X - root.Position.X, 0, pos.Z - root.Position.Z)
		local stand = pos - flat.Unit * REACH
		humanoid:MoveTo(Vector3.new(stand.X, root.Position.Y, stand.Z))
		local t0 = os.clock()
		while token == walkToken and os.clock() - t0 < WALK_TIMEOUT do
			if close() or humanoid.Health <= 0 then
				break
			end
			RunService.Heartbeat:Wait()
		end
		if token ~= walkToken then
			return
		end
		humanoid:Move(Vector3.zero) -- end the walk (MoveTo) where we are
		if flatDistance(root.Position, pos) <= PLAY_RANGE and humanoid.Health > 0 then
			p.ready = true
		else
			pending = nil
			grabNow(p)
		end
	end)
end

local function state(ctx)
	if not ctx.Pickup then
		local function load(name)
			local track = ctx.LoadClip(name)
			track.Priority = Enum.AnimationPriority.Action4 -- over the gun and item-use clips
			track.Looped = false
			return track
		end
		ctx.Pickup = { right = load("Tulevo_Pickup"), left = load("Tulevo_PickupLeft"), track = nil, t = 0, job = nil }
	end
	return ctx.Pickup
end

local function gunInHand(): boolean
	return WeaponState.Equipped ~= nil
end

Pickup.CanStart = function(ctx)
	local p = pending
	if not p or not p.ready then
		return false
	end
	if os.clock() - p.at > 4 or ctx.Humanoid.SeatPart then
		pending = nil
		grabNow(p)
		return false
	end
	return ctx.Grounded
end

Pickup.KeepGoing = function(ctx)
	local s = state(ctx)
	return s.t < LENGTH - ctx.Config.Movement.BlendTime * 0.5 and ctx.Humanoid.Health > 0
end

Pickup.Speed = function(_ctx)
	return 0
end

Pickup.Start = function(ctx)
	local s = state(ctx)
	local p = pending :: Pending
	pending = nil
	s.job, s.t = p, 0
	s.track = if gunInHand() then s.left else s.right
	local blend = ctx.Config.Movement.BlendTime
	s.track:Play(blend * 0.5, 1, 1)
	ctx.Humanoid.AutoRotate = false
	-- turn to face the item
	local root = ctx.Root
	local flat = Vector3.new(p.pos.X - root.Position.X, 0, p.pos.Z - root.Position.Z)
	s.from = root.CFrame.Rotation
	s.to = if flat.Magnitude > 0.2 then CFrame.lookAt(Vector3.zero, flat.Unit) else s.from
end

Pickup.Update = function(ctx, dt)
	local s = state(ctx)
	s.t += dt
	if s.t <= TURN_TIME + dt then
		local u = math.clamp(s.t / TURN_TIME, 0, 1)
		local root = ctx.Root
		root.CFrame = CFrame.new(root.Position) * s.from:Lerp(s.to, u * u * (3 - 2 * u))
	end
	-- rooted: no sliding from leftover speed, input can't push the body
	local v = ctx.Root.AssemblyLinearVelocity
	ctx.Root.AssemblyLinearVelocity = Vector3.new(0, v.Y, 0)
	if s.job and s.t >= GRAB_AT then
		grabNow(s.job)
		s.job = nil
	end
end

Pickup.Stop = function(ctx)
	local s = state(ctx)
	if s.track then
		s.track:Stop(ctx.Config.Movement.BlendTime)
		s.track = nil
	end
	if s.job and ctx.Humanoid.Health > 0 then
		grabNow(s.job) -- cut short (jumped, knocked...): still take it
	end
	s.job = nil
	ctx.Humanoid.AutoRotate = true
end

return Pickup
