--[[
	Inventory window (copied from Dev's reference screenshot). N opens / closes it (phone: Bag
	button). Roblox's own backpack bar is turned off.

	The server owns the items (Server/Inventory/InventoryService) and sends them here; this
	draws them and asks the server to move them. Items cover several cells (Shared/Items Cells:
	vest 2 x 2, carbine 4 x 1). While dragging, a green box shows where it lands (red: it doesn't
	fit or is too heavy) and R turns it 90 degrees. Drag an item:
	  - into Inventory / Backpack: puts it there (or onto a stack of the same item)
	  - onto Ground: drops it in front of you (a gun in your hands is put away first)
	  - from Ground into a slot: picks it up (also: walk up to it and hold E)
	  - a vest onto the Armor slot: puts it on (the vest animation, like V); the worn vest
	    dragged into a slot takes it off
	Moves that would go over a weight limit are refused by the server. Hovering an item shows
	its name and weight. Item icons are the real 3D models (ReplicatedStorage.ItemModels).

	The window is drawn at a fixed design size (W x H) and a UIScale fits it to 94% of the
	screen height (or 96% of the width on narrow screens).
	Equipment slots around the character, the Bag slot and quick slots 1-3 are layout only.
]]

local ContextActionService = game:GetService("ContextActionService")
local GuiService = game:GetService("GuiService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
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

local Remotes = ReplicatedStorage:WaitForChild("InventoryRemotes")
local MoveRemote = Remotes:WaitForChild("Move") :: RemoteEvent
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
	return sf
end

-- column dividers
box(window, "DividerLeft", MID_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)
box(window, "DividerRight", RIGHT_X - 8, TOP, 1, BOTTOM - TOP, COLORS.Line, 0.6)

---------------------------------------------------------------- left: ground + backpack
local left = box(window, "Left", LEFT_X, 0, SIDE_W, H)
label(left, "Title", "Ground", 0, 10, SIDE_W, 26, 16, COLORS.Text, BOLD)
local groundGrid = grid(left, "Ground", 0, TOP, SIDE_W, 320, 4, 56, 6, 20)
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
grid(left, "Backpack", 0, 422, SIDE_W, BOTTOM - 422, GRIDS.Backpack.cols, 56, 6, GRIDS.Backpack.cols * GRIDS.Backpack.rows)

---------------------------------------------------------------- middle: character + equipment
local mid = box(window, "Middle", MID_X, 0, MID_W, H)
local nameLabel = label(mid, "PlayerName", "", 0, 10, MID_W, 26, 16, COLORS.Text, BOLD, Enum.TextXAlignment.Center)

-- 4 equipment slots down each side of the character, 5 under it (layout only for now)
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

-- active items (things in use right now)
local active = box(mid, "ActiveItems", 0, 372, MID_W, 126, COLORS.Panel, 0.5)
icon(active, "Icon", IconIds.Hands, MID_W / 2 - 18, 30, 36, COLORS.Icon)
label(active, "Label", "Active items", 0, 66, MID_W, 20, 13, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)

-- armor + bag slots
local armorSlot = slot(mid, "ArmorSlot", 0, 506, 130, 96)
local armorEmptyIcon = icon(armorSlot, "EmptyIcon", IconIds.Vest, 65 - 21, 20, 42, COLORS.Icon)
local armorEmptyLabel = label(armorSlot, "Label", "Armor", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
cellMeta[armorSlot] = { container = "Armor" }
table.insert(targets, { frame = armorSlot, container = "Armor" })

local bagSlot = slot(mid, "BagSlot", 138, 506, 130, 96)
icon(bagSlot, "EmptyIcon", IconIds.Backpack, 65 - 20, 20, 40, COLORS.Icon)
label(bagSlot, "Label", "Bag", 0, 70, 130, 22, 12, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)

-- quick slots 1-3 (layout only for now)
for i = 0, 2 do
	local q = slot(mid, `Quick{i + 1}`, i * 92, 610, 84, BOTTOM - 610)
	label(q, "Number", tostring(i + 1), 0, 2, 84, 14, 11, COLORS.Dim, REGULAR, Enum.TextXAlignment.Center)
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

-- The item's 3D model in a transparent ViewportFrame, framed to fill a tile of this aspect
-- (width / height); turned items are drawn turned. Its name until the model has loaded.
local function makeIcon(id: string, aspect: number, rot: boolean?): GuiObject
	local def = Items.get(id)
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
	-- fit the bounding box corners into the view
	local maxX, maxY, maxZ = 0, 0, 0
	for _, sx in { -1, 1 } do
		for _, sy in { -1, 1 } do
			for _, sz in { -1, 1 } do
				local corner = cf:VectorToWorldSpace(Vector3.new(sx * size.X, sy * size.Y, sz * size.Z) / 2)
				local v = turn:VectorToObjectSpace(corner)
				maxX = math.max(maxX, math.abs(v.X))
				maxY = math.max(maxY, math.abs(v.Y))
				maxZ = math.max(maxZ, v.Z)
			end
		end
	end
	local tanV = math.tan(math.rad(cam.FieldOfView / 2))
	local dist = math.max(maxX / (tanV * aspect), maxY / tanV) * 1.15 + maxZ
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

local state: any = { containers = { Inventory = {}, Backpack = {} }, armor = false }
local lists: { [string]: { [number]: any } } = { Inventory = {}, Backpack = {} } -- top-left slot -> item
local ground: { any } = {}

local function weightOf(list: { [any]: any }): number
	local w = 0
	for _, e in list do
		local def = Items.get(e.id)
		w += (if def then def.Weight else 0) * (e.count or 1)
	end
	return w
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
	invWeight.Text = string.format("%.2f / %d kg", weightOf(lists.Inventory), CFG.MaxWeight)
	backpackWeight.Text = string.format("%.2f / %d kg", weightOf(lists.Backpack), CFG.BackpackMaxWeight)
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
	table.insert(lines, string.format("%.2f kg  ·  %d x %d", def.Weight * n, w, h))
	local share = armorShare(item, hovered == armorSlot)
	if share then
		table.insert(lines, `Armor {math.floor(share * 100 + 0.5)}%`)
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
}
local drag: Drag? = nil

local function cancelDrag()
	if drag and drag.ghost then
		drag.ghost:Destroy()
	end
	if drag then
		local tile = drag.cell:FindFirstChild("Tile") :: GuiObject?
		if tile then
			tile.Visible = true
		end
	end
	drag = nil
	preview.Visible = false
	ContextActionService:UnbindAction("Inventory_Rotate")
end

local function hitTest(p: Vector2): Target?
	for _, t in targets do
		if t.frame.Visible and inside(t.frame, p) and (not t.clip or inside(t.clip, p)) then
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
	local g = GRIDS[t.container]
	local list = lists[t.container]
	local slotNo = t.slot :: number
	local w, h = dragSize(d)
	local step = (g.cell + g.gap) * s
	local occ = Grid.occupancy(list, g.cols)
	local fromHere = d.from == t.container
	local extra = if fromHere then 0 else def.Weight * (d.item.count or 1)
	local max = if t.container == "Inventory" then CFG.MaxWeight else CFG.BackpackMaxWeight
	-- the same item under the pointer: stack onto it
	local under = occ[slotNo]
	local dst = under and list[under]
	if dst and dst.uid ~= d.item.uid and dst.id == d.item.id and def.Stack > 1 and not dst.data and not d.item.data then
		local roomStack = def.Stack - (dst.count or 1)
		local roomWeight = if fromHere then math.huge else math.floor((max - weightOf(list)) / math.max(def.Weight, 1e-6))
		local ok = math.min(roomStack, roomWeight) > 0
		local uc, ur = Grid.pos(under, g.cols)
		local hc, hr = Grid.pos(slotNo, g.cols)
		local a = rectOf(t.frame) - Vector2.new(hc - uc, hr - ur) * step
		local dw, dh = Grid.size(dst)
		showPreview(a, footprint(g, dw, dh) * s, ok)
		return if ok then { action = "move", to = t.container, slot = slotNo } else nil
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
		and (fromHere or weightOf(list) + extra <= max + 1e-6)
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
		ghost.BackgroundTransparency = 0.5
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
	local tile = d.cell:FindFirstChild("Tile") :: GuiObject?
	if tile and d.from ~= "Ground" then
		tile.Visible = false -- it's in your hand now
	end
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
	if not pl then
		return
	end
	local item = d.item
	local def = Items.get(item.id)
	if pl.action == "drop" then
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

UserInputService.InputBegan:Connect(function(input)
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
	local meta = cellMeta[cell]
	local w, h = Grid.size(item)
	local key, from, gx, gy = nil, meta.container, (w - 1) // 2, (h - 1) // 2
	local source = cell
	if GRIDS[from] then
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
	}
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
end, true, Enum.ContextActionPriority.High.Value, Enum.KeyCode.N)
ContextActionService:SetTitle("Inventory_Toggle", "Bag")
ContextActionService:SetPosition("Inventory_Toggle", UDim2.new(1, -245, 1, -210))

UserInputService.InputBegan:Connect(function(input)
	if input.KeyCode == Enum.KeyCode.N and UserInputService:GetFocusedTextBox() == nil then
		toggle()
	end
end)
