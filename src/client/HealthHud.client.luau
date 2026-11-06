-- Bottom-left health bar (copy of the reference): one dark frame split in
-- two, green health on the left, blue armor on the right, the number inside each half.
-- Armor comes from the Humanoid's Armor / MaxArmor attributes (set by the server).
local Players = game:GetService("Players")
local StarterGui = game:GetService("StarterGui")
local TweenService = game:GetService("TweenService")

local player = Players.LocalPlayer

pcall(function()
	StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
end)

local BAR_W, BAR_H = 230, 18
local BORDER = 3
local MARGIN = 20
local BOTTOM = 8

local COLORS = {
	Frame = Color3.fromRGB(62, 70, 58),
	Empty = Color3.fromRGB(38, 44, 36),
	Health = Color3.fromRGB(92, 150, 86),
	Armor = Color3.fromRGB(66, 112, 142),
	Text = Color3.fromRGB(232, 235, 230),
}
local FONT = Font.new("rbxasset://fonts/families/RobotoCondensed.json", Enum.FontWeight.Regular)

local gui = Instance.new("ScreenGui")
gui.Name = "HealthHud"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
-- Stay clear of the notch and Roblox's top buttons.
gui.ScreenInsets = Enum.ScreenInsets.CoreUISafeInsets
gui.Parent = player:WaitForChild("PlayerGui")

local root = Instance.new("Frame")
root.Name = "Root"
root.AnchorPoint = Vector2.new(0, 1)
root.Position = UDim2.new(0, MARGIN, 1, -BOTTOM)

-- Size/position per screen (see HudLayout): bottom-left on desktop, under the
-- radar at the top-left on phones.
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))
local uiScale = Instance.new("UIScale")
uiScale.Parent = root
local RADAR_H, GAP = 150, 3 -- matches Minimap
local function layout()
	local l = HudLayout.get()
	uiScale.Scale = l.scale
	if l.touch then
		root.AnchorPoint = Vector2.new(0, 0)
		root.Position = UDim2.fromOffset(MARGIN * l.scale, 8 + (RADAR_H + GAP) * l.scale)
	else
		root.AnchorPoint = Vector2.new(0, 1)
		root.Position = UDim2.new(0, MARGIN, 1, -BOTTOM)
	end
end
HudLayout.Changed:Connect(layout)
layout()
root.Size = UDim2.fromOffset(BAR_W, BAR_H)
root.BackgroundTransparency = 1
root.Parent = gui

local bar = Instance.new("Frame")
bar.Name = "Bar"
bar.AnchorPoint = Vector2.new(0, 1)
bar.Position = UDim2.fromScale(0, 1)
bar.Size = UDim2.fromOffset(BAR_W, BAR_H)
bar.BackgroundColor3 = COLORS.Frame
bar.BorderSizePixel = 0
bar.Parent = root

local inner = BAR_W - BORDER * 3
local half = math.floor(inner / 2)

local function segment(name: string, x: number, w: number, color: Color3)
	local slot = Instance.new("Frame")
	slot.Name = name
	slot.Position = UDim2.fromOffset(x, BORDER)
	slot.Size = UDim2.fromOffset(w, BAR_H - BORDER * 2)
	slot.BackgroundColor3 = COLORS.Empty
	slot.BorderSizePixel = 0
	slot.ClipsDescendants = true
	slot.Parent = bar

	local fill = Instance.new("Frame")
	fill.Name = "Fill"
	fill.Size = UDim2.fromScale(1, 1)
	fill.BackgroundColor3 = color
	fill.BorderSizePixel = 0
	fill.Parent = slot

	local label = Instance.new("TextLabel")
	label.Name = name .. "Text"
	-- On the bar (not inside the clipped slot) and above the fill.
	label.Position = UDim2.fromOffset(x, BORDER)
	label.Size = UDim2.fromOffset(w, BAR_H - BORDER * 2)
	label.ZIndex = 3
	label.BackgroundTransparency = 1
	label.FontFace = FONT
	label.TextSize = 12
	label.TextColor3 = COLORS.Text
	label.TextStrokeTransparency = 0.5
	label.Text = "0"
	label.Parent = bar

	return fill, label
end

local healthFill, healthText = segment("Health", BORDER, half, COLORS.Health)
local armorFill, armorText = segment("Armor", BORDER * 2 + half, inner - half, COLORS.Armor)

local tweenInfo = TweenInfo.new(0.15, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
local function setFill(fill: Frame, label: TextLabel, value: number, max: number)
	local pct = if max > 0 then math.clamp(value / max, 0, 1) else 0
	TweenService:Create(fill, tweenInfo, { Size = UDim2.fromScale(pct, 1) }):Play()
	label.Text = tostring(math.ceil(math.max(value, 0)))
end

armorFill.Size = UDim2.fromScale(0, 1)
armorText.Text = "0"
-- Empty until a character with a Humanoid exists.
healthFill.Size = UDim2.fromScale(0, 1)
healthText.Text = "0"

local function onCharacter(character: Model)
	local humanoid = character:WaitForChild("Humanoid") :: Humanoid
	local function update()
		setFill(healthFill, healthText, humanoid.Health, humanoid.MaxHealth)
	end
	humanoid.HealthChanged:Connect(update)
	humanoid:GetPropertyChangedSignal("MaxHealth"):Connect(update)
	update()

	local function updateArmor()
		local max = humanoid:GetAttribute("MaxArmor") or 0
		setFill(armorFill, armorText, humanoid:GetAttribute("Armor") or 0, max)
	end
	humanoid:GetAttributeChangedSignal("Armor"):Connect(updateArmor)
	humanoid:GetAttributeChangedSignal("MaxArmor"):Connect(updateArmor)
	updateArmor()
end
player.CharacterAdded:Connect(onCharacter)
if player.Character then
	task.spawn(onCharacter, player.Character)
end
