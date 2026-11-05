--[[
	Inventory window, layout pass (copied from Dev's reference screenshot). I opens / closes it
	(phone: Bag button). Nothing is functional yet: every slot is empty and nothing can be
	picked up, moved or used. The two bars show your real health and armor.

	The window is drawn at a fixed design size (W x H) and a UIScale fits it to 94% of the
	screen height (or 96% of the width on narrow screens), so the layout keeps its proportions
	on every screen.

	Three columns:
	  left    Ground (items around you), Backpack under it (weight + Take off button)
	  middle  your name, character in the middle with 4 equipment slots on each side and 5 under
	          it, health / armor bars, Active items, Armor + Bag slots, quick slots 1-3
	  right   Inventory grid (5 wide, scrolls) with total weight and the close button
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")

local player = Players.LocalPlayer

-- design size; the UIScale fits it to the screen
local W, H = 820, 700
local HEIGHT_SHARE = 0.94
local WIDTH_SHARE = 0.96

local PAD = 14
local TOP = 48 -- columns start under the header row
local BOTTOM = H - PAD
local LEFT_X, SIDE_W = PAD, 248
local MID_X, MID_W = 276, 268
local RIGHT_X = 558

local COLORS = {
	Window = Color3.fromRGB(28, 29, 31),
	Slot = Color3.fromRGB(62, 64, 68),
	Panel = Color3.fromRGB(44, 45, 48),
	Line = Color3.fromRGB(80, 82, 86),
	Text = Color3.fromRGB(232, 233, 235),
	Dim = Color3.fromRGB(140, 143, 148),
	Health = Color3.fromRGB(205, 62, 62),
	Armor = Color3.fromRGB(66, 130, 190),
	BarBack = Color3.fromRGB(70, 72, 76),
}
local SLOT_TRANSPARENCY = 0.45
local FONT_FAMILY = "rbxasset://fonts/families/BuilderSans.json"
local BOLD = Font.new(FONT_FAMILY, Enum.FontWeight.Bold)
local REGULAR = Font.new(FONT_FAMILY, Enum.FontWeight.Medium)

local gui = Instance.new("ScreenGui")
gui.Name = "Inventory"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 10
gui.Enabled = false

local window = Instance.new("Frame")
window.Name = "Window"
window.AnchorPoint = Vector2.new(0.5, 0.5)
window.Position = UDim2.fromScale(0.5, 0.5)
window.Size = UDim2.fromOffset(W, H)
window.BackgroundColor3 = COLORS.Window
window.BackgroundTransparency = 0.12
window.BorderSizePixel = 0
window.Parent = gui

local scale = Instance.new("UIScale")
scale.Parent = window

-- frees the mouse while the window is open (first person locks it otherwise)
local modal = Instance.new("TextButton")
modal.Name = "Modal"
modal.Size = UDim2.fromOffset(0, 0)
modal.BackgroundTransparency = 1
modal.Text = ""
modal.Modal = true
modal.Parent = window

local function box(
	parent: Instance,
	name: string,
	x: number,
	y: number,
	w: number,
	h: number,
	color: Color3?,
	transparency: number?
): Frame
	local f = Instance.new("Frame")
	f.Name = name
	f.Position = UDim2.fromOffset(x, y)
	f.Size = UDim2.fromOffset(w, h)
	f.BorderSizePixel = 0
	if color then
		f.BackgroundColor3 = color
		f.BackgroundTransparency = transparency or 0
	else
		f.BackgroundTransparency = 1
	end
	f.Parent = parent
	return f
end

local function slot(parent: Instance, name: string, x: number, y: number, w: number, h: number): Frame
	return box(parent, name, x, y, w, h, COLORS.Slot, SLOT_TRANSPARENCY)
end

local function label(
	parent: Instance,
	name: string,
	str: string,
	x: number,
	y: number,
	w: number,
	h: number,
	size: number,
	color: Color3,
	font: Font,
	align: Enum.TextXAlignment?
): TextLabel
	local t = Instance.new("TextLabel")
	t.Name = name
	t.Position = UDim2.fromOffset(x, y)
	t.Size = UDim2.fromOffset(w, h)
	t.BackgroundTransparency = 1
	t.Text = str
	t.TextSize = size
	t.TextColor3 = color
	t.FontFace = font
	t.TextXAlignment = align or Enum.TextXAlignment.Left
	t.TextYAlignment = Enum.TextYAlignment.Center
	t.Parent = parent
	return t
end

-- A scrolling grid of empty square slots.
local function grid(
	parent: Instance,
	name: string,
	x: number,
	y: number,
	w: number,
	h: number,
	cols: number,
	cell: number,
	gap: number,
	count: number
): ScrollingFrame
	local sf = Instance.new("ScrollingFrame")
	sf.Name = name
	sf.Position = UDim2.fromOffset(x, y)
	sf.Size = UDim2.fromOffset(w, h)
	sf.BackgroundTransparency = 1
	sf.BorderSizePixel = 0
	sf.ScrollBarThickness = 4
	sf.ScrollBarImageColor3 = COLORS.Dim
	sf.ScrollingDirection = Enum.ScrollingDirection.Y
	sf.CanvasSize = UDim2.new()
	sf.AutomaticCanvasSize = Enum.AutomaticSize.Y
	local layout = Instance.new("UIGridLayout")
	layout.CellSize = UDim2.fromOffset(cell, cell)
	layout.CellPadding = UDim2.fromOffset(gap, gap)
	layout.FillDirectionMaxCells = cols
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = sf
	for i = 1, count do
		local s = Instance.new("Frame")
		s.Name = `Slot{i}`
		s.LayoutOrder = i
		s.BackgroundColor3 = COLORS.Slot
		s.BackgroundTransparency = SLOT_TRANSPARENCY
		s.BorderSizePixel = 0
		s.Parent = sf
	end
	sf.Parent = parent
	return sf
end

-- column dividers
box(window, "DividerLeft", MID_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)
box(window, "DividerRight", RIGHT_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)

---------------------------------------------------------------- left: ground + backpack
local left = box(window, "Left", LEFT_X, 0, SIDE_W, H)
label(left, "Title", "Ground", 0, 10, SIDE_W, 26, 16, COLORS.Text, BOLD)
grid(left, "Ground", 0, TOP, SIDE_W, 320, 4, 56, 6, 20)

box(left, "Line", 0, 380, SIDE_W, 1, COLORS.Line, 0.6)
label(left, "BackpackTitle", "Backpack", 0, 390, 80, 24, 16, COLORS.Text, BOLD)
label(left, "BackpackWeight", "0.00 / 10 kg", 80, 390, 90, 24, 13, COLORS.Dim, REGULAR)
local takeOff = Instance.new("TextButton")
takeOff.Name = "TakeOff"
takeOff.Position = UDim2.fromOffset(SIDE_W - 70, 391)
takeOff.Size = UDim2.fromOffset(70, 22)
takeOff.BackgroundColor3 = COLORS.Slot
takeOff.BackgroundTransparency = SLOT_TRANSPARENCY
takeOff.BorderSizePixel = 0
takeOff.AutoButtonColor = true
takeOff.Text = "Take off"
takeOff.TextSize = 13
takeOff.TextColor3 = COLORS.Dim
takeOff.FontFace = REGULAR
takeOff.Parent = left
grid(left, "Backpack", 0, 422, SIDE_W, BOTTOM - 422, 4, 56, 6, 16)

---------------------------------------------------------------- middle: character + equipment
local mid = box(window, "Middle", MID_X, 0, MID_W, H)
local nameLabel = label(mid, "PlayerName", "", 0, 10, MID_W, 26, 16, COLORS.Text, BOLD, Enum.TextXAlignment.Center)

-- 4 equipment slots down each side of the character, 5 under it
local EQUIP = 44
for i = 0, 3 do
	slot(mid, `EquipLeft{i + 1}`, 0, TOP + i * 54, EQUIP, EQUIP)
	slot(mid, `EquipRight{i + 1}`, MID_W - EQUIP, TOP + i * 54, EQUIP, EQUIP)
end
box(mid, "Character", EQUIP + 8, TOP, MID_W - (EQUIP + 8) * 2, 206, COLORS.Panel, 0.5)
for i = 0, 4 do
	slot(mid, `EquipBottom{i + 1}`, i * 55, 264, 48, EQUIP)
end

-- health / armor bars (live)
local function bar(name: string, y: number, color: Color3): (Frame, TextLabel)
	box(mid, name .. "Icon", 0, y + 2, 10, 10, color)
	local back = box(mid, name .. "Bar", 18, y + 5, MID_W - 18 - 40, 4, COLORS.BarBack)
	local fill = box(back, "Fill", 0, 0, 0, 4, color)
	fill.Size = UDim2.fromScale(0, 1)
	local value = label(mid, name .. "Value", "0", MID_W - 34, y, 34, 14, 13, COLORS.Text, REGULAR, Enum.TextXAlignment.Right)
	return fill, value
end
local healthFill, healthValue = bar("Health", 322, COLORS.Health)
local armorFill, armorValue = bar("Armor", 344, COLORS.Armor)

-- active items (things in use right now)
local active = box(mid, "ActiveItems", 0, 372, MID_W, 126, COLORS.Panel, 0.5)
label(active, "Label", "Active items", 0, 0, MID_W, 126, 13, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)

-- armor + bag slots
local armorSlot = slot(mid, "ArmorSlot", 0, 506, 130, 96)
label(armorSlot, "Label", "Armor", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
local bagSlot = slot(mid, "BagSlot", 138, 506, 130, 96)
label(bagSlot, "Label", "Bag", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)

-- quick slots 1-3
for i = 0, 2 do
	local q = slot(mid, `Quick{i + 1}`, i * 92, 610, 84, BOTTOM - 610)
	label(q, "Number", tostring(i + 1), 0, 2, 84, 14, 11, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
end

---------------------------------------------------------------- right: inventory grid
local right = box(window, "Right", RIGHT_X, 0, SIDE_W, H)
label(right, "Title", "Inventory", 0, 10, 120, 26, 16, COLORS.Text, BOLD)
label(right, "Weight", "0.00 / 30 kg", 120, 10, SIDE_W - 120 - 30, 26, 13, COLORS.Dim, REGULAR, Enum.TextXAlignment.Right)
local close = Instance.new("TextButton")
close.Name = "Close"
close.Position = UDim2.fromOffset(SIDE_W - 22, 10)
close.Size = UDim2.fromOffset(22, 26)
close.BackgroundTransparency = 1
close.Text = "×"
close.TextSize = 22
close.TextColor3 = COLORS.Dim
close.FontFace = REGULAR
close.Parent = right
grid(right, "Items", 0, TOP, SIDE_W, BOTTOM - TOP, 5, 44, 4, 70)

---------------------------------------------------------------- fit, live bars, open / close
local function fit()
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local v = cam.ViewportSize
	scale.Scale = math.min(v.Y * HEIGHT_SHARE / H, v.X * WIDTH_SHARE / W)
end
local camConn: RBXScriptConnection? = nil
local function watchCamera()
	if camConn then
		camConn:Disconnect()
	end
	local cam = workspace.CurrentCamera
	if cam then
		camConn = cam:GetPropertyChangedSignal("ViewportSize"):Connect(fit)
	end
	fit()
end
workspace:GetPropertyChangedSignal("CurrentCamera"):Connect(watchCamera)
watchCamera()

local function setBar(fill: Frame, value: TextLabel, now: number, max: number)
	fill.Size = UDim2.fromScale(if max > 0 then math.clamp(now / max, 0, 1) else 0, 1)
	value.Text = tostring(math.ceil(math.max(now, 0)))
end

local charConns: { RBXScriptConnection } = {}
local function onCharacter(character: Model)
	for _, c in charConns do
		c:Disconnect()
	end
	table.clear(charConns)
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if not humanoid then
		return
	end
	local function update()
		setBar(healthFill, healthValue, humanoid.Health, humanoid.MaxHealth)
		setBar(armorFill, armorValue, humanoid:GetAttribute("Armor") or 0, humanoid:GetAttribute("MaxArmor") or 0)
	end
	table.insert(charConns, humanoid.HealthChanged:Connect(update))
	table.insert(charConns, humanoid:GetAttributeChangedSignal("Armor"):Connect(update))
	table.insert(charConns, humanoid:GetAttributeChangedSignal("MaxArmor"):Connect(update))
	update()
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end

local function setOpen(open: boolean)
	if open then
		nameLabel.Text = player.DisplayName
		fit()
	end
	gui.Enabled = open
end
close.Activated:Connect(function()
	setOpen(false)
end)

gui.Parent = player:WaitForChild("PlayerGui")

ContextActionService:BindAction("Inventory_Toggle", function(_, state)
	if state == Enum.UserInputState.Begin then
		setOpen(not gui.Enabled)
	end
	return Enum.ContextActionResult.Pass
end, true, Enum.KeyCode.I)
ContextActionService:SetTitle("Inventory_Toggle", "Bag")
ContextActionService:SetPosition("Inventory_Toggle", UDim2.new(1, -245, 1, -210))
