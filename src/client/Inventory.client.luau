--[[
	Inventory window (copied from Dev's reference screenshot). N opens / closes it (phone: Bag
	button). Roblox's own backpack bar is turned off.

	The server owns the items (Server/Inventory/InventoryService) and sends them here; this
	draws them and asks the server to move them. Items cover several cells (Shared/Items Cells:
	vest 2 x 2, carbine 4 x 2). While dragging, a green box shows where it lands (red: it doesn't
	fit or is too heavy) and R turns it 90 degrees. Drag an item:
	  - into Inventory / Backpack: puts it there (or onto a stack of the same item)
	  - onto Ground: drops it in front of you (a gun in your hands is put away first)
	  - from Ground into a slot: picks it up (also: press E on it: walk up, bend down, grab,
	    Movement/Moves/Pickup)
	  - a vest onto the Armor slot: puts it on (the vest animation, like V); the worn vest
	    dragged into a slot takes it off
	Moves that would go over a weight limit are refused by the server. Hovering an item shows
	its name, description and weight. Right-click or double-click (double-tap) uses an item
	(Shared/Items Use: drink, heal, take a gun out, put a vest on); so does its quick slot key.
	A timed use shows a bar above the quick bar. Item icons are the real 3D models (ReplicatedStorage.ItemModels).

	The window is drawn at a fixed design size (W x H) and a UIScale fits it to 94% of the
	screen height (or 96% of the width on narrow screens).
	Equipment slots around the character, the Bag slot and quick slots 1-3 are layout only.
]]

local ContextActionService = game:GetService("ContextActionService")
local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local StarterGui = game:GetService("StarterGui")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Items = require(Shared:WaitForChild("Items"))
local Grid = require(Shared:WaitForChild("Items"):WaitForChild("Grid"))
local Armor = require(Shared:WaitForChild("Armor"))
local IconIds = require(Shared:WaitForChild("IconIds"))
local Weapons = require(script.Parent:WaitForChild("Weapons"))
local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))
local Pickup = require(script.Parent:WaitForChild("Movement"):WaitForChild("Moves"):WaitForChild("Pickup"))

local Remotes = ReplicatedStorage:WaitForChild("InventoryRemotes")
local MoveRemote = Remotes:WaitForChild("Move") :: RemoteEvent
local UseRemote = Remotes:WaitForChild("Use") :: RemoteEvent
local NoticeRemote = Remotes:WaitForChild("Notice") :: RemoteEvent
local CFG = Config.Inventory
local player = Players.LocalPlayer

-- Roblox's default backpack / hotbar
task.spawn(function()
	for _ = 1, 10 do
		if pcall(StarterGui.SetCoreGuiEnabled, StarterGui, Enum.CoreGuiType.Backpack, false) then
			return
		end
		task.wait(1)
	end
end)

-- design size; the UIScale fits it to the screen
local W, H = 820, 700
local HEIGHT_SHARE = 0.94
local WIDTH_SHARE = 0.96
-- Short screens (phones held sideways): the whole window would shrink to about half size, so
-- instead it fills the width at a readable size, sits under the Roblox top bar, and the left
-- and middle columns scroll (the inventory grid gets shorter and scrolls on its own).
local COMPACT_BELOW = 0.75 -- use that when the fitted scale would be smaller than this
local COMPACT_WIDTH_SHARE = 0.86 -- leaves room for a phone's notch on either side

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
	Icon = Color3.fromRGB(120, 123, 128),
	Health = Color3.fromRGB(205, 62, 62),
	Armor = Color3.fromRGB(66, 130, 190),
	BarBack = Color3.fromRGB(70, 72, 76),
	Good = Color3.fromRGB(110, 200, 110),
	Mid = Color3.fromRGB(230, 170, 70),
	Bad = Color3.fromRGB(220, 80, 70),
}
local SLOT_TRANSPARENCY = 0.45
local FONT_FAMILY = "rbxasset://fonts/families/BuilderSans.json"
local BOLD = Font.new(FONT_FAMILY, Enum.FontWeight.Bold)
local REGULAR = Font.new(FONT_FAMILY, Enum.FontWeight.Medium)

local gui = Instance.new("ScreenGui")
gui.Name = "Inventory"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling -- a big item's tile draws over the cells it covers
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
window.Active = true -- clicks on the window don't reach the game (no shooting while dragging)
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

local function icon(parent: Instance, name: string, image: string?, x: number, y: number, size: number, color: Color3): ImageLabel
	local img = Instance.new("ImageLabel")
	img.Name = name
	img.Position = UDim2.fromOffset(x, y)
	img.Size = UDim2.fromOffset(size, size)
	img.BackgroundTransparency = 1
	img.Image = image or ""
	img.ImageColor3 = color
	img.ScaleType = Enum.ScaleType.Fit
	img.Parent = parent
	return img
end

---------------------------------------------------------------- drop targets / cells

type Target = { frame: GuiObject, container: string, slot: number?, clip: GuiObject? }
local targets: { Target } = {}
local scrollers: { ScrollingFrame } = {} -- everything that scrolls; frozen while dragging
local cells: { [string]: { Frame } } = { Inventory = {}, Backpack = {}, Ground = {} }
local cellMeta: { [Frame]: { container: string, slot: number? } } = {}
local cellItem: { [Frame]: any } = {} -- the item covering this cell
local cellAnchor: { [Frame]: number? } = {} -- top-left slot of that item (grids)

-- the two item grids (cell size in design px); items cover Cells of them (Shared/Items/Grid)
local GRIDS = {
	Inventory = { cols = CFG.Cols, rows = CFG.Rows, cell = 44, gap = 4 },
	Backpack = { cols = CFG.BackpackCols, rows = CFG.BackpackRows, cell = 56, gap = 6 },
}

-- A scrolling grid of square slots; each one is a drop target.
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
		cells[name][i] = s
		cellMeta[s] = { container = name, slot = i }
		table.insert(targets, { frame = s, container = name, slot = i, clip = sf })
	end
	sf.Parent = parent
	table.insert(scrollers, sf)
	return sf
end

-- column dividers
box(window, "DividerLeft", MID_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)
box(window, "DividerRight", RIGHT_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)

-- a column that scrolls when the window is shorter than its content (phones)
-- a grid that always fits its box doesn't scroll, so a finger on it scrolls the column instead
local function fixed(sf: ScrollingFrame)
	sf.ScrollingEnabled = false
	local i = table.find(scrollers, sf)
	if i then
		table.remove(scrollers, i)
	end
end

local function column(name: string, x: number, w: number): ScrollingFrame
	local sf = Instance.new("ScrollingFrame")
	sf.Name = name
	sf.Position = UDim2.fromOffset(x, 0)
	sf.Size = UDim2.fromOffset(w, H)
	sf.CanvasSize = UDim2.fromOffset(0, H)
	sf.BackgroundTransparency = 1
	sf.BorderSizePixel = 0
	sf.ScrollBarThickness = 3
	sf.ScrollBarImageColor3 = COLORS.Dim
	sf.ScrollingDirection = Enum.ScrollingDirection.Y
	sf.Parent = window
	table.insert(scrollers, sf)
	return sf
end

---------------------------------------------------------------- left: ground + backpack
local left = column("Left", LEFT_X, SIDE_W)
label(left, "Title", "Ground", 0, 10, SIDE_W, 26, 16, COLORS.Text, BOLD)
local groundGrid = grid(left, "Ground", 0, TOP, SIDE_W, 320, 4, 56, 6, 20)
fixed(groundGrid)
table.insert(targets, { frame = groundGrid, container = "Ground" }) -- empty space counts too

box(left, "Line", 0, 380, SIDE_W, 1, COLORS.Line, 0.6)
label(left, "BackpackTitle", "Backpack", 0, 390, 80, 24, 16, COLORS.Text, BOLD)
local backpackWeight = label(left, "BackpackWeight", "", 80, 390, 100, 24, 13, COLORS.Dim, REGULAR)
local takeOff = Instance.new("TextButton")
takeOff.Name = "TakeOff" -- for bags later (the Bag slot); does nothing yet
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
fixed(grid(left, "Backpack", 0, 422, SIDE_W, BOTTOM - 422, GRIDS.Backpack.cols, 56, 6, GRIDS.Backpack.cols * GRIDS.Backpack.rows))

