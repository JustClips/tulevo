-- Traffic signals at the downtown intersections: City Prop signal models in City.TrafficSignals
-- (lens discs added by Server/CityBuildings), or old baked ones in City.Buildings.StreetCorners. Each lens is a part named
-- Signal<Phase><Colour>: Phase EW = traffic on the east-west streets, NS = north-south.
-- Every client runs the same cycle from the server clock, so all players see the same lights.
local RunService = game:GetService("RunService")

local GREEN, AMBER, ALL_RED = 20, 3, 2
local CYCLE = 2 * (GREEN + AMBER + ALL_RED)
local ON = {
	Red = Color3.fromRGB(255, 40, 30),
	Amber = Color3.fromRGB(255, 170, 20),
	Green = Color3.fromRGB(40, 255, 140),
}
local OFF = {
	Red = Color3.fromRGB(60, 14, 12),
	Amber = Color3.fromRGB(60, 42, 10),
	Green = Color3.fromRGB(10, 50, 32),
}

local lenses = {} -- { part, phase, colour }

local function scan(model: Instance)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			local phase, colour = d.Name:match("^Signal(%u%u)(%a+)$")
			if phase and ON[colour] then
				table.insert(lenses, { part = d, phase = phase, colour = colour })
			end
		end
	end
end

-- which colour each phase shows at time t in the cycle
local function state(t: number): (string, string)
	local half = GREEN + AMBER + ALL_RED
	local first = t < half
	local u = if first then t else t - half
	local active = if u < GREEN then "Green" elseif u < GREEN + AMBER then "Amber" else "Red"
	if first then
		return active, "Red"
	end
	return "Red", active
end

local city = workspace:WaitForChild("City", 30)
if not city then
	return
end
-- Lenses live in the baked StreetCorners mesh (old signals) and/or the City Prop signal models
-- in City.TrafficSignals (Server/CityBuildings). Both may still be loading: rescan when lens
-- parts arrive.
local roots: { Instance } = {}
local function rescan()
	table.clear(lenses)
	for _, r in roots do
		if r.Parent then
			scan(r)
		end
	end
end
local function watch(root: Instance)
	table.insert(roots, root)
	root.DescendantAdded:Connect(function(d)
		if d:IsA("BasePart") and d.Name:match("^Signal") then
			rescan()
		end
	end)
	rescan()
end
local buildings = city:FindFirstChild("Buildings")
local corners = buildings and buildings:FindFirstChild("StreetCorners")
if corners then
	watch(corners)
end
local signals = city:FindFirstChild("TrafficSignals")
if signals then
	watch(signals)
end
city.ChildAdded:Connect(function(c)
	if c.Name == "TrafficSignals" or c.Name == "Buildings" then
		task.defer(function()
			local b = city:FindFirstChild("Buildings")
			local sc = b and b:FindFirstChild("StreetCorners")
			if sc and not table.find(roots, sc) then
				watch(sc)
			end
			local ts = city:FindFirstChild("TrafficSignals")
			if ts and not table.find(roots, ts) then
				watch(ts)
			end
		end)
	end
end)

local lastEW, lastNS
RunService.Heartbeat:Connect(function()
	local t = workspace:GetServerTimeNow() % CYCLE
	local ew, ns = state(t)
	if ew == lastEW and ns == lastNS then
		return
	end
	lastEW, lastNS = ew, ns
	for _, l in lenses do
		local on = (if l.phase == "EW" then ew else ns) == l.colour
		l.part.Material = if on then Enum.Material.Neon else Enum.Material.SmoothPlastic
		l.part.Color = if on then ON[l.colour] else OFF[l.colour]
	end
end)
