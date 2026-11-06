-- Ammo counters. Reads Client.Weapons.State.
--
-- Floating counter (Dev 2026-11-06, GTA RP reference): while the gun is up (aiming, hip-fire,
-- reloading) a small panel floats in the world to the right of the aim point: an orange
-- magazine icon + bullets in the mag, and an orange round icon + spare bullets. It hangs in
-- front of the camera and trails camera turns with a soft lag, so it swings a little when you
-- flick the view and settles back.
--
-- Top-right counter: the plain GTA-style one, shown while a gun is in hand but not up.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local Weapons = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Weapons"))
local State = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local FONT = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Bold)
local FLOAT_FONT = Font.new("rbxasset://fonts/families/GothamSSm.json", Enum.FontWeight.Bold)

local WHITE = Color3.fromRGB(240, 240, 235)
local ORANGE = Color3.fromRGB(245, 128, 36)
local LOW = Color3.fromRGB(240, 190, 80)
local EMPTY = Color3.fromRGB(230, 70, 60)

-- floating panel placement, in camera space as a share of the view's half-height at the
-- panel's depth (so it keeps the same spot and size on screen when the aim zoom changes FOV)
local FLOAT = {
	Depth = 7, -- studs in front of the camera at FOV 70
	Right = 0.2, -- left edge of the panel, right of the crosshair
	Down = 0.1, -- panel centre, below the crosshair
	Height = 0.2, -- panel height
	Yaw = 10, -- degrees the panel is turned toward the view centre (reads as 3D)
	Follow = 11, -- how fast it catches up with camera turns (higher = less lag)
	MaxLag = 14, -- degrees it may trail behind at most
	Linger = 0.8, -- seconds it stays after the gun goes down
	Fade = 0.15, -- seconds to fade in / out
}
local CANVAS = Vector2.new(300, 150) -- SurfaceGui pixels (width x height), 2 rows

local function magColor(def, mag: number): Color3
	if mag == 0 then
		return EMPTY
	elseif mag <= math.ceil((def.MagSize or 30) * 0.2) then
		return LOW
	end
	return WHITE
end

local gui = Instance.new("ScreenGui")
gui.Name = "AmmoHud"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = player:WaitForChild("PlayerGui")

-- top right ------------------------------------------------------------------------------
local root = Instance.new("Frame")
root.AnchorPoint = Vector2.new(1, 0)
root.Position = UDim2.new(1, -24, 0, 64)
root.Size = UDim2.fromOffset(220, 48)
root.BackgroundTransparency = 1
root.Visible = false
root.Parent = gui

local list = Instance.new("UIListLayout")
list.FillDirection = Enum.FillDirection.Horizontal
list.HorizontalAlignment = Enum.HorizontalAlignment.Right
list.VerticalAlignment = Enum.VerticalAlignment.Bottom
list.Padding = UDim.new(0, 8)
list.SortOrder = Enum.SortOrder.LayoutOrder
list.Parent = root

local function label(order: number, size: number): TextLabel
	local t = Instance.new("TextLabel")
	t.LayoutOrder = order
	t.AutomaticSize = Enum.AutomaticSize.X
	t.Size = UDim2.fromOffset(0, size)
	t.BackgroundTransparency = 1
	t.FontFace = FONT
	t.TextSize = size
	t.TextColor3 = WHITE
	t.TextStrokeTransparency = 0.4
	t.Parent = root
	return t
end
local reserve = label(1, 22)
local mag = label(2, 40)

-- floating panel ---------------------------------------------------------------------------
-- an invisible local part in front of the camera carries a SurfaceGui drawn on top of the world
local board = Instance.new("Part")
board.Name = "AmmoFloat"
board.Anchored = true
board.CanCollide = false
board.CanQuery = false
board.CanTouch = false
board.CastShadow = false
board.Transparency = 1
board.Size = Vector3.new(2, 1, 0.05)

local surface = Instance.new("SurfaceGui")
surface.Name = "AmmoFloat"
surface.Adornee = board
surface.Face = Enum.NormalId.Back -- the face looking back at the camera
surface.AlwaysOnTop = true
surface.LightInfluence = 0
surface.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
surface.CanvasSize = CANVAS
surface.ResetOnSpawn = false
surface.Enabled = false
surface.Parent = gui.Parent

local panel = Instance.new("Frame")
panel.Size = UDim2.fromScale(1, 1)
panel.BackgroundTransparency = 1
panel.Parent = surface

local ROW_H = CANVAS.Y / 2
local ICON = 34
local function row(y: number): (Frame, TextLabel)
	local icon = Instance.new("Frame")
	icon.BackgroundTransparency = 1
	icon.AnchorPoint = Vector2.new(0, 0.5)
	icon.Position = UDim2.fromOffset(4, y + ROW_H / 2)
	icon.Size = UDim2.fromOffset(ICON + 4, ICON)
	icon.Parent = panel

	local text = Instance.new("TextLabel")
	text.BackgroundTransparency = 1
	text.AnchorPoint = Vector2.new(0, 0.5)
	text.Position = UDim2.fromOffset(ICON + 22, y + ROW_H / 2)
	text.Size = UDim2.fromOffset(CANVAS.X - ICON - 26, ROW_H)
	text.TextXAlignment = Enum.TextXAlignment.Left
	text.FontFace = FLOAT_FONT
	text.TextSize = 50
	text.TextColor3 = WHITE
	text.TextStrokeColor3 = Color3.new(0, 0, 0)
	text.TextStrokeTransparency = 0.75
	text.Parent = panel
	return icon, text
