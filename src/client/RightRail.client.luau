-- Right-side button rail, in the Sweep the World HUD style (Dev, 2026-11-10): square toy
-- buttons with a colour fill, stud texture, thick dark outline, a lighter top, a big
-- colour icon and a Montserrat label inside the tile. No rounded corners (the red badge is
-- the one round thing, on purpose).
--
--   Store  (F4)   opens the Store window (below)
--   Bag    (N)    toggles the inventory      (Inventory gui attribute "ToggleRequest")
--   Phone  (Up)   toggles the phone          (Client.Phone.toggle)
--   Map    (M)    opens the full map         (Minimap gui attribute "OpenMapRequest")
--
-- Desktop/console: one column, centred on the right edge. Phones: a 2 x 2 block at the top
-- right, under the game name strip, so the jump / sprint / car buttons stay free.
-- Badge: set the tile's "Badge" attribute to a number (0 hides it), e.g.
--   PlayerGui.RightRail.Rail.Store:SetAttribute("Badge", 3)
-- Icons: art/rail_icons (ForgeGUI, gen.py + proc.py) -> tools/upload_icons.py --set rail.
-- Store contents: fill PlayerGui.Store.Window.Body.
local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local RailIcons = require(Shared:WaitForChild("RailIconIds"))
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))
local MouseLook = require(script.Parent:WaitForChild("Movement"):WaitForChild("MouseLook"))

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui")

-- Sweep the World tokens (JustClips/Dev tools/gen_ui.py)
local INK = Color3.fromHex("#17191E")
local WHITE = Color3.new(1, 1, 1)
local SURFACE = Color3.fromHex("#F7F8FA")
local HEADER = Color3.fromHex("#2F9BFF")
local DANGER = Color3.fromHex("#FF4D5E")
local SUB = Color3.fromHex("#5B6070")
local BADGE_RED = Color3.fromHex("#D61634")
local STROKE = 4
local STUD_ALPHA = 0.45
local MONTSERRAT = "rbxasset://fonts/families/Montserrat.json"
local DISPLAY = Font.new(MONTSERRAT, Enum.FontWeight.Heavy)
local BODY = Font.new(MONTSERRAT, Enum.FontWeight.Bold)

local R = HudLayout.Rail
local TILE, GAP = R.Tile, R.Gap

local function stroke(parent: Instance, thickness: number, color: Color3?, mode: Enum.ApplyStrokeMode?)
	local s = Instance.new("UIStroke")
	s.Color = color or INK
	s.Thickness = thickness
	s.ApplyStrokeMode = mode or Enum.ApplyStrokeMode.Border
	s.LineJoinMode = Enum.LineJoinMode.Miter
	s.Parent = parent
	return s
end

local function label(parent: Instance, text: string, size: number, font: Font?): TextLabel
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.FontFace = font or DISPLAY
	t.TextSize = size
	t.TextColor3 = WHITE
	t.Text = text
	t.ZIndex = 3
	local s = stroke(t, 2.5, INK, Enum.ApplyStrokeMode.Contextual)
	s.LineJoinMode = Enum.LineJoinMode.Round
	t.Parent = parent
	return t
end

-- The raised toy look shared by tiles and buttons: fill, outline, lighter top, studs, bevel.
local function toy(b: GuiObject, color: Color3)
	b.BackgroundColor3 = color
	b.BorderSizePixel = 0
	stroke(b, STROKE)
	local shine = Instance.new("UIGradient")
	shine.Rotation = 90
	shine.Color = ColorSequence.new({
		ColorSequenceKeypoint.new(0, WHITE),
		ColorSequenceKeypoint.new(0.55, WHITE),
		ColorSequenceKeypoint.new(1, Color3.fromHex("#BCC4D4")),
	})
	shine.Parent = b
	local studs = Instance.new("ImageLabel")
	studs.Name = "Studs"
	studs.Size = UDim2.fromScale(1, 1)
	studs.BackgroundTransparency = 1
	studs.Image = RailIcons.Stud
	studs.ScaleType = Enum.ScaleType.Tile
	studs.TileSize = UDim2.fromOffset(48, 48)
	studs.ImageColor3 = color
	studs.ImageTransparency = STUD_ALPHA
	studs.ZIndex = 0
	studs.Parent = b
	local bevel = Instance.new("Frame")
	bevel.Name = "Bevel"
	bevel.AnchorPoint = Vector2.new(0.5, 0.5)
	bevel.Position = UDim2.fromScale(0.5, 0.5)
	bevel.Size = UDim2.new(1, -6, 1, -6)
	bevel.BackgroundTransparency = 1
	bevel.ZIndex = 0
	bevel.Parent = b
	local bs = stroke(bevel, 2, WHITE)
	bs.Transparency = 0.55
