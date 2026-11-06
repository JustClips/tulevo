--[[
	Knocked down screen + ragdoll on your own client (server side: Server/Knocked).

	Health 0 no longer kills: the Dead state is off here and on the server. When the server
	marks the character Knocked (and has swapped the joints for loose BallSockets), this
	script lets the body fall: Physics humanoid state, every animation stopped, a small random
	push so nobody lands the same way. The world goes black and white and the "ВЫ РАНЕНЫ"
	screen shows two buttons:
	  - "Ожидать помощи": stay down and wait (the button turns into a wait timer).
	  - "Потерять сознание": respawn.
	If the server revives the character (Knocked back to false), the body gets up again.
]]

local GuiService = game:GetService("GuiService")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local player = Players.LocalPlayer
local settings = Config.Knocked or {}
if settings.Enabled == false then
	return
end

local remotes = ReplicatedStorage:WaitForChild("KnockedRemotes")
local GiveUpRemote = remotes:WaitForChild("GiveUp") :: RemoteEvent
local WaitHelpRemote = remotes:WaitForChild("WaitHelp") :: RemoteEvent

local TITLE_FONT = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.Heavy, Enum.FontStyle.Italic)
local BODY_FONT = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.Medium)
local BUTTON_FONT = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.SemiBold)
local SMALL_FONT = Font.new("rbxasset://fonts/families/Montserrat.json", Enum.FontWeight.Bold)

local RED = Color3.fromRGB(214, 38, 46)
local BUTTON_BG = Color3.fromRGB(14, 14, 16)
local BUTTON_HOVER = Color3.fromRGB(34, 34, 38)

local TEXT = {
	Tag = "КРИТИЧЕСКОЕ СОСТОЯНИЕ",
	Title = "ВЫ РАНЕНЫ",
	Body = "Вы получили тяжёлые ранения и не можете подняться.\nОрганизм держится из последних сил.",
	BodyWaiting = "Вы ждёте помощи. Кто-то рядом может\nпоставить вас на ноги.",
	BodyHelped = "%s поднимает вас...",
	Wait = "Ожидать помощи",
	Waiting = "Ожидание помощи",
	GiveUp = "Потерять сознание",
}

----------------------------------------------------------------------------- the screen

local gui = Instance.new("ScreenGui")
gui.Name = "Knocked"
gui.IgnoreGuiInset = true
gui.ResetOnSpawn = false
gui.DisplayOrder = 50
gui.Enabled = false
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.Parent = player:WaitForChild("PlayerGui")

-- dark edges, darker at the top and bottom
local shade = Instance.new("Frame")
shade.Name = "Shade"
shade.Size = UDim2.fromScale(1, 1)
shade.BackgroundColor3 = Color3.new(0, 0, 0)
shade.BackgroundTransparency = 0.25
shade.BorderSizePixel = 0
shade.Parent = gui
local shadeFade = Instance.new("UIGradient")
shadeFade.Rotation = 90
shadeFade.Transparency = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 0.2),
	NumberSequenceKeypoint.new(0.3, 0.85),
	NumberSequenceKeypoint.new(0.7, 0.85),
	NumberSequenceKeypoint.new(1, 0.2),
})
shadeFade.Parent = shade

-- red heartbeat glow on the screen edges
local pulse = Instance.new("Frame")
pulse.Name = "Pulse"
pulse.Size = UDim2.fromScale(1, 1)
pulse.BackgroundColor3 = RED
pulse.BackgroundTransparency = 1
pulse.BorderSizePixel = 0
pulse.Parent = gui
local pulseFade = Instance.new("UIGradient")
pulseFade.Transparency = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 0),
	NumberSequenceKeypoint.new(0.18, 1),
	NumberSequenceKeypoint.new(0.82, 1),
	NumberSequenceKeypoint.new(1, 0),
})
pulseFade.Parent = pulse

-- the band across the middle of the screen
local band = Instance.new("Frame")
band.Name = "Band"
band.AnchorPoint = Vector2.new(0.5, 0.5)
band.Position = UDim2.fromScale(0.5, 0.5)
band.Size = UDim2.new(1, 0, 0, 380)
band.BackgroundColor3 = Color3.fromRGB(8, 8, 10)
band.BackgroundTransparency = 0.3
band.BorderSizePixel = 0
band.Parent = gui
local bandFade = Instance.new("UIGradient")
bandFade.Rotation = 90
bandFade.Transparency = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 1),
	NumberSequenceKeypoint.new(0.18, 0),
	NumberSequenceKeypoint.new(0.82, 0),
	NumberSequenceKeypoint.new(1, 1),
})
bandFade.Parent = band

