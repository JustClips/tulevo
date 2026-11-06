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

-- floating panel placement (Dev 2026-11-06: camera-pinned looked "far asf"): it hangs in the
-- world beside the character's head, on the gun side, in the camera's (lagged) frame, so it
-- reads as an object next to you and swings a little when the camera turns
local FLOAT = {
	Right = 0.55, -- studs right of the crosshair line, measured at the head
	Up = -0.35, -- studs above the head (negative = lower, about gun height)
	Forward = 1.6, -- studs ahead of the head, toward the aim
	Height = 0.85, -- panel height in studs
	Yaw = 16, -- degrees turned about its left edge: the right end goes away from you
	Pitch = -8, -- degrees tipped back (top away)
	Roll = -2,
	Layers = 6, -- stacked copies that make the extrusion
	Thickness = 0.18, -- extrusion depth, as a share of the panel height
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
-- A stack of invisible local parts in front of the camera, each carrying the same SurfaceGui
-- drawn on top of the world. The front layer is lit; the ones behind it are darker and
-- step back in depth, so the icons and digits read as a solid extruded 3D object.
local ROW_H = CANVAS.Y / 2
local ICON = 34

type Layer = {
	part: Part,
	surface: SurfaceGui,
	magText: TextLabel,
	resText: TextLabel,
	bars: { Frame },
	disc: Frame,
	front: boolean,
}

local function shade(c: Color3, k: number): Color3
	return Color3.new(c.R * k, c.G * k, c.B * k)
end

local function makeLayer(index: number): Layer
	local front = index == 0
	local k = if front then 1 else 0.42 - 0.04 * index -- side walls of the extrusion
	local part = Instance.new("Part")
	part.Name = "AmmoFloat" .. index
	part.Anchored = true
	part.CanCollide = false
	part.CanQuery = false
	part.CanTouch = false
	part.CastShadow = false
	part.Transparency = 1
	part.Size = Vector3.new(2, 1, 0.01)

	local surface = Instance.new("SurfaceGui")
	surface.Name = part.Name
	surface.Adornee = part
	surface.Face = Enum.NormalId.Back -- the face looking back at the camera
	surface.AlwaysOnTop = true
	surface.ZOffset = -index -- front layer drawn last
	surface.LightInfluence = 0
	surface.SizingMode = Enum.SurfaceGuiSizingMode.FixedSize
	surface.CanvasSize = CANVAS
	surface.ResetOnSpawn = false
	surface.Enabled = false
	surface.Parent = gui.Parent

	local function row(y: number): (Frame, TextLabel)
		local icon = Instance.new("Frame")
		icon.BackgroundTransparency = 1
		icon.AnchorPoint = Vector2.new(0, 0.5)
		icon.Position = UDim2.fromOffset(4, y + ROW_H / 2)
		icon.Size = UDim2.fromOffset(ICON + 4, ICON)
		icon.Parent = surface

		local text = Instance.new("TextLabel")
		text.BackgroundTransparency = 1
		text.AnchorPoint = Vector2.new(0, 0.5)
		text.Position = UDim2.fromOffset(ICON + 22, y + ROW_H / 2)
		text.Size = UDim2.fromOffset(CANVAS.X - ICON - 26, ROW_H)
		text.TextXAlignment = Enum.TextXAlignment.Left
		text.FontFace = FLOAT_FONT
		text.TextSize = 50
		text.TextColor3 = shade(WHITE, k)
		text.TextStrokeTransparency = 1
		text.Parent = surface
		return icon, text
	end

	-- magazine icon: rounds standing side by side, like the reference
	local magIcon, magText = row(0)
	local bars = {}
	for i = 0, 3 do
		local b = Instance.new("Frame")
		b.BorderSizePixel = 0
		b.BackgroundColor3 = shade(ORANGE, k)
		b.Position = UDim2.fromOffset(i * 10, 4)
		b.Size = UDim2.fromOffset(7, ICON - 8)
		b.Parent = magIcon
		local tip = Instance.new("UICorner")
		tip.CornerRadius = UDim.new(0, 3)
		tip.Parent = b
		bars[i + 1] = b
	end

	-- round icon: an orange disc
	local resIcon, resText = row(ROW_H)
	local disc = Instance.new("Frame")
	disc.BorderSizePixel = 0
	disc.BackgroundColor3 = shade(ORANGE, k)
	disc.AnchorPoint = Vector2.new(0.5, 0.5)
	disc.Position = UDim2.fromScale(0.5, 0.5)
	disc.Size = UDim2.fromOffset(ICON - 4, ICON - 4)
	disc.Parent = resIcon
	local round = Instance.new("UICorner")
	round.CornerRadius = UDim.new(0.5, 0)
	round.Parent = disc

	return {
		part = part,
		surface = surface,
		magText = magText,
		resText = resText,
		bars = bars,
		disc = disc,
		front = front,
	}
end

local layers: { Layer } = {}
for i = 0, FLOAT.Layers - 1 do
	layers[i + 1] = makeLayer(i)
end

local lagRot: CFrame? = nil -- camera rotation the panel follows, trailing the real one
local alpha = 0 -- 0 hidden .. 1 shown
local shownUntil = 0
local lastMag = -1
local pop = 0 -- number punch when a shot is fired

local function placeLayers(cam: Camera, dt: number, head: BasePart)
	local rot = cam.CFrame.Rotation
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
	local lr = lagRot :: CFrame
	local look = lr.LookVector
	local flat = Vector3.new(look.X, 0, look.Z)
	flat = if flat.Magnitude > 0.01 then flat.Unit else Vector3.zAxis
	local right = flat:Cross(Vector3.yAxis)

	local h = FLOAT.Height
	local w = h * CANVAS.X / CANVAS.Y
	local step = FLOAT.Thickness * h / FLOAT.Layers
	-- sideways from the camera's line (the shoulder camera sits right of the head), so the
	-- panel stays just right of the crosshair whether or not the camera is over the shoulder
	local side = (head.Position - cam.CFrame.Position):Dot(right)
	local origin = head.Position + right * (FLOAT.Right - side) + Vector3.yAxis * FLOAT.Up + flat * FLOAT.Forward

	-- faces the camera (lagged), turned about its left edge so the far end recedes
	local hinge = CFrame.new(origin)
		* lr
		* CFrame.Angles(math.rad(FLOAT.Pitch), math.rad(FLOAT.Yaw), math.rad(FLOAT.Roll))
	for i, layer in layers do
		layer.part.Size = Vector3.new(w, h, 0.01)
		layer.part.CFrame = hinge * CFrame.new(w / 2, 0, -(i - 1) * step)
	end
end

local function hideFloat()
	for _, layer in layers do
		layer.surface.Enabled = false
		layer.part.Parent = nil
	end
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
	local cam = workspace.CurrentCamera
	local char = player.Character
	local head = char and char:FindFirstChild("Head") :: BasePart?
	if alpha <= 0 or not cam or not def or not head then
		hideFloat()
		lagRot = nil
		lastMag = -1
		return
	end

	placeLayers(cam, dt, head :: BasePart)

	if lastMag >= 0 and State.Mag < lastMag then
		pop = 1
	end
	lastMag = State.Mag
	pop = math.max(0, pop - dt * 8)
	local fade = 1 - alpha
	-- while reloading the magazine icon pulses
	local dim = if State.Reloading then 0.35 + 0.35 * math.sin(now * 12) else 0
	local magCol = magColor(def, State.Mag)
	for i, layer in layers do
		if layer.part.Parent ~= cam then
			layer.part.Parent = cam
		end
		layer.surface.Enabled = true
		layer.magText.Text = tostring(State.Mag)
		layer.magText.TextSize = 50 + 6 * pop
		layer.resText.Text = tostring(State.Reserve)
		layer.magText.TextTransparency = fade
		layer.resText.TextTransparency = fade
		layer.disc.BackgroundTransparency = fade
		if layer.front then
			layer.magText.TextColor3 = magCol
		else
			local k = 0.42 - 0.04 * (i - 1)
			layer.magText.TextColor3 = Color3.new(magCol.R * k, magCol.G * k, magCol.B * k)
		end
		for _, b in layer.bars do
			b.BackgroundTransparency = 1 - (1 - dim) * alpha
		end
	end
end)
