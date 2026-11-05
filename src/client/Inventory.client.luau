--[[
	Inventory window (sizing pass only): I opens / closes an empty box in the middle of the
	screen. No slots, text or items yet.

	Size comes from Dev's reference screenshot: the window is 94% of the screen height and
	1.17x as wide as it is tall (about 62% of a 16:9 screen's width), centred. On narrow
	screens it shrinks to fit the width instead.
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")

local player = Players.LocalPlayer

local HEIGHT = 0.94 -- share of the screen height
local ASPECT = 1.17 -- width / height
local MAX_WIDTH = 0.96 -- share of the screen width it may use on narrow screens

local gui = Instance.new("ScreenGui")
gui.Name = "Inventory"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 10
gui.Enabled = false
gui.Parent = player:WaitForChild("PlayerGui")

local box = Instance.new("Frame")
box.Name = "Window"
box.AnchorPoint = Vector2.new(0.5, 0.5)
box.Position = UDim2.fromScale(0.5, 0.5)
box.Size = UDim2.fromScale(MAX_WIDTH, HEIGHT)
box.BackgroundColor3 = Color3.fromRGB(28, 29, 31)
box.BackgroundTransparency = 0.12
box.BorderSizePixel = 0
box.Parent = gui

local aspect = Instance.new("UIAspectRatioConstraint")
aspect.AspectRatio = ASPECT
aspect.AspectType = Enum.AspectType.FitWithinMaxSize
aspect.DominantAxis = Enum.DominantAxis.Height
aspect.Parent = box

ContextActionService:BindAction("Inventory_Toggle", function(_, state)
	if state == Enum.UserInputState.Begin then
		gui.Enabled = not gui.Enabled
	end
	return Enum.ContextActionResult.Pass
end, false, Enum.KeyCode.I)
