-- Top-right strip (GTA RP server style):
--
--   TULEVO
--   [people] 12 / 30 online
--
-- The game name (Config.GameName) and how many players are on this server right now, out of
-- the server's max. Sits under Roblox's own top buttons (CoreUISafeInsets) and scales with the
-- rest of the HUD (HudLayout). The ammo counter sits under it, the admin DEBUG button left of it.
-- The Store / Bag / Phone / Map buttons are on the right edge: RightRail.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local IconIds = require(Shared:WaitForChild("IconIds"))
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))

local player = Players.LocalPlayer

local COLORS = {
	Main = Color3.fromRGB(245, 245, 245),
	Dim = Color3.fromRGB(185, 190, 196),
	Accent = Color3.fromRGB(110, 200, 110),
	Stroke = Color3.fromRGB(0, 0, 0),
}
-- Montserrat, like the right rail (Sweep the World style)
local REGULAR = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.Bold)
local BOLD = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.Heavy)

local TR = HudLayout.TopRight
local BTN = TR.Height -- strip height

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
	local outline = Instance.new("UIStroke") -- dark text edge, like the rail labels
	outline.Color = Color3.fromHex("#17191E")
	outline.Thickness = if size >= 20 then 2.5 else 1.5
	outline.LineJoinMode = Enum.LineJoinMode.Round
	outline.Parent = t
	t.TextXAlignment = Enum.TextXAlignment.Right
	t.Text = ""
	t.Parent = parent
	return t
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

---------------------------------------------------------------- scale

local function layout()
	local l = HudLayout.get()
	uiScale.Scale = l.scale
end
HudLayout.Changed:Connect(layout)
layout()