local content = Instance.new("Frame")
content.Name = "Content"
content.AnchorPoint = Vector2.new(0.5, 0.5)
content.Position = UDim2.fromScale(0.5, 0.5)
content.Size = UDim2.fromOffset(600, 330)
content.BackgroundTransparency = 1
content.Parent = band
local scale = Instance.new("UIScale")
scale.Parent = content

local function label(name: string, text: string, font: Font, size: number, y: number, h: number): TextLabel
	local t = Instance.new("TextLabel")
	t.Name = name
	t.BackgroundTransparency = 1
	t.Position = UDim2.fromOffset(0, y)
	t.Size = UDim2.new(1, 0, 0, h)
	t.FontFace = font
	t.Text = text
	t.TextSize = size
	t.TextColor3 = Color3.new(1, 1, 1)
	t.TextXAlignment = Enum.TextXAlignment.Center
	t.TextYAlignment = Enum.TextYAlignment.Center
	t.Parent = content
	return t
end

local tag = label("Tag", TEXT.Tag, SMALL_FONT, 15, 0, 22)
tag.TextColor3 = RED
local title = label("Title", TEXT.Title, TITLE_FONT, 72, 24, 86)
local titleStroke = Instance.new("UIStroke")
titleStroke.Thickness = 1.5
titleStroke.Transparency = 0.6
titleStroke.Color = Color3.new(0, 0, 0)
titleStroke.Parent = title

-- red line under the title, brightest in the middle
local line = Instance.new("Frame")
line.Name = "Line"
line.AnchorPoint = Vector2.new(0.5, 0)
line.Position = UDim2.fromOffset(300, 116)
line.Size = UDim2.fromOffset(0, 4)
line.BackgroundColor3 = RED
line.BorderSizePixel = 0
line.Parent = content
local lineFade = Instance.new("UIGradient")
lineFade.Transparency = NumberSequence.new({
	NumberSequenceKeypoint.new(0, 1),
	NumberSequenceKeypoint.new(0.2, 0),
	NumberSequenceKeypoint.new(0.8, 0),
	NumberSequenceKeypoint.new(1, 1),
})
lineFade.Parent = line

local body = label("Body", TEXT.Body, BODY_FONT, 20, 138, 60)
body.TextColor3 = Color3.fromRGB(225, 225, 225)
body.TextWrapped = true

local buttons = Instance.new("Frame")
buttons.Name = "Buttons"
buttons.AnchorPoint = Vector2.new(0.5, 0)
buttons.Position = UDim2.fromOffset(300, 228)
buttons.Size = UDim2.fromOffset(500, 58)
buttons.BackgroundTransparency = 1
buttons.Parent = content
local row = Instance.new("UIListLayout")
row.FillDirection = Enum.FillDirection.Horizontal
row.HorizontalAlignment = Enum.HorizontalAlignment.Center
row.Padding = UDim.new(0, 16)
row.SortOrder = Enum.SortOrder.LayoutOrder
row.Parent = buttons

local function button(name: string, text: string, order: number): TextButton
	local b = Instance.new("TextButton")
	b.Name = name
	b.LayoutOrder = order
	b.Size = UDim2.fromOffset(242, 58)
	b.AutoButtonColor = false
	b.BackgroundColor3 = BUTTON_BG
	b.BackgroundTransparency = 0.05
	b.BorderSizePixel = 0
	b.FontFace = BUTTON_FONT
	b.Text = text
	b.TextSize = 19
	b.TextColor3 = Color3.new(1, 1, 1)
	b.Modal = true -- frees the mouse even in first person
	b.Parent = buttons
	local corner = Instance.new("UICorner")
	corner.CornerRadius = UDim.new(0, 4)
	corner.Parent = b
	local stroke = Instance.new("UIStroke")
	stroke.ApplyStrokeMode = Enum.ApplyStrokeMode.Border
	stroke.Color = Color3.fromRGB(70, 70, 76)
	stroke.Thickness = 1
	stroke.Parent = b
	-- red mark on the left edge, shown on hover / while chosen
	local mark = Instance.new("Frame")
	mark.Name = "Mark"
	mark.Size = UDim2.new(0, 4, 1, 0)
	mark.BackgroundColor3 = RED
	mark.BorderSizePixel = 0
	mark.Visible = false
	mark.Parent = b
	local function hover(on: boolean)
		local chosen = b:GetAttribute("Chosen") == true
		b.BackgroundColor3 = if on or chosen then BUTTON_HOVER else BUTTON_BG
		stroke.Color = if on then RED else Color3.fromRGB(70, 70, 76)
		mark.Visible = on or chosen
	end
	b.MouseEnter:Connect(function()
		hover(true)
	end)
	b.MouseLeave:Connect(function()
		hover(false)
	end)
	b.SelectionGained:Connect(function()
		hover(true)
	end)
	b.SelectionLost:Connect(function()
		hover(false)
	end)
	b:GetAttributeChangedSignal("Chosen"):Connect(function()
		hover(false)
	end)
	return b
