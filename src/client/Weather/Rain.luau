-- Rain around the camera:
--   streaks   a GRID x GRID patch of ParticleEmitters over the camera. Each cell casts a ray
--             down from its emitter, and the drops live just long enough to reach what's
--             under them, so rain stops at roofs, canopies and awnings. A cell with
--             something above its emitter (you're inside a tall building) is switched off.
--   splashes  Blender mesh crowns + spreading ripples (RainCrown / RainRipple from
--             ReplicatedStorage.WeatherMeshes) and a few spray droplets where drops land
--   mist      big faint streaky sheets falling further out, so heavy rain looks thick
--   sound     light + heavy rain loops (Shared/SoundIds), muffled when there's a roof over you
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local SoundService = game:GetService("SoundService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local SoundIds = require(Shared:WaitForChild("SoundIds"))
local TextureIds = require(Shared:WaitForChild("TextureIds"))

local Rain = {}

local CELL = 16 -- studs per emitter cell
local GRID = 7 -- cells per side (112 x 112 studs of rain round the camera)
local HEIGHT = 48 -- emitters sit this far above the camera
local SPEED = 95 -- drop speed, studs/s
local RATE = 95 -- drops per second per cell at full rain
local SPLASH_RATE = 80 -- splashes per second at full rain
local SPLASH_RADIUS = 46
local POOL = 48

local tex = TextureIds.Weather or {}
local folder: Folder
local params = RaycastParams.new()
params.FilterType = Enum.RaycastFilterType.Exclude
params.RespectCanCollide = true
params.IgnoreWater = false

type Cell = { part: Part, emitter: ParticleEmitter, life: number, open: boolean }
local cells: { Cell } = {}
local origin = Vector2.new(math.huge, math.huge) -- grid corner the cells were placed for
local castIndex = 0
local mist: Part
local mistEmitter: ParticleEmitter
local spray: Attachment
local sprayEmitter: ParticleEmitter
local lightLoop: Sound
local heavyLoop: Sound
local muffle: EqualizerSoundEffect
local indoor = 0 -- 0 out in the open .. 1 under a roof (smoothed)
local indoorTarget = 0
local roofClock = 0
local filterClock = 0
local splashBudget = 0
local lastRate = -1

type Splash = {
	crown: MeshPart,
	ripple: MeshPart,
	cf: CFrame,
	t0: number,
	crownSize: Vector3,
	rippleSize: number,
	busy: boolean,
}
local splashes: { Splash } = {}
local crownBase = Vector3.new(1, 1, 1)
local rippleBase = Vector3.new(1, 0.05, 1)

local function invisiblePart(name: string, size: Vector3): Part
	local p = Instance.new("Part")
	p.Name = name
	p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
	p.Transparency = 1
	p.Size = size
	p.Parent = folder
	return p
end

local function streakEmitter(parent: Instance): ParticleEmitter
	local e = Instance.new("ParticleEmitter")
	e.Texture = if tex.RainStreak then `rbxassetid://{tex.RainStreak}` else ""
	e.Orientation = Enum.ParticleOrientation.FacingCameraWorldUp
	e.EmissionDirection = Enum.NormalId.Bottom
	e.Speed = NumberRange.new(SPEED * 0.92, SPEED * 1.08)
	e.SpreadAngle = Vector2.new(2, 2)
	e.Size = NumberSequence.new(2.4)
	e.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.08, 0.45),
		NumberSequenceKeypoint.new(1, 0.45),
	})
	e.Color = ColorSequence.new(Color3.fromRGB(205, 215, 230))
	e.LightEmission = 0.15
	e.LightInfluence = 0.85
	e.Rate = 0
	e.Lifetime = NumberRange.new(0.5)
	e.Parent = parent
	return e
end

