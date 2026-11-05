-- Full-screen map with GPS waypoint.
--
-- Open/close: M, gamepad Select (Back), or tap the radar. Esc or the X closes.
-- On the map: drag to move, mouse wheel / pinch / +- buttons to zoom,
-- click or tap to set a waypoint (purple route along the roads).
-- Click the waypoint again, or right-click / the CLEAR button, to remove it.
-- While the map is open the character doesn't move.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local UserInputService = game:GetService("UserInputService")
local ContextActionService = game:GetService("ContextActionService")
local GuiService = game:GetService("GuiService")

local MapData = require(script.Parent:WaitForChild("MapData"))
local Nav = require(script.Parent:WaitForChild("Nav"))

local player = Players.LocalPlayer

local HEIGHT = 3000 -- camera height; with a small FOV the map looks flat
local ZOOM_MIN, ZOOM_MAX = 40, 1500 -- studs from the screen centre to the top edge
local TAP_MOVE = 6 -- pixels a press can move and still count as a tap
local ARROW_IMAGE = "rbxassetid://112768085815375"
local FONT = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Bold)
local WHITE = Color3.fromRGB(240, 240, 240)

local gui = Instance.new("ScreenGui")
gui.Name = "FullMap"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 20
gui.Enabled = false
gui.Parent = player:WaitForChild("PlayerGui")

local vp = Instance.new("ViewportFrame")
vp.Name = "View"
vp.Size = UDim2.fromScale(1, 1)
vp.BackgroundColor3 = MapData.GROUND
vp.BorderSizePixel = 0
vp.Ambient = Color3.fromRGB(255, 255, 255)
vp.LightColor = Color3.fromRGB(60, 60, 60)
vp.LightDirection = Vector3.new(0, -1, 0)
vp.Active = true
vp.Parent = gui

local cam = Instance.new("Camera")
cam.Parent = vp
vp.CurrentCamera = cam

local world = Instance.new("WorldModel")
world.Parent = vp
local shapes = Instance.new("Folder")
shapes.Name = "Shapes"
shapes.Parent = world
local routeFolder = Instance.new("Folder")
routeFolder.Name = "Route"
routeFolder.Parent = world

-- Top bar
local top = Instance.new("Frame")
top.Name = "Top"
top.Size = UDim2.new(1, 0, 0, 48)
top.BackgroundColor3 = Color3.fromRGB(14, 14, 14)
top.BackgroundTransparency = 0.15
top.BorderSizePixel = 0
top.ZIndex = 5
top.Parent = gui

local title = Instance.new("TextLabel")
title.Position = UDim2.fromOffset(20, 0)
title.Size = UDim2.new(0, 200, 1, 0)
title.BackgroundTransparency = 1
title.FontFace = FONT
title.Text = "MAP"
title.TextSize = 24
title.TextColor3 = WHITE
title.TextXAlignment = Enum.TextXAlignment.Left
title.ZIndex = 6
title.Parent = top

local function button(name: string, text: string, x: number, w: number)
	local b = Instance.new("TextButton")
	b.Name = name
	b.AnchorPoint = Vector2.new(1, 0.5)
	b.Position = UDim2.new(1, x, 0.5, 0)
	b.Size = UDim2.fromOffset(w, 34)
	b.BackgroundColor3 = Color3.fromRGB(40, 40, 40)
	b.BorderSizePixel = 0
	b.AutoButtonColor = true
	b.FontFace = FONT
	b.Text = text
	b.TextSize = 18
	b.TextColor3 = WHITE
	b.ZIndex = 6
	b.Parent = top
	return b
end
local closeBtn = button("Close", "X", -12, 34)
local clearBtn = button("Clear", "CLEAR WAYPOINT", -56, 150)
local zoomIn = button("ZoomIn", "+", -216, 34)
local zoomOut = button("ZoomOut", "-", -256, 34)

local hint = Instance.new("TextLabel")
hint.AnchorPoint = Vector2.new(0.5, 1)
hint.Position = UDim2.new(0.5, 0, 1, -14)
hint.Size = UDim2.fromOffset(600, 22)
hint.BackgroundTransparency = 1
hint.FontFace = FONT
hint.TextSize = 16
hint.TextColor3 = WHITE
hint.TextStrokeTransparency = 0.4
hint.ZIndex = 5
hint.Parent = gui

-- Blips
local me = Instance.new("ImageLabel")
me.Name = "Player"
me.AnchorPoint = Vector2.new(0.5, 0.5)
me.Size = UDim2.fromOffset(18, 18)
me.BackgroundTransparency = 1
me.Image = ARROW_IMAGE
me.ZIndex = 4
me.Parent = vp

local wpBlip = Instance.new("Frame")
wpBlip.Name = "Waypoint"
wpBlip.AnchorPoint = Vector2.new(0.5, 0.5)
wpBlip.Size = UDim2.fromOffset(16, 16)
wpBlip.BackgroundColor3 = MapData.ROUTE
wpBlip.BorderSizePixel = 0
wpBlip.ZIndex = 4
wpBlip.Visible = false
wpBlip.Parent = vp
do
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(1, 0)
	c.Parent = wpBlip
	local s = Instance.new("UIStroke")
	s.Color = WHITE
	s.Thickness = 2
	s.Parent = wpBlip
