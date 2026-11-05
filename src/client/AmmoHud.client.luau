-- GTA-style ammo counter, top right: bullets in the magazine (big) and spare bullets
-- (small). Only shows while a gun is in hand. Reads Client.Weapons.State.
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local Weapons = require(game:GetService("ReplicatedStorage"):WaitForChild("Shared"):WaitForChild("Weapons"))
local State = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local FONT = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Bold)

local gui = Instance.new("ScreenGui")
gui.Name = "AmmoHud"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = player:WaitForChild("PlayerGui")

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
	t.TextColor3 = Color3.fromRGB(240, 240, 235)
	t.TextStrokeTransparency = 0.4
	t.Parent = root
	return t
end
local reserve = label(1, 22)
local mag = label(2, 40)

RunService.RenderStepped:Connect(function()
	local def = State.Equipped and Weapons.get(State.Equipped)
	local show = def ~= nil and def.Class.Kind == "Gun" and not State.InVehicle
	root.Visible = show
	if show then
		reserve.Text = tostring(State.Reserve)
		mag.Text = tostring(State.Mag)
		mag.TextColor3 = if State.Mag == 0
			then Color3.fromRGB(230, 70, 60)
			elseif State.Mag <= math.ceil((def.MagSize or 30) * 0.2) then Color3.fromRGB(240, 190, 80)
			else Color3.fromRGB(240, 240, 235)
	end
end)
