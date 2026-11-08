-- Finishes the city's Blender buildings: Models under workspace.City.Buildings with
-- attribute LiveSyncAsset (made by tools/build_city_map.py).
-- In Studio the LiveSync plugin (v5+) already loads each mesh in edit mode; if a model
-- is still empty here (older plugin, or a fresh server) it is loaded now the same way.
-- Then parts are anchored, kept streamed in so the skyline shows from anywhere, and
-- named parts get their Roblox look:
--   Light*     glowing strips -> Neon, no texture
--   Lamp*      canopy lamps -> Neon + a SurfaceLight shining down
--   ShopLamp   strip over a shop front -> Neon + a SurfaceLight shining down
--   PriceFace  printed price sign -> a small glow so it reads at night
--   Neon<Colour> (NeonPink, NeonCyan, NeonRed) coloured neon tubes / beacons + a coloured glow
--   Sconce     small porch lights -> warm Neon
--   StreetLamp<n>  street light lenses (art/blender/cityfill) -> Neon + a wide SurfaceLight
--              without shadows (there are ~150 of them). No light-shaft beams: from a distance
--              they read as pale slabs floating over the city at night
--   Signal<EW|NS><Red|Amber|Green>  traffic signal lenses, cycled by Client/TrafficSignals
-- Lamps get brighter as the in-game clock goes into night.
local InsertService = game:GetService("InsertService")
local Lighting = game:GetService("Lighting")
local PhysicsService = game:GetService("PhysicsService")
local RunService = game:GetService("RunService")

-- Exact collision (tools/city_colliders.py): invisible boxes per building, built below. The
-- visible meshes go in collision group CityVisual, which collides with nothing, so the merged
-- meshes' rough hulls stop making invisible walls. They keep CanCollide + CanQuery so the default
-- camera still treats them as walls; raycasts with the default RaycastParams (group Default) skip
-- them and hit the boxes instead (bullets, rain, car wheels, footprints).
local Colliders = require(script.Parent:WaitForChild("CityColliders")) :: any
local VISUAL_GROUP = "CityVisual"
pcall(function()
	PhysicsService:RegisterCollisionGroup(VISUAL_GROUP)
end)
PhysicsService:CollisionGroupSetCollidable(VISUAL_GROUP, "Default", false)
PhysicsService:CollisionGroupSetCollidable(VISUAL_GROUP, VISUAL_GROUP, false)
local BOX_MATERIALS = {
	Enum.Material.Concrete,
	Enum.Material.Grass,
	Enum.Material.Asphalt,
	Enum.Material.Wood,
	Enum.Material.Metal,
	Enum.Material.Glass,
	Enum.Material.Slate,
	Enum.Material.Plastic,
	Enum.Material.Ground,
	Enum.Material.Brick,
	Enum.Material.Granite,
}
-- Moving door / gate parts (Client/CityDoors) keep their own mesh collision.
local function isDoorPart(name: string): boolean
	return name:match("^Swing%d") ~= nil or name:match("^Slide%d") ~= nil or name:match("^Lift%d") ~= nil
end

