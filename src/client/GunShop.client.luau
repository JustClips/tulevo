--!strict
--[[
	Gun shop buy menu (Server/GunShop, docs/gunshop.md). GTA-style list at the top left:
	shop banner, a title row with "n / m", rows with prices, and a box under it with the
	description, stat bars and the item picture. First the categories, Enter opens one.

		Up / Down (W / S, D-pad)      select
		Enter / A / click the row     open the category / buy
		Backspace / B / X button      back, or close the menu

	While it's open the camera looks at the gun wall from the shop floor, the cursor is free and
	movement, shooting and the other HUD keys are blocked (sunk here). Walking away, dying or
	being knocked down closes it. The server checks and does every purchase.
]]

local ContextActionService = game:GetService("ContextActionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local Items = require(Shared:WaitForChild("Items"))
local Weapons = require(Shared:WaitForChild("Weapons"))
local TextureIds = require(Shared:WaitForChild("TextureIds")) :: any
local HudLayout = require(script.Parent:WaitForChild("HudLayout"))
local MouseLook = require(script.Parent:WaitForChild("Movement"):WaitForChild("MouseLook")) :: any

local remotes = ReplicatedStorage:WaitForChild("GunShopRemotes")
local OpenRemote = remotes:WaitForChild("Open") :: RemoteEvent
local CloseRemote = remotes:WaitForChild("Close") :: RemoteEvent
local BuyRemote = remotes:WaitForChild("Buy") :: RemoteFunction

local player = Players.LocalPlayer
local CFG = Config.GunShop

local W = 440
local ROW_H = 36
local MAX_ROWS = 9
local BOLD = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Bold)
local SEMI = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.SemiBold)
local REG = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Regular)
local C = {
	Panel = Color3.fromRGB(0, 0, 0),
	Text = Color3.fromRGB(240, 240, 240),
	Dim = Color3.fromRGB(160, 160, 160),
	SelBg = Color3.fromRGB(240, 240, 240),
	SelText = Color3.fromRGB(10, 10, 10),
	Amber = Color3.fromRGB(232, 150, 30),
	Good = Color3.fromRGB(114, 204, 114),
	Bad = Color3.fromRGB(224, 84, 74),
}

---------------------------------------------------------------- gui

local gui = Instance.new("ScreenGui")
gui.Name = "GunShop"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 20
gui.Enabled = false
gui.Parent = player:WaitForChild("PlayerGui")

local root = Instance.new("Frame")
root.Name = "Menu"
root.BackgroundTransparency = 1
root.Size = UDim2.fromOffset(W, 0)
root.AutomaticSize = Enum.AutomaticSize.Y
root.Parent = gui
local scale = Instance.new("UIScale")
scale.Parent = root
local list = Instance.new("UIListLayout")
list.SortOrder = Enum.SortOrder.LayoutOrder
list.Parent = root

local function label(
	parent: Instance,
	text: string,
	font: Font,
	size: number,
	color: Color3,
	align: Enum.TextXAlignment?
): TextLabel
	local t = Instance.new("TextLabel")
	t.BackgroundTransparency = 1
	t.FontFace = font
	t.TextSize = size
	t.TextColor3 = color
	t.Text = text
	t.TextXAlignment = align or Enum.TextXAlignment.Left
	t.TextYAlignment = Enum.TextYAlignment.Center
	t.Parent = parent
	return t
end

-- banner: the shop's own printed sign on black
local banner = Instance.new("Frame")
banner.Name = "Banner"
banner.LayoutOrder = 1
banner.Size = UDim2.fromOffset(W, 92)
banner.BackgroundColor3 = Color3.fromRGB(22, 23, 26)
banner.BorderSizePixel = 0
banner.Parent = root
local signId = TextureIds.GunShop and TextureIds.GunShop.ShopSign
local sign = Instance.new("ImageLabel")
sign.BackgroundTransparency = 1
sign.AnchorPoint = Vector2.new(0.5, 0.5)
sign.Position = UDim2.fromScale(0.5, 0.5)
sign.Size = UDim2.fromOffset(W - 24, (W - 24) / 8)
sign.Image = if signId then `rbxassetid://{signId}` else ""
sign.Parent = banner
if not signId then
	local t = label(banner, string.upper(CFG.Name), BOLD, 40, C.Text, Enum.TextXAlignment.Center)
	t.Size = UDim2.fromScale(1, 1)
