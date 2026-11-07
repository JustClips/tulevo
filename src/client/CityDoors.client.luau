--!strict
--[[
	Opening doors and gates in the city's Blender buildings (workspace.City.Buildings), GTA style.

	A door is a set of mesh parts named <Kind><N><Role> in one building model, for example
	Swing1Leaf, Swing1Latch, Swing1Pivot (art/blender/hood/build_hood.py swing_gate, the store
	door, the Fort Halden gates). Every <Kind><N>* part moves together except <Kind><N>Pivot,
	whose bounding-box centre is the hinge / axis:
	  Swing  hinged door or gate, swinging free both ways about the vertical line through the Pivot
	         (up to 85 deg). Nothing opens it but bodies: walk into it and it gives way in front of
	         you, as far as you push it (run into it and it flies open); let go and it swings back
	         shut on its own, past closed a little and back, like a door on a spring hinge. Walking
	         up to it facing it, your hand comes up and pushes (Tulevo_DoorPush / Tulevo_DoorPushLeft
	         from art/anim/door_push.py).
	  Slide  sliding gate: moves along its long horizontal side by its own length toward the Pivot.
	  Lift   boom barrier: the arm swings up 85 deg about the horizontal axis at the Pivot.
	  (Slide and Lift open when someone comes near and close HOLD seconds after the last one leaves.)
	A building attribute Lock_<Kind><N> = true keeps that door shut.

	Every client runs its own doors from where all characters are (nothing is sent to the server).
	A moving door's parts stop colliding here. Door parts keep their own mesh collision (no
	CityColliders boxes, Server/CityBuildings); on the server they stay shut.
]]

local ContentProvider = game:GetService("ContentProvider")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local RANGE = { Slide = 9, Lift = 16 } -- studs from the closed gate / arm
local LOOKAHEAD = 0.35 -- seconds of walking counted toward the range (opens a bit early when running)
local OPEN_TIME = { Lift = 1.6 } -- seconds; Slide goes by speed
local CLOSE_TIME = { Lift = 1.8 }
local SLIDE_SPEED = 13 -- studs per second
local HOLD = 1.2 -- seconds open after nobody is near
local LIFT_ANGLE = math.rad(85)
local SCAN_EVERY = 0.1
-- Swing doors: a body is a circle of BODY studs around the character; the leaf can't be inside it.
local BODY = 1.2
local SWING_MAX = math.rad(85) -- stops (it bounces off them a little)
local SPRING = 7 -- closing spring (rad/s^2 per rad)...
local DAMP = 3.6 -- ...and damping: swings past closed a touch and settles
local MAX_SPIN = 9 -- rad/s
-- your hand comes up when you walk into a closed door facing it, this long before you'd touch it
local PUSH_AHEAD = 0.18 -- seconds (door_push.py: the hand is out at 0.2 s)

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
	normal: Vector3, -- Swing: horizontal, perpendicular to the closed leaf (+angle swings the leaf this way)
	u: Vector3, -- Swing / Lift: hinge -> tip, horizontal unit
	len: number, -- Swing / Lift: hinge -> tip length
	axis: Vector3, -- Lift: rotation axis
	shift: Vector3, -- Slide: full-open offset
	duration: { open: number, close: number },
	t: number, -- Slide / Lift: 0 closed .. 1 open (linear progress)
	want: boolean,
	lastNear: number,
	angle: number, -- Swing: radians, signed
	spin: number, -- Swing: rad/s
	sides: { [Player]: number }, -- Swing: which side of the leaf each body near it is on
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
		u = Vector3.xAxis,
		len = 0,
		axis = Vector3.xAxis,
		shift = Vector3.zero,
		duration = { open = OPEN_TIME[kind] or 1, close = CLOSE_TIME[kind] or 1 },
		t = 0,
		want = false,
		lastNear = -math.huge,
		angle = 0,
		spin = 0,
		sides = {},
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
		door.u = u.Unit
		door.len = reach
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
			warn(`[CityDoors] could not load {name}: {t}`)
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