local LAMP_COLOR = Color3.fromRGB(255, 244, 222)
-- parts of the old baked street lamps, removed at load (see style)
local OLD_LAMP_PARTS = { PoleLamp = true, MetalLampHead = true, MetalLampCap = true }
local NEON = {
	NeonPink = Color3.fromRGB(255, 70, 170),
	NeonCyan = Color3.fromRGB(60, 235, 255),
	NeonRed = Color3.fromRGB(255, 40, 30),
	-- ATM card reader / cash slot guide lights (art/blender/atm)
	AtmCardLight = Color3.fromRGB(70, 240, 120),
	AtmCashLight = Color3.fromRGB(70, 240, 120),
}
-- Textures with see-through pixels (chain-link fence, graffiti decals).
local ALPHA = {
	ChainLink = true,
	Tag = true,
	FxFall = true,
	FxRipple = true,
	-- Fort Halden army base
	RazorWire = true,
	CamoNet = true,
	Slide1Mesh = true,
	Slide2Mesh = true,
	-- Bellmont Hills mansions
	Ivy = true,
	-- street tree canopies (art/blender/cityfill)
	LeafCard = true,
	LeafCardB = true,
	LeafCardC = true,
	LeafCardD = true,
	-- faded painted wall advert on the brick block (paint only, brick shows through)
	GhostSign = true,
	LeafCardE = true,
	LeafCardF = true,
}
-- Small decor parts that should not collide.
local DECO = {
	Frame = true,
	Sill = true,
	WinIron = true,
	Pipe = true,
	Meter = true,
	CandyRack = true,
	FridgeDoors = true,
	Tag = true,
}
local lamps = {} -- { light = SurfaceLight, day = number, night = number }
local lampGlass: { BasePart } = {} -- City Prop lamp glass: lit (Neon) at night
local GLASS_COLOR = Color3.fromRGB(235, 232, 220) -- City Prop lamp glass by day

local function hasParts(model: Model): boolean
	return model:FindFirstChildWhichIsA("BasePart", true) ~= nil
end