end
local closeBtn = Instance.new("TextButton")
closeBtn.Name = "Close"
closeBtn.AnchorPoint = Vector2.new(1, 0)
closeBtn.Position = UDim2.new(1, -4, 0, 4)
closeBtn.Size = UDim2.fromOffset(30, 30)
closeBtn.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
closeBtn.BackgroundTransparency = 0.3
closeBtn.BorderSizePixel = 0
closeBtn.FontFace = BOLD
closeBtn.TextSize = 18
closeBtn.TextColor3 = C.Text
closeBtn.Text = "X"
closeBtn.Parent = banner
local amber = Instance.new("Frame")
amber.BackgroundColor3 = C.Amber
amber.BorderSizePixel = 0
amber.Position = UDim2.new(0, 0, 1, -3)
amber.Size = UDim2.new(1, 0, 0, 3)
amber.Parent = banner

-- title row: "RIFLES" ... "2 / 5"
local title = Instance.new("Frame")
title.LayoutOrder = 2
title.Size = UDim2.fromOffset(W, 34)
title.BackgroundColor3 = C.Panel
title.BackgroundTransparency = 0.1
title.BorderSizePixel = 0
title.Parent = root
local titleL = label(title, "", BOLD, 18, C.Amber)
titleL.Position = UDim2.fromOffset(14, 0)
titleL.Size = UDim2.new(1, -110, 1, 0)
local titleR = label(title, "", SEMI, 16, C.Text, Enum.TextXAlignment.Right)
titleR.Position = UDim2.new(1, -110, 0, 0)
titleR.Size = UDim2.new(0, 96, 1, 0)

local rowsFrame = Instance.new("Frame")
rowsFrame.LayoutOrder = 3
rowsFrame.BackgroundTransparency = 1
rowsFrame.Size = UDim2.fromOffset(W, 0)
rowsFrame.AutomaticSize = Enum.AutomaticSize.Y
rowsFrame.Parent = root
local rowsLayout = Instance.new("UIListLayout")
rowsLayout.SortOrder = Enum.SortOrder.LayoutOrder
rowsLayout.Parent = rowsFrame

-- info box: description, stat bars, picture, money, status line
local info = Instance.new("Frame")
info.LayoutOrder = 4
info.Size = UDim2.fromOffset(W, 0)
info.AutomaticSize = Enum.AutomaticSize.Y
info.BackgroundColor3 = C.Panel
info.BackgroundTransparency = 0.25
info.BorderSizePixel = 0
info.Parent = root
local infoPad = Instance.new("UIPadding")
infoPad.PaddingLeft, infoPad.PaddingRight = UDim.new(0, 14), UDim.new(0, 14)
infoPad.PaddingTop, infoPad.PaddingBottom = UDim.new(0, 10), UDim.new(0, 12)
infoPad.Parent = info
local infoList = Instance.new("UIListLayout")
infoList.SortOrder = Enum.SortOrder.LayoutOrder
infoList.Padding = UDim.new(0, 6)
infoList.Parent = info

local topLine = Instance.new("Frame")
topLine.LayoutOrder = 1
topLine.BackgroundTransparency = 1
topLine.Size = UDim2.new(1, 0, 0, 96)
topLine.Parent = info
local desc = label(topLine, "", REG, 16, C.Text)
desc.Size = UDim2.new(1, -110, 1, 0)
desc.TextWrapped = true
desc.TextYAlignment = Enum.TextYAlignment.Top
local pic = Instance.new("ImageLabel")
pic.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
pic.BackgroundTransparency = 0.92
pic.BorderSizePixel = 0
pic.AnchorPoint = Vector2.new(1, 0)
pic.Position = UDim2.fromScale(1, 0)
pic.Size = UDim2.fromOffset(96, 96)
pic.ScaleType = Enum.ScaleType.Fit
pic.Parent = topLine