end

local waitButton = button("WaitHelp", TEXT.Wait, 1)
local giveUpButton = button("GiveUp", TEXT.GiveUp, 2)
waitButton.NextSelectionRight = giveUpButton
giveUpButton.NextSelectionLeft = waitButton

-- fits phones: shrink the content (the band stays full width)
local function fit()
	local cam = workspace.CurrentCamera
	local vp = if cam then cam.ViewportSize else Vector2.new(1280, 720)
	local s = math.clamp(math.min(vp.X / 680, vp.Y / 520), 0.5, 1)
	scale.Scale = s
	band.Size = UDim2.new(1, 0, 0, 380 * s)
end
fit()
if workspace.CurrentCamera then
	workspace.CurrentCamera:GetPropertyChangedSignal("ViewportSize"):Connect(fit)
end

local grey = Instance.new("ColorCorrectionEffect")
grey.Name = "KnockedGrey"
grey.Enabled = false
grey.Parent = Lighting

----------------------------------------------------------------------------- state

local knockedAt: number? = nil
local waiting = false
local shownAt = 0
local oldMinZoom: number? = nil
local loop: RBXScriptConnection? = nil
local tweens: { Tween } = {}

local function tween(obj: Instance, time: number, props: { [string]: any }, style: Enum.EasingStyle?)
	local t = TweenService:Create(obj, TweenInfo.new(time, style or Enum.EasingStyle.Quad, Enum.EasingDirection.Out), props)
	t:Play()
	table.insert(tweens, t)
	return t
end

local function stopTweens()
	for _, t in tweens do
		t:Cancel()
	end
	table.clear(tweens)
end