local function makeSplashes()
	local meshes = ReplicatedStorage:WaitForChild("WeatherMeshes", 60)
	local crown = meshes and meshes:FindFirstChild("RainCrown") :: MeshPart?
	local ripple = meshes and meshes:FindFirstChild("RainRipple") :: MeshPart?
	if not crown or not ripple then
		warn("[Weather] rain splash meshes missing, splashes off")
		return
	end
	crownBase = crown.Size
	rippleBase = ripple.Size
	local water = Color3.fromRGB(214, 224, 236)
	for _ = 1, POOL do
		local c = crown:Clone()
		local r = ripple:Clone()
		for _, p in { c, r } do
			p.Anchored, p.CanCollide, p.CanQuery, p.CanTouch, p.CastShadow = true, false, false, false, false
			p.Material = Enum.Material.SmoothPlastic
			p.Reflectance = 0.15
			p.Color = water
			p.Transparency = 1
			p.Parent = folder
		end
		table.insert(
			splashes,
			{ crown = c, ripple = r, cf = CFrame.identity, t0 = 0, crownSize = crownBase, rippleSize = 1, busy = false }
		)
	end
end

function Rain.start()
	folder = Instance.new("Folder")
	folder.Name = "WeatherRain"
	folder.Parent = workspace
	for _ = 1, GRID * GRID do
		local p = invisiblePart("RainCell", Vector3.new(CELL, 0.2, CELL))
		table.insert(cells, { part = p, emitter = streakEmitter(p), life = 0.5, open = true })
	end

	mist = invisiblePart("RainMist", Vector3.new(260, 0.2, 260))
	mistEmitter = Instance.new("ParticleEmitter")
	mistEmitter.Texture = if tex.RainSheet then `rbxassetid://{tex.RainSheet}` else ""
	mistEmitter.Orientation = Enum.ParticleOrientation.FacingCameraWorldUp
	mistEmitter.EmissionDirection = Enum.NormalId.Bottom
	mistEmitter.Speed = NumberRange.new(26, 34)
	mistEmitter.Size = NumberSequence.new(46, 70)
	mistEmitter.Lifetime = NumberRange.new(2.4, 3.2)
	mistEmitter.Transparency = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 1),
		NumberSequenceKeypoint.new(0.25, 0.86),
		NumberSequenceKeypoint.new(0.75, 0.86),
		NumberSequenceKeypoint.new(1, 1),
	})
	mistEmitter.Color = ColorSequence.new(Color3.fromRGB(200, 206, 216))
	mistEmitter.LightInfluence = 1
	mistEmitter.Rate = 0
	mistEmitter.Parent = mist

	spray = Instance.new("Attachment")
	spray.Parent = workspace.Terrain
	sprayEmitter = Instance.new("ParticleEmitter")
	sprayEmitter.Texture = if tex.RainSpray then `rbxassetid://{tex.RainSpray}` else ""
	sprayEmitter.EmissionDirection = Enum.NormalId.Top
	sprayEmitter.SpreadAngle = Vector2.new(55, 55)
	sprayEmitter.Speed = NumberRange.new(4, 9)
	sprayEmitter.Acceleration = Vector3.new(0, -60, 0)
	sprayEmitter.Lifetime = NumberRange.new(0.18, 0.32)
	sprayEmitter.Size = NumberSequence.new(0.55, 0.15)
	sprayEmitter.Transparency = NumberSequence.new(0.3, 1)
	sprayEmitter.Color = ColorSequence.new(Color3.fromRGB(220, 228, 238))
	sprayEmitter.LightInfluence = 0.8
	sprayEmitter.Rate = 0
	sprayEmitter.Parent = spray

	local function loop(name: string, id: number?): Sound
		local s = Instance.new("Sound")
		s.Name = name
		s.SoundId = if id then `rbxassetid://{id}` else ""
		s.Looped = true
		s.Volume = 0
		s.Parent = SoundService
		return s
	end
	lightLoop = loop("RainLoop", SoundIds.RainLoop)
	heavyLoop = loop("RainHeavyLoop", SoundIds.RainHeavyLoop)
	-- one muffler shared by both loops: a SoundGroup with an EQ that cuts the highs indoors
	local group = Instance.new("SoundGroup")
	group.Name = "Rain"
	group.Volume = 1
	group.Parent = SoundService
	muffle = Instance.new("EqualizerSoundEffect")
	muffle.HighGain, muffle.MidGain, muffle.LowGain = 0, 0, 0
	muffle.Parent = group
	lightLoop.SoundGroup = group
	heavyLoop.SoundGroup = group

	task.spawn(makeSplashes)
