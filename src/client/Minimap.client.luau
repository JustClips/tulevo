-- GTA-style radar in the bottom-left, right above the health bar.
--
-- The radar is a simple drawing of the map, not a camera view of it. Tag map
-- parts in Studio (Tag Editor / Properties > Tags) and each one shows up as a
-- flat colored shape:
--   Road     light grey, drawn thinner than the real road
--   Building grey block on the dark ground
--   Water    dark blue
--   Park     dark green
-- A tag works on a Part (its footprint), a Model (its bounding box) or a
-- Folder (every part inside). Untagged things don't show. The radar rebuilds
-- itself when tags are added or removed.
--
-- The radar turns with the camera (forward = up) and is tilted like GTA's.
-- The player is a 2D arrow; an "N" marker on the edge points north (-Z).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local CollectionService = game:GetService("CollectionService")

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

-- Layout (matches HealthHud: left 20, bar 18 px tall, 8 px from bottom)
local W, H = 230, 150
local LEFT, BOTTOM = 20, 8 + 18 + 3
local BORDER = 2

-- View
local DIST = 700 -- studs from the radar camera to the point it looks at
local FOV = 24 -- smaller = more zoomed in
local TILT = math.rad(38) -- 0 = straight down
local AHEAD = 30 -- studs the view looks ahead of the player (player sits low, like GTA)

-- Arrow image (ForgeGUI, art/RadarArrow.png). Empty = a text arrow instead.
local ARROW_IMAGE = "rbxassetid://112768085815375"

-- Colors follow the GTA radar look: dark ground, low-contrast building blocks,
-- light thin roads. Road.Thin shrinks a road's width on the radar.
local LAYERS = {
	Park = { Color = Color3.fromRGB(58, 68, 56), Y = 0.1 },
	Water = { Color = Color3.fromRGB(52, 70, 86), Y = 0.2 },
	Building = { Color = Color3.fromRGB(78, 80, 80), Y = 0.3, Inset = 2 },
	Road = { Color = Color3.fromRGB(176, 178, 178), Y = 0.4, Thin = 0.45 },
}

local COLORS = {
	Frame = Color3.fromRGB(18, 18, 18),
	Ground = Color3.fromRGB(44, 46, 46),
	Arrow = Color3.fromRGB(240, 240, 240),
	North = Color3.fromRGB(30, 30, 30),
}

local gui = Instance.new("ScreenGui")
gui.Name = "Minimap"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = player:WaitForChild("PlayerGui")

local frame = Instance.new("Frame")
frame.Name = "Frame"
frame.AnchorPoint = Vector2.new(0, 1)
frame.Position = UDim2.new(0, LEFT, 1, -BOTTOM)
frame.Size = UDim2.fromOffset(W, H)
frame.BackgroundColor3 = COLORS.Frame
frame.BorderSizePixel = 0
frame.Parent = gui

local vp = Instance.new("ViewportFrame")
vp.Name = "View"
vp.Position = UDim2.fromOffset(BORDER, BORDER)
vp.Size = UDim2.new(1, -BORDER * 2, 1, -BORDER * 2)
vp.BackgroundColor3 = COLORS.Ground
vp.BorderSizePixel = 0
vp.Ambient = Color3.fromRGB(255, 255, 255)
vp.LightColor = Color3.fromRGB(60, 60, 60)
vp.LightDirection = Vector3.new(0, -1, 0)
vp.ClipsDescendants = true
vp.Parent = frame

local vpCam = Instance.new("Camera")
vpCam.FieldOfView = FOV
vpCam.Parent = vp
vp.CurrentCamera = vpCam

local world = Instance.new("WorldModel")
world.Parent = vp

-- Player arrow
local arrow: GuiObject
if ARROW_IMAGE ~= "" then
	local img = Instance.new("ImageLabel")
	img.Image = ARROW_IMAGE
	img.BackgroundTransparency = 1
	img.Size = UDim2.fromOffset(13, 13)
	arrow = img
else
	local txt = Instance.new("TextLabel")
	txt.Text = "▲"
	txt.TextSize = 16
	txt.TextColor3 = COLORS.Arrow
	txt.TextStrokeTransparency = 0.2
	txt.BackgroundTransparency = 1
	txt.Size = UDim2.fromOffset(18, 18)
	arrow = txt
end
arrow.Name = "Arrow"
arrow.AnchorPoint = Vector2.new(0.5, 0.5)
arrow.ZIndex = 3
arrow.Parent = vp

-- North marker
local north = Instance.new("Frame")
north.Name = "North"
north.AnchorPoint = Vector2.new(0.5, 0.5)
north.Size = UDim2.fromOffset(18, 18)
north.BackgroundColor3 = COLORS.North
north.BorderSizePixel = 0
north.ZIndex = 3
north.Parent = vp
local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(1, 0)
corner.Parent = north
local nText = Instance.new("TextLabel")
nText.Size = UDim2.fromScale(1, 1)
nText.BackgroundTransparency = 1
nText.FontFace = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Bold)
nText.Text = "N"
nText.TextSize = 13
nText.TextColor3 = COLORS.Arrow
nText.ZIndex = 4
nText.Parent = north

