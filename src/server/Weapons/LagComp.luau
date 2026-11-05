--[[
	Lag compensation for gun hits (server only).

	Every player's body parts are recorded RATE times a second (the last HISTORY seconds).
	When a shot arrives, the server works out how old the shooter's view was from the
	shooter's ping, which Roblox measures itself (the client never sends a time, so it
	can't be faked), and checks the bullet against everyone's hitboxes as they were then.

	Abuse limits:
	  * rewind is capped at Config.Weapons.LagComp.MaxRewind (a lag switch can't reach further
	    back than that),
	  * the map is never rewound: the bullet is also raycast against the real world now, so
	    walls and cover always block,
	  * the shot origin, spread and damage stay server-side (Hitscan / WeaponService).

	No physics or real parts are moved: hits are maths (ray vs box) on the recorded CFrames,
	and only players near the bullet's path are checked.

		LagComp.cast(shooter, origin, dir, maxDist) -> (player?, partName?, distance?)
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local C = Config.Weapons.LagComp

local LagComp = {}

local PARTS = {
	"Head", "UpperTorso", "LowerTorso",
	"LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
	"LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
}
local NEAR = 7 -- studs: players whose root is further than this from the bullet line are skipped

type Snapshot = { t: number, cf: { [string]: CFrame } }
type Track = { snaps: { Snapshot }, sizes: { [string]: Vector3 }, character: Model }

local tracks: { [Player]: Track } = {}

local function record(player: Player, now: number)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	if not character or not humanoid or humanoid.Health <= 0 then
		tracks[player] = nil
		return
	end
	local track = tracks[player]
	if not track or track.character ~= character then
		track = { snaps = {}, sizes = {}, character = character }
		tracks[player] = track
	end
	local cf = {}
	for _, name in PARTS do
		local part = character:FindFirstChild(name)
		if part and part:IsA("BasePart") then
			cf[name] = part.CFrame
			track.sizes[name] = part.Size
		end
	end
	local root = character:FindFirstChild("HumanoidRootPart")
	if root and root:IsA("BasePart") then
		cf.Root = root.CFrame
	end
	table.insert(track.snaps, { t = now, cf = cf })
	while #track.snaps > 1 and now - track.snaps[1].t > C.History do
		table.remove(track.snaps, 1)
	end
end

-- Part CFrames of a track at time t (blended between the two nearest snapshots).
local function poseAt(track: Track, t: number): { [string]: CFrame }?
	local snaps = track.snaps
	if #snaps == 0 then
		return nil
	end
	if t <= snaps[1].t then
		return snaps[1].cf
	end
	for i = #snaps, 1, -1 do
		local a = snaps[i]
		if a.t <= t then
			local b = snaps[i + 1]
			if not b then
				return a.cf
			end
			local u = (t - a.t) / math.max(1e-4, b.t - a.t)
			local out = {}
			for name, ca in a.cf do
				local cb = b.cf[name]
				out[name] = if cb then ca:Lerp(cb, u) else ca
			end
			return out
		end
	end
	return snaps[#snaps].cf
end

-- Ray (in world space) vs an oriented box; returns the entry distance or nil.
local function rayBox(origin: Vector3, dir: Vector3, cf: CFrame, size: Vector3): number?
	local o = cf:PointToObjectSpace(origin)
	local d = cf:VectorToObjectSpace(dir)
	local half = size / 2
	local tmin, tmax = -math.huge, math.huge
	for _, axis in { "X", "Y", "Z" } do
		local oa, da, h = (o :: any)[axis], (d :: any)[axis], (half :: any)[axis]
		if math.abs(da) < 1e-8 then
			if oa < -h or oa > h then
				return nil
			end
		else
			local t1, t2 = (-h - oa) / da, (h - oa) / da
			if t1 > t2 then
				t1, t2 = t2, t1
			end
			tmin, tmax = math.max(tmin, t1), math.min(tmax, t2)
			if tmin > tmax then
				return nil
			end
		end
	end
	if tmax < 0 then
		return nil
	end
	return math.max(0, tmin)
end

-- How far back to look for this shooter: their round trip plus the time Roblox spends
-- smoothing other players' movement on their screen, capped.
function LagComp.rewindFor(shooter: Player): number
	local ok, ping = pcall(shooter.GetNetworkPing, shooter)
	if not ok or typeof(ping) ~= "number" or ping ~= ping then
		ping = 0
	end
	return math.clamp(ping + C.Interpolation, 0, C.MaxRewind)
end

-- Debug: show the rewound hitboxes in Studio for a moment.
local debugFolder: Folder? = nil
local function showDebug(pose: { [string]: CFrame }, sizes: { [string]: Vector3 }, hitName: string?)
	if not (C.Debug and RunService:IsStudio()) then
		return
	end
	if not debugFolder then
		debugFolder = Instance.new("Folder")
		debugFolder.Name = "LagCompDebug"
		debugFolder.Parent = workspace
	end
	for name, cf in pose do
		local size = sizes[name]
		if size then
			local p = Instance.new("Part")
			p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
			p.Transparency = 0.6
			p.Color = if name == hitName then Color3.new(1, 0.2, 0.2) else Color3.new(0.3, 0.6, 1)
			p.Size, p.CFrame = size, cf
			p.Parent = debugFolder
			game:GetService("Debris"):AddItem(p, 1.5)
		end
	end
end

-- Closest player body part the ray hits (as seen by the shooter), within maxDist.
function LagComp.cast(shooter: Player, origin: Vector3, dir: Vector3, maxDist: number): (Player?, string?, number?)
	local t = os.clock() - LagComp.rewindFor(shooter)
	local bestPlayer, bestPart, bestDist = nil, nil, maxDist
	for player, track in tracks do
		if player == shooter or not track.character.Parent then
			continue
		end
		local pose = poseAt(track, t)
		local root = pose and (pose.Root or pose.UpperTorso)
		if not pose or not root then
			continue
		end
		-- broadphase: is this player near the bullet line at all?
		local rel = root.Position - origin
		local along = rel:Dot(dir)
		if along < -NEAR or along > bestDist + NEAR or (rel - dir * along).Magnitude > NEAR then
			continue
		end
		local hitHere = nil
		for name, cf in pose do
			local size = track.sizes[name]
			if size then
				local d = rayBox(origin, dir, cf, size)
				if d and d < bestDist then
					bestPlayer, bestPart, bestDist, hitHere = player, name, d, name
				end
			end
		end
		showDebug(pose, track.sizes, hitHere)
	end
	if bestPlayer then
		return bestPlayer, bestPart, bestDist
	end
	return nil, nil, nil
end

function LagComp.characters(): { Model }
	local list = {}
	for _, p in Players:GetPlayers() do
		if p.Character then
			table.insert(list, p.Character)
		end
	end
	return list
end

local acc = 0
RunService.Heartbeat:Connect(function(dt)
	acc += dt
	if acc < 1 / C.Rate then
		return
	end
	acc = 0
	local now = os.clock()
	for _, p in Players:GetPlayers() do
		record(p, now)
	end
end)

Players.PlayerRemoving:Connect(function(p)
	tracks[p] = nil
end)

return LagComp
