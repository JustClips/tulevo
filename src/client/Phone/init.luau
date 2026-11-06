--[[
	Phone: the in-game phone (docs/phone.md).

	Phone.start()            build it and bind the key (PhoneRunner.client does this)
	Phone.open() / close() / toggle() / isOpen()
	Phone.openApp(id)        open an app page (opens the phone first if needed)
	Phone.home()             back to the home screen
	Phone.notify(text, s?)   grow the Dynamic Island with a short message
	Phone.Opened / Closed    events

	Apps are ModuleScripts in Phone/Apps. A module returns one app or a list of apps:
		{
			Id = "Bank", Name = "Bank", Color = Color3, Icon = "rbxassetid://..." (or nil = first letter),
			Order = 12, Dock = false,
			open = function(page: Frame, phone) ... end,  -- build the app's page (optional)
			close = function(page: Frame) ... end,        -- clean up (optional)
		}

	Keys: Config.Phone.Key (up arrow, on foot only) / GamepadKey (D-pad down); phones get a
	small phone button on the right. Backspace or B goes back (app -> home -> closed).
	It opens GTA style: slides up from below the bottom-right corner and the screen wakes.
]]
local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local GameTime = require(ReplicatedStorage.Shared:WaitForChild("GameTime"))
local WeaponState = require(script.Parent:WaitForChild("Weapons"):WaitForChild("State"))

local Theme = require(script.Theme)
local Frame = require(script.Frame)
local Home = require(script.Home)
local Island = require(script.Island)

local CFG = Config.Phone
local C = Theme.Colors
local player = Players.LocalPlayer

local Phone = {}
local openedEvent = Instance.new("BindableEvent")
local closedEvent = Instance.new("BindableEvent")
Phone.Opened = openedEvent.Event
Phone.Closed = closedEvent.Event

local gui: ScreenGui
local parts
local apps = {}
local byId = {}
local isOpen = false
local moving: Tween? = nil
local currentApp = nil
local currentPage: Frame? = nil
local mouseFree: TextButton
local touchButton: TextButton?

local function touch(): boolean
	return UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled
end

-- ----------------------------------------------------------------- apps
local function addApp(def)
	assert(type(def.Id) == "string" and type(def.Name) == "string", "phone app needs Id and Name")
	assert(not byId[def.Id], "two phone apps use the Id " .. def.Id)
	byId[def.Id] = def
	table.insert(apps, def)
end

local function loadApps()
	for _, mod in script.Apps:GetChildren() do
		if mod:IsA("ModuleScript") then
			local ok, result = pcall(require, mod)
			if not ok then
				warn("[Phone] app module " .. mod.Name .. " failed: " .. tostring(result))
			elseif type(result) == "table" and result.Id then
				addApp(result)
			elseif type(result) == "table" then
				for _, def in result do
					addApp(def)
				end
			end
		end
	end
	table.sort(apps, function(a, b)
		return (a.Order or 100) < (b.Order or 100)
	end)
end

-- the empty page an app without its own open() gets
local function emptyPage(page: Frame, app)
	Frame.new("TextLabel", {
		Parent = page,
		BackgroundTransparency = 1,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.45),
		Size = UDim2.new(1, -40, 0, 20),
		FontFace = Theme.Regular,
		TextSize = 14,
		TextColor3 = C.Dim,
		Text = "Coming soon",
		ZIndex = 22,
	})
end

local function slide(page: Frame, from: UDim2, to: UDim2, t: number)
	page.Position = from
	local tw = TweenService:Create(page, TweenInfo.new(t, Enum.EasingStyle.Quint, Enum.EasingDirection.Out), { Position = to })
	tw:Play()
	return tw
end

local function closeApp(animate: boolean)
	local page, app = currentPage, currentApp
	currentPage, currentApp = nil, nil
	if not page then
		return
	end
	if app and app.close then
		task.spawn(app.close, page)
	end
	if animate then
		slide(page, page.Position, UDim2.fromScale(1, 0), 0.25).Completed:Connect(function()
			page:Destroy()
		end)
	else
		page:Destroy()
	end
end

function Phone.home()
	closeApp(true)
end

