-- Wet footprints: once it has rained for a bit the ground counts as wet, and every player's
-- steps leave dark shoe prints (FootprintL / FootprintR textures) that fade away. The ground
-- dries a couple of minutes after the rain stops. Nothing is printed where there's a roof
-- overhead (that ground stayed dry). Steps in the rain also splash.
--
-- Steps are counted from how far each character moves on the ground (stride grows with
-- speed) and land under the real foot part, alternating left / right.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local Rain = require(script.Parent:WaitForChild("Rain"))

local Footprints = {}

local POOL = 140
local FADE = 22 -- seconds a print takes to fade
local RANGE = 160 -- only characters this close to the camera print
local WET_UP = 45 -- seconds of full rain to soak the ground
local DRY = 150 -- seconds for soaked ground to dry
-- which way the print's toe points: 0 if prints look right, math.pi if they point backwards
local TOE_FLIP = 0

local tex = TextureIds.Weather or {}
local folder: Folder
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.RespectCanCollide = true

type Print = { part: Part, decal: Decal, t0: number, start: number }
local prints: { Print } = {}
local nextPrint = 1
local wet = 0
local filterClock = 0

type Walker = { last: Vector3, travelled: number, left: boolean }
local walkers: { [Model]: Walker } = {}

function Footprints.start()
	folder = Instance.new("Folder")
	folder.Name = "WeatherFootprints"
	folder.Parent = workspace
	for _ = 1, POOL do
		local p = Instance.new("Part")
		p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
		p.Transparency = 1
		p.Size = Vector3.new(0.8, 0.02, 1.4)
		p.Parent = folder
		local d = Instance.new("Decal")
		d.Face = Enum.NormalId.Top
		d.Color3 = Color3.fromRGB(28, 30, 36)
		d.Transparency = 1
		d.Parent = p
		table.insert(prints, { part = p, decal = d, t0 = -math.huge, start = 1 })
	end
end

-- 0 dry .. 1 soaked
function Footprints.wetness(): number
	return wet
end

local function refreshFilter()
	local list: { Instance } = { folder }
	for _, name in { "WeatherSky", "WeatherRain" } do
		local f = workspace:FindFirstChild(name)
		if f then
			table.insert(list, f)
		end
	end
	for _, plr in Players:GetPlayers() do
		if plr.Character then
			table.insert(list, plr.Character)
		end
	end
	params.FilterDescendantsInstances = list
end

local function place(char: Model, root: BasePart, left: boolean, raining: boolean)
	local foot = char:FindFirstChild(if left then "LeftFoot" else "RightFoot") :: BasePart?
	local side = if left then -0.5 else 0.5
	local from = if foot then foot.Position else (root.CFrame * CFrame.new(side, 0, 0)).Position
	local hit = workspace:Raycast(from + Vector3.new(0, 1, 0), Vector3.new(0, -6, 0), params)
	if not hit or hit.Normal.Y < 0.7 then
		return
	end
	if workspace:Raycast(hit.Position + Vector3.new(0, 0.5, 0), Vector3.new(0, 300, 0), params) then
		return -- under a roof: dry ground
	end
	local look = root.CFrame.LookVector
	local flat = Vector3.new(look.X, 0, look.Z)
	if flat.Magnitude < 0.1 then
		return
	end
	local n = hit.Normal
	local fwd = (flat.Unit - n * flat.Unit:Dot(n)).Unit
	local right = fwd:Cross(n)
	local cf = CFrame.fromMatrix(hit.Position + n * 0.012, right, n) * CFrame.Angles(0, TOE_FLIP, 0)
	local pr = prints[nextPrint]
	nextPrint = nextPrint % POOL + 1
	local size = if foot
		then Vector3.new(foot.Size.X * 0.95, 0.02, math.max(foot.Size.Z * 1.15, 1))
		else Vector3.new(0.8, 0.02, 1.4)
	pr.part.Size = size
	pr.part.CFrame = cf
	pr.decal.Texture = `rbxassetid://{if left then tex.FootprintL else tex.FootprintR}`
	pr.t0 = os.clock()
	pr.start = 1 - 0.6 * wet
	pr.decal.Transparency = pr.start
	if math.random() < 0.6 then
		Rain.footSplash(hit.Position, n, raining)
	end
end

function Footprints.update(w, dt: number)
	if not folder then
		return
	end
	if w.rain > 0.05 then
		wet = math.min(1, wet + dt * w.rain / WET_UP)
	else
		wet = math.max(0, wet - dt / DRY)
	end

	local now = os.clock()
	for _, pr in prints do
		if pr.decal.Transparency < 1 then
			local a = math.clamp((now - pr.t0) / FADE, 0, 1)
			local tr = pr.start + (1 - pr.start) * a * a
			pr.decal.Transparency = if a >= 1 then 1 else tr
		end
	end

	local cam = workspace.CurrentCamera
	if wet < 0.15 or not cam then
		table.clear(walkers)
		return
	end
	filterClock -= dt
	if filterClock <= 0 then
		filterClock = 1
		refreshFilter()
	end
	local camPos = cam.CFrame.Position
	local seen = {}
	for _, plr in Players:GetPlayers() do
		local char = plr.Character
		local root = char and char:FindFirstChild("HumanoidRootPart") :: BasePart?
		local hum = char and char:FindFirstChildOfClass("Humanoid")
		if char and root and hum and hum.Health > 0 and (root.Position - camPos).Magnitude < RANGE then
			seen[char] = true
			local wk = walkers[char]
			if not wk then
				wk = { last = root.Position, travelled = 0, left = true }
				walkers[char] = wk
			end
			local pos = root.Position
			local step = Vector3.new(pos.X - wk.last.X, 0, pos.Z - wk.last.Z).Magnitude
			wk.last = pos
			-- on the ground? (works for other players too, unlike FloorMaterial)
			local grounded = math.abs(root.AssemblyLinearVelocity.Y) < 6
				and workspace:Raycast(pos, Vector3.new(0, -(hum.HipHeight + root.Size.Y / 2 + 1.2), 0), params)
					~= nil
			if step > 8 or not grounded then
				wk.travelled = 0 -- teleport / jump: start fresh
			else
				wk.travelled += step
				local speed = Vector3.new(root.AssemblyLinearVelocity.X, 0, root.AssemblyLinearVelocity.Z).Magnitude
				local stride = math.clamp(speed * 0.3, 2, 4.5)
				if wk.travelled >= stride then
					wk.travelled = 0
					place(char, root, wk.left, w.rain > 0.05)
					wk.left = not wk.left
				end
			end
		end
	end
	for char in walkers do
		if not seen[char] then
			walkers[char] = nil
		end
	end
end

return Footprints
