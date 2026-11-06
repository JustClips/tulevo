--[[
	Overhead name tags (replace Roblox's default name; Server/PlayerIds hides that):
		Username [TUID]
		#StaticUID
	Small white text above each other player's head, hidden behind walls, fading out
	with distance (Config.PlayerIds). Line 2 only shows once the static ID has loaded.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local cfg = Config.PlayerIds

local localPlayer = Players.LocalPlayer
local playerGui = localPlayer:WaitForChild("PlayerGui")

local NAME_FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.SemiBold)
local ID_FONT = Font.new("rbxasset://fonts/families/BuilderSans.json", Enum.FontWeight.Medium)

type Tag = { gui: BillboardGui, labels: { TextLabel }, strokes: { UIStroke } }

local tags: { [Player]: Tag } = {}

local function line(parent: Instance, order: number, font: Font, size: number): (TextLabel, UIStroke)
	local label = Instance.new("TextLabel")
	label.Name = "Line" .. order
	label.LayoutOrder = order
	label.BackgroundTransparency = 1
	label.Size = UDim2.new(1, 0, 0, size + 2)
	label.FontFace = font
	label.TextSize = size
	label.TextColor3 = Color3.new(1, 1, 1)
	label.Text = ""
	local stroke = Instance.new("UIStroke")
	stroke.Color = Color3.new(0, 0, 0)
	stroke.Thickness = 1
	stroke.Transparency = 0.55
	stroke.Parent = label
	label.Parent = parent
	return label, stroke
end

local function refresh(player: Player, tag: Tag)
	local tuid = player:GetAttribute("TUID")
	local static = player:GetAttribute("StaticUID")
	tag.labels[1].Text = if tuid then `{player.Name} [{tuid}]` else player.Name
	tag.labels[2].Text = if static then `#{static}` else ""
	tag.labels[2].Visible = static ~= nil
end

local function attach(player: Player, character: Model)
	local tag = tags[player]
	if not tag then
		return
	end
	local head = character:WaitForChild("Head", 10)
	if head and tags[player] == tag and player.Character == character then
		tag.gui.Adornee = head
	end
end

local function addPlayer(player: Player)
	if player == localPlayer and not cfg.ShowOwnTag then
		return
	end

	local gui = Instance.new("BillboardGui")
	gui.Name = "NameTag_" .. player.Name
	gui.ResetOnSpawn = false
	gui.AlwaysOnTop = false -- walls hide it
	gui.LightInfluence = 0
	gui.Size = UDim2.fromOffset(260, 40)
	gui.StudsOffsetWorldSpace = Vector3.new(0, 2.1, 0)
	gui.MaxDistance = cfg.TagMaxDistance
	gui.ClipsDescendants = false

	local list = Instance.new("UIListLayout")
	list.SortOrder = Enum.SortOrder.LayoutOrder
	list.HorizontalAlignment = Enum.HorizontalAlignment.Center
	list.VerticalAlignment = Enum.VerticalAlignment.Bottom
	list.Padding = UDim.new(0, 0)
	list.Parent = gui

	local name, nameStroke = line(gui, 1, NAME_FONT, 15)
	local id, idStroke = line(gui, 2, ID_FONT, 14)

	local tag: Tag = { gui = gui, labels = { name, id }, strokes = { nameStroke, idStroke } }
	tags[player] = tag
	refresh(player, tag)
	player:GetAttributeChangedSignal("TUID"):Connect(function()
		refresh(player, tag)
	end)
	player:GetAttributeChangedSignal("StaticUID"):Connect(function()
		refresh(player, tag)
	end)

	gui.Parent = playerGui
	player.CharacterAdded:Connect(function(character)
		attach(player, character)
	end)
	if player.Character then
		task.spawn(attach, player, player.Character)
	end
end

local function removePlayer(player: Player)
	local tag = tags[player]
	if tag then
		tags[player] = nil
		tag.gui:Destroy()
	end
end

Players.PlayerAdded:Connect(addPlayer)
Players.PlayerRemoving:Connect(removePlayer)
for _, player in Players:GetPlayers() do
	task.spawn(addPlayer, player)
end

-- fade out over the last few studs before MaxDistance cuts the tag off
RunService.RenderStepped:Connect(function()
	local camera = workspace.CurrentCamera
	if not camera then
		return
	end
	local eye = camera.CFrame.Position
	local fadeStart = cfg.TagMaxDistance - cfg.TagFadeStuds
	for _, tag in tags do
		local head = tag.gui.Adornee :: BasePart?
		if head and head.Parent then
			local dist = (head.Position - eye).Magnitude
			local fade = math.clamp((dist - fadeStart) / cfg.TagFadeStuds, 0, 1)
			for i, label in tag.labels do
				label.TextTransparency = fade
				tag.strokes[i].Transparency = 0.55 + 0.45 * fade
			end
		end
	end
end)
