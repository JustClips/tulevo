-- Top-right strip (GTA RP server style):
--
--   [cart]   TULEVO
--            [people] 12 / 30 online
--
-- The cart is the Store button (click/tap, or F4); it opens the Store window. The text is
-- the game name (Config.GameName) and how many players are on this server right now, out of
-- the server's max. Sits under Roblox's own top buttons (CoreUISafeInsets) and scales with the
-- rest of the HUD (HudLayout). The ammo counter and the admin DEBUG button sit under it.
--
-- More store-style buttons: add a row to BUTTONS (icon from Shared/IconIds, made with
-- art/icons/gen.py + proc.py + tools/upload_icons.py).
-- Store contents: fill the window's Body frame (PlayerGui.Store.Window.Body).
local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local IconIds = require(Shared:WaitForChild("IconIds"))
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))
local MouseLook = require(script.Parent:WaitForChild("Movement"):WaitForChild("MouseLook"))

local player = Players.LocalPlayer

local COLORS = {
	Button = Color3.fromRGB(18, 20, 24),
	ButtonHover = Color3.fromRGB(40, 44, 52),
	Window = Color3.fromRGB(18, 20, 24),
	Header = Color3.fromRGB(28, 31, 37),
	Close = Color3.fromRGB(150, 50, 46),
	Main = Color3.fromRGB(245, 245, 245),
	Dim = Color3.fromRGB(185, 190, 196),
	Accent = Color3.fromRGB(110, 200, 110),
	Stroke = Color3.fromRGB(0, 0, 0),
}
local REGULAR = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Regular)
local BOLD = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Bold)

local STORE_KEY = Enum.KeyCode.F4
local TR = HudLayout.TopRight
local BTN = TR.Height -- square buttons, as tall as the strip

local gui = Instance.new("ScreenGui")
gui.Name = "TopRightHud"
gui.ResetOnSpawn = false
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.Parent = player:WaitForChild("PlayerGui")

local root = Instance.new("Frame")
root.Name = "Root"
root.AnchorPoint = Vector2.new(1, 0)
root.Position = UDim2.new(1, -TR.Right, 0, TR.Top)
root.Size = UDim2.fromOffset(0, BTN)
root.AutomaticSize = Enum.AutomaticSize.X
root.BackgroundTransparency = 1
root.Parent = gui

local uiScale = Instance.new("UIScale")
uiScale.Parent = root

local list = Instance.new("UIListLayout")
list.FillDirection = Enum.FillDirection.Horizontal
list.HorizontalAlignment = Enum.HorizontalAlignment.Right
list.VerticalAlignment = Enum.VerticalAlignment.Center
list.SortOrder = Enum.SortOrder.LayoutOrder
list.Padding = UDim.new(0, 10)
list.Parent = root

local function text(parent: Instance, size: number, font: Font, color: Color3): TextLabel
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.AutomaticSize = Enum.AutomaticSize.X
	t.Size = UDim2.fromOffset(0, size)
	t.FontFace = font
	t.TextSize = size
	t.TextColor3 = color
	t.TextStrokeColor3 = COLORS.Stroke
	t.TextStrokeTransparency = 0.6
	t.TextXAlignment = Enum.TextXAlignment.Right
	t.Text = ""
	t.Parent = parent
	return t
end

---------------------------------------------------------------- buttons

local buttonRow = Instance.new("Frame")
buttonRow.Name = "Buttons"
buttonRow.LayoutOrder = 1
buttonRow.BackgroundTransparency = 1
buttonRow.AutomaticSize = Enum.AutomaticSize.X
buttonRow.Size = UDim2.fromOffset(0, BTN)
buttonRow.Parent = root

local rowList = Instance.new("UIListLayout")
rowList.FillDirection = Enum.FillDirection.Horizontal
rowList.SortOrder = Enum.SortOrder.LayoutOrder
rowList.Padding = UDim.new(0, 6)
rowList.Parent = buttonRow

local keyHints: { TextLabel } = {}