end

-- Cursor crosshair (mouse only)
local crossH = Instance.new("Frame")
crossH.AnchorPoint = Vector2.new(0, 0.5)
crossH.Size = UDim2.new(1, 0, 0, 1)
crossH.BackgroundColor3 = WHITE
crossH.BackgroundTransparency = 0.6
crossH.BorderSizePixel = 0
crossH.ZIndex = 2
crossH.Parent = vp
local crossV = crossH:Clone()
crossV.AnchorPoint = Vector2.new(0.5, 0)
crossV.Size = UDim2.new(0, 1, 1, 0)
crossV.Parent = vp

-- View state ---------------------------------------------------------------
local center = Vector3.zero -- ground point at the screen centre
local zoom = 300 -- studs from centre to the top edge

local function applyCamera()
	zoom = math.clamp(zoom, ZOOM_MIN, ZOOM_MAX)
	cam.FieldOfView = math.deg(2 * math.atan(zoom / HEIGHT))
	cam.CFrame = CFrame.lookAt(center + Vector3.new(0, HEIGHT, 0), center, Vector3.new(0, 0, -1))
end

-- Screen pixel (inside the map) <-> ground point. North is up, east is right.
local function toWorld(px: Vector2): Vector3
	local size = vp.AbsoluteSize
	local aspect = size.X / math.max(size.Y, 1)
	local nx = px.X / size.X * 2 - 1
	local ny = px.Y / size.Y * 2 - 1
	return Vector3.new(center.X + nx * zoom * aspect, 0, center.Z + ny * zoom)
end

local function toScreen(p: Vector3): Vector2
	local size = vp.AbsoluteSize
	local aspect = size.X / math.max(size.Y, 1)
	local nx = (p.X - center.X) / (zoom * aspect)
	local ny = (p.Z - center.Z) / zoom
	return Vector2.new((nx + 1) / 2 * size.X, (ny + 1) / 2 * size.Y)
end

-- Input position -> pixel inside the map (the map ignores the top-bar inset).
local function localPos(input: InputObject): Vector2
	local inset = GuiService:GetGuiInset()
	return Vector2.new(input.Position.X, input.Position.Y) + inset - vp.AbsolutePosition
end

-- Drawing ----------------------------------------------------------------
local drawnZoom = 0
local function routeWidth(): number
	return math.max(4, zoom * 0.018)
end

local function redrawRoute()
	if Nav.waypoint and #Nav.route > 1 then
		drawnZoom = zoom
		MapData.drawPath(routeFolder, Nav.route, routeWidth())
	else
		routeFolder:ClearAllChildren()
	end
	wpBlip.Visible = Nav.waypoint ~= nil
	clearBtn.Visible = Nav.waypoint ~= nil
end

MapData.Changed:Connect(function()
	MapData.drawShapes(shapes)
end)
MapData.drawShapes(shapes)
Nav.Changed:Connect(function()
	if gui.Enabled then
		redrawRoute()
	end
end)

local function updateHint()
	local touch = UserInputService.TouchEnabled and not UserInputService.MouseEnabled
	if Nav.waypoint then
		hint.Text = if touch then "Tap the waypoint to remove it" else "Click the waypoint or right-click to remove it"
	else
		hint.Text = if touch then "Drag to move  ·  Pinch to zoom  ·  Tap to set a waypoint"
			else "Drag to move  ·  Scroll to zoom  ·  Click to set a waypoint"
	end
end
Nav.Changed:Connect(updateHint)

-- Open / close ----------------------------------------------------------------
local BLOCK = "FullMapBlockControls"
local function sink()
	return Enum.ContextActionResult.Sink
end

local function setOpen(on: boolean)
	if gui.Enabled == on then
		return
	end
	gui.Enabled = on
	if on then
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart")
		if root then
			center = Vector3.new(root.Position.X, 0, root.Position.Z)
		else
			center = MapData.bounds()
		end
		zoom = 300
		applyCamera()
		redrawRoute()
		updateHint()
		ContextActionService:BindActionAtPriority(
			BLOCK,
			sink,
			false,
			Enum.ContextActionPriority.High.Value + 100,
			Enum.KeyCode.W,
			Enum.KeyCode.A,
			Enum.KeyCode.S,
			Enum.KeyCode.D,
			Enum.KeyCode.Up,
			Enum.KeyCode.Down,
			Enum.KeyCode.Left,
			Enum.KeyCode.Right,
			Enum.KeyCode.Space,
			Enum.KeyCode.Thumbstick1,
			Enum.KeyCode.ButtonA,
			Enum.UserInputType.MouseWheel
		)
	else
		ContextActionService:UnbindAction(BLOCK)
	end
end

