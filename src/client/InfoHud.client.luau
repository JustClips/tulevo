-- Clock + money panel, right of the radar (GTA RP style):
--   21:29  27.05.2020
--   Wednesday
--   [wallet] $5,561      cash
--   [card]   $43,239     bank
-- Time/date come from Shared/GameTime, money from the Player's "Cash" / "Bank"
-- attributes (set by Server/Money). When cash changes, a green +$ / red -$ pops up
-- next to it for a moment.
-- Desktop and phone: its bottom lines up with the bottom of the health bar, same
-- UIScale as the radar (see HudLayout).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local GameTime = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameTime"))
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))

local player = Players.LocalPlayer

-- Must match Minimap / HealthHud: left 20, radar 230 x 150, bar 18 tall, 3 gap, 8 from the edge.
local LEFT, RADAR_W, STACK_H, EDGE = 20, 230, 150 + 3 + 18, 8
local GAP = 14 -- radar -> panel
local PANEL_W = 220

local COLORS = {
	Main = Color3.fromRGB(245, 245, 245),
	Dim = Color3.fromRGB(185, 190, 196),
	Plus = Color3.fromRGB(110, 200, 110),
	Minus = Color3.fromRGB(225, 90, 80),
	Stroke = Color3.fromRGB(0, 0, 0),
}
local REGULAR = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Regular)
local BOLD = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.SemiBold)

local gui = Instance.new("ScreenGui")
gui.Name = "InfoHud"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.Parent = player:WaitForChild("PlayerGui")

local root = Instance.new("Frame")
root.Name = "Root"
root.BackgroundTransparency = 1
root.Size = UDim2.fromOffset(PANEL_W, 0)
root.AutomaticSize = Enum.AutomaticSize.Y
root.Parent = gui

local uiScale = Instance.new("UIScale")
uiScale.Parent = root

local function layout()
	local l = HudLayout.get()
	uiScale.Scale = l.scale
	local s = l.scale
	root.AnchorPoint = Vector2.new(0, 1)
	if l.touch then
		-- radar is at the top-left: panel bottom = bar bottom
		root.Position = UDim2.fromOffset((LEFT + RADAR_W + GAP) * s, EDGE + STACK_H * s)
	else
		root.Position = UDim2.new(0, LEFT + (RADAR_W + GAP) * s, 1, -EDGE)
	end
end
HudLayout.Changed:Connect(layout)
layout()

local list = Instance.new("UIListLayout")
list.FillDirection = Enum.FillDirection.Vertical
list.SortOrder = Enum.SortOrder.LayoutOrder
list.Padding = UDim.new(0, 0)
list.Parent = root

local function row(order: number, height: number, padTop: number?)
	local r = Instance.new("Frame")
	r.Name = "Row" .. order
	r.LayoutOrder = order
	r.BackgroundTransparency = 1
	r.Size = UDim2.new(1, 0, 0, height + (padTop or 0))
	r.Parent = root
	local pad = Instance.new("UIPadding")
	pad.PaddingTop = UDim.new(0, padTop or 0)
	pad.Parent = r
	local l = Instance.new("UIListLayout")
	l.FillDirection = Enum.FillDirection.Horizontal
	l.VerticalAlignment = Enum.VerticalAlignment.Bottom
	l.SortOrder = Enum.SortOrder.LayoutOrder
	l.Padding = UDim.new(0, 7)
	l.Parent = r
	return r
end

local function label(parent: Instance, order: number, size: number, font: Font, color: Color3)
	local t = Instance.new("TextLabel")
	t.LayoutOrder = order
	t.BackgroundTransparency = 1
	t.AutomaticSize = Enum.AutomaticSize.X
	t.Size = UDim2.new(0, 0, 1, 0)
	t.FontFace = font
	t.TextSize = size
	t.TextColor3 = color
	t.TextStrokeColor3 = COLORS.Stroke
	t.TextStrokeTransparency = 0.7
	t.TextXAlignment = Enum.TextXAlignment.Left
	t.TextYAlignment = Enum.TextYAlignment.Bottom
	t.Text = ""
	t.Parent = parent
	return t
end