-- One square, solid, sharp-cornered icon button. key: shown in the corner on keyboards.
local function iconButton(order: number, name: string, image: string, key: string?, onClick: () -> ())
	local b = Instance.new("ImageButton")
	b.Name = name
	b.LayoutOrder = order
	b.Size = UDim2.fromOffset(BTN, BTN)
	b.BackgroundColor3 = COLORS.Button
	b.BackgroundTransparency = 0.15
	b.BorderSizePixel = 0
	b.AutoButtonColor = false
	b.Image = ""
	b.Parent = buttonRow

	local img = Instance.new("ImageLabel")
	img.AnchorPoint = Vector2.new(0.5, 0.5)
	img.Position = UDim2.fromScale(0.5, 0.5)
	img.Size = UDim2.fromOffset(BTN - 18, BTN - 18)
	img.BackgroundTransparency = 1
	img.Image = image
	img.ImageColor3 = COLORS.Main
	img.ScaleType = Enum.ScaleType.Fit
	img.Parent = b

	if key then
		local k = Instance.new("TextLabel")
		k.Name = "Key"
		k.AnchorPoint = Vector2.new(1, 1)
		k.Position = UDim2.new(1, -2, 1, 0)
		k.Size = UDim2.fromOffset(20, 12)
		k.BackgroundTransparency = 1
		k.FontFace = BOLD
		k.TextSize = 11
		k.TextColor3 = COLORS.Dim
		k.TextXAlignment = Enum.TextXAlignment.Right
		k.Text = key
		k.Parent = b
		table.insert(keyHints, k)
	end

	b.MouseEnter:Connect(function()
		b.BackgroundColor3 = COLORS.ButtonHover
	end)
	b.MouseLeave:Connect(function()
		b.BackgroundColor3 = COLORS.Button
	end)
	b.Activated:Connect(onClick)
	return b
end

---------------------------------------------------------------- name + players online

local info = Instance.new("Frame")
info.Name = "Info"
info.LayoutOrder = 2
info.BackgroundTransparency = 1
info.AutomaticSize = Enum.AutomaticSize.X
info.Size = UDim2.fromOffset(0, BTN)
info.Parent = root

local infoList = Instance.new("UIListLayout")
infoList.FillDirection = Enum.FillDirection.Vertical
infoList.HorizontalAlignment = Enum.HorizontalAlignment.Right
infoList.VerticalAlignment = Enum.VerticalAlignment.Center
infoList.SortOrder = Enum.SortOrder.LayoutOrder
infoList.Padding = UDim.new(0, 1)
infoList.Parent = info

local nameText = text(info, 24, BOLD, COLORS.Main)
nameText.LayoutOrder = 1
nameText.Text = string.upper(Config.GameName or "Tulevo")

local onlineRow = Instance.new("Frame")
onlineRow.LayoutOrder = 2
onlineRow.BackgroundTransparency = 1
onlineRow.AutomaticSize = Enum.AutomaticSize.X
onlineRow.Size = UDim2.fromOffset(0, 16)
onlineRow.Parent = info

local onlineList = Instance.new("UIListLayout")
onlineList.FillDirection = Enum.FillDirection.Horizontal
onlineList.VerticalAlignment = Enum.VerticalAlignment.Center
onlineList.SortOrder = Enum.SortOrder.LayoutOrder
onlineList.Padding = UDim.new(0, 5)
onlineList.Parent = onlineRow

local dot = Instance.new("Frame") -- small green "live" square
dot.LayoutOrder = 1
dot.Size = UDim2.fromOffset(6, 6)
dot.BackgroundColor3 = COLORS.Accent
dot.BorderSizePixel = 0
dot.Parent = onlineRow

local peopleIcon = Instance.new("ImageLabel")
peopleIcon.LayoutOrder = 2
peopleIcon.Size = UDim2.fromOffset(15, 15)
peopleIcon.BackgroundTransparency = 1
peopleIcon.Image = IconIds.Players
peopleIcon.ImageColor3 = COLORS.Dim
peopleIcon.ScaleType = Enum.ScaleType.Fit
peopleIcon.Parent = onlineRow

local onlineText = text(onlineRow, 16, REGULAR, COLORS.Dim)
onlineText.LayoutOrder = 3

local function refreshOnline()
	local n = #Players:GetPlayers()
	local max = Players.MaxPlayers
	if max and max > 0 then
		onlineText.Text = string.format("%d / %d online", n, max)
	else
		onlineText.Text = string.format("%d online", n)
	end