---------------------------------------------------------------- middle: character + equipment
local mid = column("Middle", MID_X, MID_W)
local nameLabel = label(mid, "PlayerName", "", 0, 10, MID_W, 26, 16, COLORS.Text, BOLD, Enum.TextXAlignment.Center)

-- 4 equipment slots down each side of the character, 5 under it (layout only for now)
local EQUIP = 44
for i = 0, 3 do
	slot(mid, `EquipLeft{i + 1}`, 0, TOP + i * 54, EQUIP, EQUIP)
	slot(mid, `EquipRight{i + 1}`, MID_W - EQUIP, TOP + i * 54, EQUIP, EQUIP)
end
local characterBox = box(mid, "Character", EQUIP + 8, TOP, MID_W - (EQUIP + 8) * 2, 206, COLORS.Panel, 0.5)
-- your own character, seen from the front (filled in by refreshPortrait below)
local portrait = Instance.new("ViewportFrame")
portrait.Name = "Portrait"
portrait.Size = UDim2.fromScale(1, 1)
portrait.BackgroundTransparency = 1
portrait.Ambient = Color3.fromRGB(150, 150, 156)
portrait.LightColor = Color3.fromRGB(255, 255, 255)
portrait.LightDirection = Vector3.new(-0.4, -0.6, 1) -- from the front, top left
portrait.Parent = characterBox
for i = 0, 4 do
	slot(mid, `EquipBottom{i + 1}`, i * 55, 264, 48, EQUIP)
end

-- health / armor bars (live)
local function bar(name: string, y: number, color: Color3, image: string?): (Frame, TextLabel)
	icon(mid, name .. "Icon", image, 0, y - 1, 14, color)
	local back = box(mid, name .. "Bar", 20, y + 5, MID_W - 20 - 40, 4, COLORS.BarBack)
	local fill = box(back, "Fill", 0, 0, 0, 4, color)
	fill.Size = UDim2.fromScale(0, 1)
	local value = label(mid, name .. "Value", "0", MID_W - 34, y, 34, 14, 13, COLORS.Text, REGULAR, Enum.TextXAlignment.Right)
	return fill, value
end
local healthFill, healthValue = bar("Health", 322, COLORS.Health, IconIds.Heart)
local armorFill, armorValue = bar("Armor", 344, COLORS.Armor, IconIds.Shield)