local stats = Instance.new("Frame")
stats.LayoutOrder = 2
stats.BackgroundTransparency = 1
stats.Size = UDim2.new(1, 0, 0, 0)
stats.AutomaticSize = Enum.AutomaticSize.Y
stats.Parent = info
local statsList = Instance.new("UIListLayout")
statsList.Padding = UDim.new(0, 5)
statsList.SortOrder = Enum.SortOrder.LayoutOrder
statsList.Parent = stats

local bars: { [string]: Frame } = {}
for i, name in { "Damage", "Fire rate", "Accuracy", "Range" } do
	local row = Instance.new("Frame")
	row.LayoutOrder = i
	row.BackgroundTransparency = 1
	row.Size = UDim2.new(1, 0, 0, 14)
	row.Parent = stats
	local l = label(row, string.upper(name), SEMI, 13, C.Dim)
	l.Size = UDim2.new(0, 110, 1, 0)
	local back = Instance.new("Frame")
	back.Position = UDim2.fromOffset(110, 3)
	back.Size = UDim2.new(1, -110, 0, 8)
	back.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
	back.BackgroundTransparency = 0.8
	back.BorderSizePixel = 0
	back.Parent = row
	local fill = Instance.new("Frame")
	fill.Size = UDim2.fromScale(0, 1)
	fill.BackgroundColor3 = C.Text
	fill.BorderSizePixel = 0
	fill.Parent = back
	bars[name] = fill
end

local moneyLine = label(info, "", SEMI, 15, C.Text)
moneyLine.LayoutOrder = 3
moneyLine.Size = UDim2.new(1, 0, 0, 20)
moneyLine.RichText = true

local buyBtn = Instance.new("TextButton")
buyBtn.LayoutOrder = 4
buyBtn.Size = UDim2.new(1, 0, 0, 38)
buyBtn.BackgroundColor3 = C.Amber
buyBtn.BorderSizePixel = 0
buyBtn.FontFace = BOLD
buyBtn.TextSize = 18
buyBtn.TextColor3 = Color3.fromRGB(15, 15, 15)
buyBtn.Text = "BUY"
buyBtn.Parent = info

local status = label(info, "", SEMI, 15, C.Good)
status.LayoutOrder = 5
status.Size = UDim2.new(1, 0, 0, 18)

local hints = label(
	gui,
	"ENTER  Select / Buy     BACKSPACE  Back     ARROWS  Choose",
	SEMI,
	15,
	C.Text,
	Enum.TextXAlignment.Right
)
hints.AnchorPoint = Vector2.new(1, 1)
hints.Position = UDim2.new(1, -24, 1, -18)
hints.Size = UDim2.fromOffset(600, 24)
hints.TextStrokeTransparency = 0.4

---------------------------------------------------------------- state

type Entry = { Index: number, Category: string, Id: string, Price: number, Count: number, State: string }
type Shop = { Name: string, Categories: { string }, Stock: { Entry }, Camera: CFrame?, At: Vector3? }

local shop: Shop? = nil
local open = false
local category: string? = nil -- nil = the category list
local sel = 1
local scroll = 0
local busy = false
local rows: { TextButton } = {}
local statusToken = 0

local function money(n: number): string
	local s = tostring(math.floor(n))
	local out = s:reverse():gsub("(%d%d%d)", "%1,"):reverse()
	return "$" .. out:gsub("^,", "")
end

local function entriesIn(cat: string): { Entry }
	local out = {}
	if shop then
		for _, e in (shop :: Shop).Stock do
			if e.Category == cat then
				table.insert(out, e)
			end
		end
	end
	return out
end

