--!strict
-- Fountain water in the city (parts from art/blender/hood/build_hood.py): flipbook animation by
-- swapping MeshPart.TextureID through looping frames (tools/fountain_fx_textures.py ->
-- TextureIds.Fountain), plus spray mist and splash droplets where the water lands.
--   FxPool    caustic water surfaces   Pool0..15, 8 fps
--   FxFall    falling sheets           Fall0..7, 14 fps (streaks run down)
--   FxRipple  impact rings             Ripple0..7, 10 fps

local ContentProvider = game:GetService("ContentProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local TextureIds = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("TextureIds"))
local frames = (TextureIds :: any).Fountain
if not frames then
	return
end

local SETS = {
	FxPool = { prefix = "Pool", count = 16, fps = 8 },
	FxFall = { prefix = "Fall", count = 8, fps = 14 },
	FxRipple = { prefix = "Ripple", count = 8, fps = 10 },
}

local ids: { [string]: { string } } = {}
local all = {}
for name, set in SETS do
	ids[name] = {}
	for i = 0, set.count - 1 do
		local id = frames[`{set.prefix}{i}`]
		if id then
			table.insert(ids[name], `rbxassetid://{id}`)
			table.insert(all, `rbxassetid://{id}`)
		end
	end
end
task.spawn(function()
	pcall(ContentProvider.PreloadAsync, ContentProvider, all)
end)

local city = workspace:WaitForChild("City", 30)
if not city then
	return
end

local parts: { [string]: { MeshPart } } = { FxPool = {}, FxFall = {}, FxRipple = {} }
local seen: { [Instance]: boolean } = {}

local function addSpray(part: BasePart)
	-- fine mist + droplets over the ripple rings (where falling water lands)
	local mist = Instance.new("ParticleEmitter")
	mist.Texture = "rbxasset://textures/particles/smoke_main.dds"
	mist.Color = ColorSequence.new(Color3.fromRGB(235, 245, 255))
	mist.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.85), NumberSequenceKeypoint.new(1, 1) })
	mist.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1.2), NumberSequenceKeypoint.new(1, 3) })
	mist.Lifetime = NumberRange.new(0.8, 1.4)
	mist.Rate = 18
	mist.Speed = NumberRange.new(0.5, 1.5)
	mist.SpreadAngle = Vector2.new(30, 30)
	mist.EmissionDirection = Enum.NormalId.Top
	mist.Shape = Enum.ParticleEmitterShape.Box
	mist.LightEmission = 0.2
	mist.Parent = part
	local drops = Instance.new("ParticleEmitter")
	drops.Texture = "rbxasset://textures/particles/sparkles_main.dds"
	drops.Color = ColorSequence.new(Color3.fromRGB(220, 240, 255))
	drops.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.3), NumberSequenceKeypoint.new(1, 1) })
	drops.Size = NumberSequence.new(0.18)
	drops.Lifetime = NumberRange.new(0.35, 0.6)
	drops.Rate = 40
	drops.Speed = NumberRange.new(3, 6)
	drops.SpreadAngle = Vector2.new(25, 25)
	drops.Acceleration = Vector3.new(0, -workspace.Gravity * 0.5, 0)
	drops.EmissionDirection = Enum.NormalId.Top
	drops.Shape = Enum.ParticleEmitterShape.Box
	drops.Parent = part
end

local function track(d: Instance)
	if seen[d] or not d:IsA("MeshPart") or not parts[d.Name] then
		return
	end
	seen[d] = true
	table.insert(parts[d.Name], d)
	if d.Name == "FxRipple" then
		addSpray(d)
	end
end

for _, d in city:GetDescendants() do
	track(d)
end
city.DescendantAdded:Connect(track)

local clock = 0
local last: { [string]: number } = {}
RunService.RenderStepped:Connect(function(dt)
	clock += dt
	for name, set in SETS do
		local list = ids[name]
		if #list == 0 then
			continue
		end
		local frame = math.floor(clock * set.fps) % #list + 1
		if last[name] ~= frame then
			last[name] = frame
			for _, p in parts[name] do
				p.TextureID = list[frame]
			end
		end
	end
end)