end

-- Round red count badge on the tile's top-right corner (Sweep's badge look).
local function badge(tile: GuiObject)
	local holder = Instance.new("Frame")
	holder.Name = "Badge"
	holder.AnchorPoint = Vector2.new(0.5, 0.5)
	holder.Position = UDim2.new(1, -4, 0, 4)
	holder.Size = UDim2.fromOffset(30, 30)
	holder.BackgroundTransparency = 1
	holder.Visible = false
	holder.ZIndex = 6
	holder.Parent = tile
	local disc = Instance.new("Frame")
	disc.Name = "Disc"
	disc.Size = UDim2.fromScale(1, 1)
	disc.BackgroundColor3 = BADGE_RED
	disc.ZIndex = 6
	disc.Parent = holder
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0.5, 0)
	corner.Parent = disc
	local rim = stroke(disc, 3, WHITE)
	rim.LineJoinMode = Enum.LineJoinMode.Round
	local num = label(holder, "", 20)
	num.Size = UDim2.fromScale(1, 1)
	num.ZIndex = 7
	local function update()
		local n = tonumber(tile:GetAttribute("Badge")) or 0
		holder.Visible = n > 0
		num.Text = if n > 99 then "99+" else tostring(n)
		holder.Size = UDim2.fromOffset(if n > 9 then 40 else 30, 30)
	end
	tile:GetAttributeChangedSignal("Badge"):Connect(update)
	update()
end

---------------------------------------------------------------- rail

local gui = Instance.new("ScreenGui")
gui.Name = "RightRail"
gui.ResetOnSpawn = false
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.DisplayOrder = 5
gui.Parent = playerGui

local rail = Instance.new("Frame")
rail.Name = "Rail"
rail.BackgroundTransparency = 1
rail.Parent = gui

local railScale = Instance.new("UIScale")
railScale.Parent = rail

local grid = Instance.new("UIGridLayout")
grid.CellSize = UDim2.fromOffset(TILE, TILE)
grid.CellPadding = UDim2.fromOffset(GAP, GAP)
grid.FillDirection = Enum.FillDirection.Horizontal
grid.HorizontalAlignment = Enum.HorizontalAlignment.Right
grid.SortOrder = Enum.SortOrder.LayoutOrder
grid.Parent = rail

local keyHints: { TextLabel } = {}
local tiles: { GuiObject } = {}

