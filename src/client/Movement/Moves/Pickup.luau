--[[
	Picking an item up off the ground (GTA style): bend the knees, reach down, grab it, stand
	back up. Clips Tulevo_Pickup (right hand) and Tulevo_PickupLeft (left hand, used while a gun
	is in the right hand) from art/anim/pickup.py.

	Press E (no hold) on a dropped item (Client/Inventory): the character first walks up to it (Humanoid:MoveTo,
	so pushing the stick cancels the walk), turns to face it, plays the clip and asks the server
	to take the item at GRAB_AT, when the hand closes on it. Too far away after the walk (or
	cancelled): the clip still plays where you stand. Dragging an item out of the
	inventory's Ground list only plays the clip (the item has already moved).

	The player is rooted while it plays (Locked: no moving or jumping, Speed 0); weapons can't fire
	meanwhile (Movement.busy).
	Fades in and out over Config.Movement.BlendTime like every other move.

	Other scripts: require this module and call Pickup.request(position, grab?, walk?).
]]

local ContentProvider = game:GetService("ContentProvider")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

-- Client/Weapons/State (plain state table, no requires back into Movement)
local WeaponState = require(script.Parent.Parent.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local LENGTH = 1.2 -- clip length (art/anim/pickup.py LENGTH)
local GRAB_AT = 0.5 -- the hand closes on the item (pickup.py GRAB_AT)
local REACH = 1.15 -- the clip's hand lands this far in front of the root (pickup.py PICK_SPOT)
local WALK_TIMEOUT = 2.2 -- seconds to walk up to it before giving up (the clip plays anyway)
local TURN_TIME = 0.15

-- download both clips up front (the first pickup used to finish before its clip had loaded)
task.spawn(function()
	local ids = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("AnimIds")) :: any
	local list = {}
	for _, name in { "Tulevo_Pickup", "Tulevo_PickupLeft" } do
		if ids[name] then
			local a = Instance.new("Animation")
			a.AnimationId = ids[name]
			table.insert(list, a)
		end
	end
	pcall(ContentProvider.PreloadAsync, ContentProvider, list)
end)

type Pending = { pos: Vector3, grab: (() -> ())?, ready: boolean, at: number }

local pending: Pending? = nil
local walkToken = 0

-- Output lines for chasing "no animation" reports (only when something goes off the normal path)
local function note(text: string)
	print(`[Pickup] {text}`)
end

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
		note("no character / seated: taken without the clip")
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
		if not close() then
			note(`walk-up ended {math.floor(flatDistance(root.Position, pos) * 10) / 10} studs away: clip plays here`)
		end
		humanoid:MoveTo(root.Position) -- end the walk (MoveTo) where we are
		-- Dev 2026-11-06 ("sometimes it doesn't play at all"): always play the clip, even if the
		-- walk was cut short or blocked
		if humanoid.Health > 0 then
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
	state(ctx) -- load the clips with the character, so the first pickup isn't skipped while they download
	local p = pending
	if not p or not p.ready then
		return false
	end
	if os.clock() - p.at > 6 or ctx.Humanoid.SeatPart then
		note(`couldn't start (grounded {ctx.Grounded}, state {ctx.Humanoid:GetState().Name}, move {ctx.Active}): taken without the clip`)
		pending = nil
		grabNow(p)
		return false
	end
	-- standing on something (FloorMaterial alone: the state can flicker to Landed/Freefall for a
	-- frame after a walk or a drop, and that used to keep the clip from starting)
	return ctx.Humanoid.FloorMaterial ~= Enum.Material.Air
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
	s.track:Stop(0)
	s.track:Play(blend * 0.5, 1, 1)
	if s.track.Length <= 0 then
		note("clip not loaded yet when it started")
	end
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
		note(`clip cut short at {math.floor(s.t * 100) / 100}s (move {ctx.Active})`)
		grabNow(s.job) -- cut short (jumped, knocked...): still take it
	end
	s.job = nil
	ctx.Humanoid.AutoRotate = true
end

return Pickup