end
Players.PlayerAdded:Connect(refreshOnline)
Players.PlayerRemoving:Connect(function()
	task.defer(refreshOnline) -- the leaving player is still in the list during this event
end)
refreshOnline()

---------------------------------------------------------------- store window

local storeGui = Instance.new("ScreenGui")
storeGui.Name = "Store"
storeGui.ResetOnSpawn = false
storeGui.DisplayOrder = 20
storeGui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
storeGui.Enabled = false
storeGui.Parent = player:WaitForChild("PlayerGui")

local window = Instance.new("Frame")
window.Name = "Window"
window.AnchorPoint = Vector2.new(0.5, 0.5)
window.Position = UDim2.fromScale(0.5, 0.5)
window.Size = UDim2.fromOffset(620, 400)
window.BackgroundColor3 = COLORS.Window
window.BackgroundTransparency = 0.05
window.BorderSizePixel = 0
window.Active = true
window.Parent = storeGui

local windowScale = Instance.new("UIScale")
windowScale.Parent = window

local header = Instance.new("Frame")
header.Name = "Header"
header.Size = UDim2.new(1, 0, 0, 48)
header.BackgroundColor3 = COLORS.Header
header.BorderSizePixel = 0
header.Parent = window

local headerIcon = Instance.new("ImageLabel")
headerIcon.AnchorPoint = Vector2.new(0, 0.5)
headerIcon.Position = UDim2.new(0, 14, 0.5, 0)
headerIcon.Size = UDim2.fromOffset(26, 26)
headerIcon.BackgroundTransparency = 1
headerIcon.Image = IconIds.Store
headerIcon.ImageColor3 = COLORS.Main
headerIcon.ScaleType = Enum.ScaleType.Fit
headerIcon.Parent = header

local title = Instance.new("TextLabel")
title.Position = UDim2.fromOffset(50, 0)
title.Size = UDim2.new(1, -110, 1, 0)
title.BackgroundTransparency = 1
title.FontFace = BOLD
title.TextSize = 22
title.TextColor3 = COLORS.Main
title.TextXAlignment = Enum.TextXAlignment.Left
title.Text = "STORE"
title.Parent = header

local closeBtn = Instance.new("TextButton")
closeBtn.Name = "Close"
closeBtn.AnchorPoint = Vector2.new(1, 0.5)
closeBtn.Position = UDim2.new(1, -8, 0.5, 0)
closeBtn.Size = UDim2.fromOffset(34, 34)
closeBtn.BackgroundColor3 = COLORS.Close
closeBtn.BorderSizePixel = 0
closeBtn.FontFace = BOLD
closeBtn.TextSize = 20
closeBtn.TextColor3 = COLORS.Main
closeBtn.Text = "X"
closeBtn.Parent = header

-- Store contents go here (nothing is for sale yet).
local body = Instance.new("Frame")
body.Name = "Body"
body.Position = UDim2.fromOffset(0, 48)
body.Size = UDim2.new(1, 0, 1, -48)
body.BackgroundTransparency = 1
body.Parent = window

local empty = Instance.new("TextLabel")
empty.Name = "Empty"
empty.Size = UDim2.fromScale(1, 1)
empty.BackgroundTransparency = 1
empty.FontFace = REGULAR
empty.TextSize = 18
empty.TextColor3 = COLORS.Dim
empty.Text = "Nothing for sale yet."
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
	if io.KeyCode == STORE_KEY then
		setStore(not storeOpen)
	end
end)

---------------------------------------------------------------- buttons list

iconButton(1, "Store", IconIds.Store, "F4", function()
	setStore(not storeOpen)
end)

---------------------------------------------------------------- scale

local function layout()
	local l = HudLayout.get()
	uiScale.Scale = l.scale
	-- the window shrinks on small screens so it never runs off the edge
	local cam = workspace.CurrentCamera
	local vp = if cam then cam.ViewportSize else Vector2.new(1280, 900)
	windowScale.Scale = math.min(1, (vp.X - 24) / 620, (vp.Y - 24) / 400)
	for _, k in keyHints do
		k.Visible = UserInputService.KeyboardEnabled
	end
end
HudLayout.Changed:Connect(layout)
UserInputService.LastInputTypeChanged:Connect(layout)
layout()