local function choices(): { any }
	if not shop then
		return {}
	end
	if category then
		return entriesIn(category :: string)
	end
	local out = {}
	for _, cat in (shop :: Shop).Categories do
		if #entriesIn(cat) > 0 then
			table.insert(out, cat)
		end
	end
	return out
end

local function entryName(e: Entry): string
	local def = Items.get(e.Id)
	local name = if def then def.Name else e.Id
	if e.Count > 1 then
		name ..= ` x{e.Count}`
	end
	return name
end

local function setStatus(text: string, good: boolean)
	statusToken += 1
	local my = statusToken
	status.Text = text
	status.TextColor3 = if good then C.Good else C.Bad
	task.delay(3, function()
		if statusToken == my then
			status.Text = ""
		end
	end)
end

local function setBars(e: Entry?)
	local w = e and Weapons.get(e.Id) :: any
	stats.Visible = w ~= nil
	if not w then
		return
	end
	local dmg = (w.Damage or 0) * (w.Pellets or 1)
	local vals = {
		Damage = dmg / 120,
		["Fire rate"] = (w.FireRate or 1) / 14,
		Accuracy = 1 - math.clamp((w.AimSpread or w.Spread or 3) / 6, 0, 0.95),
		Range = (w.Range or 0) / 500,
	}
	for name, fill in bars do
		TweenService
			:Create(fill, TweenInfo.new(0.2), { Size = UDim2.fromScale(math.clamp(vals[name] or 0, 0.04, 1), 1) })
			:Play()
	end
end

