--[[
	Debug panel window (testing tool, admins only). F8 or the small DEBUG button opens it.
	Built from plain Frames on purpose: dev tooling, not game UI.

	The server (Server/DebugPanel.server.luau) sets the Player attribute "DebugAdmin" for
	admins and checks every action again, so this window is only a remote control.

	Tabs: Items (give any item, fill ammo), Money (add / set Cash and Bank), World (clock,
	weather), Cars (spawn in front of you, remove yours), Player (knock down, revive, heal,
	god mode, teleports).
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local GameTime = require(Shared:WaitForChild("GameTime"))

local player = Players.LocalPlayer

if not player:GetAttribute("DebugAdmin") then
	player:GetAttributeChangedSignal("DebugAdmin"):Wait()
end

local Run = ReplicatedStorage:WaitForChild("DebugRemotes"):WaitForChild("Run") :: RemoteFunction
local Nav = require(script.Parent:WaitForChild("Nav"))

local cfg = Config.Debug or {}
local KEY = cfg.Key or Enum.KeyCode.F8

local W, H = 580, 420
local TAB_W = 110
local PAD = 10

local COLORS = {
	Window = Color3.fromRGB(28, 29, 31),
	Panel = Color3.fromRGB(44, 45, 48),
	Button = Color3.fromRGB(62, 64, 68),
	ButtonOn = Color3.fromRGB(70, 120, 190),
	Danger = Color3.fromRGB(150, 60, 55),
	Text = Color3.fromRGB(232, 233, 235),
	Dim = Color3.fromRGB(140, 143, 148),
	Good = Color3.fromRGB(110, 200, 110),
	Bad = Color3.fromRGB(220, 80, 70),
	Header = Color3.fromRGB(230, 170, 70),
}
local FONT_FAMILY = "rbxasset://fonts/families/BuilderSans.json"
local BOLD = Font.new(FONT_FAMILY, Enum.FontWeight.Bold)
local REGULAR = Font.new(FONT_FAMILY, Enum.FontWeight.Medium)

---------------------------------------------------------------- window

local gui = Instance.new("ScreenGui")
gui.Name = "DebugPanel"
gui.ResetOnSpawn = false
gui.DisplayOrder = 50
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets

local window = Instance.new("Frame")
window.Name = "Window"
window.AnchorPoint = Vector2.new(0.5, 0.5)
window.Position = UDim2.fromScale(0.5, 0.5)
window.Size = UDim2.fromOffset(W, H)
window.BackgroundColor3 = COLORS.Window
window.BackgroundTransparency = 0.05
window.BorderSizePixel = 0
window.Visible = false
window.Parent = gui

local scale = Instance.new("UIScale")
scale.Parent = window

local function label(parent: Instance, text: string, size: number, font: Font?, color: Color3?): TextLabel
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.Text = text
	t.TextSize = size
	t.FontFace = font or REGULAR
	t.TextColor3 = color or COLORS.Text
	t.TextXAlignment = Enum.TextXAlignment.Left
	t.Size = UDim2.new(1, 0, 0, size + 6)
	t.Parent = parent
	return t
end

local function button(parent: Instance, text: string, width: number?, onClick: () -> ()): TextButton
	local b = Instance.new("TextButton")
	b.AutoButtonColor = true
	b.BackgroundColor3 = COLORS.Button
	b.BorderSizePixel = 0
	b.Text = text
	b.TextSize = 15
	b.FontFace = BOLD
	b.TextColor3 = COLORS.Text
	b.Size = UDim2.fromOffset(width or 100, 30)
	b.Parent = parent
	b.Activated:Connect(onClick)
	return b
end

local function input(parent: Instance, placeholder: string, width: number, default: string?): TextBox
	local t = Instance.new("TextBox")
	t.BackgroundColor3 = COLORS.Panel
	t.BorderSizePixel = 0
	t.ClearTextOnFocus = false
	t.PlaceholderText = placeholder
	t.PlaceholderColor3 = COLORS.Dim
	t.Text = default or ""
	t.TextSize = 15
	t.FontFace = REGULAR
	t.TextColor3 = COLORS.Text
	t.Size = UDim2.fromOffset(width, 30)
	t.Parent = parent
	return t
end

local function row(parent: Instance): Frame
	local f = Instance.new("Frame")
	f.BackgroundTransparency = 1
	f.AutomaticSize = Enum.AutomaticSize.Y
	f.Size = UDim2.fromScale(1, 0)
	f.Parent = parent
	local layout = Instance.new("UIGridLayout")
	layout.CellPadding = UDim2.fromOffset(6, 6)
	layout.CellSize = UDim2.fromOffset(100, 30)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = f
	return f
end

local function flow(parent: Instance): Frame
	local f = Instance.new("Frame")
	f.BackgroundTransparency = 1
	f.Size = UDim2.new(1, 0, 0, 30)
	f.Parent = parent
	local layout = Instance.new("UIListLayout")
	layout.FillDirection = Enum.FillDirection.Horizontal
	layout.Padding = UDim.new(0, 6)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.VerticalAlignment = Enum.VerticalAlignment.Center
	layout.Parent = f
	return f
end

-- header
local title = label(window, "DEBUG", 18, BOLD, COLORS.Header)
title.Position = UDim2.fromOffset(PAD, 6)
title.Size = UDim2.new(1, -60, 0, 24)

local close = button(window, "X", 30, function()
	window.Visible = false
end)
close.Position = UDim2.new(1, -PAD - 30, 0, 6)
close.Modal = true -- frees the mouse in first person while the window is open

-- status line at the bottom
local status = label(window, "F8 closes this window", 14, REGULAR, COLORS.Dim)
status.Position = UDim2.new(0, PAD, 1, -26)
status.Size = UDim2.new(1, -PAD * 2, 0, 20)
status.TextTruncate = Enum.TextTruncate.AtEnd

local function say(ok: boolean, message: any)
	status.Text = tostring(message or (if ok then "Done" else "Failed"))
	status.TextColor3 = if ok then COLORS.Good else COLORS.Bad
end

local function run(action: string, a: any?, b: any?): (boolean, any)
	local ok, success, message = pcall(Run.InvokeServer, Run, action, a, b)
	if not ok then
		say(false, success)
		return false, success
	end
	if action ~= "Info" then
		say(success, message)
	end
	return success, message
end

-- tabs on the left, pages on the right
local tabBar = Instance.new("Frame")
tabBar.BackgroundTransparency = 1
tabBar.Position = UDim2.fromOffset(PAD, 38)
tabBar.Size = UDim2.new(0, TAB_W, 1, -38 - 32)
tabBar.Parent = window
local tabLayout = Instance.new("UIListLayout")
tabLayout.Padding = UDim.new(0, 6)
tabLayout.SortOrder = Enum.SortOrder.LayoutOrder
tabLayout.Parent = tabBar

local pageHolder = Instance.new("Frame")
pageHolder.BackgroundColor3 = COLORS.Panel
pageHolder.BackgroundTransparency = 0.3
pageHolder.BorderSizePixel = 0
pageHolder.Position = UDim2.fromOffset(PAD + TAB_W + PAD, 38)
pageHolder.Size = UDim2.new(1, -(PAD * 3 + TAB_W), 1, -38 - 32)
pageHolder.Parent = window

local pages: { [string]: ScrollingFrame } = {}
local tabs: { [string]: TextButton } = {}

local function showPage(name: string)
	for n, p in pages do
		p.Visible = n == name
		tabs[n].BackgroundColor3 = if n == name then COLORS.ButtonOn else COLORS.Button
	end
end

local function page(name: string): ScrollingFrame
	local p = Instance.new("ScrollingFrame")
	p.Name = name
	p.BackgroundTransparency = 1
	p.BorderSizePixel = 0
	p.Size = UDim2.fromScale(1, 1)
	p.CanvasSize = UDim2.new()
	p.AutomaticCanvasSize = Enum.AutomaticSize.Y
	p.ScrollBarThickness = 6
	p.Visible = false
	p.Parent = pageHolder
	local pad = Instance.new("UIPadding")
	pad.PaddingTop = UDim.new(0, 8)
	pad.PaddingLeft = UDim.new(0, 8)
	pad.PaddingRight = UDim.new(0, 12)
	pad.PaddingBottom = UDim.new(0, 8)
	pad.Parent = p
	local layout = Instance.new("UIListLayout")
	layout.Padding = UDim.new(0, 6)
	layout.SortOrder = Enum.SortOrder.LayoutOrder
	layout.Parent = p
	pages[name] = p
	local t = button(tabBar, name, TAB_W, function()
		showPage(name)
	end)
	t.LayoutOrder = #tabBar:GetChildren()
	tabs[name] = t
	return p
end

---------------------------------------------------------------- Items

local itemsPage = page("Items")
local countRow = flow(itemsPage)
label(countRow, "Count", 15).Size = UDim2.fromOffset(50, 30)
local countBox = input(countRow, "1", 60, "1")
button(countRow, "Fill ammo", 110, function()
	run("FillAmmo")
end)
local itemsHeader = label(itemsPage, "Click an item to give it to yourself", 14, REGULAR, COLORS.Dim)
itemsHeader.LayoutOrder = 1
local itemGrid = row(itemsPage)
itemGrid.LayoutOrder = 2
(itemGrid:FindFirstChildOfClass("UIGridLayout") :: UIGridLayout).CellSize = UDim2.fromOffset(130, 30)

---------------------------------------------------------------- Money

local moneyPage = page("Money")
local moneyNow = label(moneyPage, "", 16, BOLD)

local function updateMoney()
	local cash = player:GetAttribute("Cash") or 0
	local bank = player:GetAttribute("Bank") or 0
	moneyNow.Text = `Cash ${cash}   Bank ${bank}`
end
player:GetAttributeChangedSignal("Cash"):Connect(updateMoney)
player:GetAttributeChangedSignal("Bank"):Connect(updateMoney)
updateMoney()

for i, which in { "Cash", "Bank" } do
	local head = label(moneyPage, which, 15, BOLD, COLORS.Header)
	head.LayoutOrder = i * 10
	local quick = flow(moneyPage)
	quick.LayoutOrder = i * 10 + 1
	for _, amount in { 1000, 10000, 100000, -1000 } do
		button(quick, if amount > 0 then `+{amount}` else tostring(amount), 80, function()
			run("AddMoney", which, amount)
		end)
	end
	local custom = flow(moneyPage)
	custom.LayoutOrder = i * 10 + 2
	local box = input(custom, "amount", 110)
	button(custom, "Add", 70, function()
		run("AddMoney", which, box.Text)
	end)
	button(custom, "Set to", 70, function()
		run("SetMoney", which, box.Text)
	end)
end

---------------------------------------------------------------- World

local worldPage = page("World")
local clockNow = label(worldPage, "", 16, BOLD)
local timeHead = label(worldPage, "Time", 15, BOLD, COLORS.Header)
timeHead.LayoutOrder = 1
local hours = row(worldPage)
hours.LayoutOrder = 2
(hours:FindFirstChildOfClass("UIGridLayout") :: UIGridLayout).CellSize = UDim2.fromOffset(60, 30)
for h = 0, 21, 3 do
	button(hours, string.format("%02d:00", h), 60, function()
		run("SetTime", h, 0)
	end)
end
local customTime = flow(worldPage)
customTime.LayoutOrder = 3
local timeBox = input(customTime, "HH:MM", 80)
button(customTime, "Set time", 90, function()
	local h, m = string.match(timeBox.Text, "^%s*(%d+)%s*[:%.]?%s*(%d*)%s*$")
	if not h then
		say(false, "Type a time like 21:30")
		return
	end
	run("SetTime", tonumber(h), tonumber(m) or 0)
end)
local weatherHead = label(worldPage, "Weather", 15, BOLD, COLORS.Header)
weatherHead.LayoutOrder = 4
local weatherRow = row(worldPage)
weatherRow.LayoutOrder = 5

task.spawn(function()
	while true do
		if window.Visible then
			local t = GameTime.now()
			if t then
				clockNow.Text =
					string.format("%02d:%02d  %s %d.%02d.%d", t.hour, t.min, t.weekday, t.day, t.month, t.year)
			end
		end
		task.wait(0.5)
	end
end)

---------------------------------------------------------------- Cars

local carsPage = page("Cars")
label(carsPage, "Spawns next to you (up to 3, the oldest goes)", 14, REGULAR, COLORS.Dim)
local carRow = row(carsPage)
carRow.LayoutOrder = 1
(carRow:FindFirstChildOfClass("UIGridLayout") :: UIGridLayout).CellSize = UDim2.fromOffset(130, 30)
local clearRow = flow(carsPage)
clearRow.LayoutOrder = 2
button(clearRow, "Remove my cars", 150, function()
	run("ClearCars")
end).BackgroundColor3 = COLORS.Danger

---------------------------------------------------------------- Player

local playerPage = page("Player")
label(playerPage, "Health", 15, BOLD, COLORS.Header)
local hp = flow(playerPage)
hp.LayoutOrder = 1
button(hp, "Knock down", 110, function()
	run("Knock")
end).BackgroundColor3 = COLORS.Danger
button(hp, "Revive", 80, function()
	run("Revive")
end)
button(hp, "Full heal", 90, function()
	run("Heal")
end)
local godButton = button(hp, "God mode", 100, function()
	run("God")
end)
local function updateGod()
	godButton.BackgroundColor3 = if player:GetAttribute("DebugGod") then COLORS.ButtonOn else COLORS.Button
end
player:GetAttributeChangedSignal("DebugGod"):Connect(updateGod)
updateGod()

local tpHead = label(playerPage, "Teleport", 15, BOLD, COLORS.Header)
tpHead.LayoutOrder = 2
local tp = flow(playerPage)
tp.LayoutOrder = 3
button(tp, "To spawn", 90, function()
	run("TeleportSpawn")
end)
button(tp, "To GPS mark", 110, function()
	local wp = Nav.waypoint
	if not wp then
		say(false, "No GPS mark: set one on the map (M)")
		return
	end
	run("TeleportXZ", wp.X, wp.Z)
end)
local clickTp = false
local clickButton
clickButton = button(tp, "Click to teleport", 140, function()
	clickTp = not clickTp
	clickButton.BackgroundColor3 = if clickTp then COLORS.ButtonOn else COLORS.Button
	if clickTp then
		window.Visible = false
		say(true, "Click the ground to teleport there")
	end
end)

-- gangs: join one (spawn in its hood from the next respawn) and jump to every city spawn
local gangRow = flow(playerPage)
gangRow.LayoutOrder = 3
button(gangRow, "Civilian", 90, function()
	run("SetGang", "")
end)
for _, g in Config.Gangs do
	local b = button(gangRow, `Join {g.Name}`, 130, function()
		run("SetGang", g.Id)
	end)
	b.BackgroundColor3 = g.Color:Lerp(COLORS.Button, 0.45)
end
local spawnRow = flow(playerPage)
spawnRow.LayoutOrder = 3
button(spawnRow, "Main spawn", 110, function()
	run("TeleportNamedSpawn", "Spawn")
end)
for _, g in Config.Gangs do
	button(spawnRow, `{g.Name} hood`, 130, function()
		run("TeleportNamedSpawn", g.Id .. "Spawn")
	end)
end

local toPlayerHead = label(playerPage, "To player", 15, BOLD, COLORS.Header)
toPlayerHead.LayoutOrder = 4
local playerRow = row(playerPage)
playerRow.LayoutOrder = 5
(playerRow:FindFirstChildOfClass("UIGridLayout") :: UIGridLayout).CellSize = UDim2.fromOffset(130, 30)

local function refreshPlayers()
	for _, c in playerRow:GetChildren() do
		if c:IsA("GuiButton") then
			c:Destroy()
		end
	end
	for _, p in Players:GetPlayers() do
		if p ~= player then
			button(playerRow, p.DisplayName, 130, function()
				run("TeleportToPlayer", p.UserId)
			end)
		end
	end
end
Players.PlayerAdded:Connect(refreshPlayers)
Players.PlayerRemoving:Connect(function()
	task.defer(refreshPlayers)
end)
refreshPlayers()

---------------------------------------------------------------- lists from the server

local function fillLists()
	local ok, info = run("Info")
	if not ok or type(info) ~= "table" then
		say(false, "Couldn't load lists")
		return
	end
	for _, item in info.items or {} do
		button(itemGrid, item.Name, 130, function()
			run("GiveItem", item.Id, tonumber(countBox.Text) or 1)
		end)
	end
	for _, car in info.cars or {} do
		button(carRow, car.Name, 130, function()
			run("SpawnCar", car.Id)
		end)
	end
	for _, name in info.weathers or {} do
		button(weatherRow, tostring(name), 100, function()
			run("Weather", name)
		end)
	end
end

---------------------------------------------------------------- open / close

local openButton = Instance.new("TextButton")
openButton.Name = "Open"
openButton.AnchorPoint = Vector2.new(1, 0)
openButton.Position = UDim2.new(1, -8, 0, 8)
openButton.Size = UDim2.fromOffset(64, 26)
openButton.BackgroundColor3 = COLORS.Window
openButton.BackgroundTransparency = 0.25
openButton.BorderSizePixel = 0
openButton.Text = "DEBUG"
openButton.TextSize = 13
openButton.FontFace = BOLD
openButton.TextColor3 = COLORS.Header
openButton.Parent = gui

---------------------------------------------------------------- Camera
-- live tuning for Movement/MouseLook (this session only; send Dev's picks to Config.Camera)

local MouseLook = require(script.Parent:WaitForChild("Movement"):WaitForChild("MouseLook"))
local cameraPage = page("Camera")
label(cameraPage, "Mouse sensitivity (this session; defaults in Config.Camera)", 14, REGULAR, COLORS.Dim)
local SENS_ROWS = {
	{ "Sensitivity", "On foot" },
	{ "AimSensitivity", "Aiming" },
	{ "VehicleSensitivity", "Driving" },
}
local sensDefaults = {}
for i, r in SENS_ROWS do
	local key, name = r[1], r[2]
	sensDefaults[key] = MouseLook.get(key)
	local f = flow(cameraPage)
	f.LayoutOrder = i
	label(f, name, 15, BOLD).Size = UDim2.fromOffset(80, 30)
	local value: TextLabel
	local function show()
		value.Text = string.format("%.2f", MouseLook.get(key))
	end
	local function nudge(by: number)
		MouseLook.set(key, math.clamp(math.round((MouseLook.get(key) + by) * 100) / 100, 0.05, 5))
		show()
	end
	button(f, "-0.1", 50, function()
		nudge(-0.1)
	end)
	button(f, "-", 34, function()
		nudge(-0.02)
	end)
	value = label(f, "", 16, BOLD)
	value.Size = UDim2.fromOffset(50, 30)
	value.TextXAlignment = Enum.TextXAlignment.Center
	button(f, "+", 34, function()
		nudge(0.02)
	end)
	button(f, "+0.1", 50, function()
		nudge(0.1)
	end)
	button(f, "Reset", 60, function()
		MouseLook.set(key, sensDefaults[key])
		show()
	end)
	show()
end

local TOGGLES = {
	{ "MouseLook", "Mouse look" },
	{ "EqualAxes", "Equal up/down" },
	{ "AimFovScale", "Aim zoom scale" },
}
local toggleRow = flow(cameraPage)
toggleRow.LayoutOrder = #SENS_ROWS + 1
for _, t in TOGGLES do
	local key = t[1]
	local b: TextButton
	local function show()
		b.BackgroundColor3 = if MouseLook.get(key) then COLORS.ButtonOn else COLORS.Button
	end
	b = button(toggleRow, t[2], 130, function()
		MouseLook.set(key, not MouseLook.get(key))
		show()
	end)
	show()
end
local camHint = label(cameraPage, "Hold Left Alt in game to get the cursor back.", 14, REGULAR, COLORS.Dim)
camHint.LayoutOrder = #SENS_ROWS + 2

local filled = false
local function toggle()
	window.Visible = not window.Visible
	if window.Visible then
		clickTp = false
		clickButton.BackgroundColor3 = COLORS.Button
		if not filled then
			filled = true
			task.spawn(fillLists)
		end
	end
end
openButton.Activated:Connect(toggle)

UserInputService.InputBegan:Connect(function(io, processed)
	if io.KeyCode == KEY and not UserInputService:GetFocusedTextBox() then
		toggle()
		return
	end
	if not clickTp or processed then
		return
	end
	if io.UserInputType ~= Enum.UserInputType.MouseButton1 and io.UserInputType ~= Enum.UserInputType.Touch then
		return
	end
	local camera = workspace.CurrentCamera
	local ray = camera:ViewportPointToRay(io.Position.X, io.Position.Y)
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { player.Character :: Instance }
	local hit = workspace:Raycast(ray.Origin, ray.Direction * 5000, params)
	clickTp = false
	clickButton.BackgroundColor3 = COLORS.Button
	if hit then
		run("TeleportPoint", hit.Position)
	else
		say(false, "Clicked the sky")
	end
end)

-- fit small screens
local function fit()
	local camera = workspace.CurrentCamera
	local view = camera and camera.ViewportSize or Vector2.new(1280, 720)
	scale.Scale = math.clamp(math.min((view.X - 20) / W, (view.Y - 20) / H), 0.5, 1)
end
workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(fit)
fit()

showPage("Items")
gui.Parent = player:WaitForChild("PlayerGui")