-- active items: what's in your hands. Drag a gun in to take it out, drag it out to put it away.
local active = box(mid, "ActiveItems", 0, 372, MID_W, 126, COLORS.Panel, 0.5)
local activeIcon = icon(active, "Icon", IconIds.Hands, MID_W / 2 - 18, 30, 36, COLORS.Icon)
local activeLabel =
	label(active, "Label", "Active items", 0, 66, MID_W, 20, 13, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
cellMeta[active] = { container = "Active" }
table.insert(targets, { frame = active, container = "Active" })

-- armor + bag slots
local armorSlot = slot(mid, "ArmorSlot", 0, 506, 130, 96)
local armorEmptyIcon = icon(armorSlot, "EmptyIcon", IconIds.Vest, 65 - 21, 20, 42, COLORS.Icon)
local armorEmptyLabel = label(armorSlot, "Label", "Armor", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
cellMeta[armorSlot] = { container = "Armor" }
table.insert(targets, { frame = armorSlot, container = "Armor" })

local bagSlot = slot(mid, "BagSlot", 138, 506, 130, 96)
icon(bagSlot, "EmptyIcon", IconIds.Backpack, 65 - 20, 20, 40, COLORS.Icon)
label(bagSlot, "Label", "Bag", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)

-- quick slots 1-3 (keys 1-3 / the quick bar use what's in them; Server/Inventory "Quick")
local QUICK = CFG.QuickSlots or 3
local quickSlots: { Frame } = {}
for i = 1, QUICK do
	local qw = (MID_W - (QUICK - 1) * 8) / QUICK
	local q = slot(mid, `Quick{i}`, (i - 1) * (qw + 8), 610, qw, BOTTOM - 610)
	local n = label(q, "Number", tostring(i), 0, 2, qw, 14, 11, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
	n.ZIndex = 3
	quickSlots[i] = q
	cellMeta[q] = { container = "Quick", slot = i }
	table.insert(targets, { frame = q, container = "Quick", slot = i })
end

---------------------------------------------------------------- right: inventory grid
local right = box(window, "Right", RIGHT_X, 0, SIDE_W, H)
label(right, "Title", "Inventory", 0, 10, 120, 26, 16, COLORS.Text, BOLD)
local invWeight =
	label(right, "Weight", "", 120, 10, SIDE_W - 120 - 30, 26, 13, COLORS.Dim, REGULAR, Enum.TextXAlignment.Right)
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
local inventoryGrid =
	grid(right, "Inventory", 0, TOP, SIDE_W, BOTTOM - TOP, GRIDS.Inventory.cols, 44, 4, GRIDS.Inventory.cols * GRIDS.Inventory.rows)

-- hover info and the item being dragged sit above the window, outside its UIScale
local tooltip = Instance.new("TextLabel")
tooltip.Name = "Tooltip"
tooltip.AutomaticSize = Enum.AutomaticSize.XY
tooltip.Size = UDim2.fromOffset(0, 0)
tooltip.BackgroundColor3 = Color3.fromRGB(20, 21, 23)
tooltip.BackgroundTransparency = 0.05
tooltip.BorderSizePixel = 0
tooltip.TextColor3 = COLORS.Text
tooltip.FontFace = REGULAR
tooltip.TextSize = 14
tooltip.RichText = true
tooltip.TextXAlignment = Enum.TextXAlignment.Left
tooltip.ZIndex = 50
tooltip.Visible = false
local tipPad = Instance.new("UIPadding")
tipPad.PaddingLeft = UDim.new(0, 8)
tipPad.PaddingRight = UDim.new(0, 8)
tipPad.PaddingTop = UDim.new(0, 5)
tipPad.PaddingBottom = UDim.new(0, 5)
tipPad.Parent = tooltip
tooltip.Parent = gui

---------------------------------------------------------------- item icons

local modelsFolder = ReplicatedStorage:WaitForChild("ItemModels", 10)

-- The item's picture, filling a tile of this aspect (width / height); turned items are drawn
-- turned. Items with a rendered picture (def.Icon from Shared.ItemIconIds, sharp and smooth) use that;
-- the rest show their 3D model in a transparent ViewportFrame, or their name until it loads.
local function makeIcon(id: string, aspect: number, rot: boolean?): GuiObject
	local def = Items.get(id)
	local picture = def and def.Icon
	if picture then
		local holder = Instance.new("Frame")
		holder.Name = "Icon"
		holder.Size = UDim2.fromScale(1, 1)
		holder.BackgroundTransparency = 1
		local img = Instance.new("ImageLabel")
		img.Name = "Image"
		img.BackgroundTransparency = 1
		img.Image = picture
		img.ScaleType = Enum.ScaleType.Fit
		img.AnchorPoint = Vector2.new(0.5, 0.5)
		img.Position = UDim2.fromScale(0.5, 0.5)
		-- a turned item: the picture keeps its own shape, turned a quarter to the left
		img.Size = if rot then UDim2.fromScale(1 / aspect, aspect) else UDim2.fromScale(1, 1)
		img.Rotation = if rot then -90 else 0
		img.Parent = holder
		return holder
	end
	local template = modelsFolder and modelsFolder:FindFirstChild(id)
	if not template or not template:IsA("Model") then
		local t = Instance.new("TextLabel")
		t.Name = "Icon"
		t.Size = UDim2.fromScale(1, 1)
		t.BackgroundTransparency = 1
		t.Text = if def then def.Name else id
		t.TextWrapped = true
		t.TextSize = 11
		t.TextColor3 = COLORS.Text
		t.FontFace = REGULAR
		t:SetAttribute("Fallback", true)
		return t
	end
	local vf = Instance.new("ViewportFrame")
	vf.Name = "Icon"
	vf.Size = UDim2.fromScale(1, 1)
	vf.BackgroundTransparency = 1
	vf.Ambient = Color3.fromRGB(165, 165, 170)
	vf.LightColor = Color3.fromRGB(255, 255, 255)
	vf.LightDirection = Vector3.new(-0.4, -1, -0.6)
	local m = template:Clone()
	m.Parent = vf
	local cf, size = m:GetBoundingBox()
	local cam = Instance.new("Camera")
	cam.FieldOfView = 20
	local dir = ((def and def.IconView) or Vector3.new(0, 0.2, -1)).Unit
	local roll = ((def and def.IconRoll) or 0) + (if rot then 90 else 0)
	local turn = CFrame.lookAt(Vector3.zero, -dir) * CFrame.Angles(0, 0, math.rad(roll))
	-- the closest camera distance that keeps every bounding box corner inside the view (a
	-- little padding), so the item fills its tile
	local tanV = math.tan(math.rad(cam.FieldOfView / 2)) * 0.95
	local tanH = tanV * aspect
	local dist = 0
	for _, sx in { -1, 1 } do
		for _, sy in { -1, 1 } do
			for _, sz in { -1, 1 } do
				local corner = cf:VectorToWorldSpace(Vector3.new(sx * size.X, sy * size.Y, sz * size.Z) / 2)
				local v = turn:VectorToObjectSpace(corner)
				dist = math.max(dist, v.Z + math.abs(v.X) / tanH, v.Z + math.abs(v.Y) / tanV)
			end
		end
	end
	cam.CFrame = CFrame.new(cf.Position) * turn * CFrame.new(0, 0, dist)
	cam.Parent = vf
	vf.CurrentCamera = cam
	return vf
end

local function armorShare(item: any, worn: boolean): number?
	local def = Armor.get(item.id)
	if not def or def.MaxArmor <= 0 then
		return nil
	end
	if worn then
		local h = player.Character and player.Character:FindFirstChildOfClass("Humanoid")
		return h and (h:GetAttribute("Armor") or 0) / def.MaxArmor or nil
	end
	local a = item.data and item.data.armor
	return if typeof(a) == "number" then a / def.MaxArmor else 1
end

-- design px of a w x h footprint in a grid
local function footprint(g: any, w: number, h: number): Vector2
	return Vector2.new(w * g.cell + (w - 1) * g.gap, h * g.cell + (h - 1) * g.gap)
end

-- Show an item (or nothing) on a cell. For grid cells the tile spans the item's whole
-- footprint (g = the grid, w x h cells); Ground / Armor tiles fill their one cell.
local function setTile(cell: Frame, item: any?, g: any?, w: number?, h: number?, worn: boolean?)
	local tile = cell:FindFirstChild("Tile") :: Frame?
	if not item then
		if tile then
			tile:Destroy()
		end
		return
	end
	if not tile then
		local t = Instance.new("Frame")
		t.Name = "Tile"
		t.BorderSizePixel = 0
		t.BackgroundColor3 = COLORS.Slot
		t.Parent = cell
		tile = t
	end
	assert(tile)
	local aspect = cell.Size.X.Offset / math.max(1, cell.Size.Y.Offset)
	if g and w and h then
		local px = footprint(g, w, h)
		tile.Size = UDim2.fromOffset(px.X, px.Y)
		tile.BackgroundTransparency = SLOT_TRANSPARENCY -- one tile background over the covered cells
		aspect = px.X / px.Y
	else
		tile.Size = UDim2.fromScale(1, 1)
		tile.BackgroundTransparency = 1
		if cell.Size.X.Scale == 0 and cell.Size.X.Offset > 0 then
			aspect = cell.Size.X.Offset / cell.Size.Y.Offset
		else
			aspect = 1
		end
	end
	local key = `{item.id}|{if item.rot then 1 else 0}|{math.floor(aspect * 100)}`
	local old = tile:FindFirstChild("Icon")
	local stale = old and old:GetAttribute("Fallback") and modelsFolder and modelsFolder:FindFirstChild(item.id)
	if tile:GetAttribute("Key") ~= key or not old or stale then
		if old then
			old:Destroy()
		end
		makeIcon(item.id, aspect, item.rot).Parent = tile
		tile:SetAttribute("Key", key)
	end
	-- stack count, bottom right
	local count = tile:FindFirstChild("Count") :: TextLabel?
	local n = item.count or 1
	if n > 1 then
		if not count then
			local c = label(tile, "Count", "", 0, 0, 40, 14, 12, COLORS.Text, BOLD, Enum.TextXAlignment.Right)
			c.AnchorPoint = Vector2.new(1, 1)
			c.Position = UDim2.new(1, -3, 1, -1)
			c.TextStrokeTransparency = 0.5
			c.ZIndex = 3
			count = c
		end
		assert(count).Text = tostring(n)
	elseif count then
		count:Destroy()
	end
	-- armor left on a vest, bottom left (like the reference's 50%)
	local info = tile:FindFirstChild("Info") :: TextLabel?
	local share = armorShare(item, worn == true)
	if share then
		if not info then
			local c = label(tile, "Info", "", 0, 0, 40, 14, 11, COLORS.Good, BOLD, Enum.TextXAlignment.Left)
			c.AnchorPoint = Vector2.new(0, 1)
			c.Position = UDim2.new(0, 3, 1, -1)
			c.TextStrokeTransparency = 0.6
			c.ZIndex = 3
			info = c
		end
		local i = assert(info)
		i.Text = `{math.floor(share * 100 + 0.5)}%`
		i.TextColor3 = if share >= 0.66 then COLORS.Good elseif share >= 0.33 then COLORS.Mid else COLORS.Bad
	elseif info then
		info:Destroy()
	end
end

---------------------------------------------------------------- state from the server

local state: any = { containers = { Inventory = {}, Backpack = {} }, armor = false, quick = {} }
-- top-left slot -> item (Quick: slot number -> item)
local lists: { [string]: { [number]: any } } = { Inventory = {}, Backpack = {}, Quick = {} }
local ground: { any } = {}

local function weightOf(list: { [any]: any }): number
	local w = 0
	for _, e in list do
		local def = Items.get(e.id)
		w += (if def then def.Weight else 0) * (e.count or 1)
	end
	return w
end

-- kg used toward a container's limit (the quick slots share the Inventory's)
local function bucket(name: string): string
	return if name == "Quick" then "Inventory" else name
end
local function used(name: string): number
	local b = bucket(name)
	local w = weightOf(lists[b] or {})
	if b == "Inventory" then
		w += weightOf(lists.Quick)
	end
	return w
end
local function maxOf(name: string): number
	return if bucket(name) == "Backpack" then CFG.BackpackMaxWeight else CFG.MaxWeight
end

-- The carried item with this id (the gun in your hands): container, slot, item.
local function findCarried(id: string?): (string?, number?, any?)
	if not id then
		return nil, nil, nil
	end
	for _, name in { "Quick", "Inventory", "Backpack" } do
		for slotNo, e in lists[name] or {} do
			if e.id == id then
				return name, slotNo, e
			end
		end
	end
	return nil, nil, nil
end

local onQuickChanged: (() -> ())? = nil -- the quick bar (below) redraws on this

-- Active items: the gun in your hands
local activeRef: { container: string, slot: number, item: any }? = nil
local shownEquipped: string? = nil
local function renderActive()
	shownEquipped = WeaponState.Equipped
	local name, slotNo, e = findCarried(WeaponState.Equipped)
	activeRef = if name and slotNo and e then { container = name, slot = slotNo, item = e } else nil
	cellItem[active] = e
	setTile(active, e)
	activeIcon.Visible = e == nil
	activeLabel.Visible = e == nil
end

local function renderGround()
	for i, cell in cells.Ground do
		cellItem[cell] = ground[i]
		setTile(cell, ground[i])
	end
end

local function render()
	for name, g in GRIDS do
		local bySlot = {}
		for _, e in state.containers[name] or {} do
			bySlot[e.slot] = e
		end
		lists[name] = bySlot
		local occ = Grid.occupancy(bySlot, g.cols)
		for i, cell in cells[name] do
			local anchor = occ[i]
			cellAnchor[cell] = anchor
			cellItem[cell] = if anchor then bySlot[anchor] else nil
			if anchor == i then
				local w, h = Grid.size(bySlot[i])
				setTile(cell, bySlot[i], g, w, h)
				cell.ZIndex = 2 -- the tile spills over the next cells: draw it above them
			else
				setTile(cell, nil)
				cell.ZIndex = 1
			end
			cell.BackgroundTransparency = if anchor then 1 else SLOT_TRANSPARENCY
		end
	end
	local quickBy = {}
	for _, e in state.quick or {} do
		quickBy[e.slot] = e
	end
	lists.Quick = quickBy
	for i, q in quickSlots do
		cellItem[q] = quickBy[i]
		setTile(q, quickBy[i])
	end
	renderActive()
	if onQuickChanged then
		onQuickChanged()
	end
	invWeight.Text = string.format("%.2f / %d kg", used("Inventory"), CFG.MaxWeight)
	backpackWeight.Text = string.format("%.2f / %d kg", used("Backpack"), CFG.BackpackMaxWeight)
	local armor = if state.armor then state.armor else nil
	cellItem[armorSlot] = armor
	setTile(armorSlot, armor, nil, nil, nil, true)
	armorEmptyIcon.Visible = armor == nil
	armorEmptyLabel.Visible = armor == nil
	renderGround()
end

Remotes:WaitForChild("State").OnClientEvent:Connect(function(snapshot)
	state = snapshot
	render()
end)
Remotes:WaitForChild("Request"):FireServer()

if modelsFolder then
	modelsFolder.ChildAdded:Connect(function()
		task.defer(render) -- swap name placeholders for the model icons
	end)
end

-- a dropped item's model by its Uid
local function droppedModel(uid: string): Model?
	local folder = workspace:FindFirstChild("DroppedItems")
	for _, m in (if folder then folder:GetChildren() else {}) do
		if m:IsA("Model") and m:GetAttribute("Uid") == uid then
			return m
		end
	end
	return nil
end

-- E on a dropped item: walk up to it, bend down and grab it (Movement/Moves/Pickup); the server
-- is asked to take it when the hand gets there. (The server also takes it by itself a few
-- seconds later if that request never comes.)
local ProximityPromptService = game:GetService("ProximityPromptService")
ProximityPromptService.PromptTriggered:Connect(function(prompt, who)
	if who ~= player or Pickup.busy() then
		return -- already picking something up: extra presses do nothing
	end
	local folder = workspace:FindFirstChild("DroppedItems")
	local model = folder and prompt:FindFirstAncestorOfClass("Model")
	while model and model.Parent ~= folder do
		model = model:FindFirstAncestorOfClass("Model")
	end
	local uid = model and model:GetAttribute("Uid")
	if not model or typeof(uid) ~= "string" then
		print("[Pickup] prompt isn't on a dropped item model:", prompt:GetFullName())
		return
	end
	-- hide this item's prompt until the pickup is over, so it can't be pressed again
	prompt.Enabled = false
	task.spawn(function()
		local t0 = os.clock()
		repeat
			task.wait(0.1)
		until not Pickup.busy() or os.clock() - t0 > 8
		task.wait(0.5) -- the server's answer (item gone) usually lands first
		if prompt.Parent then
			prompt.Enabled = true
		end
	end)
	Pickup.request(model:GetPivot().Position, function()
		MoveRemote:FireServer("Ground", uid, "Inventory", 0, false) -- no slot: wherever it fits
	end, true)
end)

-- dropped items near you (Workspace.DroppedItems, Server/Inventory)
local function scanGround()
	local list = {}
	local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
	local folder = workspace:FindFirstChild("DroppedItems")
	if root and folder then
		for _, m in folder:GetChildren() do
			local uid = m:GetAttribute("Uid")
			if uid and m:IsA("Model") then
				local d = (m:GetPivot().Position - root.Position).Magnitude
				if d <= CFG.GroundRange then
					table.insert(list, { uid = uid, id = m:GetAttribute("ItemId"), count = m:GetAttribute("Count") or 1, dist = d })
				end
			end
		end
	end
	table.sort(list, function(a, b)
		return a.dist < b.dist
	end)
	ground = list
end

---------------------------------------------------------------- hover info

local function point(input: InputObject): Vector2
	-- screen pixels from the very top-left (this ScreenGui ignores the top bar inset)
	if input.UserInputType == Enum.UserInputType.Touch then
		local inset = GuiService:GetGuiInset()
		return Vector2.new(input.Position.X, input.Position.Y) + inset
	end
	return UserInputService:GetMouseLocation()
end

local function rectOf(obj: GuiObject): (Vector2, Vector2)
	local p = obj.AbsolutePosition - gui.AbsolutePosition
	return p, p + obj.AbsoluteSize
end

local function inside(obj: GuiObject, p: Vector2): boolean
	local a, b = rectOf(obj)
	return p.X >= a.X and p.Y >= a.Y and p.X <= b.X and p.Y <= b.Y
end

local hovered: Frame? = nil
local function showTip(p: Vector2)
	local item = hovered and cellItem[hovered]
	local def = item and Items.get(item.id)
	if not item or not def then
		tooltip.Visible = false
		return
	end
	local n = item.count or 1
	local w, h = Grid.size(item)
	local lines = { `<b>{def.Name}</b>{if n > 1 then `  x{n}` else ""}` }
	if def.Description then
		table.insert(lines, def.Description)
	end
	table.insert(lines, string.format("%.2f kg  ·  %d x %d", def.Weight * n, w, h))
	local share = armorShare(item, hovered == armorSlot)
	if share then
		table.insert(lines, `Armor {math.floor(share * 100 + 0.5)}%`)
	end
	local action = Items.useAction(def)
	local meta = hovered and cellMeta[hovered]
	if action and not (meta and meta.container == "Ground") then
		local verb = if def.Use and def.Use.Action == "Wear" and hovered == armorSlot then "Take off" else action.Label
		table.insert(lines, `<font color="#8c8f94">Right-click: {verb}</font>`)
	end
	tooltip.Text = table.concat(lines, "\n")
	tooltip.Position = UDim2.fromOffset(p.X + 16, p.Y + 12)
	tooltip.Visible = true
end

---------------------------------------------------------------- drag and drop

local vestToggle: BindableEvent? = nil
task.spawn(function()
	local vest = script.Parent:WaitForChild("Vest", 30)
	local ev = vest and vest:WaitForChild("VestToggle", 30)
	if ev and ev:IsA("BindableEvent") then
		vestToggle = ev
	end
end)

-- Use an item you carry (Shared/Items Use). from = the container it's shown in. Guns come
-- out / go on your back, vests go on / come off (both here, with their animations); the rest
-- is done by the server after the item's Use.Time. false if it can't be used.
local function useItem(item: any, from: string?): boolean
	local def = item and Items.get(item.id)
	local action = Items.useAction(def)
	if not def or not def.Use or not action or from == "Ground" then
		return false
	end
	local kind = def.Use.Action
	if kind == "Equip" then
		Weapons.equip(if WeaponState.Equipped == item.id then nil else item.id)
	elseif kind == "Wear" then
		if not vestToggle then
			return false
		end
		if from == "Armor" then
			vestToggle:Fire(nil) -- take it off (into the first free spot)
		elseif not state.armor then
			vestToggle:Fire(item.uid)
		else
			return false
		end
	else
		if WeaponState.Dressing or player:GetAttribute("UsingItem") ~= nil then
			return false
		end
		if WeaponState.Equipped then
			-- both hands are needed: the gun goes on your back first
			Weapons.equip(nil)
			task.delay(0.65, function()
				UseRemote:FireServer(item.uid)
			end)
		else
			UseRemote:FireServer(item.uid)
		end
	end
	return true
end

-- where the dragged item would land: green if it fits, red if not
local preview = Instance.new("Frame")
preview.Name = "DropPreview"
preview.BorderSizePixel = 0
preview.BackgroundColor3 = COLORS.Good
preview.BackgroundTransparency = 0.6
preview.ZIndex = 30
preview.Visible = false
local previewStroke = Instance.new("UIStroke")
previewStroke.Thickness = 2
previewStroke.Color = COLORS.Good
previewStroke.Parent = preview
preview.Parent = gui

type Drag = {
	from: string,
	key: any,
	item: any,
	cell: Frame,
	start: Vector2,
	rot: boolean,
	grabX: number, -- which cell of the item (from its top-left) is under the pointer
	grabY: number,
	ghost: Frame?,
	ghostKey: string?,
	plan: any?, -- what letting go here would do (see plan())
	fromActive: boolean?, -- picked up from Active items (the gun in your hands)
}
local drag: Drag? = nil

-- The item you picked up stays in its spot, faded, until you let go.
local function fade(cell: Frame, on: boolean)
	local tile = cell:FindFirstChild("Tile")
	local ic = tile and tile:FindFirstChild("Icon")
	local img = ic and ic:FindFirstChild("Image")
	if ic and ic:IsA("ViewportFrame") then
		ic.ImageTransparency = if on then 0.65 else 0
	elseif ic and ic:IsA("TextLabel") then
		ic.TextTransparency = if on then 0.65 else 0
	elseif img and img:IsA("ImageLabel") then
		img.ImageTransparency = if on then 0.65 else 0
	end
end

local function freezeScrolling(on: boolean)
	for _, sf in scrollers do
		sf.ScrollingEnabled = not on
	end
end

local function cancelDrag()
	freezeScrolling(false)
	if drag and drag.ghost then
		drag.ghost:Destroy()
	end
	if drag then
		fade(drag.cell, false)
	end
	drag = nil
	preview.Visible = false
	ContextActionService:UnbindAction("Inventory_Rotate")
end

-- inside every scrolling area around it too (the rest of a scrolled column is hidden)
local function shown(obj: GuiObject, p: Vector2): boolean
	local a = obj.Parent
	while a and a ~= window do
		if a:IsA("ScrollingFrame") and not inside(a, p) then
			return false
		end
		a = a.Parent
	end
	return true
end

local function hitTest(p: Vector2): Target?
	for _, t in targets do
		if t.frame.Visible and inside(t.frame, p) and (not t.clip or inside(t.clip, p)) and shown(t.frame, p) then
			return t
		end
	end
	return nil
end

local function dragSize(d: Drag): (number, number)
	local w, h = Grid.baseSize(d.item.id)
	if d.rot then
		return h, w
	end
	return w, h
end

local function showPreview(a: Vector2, size: Vector2, ok: boolean)
	preview.Position = UDim2.fromOffset(a.X, a.Y)
	preview.Size = UDim2.fromOffset(size.X, size.Y)
	local color = if ok then COLORS.Good else COLORS.Bad
	preview.BackgroundColor3 = color
	previewStroke.Color = color
	preview.Visible = true
end

-- Work out what dropping at p would do, and show it.
local function plan(d: Drag, p: Vector2): any?
	local t = hitTest(p)
	local def = Items.get(d.item.id)
	if not t or not def then
		preview.Visible = false
		return nil
	end
	local s = scale.Scale
	if t.container == "Ground" then
		local ok = d.from ~= "Ground" and d.from ~= "Armor"
		local a, b = rectOf(groundGrid)
		showPreview(a, b - a, ok)
		return if ok then { action = "drop" } else nil
	end
	if t.container == "Armor" then
		local ok = def.Kind == "Armor" and d.from ~= "Ground" and d.from ~= "Armor" and not state.armor
		local a, b = rectOf(armorSlot)
		showPreview(a, b - a, ok)
		return if ok then { action = "wear" } else nil
	end
	if t.container == "Active" then
		-- a gun dropped here comes out into your hands
		local ok = def.Kind == "Weapon" and d.from ~= "Ground" and d.from ~= "Armor"
		local a, b = rectOf(active)
		showPreview(a, b - a, ok)
		return if ok then { action = "equip" } else nil
	end
	local sameBucket = bucket(d.from) == bucket(t.container) -- moving it doesn't add weight there
	local extra = if sameBucket then 0 else def.Weight * (d.item.count or 1)
	local max = maxOf(t.container)
	if t.container == "Quick" then
		-- one item per quick slot, any size
		local slotNo = t.slot :: number
		local dst = lists.Quick[slotNo]
		local a, b = rectOf(t.frame)
		local ok, merge = false, false
		local weightOk = sameBucket or used(t.container) + extra <= max + 1e-6
		if d.from == "Armor" then
			ok = dst == nil and weightOk
		elseif dst and dst.uid == d.item.uid then
			ok = true -- back where it was
		elseif dst and dst.id == d.item.id and def.Stack > 1 and not dst.data and not d.item.data then
			local roomWeight = if sameBucket then math.huge else math.floor((max - used(t.container)) / math.max(def.Weight, 1e-6))
			ok = math.min(def.Stack - (dst.count or 1), roomWeight) > 0
			merge = true
		elseif dst then
			-- swap: the quick slot's item goes where this one was (the server checks it fits)
			ok = d.from == "Quick" or GRIDS[d.from] ~= nil
		else
			ok = weightOk
		end
		showPreview(a, b - a, ok)
		if not ok then
			return nil
		end
		return { action = if d.from == "Armor" then "takeoff" else "move", to = "Quick", slot = slotNo, merge = merge }
	end
	local g = GRIDS[t.container]
	local list = lists[t.container]
	local slotNo = t.slot :: number
	local w, h = dragSize(d)
	local step = (g.cell + g.gap) * s
	local occ = Grid.occupancy(list, g.cols)
	local fromHere = d.from == t.container
	-- the same item under the pointer: stack onto it
	local under = occ[slotNo]
	local dst = under and list[under]
	if dst and dst.uid ~= d.item.uid and dst.id == d.item.id and def.Stack > 1 and not dst.data and not d.item.data then
		local roomStack = def.Stack - (dst.count or 1)
		local roomWeight = if sameBucket then math.huge else math.floor((max - used(t.container)) / math.max(def.Weight, 1e-6))
		local ok = math.min(roomStack, roomWeight) > 0
		local uc, ur = Grid.pos(under, g.cols)
		local hc, hr = Grid.pos(slotNo, g.cols)
		local a = rectOf(t.frame) - Vector2.new(hc - uc, hr - ur) * step
		local dw, dh = Grid.size(dst)
		showPreview(a, footprint(g, dw, dh) * s, ok)
		return if ok then { action = "move", to = t.container, slot = slotNo, merge = true } else nil
	end
	-- place it with the grabbed cell under the pointer
	local hc, hr = Grid.pos(slotNo, g.cols)
	local ac, ar = hc - d.grabX, hr - d.grabY
	local a = rectOf(t.frame) - Vector2.new(d.grabX, d.grabY) * step
	local inBounds = ac >= 0 and ar >= 0 and ac + w <= g.cols and ar + h <= g.rows
	local anchor = if inBounds then Grid.slot(ac, ar, g.cols) else nil
	local ignore = if fromHere then d.key else nil
	local ok = anchor ~= nil
		and Grid.fits(list, g.cols, g.rows, anchor, w, h, ignore, occ)
		and (sameBucket or used(t.container) + extra <= max + 1e-6)
	showPreview(a, footprint(g, w, h) * s, ok)
	if not ok then
		return nil
	end
	return { action = if d.from == "Armor" then "takeoff" else "move", to = t.container, slot = anchor }
end

local function updateGhost(d: Drag, p: Vector2)
	local w, h = dragSize(d)
	local t = hitTest(p)
	local g = if t and GRIDS[t.container] then GRIDS[t.container] else GRIDS.Inventory
	local size = footprint(g, w, h) * scale.Scale
	local key = `{w}x{h}|{size.X}`
	if not d.ghost or d.ghostKey ~= key then
		if d.ghost then
			d.ghost:Destroy()
		end
		local ghost = Instance.new("Frame")
		ghost.Name = "DragGhost"
		ghost.BackgroundColor3 = COLORS.Slot
		ghost.BackgroundTransparency = 1 -- just the item; the green / red box shows the space
		ghost.BorderSizePixel = 0
		ghost.ZIndex = 40
		local ic = makeIcon(d.item.id, size.X / math.max(1, size.Y), d.rot)
		ic.ZIndex = 41
		ic.Parent = ghost
		ghost.Parent = gui
		d.ghost = ghost
		d.ghostKey = key
	end
	local ghost = d.ghost :: Frame
	local step = (g.cell + g.gap) * scale.Scale
	local cellPx = g.cell * scale.Scale
	ghost.Size = UDim2.fromOffset(size.X, size.Y)
	ghost.Position = UDim2.fromOffset(p.X - (d.grabX * step + cellPx / 2), p.Y - (d.grabY * step + cellPx / 2))
	d.plan = plan(d, p)
end

local lastPoint = Vector2.zero
local function rotateDrag()
	local d = drag
	if not d or not d.ghost then
		return
	end
	d.rot = not d.rot
	local w, h = dragSize(d)
	d.grabX, d.grabY = math.min(d.grabY, w - 1), math.min(d.grabX, h - 1)
	updateGhost(d, lastPoint)
end

local function startGhost(d: Drag)
	tooltip.Visible = false
	fade(d.cell, true)
	-- R turns it (above Reload while dragging)
	ContextActionService:BindActionAtPriority("Inventory_Rotate", function(_, inputState)
		if inputState == Enum.UserInputState.Begin then
			rotateDrag()
		end
		return Enum.ContextActionResult.Sink
	end, false, Enum.ContextActionPriority.High.Value, Enum.KeyCode.R)
end

local function finish(d: Drag)
	local pl = d.plan
	-- the gun dragged out of your hands goes on your back (wherever it's dropped)
	if d.fromActive and not (pl and (pl.action == "equip" or pl.action == "drop")) then
		Weapons.equip(nil)
	end
	if not pl then
		return
	end
	local item = d.item
	local def = Items.get(item.id)
	if pl.action == "equip" then
		if WeaponState.Equipped ~= item.id then
			Weapons.equip(item.id)
		end
	elseif pl.action == "drop" then
		if def and def.Kind == "Weapon" and WeaponState.Equipped == item.id then
			Weapons.equip(nil) -- put it away before it leaves your hands
		end
		MoveRemote:FireServer(d.from, d.key, "Ground", nil, false)
	elseif pl.action == "wear" then
		if vestToggle then
			vestToggle:Fire(item.uid)
		end
	elseif pl.action == "takeoff" then
		if vestToggle then
			vestToggle:Fire(nil, pl.to, pl.slot, d.rot)
		end
	elseif pl.action == "move" then
		if d.from == pl.to and d.key == pl.slot and (item.rot == true) == d.rot then
			return -- dropped back where it was
		end
		MoveRemote:FireServer(d.from, d.key, pl.to, pl.slot, d.rot)
		if d.from == "Ground" then
			local m = droppedModel(d.key)
			if m then
				Pickup.request(m:GetPivot().Position, nil, false) -- bend down for it (just the animation)
			end
		end
		-- show it there straight away (the server's answer follows and wins if it disagrees)
		if not pl.merge and GRIDS[d.from] and GRIDS[pl.to] then
			local src = state.containers[d.from] or {}
			for i, e in src do
				if e.slot == d.key then
					table.remove(src, i)
					e.slot = pl.slot
					e.rot = if d.rot then true else nil
					state.containers[pl.to] = state.containers[pl.to] or {}
					table.insert(state.containers[pl.to], e)
					break
				end
			end
			render()
		end
	end
end

-- The cell under a screen point (tiles of big items spill over other cells, so this goes by
-- position, not by which frame got the click).
local function cellAt(p: Vector2): Frame?
	local t = hitTest(p)
	if t and cellMeta[t.frame :: Frame] then
		return t.frame :: Frame
	end
	return nil
end

-- the item's container for useItem (Active items = the gun in your hands)
local function useFrom(cell: Frame): string?
	local c = cellMeta[cell] and cellMeta[cell].container
	return if c == "Active" then "Quick" else c
end

local lastClick = { uid = nil :: string?, at = 0 }
local DOUBLE_CLICK = 0.35

UserInputService.InputBegan:Connect(function(input)
	if input.UserInputType == Enum.UserInputType.MouseButton2 and gui.Enabled and not drag then
		local cell = cellAt(point(input))
		local item = cell and cellItem[cell]
		if cell and item then
			useItem(item, useFrom(cell))
		end
		return
	end
	if input.UserInputType ~= Enum.UserInputType.MouseButton1 and input.UserInputType ~= Enum.UserInputType.Touch then
		return
	end
	if not gui.Enabled or drag then
		return
	end
	local p = point(input)
	local cell = cellAt(p)
	local item = cell and cellItem[cell]
	if not cell or not item then
		return
	end
	-- double-click / double-tap: use it
	local now = os.clock()
	if item.uid and lastClick.uid == item.uid and now - lastClick.at < DOUBLE_CLICK then
		lastClick.uid = nil
		useItem(item, useFrom(cell))
		return
	end
	lastClick.uid, lastClick.at = item.uid, now
	local meta = cellMeta[cell]
	local w, h = Grid.size(item)
	local key, from, gx, gy = nil, meta.container, (w - 1) // 2, (h - 1) // 2
	local source = cell
	local fromActive = false
	if from == "Active" then
		-- the gun in your hands: drag the real item (where it's kept in the bag)
		local ref = activeRef
		if not ref then
			return
		end
		from, key, fromActive = ref.container, ref.slot, true
	elseif from == "Quick" then
		key = meta.slot
	elseif GRIDS[from] then
		local anchor = cellAnchor[cell] :: number
		local g = GRIDS[from]
		local cc, cr = Grid.pos(meta.slot :: number, g.cols)
		local ac, ar = Grid.pos(anchor, g.cols)
		key, gx, gy = anchor, cc - ac, cr - ar
		source = cells[from][anchor]
	elseif from == "Ground" then
		key = item.uid
	else
		key = "Armor"
	end
	drag = {
		from = from,
		key = key,
		item = item,
		cell = source,
		start = p,
		rot = item.rot == true,
		grabX = gx,
		grabY = gy,
		fromActive = fromActive,
	}
	freezeScrolling(true) -- a finger dragging an item mustn't scroll the list under it
end)

UserInputService.InputChanged:Connect(function(input)
	if input.UserInputType ~= Enum.UserInputType.MouseMovement and input.UserInputType ~= Enum.UserInputType.Touch then
		return
	end
	local p = point(input)
	lastPoint = p
	if gui.Enabled and not drag then
		hovered = cellAt(p)
		showTip(p)
	end
	local d = drag
	if not d then
		return
	end
	if not d.ghost and (p - d.start).Magnitude > 5 then
		startGhost(d)
		updateGhost(d, p)
	elseif d.ghost then
		updateGhost(d, p)
	end
end)

UserInputService.InputEnded:Connect(function(input)
	if input.UserInputType ~= Enum.UserInputType.MouseButton1 and input.UserInputType ~= Enum.UserInputType.Touch then
		return
	end
	local d = drag
	if not d then
		return
	end
	if d.ghost then
		updateGhost(d, point(input))
		finish(d)
	end
	cancelDrag()
end)

---------------------------------------------------------------- fit, live bars, open / close
local function fit()
	local cam = workspace.CurrentCamera
	if not cam then
		return
	end
	local v = cam.ViewportSize
	local s = math.min(v.Y * HEIGHT_SHARE / H, v.X * WIDTH_SHARE / W)
	local shownH = H
	local top = 0
	if s < COMPACT_BELOW then
		-- phone: fill the width, start under the top bar, scroll the columns
		top = GuiService:GetGuiInset().Y
		s = math.min(1, v.X * COMPACT_WIDTH_SHARE / W)
		shownH = math.min(H, math.floor((v.Y - top - 8) / s))
	end
	scale.Scale = s
	window.Size = UDim2.fromOffset(W, shownH)
	window.Position = UDim2.new(0.5, 0, 0.5, top / 2)
	window.ClipsDescendants = shownH < H
	left.Size = UDim2.fromOffset(SIDE_W, shownH)
	mid.Size = UDim2.fromOffset(MID_W, shownH)
	inventoryGrid.Size = UDim2.fromOffset(SIDE_W, shownH - TOP - PAD)
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

-- The middle picture: a still copy of your character in the idle pose, facing the camera.
-- The copy is posed by playing the idle animation (frozen on its first frame) on it out of
-- sight in the workspace for a moment, then moved, anchored, into the ViewportFrame, so it
-- never moves. Rebuilt when the window opens and when the vest / a gun / clothes change.
local PORTRAIT_FOV = 16
local IDLE_FALLBACK = "rbxassetid://507766388" -- Roblox's default R15 idle
local POSE_SPOT = CFrame.new(0, 3000, 0) -- where the copy is posed, far out of sight

-- every joint put at rest (no animation), as a starting pose
local function standStraight(model: Model, root: BasePart)
	-- every joint as (part0, part1, offset of part1 from part0 at rest)
	local links: { [BasePart]: { { other: BasePart, offset: CFrame } } } = {}
	local function link(a: BasePart, b: BasePart, offset: CFrame)
		links[a] = links[a] or {}
		links[b] = links[b] or {}
		table.insert(links[a], { other = b, offset = offset })
		table.insert(links[b], { other = a, offset = offset:Inverse() })
	end
	for _, j in model:GetDescendants() do
		if j:IsA("JointInstance") and j.Part0 and j.Part1 then
			link(j.Part0, j.Part1, j.C0 * j.C1:Inverse())
		elseif j:IsA("WeldConstraint") and j.Part0 and j.Part1 then
			link(j.Part0, j.Part1, j.Part0.CFrame:ToObjectSpace(j.Part1.CFrame))
		elseif (j:IsA("RigidConstraint") or j:IsA("AnimationConstraint")) and j.Attachment0 and j.Attachment1 then
			local a0, a1 = j.Attachment0 :: Attachment, j.Attachment1 :: Attachment
			local p0, p1 = a0.Parent, a1.Parent
			if p0 and p1 and p0:IsA("BasePart") and p1:IsA("BasePart") then
				link(p0, p1, a0.CFrame * a1.CFrame:Inverse())
			end
		end
	end
	local seen = { [root] = true }
	local queue = { root }
	local i = 1
	while queue[i] do
		local part = queue[i]
		i += 1
		for _, l in links[part] or {} do
			if not seen[l.other] then
				seen[l.other] = true
				l.other.CFrame = part.CFrame * l.offset
				table.insert(queue, l.other)
			end
		end
	end
end

local function idleAnimationId(character: Model): string
	local animate = character:FindFirstChild("Animate")
	local idle = animate and animate:FindFirstChild("idle")
	local anim = idle and (idle:FindFirstChild("Animation1") or idle:FindFirstChildWhichIsA("Animation"))
	if anim and anim:IsA("Animation") and anim.AnimationId ~= "" then
		return anim.AnimationId
	end
	return IDLE_FALLBACK
end

local portraitSeq = 0
local function refreshPortrait()
	portraitSeq += 1
	local seq = portraitSeq
	local character = player.Character
	local root = character and character:FindFirstChild("HumanoidRootPart")
	if not character or not root or not root:IsA("BasePart") then
		portrait:ClearAllChildren()
		return
	end
	local idleId = idleAnimationId(character)
	local wasArchivable = character.Archivable
	character.Archivable = true
	local copy = character:Clone()
	character.Archivable = wasArchivable
	if not copy then
		return
	end
	for _, d in copy:GetDescendants() do
		if
			d:IsA("BaseScript")
			or d:IsA("ModuleScript")
			or d:IsA("Sound")
			or d:IsA("BillboardGui")
			or d:IsA("ProximityPrompt")
			or d:IsA("ForceField")
		then
			d:Destroy()
		end
	end
	-- a gun in the hand would stick out of the idle arm; one on the back stays
	for _, d in copy:GetChildren() do
		if d:IsA("Tool") or (d.Name == "Gun" and d:GetAttribute("On") ~= "UpperTorso") then
			d:Destroy()
		end
	end
	local copyRoot = copy:FindFirstChild("HumanoidRootPart")
	if not copyRoot or not copyRoot:IsA("BasePart") then
		copy:Destroy()
		return
	end
	copy.PrimaryPart = copyRoot
	standStraight(copy, copyRoot)
	copy:PivotTo(POSE_SPOT)
	local parts: { BasePart } = {}
	for _, d in copy:GetDescendants() do
		if d:IsA("BasePart") then
			table.insert(parts, d)
			d.Anchored = d == copyRoot
			d.CanCollide = false
			d.CanQuery = false
			d.CanTouch = false
			d.Massless = true
			d.LocalTransparencyModifier = 1 -- hidden while it's being posed
		end
	end
	copyRoot.Transparency = 1
	local humanoid = copy:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
		humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
		humanoid.EvaluateStateMachine = false
	end

	-- pose: the idle animation, frozen on its first frame
	copy.Parent = workspace
	local track: AnimationTrack? = nil
	if humanoid then
		local animator = humanoid:FindFirstChildOfClass("Animator")
		if not animator then
			animator = Instance.new("Animator")
			assert(animator).Parent = humanoid
		end
		local anim = Instance.new("Animation")
		anim.AnimationId = idleId
		local ok, t = pcall(function()
			return (animator :: Animator):LoadAnimation(anim)
		end)
		if ok and t then
			track = t
			t:Play(0, 1, 0)
			local waited = 0
			while t.Length <= 0 and waited < 3 do -- still loading
				waited += task.wait()
			end
		end
	end
	for _ = 1, 3 do -- let the pose land on the parts
		task.wait()
	end
	if seq ~= portraitSeq or not copy.Parent then
		copy:Destroy()
		return
	end

	-- freeze it: every part anchored where the pose put it, next to the root at the origin
	local rootCf = copyRoot.CFrame
	local pose: { [BasePart]: CFrame } = {}
	for _, part in parts do
		pose[part] = rootCf:ToObjectSpace(part.CFrame)
	end
	if track then
		track:Stop(0)
	end
	copy.Parent = nil
	for _, part in parts do
		part.Anchored = true
		part.CFrame = pose[part]
		part.LocalTransparencyModifier = 0
	end
	portrait:ClearAllChildren()
	copy.Parent = portrait

	-- frame the whole body: camera in front (on -Z, the way it faces) looking back at it
	local bounds, size = copy:GetBoundingBox()
	local cam = Instance.new("Camera")
	cam.FieldOfView = PORTRAIT_FOV
	local aspect = characterBox.Size.X.Offset / characterBox.Size.Y.Offset
	local tanV = math.tan(math.rad(PORTRAIT_FOV / 2))
	local dist = math.max(size.Y / 2 / tanV, size.X / 2 / (tanV * aspect)) * 1.08 + size.Z / 2
	local centre = bounds.Position
	cam.CFrame = CFrame.lookAt(centre + Vector3.new(0, 0, -dist), centre)
	cam.Parent = portrait
	portrait.CurrentCamera = cam
end

local portraitQueued = false
local function queuePortrait()
	if portraitQueued or not gui.Enabled then
		return
	end
	portraitQueued = true
	task.delay(0.25, function()
		portraitQueued = false
		if gui.Enabled then
			refreshPortrait()
		end
	end)
end

local charConns: { RBXScriptConnection } = {}
local function onCharacter(character: Model)
	for _, c in charConns do
		c:Disconnect()
	end
	table.clear(charConns)
	-- vest / gun / clothes put on or taken off
	local function looks(d: Instance)
		if d:IsA("Accessory") or d:IsA("Clothing") or d:IsA("Model") then
			queuePortrait()
		end
	end
	table.insert(charConns, character.DescendantAdded:Connect(looks))
	table.insert(charConns, character.DescendantRemoving:Connect(looks))
	queuePortrait()
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if not humanoid then
		return
	end
	local function update()
		setBar(healthFill, healthValue, humanoid.Health, humanoid.MaxHealth)
		setBar(armorFill, armorValue, humanoid:GetAttribute("Armor") or 0, humanoid:GetAttribute("MaxArmor") or 0)
		if state.armor then
			setTile(armorSlot, state.armor, nil, nil, nil, true) -- the worn vest's armor %
		end
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
		scanGround()
		render()
		task.spawn(refreshPortrait)
	else
		cancelDrag()
		hovered = nil
		tooltip.Visible = false
	end
	gui.Enabled = open
end
close.Activated:Connect(function()
	setOpen(false)
end)

-- the Ground list follows you while the window is open
task.spawn(function()
	while true do
		task.wait(0.3)
		if gui.Enabled then
			scanGround()
			if not drag then
				renderGround()
			end
		end
	end
end)

gui.Parent = player:WaitForChild("PlayerGui")

-- N toggles the window (Dev's pick; I is Roblox's camera zoom key). Bound at High priority and
-- sinks the key. The InputBegan fallback catches N even if something else ever takes it first;
-- the debounce keeps the two from toggling twice on one press.
local lastToggle = 0
local function toggle()
	local now = os.clock()
	if now - lastToggle < 0.2 then
		return
	end
	lastToggle = now
	setOpen(not gui.Enabled)
end

ContextActionService:BindActionAtPriority("Inventory_Toggle", function(_, inputState)
	if inputState == Enum.UserInputState.Begin then
		toggle()
	end
	return Enum.ContextActionResult.Sink
end, false, Enum.ContextActionPriority.High.Value, Enum.KeyCode.N)
-- the Bag tile on the right rail (RightRail) toggles it through this attribute; phones use
-- that tile instead of a separate touch button
gui:GetAttributeChangedSignal("ToggleRequest"):Connect(toggle)

UserInputService.InputBegan:Connect(function(input)
	if input.KeyCode == Enum.KeyCode.N and UserInputService:GetFocusedTextBox() == nil then
		toggle()
	end
end)

---------------------------------------------------------------- quick slots: keys 1-3 + the bar

-- Use quick slot i: a gun there comes out (or goes on your back if it's in your hands),
-- food / first aid gets used, a vest goes on.
local function useQuick(i: number): boolean
	local e = lists.Quick[i]
	if not e then
		return false
	end
	return useItem(e, "Quick")
end

local QUICK_KEYS = {
	{ Enum.KeyCode.One, Enum.KeyCode.DPadLeft },
	{ Enum.KeyCode.Two, Enum.KeyCode.DPadUp },
	{ Enum.KeyCode.Three, Enum.KeyCode.DPadRight },
}
for i = 1, QUICK do
	local keys = QUICK_KEYS[i]
	if keys then
		ContextActionService:BindActionAtPriority(`Inventory_Quick{i}`, function(_, inputState)
			if inputState == Enum.UserInputState.Begin then
				useQuick(i)
			end
			return Enum.ContextActionResult.Sink
		end, false, Enum.ContextActionPriority.High.Value, table.unpack(keys))
	end
end

-- the quick bar: the 3 quick slots at the bottom of the screen (tap one on a phone), the one
-- in your hands outlined. Hidden while the window is open or you're driving.
local bar = Instance.new("ScreenGui")
bar.Name = "QuickBar"
bar.ResetOnSpawn = false
bar.IgnoreGuiInset = true
bar.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
bar.DisplayOrder = 5
local BAR_CELL, BAR_GAP = 58, 6
local row = Instance.new("Frame")
row.Name = "Row"
row.AnchorPoint = Vector2.new(0.5, 1)
row.Position = UDim2.new(0.5, 0, 1, -12)
row.Size = UDim2.fromOffset(QUICK * BAR_CELL + (QUICK - 1) * BAR_GAP, BAR_CELL)
row.BackgroundTransparency = 1
row.Parent = bar

type BarSlot = { button: TextButton, stroke: UIStroke, holder: Frame, count: TextLabel, key: string? }
local barSlots: { BarSlot } = {}
for i = 1, QUICK do
	local b = Instance.new("TextButton")
	b.Name = `Slot{i}`
	b.AutoButtonColor = false
	b.Text = ""
	b.Position = UDim2.fromOffset((i - 1) * (BAR_CELL + BAR_GAP), 0)
	b.Size = UDim2.fromOffset(BAR_CELL, BAR_CELL)
	b.BackgroundColor3 = COLORS.Window
	b.BackgroundTransparency = 0.3
	b.BorderSizePixel = 0
	local stroke = Instance.new("UIStroke")
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Thickness = 2
	stroke.Color = COLORS.Text
	stroke.Transparency = 1
	stroke.Parent = b
	local holder = box(b, "Item", 4, 4, BAR_CELL - 8, BAR_CELL - 8)
	local n = label(b, "Number", tostring(i), 4, 2, 14, 14, 12, COLORS.Dim, BOLD)
	n.ZIndex = 3
	local count = label(b, "Count", "", BAR_CELL - 44, BAR_CELL - 16, 40, 14, 12, COLORS.Text, BOLD, Enum.TextXAlignment.Right)
	count.TextStrokeTransparency = 0.5
	count.ZIndex = 3
	b.Activated:Connect(function()
		useQuick(i)
	end)
	b.Parent = row
	barSlots[i] = { button = b, stroke = stroke, holder = holder, count = count, key = nil }
end
bar.Enabled = false
bar.Parent = player:WaitForChild("PlayerGui")

local function renderBar()
	for i, slotUi in barSlots do
		local e = lists.Quick[i]
		local key = if e then e.id else ""
		if slotUi.key ~= key then
			slotUi.key = key
			slotUi.holder:ClearAllChildren()
			if e then
				makeIcon(e.id, 1, false).Parent = slotUi.holder
			end
		end
		local n = if e then e.count or 1 else 0
		slotUi.count.Text = if n > 1 then tostring(n) else ""
		slotUi.stroke.Transparency = if e and WeaponState.Equipped == e.id then 0.1 else 1
	end
end
onQuickChanged = renderBar
renderBar()

---------------------------------------------------------------- using an item: bar + notices

-- While the server runs a timed use (player attributes UsingItem / UseStart / UseEnd, set by
-- Server/Inventory), a bar fills above the quick bar. Refusals ("Already at full health")
-- show there for a moment too.
local useGui = Instance.new("ScreenGui")
useGui.Name = "ItemUse"
useGui.ResetOnSpawn = false
useGui.IgnoreGuiInset = true
useGui.DisplayOrder = 6
local USE_W = 220
local useBox = Instance.new("Frame")
useBox.Name = "Bar"
useBox.AnchorPoint = Vector2.new(0.5, 1)
useBox.Position = UDim2.new(0.5, 0, 1, -12 - BAR_CELL - 10)
useBox.Size = UDim2.fromOffset(USE_W, 26)
useBox.BackgroundColor3 = COLORS.Window
useBox.BackgroundTransparency = 0.25
useBox.BorderSizePixel = 0
useBox.Visible = false
useBox.Parent = useGui
local useFill = box(useBox, "Fill", 0, 0, 0, 26, COLORS.Good, 0.35)
local useText = label(useBox, "Text", "", 0, 0, USE_W, 26, 13, COLORS.Text, BOLD, Enum.TextXAlignment.Center)
useText.ZIndex = 2
useText.TextStrokeTransparency = 0.6
useGui.Parent = player:WaitForChild("PlayerGui")

-- the use animation (Shared/Items Use.Anim), stretched to the use's length; the server holds
-- the item's model in the hand meanwhile
local AnimIds = require(Shared:WaitForChild("AnimIds"))
local useTrack: AnimationTrack? = nil
local function stopUseAnim()
	if useTrack then
		useTrack:Stop(0.2)
		useTrack = nil
	end
end
local function playUseAnim()
	stopUseAnim()
	local def = Items.get(player:GetAttribute("UsingItemId"))
	local animId = def and def.Use and def.Use.Anim and (AnimIds :: any)[def.Use.Anim]
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local animator = humanoid and humanoid:FindFirstChildOfClass("Animator")
	if not def or not animId or not animator then
		return
	end
	local anim = Instance.new("Animation")
	anim.AnimationId = animId
	local track = animator:LoadAnimation(anim)
	track.Priority = Enum.AnimationPriority.Action3
	track.Looped = false
	useTrack = track
	track:Play(0.15)
	task.spawn(function()
		local t0 = os.clock()
		while track.Length <= 0 and os.clock() - t0 < 3 do
			task.wait()
		end
		local time = (def.Use :: any).Time or 0
		if useTrack == track and track.Length > 0 and time > 0 then
			track:AdjustSpeed(track.Length / time)
		end
	end)
end
player:GetAttributeChangedSignal("UsingItemId"):Connect(function()
	if player:GetAttribute("UsingItemId") then
		playUseAnim()
	else
		stopUseAnim()
	end
end)
player.CharacterAdded:Connect(stopUseAnim)

local noticeUntil = 0
NoticeRemote.OnClientEvent:Connect(function(text)
	if typeof(text) == "string" then
		useText.Text = text
		useFill.Size = UDim2.fromOffset(0, 26)
		noticeUntil = os.clock() + 1.8
		useBox.Visible = true
	end
end)

RunService.RenderStepped:Connect(function()
	local name = player:GetAttribute("UsingItem")
	local t0, t1 = player:GetAttribute("UseStart"), player:GetAttribute("UseEnd")
	if typeof(name) == "string" and typeof(t0) == "number" and typeof(t1) == "number" then
		local share = if t1 > t0 then math.clamp((workspace:GetServerTimeNow() - t0) / (t1 - t0), 0, 1) else 1
		useText.Text = name
		useFill.Size = UDim2.fromOffset(math.floor(USE_W * share), 26)
		useBox.Visible = true
	elseif os.clock() < noticeUntil then
		useBox.Visible = true
	else
		useBox.Visible = false
	end
end)

-- Active items and the bar follow the gun in your hands (it also changes on respawn, in cars...)
RunService.Heartbeat:Connect(function()
	if WeaponState.Equipped ~= shownEquipped then
		renderActive()
		renderBar()
	end
	local show = not gui.Enabled and not WeaponState.InVehicle
	if bar.Enabled ~= show then
		bar.Enabled = show
	end
end)
