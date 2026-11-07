--!strict
--[[
	Opening doors and gates in the city's Blender buildings (workspace.City.Buildings).

	A door is a set of mesh parts named <Kind><N><Role> in one building model, for example
	Swing1Leaf, Swing1Latch, Swing1Pivot (art/blender/hood/build_hood.py swing_gate, the store
	door, the Fort Halden gates). Every <Kind><N>* part moves together except <Kind><N>Pivot,
	whose bounding-box centre is the hinge / axis:
	  Swing  hinged door or gate: turns about the vertical line through the Pivot, up to 85 deg,
	         away from whoever walks up (either way). You push it open with a hand
	         (Tulevo_DoorPush / Tulevo_DoorPushLeft from art/anim/door_push.py).
	  Slide  sliding gate: moves along its long horizontal side by its own length toward the Pivot.
	  Lift   boom barrier: the arm swings up 85 deg about the horizontal axis at the Pivot.
	A building attribute Lock_<Kind><N> = true keeps that door shut.

	Every client runs its own doors from where all characters are (nothing is sent to the server):
	a door opens when someone comes near and closes HOLD seconds after the last one leaves. While a
	door is open its parts stop colliding here. Door parts keep their own mesh collision (no
	CityColliders boxes, Server/CityBuildings); on the server they stay shut.
]]

local ContentProvider = game:GetService("ContentProvider")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local RANGE = { Swing = 5.5, Slide = 9, Lift = 16 } -- studs from the closed door
local LOOKAHEAD = 0.35 -- seconds of walking counted toward the range (opens a bit early when running)
local OPEN_TIME = { Swing = 0.45, Lift = 1.6 } -- seconds; Slide goes by speed
local CLOSE_TIME = { Swing = 0.8, Lift = 1.8 }
local SLIDE_SPEED = 13 -- studs per second
local HOLD = 1.2 -- seconds open after nobody is near
local SWING_ANGLE = math.rad(85)
local LIFT_ANGLE = math.rad(85)
-- You walking up to a closed swing door you face: it stays shut until your hand gets there.
local PUSH_FACING = 0.35 -- facing it this much (dot of look and the way to the door)
local PUSH_NEAR = 2.4 -- the hand goes out from this close standing still...
local PUSH_LEAD = 0.3 -- ...or this many seconds of walking toward it before reaching it
local PUSH_CONTACT = 0.18 -- seconds into the push clip the hand meets the door (door_push.py)
local SCAN_EVERY = 0.1

type Door = {
	model: Model,
	key: string,
	kind: string,
	parts: { BasePart },
	rest: { CFrame },
	collide: { boolean },
	hinge: Vector3, -- Pivot centre
	a: Vector3, -- closed door's footprint segment (horizontal), for distances
	b: Vector3,
	center: Vector3,
	normal: Vector3, -- Swing: horizontal, perpendicular to the leaf
	axis: Vector3, -- Lift: rotation axis
	shift: Vector3, -- Slide: full-open offset
	duration: { open: number, close: number },
	t: number, -- 0 closed .. 1 open (linear progress)
	want: boolean,
	dir: number, -- Swing: +1 / -1 which way it opens (set when it leaves closed)
	lastNear: number,
	openAt: number, -- Swing: wait for the hand to reach the door
	solid: boolean, -- parts colliding (closed)
}

local doors: { Door } = {}
local byModel: { [Model]: { [string]: Door } } = {}

local function isDoorName(name: string): (string?, string?, string?)
	local kind, n, role = name:match("^(%a-)(%d+)(%a*)$")
	if kind == "Swing" or kind == "Slide" or kind == "Lift" then
		return kind, n, role
	end
	return nil, nil, nil
end

local function bounds(parts: { BasePart }): (Vector3, Vector3)
	local lo = Vector3.new(math.huge, math.huge, math.huge)
	local hi = -lo
	for _, p in parts do
		local cf, h = p.CFrame, p.Size / 2
		for _, c in
			{
				Vector3.new(h.X, h.Y, h.Z),
				Vector3.new(-h.X, h.Y, h.Z),
				Vector3.new(h.X, -h.Y, h.Z),
				Vector3.new(h.X, h.Y, -h.Z),
				Vector3.new(-h.X, -h.Y, h.Z),
				Vector3.new(-h.X, h.Y, -h.Z),
				Vector3.new(h.X, -h.Y, -h.Z),
				-h,
			}
		do
			local w = cf:PointToWorldSpace(c)
			lo = lo:Min(w)
			hi = hi:Max(w)
		end
	end
	return lo, hi