local function tile(order: number, name: string, text: string, icon: string, color: Color3, key: string?, onClick: () -> ())
	local b = Instance.new("TextButton")
	b.Name = name
	b.LayoutOrder = order
	b.Text = ""
	b.AutoButtonColor = false
	b.ZIndex = 1
	b.Parent = rail
	toy(b, color)

	local pop = Instance.new("UIScale")
	pop.Name = "Pop"
	pop.Parent = b

	local img = Instance.new("ImageLabel")
	img.Name = "Icon"
	img.AnchorPoint = Vector2.new(0.5, 0.5)
	img.Position = UDim2.fromOffset(TILE / 2, 33)
	img.Size = UDim2.fromOffset(58, 58)
	img.BackgroundTransparency = 1
	img.Image = icon
	img.ScaleType = Enum.ScaleType.Fit
	img.ZIndex = 2
	img.Parent = b

	local l = label(b, text, 15)
	l.Name = "Label"
	l.AnchorPoint = Vector2.new(0.5, 1)
	l.Position = UDim2.new(0.5, 0, 1, -5)
	l.Size = UDim2.new(1, -4, 0, 20)
	l.TextYAlignment = Enum.TextYAlignment.Bottom

	if key then
		local k = label(b, key, 12)
		k.Name = "Key"
		k.Position = UDim2.fromOffset(6, 4)
		k.Size = UDim2.fromOffset(30, 14)
		k.TextXAlignment = Enum.TextXAlignment.Left
		k.TextYAlignment = Enum.TextYAlignment.Top
		k.ZIndex = 4
		table.insert(keyHints, k)
	end

	badge(b)

	local function bounce(to: number)
		TweenService:Create(pop, TweenInfo.new(0.12, Enum.EasingStyle.Quad), { Scale = to }):Play()
	end
	b.MouseEnter:Connect(function()
		bounce(1.06)
	end)
	b.MouseLeave:Connect(function()
		bounce(1)
	end)
	b.MouseButton1Down:Connect(function()
		bounce(0.92)
	end)
	b.MouseButton1Up:Connect(function()
		bounce(1)
	end)
	b.Activated:Connect(onClick)
	table.insert(tiles, b)
	return b
end

---------------------------------------------------------------- store window (Sweep window look)

local storeGui = Instance.new("ScreenGui")
storeGui.Name = "Store"
storeGui.ResetOnSpawn = false
storeGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
storeGui.DisplayOrder = 20
storeGui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
storeGui.Enabled = false
storeGui.Parent = playerGui

local WIN_W, WIN_H = 640, 420

local window = Instance.new("Frame")
window.Name = "Window"
window.AnchorPoint = Vector2.new(0.5, 0.5)
window.Position = UDim2.fromScale(0.5, 0.5)
window.Size = UDim2.fromOffset(WIN_W, WIN_H)
window.BackgroundColor3 = SURFACE
window.BorderSizePixel = 0
window.Active = true
window.Parent = storeGui
stroke(window, STROKE)
do
	local shade = Instance.new("UIGradient")
	shade.Rotation = 90
	shade.Color = ColorSequence.new(WHITE, Color3.fromHex("#DCE0E7"))
	shade.Parent = window
end

local windowScale = Instance.new("UIScale")
windowScale.Parent = window

local header = Instance.new("Frame")
header.Name = "Header"
header.Size = UDim2.new(1, 0, 0, 64)
header.ZIndex = 2
header.Parent = window
toy(header, HEADER)

local headerIcon = Instance.new("ImageLabel")
headerIcon.AnchorPoint = Vector2.new(0, 0.5)
headerIcon.Position = UDim2.new(0, 10, 0.5, 0)
headerIcon.Size = UDim2.fromOffset(48, 48)
headerIcon.BackgroundTransparency = 1
headerIcon.Image = RailIcons.Store
headerIcon.ScaleType = Enum.ScaleType.Fit
headerIcon.ZIndex = 3
headerIcon.Parent = header

local title = label(header, "Store", 30)
title.Position = UDim2.fromOffset(68, 0)
title.Size = UDim2.new(1, -150, 1, 0)
title.TextXAlignment = Enum.TextXAlignment.Left

local closeBtn = Instance.new("TextButton")
closeBtn.Name = "Close"
closeBtn.AnchorPoint = Vector2.new(0.5, 0.5)
closeBtn.Position = UDim2.new(1, -6, 0, 6)
closeBtn.Size = UDim2.fromOffset(52, 52)
closeBtn.Text = ""
closeBtn.AutoButtonColor = false
closeBtn.ZIndex = 5
closeBtn.Parent = window
toy(closeBtn, DANGER)
do
	local x = label(closeBtn, "X", 30)
	x.Size = UDim2.fromScale(1, 1)
	x.ZIndex = 6
end