local function setSolid(door: Door, solid: boolean)
	if solid ~= door.solid then
		door.solid = solid
		for i, p in door.parts do
			p.CanCollide = solid and door.collide[i]
		end
	end
end

local function place(door: Door)
	local turn: CFrame
	if door.kind == "Swing" then
		turn = CFrame.new(door.hinge) * CFrame.Angles(0, door.angle, 0) * CFrame.new(-door.hinge)
		setSolid(door, math.abs(door.angle) < 0.03)
	else
		local k = ease(door.t)
		if door.kind == "Lift" then
			turn = CFrame.new(door.hinge) * CFrame.fromAxisAngle(door.axis, LIFT_ANGLE * k) * CFrame.new(-door.hinge)
		else
			turn = CFrame.new(door.shift * k)
		end
		setSolid(door, door.t < 0.02)
	end
	local cfs = table.create(#door.parts)
	for i, cf in door.rest do
		cfs[i] = turn * cf
	end
	workspace:BulkMoveTo(door.parts, cfs, Enum.BulkMoveMode.FireCFrameChanged)
end

-- intent: where they're trying to go (yours: the stick / WASD; others: their velocity / 16)
type Root = { who: Player, pos: Vector3, vel: Vector3, look: Vector3, intent: Vector3, isMe: boolean }
local roots: { Root } = {}

local function gather()
	table.clear(roots)
	for _, plr in Players:GetPlayers() do
		local char = plr.Character
		local root = char and (char.PrimaryPart or char:FindFirstChild("HumanoidRootPart"))
		if root and root:IsA("BasePart") then
			local vel = root.AssemblyLinearVelocity
			local hum = char:FindFirstChildOfClass("Humanoid")
			local intent = if plr == player and hum then flat(hum.MoveDirection) else flat(vel) / 16
			table.insert(roots, {
				who = plr,
				pos = root.Position,
				vel = vel,
				look = root.CFrame.LookVector,
				intent = intent,
				isMe = plr == player,
			})
		end
	end
end

-- ---------------------------------------------------------------- swing doors (every frame)
-- Your hand comes up as you walk into a (nearly) closed door you're facing.
local function maybePush(door: Door, r: Root, rel: Vector3, now: number)
	if math.abs(door.angle) > 0.3 or now - lastPush < 0.9 or WeaponState.InVehicle then
		return
	end
	local uc = door.u * math.cos(door.angle) + door.normal * math.sin(door.angle) -- leaf as it is now
	local nc = Vector3.yAxis:Cross(uc)
	local along = rel:Dot(uc) / door.len
	if along < 0.12 or along > 0.98 then
		return -- the hand would miss the leaf (hinge end / past the edge)
	end
	local side = rel:Dot(nc)
	local into = nc * (if side > 0 then -1 else 1)
	local look = flat(r.look)
	if r.intent:Dot(into) < 0.45 or look.Magnitude < 0.1 or look.Unit:Dot(into) < 0.3 then
		return
	end
	local speed = math.max(0, flat(r.vel):Dot(into))
	if math.abs(side) < BODY + 0.3 + speed * PUSH_AHEAD and push() then
		lastPush = now
	end
end

local function swingStep(door: Door, dt: number, now: number, locked: boolean)
	local before = door.angle
	-- spring hinge pulls it shut
	door.spin += (-SPRING * door.angle - DAMP * door.spin) * dt
	door.spin = math.clamp(door.spin, -MAX_SPIN, MAX_SPIN)
	door.angle += door.spin * dt
	local pushed = false
	local cap = 0 -- how fast the pushers can swing it (their speed around the hinge)
	local reach = door.len + 0.4
	for _, r in roots do
		local rel = flat(r.pos - door.hinge)
		local dist = rel.Magnitude
		if r.isMe and not locked and dist < door.len + 5 and math.abs(r.pos.Y - door.center.Y) < 6 then
			maybePush(door, r, rel, now)
		end
		-- (right at the hinge the jamb and wall are in the way: no pushing from there)
		if locked or dist > reach or dist < BODY + 0.2 or math.abs(r.pos.Y - door.center.Y) > 6 then
			door.sides[r.who] = nil
			continue
		end
		local phi = math.atan2(rel:Dot(door.normal), rel:Dot(door.u)) -- where they are, as a leaf angle
		if math.abs(phi) > math.rad(150) then
			door.sides[r.who] = nil -- behind the hinge, on the wall side
			continue
		end
		local half = math.asin(math.min(1, BODY / math.max(dist, BODY))) -- how wide the body looks from the hinge
		local side = door.sides[r.who]
		if not side then
			-- which side of the leaf they came from (decided once, while they're near)
			if math.abs(phi - before) < half * 0.9 then
				continue -- right on the leaf line beside it (in the wall / jamb): ignore until clear
			end
			side = if phi > before then 1 else -1
			door.sides[r.who] = side
		end
		if side > 0 and door.angle > phi - half then
			door.angle = phi - half
			pushed = true
		elseif side < 0 and door.angle < phi + half then
			door.angle = phi + half
			pushed = true
		else
			continue
		end
		cap = math.max(cap, flat(r.vel).Magnitude / dist * 1.3 + 0.5)
	end
	if pushed then
		cap = math.min(cap, MAX_SPIN)
		door.spin = math.clamp((door.angle - before) / math.max(dt, 1 / 240), -cap, cap)
	end
	if door.angle > SWING_MAX then
		door.angle = SWING_MAX
		door.spin = -math.abs(door.spin) * 0.3
	elseif door.angle < -SWING_MAX then
		door.angle = -SWING_MAX
		door.spin = math.abs(door.spin) * 0.3
	end
	if not pushed and math.abs(door.angle) < 0.002 and math.abs(door.spin) < 0.02 then
		door.angle, door.spin = 0, 0
	end
	if door.angle ~= before then
		place(door)
	end
end

-- ---------------------------------------------------------------- sliding gates + barriers
local function nearest(door: Door): (number, Root?)
	local best, who = math.huge, nil
	for _, r in roots do
		if math.abs(r.pos.Y - door.center.Y) > 14 then
			continue
		end
		local d = math.min((closest(r.pos, door.a, door.b)), (closest(r.pos + flat(r.vel) * LOOKAHEAD, door.a, door.b)))
		if d < best then
			best, who = d, r
		end
	end
	return best, who
end

local nextScan = 0
local function scan(now: number)
	for m, at in dirty do
		if now >= at then
			dirty[m] = nil
			if m.Parent == buildings then
				scanModel(m)
			end
		end
	end
	for _, door in doors do
		if door.kind == "Swing" then
			continue
		end
		if door.model:GetAttribute("Lock_" .. door.key) == true then
			door.want = false
			continue
		end
		local best, who = nearest(door)
		if who and best < RANGE[door.kind] then
			door.lastNear = now
			door.want = true
		elseif door.want and now - door.lastNear > HOLD then
			door.want = false
		end
	end
end

RunService.Heartbeat:Connect(function(dt)
	local now = os.clock()
	dt = math.min(dt, 1 / 20)
	gather()
	if now >= nextScan then
		nextScan = now + SCAN_EVERY
		scan(now)
	end
	for _, door in doors do
		if door.kind == "Swing" then
			if door.angle == 0 and door.spin == 0 then
				-- at rest: only wake up when someone is near the hinge
				local near = false
				local r2 = (door.len + 5) ^ 2
				for _, r in roots do
					local d = r.pos - door.hinge
					if d.X * d.X + d.Z * d.Z < r2 then
						near = true
						break
					end
				end
				if not near then
					if next(door.sides) then
						table.clear(door.sides)
					end
					continue
				end
			end
			swingStep(door, dt, now, door.model:GetAttribute("Lock_" .. door.key) == true)
			continue
		end
		local goal = if door.want then 1 else 0
		if door.t ~= goal then
			local rate = dt / (if goal > door.t then door.duration.open else door.duration.close)
			door.t = if goal > door.t then math.min(1, door.t + rate) else math.max(0, door.t - rate)
			place(door)
		end
	end
end)