end

local function flat(v: Vector3): Vector3
	return Vector3.new(v.X, 0, v.Z)
end

-- closest point on the segment a-b to p (horizontal) and its distance
local function closest(p: Vector3, a: Vector3, b: Vector3): (number, Vector3)
	local ab = flat(b - a)
	local ap = flat(p - a)
	local len2 = ab:Dot(ab)
	local t = if len2 > 1e-6 then math.clamp(ap:Dot(ab) / len2, 0, 1) else 0
	return (ap - ab * t).Magnitude, a + ab * t
end

-- puts a door back exactly where it was built (before its group is rebuilt)
local function reset(door: Door)
	for i, p in door.parts do
		p.CFrame = door.rest[i]
		p.CanCollide = door.collide[i]
	end
end

local function build(model: Model, key: string, kind: string, parts: { BasePart }, pivot: BasePart): Door?
	if #parts == 0 then
		return nil
	end
	local lo, hi = bounds(parts)
	local center = (lo + hi) / 2
	local size = hi - lo
	local hinge = pivot.Position
	local door: Door = {
		model = model,
		key = key,
		kind = kind,
		parts = parts,
		rest = {},
		collide = {},
		hinge = hinge,
		a = center,
		b = center,
		center = center,
		normal = Vector3.zero,
		axis = Vector3.xAxis,
		shift = Vector3.zero,
		duration = { open = OPEN_TIME[kind] or 1, close = CLOSE_TIME[kind] or 1 },
		t = 0,
		want = false,
		dir = 1,
		lastNear = -math.huge,
		openAt = 0,
		solid = true,
	}
	for i, p in parts do
		door.rest[i] = p.CFrame
		door.collide[i] = p.CanCollide
	end
	if kind == "Swing" or kind == "Lift" then
		local u = flat(center - hinge)
		if u.Magnitude < 0.05 then
			return nil
		end
		-- the leaf / arm runs from the hinge out past its centre to its far end
		local reach = 0
		for _, c in
			{
				Vector3.new(lo.X, 0, lo.Z),
				Vector3.new(hi.X, 0, lo.Z),
				Vector3.new(lo.X, 0, hi.Z),
				Vector3.new(hi.X, 0, hi.Z),
			}
		do
			reach = math.max(reach, (c - flat(hinge)):Dot(u.Unit))
		end
		door.a = hinge
		door.b = hinge + u.Unit * reach
		door.normal = Vector3.yAxis:Cross(u.Unit)
		door.axis = u.Unit:Cross(Vector3.yAxis)
	else
		local alongX = size.X >= size.Z
		local length = if alongX then size.X else size.Z
		local dir = if alongX
			then Vector3.new(if hinge.X >= center.X then 1 else -1, 0, 0)
			else Vector3.new(0, 0, if hinge.Z >= center.Z then 1 else -1)
		door.shift = dir * length
		door.a = center - dir * length / 2
		door.b = center + dir * length / 2
		local time = math.max(1.5, length / SLIDE_SPEED)
		door.duration = { open = time, close = time * 1.15 }
	end
	return door
end

local function scanModel(model: Model)
	local groups: { [string]: { kind: string, parts: { BasePart }, pivot: BasePart? } } = {}
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			local kind, n, role = isDoorName(d.Name)
			if kind and n then
				local key = kind .. n
				local g = groups[key]
				if not g then
					g = { kind = kind, parts = {}, pivot = nil }
					groups[key] = g
				end
				if role == "Pivot" then
					g.pivot = d
				else
					table.insert(g.parts, d)
				end
			end
		end
	end
	local old = byModel[model] or {}
	local now = {}
	for key, g in groups do
		local had = old[key]
		if had and #had.parts == #g.parts then
			now[key] = had -- unchanged
			continue
		end
		if had then
			reset(had)
		end
		local pivot = g.pivot
		if pivot then
			local door = build(model, key, g.kind, g.parts, pivot)
			if door then
				now[key] = door
			end
		end
	end
	for key, had in old do
		if not now[key] then
			reset(had)
		end
	end
	byModel[model] = now
	table.clear(doors)
	for _, list in byModel do
		for _, door in list do
			table.insert(doors, door)
		end
	end