end

local function refreshFilter()
	local list: { Instance } = { folder, workspace:FindFirstChild("WeatherSky") :: Instance }
	for _, plr in Players:GetPlayers() do
		if plr.Character then
			table.insert(list, plr.Character)
		end
	end
	if workspace.CurrentCamera then
		table.insert(list, workspace.CurrentCamera)
	end
	params.FilterDescendantsInstances = list
end

-- where does rain from this cell stop? Sets the drop lifetime, or shuts the cell off when
-- something is above its emitter.
local function cast(c: Cell)
	local top = c.part.Position
	local up = workspace:Raycast(top, Vector3.new(0, 400, 0), params)
	if up then
		c.open = false
		return
	end
	c.open = true
	local down = workspace:Raycast(top, Vector3.new(0, -HEIGHT * 3, 0), params)
	local drop = if down then top.Y - down.Position.Y else HEIGHT * 2
	c.life = math.clamp(drop / SPEED, 0.05, 1.6)
	c.emitter.Lifetime = NumberRange.new(c.life)
end

local function startSplash(pos: Vector3, normal: Vector3, now: number)
	for _, s in splashes do
		if not s.busy then
			s.busy = true
			s.t0 = now
			local k = math.random() * 0.35 + 0.35
			s.crownSize = crownBase * k
			s.rippleSize = math.random() * 1.2 + 1.6
			local spin = CFrame.Angles(0, math.random() * math.pi * 2, 0)
			local cf
			if normal.Y > 0.98 then
				cf = CFrame.new(pos + Vector3.new(0, 0.02, 0)) * spin
			else
				local right = normal:Cross(Vector3.zAxis).Unit
				cf = CFrame.fromMatrix(pos + normal * 0.02, right, normal) * spin
			end
			s.cf = cf
			s.ripple.CFrame = cf
			return
		end
	end
end

local function stepSplashes(now: number)
	for _, s in splashes do
		if s.busy then
			local age = now - s.t0
			-- crown: pops up and out in a quarter second
			local a = math.clamp(age / 0.22, 0, 1)
			if a < 1 then
				local grow = 0.35 + 0.65 * math.sqrt(a)
				local size = s.crownSize * Vector3.new(0.6 + 0.4 * grow, grow, 0.6 + 0.4 * grow)
				s.crown.Size = size
				s.crown.CFrame = s.cf * CFrame.new(0, size.Y / 2, 0) -- MeshParts sit on their middle
				s.crown.Transparency = 0.3 + 0.7 * a * a
			elseif s.crown.Transparency < 1 then
				s.crown.Transparency = 1
			end
			-- ripple: spreads and fades over 0.7 s
			local b = math.clamp(age / 0.7, 0, 1)
			local r = s.rippleSize * (0.15 + 0.85 * math.sqrt(b))
			s.ripple.Size = Vector3.new(r, rippleBase.Y, r)
			s.ripple.Transparency = 0.45 + 0.55 * b
			if b >= 1 then
				s.busy = false
			end
		end
	end
end

-- a foot landing in the wet (Footprints): a ripple, plus spray while it's raining
function Rain.footSplash(pos: Vector3, normal: Vector3, raining: boolean)
	if not spray or #splashes == 0 then
		return
	end
	startSplash(pos, normal, os.clock())
	if raining then
		spray.WorldPosition = pos + Vector3.new(0, 0.05, 0)
		sprayEmitter:Emit(3)
	end
end