-- Small flat icons from frames (no image uploads needed).
local function walletIcon(parent: Instance, order: number)
	local holder = Instance.new("Frame")
	holder.LayoutOrder = order
	holder.BackgroundTransparency = 1
	holder.Size = UDim2.fromOffset(18, 22)
	holder.Parent = parent
	local body = Instance.new("Frame")
	body.AnchorPoint = Vector2.new(0, 0.5)
	body.Position = UDim2.new(0, 0, 0.5, 2)
	body.Size = UDim2.fromOffset(17, 12)
	body.BackgroundColor3 = COLORS.Main
	body.BorderSizePixel = 0
	body.Parent = holder
	local flap = Instance.new("Frame")
	flap.Position = UDim2.fromOffset(2, -3)
	flap.Size = UDim2.fromOffset(11, 3)
	flap.BackgroundColor3 = COLORS.Main
	flap.BorderSizePixel = 0
	flap.Parent = body
	local clasp = Instance.new("Frame")
	clasp.AnchorPoint = Vector2.new(1, 0.5)
	clasp.Position = UDim2.new(1, 0, 0.5, 0)
	clasp.Size = UDim2.fromOffset(6, 5)
	clasp.BackgroundColor3 = Color3.fromRGB(40, 44, 48)
	clasp.BorderSizePixel = 0
	clasp.Parent = body
end

local function cardIcon(parent: Instance, order: number)
	local holder = Instance.new("Frame")
	holder.LayoutOrder = order
	holder.BackgroundTransparency = 1
	holder.Size = UDim2.fromOffset(18, 18)
	holder.Parent = parent
	local body = Instance.new("Frame")
	body.AnchorPoint = Vector2.new(0, 0.5)
	body.Position = UDim2.new(0, 1, 0.5, 1)
	body.Size = UDim2.fromOffset(15, 10)
	body.BackgroundTransparency = 1
	body.Parent = holder
	local stroke = Instance.new("UIStroke")
	stroke.Color = COLORS.Dim
	stroke.Thickness = 1.5
	stroke.Parent = body
	local stripe = Instance.new("Frame")
	stripe.Position = UDim2.fromOffset(0, 3)
	stripe.Size = UDim2.new(1, 0, 0, 2)
	stripe.BackgroundColor3 = COLORS.Dim
	stripe.BorderSizePixel = 0
	stripe.Parent = body
end

local timeRow = row(1, 28)
local timeText = label(timeRow, 1, 26, BOLD, COLORS.Main)
local dateText = label(timeRow, 2, 15, REGULAR, COLORS.Dim)
local dayRow = row(2, 18)
local dayText = label(dayRow, 1, 17, REGULAR, COLORS.Dim)

local cashRow = row(3, 26, 12)
walletIcon(cashRow, 1)
local cashText = label(cashRow, 2, 24, BOLD, COLORS.Main)
local deltaText = label(cashRow, 3, 18, BOLD, COLORS.Plus)
deltaText.TextTransparency = 1
deltaText.TextStrokeTransparency = 1

local bankRow = row(4, 20, 2)
cardIcon(bankRow, 1)
local bankText = label(bankRow, 2, 17, REGULAR, COLORS.Dim)

-- 1234567 -> "$1,234,567"
local function money(n: number): string
	local s = tostring(math.floor(math.abs(n)))
	local out = s:reverse():gsub("(%d%d%d)", "%1,"):reverse()
	if out:sub(1, 1) == "," then
		out = out:sub(2)
	end
	return (if n < 0 then "-$" else "$") .. out
end

-- Clock: only rewrite the labels when the minute changes.
local lastMinute = -1
task.spawn(function()
	while true do
		local t = GameTime.now()
		if t and t.min ~= lastMinute then
			lastMinute = t.min
			timeText.Text = string.format("%02d:%02d", t.hour, t.min)
			dateText.Text = string.format("%02d.%02d.%d", t.day, t.month, t.year)
			dayText.Text = t.weekday
		end
		task.wait(0.25)
	end
end)

-- Money
local lastCash: number? = nil
local deltaTween: Tween? = nil
local function showDelta(diff: number)
	if deltaTween then
		deltaTween:Cancel()
	end
	deltaText.Text = (if diff > 0 then "+" else "") .. money(diff)
	deltaText.TextColor3 = if diff > 0 then COLORS.Plus else COLORS.Minus
	deltaText.TextTransparency = 0
	deltaText.TextStrokeTransparency = 0.7
	deltaTween = TweenService:Create(
		deltaText,
		TweenInfo.new(1.2, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 1.8),
		{ TextTransparency = 1, TextStrokeTransparency = 1 }
	)
	deltaTween:Play()
end

local function updateCash()
	local cash = player:GetAttribute("Cash")
	cashText.Text = if cash then money(cash) else "$-"
	if cash and lastCash and cash ~= lastCash then
		showDelta(cash - lastCash)
	end
	lastCash = cash
end
local function updateBank()
	local bank = player:GetAttribute("Bank")
	bankText.Text = if bank then money(bank) else "$-"
end
player:GetAttributeChangedSignal("Cash"):Connect(updateCash)
player:GetAttributeChangedSignal("Bank"):Connect(updateBank)
updateCash()
updateBank()