end

-- ---------------------------------------------------------------- push clip (local player)
local AnimIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("AnimIds")) :: any
local clips: { [string]: Animation } = {}
for _, name in { "Tulevo_DoorPush", "Tulevo_DoorPushLeft" } do
	if AnimIds[name] then
		local a = Instance.new("Animation")
		a.AnimationId = AnimIds[name]
		clips[name] = a
	end
end
task.spawn(function()
	local list = {}
	for _, a in clips do
		table.insert(list, a)
	end
	pcall(ContentProvider.PreloadAsync, ContentProvider, list)
end)

local player = Players.LocalPlayer
local tracks: { [string]: AnimationTrack } = {}
local tracksFor: Model? = nil
local lastPush = 0

local function push(): boolean
	local char = player.Character
	local hum = char and char:FindFirstChildOfClass("Humanoid")
	local animator = hum and hum:FindFirstChildOfClass("Animator")
	if not (char and animator) or WeaponState.InVehicle then
		return false
	end
	if tracksFor ~= char then
		table.clear(tracks)
		tracksFor = char
	end
	local name = if WeaponState.Equipped then "Tulevo_DoorPushLeft" else "Tulevo_DoorPush"
	local clip = clips[name]
	if not clip then
		return false
	end
	local track = tracks[name]
	if not track then
		local ok, t = pcall(animator.LoadAnimation, animator, clip)
		if not ok then
			return false
		end
		track = t
		track.Priority = Enum.AnimationPriority.Action2
		track.Looped = false
		tracks[name] = track
	end
	track:Play(0.12)
	return true
end

-- ---------------------------------------------------------------- finding doors
local city = workspace:WaitForChild("City", 30)
local buildings = city and city:WaitForChild("Buildings", 30)
if not buildings then
	return
end

local dirty: { [Model]: number } = {}
local function topModel(d: Instance): Model?
	local m = d
	while m and m.Parent ~= buildings do
		m = m.Parent :: Instance
	end
	return if m and m:IsA("Model") then m else nil
end
for _, m in buildings:GetChildren() do
	if m:IsA("Model") then
		dirty[m] = 0
	end
end
buildings.DescendantAdded:Connect(function(d)
	if d:IsA("BasePart") and isDoorName(d.Name) then
		local m = topModel(d)
		if m then
			dirty[m] = os.clock() + 0.5 -- let the rest of the model's parts arrive
		end
	end
end)
buildings.ChildRemoved:Connect(function(m)
	if m:IsA("Model") and byModel[m] then
		byModel[m] = nil
		dirty[m] = nil
		table.clear(doors)
		for _, list in byModel do
			for _, door in list do
				table.insert(doors, door)
			end
		end
	end
end)

-- ---------------------------------------------------------------- running
local function ease(t: number): number
	return t * t * (3 - 2 * t)
end