local function clock(seconds: number): string
	seconds = math.max(0, math.floor(seconds))
	return string.format("%02d:%02d", seconds // 60, seconds % 60)
end

local function showScreen()
	stopTweens()
	waiting = false
	shownAt = os.clock()
	waitButton:SetAttribute("Chosen", false)
	waitButton.Text = TEXT.Wait
	body.Text = TEXT.Body
	gui.Enabled = true
	-- fade in: grey world, band, title, line, then the buttons
	grey.Enabled = true
	grey.Saturation, grey.Contrast, grey.Brightness = 0, 0, 0
	tween(grey, 1.2, { Saturation = -1, Contrast = 0.12, Brightness = -0.04 })
	shade.BackgroundTransparency = 1
	tween(shade, 1, { BackgroundTransparency = 0.25 })
	band.BackgroundTransparency = 1
	tween(band, 0.8, { BackgroundTransparency = 0.3 })
	for _, t in { tag, title, body } do
		t.TextTransparency = 1
	end
	titleStroke.Transparency = 1
	tween(tag, 0.6, { TextTransparency = 0 })
	title.Position = UDim2.fromOffset(-30, 24)
	tween(title, 0.7, { TextTransparency = 0, Position = UDim2.fromOffset(0, 24) }, Enum.EasingStyle.Quart)
	tween(titleStroke, 0.7, { Transparency = 0.6 })
	line.Size = UDim2.fromOffset(0, 4)
	task.delay(0.25, function()
		if gui.Enabled then
			tween(line, 0.7, { Size = UDim2.fromOffset(420, 4) }, Enum.EasingStyle.Quart)
		end
	end)
	tween(body, 1.2, { TextTransparency = 0 })
	buttons.Visible = false
	task.delay(math.max(1.2, settings.GiveUpDelay or 0), function()
		if gui.Enabled and knockedAt then
			buttons.Visible = true
			if UserInputService.GamepadEnabled then
				GuiService.SelectedObject = waitButton
			end
		end
	end)
end

local function hideScreen()
	stopTweens()
	gui.Enabled = false
	grey.Enabled = false
	if GuiService.SelectedObject and GuiService.SelectedObject:IsDescendantOf(gui) then
		GuiService.SelectedObject = nil
	end
end

local KEEP_DOWN = Enum.HumanoidStateType.Physics

local function fall(character: Model, humanoid: Humanoid)
	humanoid.AutoRotate = false
	humanoid:ChangeState(KEEP_DOWN)
	-- random push so the body tips over a different way every time
	local ut = character:FindFirstChild("UpperTorso") :: BasePart?
	local push = settings.FallPush or 9
	if ut then
		local a = math.random() * math.pi * 2
		local dir = Vector3.new(math.cos(a), 0, math.sin(a))
		local mass = ut.AssemblyMass
		ut:ApplyImpulseAtPosition(dir * push * mass, ut.Position + Vector3.new(0, 1, 0))
	end
	-- out of first person while lying down
	oldMinZoom = player.CameraMinZoomDistance
	player.CameraMinZoomDistance = math.max(oldMinZoom, settings.CameraMinZoom or 9)
end

local function getUp(humanoid: Humanoid?)
	if oldMinZoom then
		player.CameraMinZoomDistance = oldMinZoom
		oldMinZoom = nil
	end
	if humanoid and humanoid.Parent then
		humanoid.AutoRotate = true
		humanoid:ChangeState(Enum.HumanoidStateType.GettingUp)
	end
end

local function leave(humanoid: Humanoid?)
	if loop then
		loop:Disconnect()
		loop = nil
	end
	if knockedAt then
		knockedAt = nil
		getUp(humanoid)
	end
	hideScreen()
end

local function enter(character: Model, humanoid: Humanoid)
	if knockedAt then
		return
	end
	knockedAt = os.clock()
	fall(character, humanoid)
	showScreen()
	local animator = humanoid:FindFirstChildOfClass("Animator")
	local beat = 0
	loop = RunService.Heartbeat:Connect(function(dt)
		if not humanoid.Parent then
			leave(nil)
			return
		end
		-- stay limp: no animations, no getting up on our own
		if humanoid:GetState() ~= KEEP_DOWN then
			humanoid:ChangeState(KEEP_DOWN)
		end
		if animator then
			for _, track in animator:GetPlayingAnimationTracks() do
				track:Stop(0.15)
			end
		end
		-- slow heartbeat on the screen edges and the title
		beat += dt
		local t = beat % 1.4
		local thump = math.max(0, 1 - t / 0.35) + 0.6 * math.max(0, 1 - math.abs(t - 0.32) / 0.25)
		pulse.BackgroundTransparency = 1 - 0.22 * math.min(1, thump)
		-- nobody sees a prompt on their own body
		local prompt = character:FindFirstChild("KnockedRevive", true)
		if prompt and prompt:IsA("ProximityPrompt") and prompt.Enabled then
			prompt.Enabled = false
		end
		local helper = character:GetAttribute("BeingHelped")
		local want = if typeof(helper) == "string"
			then string.format(TEXT.BodyHelped, helper)
			elseif waiting then TEXT.BodyWaiting
			else TEXT.Body
		if body.Text ~= want then
			body.Text = want
		end
		if waiting then
			waitButton.Text = `{TEXT.Waiting}  {clock(os.clock() - (knockedAt or os.clock()))}`
		end
		-- the gun's mouse lock must not trap the cursor here
		if UserInputService.MouseBehavior ~= Enum.MouseBehavior.Default then
			UserInputService.MouseBehavior = Enum.MouseBehavior.Default
		end
		UserInputService.MouseIconEnabled = true
	end)
end

waitButton.Activated:Connect(function()
	if not knockedAt or waiting then
		return
	end
	waiting = true
	waitButton:SetAttribute("Chosen", true)
	body.Text = TEXT.BodyWaiting
	WaitHelpRemote:FireServer()
end)

giveUpButton.Activated:Connect(function()
	if not knockedAt or os.clock() - shownAt < (settings.GiveUpDelay or 0) then
		return
	end
	giveUpButton.Text = "..."
	GiveUpRemote:FireServer()
	task.delay(3, function()
		giveUpButton.Text = TEXT.GiveUp
	end)
end)

----------------------------------------------------------------------------- characters

local function bind(character: Model)
	leave(nil)
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if not humanoid then
		return
	end
	-- health 0 must not kill (the server does the same)
	humanoid:SetStateEnabled(Enum.HumanoidStateType.Dead, false)
	local function check()
		if player.Character ~= character then
			return
		end
		if character:GetAttribute("Knocked") == true then
			enter(character, humanoid)
		elseif knockedAt then
			leave(humanoid)
		end
	end
	character:GetAttributeChangedSignal("Knocked"):Connect(check)
	humanoid.Died:Connect(function()
		leave(nil)
	end)
	check()
end

player.CharacterAdded:Connect(bind)
player.CharacterRemoving:Connect(function()
	leave(nil)
end)
if player.Character then
	task.spawn(bind, player.Character)
end