closeBtn.Activated:Connect(function()
	setOpen(false)
end)
clearBtn.Activated:Connect(function()
	Nav.clear()
end)
zoomIn.Activated:Connect(function()
	zoom /= 1.4
	applyCamera()
end)
zoomOut.Activated:Connect(function()
	zoom *= 1.4
	applyCamera()
end)

local radarGui = player.PlayerGui:WaitForChild("Minimap", 10)
if radarGui then
	radarGui:GetAttributeChangedSignal("OpenMapRequest"):Connect(function()
		setOpen(true)
	end)
end

UserInputService.InputBegan:Connect(function(input)
	if input.KeyCode == Enum.KeyCode.M and not UserInputService:GetFocusedTextBox() then
		setOpen(not gui.Enabled)
	elseif input.KeyCode == Enum.KeyCode.ButtonSelect then
		setOpen(not gui.Enabled)
	elseif gui.Enabled and (input.KeyCode == Enum.KeyCode.Escape or input.KeyCode == Enum.KeyCode.ButtonB) then
		setOpen(false)
	end
end)

-- Map input: drag, tap/click, zoom -----------------------------------------
local pressStart: Vector2? = nil
local pressCenter = Vector3.zero
local moved = false
local pressInput: InputObject? = nil

local function onTap(px: Vector2)
	local wp = Nav.waypoint
	if wp and (toScreen(wp) - px).Magnitude <= 14 then
		Nav.clear()
	else
		Nav.set(toWorld(px))
	end
end

vp.InputBegan:Connect(function(input)
	local t = input.UserInputType
	if t == Enum.UserInputType.MouseButton1 or t == Enum.UserInputType.Touch then
		if pressInput then
			return -- second finger: pinch handles it
		end
		pressInput = input
		pressStart = localPos(input)
		pressCenter = center
		moved = false
	elseif t == Enum.UserInputType.MouseButton2 then
		Nav.clear()
	end
end)

UserInputService.InputChanged:Connect(function(input)
	if not gui.Enabled then
		return
	end
	if input.UserInputType == Enum.UserInputType.MouseWheel then
		local px = localPos(input)
		local before = toWorld(px)
		zoom *= if input.Position.Z > 0 then 1 / 1.2 else 1.2
		zoom = math.clamp(zoom, ZOOM_MIN, ZOOM_MAX)
		-- keep the point under the cursor in place
		local after = toWorld(px)
		center += before - after
		applyCamera()
	elseif pressStart and (input == pressInput or input.UserInputType == Enum.UserInputType.MouseMovement) then
		local px = localPos(input)
		local delta = px - pressStart
		if delta.Magnitude > TAP_MOVE then
			moved = true
		end
		if moved then
			local size = vp.AbsoluteSize
			local studsPerPx = zoom * 2 / math.max(size.Y, 1)
			center = pressCenter - Vector3.new(delta.X, 0, delta.Y) * studsPerPx
			applyCamera()
		end
	end
	if input.UserInputType == Enum.UserInputType.MouseMovement then
		local px = localPos(input)
		crossH.Position = UDim2.fromOffset(0, px.Y)
		crossV.Position = UDim2.fromOffset(px.X, 0)
	end
end)

local function samePress(input: InputObject): boolean
	if not pressInput then
		return false
	end
	if pressInput.UserInputType == Enum.UserInputType.MouseButton1 then
		return input.UserInputType == Enum.UserInputType.MouseButton1
	end
	return input == pressInput
end

UserInputService.InputEnded:Connect(function(input)
	if not samePress(input) then
		return
	end
	if gui.Enabled and pressStart and not moved then
		onTap(localPos(input))
	end
	pressStart = nil
	pressInput = nil
end)

local pinchZoom = zoom
UserInputService.TouchPinch:Connect(function(_, scale, _, state)
	if not gui.Enabled then
		return
	end
	if state == Enum.UserInputState.Begin then
		pinchZoom = zoom
		pressStart = nil
		pressInput = nil
	end
	if scale > 0 then
		zoom = pinchZoom / scale
		applyCamera()
	end
end)

-- Per-frame blips ----------------------------------------------------------
RunService.RenderStepped:Connect(function()
	if not gui.Enabled then
		return
	end
	crossH.Visible = UserInputService.MouseEnabled
	crossV.Visible = UserInputService.MouseEnabled
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
	me.Visible = root ~= nil
	if root then
		local p = toScreen(root.Position)
		me.Position = UDim2.fromOffset(p.X, p.Y)
		local look = MapData.flat(root.CFrame.LookVector)
		me.Rotation = -math.deg(math.atan2(-look.X, -look.Z))
	end
	local wp = Nav.waypoint
	if wp then
		local p = toScreen(wp)
		wpBlip.Position = UDim2.fromOffset(p.X, p.Y)
	end
	-- Keep the route line readable at any zoom.
	if Nav.waypoint and math.abs(zoom - drawnZoom) / math.max(drawnZoom, 1) > 0.3 then
		redrawRoute()
	end
end)
