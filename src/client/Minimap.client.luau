-- GTA-style minimap (radar) in the bottom-left, right above the health bar.
-- A ViewportFrame shows a top-down copy of the map that turns with the camera
-- (camera forward = up on the radar). The player is a fixed arrow in the
-- middle, and an "N" marker on the edge points north (world -Z).
--
-- The map copy is made from Workspace once and rebuilt when top-level
-- children are added or removed. Players' characters and Terrain are skipped
-- (ViewportFrames can't show Terrain). Give anything the attribute
-- NoMinimap = true to leave it off the radar.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local camera = workspace.CurrentCamera

-- Layout (matches HealthHud: left 20, bar 22 px tall, 8 px from bottom)
local W, H = 280, 170
local LEFT, BOTTOM = 20, 8 + 22 + 3
local BORDER = 3

-- View: camera height and field of view decide how many studs fit on the radar
local HEIGHT = 600
local FOV = 20

local COLORS = {
	Frame = Color3.fromRGB(62, 70, 58),
	Ground = Color3.fromRGB(70, 78, 66),
	Arrow = Color3.fromRGB(235, 235, 235),
	North = Color3.fromRGB(40, 40, 40),
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
vp.Ambient = Color3.fromRGB(170, 170, 170)
vp.LightColor = Color3.fromRGB(255, 255, 255)
vp.LightDirection = Vector3.new(-0.3, -1, -0.2)
vp.ClipsDescendants = true
vp.Parent = frame

local vpCam = Instance.new("Camera")
vpCam.FieldOfView = FOV
vpCam.Parent = vp
vp.CurrentCamera = vpCam

local world = Instance.new("WorldModel")
world.Parent = vp

-- Player arrow (fixed in the middle)
local arrow = Instance.new("TextLabel")
arrow.Name = "Arrow"
arrow.AnchorPoint = Vector2.new(0.5, 0.5)
arrow.Position = UDim2.fromScale(0.5, 0.5)
arrow.Size = UDim2.fromOffset(18, 18)
arrow.BackgroundTransparency = 1
arrow.Text = "▲"
arrow.TextSize = 16
arrow.TextColor3 = COLORS.Arrow
arrow.TextStrokeTransparency = 0.3
arrow.ZIndex = 3
arrow.Parent = vp

-- North marker
local north = Instance.new("Frame")
north.Name = "North"
north.AnchorPoint = Vector2.new(0.5, 0.5)
north.Size = UDim2.fromOffset(18, 18)
north.BackgroundColor3 = COLORS.North
north.BackgroundTransparency = 0.2
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

-- Map copy ----------------------------------------------------------------
local function skip(inst: Instance): boolean
	if inst:IsA("Terrain") or inst:IsA("Camera") then
		return true
	end
	if inst:GetAttribute("NoMinimap") then
		return true
	end
	if inst:IsA("Model") and Players:GetPlayerFromCharacter(inst) then
		return true
	end
	return not (inst:IsA("BasePart") or inst:IsA("Model") or inst:IsA("Folder"))
end

local function strip(copy: Instance)
	for _, d in copy:GetDescendants() do
		if
			d:IsA("LuaSourceContainer")
			or d:IsA("Sound")
			or d:IsA("ParticleEmitter")
			or d:IsA("Light")
			or d:IsA("GuiBase")
		then
			d:Destroy()
		elseif d:IsA("Model") and Players:GetPlayerFromCharacter(d) then
			d:Destroy()
		end
	end
end

local function rebuild()
	world:ClearAllChildren()
	for _, child in workspace:GetChildren() do
		if not skip(child) then
			local ok, copy = pcall(function()
				local old = child.Archivable
				child.Archivable = true
				local c = child:Clone()
				child.Archivable = old
				return c
			end)
			if ok and copy then
				strip(copy)
				copy.Parent = world
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
	task.delay(1, function()
		pending = false
		rebuild()
	end)
end

workspace.ChildAdded:Connect(scheduleRebuild)
workspace.ChildRemoved:Connect(scheduleRebuild)
rebuild()

-- Per-frame update ----------------------------------------------------------
local function flat(v: Vector3): Vector3
	local f = Vector3.new(v.X, 0, v.Z)
	return if f.Magnitude > 1e-3 then f.Unit else Vector3.new(0, 0, -1)
end

local function yaw(v: Vector3): number
	return math.atan2(-v.X, -v.Z)
end

RunService.RenderStepped:Connect(function()
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local camLook = flat(camera.CFrame.LookVector)
	local pos = if root then root.Position else camera.Focus.Position

	vpCam.CFrame = CFrame.lookAt(pos + Vector3.new(0, HEIGHT, 0), pos, camLook)

	local camYaw = yaw(camLook)
	if root then
		arrow.Visible = true
		arrow.Rotation = -math.deg(yaw(flat(root.CFrame.LookVector)) - camYaw)
	else
		arrow.Visible = false
	end

	-- North on the edge: screen angle clockwise from up
	local a = camYaw
	local dx, dy = math.sin(a), -math.cos(a)
	local hw, hh = vp.AbsoluteSize.X / 2 - 11, vp.AbsoluteSize.Y / 2 - 11
	local t = math.min(hw / math.max(math.abs(dx), 1e-3), hh / math.max(math.abs(dy), 1e-3))
	north.Position = UDim2.new(0.5, dx * t, 0.5, dy * t)
end)