function Phone.openApp(id: string)
	local app = byId[id]
	if not app then
		warn("[Phone] no app " .. tostring(id))
		return
	end
	if not isOpen then
		Phone.open()
	end
	if currentApp == app then
		return
	end
	closeApp(false)
	local page = Frame.new("Frame", {
		Name = "App_" .. app.Id,
		Parent = parts.pages,
		Size = UDim2.fromScale(1, 1),
		BackgroundColor3 = C.Page,
		BorderSizePixel = 0,
		ZIndex = 20,
	}, { Frame.corner(Theme.ScreenRadius) })
	-- title under the status bar
	Frame.new("TextLabel", {
		Name = "Title",
		Parent = page,
		BackgroundTransparency = 1,
		Position = UDim2.fromOffset(20, Theme.StatusBar + 6),
		Size = UDim2.new(1, -40, 0, 34),
		FontFace = Theme.Bold,
		TextSize = 28,
		TextColor3 = C.Text,
		TextXAlignment = Enum.TextXAlignment.Left,
		Text = app.Name,
		ZIndex = 22,
	})
	currentApp, currentPage = app, page
	if app.open then
		task.spawn(app.open, page, Phone)
	else
		emptyPage(page, app)
	end
	slide(page, UDim2.fromScale(1, 0), UDim2.fromScale(0, 0), 0.3)
end

function Phone.notify(text: string, seconds: number?)
	Island.show(text, seconds)
end

-- ----------------------------------------------------------------- open / close
local function scaleNow(): number
	local cam = workspace.CurrentCamera
	local vh = if cam then cam.ViewportSize.Y else 900
	local share = if touch() then CFG.TouchScreenHeight else CFG.ScreenHeight
	return vh * share / parts.size.Y
end

local function margin(): number
	return if touch() then 12 else 36
end

-- where the phone sits open, and parked below the screen edge when closed
local function openPos(): UDim2
	return UDim2.new(1, -margin(), 1, -margin())
end
local function closedPos(): UDim2
	return UDim2.new(1, -margin(), 1, parts.size.Y * parts.scale.Scale + 40)
end

local function layout()
	parts.scale.Scale = scaleNow()
	if not moving then
		parts.holder.Position = if isOpen then openPos() else closedPos()
	end
end

local function canOpen(): boolean
	local char = player.Character
	if char and char:GetAttribute("Knocked") == true then
		return false
	end
	return true
end

function Phone.isOpen(): boolean
	return isOpen
end

function Phone.open()
	if isOpen or not canOpen() then
		return
	end
	isOpen = true
	layout()
	if moving then
		moving:Cancel()
	end
	local h = parts.holder
	h.Visible = true
	h.Rotation = 4
	parts.sleepCover.BackgroundTransparency = 0
	mouseFree.Modal = true
	-- GTA style: fast rise from under the corner, slow settle
	local info = TweenInfo.new(CFG.OpenTime, Enum.EasingStyle.Quint, Enum.EasingDirection.Out)
	moving = TweenService:Create(h, info, { Position = openPos(), Rotation = 0 })
	moving.Completed:Connect(function(state)
		if state == Enum.PlaybackState.Completed then
			moving = nil
		end
	end)
	moving:Play()
	-- screen wakes as it arrives
	task.delay(CFG.OpenTime * 0.45, function()
		if isOpen then
			TweenService:Create(parts.sleepCover, TweenInfo.new(0.25), { BackgroundTransparency = 1 }):Play()
		end
	end)
	openedEvent:Fire()
end

function Phone.close()
	if not isOpen then
		return
	end
	isOpen = false
	mouseFree.Modal = false
	if moving then
		moving:Cancel()
	end
	TweenService:Create(parts.sleepCover, TweenInfo.new(0.12), { BackgroundTransparency = 0 }):Play()
	local info = TweenInfo.new(CFG.CloseTime, Enum.EasingStyle.Quad, Enum.EasingDirection.In)
	local tw = TweenService:Create(parts.holder, info, { Position = closedPos(), Rotation = 3 })
	moving = tw
	tw.Completed:Connect(function(state)
		if moving == tw then
			moving = nil
		end
		if state == Enum.PlaybackState.Completed and not isOpen then
			parts.holder.Visible = false
			closeApp(false)
			Island.reset()
		end
	end)
	tw:Play()
	closedEvent:Fire()
end

function Phone.toggle()
	if isOpen then
		Phone.close()
	else
		Phone.open()
	end
end

-- back: app -> home -> closed
local function back()
	if currentPage then
		Phone.home()
	else
		Phone.close()
	end
end