-- Centre of the box round every part's own box, the same box tools/build_city_map.py takes from
-- the GLB. (Model:GetBoundingBox comes out smaller than the meshes for thin parts such as palm
-- fronds, so lots with palms sat about a stud off and their back walls didn't line up.)
local function partsCenter(model: Model): Vector3
	local lo, hi = Vector3.one * math.huge, -Vector3.one * math.huge
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			local cf, s = d.CFrame, d.Size / 2
			local x, y, z = cf.XVector, cf.YVector, cf.ZVector
			local e = Vector3.new(
				math.abs(x.X) * s.X + math.abs(y.X) * s.Y + math.abs(z.X) * s.Z,
				math.abs(x.Y) * s.X + math.abs(y.Y) * s.Y + math.abs(z.Y) * s.Z,
				math.abs(x.Z) * s.X + math.abs(y.Z) * s.Y + math.abs(z.Z) * s.Z
			)
			lo = lo:Min(cf.Position - e)
			hi = hi:Max(cf.Position + e)
		end
	end
	return if lo.X < math.huge then (lo + hi) / 2 else model:GetPivot().Position
end

-- Asset id -> a clean loaded copy to clone. Many models share an asset (4 BrickBlock_S, 3 Store_S,
-- ~130 lamp / signal props on a handful of assets), so each id is fetched from Roblox only once,
-- even when several loader threads ask for it at the same time. Cleared once the city is done.
local assetCache: { [number]: Instance } = {}
local assetWaiting: { [number]: { thread } } = {}

local function fetch(id: number): (boolean, any)
	local cached = assetCache[id]
	if cached then
		return true, cached:Clone()
	end
	local waiting = assetWaiting[id]
	if waiting then
		-- another thread is loading this id: wait for it
		table.insert(waiting, coroutine.running())
		coroutine.yield()
		cached = assetCache[id]
		if cached then
			return true, cached:Clone()
		end
		return false, "load failed in another thread"
	end
	assetWaiting[id] = {}
	local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
	if ok then
		assetCache[id] = container:Clone()
	end
	local list = assetWaiting[id]
	assetWaiting[id] = nil
	for _, t in list do
		task.spawn(t)
	end
	return ok, container
end

local function load(model: Model)
	local id = tonumber(model:GetAttribute("LiveSyncAsset"))
	if not id then
		return
	end
	-- placed props (City Prop lamps / signals, tools/city_props.py), the same as the LiveSync
	-- plugin v10: scale the asset about its origin, then move it by LiveSyncCFrame.
	local scale = model:GetAttribute("LiveSyncScale")
	local placed = model:GetAttribute("LiveSyncCFrame")
	local isProp = typeof(placed) == "CFrame"
	local ok, container = fetch(id)
	if not ok then
		warn(`[City] could not load {model.Name} ({id}): {container}`)
		return
	end
	if isProp or type(scale) == "number" then
		for _, d in container:GetDescendants() do
			if d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript") then
				d:Destroy()
			elseif d:IsA("BasePart") then
				d.Anchored = true
			end
		end
		container.WorldPivot = CFrame.identity
		if type(scale) == "number" and scale > 0 and scale ~= 1 then
			container:ScaleTo(scale)
		end
		if typeof(placed) == "CFrame" then
			container:PivotTo(placed)
		end
		for _, child in container:GetChildren() do
			child.Parent = model
		end
		container:Destroy()
		return
	end
	-- Drop the GLB's embedded SurfaceAppearances before they reach the place: every part gets
	-- its colour map from LiveSyncTextures, and in Studio these make PublishService try (and
	-- fail, rate-limited) to upload texture packs.
	for _, d in container:GetDescendants() do
		if d:IsA("SurfaceAppearance") then
			d:Destroy()
		end
	end
	for _, child in container:GetChildren() do
		child.Parent = model
	end
	container:Destroy()
	local center = model:GetAttribute("LiveSyncBoxCenter")
	if typeof(center) == "Vector3" then
		model:PivotTo(model:GetPivot() + (center - partsCenter(model)))
	end
end

local function neon(part: BasePart)
	for _, c in part:GetChildren() do
		if c:IsA("SurfaceAppearance") then
			c:Destroy()
		end
	end
	if part:IsA("MeshPart") then
		part.TextureID = ""
	end
	part.Material = Enum.Material.Neon
	part.Color = LAMP_COLOR
	part.CastShadow = false
	part.CanCollide = false
end

local function downLight(part: BasePart, range: number, day: number, night: number): SurfaceLight
	local light = Instance.new("SurfaceLight")
	light.Face = Enum.NormalId.Bottom
	light.Angle = 120
	light.Range = range
	light.Color = LAMP_COLOR
	light.Shadows = true
	light.Brightness = day
	light.Parent = part
	table.insert(lamps, { light = light, day = day, night = night })
	return light
end

-- Colour textures uploaded as separate Images (tools/upload_textures.py): the model's
-- LiveSyncTextures attribute is JSON { part name: image id }. The GLB's own embedded
-- SurfaceAppearance images don't always show in game, so these replace them.
local HttpService = game:GetService("HttpService")

local function applyTextures(model: Model)
	local raw = model:GetAttribute("LiveSyncTextures")
	if type(raw) ~= "string" then
		return
	end
	local ok, map = pcall(HttpService.JSONDecode, HttpService, raw)
	if not ok then
		return
	end
	for _, d in model:GetDescendants() do
		local id = d:IsA("MeshPart") and map[d.Name]
		if id then
			for _, c in d:GetChildren() do
				if c:IsA("SurfaceAppearance") then
					c:Destroy()
				end
			end
			d.TextureID = `rbxassetid://{id}`
			d.Color = Color3.new(1, 1, 1)
		end
	end
end

-- Walk-in buildings (corner store): every part that shares a mesh with pieces both outside
-- and inside (door mats, frames, lights, trim) would make an invisible wall across the door,
-- so only the real solid pieces collide.
local WALK_IN_SOLID = {
	"^Wall",
	"^Parapet",
	"^Cooler",
	"^Gondola",
	"^Counter",
	"^Freezer",
	"^Atm",
	"^ShopFloor",
	"^Asphalt",
	"^Concrete",
	"^Flat",
}
-- Plants never block walking.
local PLANTS = {
	Leaf = true,
	LeafB = true,
	LeafC = true,
	LeafD = true,
	LeafE = true,
	LeafF = true,
	CamoNet = true,
	Palm = true,
	Shrub = true,
	Hedge = true,
	Soil = true,
	FlowerR = true,
	FlowerY = true,
	FlowerW = true,
	-- Bellmont Hills mansions (clipped HedgeBox hedges stay solid)
	Blossom = true,
	Ivy = true,
}

local function solidInWalkIn(name: string): boolean
	for _, pat in WALK_IN_SOLID do
		if name:match(pat) then
			return true
		end
	end
	return false
end

-- Invisible boxes from CityColliders, placed through one reference mesh part (its bounding box
-- centre in model space is known), so they follow the model wherever it stands.
local function buildCollision(model: Model): boolean
	local key = model:GetAttribute("CityModel")
	local data = type(key) == "string" and Colliders[key]
	if not data then
		return false
	end
	local ref = model:FindFirstChild(data.ref, true)
	if not (ref and ref:IsA("BasePart")) then
		warn(`[City] {model.Name}: collision reference part {data.ref} missing`)
		return false
	end
	local refMin = Vector3.new(data.refMin[1], data.refMin[2], data.refMin[3])
	local refMax = Vector3.new(data.refMax[1], data.refMax[2], data.refMax[3])
	local span = refMax - refMin
	local scale = if span.X > 0.01 then ref.Size.X / span.X else 1
	local frame = ref.CFrame * CFrame.new(-(refMin + refMax) / 2 * scale)
	local old = model:FindFirstChild("Collision")
	if old then
		old:Destroy()
	end
	local folder = Instance.new("Folder")
	folder.Name = "Collision"
	for _, b in data.boxes do
		local p = Instance.new("Part")
		p.Name = "Box"
		p.Anchored = true
		p.CanCollide = true
		p.CanQuery = true
		p.CanTouch = false
		p.CastShadow = false
		p.Transparency = 1
		p.Material = BOX_MATERIALS[(b[7] or 0) + 1] or Enum.Material.Concrete
		p.Size = Vector3.new(math.max(b[4], 0.05), math.max(b[5], 0.05), math.max(b[6], 0.05)) * scale
		local cf = if #b >= 16
			then CFrame.new(
				b[1] * scale,
				b[2] * scale,
				b[3] * scale,
				b[8],
				b[9],
				b[10],
				b[11],
				b[12],
				b[13],
				b[14],
				b[15],
				b[16]
			)
			else CFrame.new(b[1] * scale, b[2] * scale, b[3] * scale)
		p.CFrame = frame * cf
		p.Parent = folder
	end
	folder.Parent = model
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") and d.Parent ~= folder and not isDoorPart(d.Name) then
			d.CollisionGroup = VISUAL_GROUP
			d.CanTouch = false
		end
	end
	return true
end

-- How a city model streams to players (Workspace.StreamingEnabled is on, target radius in
-- default.project.json). Nothing is Persistent any more: that made every player download the
-- whole city (~1.9M triangles, ~600 textures) up front.
--   world-wide models (streets, tree rows; wider than WIDE studs)  Default: parts stream in
--     piece by piece round the player
--   everything else (houses, shops, towers, the fort)  Atomic: the whole building, collision
--     boxes and doors included, streams in together near the player. From far away players see
--     Roblox's own low-detail copy instead (LevelOfDetail StreamingMesh, set in the map by
--     tools/build_city_map.py; scripts can't set it), so the skyline still shows.
local WIDE = 600 -- studs; same as WIDE in tools/build_city_map.py

local function streamingMode(model: Model): Enum.ModelStreamingMode
	local _, size = model:GetBoundingBox()
	if math.max(size.X, size.Z) > WIDE then
		return Enum.ModelStreamingMode.Default
	end
	return Enum.ModelStreamingMode.Atomic
end

local function style(model: Model)
	applyTextures(model)
	local exact = buildCollision(model)
	local noCollide = model:GetAttribute("MeshNoCollide") == true
	local walkIn = not exact and model:FindFirstChild("WallF1", true) ~= nil
	if model.Name:match("^Street") then
		-- old baked street lamps (only in street meshes uploaded before 2026-11-07): the City Prop
		-- lamp models at the end of this script stand on their plinths instead
		for _, d in model:GetDescendants() do
			if d:IsA("BasePart") and (OLD_LAMP_PARTS[d.Name] or d.Name:match("^StreetLamp%d")) then
				d:Destroy()
			end
		end
	end
	for _, d in model:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		elseif d:IsA("BasePart") and d.Parent and d.Parent.Name == "Collision" then
			continue
		elseif d:IsA("BasePart") then
			d.Anchored = true
			if DECO[d.Name] or d.Name:match("^Poster") or d.Name:match("^ShelfGoods") or d.Name:match("^Deco") then
				-- Thin dressing: never blocks walking or bullets.
				d.CanCollide = false
				d.CanQuery = false
			end
			if not exact and (PLANTS[d.Name] or (walkIn and not solidInWalkIn(d.Name))) then
				d.CanCollide = false
			end
			if noCollide and not isDoorPart(d.Name) then
				-- collision comes from invisible box colliders (City/FortHaldenColliders); gates
				-- (Client/CityDoors) keep their own
				d.CanCollide = false
				d.CanTouch = false
			end
			if d.Name:match("^Spot%u") then
				-- marker (gun shop: SpotBuy / SpotClerk / SpotCam, read by Server/GunShop): invisible
				d.Transparency = 1
				d.CanCollide = false
				d.CanQuery = false
				d.CanTouch = false
				d.CastShadow = false
			end
			if d.Name:match("^Fx") then
				-- fountain water (Client/FountainFx animates it): walk through, no shadows
				d.CanCollide = false
				d.CanQuery = false
				d.CastShadow = false
				if d.Name == "FxJet" then
					d.Transparency = 0.45
				elseif d.Name == "FxPool" then
					d.Transparency = 0.12
				end
			end
			if ALPHA[d.Name] then
				-- A texture's transparent pixels only cut through when the part itself is
				-- a hair transparent.
				d.Transparency = 0.02
			elseif d.Name:match("^%a+%dGlass$") then
				-- door / gate glass (Swing1Glass ...): see-through, moves with its door
				d.Material = Enum.Material.Glass
				d.Transparency = 0.55
				d.CastShadow = false
			elseif d.Name:match("^ClearGlass") then
				d.Material = Enum.Material.Glass
				d.Transparency = 0.6
				d.CastShadow = false
			elseif d.Name:match("^LightCeil") then
				neon(d)
				downLight(d, 18, 0.6, 1.5)
			elseif d.Name:match("^Light") then
				neon(d)
			elseif d.Name:match("^StreetLamp%d") then
				neon(d)
				local light = downLight(d, 34, 0, 2.2)
				light.Shadows = false
				light.Angle = 150
			elseif d.Name:match("^Signal%u%u%a+$") then
				-- traffic signal lens: Client/TrafficSignals lights it by phase
				for _, c in d:GetChildren() do
					if c:IsA("SurfaceAppearance") then
						c:Destroy()
					end
				end
				if d:IsA("MeshPart") then
					d.TextureID = ""
				end
				d.CastShadow = false
				d.Material = Enum.Material.SmoothPlastic
			elseif d.Name:match("^Lamp%d") then
				neon(d)
				downLight(d, 26, 0.6, 3)
			elseif d.Name == "ShopLamp" then
				neon(d)
				downLight(d, 16, 0.4, 2)
			elseif NEON[d.Name] then
				neon(d)
				d.Color = NEON[d.Name]
				local glow = Instance.new("PointLight")
				glow.Range, glow.Brightness, glow.Color = 12, 0, NEON[d.Name]
				glow.Parent = d
				table.insert(lamps, { light = glow, day = 0, night = 1.5 })
			elseif d.Name == "Sconce" then
				neon(d)
				d.Color = Color3.fromRGB(255, 226, 170)
			elseif d.Name == "PriceFace" then
				local glow = Instance.new("PointLight")
				glow.Range, glow.Brightness, glow.Color = 14, 0, Color3.fromRGB(255, 220, 170)
				glow.Parent = d
				table.insert(lamps, { light = glow, day = 0, night = 1.2 })
			end
		end
	end
	model.ModelStreamingMode = streamingMode(model)
	-- loaded + styled: Server/Atms (and anything else that decorates city models) waits for this
	model:SetAttribute("CityReady", true)
end

local city = workspace:WaitForChild("City", 10)
local buildings = city and city:WaitForChild("Buildings", 10)
if not buildings then
	warn("[City] workspace.City.Buildings not found")
	return
end

-- Day/night: 0 by day, 1 at night, fading over an hour at dusk and dawn.
local function nightness(clock: number): number
	if clock >= 19 or clock < 5 then
		return 1
	elseif clock >= 18 then
		return clock - 18
	elseif clock < 6 then
		return 6 - clock
	end
	return 0
end

local last = -1
RunService.Heartbeat:Connect(function()
	local n = math.floor(nightness(Lighting.ClockTime) * 20 + 0.5) / 20
	if n == last then
		return
	end
	last = n
	for _, l in lamps do
		l.light.Brightness = l.day + (l.night - l.day) * n
	end
	local lit = n >= 0.5
	for _, g in lampGlass do
		g.Material = if lit then Enum.Material.Neon else Enum.Material.SmoothPlastic
		g.Color = if lit then LAMP_COLOR else GLASS_COLOR
	end
end)

-- City Props (2026-11-07): Roblox models (Shared/CityPropIds) on every street light and traffic
-- signal spot. They are in the map itself (City/StreetLamps, City/TrafficSignals from
-- tools/city_props.py), so the LiveSync plugin (v10+) shows them in edit mode; any still empty
-- here is loaded now. Then, from Shared/CityPropInfo (tools/city_prop_scan.py): the lamp glass
-- glows at night with the same light as the old baked lamps, each signal lens gets a disc named
-- Signal<EW|NS><Red|Amber|Green> that Client/TrafficSignals lights, and the models themselves
-- don't collide: an invisible box round each pole does (cars, players, bullets).
local PropInfo = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared"):WaitForChild("CityPropInfo")) :: any
local LENS_OFF = Color3.fromRGB(30, 30, 30) -- signal discs before Client/TrafficSignals lights them

local function v3(t: { number }): Vector3
	return Vector3.new(t[1], t[2], t[3])
end

-- a part by name (the pack names its model and its main part the same, so FindFirstChild won't do)
local function findPart(root: Instance, name: string): BasePart?
	for _, d in root:GetDescendants() do
		if d:IsA("BasePart") and d.Name == name then
			return d
		end
	end
	return nil
end

local function finishProp(m: Model)
	local key = m:GetAttribute("CityProp")
	local info = type(key) == "string" and PropInfo[key]
	if not info then
		warn(`[CityProps] {m.Name}: no CityPropInfo for {key}`)
		return
	end
	if not hasParts(m) then
		load(m)
	end
	local ref = findPart(m, info.ref)
	if not ref then
		warn(`[CityProps] {m.Name}: reference part {info.ref} missing`)
		return
	end
	local s = tonumber(m:GetAttribute("LiveSyncScale")) or 1
	for _, d in m:GetDescendants() do
		if d:IsA("Script") or d:IsA("LocalScript") then
			d:Destroy()
		elseif d:IsA("BasePart") then
			d.Anchored = true
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
		end
	end
	-- lamp glass: plain by day, Neon + a wide down light at night
	local phase = m:GetAttribute("SignalPhase")
	local glass = if phase then nil else findPart(m, info.glow)
	if glass and glass ~= ref then
		for _, c in glass:GetChildren() do
			if c:IsA("SurfaceAppearance") then
				c:Destroy()
			end
		end
		if glass:IsA("MeshPart") then
			glass.TextureID = ""
		end
		glass.CastShadow = false
		local lit = last >= 0.5
		glass.Material = if lit then Enum.Material.Neon else Enum.Material.SmoothPlastic
		glass.Color = if lit then LAMP_COLOR else GLASS_COLOR
		table.insert(lampGlass, glass)
		local light = downLight(glass, 34, 0, 2.2)
		light.Shadows = false
		light.Angle = 150
		light.Brightness = 2.2 * math.max(last, 0)
	end
	-- the pole up to the lamp head / signal arm
	local foot = ref.CFrame:PointToWorldSpace(v3(info.foot) * s)
	local poleH = math.min(info.glowAt[2] - info.foot[2], info.height * 0.85) * s
	local box = Instance.new("Part")
	box.Name = "PoleCollider"
	box.Anchored = true
	box.CanTouch = false
	box.CastShadow = false
	box.Transparency = 1
	box.Material = Enum.Material.Metal
	box.Size = Vector3.new(info.pole * s, poleH, info.pole * s)
	box.CFrame = ref.CFrame.Rotation + foot + Vector3.new(0, poleH / 2, 0)
	box.Parent = m
	-- signal lens discs over the painted lenses
	if type(phase) == "string" then
		for _, l in info.lenses or {} do
			local pos = ref.CFrame:PointToWorldSpace(Vector3.new(l[2], l[3], l[4]) * s)
			local n = ref.CFrame:VectorToWorldSpace(Vector3.new(l[5], l[6], l[7]))
			local disc = Instance.new("Part")
			disc.Name = `Signal{phase}{l[1]}`
			disc.Shape = Enum.PartType.Cylinder
			disc.Size = Vector3.new(0.06, l[8] * 2 * s, l[8] * 2 * s)
			disc.CFrame = CFrame.lookAt(pos + n * 0.03, pos + n) * CFrame.Angles(0, math.rad(90), 0)
			disc.Anchored = true
			disc.CanCollide = false
			disc.CanQuery = false
			disc.CanTouch = false
			disc.CastShadow = false
			disc.Material = Enum.Material.SmoothPlastic
			disc.Color = LENS_OFF
			disc.Parent = m
		end
	end
	-- a small model each: streams in whole near the player
	m.ModelStreamingMode = Enum.ModelStreamingMode.Atomic
end

task.spawn(function()
	for _, folderName in { "StreetLamps", "TrafficSignals" } do
		local folder = city:FindFirstChild(folderName)
		local n = 0
		for _, m in (if folder then folder:GetChildren() else {}) do
			if m:IsA("Model") and m:GetAttribute("CityProp") then
				finishProp(m)
				n += 1
			end
		end
		print(`[CityProps] {n} {folderName} ready`)
	end
end)

-- Buildings, nearest to the spawn first, a few at a time: one LoadAsset after another took
-- minutes on a fresh server (~130 models). Props above load alongside.
local LOADERS = 6
local started = os.clock()
local spawnPart = workspace:FindFirstChild("Spawn", true)
local spawnAt = if spawnPart and spawnPart:IsA("BasePart") then spawnPart.Position else Vector3.zero

local queue: { Model } = {}
local dist: { [Model]: number } = {}
for _, model in buildings:GetChildren() do
	if model:IsA("Model") and model:GetAttribute("LiveSyncAsset") then
		local c = model:GetAttribute("LiveSyncBoxCenter")
		local at = if typeof(c) == "Vector3" then c else model:GetPivot().Position
		dist[model] = (at - spawnAt).Magnitude
		table.insert(queue, model)
	end
end
table.sort(queue, function(a, b)
	return dist[a] < dist[b]
end)

local nextIndex, running = 0, LOADERS
for _ = 1, LOADERS do
	task.spawn(function()
		while true do
			nextIndex += 1
			local model = queue[nextIndex]
			if not model then
				break
			end
			if not hasParts(model) then
				load(model)
			end
			local ok, err = pcall(style, model)
			if not ok then
				warn(`[City] {model.Name}: {err}`)
			end
		end
		running -= 1
		if running == 0 then
			table.clear(assetCache)
			print(`[City] {#queue} buildings ready in {string.format("%.1f", os.clock() - started)} s`)
		end
	end)
end
