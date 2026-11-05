-- Full-screen map with GPS waypoint. No buttons: a controls strip in the
-- bottom-right and a scale bar in the bottom-left.
--
-- Open/close: M, gamepad Select (Back), or tap the radar. Esc / B also close;
-- on touch, tap the controls strip to close.
-- Mouse: drag to move, scroll to zoom, click to set a waypoint, click the
-- waypoint to remove it. Touch: drag, pinch, tap. Gamepad: left stick moves,
-- LT/RT zoom, A sets/removes the waypoint at the centre cursor.
-- Setting a new waypoint replaces the old one. It also clears on arrival.
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

-- Map colors: lighter than the radar, white roads on grey ground.
local MAP_GROUND = Color3.fromRGB(96, 98, 98)
local MAP_COLORS = {
	Road = Color3.fromRGB(226, 226, 226),
	Building = Color3.fromRGB(76, 78, 78),
	Park = Color3.fromRGB(84, 98, 82),
	Water = Color3.fromRGB(78, 98, 128),
}
vp.BackgroundColor3 = MAP_GROUND

-- Controls strip, bottom-right (text only, no buttons).
local strip = Instance.new("TextLabel")
strip.Name = "Controls"
strip.AnchorPoint = Vector2.new(1, 1)
strip.Position = UDim2.new(1, -12, 1, -10)
strip.Size = UDim2.fromOffset(10, 22)
strip.AutomaticSize = Enum.AutomaticSize.X
strip.BackgroundColor3 = Color3.fromRGB(12, 12, 12)
strip.BackgroundTransparency = 0.35
strip.BorderSizePixel = 0
strip.FontFace = FONT
strip.TextSize = 13
strip.TextColor3 = WHITE
strip.ZIndex = 5
strip.Parent = gui
do
	local pad = Instance.new("UIPadding")
	pad.PaddingLeft = UDim.new(0, 10)
	pad.PaddingRight = UDim.new(0, 10)
	pad.Parent = strip
end

-- Scale bar, bottom-left.
local scale = Instance.new("Frame")
scale.Name = "Scale"
scale.AnchorPoint = Vector2.new(0, 1)
scale.Position = UDim2.new(0, 16, 1, -14)
scale.Size = UDim2.fromOffset(80, 2)
scale.BackgroundColor3 = WHITE
scale.BorderSizePixel = 0
scale.ZIndex = 5
scale.Parent = gui
local scaleText = Instance.new("TextLabel")
scaleText.AnchorPoint = Vector2.new(0, 1)
scaleText.Position = UDim2.new(0, 0, 0, -3)
scaleText.Size = UDim2.fromOffset(120, 16)
scaleText.BackgroundTransparency = 1
scaleText.FontFace = FONT
scaleText.TextSize = 13
scaleText.TextColor3 = WHITE
scaleText.TextStrokeTransparency = 0.5
scaleText.TextXAlignment = Enum.TextXAlignment.Left
scaleText.ZIndex = 5
scaleText.Parent = scale

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
end

MapData.Changed:Connect(function()
	MapData.drawShapes(shapes, MAP_COLORS)
end)
MapData.drawShapes(shapes, MAP_COLORS)
Nav.Changed:Connect(function()
	if gui.Enabled then
		redrawRoute()
	end
end)

local function isTouch(): boolean
	return UserInputService.TouchEnabled and not UserInputService.MouseEnabled
end

local function updateHint()
	local wp = if Nav.waypoint then "Remove Waypoint" else "Set Waypoint"
	if UserInputService.GamepadEnabled and not UserInputService.MouseEnabled then
		strip.Text = `Zoom  LT / RT     Move  L-Stick     {wp}  A     Close  B`
	elseif isTouch() then
		strip.Text = `Zoom  Pinch     Move  Drag     {wp}  Tap     Close  Tap here`
	else
		strip.Text = `Zoom  Scroll     Move  Drag     {wp}  Click     Close  M`
	end
end
Nav.Changed:Connect(updateHint)

local onTapCenter: () -> ()

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

-- Touch has no keys: tapping the controls strip closes the map.
strip.Active = true
strip.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.Touch then
		setOpen(false)
	end
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
	elseif gui.Enabled and (input.KeyCode == Enum.KeyCode.ButtonA or input.KeyCode == Enum.KeyCode.Return) then
		-- Gamepad/keyboard: waypoint at the centre cursor.
		onTapCenter()
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

onTapCenter = function()
	onTap(vp.AbsoluteSize / 2)
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
local NICE = { 10, 20, 50, 100, 200, 500, 1000, 2000 }
local function updateScale()
	local studsPerPx = zoom * 2 / math.max(vp.AbsoluteSize.Y, 1)
	local pick = NICE[1]
	for _, n in NICE do
		if n / studsPerPx <= 110 then
			pick = n
		end
	end
	scale.Size = UDim2.fromOffset(math.floor(pick / studsPerPx), 2)
	scaleText.Text = `{pick} studs`
end

local function gamepadInput(dt: number)
	local stick, lt, rt = Vector3.zero, 0, 0
	for _, s in UserInputService:GetGamepadState(Enum.UserInputType.Gamepad1) do
		if s.KeyCode == Enum.KeyCode.Thumbstick1 then
			stick = s.Position
		elseif s.KeyCode == Enum.KeyCode.ButtonL2 then
			lt = s.Position.Z
		elseif s.KeyCode == Enum.KeyCode.ButtonR2 then
			rt = s.Position.Z
		end
	end
	if stick.Magnitude > 0.15 then
		center += Vector3.new(stick.X, 0, -stick.Y) * zoom * 1.2 * dt
	end
	if lt > 0.1 or rt > 0.1 then
		zoom *= (1 + 1.5 * dt) ^ (lt - rt)
	end
	applyCamera()
end

RunService.RenderStepped:Connect(function(dt)
	if not gui.Enabled then
		return
	end
	local gamepad = UserInputService.GamepadEnabled and not UserInputService.MouseEnabled
	if gamepad then
		gamepadInput(dt)
		local c = vp.AbsoluteSize / 2
		crossH.Position = UDim2.fromOffset(0, c.Y)
		crossV.Position = UDim2.fromOffset(c.X, 0)
	end
	crossH.Visible = UserInputService.MouseEnabled or gamepad
	crossV.Visible = crossH.Visible
	updateScale()
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