-- ----------------------------------------------------------------- input
local function onKey(_, state: Enum.UserInputState)
	-- in a car the arrow keys drive
	if WeaponState.InVehicle and not isOpen then
		return Enum.ContextActionResult.Pass
	end
	if state == Enum.UserInputState.Begin then
		Phone.toggle()
	end
	return Enum.ContextActionResult.Sink
end

local function onBack(_, state: Enum.UserInputState)
	if not isOpen then
		return Enum.ContextActionResult.Pass
	end
	if state == Enum.UserInputState.Begin then
		back()
	end
	return Enum.ContextActionResult.Sink
end

local function makeTouchButton()
	local b = Frame.new("TextButton", {
		Name = "PhoneButton",
		Parent = gui,
		Text = "",
		AutoButtonColor = false,
		AnchorPoint = Vector2.new(1, 0.5),
		Position = UDim2.new(1, -10, 0.42, 0),
		Size = UDim2.fromOffset(40, 40),
		BackgroundColor3 = Color3.fromRGB(20, 20, 24),
		BackgroundTransparency = 0.25,
		Visible = touch(),
	}, { Frame.corner(10) })
	-- a tiny phone outline as the button picture
	Frame.new("Frame", {
		Parent = b,
		AnchorPoint = Vector2.new(0.5, 0.5),
		Position = UDim2.fromScale(0.5, 0.5),
		Size = UDim2.fromOffset(14, 24),
		BackgroundTransparency = 1,
	}, {
		Frame.corner(4),
		Frame.new("UIStroke", { Color = Color3.new(1, 1, 1), Thickness = 2 }),
		Frame.new("Frame", {
			AnchorPoint = Vector2.new(0.5, 0),
			Position = UDim2.new(0.5, 0, 0, 3),
			Size = UDim2.fromOffset(6, 2),
			BackgroundColor3 = Color3.new(1, 1, 1),
		}, { Frame.corner(1) }),
	})
	b.Activated:Connect(Phone.toggle)
	return b
end

-- ----------------------------------------------------------------- start
function Phone.start()
	gui = Instance.new("ScreenGui")
	gui.Name = "Phone"
	gui.ResetOnSpawn = false
	gui.IgnoreGuiInset = true
	gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
	gui.DisplayOrder = 12

	-- an invisible Modal button frees the mouse (first person / shift lock) while the phone is open
	mouseFree = Frame.new("TextButton", {
		Name = "MouseFree",
		Parent = gui,
		Text = "",
		BackgroundTransparency = 1,
		Size = UDim2.fromOffset(0, 0),
	})

	parts = Frame.build(gui)
	Island.attach(parts.island)
	loadApps()
	Home.build(parts.pages, apps, function(app)
		Phone.openApp(app.Id)
	end)

	parts.homeBar.Activated:Connect(Phone.home)
	parts.homeBar:FindFirstChild("HomeHit").Activated:Connect(Phone.home)
	parts.power.Activated:Connect(Phone.close) -- side button locks it, like a real phone

	touchButton = makeTouchButton()
	gui.Parent = player:WaitForChild("PlayerGui")

	layout()
	local function watchCam()
		local cam = workspace.CurrentCamera
		if cam then
			cam:GetPropertyChangedSignal("ViewportSize"):Connect(layout)
		end
	end
	watchCam()
	workspace:GetPropertyChangedSignal("CurrentCamera"):Connect(function()
		watchCam()
		layout()
	end)
	UserInputService.LastInputTypeChanged:Connect(function()
		if touchButton then
			touchButton.Visible = touch()
		end
		layout()
	end)

	ContextActionService:BindActionAtPriority(
		"PhoneToggle",
		onKey,
		false,
		Enum.ContextActionPriority.High.Value,
		CFG.Key,
		CFG.GamepadKey
	)
	ContextActionService:BindActionAtPriority(
		"PhoneBack",
		onBack,
		false,
		Enum.ContextActionPriority.High.Value,
		Enum.KeyCode.Backspace,
		Enum.KeyCode.ButtonB
	)

	-- clock in the status bar follows the in-game time
	local shown = ""
	RunService.Heartbeat:Connect(function()
		if not isOpen then
			return
		end
		local t = GameTime.now()
		local text = if t then string.format("%d:%02d", t.hour, t.min) else "9:41"
		if text ~= shown then
			shown = text
			parts.clock.Text = text
		end
	end)

	-- knocked down or getting into a car puts the phone away
	RunService.Heartbeat:Connect(function()
		if isOpen and (not canOpen() or WeaponState.InVehicle) then
			Phone.close()
		end
	end)
end

return Phone
