--[[
	TEMP debug readout for the weapon system (Config.Weapons.Debug): a small box at the top
	left with what the client and the server think about the gun right now. If it shows up at
	all, LiveSync has the code from 2026-11-05 22:35 UTC or later.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
if not Config.Weapons.Debug then
	return
end
local Weapons = require(script.Parent:WaitForChild("Weapons"))

local BUILD = "weapons debug 2026-11-05 22:35"

local gui = Instance.new("ScreenGui")
gui.Name = "WeaponDebug"
gui.ResetOnSpawn = false
gui.DisplayOrder = 50
local label = Instance.new("TextLabel")
label.AnchorPoint = Vector2.new(0, 0)
label.Position = UDim2.fromOffset(8, 8)
label.Size = UDim2.fromOffset(330, 150)
label.BackgroundColor3 = Color3.new(0, 0, 0)
label.BackgroundTransparency = 0.35
label.BorderSizePixel = 0
label.TextColor3 = Color3.new(1, 1, 1)
label.Font = Enum.Font.Code
label.TextSize = 13
label.TextXAlignment = Enum.TextXAlignment.Left
label.TextYAlignment = Enum.TextYAlignment.Top
label.Parent = gui
local pad = Instance.new("UIPadding")
pad.PaddingLeft = UDim.new(0, 6)
pad.PaddingTop = UDim.new(0, 4)
pad.Parent = label
gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")

local last = 0
RunService.Heartbeat:Connect(function()
	local now = os.clock()
	if now - last < 0.2 then
		return
	end
	last = now
	local ok, d = pcall(Weapons.debug)
	if not ok then
		label.Text = `{BUILD}\nerror: {d}`
		return
	end
	label.Text = table.concat({
		BUILD,
		`client equipped: {d.equipped}`,
		`server equipped: {d.serverHas}`,
		`gun on: {d.gunOn}   guns: {d.guns}`,
		`anims: {d.anims}   playing: {d.playing}   hold len: {string.format("%.2f", d.holdLength)}`,
		`last clip: {d.clip}   drawing: {string.format("%.2f", d.drawing)}`,
		`holstering: {d.holstering}   reloading: {d.reloading}`,
		`dressing: {d.dressing}   in car: {d.inVehicle}`,
		`last held: {d.lastHeld}`,
	}, "\n")
end)