end

-- magazine icon: rounds standing side by side, like the reference
local magIcon, magText = row(0)
local magBars = {}
for i = 0, 3 do
	local b = Instance.new("Frame")
	b.BorderSizePixel = 0
	b.BackgroundColor3 = ORANGE
	b.Position = UDim2.fromOffset(i * 10, 4)
	b.Size = UDim2.fromOffset(7, ICON - 8)
	b.Parent = magIcon
	local tip = Instance.new("UICorner")
	tip.CornerRadius = UDim.new(0, 3)
	tip.Parent = b
	magBars[i + 1] = b
end

-- round icon: an orange disc
local resIcon, resText = row(ROW_H)
local disc = Instance.new("Frame")
disc.BorderSizePixel = 0
disc.BackgroundColor3 = ORANGE
disc.AnchorPoint = Vector2.new(0.5, 0.5)
disc.Position = UDim2.fromScale(0.5, 0.5)
disc.Size = UDim2.fromOffset(ICON - 4, ICON - 4)
disc.Parent = resIcon
local round = Instance.new("UICorner")
round.CornerRadius = UDim.new(0.5, 0)
round.Parent = disc

local lagRot: CFrame? = nil -- camera rotation the panel follows, trailing the real one
local alpha = 0 -- 0 hidden .. 1 shown
local shownUntil = 0
local lastMag = -1
local pop = 0 -- number punch when a shot is fired

local function placeBoard(cam: Camera, dt: number)
	local camCf = cam.CFrame
	local rot = camCf.Rotation
	if not lagRot then
		lagRot = rot
	else
		local k = 1 - math.exp(-FLOAT.Follow * dt)
		local nextRot = (lagRot :: CFrame):Lerp(rot, k)
		-- never fall too far behind on a big flick
		local _, ang = (rot:Inverse() * nextRot):ToAxisAngle()
		local max = math.rad(FLOAT.MaxLag)
		if ang > max then
			nextRot = rot:Lerp(nextRot, max / ang)
		end
		lagRot = nextRot
	end

	-- same on-screen size and spot whatever the FOV (the aim zoom changes it)
	local tanHalf = math.tan(math.rad(cam.FieldOfView / 2))
	local depth = FLOAT.Depth * math.tan(math.rad(35)) / tanHalf
	local unit = depth * tanHalf -- studs per "half view height" at that depth
	local h = FLOAT.Height * unit
	local w = h * CANVAS.X / CANVAS.Y
	board.Size = Vector3.new(w, h, 0.05)

	local centre = Vector3.new(FLOAT.Right * unit + w / 2, -FLOAT.Down * unit, -depth)
	board.CFrame = CFrame.new(camCf.Position)
		* (lagRot :: CFrame)
		* CFrame.new(centre)
		* CFrame.Angles(0, math.rad(FLOAT.Yaw), 0)
end

RunService:BindToRenderStep("AmmoHud", Enum.RenderPriority.Last.Value + 2, function(dt)
	local def = State.Equipped and Weapons.get(State.Equipped)
	local isGun = def ~= nil and def.Class.Kind == "Gun" and not State.InVehicle
	local now = os.clock()
	local up = isGun and (State.Raised or State.Aiming or State.Reloading)
	if up then
		shownUntil = now + FLOAT.Linger
	end
	local floating = isGun and now < shownUntil

	root.Visible = isGun and alpha < 0.5 and not floating
	if root.Visible then
		reserve.Text = tostring(State.Reserve)
		mag.Text = tostring(State.Mag)
		mag.TextColor3 = magColor(def, State.Mag)
	end

	local target = if floating then 1 else 0
	alpha = math.clamp(alpha + (if target > alpha then 1 else -1) * dt / FLOAT.Fade, 0, 1)
	if alpha <= 0 then
		surface.Enabled = false
		board.Parent = nil
		lagRot = nil
		lastMag = -1
		return
	end

	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	if board.Parent ~= cam then
		board.Parent = cam
	end
	surface.Enabled = true
	local fade = 1 - alpha
	magText.TextTransparency = fade
	resText.TextTransparency = fade
	magText.TextStrokeTransparency = 0.75 + 0.25 * fade
	resText.TextStrokeTransparency = 0.75 + 0.25 * fade
	disc.BackgroundTransparency = fade
	placeBoard(cam, dt)

	if def then
		if lastMag >= 0 and State.Mag < lastMag then
			pop = 1
		end
		lastMag = State.Mag
		pop = math.max(0, pop - dt * 8)
		magText.Text = tostring(State.Mag)
		magText.TextSize = 50 + 6 * pop
		magText.TextColor3 = magColor(def, State.Mag)
		resText.Text = tostring(State.Reserve)
		-- while reloading the magazine icon pulses
		local dim = if State.Reloading then 0.35 + 0.35 * math.sin(now * 12) else 0
		for _, b in magBars do
			b.BackgroundTransparency = 1 - (1 - dim) * alpha
		end
	end
end)