local function place(door: Door)
	local k = ease(door.t)
	local turn: CFrame
	if door.kind == "Swing" then
		turn = CFrame.new(door.hinge) * CFrame.Angles(0, door.dir * SWING_ANGLE * k, 0) * CFrame.new(-door.hinge)
	elseif door.kind == "Lift" then
		turn = CFrame.new(door.hinge) * CFrame.fromAxisAngle(door.axis, LIFT_ANGLE * k) * CFrame.new(-door.hinge)
	else
		turn = CFrame.new(door.shift * k)
	end
	local cfs = table.create(#door.parts)
	for i, cf in door.rest do
		cfs[i] = turn * cf
	end
	workspace:BulkMoveTo(door.parts, cfs, Enum.BulkMoveMode.FireCFrameChanged)
	local solid = door.t < 0.02
	if solid ~= door.solid then
		door.solid = solid
		for i, p in door.parts do
			p.CanCollide = solid and door.collide[i]
		end
	end
end

local nextScan = 0
type Root = { pos: Vector3, vel: Vector3, look: Vector3, isMe: boolean }
local roots: { Root } = {}
local me: Root? = nil

local function gather()
	table.clear(roots)
	me = nil
	for _, plr in Players:GetPlayers() do
		local char = plr.Character
		local root = char and (char.PrimaryPart or char:FindFirstChild("HumanoidRootPart"))
		if root and root:IsA("BasePart") then
			local r = {
				pos = root.Position,
				vel = root.AssemblyLinearVelocity,
				look = root.CFrame.LookVector,
				isMe = plr == player,
			}
			table.insert(roots, r)
			if r.isMe then
				me = r
			end
		end
	end
end

-- nearest character to a door, counting LOOKAHEAD seconds of their walking
local function nearest(door: Door, skipMe: boolean): (number, Root?)
	local best, who = math.huge, nil
	for _, r in roots do
		if (skipMe and r.isMe) or math.abs(r.pos.Y - door.center.Y) > 14 then
			continue
		end
		local d = math.min((closest(r.pos, door.a, door.b)), (closest(r.pos + flat(r.vel) * LOOKAHEAD, door.a, door.b)))
		if d < best then
			best, who = d, r
		end
	end
	return best, who
end

-- swing doors open away from whoever opens them
local function awayFrom(door: Door, r: Root)
	door.dir = if (r.pos - door.hinge):Dot(door.normal) > 0 then -1 else 1
end

-- The local player walking up to a closed swing door they face: it waits for their hand. Returns
-- "push" when the hand goes out now, "wait" while they're still walking up, nil otherwise.
local function walkUp(door: Door, now: number): string?
	local r = me
	if not r or door.kind ~= "Swing" or door.want or door.t >= 0.02 or WeaponState.InVehicle then
		return nil
	end
	if math.abs(r.pos.Y - door.center.Y) > 6 then
		return nil
	end
	local d, q = closest(r.pos, door.a, door.b)
	local to, look = flat(q - r.pos), flat(r.look)
	if d > RANGE.Swing + 1 or to.Magnitude < 0.2 or look.Magnitude < 0.1 or look.Unit:Dot(to.Unit) < PUSH_FACING then
		return nil
	end
	local toward = math.max(0, flat(r.vel):Dot(to.Unit))
	if d < math.max(PUSH_NEAR, 1.6 + toward * PUSH_LEAD) and now - lastPush > 0.6 then
		return "push"
	end
	return "wait"
end

local function scan(now: number)
	for m, at in dirty do
		if now >= at then
			dirty[m] = nil
			if m.Parent == buildings then
				scanModel(m)
			end
		end
	end
	gather()
	for _, door in doors do
		if door.model:GetAttribute("Lock_" .. door.key) == true then
			door.want = false
			continue
		end
		local walk = walkUp(door, now)
		if walk == "push" and me then
			door.want = true
			door.lastNear = now
			awayFrom(door, me)
			lastPush = now
			door.openAt = now + (if push() then PUSH_CONTACT else 0)
			continue
		end
		local best, who = nearest(door, walk == "wait")
		if who and best < RANGE[door.kind] then
			door.lastNear = now
			if not door.want then
				door.want = true
				if door.kind == "Swing" and door.t < 0.02 then
					awayFrom(door, who)
					door.openAt = now
				end
			end
		elseif door.want and now - door.lastNear > HOLD then
			door.want = false
		end
	end
end

RunService.Heartbeat:Connect(function(dt)
	local now = os.clock()
	if now >= nextScan then
		nextScan = now + SCAN_EVERY
		scan(now)
	end
	for _, door in doors do
		local goal = if door.want and now >= door.openAt then 1 else 0
		if door.t ~= goal then
			local rate = dt / (if goal > door.t then door.duration.open else door.duration.close)
			door.t = if goal > door.t then math.min(1, door.t + rate) else math.max(0, door.t - rate)
			place(door)
		end
	end
end)