function Rain.update(w, dt: number)
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local camPos = cam.CFrame.Position
	local rain = w.rain
	local now = os.clock()

	filterClock -= dt
	if filterClock <= 0 then
		filterClock = 1
		refreshFilter()
	end

	-- move the cell grid with the camera (snapped, so cells keep their world spots)
	local gx = math.floor(camPos.X / CELL) - (GRID - 1) / 2
	local gz = math.floor(camPos.Z / CELL) - (GRID - 1) / 2
	local y = camPos.Y + HEIGHT
	local moved = Vector2.new(gx, gz) ~= origin or math.abs(cells[1].part.Position.Y - y) > 6
	if moved then
		origin = Vector2.new(gx, gz)
		for i, c in cells do
			local ix = (i - 1) % GRID
			local iz = (i - 1) // GRID
			c.part.CFrame = CFrame.new((gx + ix + 0.5) * CELL, y, (gz + iz + 0.5) * CELL)
		end
	end

	local rate = if rain > 0.01 then RATE * rain else 0
	if rate > 0 then
		-- recast: everything after a move, else a few cells a frame round-robin
		local count = if moved then #cells else 5
		for _ = 1, count do
			castIndex = castIndex % #cells + 1
			cast(cells[castIndex])
		end
	end
	local wind = Config.Weather.WindDirection.Unit * (4 + 10 * w.heavy)
	local accel = Vector3.new(wind.X, 0, wind.Y)
	local rounded = math.floor(rate * 4) / 4
	for _, c in cells do
		local r = if c.open then rounded else 0
		if c.emitter.Rate ~= r then
			c.emitter.Rate = r
		end
	end
	if rounded ~= lastRate then
		lastRate = rounded
		for _, c in cells do
			c.emitter.Acceleration = accel
		end
		mistEmitter.Acceleration = accel
	end

	-- mist sheets further out
	mist.CFrame = CFrame.new(camPos.X, camPos.Y + 40, camPos.Z)
	local mistRate = math.floor(16 * math.max(rain - 0.2, 0) / 0.8 * (1 - indoor) * 4) / 4
	if mistEmitter.Rate ~= mistRate then
		mistEmitter.Rate = mistRate
	end

	-- splashes
	if rain > 0.01 and #splashes > 0 then
		splashBudget += SPLASH_RATE * rain * dt
		local tries = 0
		while splashBudget >= 1 and tries < 8 do
			splashBudget -= 1
			tries += 1
			local ang = math.random() * math.pi * 2
			local d = SPLASH_RADIUS * math.sqrt(math.random())
			local from = Vector3.new(camPos.X + math.cos(ang) * d, camPos.Y + HEIGHT, camPos.Z + math.sin(ang) * d)
			local hit = workspace:Raycast(from, Vector3.new(0, -HEIGHT * 3, 0), params)
			if hit and hit.Normal.Y > 0.6 and not workspace:Raycast(from, Vector3.new(0, 400, 0), params) then
				startSplash(hit.Position, hit.Normal, now)
				if math.random() < 0.5 then
					spray.WorldPosition = hit.Position + Vector3.new(0, 0.05, 0)
					sprayEmitter:Emit(2)
				end
			end
		end
		splashBudget = math.min(splashBudget, 4)
	end
	stepSplashes(now)

	-- sound: muffled under a roof
	roofClock -= dt
	if roofClock <= 0 then
		roofClock = 0.3
		indoorTarget = if workspace:Raycast(camPos, Vector3.new(0, 150, 0), params) then 1 else 0
	end
	indoor += (indoorTarget - indoor) * math.min(dt * 3, 1)
	local vol = Config.Weather.RainVolume * rain * (1 - 0.45 * indoor)
	lightLoop.Volume = vol * (1 - 0.7 * w.heavy)
	heavyLoop.Volume = vol * w.heavy * 1.15
	muffle.HighGain = -24 * indoor
	muffle.MidGain = -9 * indoor
	for _, s in { lightLoop, heavyLoop } do
		if s.Volume > 0.001 and not s.IsPlaying then
			s:Play()
		elseif s.Volume <= 0.001 and s.IsPlaying then
			s:Stop()
		end
	end
end

return Rain