-- Radar shapes -----------------------------------------------------------------
local function flat(v: Vector3): Vector3
	local f = Vector3.new(v.X, 0, v.Z)
	return if f.Magnitude > 1e-3 then f.Unit else Vector3.new(0, 0, -1)
end

local function slab(cf: CFrame, size: Vector3, layer)
	local look = flat(cf.LookVector)
	local right = flat(cf.RightVector)
	-- Footprint of a part that may be pitched/rolled: project its size onto the ground axes.
	local sx = math.abs(cf.RightVector:Dot(right)) * size.X
		+ math.abs(cf.UpVector:Dot(right)) * size.Y
		+ math.abs(cf.LookVector:Dot(right)) * size.Z
	local sz = math.abs(cf.RightVector:Dot(look)) * size.X
		+ math.abs(cf.UpVector:Dot(look)) * size.Y
		+ math.abs(cf.LookVector:Dot(look)) * size.Z
	if layer.Thin then
		if sx < sz then
			sx *= layer.Thin
		else
			sz *= layer.Thin
		end
	end
	if layer.Inset then
		sx -= layer.Inset * 2
		sz -= layer.Inset * 2
	end
	local h = 0.1
	local p = Instance.new("Part")
	p.Anchored = true
	p.CanCollide = false
	p.CastShadow = false
	p.Material = Enum.Material.SmoothPlastic
	p.Color = layer.Color
	p.Size = Vector3.new(math.max(sx, 0.2), h, math.max(sz, 0.2))
	p.CFrame = CFrame.lookAt(Vector3.new(cf.X, layer.Y + h / 2, cf.Z), Vector3.new(cf.X, layer.Y + h / 2, cf.Z) + look)
	p.Parent = world
end

local function addTagged(inst: Instance, layer)
	if inst:IsA("BasePart") then
		slab(inst.CFrame, inst.Size, layer)
	elseif inst:IsA("Model") then
		local cf, size = inst:GetBoundingBox()
		slab(cf, size, layer)
	else
		for _, d in inst:GetDescendants() do
			if d:IsA("BasePart") then
				slab(d.CFrame, d.Size, layer)
			end
		end
	end
end

local function rebuild()
	world:ClearAllChildren()
	for tag, layer in LAYERS do
		for _, inst in CollectionService:GetTagged(tag) do
			if inst:IsDescendantOf(workspace) then
				addTagged(inst, layer)
			end
		end
	end
end

local pending = false
local function scheduleRebuild()
	if pending then
		return
	end
	pending = true
	task.delay(0.5, function()
		pending = false
		rebuild()
	end)
end

for tag in LAYERS do
	CollectionService:GetInstanceAddedSignal(tag):Connect(scheduleRebuild)
	CollectionService:GetInstanceRemovedSignal(tag):Connect(scheduleRebuild)
end
rebuild()

-- Per-frame update ----------------------------------------------------------
local function yaw(v: Vector3): number
	return math.atan2(-v.X, -v.Z)
end

local tanHalf = math.tan(math.rad(FOV) / 2)

RunService.RenderStepped:Connect(function()
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local forward = flat(camera.CFrame.LookVector)
	local pos = if root then root.Position else camera.Focus.Position
	pos = Vector3.new(pos.X, 0, pos.Z)

	local target = pos + forward * AHEAD
	local viewDir = forward * math.sin(TILT) - Vector3.yAxis * math.cos(TILT)
	vpCam.CFrame = CFrame.lookAt(target - viewDir * DIST, target, forward)

	-- Place the arrow where the player is on the radar.
	local size = vp.AbsoluteSize
	local aspect = if size.Y > 0 then size.X / size.Y else 1
	local rel = vpCam.CFrame:PointToObjectSpace(pos)
	local depth = math.max(-rel.Z, 1)
	local nx = rel.X / depth / (tanHalf * aspect)
	local ny = rel.Y / depth / tanHalf
	arrow.Position = UDim2.fromScale(0.5 + nx / 2, 0.5 - ny / 2)

	local camYaw = yaw(forward)
	arrow.Visible = root ~= nil
	if root then
		arrow.Rotation = -math.deg(yaw(flat(root.CFrame.LookVector)) - camYaw)
	end

	-- North on the edge, pointing from the player: screen angle clockwise from up
	local dx, dy = math.sin(camYaw), -math.cos(camYaw)
	local cx, cy = (0.5 + nx / 2) * size.X, (0.5 - ny / 2) * size.Y
	local m = 11
	local tx = if dx > 0 then (size.X - m - cx) / dx elseif dx < 0 then (m - cx) / dx else math.huge
	local ty = if dy > 0 then (size.Y - m - cy) / dy elseif dy < 0 then (m - cy) / dy else math.huge
	local t = math.max(math.min(tx, ty), 0)
	north.Position = UDim2.fromOffset(cx + dx * t, cy + dy * t)
end)
