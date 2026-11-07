-- Traffic signals at the downtown intersections (art/blender/cityfill/build_street.py,
-- model City.Buildings.StreetCorners). Each lens set is one MeshPart named
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
local buildings = city and city:WaitForChild("Buildings", 30)
local corners = buildings and buildings:WaitForChild("StreetCorners", 30)
if not corners then
	return
end
-- the mesh may still be loading (CityBuildings / LiveSync): rescan when parts arrive
scan(corners)
corners.DescendantAdded:Connect(function(d)
	if d:IsA("BasePart") and d.Name:match("^Signal") then
		table.clear(lenses)
		scan(corners)
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
