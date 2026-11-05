-- Radar in the bottom-left, right above the health bar.
--
-- Shows the tagged map (see MapData), tilted and turning with the camera
-- (forward = up). The player is a 2D arrow, an "N" marker on the edge points
-- north (-Z). With a GPS waypoint set (Nav), the purple route is drawn and the
-- waypoint marker sits on the radar edge when it's off screen.
-- Tap/click the radar to open the full map.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local MapData = require(script.Parent:WaitForChild("MapData"))
local Nav = require(script.Parent:WaitForChild("Nav"))

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
local AHEAD = 30 -- studs the view looks ahead of the player (player sits low)
local ROUTE_WIDTH = 7 -- studs

-- Arrow image (ForgeGUI, art/RadarArrow.png). Empty = a text arrow instead.
local ARROW_IMAGE = "rbxassetid://112768085815375"

local COLORS = {
	Frame = Color3.fromRGB(18, 18, 18),
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
vp.BackgroundColor3 = MapData.GROUND
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
local shapes = Instance.new("Folder")
shapes.Name = "Shapes"
shapes.Parent = world
local routeFolder = Instance.new("Folder")
routeFolder.Name = "Route"
routeFolder.Parent = world

-- Tap the radar to open the full map (FullMap listens for this attribute).
local open = Instance.new("TextButton")
open.Name = "OpenMap"
open.Size = UDim2.fromScale(1, 1)
open.BackgroundTransparency = 1
open.Text = ""
open.ZIndex = 10
open.Parent = frame
open.Activated:Connect(function()
	gui:SetAttribute("OpenMapRequest", (gui:GetAttribute("OpenMapRequest") or 0) + 1)
end)

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
	txt.TextSize = 12
	txt.TextColor3 = COLORS.Arrow
	txt.TextStrokeTransparency = 0.2
	txt.BackgroundTransparency = 1
	txt.Size = UDim2.fromOffset(13, 13)
	arrow = txt
end
arrow.Name = "Arrow"
arrow.AnchorPoint = Vector2.new(0.5, 0.5)
arrow.ZIndex = 4
arrow.Parent = vp

local function marker(name: string, color: Color3, label: string?, size: number)
	local m = Instance.new("Frame")
	m.Name = name
	m.AnchorPoint = Vector2.new(0.5, 0.5)
	m.Size = UDim2.fromOffset(size, size)
	m.BackgroundColor3 = color
	m.BorderSizePixel = 0
	m.ZIndex = 3
	m.Parent = vp
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(1, 0)
	c.Parent = m
	if label then
		local t = Instance.new("TextLabel")
		t.Size = UDim2.fromScale(1, 1)
		t.BackgroundTransparency = 1
		t.FontFace = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Bold)
		t.Text = label
		t.TextSize = 12
		t.TextColor3 = COLORS.Arrow
		t.ZIndex = 4
		t.Parent = m
	else
		local s = Instance.new("UIStroke")
		s.Color = Color3.fromRGB(240, 240, 240)
		s.Thickness = 1.5
		s.Parent = m
	end
	return m
end

local north = marker("North", COLORS.North, "N", 16)
local waypoint = Instance.new("ImageLabel")
waypoint.Name = "Waypoint"
waypoint.AnchorPoint = Vector2.new(0.5, 0.9)
waypoint.Size = UDim2.fromOffset(16, 16)
waypoint.BackgroundTransparency = 1
waypoint.Image = "rbxassetid://82585376348119" -- ForgeGUI pin, art/WaypointPin.png
waypoint.ZIndex = 3
waypoint.Visible = false
waypoint.Parent = vp

-- Map + route drawing -----------------------------------------------------
local function redrawShapes()
	MapData.drawShapes(shapes, { RoadEdge = Color3.fromRGB(24, 25, 25) })
end
MapData.Changed:Connect(redrawShapes)
redrawShapes()

local function redrawRoute()
	if Nav.waypoint and #Nav.route > 1 then
		MapData.drawPath(routeFolder, Nav.route, ROUTE_WIDTH)
	else
		routeFolder:ClearAllChildren()
	end
	waypoint.Visible = Nav.waypoint ~= nil
end
Nav.Changed:Connect(redrawRoute)
redrawRoute()

-- Per-frame update ----------------------------------------------------------
local function yaw(v: Vector3): number
	return math.atan2(-v.X, -v.Z)
end

local tanHalf = math.tan(math.rad(FOV) / 2)
local EDGE = 9

-- Pixel position of a ground point on the radar.
local function project(p: Vector3, size: Vector2): Vector2
	local aspect = if size.Y > 0 then size.X / size.Y else 1
	local rel = vpCam.CFrame:PointToObjectSpace(p)
	local depth = math.max(-rel.Z, 1)
	local nx = rel.X / depth / (tanHalf * aspect)
	local ny = rel.Y / depth / tanHalf
	return Vector2.new((0.5 + nx / 2) * size.X, (0.5 - ny / 2) * size.Y)
end

-- Moves a point that's off the radar onto its edge, along the line from `from`.
local function toEdge(from: Vector2, p: Vector2, size: Vector2): Vector2
	if p.X >= EDGE and p.X <= size.X - EDGE and p.Y >= EDGE and p.Y <= size.Y - EDGE then
		return p
	end
	local d = p - from
	local tx = if d.X > 0 then (size.X - EDGE - from.X) / d.X elseif d.X < 0 then (EDGE - from.X) / d.X else math.huge
	local ty = if d.Y > 0 then (size.Y - EDGE - from.Y) / d.Y elseif d.Y < 0 then (EDGE - from.Y) / d.Y else math.huge
	local t = math.clamp(math.min(tx, ty), 0, 1)
	return from + d * t
end

RunService.RenderStepped:Connect(function()
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local forward = MapData.flat(camera.CFrame.LookVector)
	local pos = if root then root.Position else camera.Focus.Position
	pos = Vector3.new(pos.X, 0, pos.Z)

	local target = pos + forward * AHEAD
	local viewDir = forward * math.sin(TILT) - Vector3.yAxis * math.cos(TILT)
	vpCam.CFrame = CFrame.lookAt(target - viewDir * DIST, target, forward)

	local size = vp.AbsoluteSize
	local me = project(pos, size)
	arrow.Position = UDim2.fromOffset(me.X, me.Y)

	local camYaw = yaw(forward)
	arrow.Visible = root ~= nil
	if root then
		arrow.Rotation = -math.deg(yaw(MapData.flat(root.CFrame.LookVector)) - camYaw)
	end

	-- North on the edge, in the direction of north from the player.
	local far = me + Vector2.new(math.sin(camYaw), -math.cos(camYaw)) * 10000
	local n = toEdge(me, far, size)
	north.Position = UDim2.fromOffset(n.X, n.Y)

	local wp = Nav.waypoint
	if wp then
		local w = toEdge(me, project(wp, size), size)
		waypoint.Position = UDim2.fromOffset(w.X, w.Y)
	end
end)