-- Store contents go here (nothing is for sale yet).
local body = Instance.new("Frame")
body.Name = "Body"
body.Position = UDim2.fromOffset(0, 64)
body.Size = UDim2.new(1, 0, 1, -64)
body.BackgroundTransparency = 1
body.ZIndex = 2
body.Parent = window

local empty = Instance.new("TextLabel")
empty.Name = "Empty"
empty.Size = UDim2.fromScale(1, 1)
empty.BackgroundTransparency = 1
empty.FontFace = BODY
empty.TextSize = 20
empty.TextColor3 = SUB
empty.Text = "Nothing for sale yet."
empty.ZIndex = 2
empty.Parent = body
body.ChildAdded:Connect(function(c)
	if c ~= empty then
		empty.Visible = false
	end
end)

local storeOpen = false
local function setStore(on: boolean)
	if on == storeOpen then
		return
	end
	storeOpen = on
	storeGui.Enabled = on
	MouseLook.free("Store", on)
	if on then
		ContextActionService:BindActionAtPriority("StoreClose", function(_, state)
			if state == Enum.UserInputState.Begin then
				setStore(false)
			end
			return Enum.ContextActionResult.Sink
		end, false, Enum.ContextActionPriority.High.Value, Enum.KeyCode.ButtonB)
	else
		ContextActionService:UnbindAction("StoreClose")
	end
end
closeBtn.Activated:Connect(function()
	setStore(false)
end)

UserInputService.InputBegan:Connect(function(io, processed)
	if processed or UserInputService:GetFocusedTextBox() then
		return
	end
	if io.KeyCode == Enum.KeyCode.F4 then
		setStore(not storeOpen)
	end
end)

---------------------------------------------------------------- the tiles

tile(1, "Store", "Store", RailIcons.Store, Color3.fromHex("#FFC83C"), "F4", function()
	setStore(not storeOpen)
end)

tile(2, "Bag", "Bag", RailIcons.Inventory, Color3.fromHex("#FF9A3C"), "N", function()
	local inv = playerGui:FindFirstChild("Inventory")
	if inv then
		inv:SetAttribute("ToggleRequest", os.clock())
	end
end)

tile(3, "Phone", "Phone", RailIcons.Phone, Color3.fromHex("#4C8DFF"), "UP", function()
	local ok, Phone = pcall(require, script.Parent:WaitForChild("Phone"))
	if ok and Phone then
		Phone.toggle()
	end
end)

tile(4, "Map", "Map", RailIcons.Map, Color3.fromHex("#3DDC5A"), "M", function()
	local radar = playerGui:FindFirstChild("Minimap")
	if radar then
		radar:SetAttribute("OpenMapRequest", os.clock())
	end
end)

---------------------------------------------------------------- layout

local function layout()
	local l = HudLayout.get()
	local s = l.scale
	railScale.Scale = s
	local n = #tiles
	local cols = if l.touch then 2 else 1
	local rows = math.ceil(n / cols)
	grid.FillDirectionMaxCells = cols
	rail.Size = UDim2.fromOffset(cols * TILE + (cols - 1) * GAP, rows * TILE + (rows - 1) * GAP)
	if l.touch then
		rail.AnchorPoint = Vector2.new(1, 0)
		rail.Position = UDim2.new(1, -R.Right, 0, HudLayout.topRightBottom() + 10)
	else
		rail.AnchorPoint = Vector2.new(1, 0.5)
		rail.Position = UDim2.new(1, -R.Right, 0.5, 0)
	end
	for _, k in keyHints do
		k.Visible = UserInputService.KeyboardEnabled and not l.touch
	end
	local cam = workspace.CurrentCamera
	local vp = if cam then cam.ViewportSize else Vector2.new(1280, 900)
	windowScale.Scale = math.min(1, (vp.X - 40) / WIN_W, (vp.Y - 40) / WIN_H)
end
HudLayout.Changed:Connect(layout)
UserInputService.LastInputTypeChanged:Connect(layout)
layout()
