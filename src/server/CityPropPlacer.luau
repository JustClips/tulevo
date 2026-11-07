-- Puts the City Prop street lamps and traffic signals (Shared/CityPropIds) into the world on the
-- old lamp and signal spots (Server/CityPropLayout, from tools/city_props.py), in
-- workspace.City.StreetLamps and workspace.City.TrafficSignals. Each model is turned so its arm
-- reaches over the road and its pole stands on the plinth left in the street mesh. A lamp's
-- glowing part gets the attribute PropLight (CityBuildings adds the light). A signal's lenses are
-- renamed Signal<EW|NS><Red|Amber|Green> so Client/TrafficSignals cycles them.
-- Signals are only placed once StreetCorners has been re-baked without the old mast-arm signals
-- (build_street.py signal()); while the old lenses are still in it they are skipped.
--
-- Edit mode (so the lamps are in the place itself, not only in Play): paste in the Studio
-- command bar, then save / publish the place:
--   require(game.ServerScriptService.Server.CityPropPlacer).place(true)
-- This also deletes the old baked lamp parts from the street meshes. Run it again after changing
-- STREET_LAMP, LAMP_TURN, SIGNAL_MODEL etc: it rebuilds the folders. LiveSync leaves the folder alone (it only
-- removes what it made itself). If the folder is missing at run time, CityBuildings places the
-- lamps then.
local InsertService = game:GetService("InsertService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local CityPropIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("CityPropIds")) :: any
local PropLayout = require(script.Parent:WaitForChild("CityPropLayout")) :: any

local M = {}

-- Which lamp model stands on each street. Change freely: any lamp key of Shared/CityPropIds.
M.STREET_LAMP = {
	StreetVaultAvenue = "StreetLightLongArm1",
	StreetBackStreet = "StreetLightLongArm2",
	StreetNorthStreet = "StreetLight1",
	StreetSouthStreet = "StreetLight2",
	StreetWestStreet = "StreetLight3",
	StreetEastStreet = "StreetLight1",
}
-- Extra turn in degrees for a lamp model that ends up facing the wrong way,
-- e.g. { StreetLight2 = 180 }.
M.LAMP_TURN = {} :: { [string]: number }
-- Extra size for a lamp model that comes out too big or small, e.g. { StreetLight3 = 1.3 }.
M.LAMP_SCALE = {} :: { [string]: number }

-- Which signal model stands on every signal corner (any signal key of Shared/CityPropIds), plus
-- an extra turn (degrees) and size like the lamps have.
M.SIGNAL_MODEL = "IntersectionTrafficLight2Long"
M.SIGNAL_TURN = 0
M.SIGNAL_SCALE = 1

local PLINTH_TOP = 0.22 -- plinth top above the sidewalk point
local LIGHT_NAMES = { "bulb", "lens", "light", "glow", "emit", "glass" }
-- parts of the old baked street lamps in the Street* meshes
local OLD_LAMP_PARTS = { PoleLamp = true, MetalLampHead = true, MetalLampCap = true }

-- world AABB of a part
local function extents(p: BasePart): (Vector3, Vector3)
	local cf, s = p.CFrame, p.Size / 2
	local e = Vector3.new(
		math.abs(cf.RightVector.X) * s.X + math.abs(cf.UpVector.X) * s.Y + math.abs(cf.LookVector.X) * s.Z,
		math.abs(cf.RightVector.Y) * s.X + math.abs(cf.UpVector.Y) * s.Y + math.abs(cf.LookVector.Y) * s.Z,
		math.abs(cf.RightVector.Z) * s.X + math.abs(cf.UpVector.Z) * s.Y + math.abs(cf.LookVector.Z) * s.Z
	)
	return cf.Position - e, cf.Position + e
end

-- how much a part looks like the lamp's glowing bit: Neon first, then by name; 0 = not at all
local function lightScore(p: BasePart): number
	if p.Material == Enum.Material.Neon then
		return 100
	end
	local n = p.Name:lower()
	for i, k in LIGHT_NAMES do
		if n:find(k, 1, true) then
			return 50 - i
		end
	end
	return 0
end

-- Loads one lamp model at the origin and works out where its pole stands and which way its arm
-- reaches. Returns the model, the pole foot (model space) and the arm direction.
local function prototype(key: string): (Model?, Vector3?, Vector3?)
	local id = CityPropIds[key]
	if not id then
		warn(`[CityProps] no id for {key} in Shared/CityPropIds`)
		return nil
	end
	local ok, res = pcall(InsertService.LoadAsset, InsertService, id)
	if not ok then
		warn(`[CityProps] {key} ({id}) failed to load: {res}`)
		return nil
	end
	local inner = res:FindFirstChildWhichIsA("Model")
	local m: Model = if inner and #res:GetChildren() == 1 then inner else res
	m.Name = key
	m.Parent = nil
	if m ~= res then
		res:Destroy()
	end
	for _, d in m:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
			d.CanTouch = false
		end
	end
	local scale = M.LAMP_SCALE[key]
	if scale and scale > 0 then
		m:ScaleTo(m:GetScale() * scale)
	end
	m:PivotTo(CFrame.new())
	local box, size = m:GetBoundingBox()
	-- pole: the tallest, slimmest part
	local pole, best = nil, 0
	local glow, glowScore, top, topY = nil, 0, nil, -math.huge
	for _, d in m:GetDescendants() do
		if d:IsA("BasePart") then
			local lo, hi = extents(d)
			local h, w = hi.Y - lo.Y, math.max(hi.X - lo.X, hi.Z - lo.Z, 0.05)
			if h > size.Y * 0.4 and h / w > best then
				pole, best = (lo + hi) / 2, h / w
			end
			local sc = lightScore(d)
			if sc > glowScore then
				glow, glowScore = d, sc
			end
			if hi.Y > topY then
				top, topY = d, hi.Y
			end
		end
	end
	-- one light per lamp: its glowing part, or the part highest up if nothing looks like one
	local lit = glow or top
	if lit then
		lit:SetAttribute("PropLight", true)
	end
	local foot = Vector3.new((pole or box.Position).X, box.Y - size.Y / 2, (pole or box.Position).Z)
	local reach = Vector3.new(box.X - foot.X, 0, box.Z - foot.Z)
	local dir = if reach.Magnitude > 0.5 then reach.Unit else Vector3.new(0, 0, -1)
	return m, foot, dir
end

-- Deletes the old baked lamp parts from the Street* meshes under City.Buildings.
function M.removeOldLamps(city: Instance): number
	local n = 0
	local buildings = city:FindFirstChild("Buildings")
	for _, model in (if buildings then buildings:GetChildren() else {}) do
		if model:IsA("Model") and model.Name:match("^Street") then
			for _, d in model:GetDescendants() do
				if d:IsA("BasePart") and (OLD_LAMP_PARTS[d.Name] or d.Name:match("^StreetLamp%d")) then
					d:Destroy()
					n += 1
				end
			end
		end
	end
	return n
end

-- Places every lamp in a fresh City.StreetLamps folder and returns it.
function M.placeLamps(): Folder?
	local city = workspace:FindFirstChild("City")
	if not city then
		warn("[CityProps] workspace.City not found")
		return nil
	end
	local old = city:FindFirstChild("StreetLamps")
	if old then
		old:Destroy()
	end
	local folder = Instance.new("Folder")
	folder.Name = "StreetLamps"
	local protos = {}
	local placed = 0
	for street, spots in PropLayout do
		local key = M.STREET_LAMP[street]
		if street == "Signals" or not key then
			continue
		end
		if protos[key] == nil then
			local m, foot, dir = prototype(key)
			protos[key] = if m then { model = m, foot = foot, dir = dir } else false
		end
		local proto = protos[key]
		if not proto then
			continue
		end
		local base = CFrame.lookAt(Vector3.zero, proto.dir)
		local turn = CFrame.Angles(0, math.rad(M.LAMP_TURN[key] or 0), 0)
		for i, s in spots do
			local road = Vector3.new(s[4], 0, s[5])
			local rot = CFrame.lookAt(Vector3.zero, road) * base:Inverse()
			local lamp = proto.model:Clone()
			lamp.Name = `{street}Lamp{i}`
			lamp:PivotTo(CFrame.new(s[1], s[2] + PLINTH_TOP, s[3]) * turn * rot * CFrame.new(-proto.foot))
			lamp.ModelStreamingMode = Enum.ModelStreamingMode.Persistent
			lamp.Parent = folder
			placed += 1
		end
	end
	for _, p in protos do
		if p then
			p.model:Destroy()
		end
	end
	folder.Parent = city
	print(`[CityProps] {placed} street lamps placed`)
	return folder
end

-- which signal colour a part is: by name, else by colour for parts that look like a lens
local COLOUR_NAMES = {
	{ "Red", { "red", "stop" } },
	{ "Amber", { "amber", "yellow", "orange", "caution" } },
	{ "Green", { "green", "go" } },
}
local LENS_NAMES = { "lens", "light", "bulb", "lamp", "glow", "led", "signal" }
local function lensColour(p: BasePart): string?
	local n = p.Name:lower()
	local looksLens = p.Material == Enum.Material.Neon
	for _, k in LENS_NAMES do
		if n:find(k, 1, true) then
			looksLens = true
		end
	end
	if looksLens then
		for _, c in COLOUR_NAMES do
			for _, k in c[2] do
				if n:find(k, 1, true) then
					return c[1]
				end
			end
		end
		local h, s, v = p.Color:ToHSV()
		if s > 0.45 and v > 0.25 and math.max(p.Size.X, p.Size.Y, p.Size.Z) < 4 then
			if h < 0.04 or h > 0.93 then
				return "Red"
			elseif h < 0.17 then
				return "Amber"
			elseif h > 0.22 and h < 0.5 then
				return "Green"
			end
		end
	end
	return nil
end

-- True while StreetCorners still has the old baked signal lenses (not re-baked yet).
local function oldSignalsBaked(city: Instance): boolean
	local buildings = city:FindFirstChild("Buildings")
	local corners = buildings and buildings:FindFirstChild("StreetCorners")
	if not corners then
		return false
	end
	for _, d in corners:GetDescendants() do
		if d:IsA("BasePart") and d.Name:match("^Signal%u%u%a+$") then
			return true
		end
	end
	return false
end

-- Places a signal on every signal corner in a fresh City.TrafficSignals folder and returns it.
-- Skipped (nil) while the old baked signals are still in StreetCorners.
function M.placeSignals(): Folder?
	local city = workspace:FindFirstChild("City")
	if not city then
		return nil
	end
	if oldSignalsBaked(city) then
		print("[CityProps] StreetCorners still has the old signals: re-bake it first, signals skipped")
		return nil
	end
	local spots = PropLayout.Signals
	if not spots then
		return nil
	end
	local old = city:FindFirstChild("TrafficSignals")
	if old then
		old:Destroy()
	end
	local key = M.SIGNAL_MODEL
	if M.SIGNAL_SCALE ~= 1 then
		M.LAMP_SCALE[key] = M.SIGNAL_SCALE
	end
	local proto, foot, dir = prototype(key)
	if not proto then
		return nil
	end
	local lenses = 0
	for _, d in proto:GetDescendants() do
		if d:IsA("BasePart") then
			d:SetAttribute("PropLight", nil)
			local c = lensColour(d)
			if c then
				d:SetAttribute("LensColour", c)
				lenses += 1
			end
		end
	end
	if lenses == 0 then
		warn(`[CityProps] {key}: found no red/amber/green lens parts, the signals won't change colour`)
	end
	local folder = Instance.new("Folder")
	folder.Name = "TrafficSignals"
	local base = CFrame.lookAt(Vector3.zero, dir)
	local turn = CFrame.Angles(0, math.rad(M.SIGNAL_TURN or 0), 0)
	for i, s in spots do
		-- the arm reaches over the lanes to the left of the traffic the heads face: (dz, -dx)
		local arm = Vector3.new(s[5], 0, -s[4])
		local rot = CFrame.lookAt(Vector3.zero, arm) * base:Inverse()
		local sig = proto:Clone()
		sig.Name = `Signal{s[7]}{i}`
		sig:PivotTo(CFrame.new(s[1], s[2] + PLINTH_TOP, s[3]) * turn * rot * CFrame.new(-foot))
		sig.ModelStreamingMode = Enum.ModelStreamingMode.Persistent
		for _, d in sig:GetDescendants() do
			local c = d:IsA("BasePart") and d:GetAttribute("LensColour")
			if c then
				d.Name = `Signal{s[7]}{c}`
			end
		end
		sig.Parent = folder
	end
	proto:Destroy()
	folder.Parent = city
	print(`[CityProps] {#spots} traffic signals placed ({lenses} lens parts each)`)
	return folder
end

-- Command bar entry: lamps + signals, and with editMode the old baked lamps are removed.
function M.place(editMode: boolean?)
	local city = workspace:FindFirstChild("City")
	if editMode and city then
		print(`[CityProps] removed {M.removeOldLamps(city)} old lamp parts`)
	end
	M.placeLamps()
	M.placeSignals()
end

return M