local function render()
	if not shop then
		return
	end
	local items = choices()
	sel = math.clamp(sel, 1, math.max(1, #items))
	if sel <= scroll then
		scroll = sel - 1
	elseif sel > scroll + MAX_ROWS then
		scroll = sel - MAX_ROWS
	end
	titleL.Text = if category then string.upper(category :: string) else "CATEGORIES"
	titleR.Text = `{sel} / {#items}`
	for i = 1, MAX_ROWS do
		local row = rows[i]
		local item = items[i + scroll]
		row.Visible = item ~= nil
		if item then
			local selected = i + scroll == sel
			local left = row:FindFirstChild("L") :: TextLabel
			local right = row:FindFirstChild("R") :: TextLabel
			row.BackgroundColor3 = if selected then C.SelBg else C.Panel
			row.BackgroundTransparency = if selected then 0.05 else 0.4
			local textColor = if selected then C.SelText else C.Text
			if typeof(item) == "string" then
				left.Text = item
				right.Text = ">"
				left.TextColor3, right.TextColor3 = textColor, textColor
			else
				local e = item :: Entry
				left.Text = entryName(e)
				left.TextColor3 = if e.State == "soldout" and not selected then C.Dim else textColor
				if e.State == "owned" then
					right.Text = "OWNED"
				elseif e.State == "soldout" then
					right.Text = "OUT OF STOCK"
				else
					right.Text = money(e.Price)
				end
				right.TextColor3 = if e.State == "buy"
					then (if selected then C.SelText else C.Good)
					else (if selected then C.SelText else C.Dim)
			end
		end
	end
	-- info box
	local item = items[sel]
	local cash, bank = player:GetAttribute("Cash") or 0, player:GetAttribute("Bank") or 0
	moneyLine.Text =
		`CASH <font color="#72CC72">{money(cash)}</font>     BANK <font color="#72CC72">{money(bank)}</font>`
	if typeof(item) == "table" then
		local e = item :: Entry
		local def = Items.get(e.Id)
		desc.Text = if def then (def.Description or def.Name) else e.Id
		pic.Image = if def and def.Icon then def.Icon else ""
		pic.Visible = true
		setBars(e)
		buyBtn.Visible = true
		buyBtn.Text = if e.State == "buy"
			then `BUY  {money(e.Price)}`
			elseif e.State == "owned" then "OWNED"
			else "OUT OF STOCK"
		buyBtn.BackgroundColor3 = if e.State == "buy" then C.Amber else Color3.fromRGB(70, 70, 70)
		buyBtn.TextColor3 = if e.State == "buy" then Color3.fromRGB(15, 15, 15) else C.Dim
	else
		local n = typeof(item) == "string" and #entriesIn(item :: string) or 0
		desc.Text = if item then `{n} item{if n == 1 then "" else "s"} in stock. Press Enter to look.` else ""
		pic.Visible = false
		setBars(nil)
		buyBtn.Visible = false
	end
end

local function activate()
	if not shop or busy then
		return
	end
	local items = choices()
	local item = items[sel]
	if typeof(item) == "string" then
		category = item :: string
		sel, scroll = 1, 0
		render()
		return
	end
	if typeof(item) ~= "table" then
		return
	end
	local e = item :: Entry
	if e.State == "owned" then
		setStatus("You already own this", false)
		return
	elseif e.State == "soldout" then
		setStatus("Out of stock", false)
		return
	end
	busy = true
	local ok, result = pcall(function()
		return BuyRemote:InvokeServer(e.Index)
	end)
	busy = false
	if not ok or typeof(result) ~= "table" then
		setStatus("Couldn't reach the shop", false)
		return
	end
	if result.shop and shop then
		(shop :: Shop).Stock = result.shop.Stock
	end
	setStatus(result.message or "", result.ok == true)
	render()
end

for i = 1, MAX_ROWS do
	local row = Instance.new("TextButton")
	row.Name = `Row{i}`
	row.LayoutOrder = i
	row.AutoButtonColor = false
	row.Text = ""
	row.Size = UDim2.fromOffset(W, ROW_H)
	row.BorderSizePixel = 0
	row.Parent = rowsFrame
	local l = label(row, "", SEMI, 17, C.Text)
	l.Name = "L"
	l.Position = UDim2.fromOffset(14, 0)
	l.Size = UDim2.new(1, -170, 1, 0)
	local r = label(row, "", SEMI, 17, C.Text, Enum.TextXAlignment.Right)
	r.Name = "R"
	r.Position = UDim2.new(1, -164, 0, 0)
	r.Size = UDim2.new(0, 150, 1, 0)
	row.MouseButton1Click:Connect(function()
		local idx = i + scroll
		if idx == sel then
			activate()
		else
			sel = idx
			render()
		end
	end)
	rows[i] = row
end

---------------------------------------------------------------- open / close

local savedCam: { type: Enum.CameraType, cf: CFrame }? = nil
local renderConn: RBXScriptConnection? = nil
local SINK = {
	Enum.KeyCode.W,
	Enum.KeyCode.A,
	Enum.KeyCode.S,
	Enum.KeyCode.D,
	Enum.KeyCode.Up,
	Enum.KeyCode.Down,
	Enum.KeyCode.Left,
	Enum.KeyCode.Right,
	Enum.KeyCode.Space,
	Enum.KeyCode.Return,
	Enum.KeyCode.KeypadEnter,
	Enum.KeyCode.Backspace,
	Enum.KeyCode.ButtonA,
	Enum.KeyCode.ButtonB,
	Enum.KeyCode.DPadUp,
	Enum.KeyCode.DPadDown,
	Enum.KeyCode.DPadLeft,
	Enum.KeyCode.DPadRight,
	Enum.KeyCode.Thumbstick1,
	Enum.KeyCode.LeftShift,
	Enum.KeyCode.LeftControl,
	Enum.KeyCode.C,
	Enum.KeyCode.R,
	Enum.KeyCode.Q,
	Enum.KeyCode.E,
	Enum.KeyCode.N,
	Enum.KeyCode.Tab,
	Enum.KeyCode.One,
	Enum.KeyCode.Two,
	Enum.KeyCode.Three,
	Enum.KeyCode.ButtonR2,
	Enum.KeyCode.ButtonL2,
	Enum.KeyCode.ButtonX,
	Enum.KeyCode.ButtonY,
	Enum.UserInputType.MouseButton1,
	Enum.UserInputType.MouseButton2,
}

local close: () -> ()

local function onKey(_: string, state: Enum.UserInputState, input: InputObject): Enum.ContextActionResult
	if state ~= Enum.UserInputState.Begin then
		return Enum.ContextActionResult.Sink
	end
	local k = input.KeyCode
	local n = #choices()
	if k == Enum.KeyCode.Up or k == Enum.KeyCode.W or k == Enum.KeyCode.DPadUp then
		sel = if sel <= 1 then n else sel - 1
		render()
	elseif k == Enum.KeyCode.Down or k == Enum.KeyCode.S or k == Enum.KeyCode.DPadDown then
		sel = if sel >= n then 1 else sel + 1
		render()
	elseif k == Enum.KeyCode.Return or k == Enum.KeyCode.KeypadEnter or k == Enum.KeyCode.ButtonA then
		activate()
	elseif k == Enum.KeyCode.Backspace or k == Enum.KeyCode.ButtonB then
		if category then
			local back = category
			category = nil
			sel, scroll = table.find(choices(), back) or 1, 0
			render()
		else
			close()
		end
	end
	return Enum.ContextActionResult.Sink
end

local function layout()
	local l = HudLayout.get()
	scale.Scale = l.scale
	root.Position = if l.touch
		then UDim2.fromOffset(12 * l.scale, 12 * l.scale)
		else UDim2.fromOffset(40 * l.scale, 40 * l.scale)
	hints.Visible = not l.touch
end
HudLayout.Changed:Connect(layout)
layout()

close = function()
	if not open then
		return
	end
	open = false
	gui.Enabled = false
	ContextActionService:UnbindAction("GunShopKeys")
	MouseLook.free("GunShop", false)
	if renderConn then
		renderConn:Disconnect()
		renderConn = nil
	end
	local cam = workspace.CurrentCamera
	if savedCam then
		cam.CameraType = Enum.CameraType.Custom
		savedCam = nil
	end
	CloseRemote:FireServer()
end

local function openShop(data: Shop)
	shop = data
	category, sel, scroll = nil, 1, 0
	status.Text = ""
	render()
	if open then
		return
	end
	open = true
	gui.Enabled = true
	MouseLook.free("GunShop", true)
	ContextActionService:BindActionAtPriority(
		"GunShopKeys",
		onKey,
		false,
		Enum.ContextActionPriority.High.Value + 100,
		table.unpack(SINK)
	)
	local cam = workspace.CurrentCamera
	if data.Camera then
		savedCam = { type = cam.CameraType, cf = cam.CFrame }
		local from = cam.CFrame
		local t0 = os.clock()
		renderConn = RunService.RenderStepped:Connect(function()
			cam.CameraType = Enum.CameraType.Scriptable
			local a = math.clamp((os.clock() - t0) / 0.6, 0, 1)
			a = 1 - (1 - a) ^ 3
			cam.CFrame = from:Lerp(data.Camera :: CFrame, a)
			UserInputService.MouseBehavior = Enum.MouseBehavior.Default
			UserInputService.MouseIconEnabled = true
			-- walked away, died, knocked down
			local char = player.Character
			local hum = char and char:FindFirstChildOfClass("Humanoid")
			local rootPart = char and char:FindFirstChild("HumanoidRootPart") :: BasePart?
			if
				not hum
				or hum.Health <= 0
				or (char :: Model):GetAttribute("Knocked") == true
				or not rootPart
				or (data.At and (rootPart.Position - data.At).Magnitude > CFG.LeaveDistance)
			then
				close()
			end
		end)
	end
end

closeBtn.MouseButton1Click:Connect(function()
	close()
end)
buyBtn.MouseButton1Click:Connect(activate)
OpenRemote.OnClientEvent:Connect(openShop)
player:GetAttributeChangedSignal("Cash"):Connect(function()
	if open then
		render()
	end
end)
player:GetAttributeChangedSignal("Bank"):Connect(function()
	if open then
		render()
	end
end)
player.CharacterRemoving:Connect(close)
