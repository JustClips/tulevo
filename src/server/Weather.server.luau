-- Picks the weather (see Config.Weather, Shared/WeatherTypes) and shares it through
-- attributes on ReplicatedStorage.Shared:
--   Weather       current weather name
--   WeatherFrom   the one before it (clients fade from it)
--   WeatherSince  workspace:GetServerTimeNow() when it changed
-- Also loads the weather meshes (clouds, rain splashes) into ReplicatedStorage.WeatherMeshes
-- for the clients, and handles the /weather chat command.
local InsertService = game:GetService("InsertService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local ModelIds = require(Shared:WaitForChild("ModelIds"))
local WeatherTypes = require(Shared:WaitForChild("WeatherTypes"))

local W = Config.Weather
if not W or not W.Enabled then
	return
end

-- meshes ---------------------------------------------------------------------
task.spawn(function()
	local folder = Instance.new("Folder")
	folder.Name = "WeatherMeshes"
	local id = ModelIds.WeatherMeshes
	for attempt = 1, 4 do
		local ok, container = pcall(InsertService.LoadAsset, InsertService, id)
		if ok then
			for _, d in container:GetDescendants() do
				if d:IsA("MeshPart") then
					for _, c in d:GetChildren() do
						c:Destroy() -- no SurfaceAppearance etc.; the client colours them
					end
					d.Anchored = true
					d.Parent = folder
				end
			end
			container:Destroy()
			break
		end
		warn(`[Weather] could not load the weather meshes ({id}), try {attempt}: {container}`)
		task.wait(3 * attempt)
	end
	folder.Parent = ReplicatedStorage
end)

-- weather state --------------------------------------------------------------
local auto = W.Cycle
local nextChange = math.huge

local function set(name: string)
	if not WeatherTypes[name] then
		return
	end
	Shared:SetAttribute("WeatherFrom", Shared:GetAttribute("Weather") or name)
	Shared:SetAttribute("Weather", name)
	Shared:SetAttribute("WeatherSince", workspace:GetServerTimeNow())
	print(`[Weather] {name}`)
end

local function roll(): string
	local current = Shared:GetAttribute("Weather")
	local total = 0
	for name, w in W.Chances do
		if name ~= current and WeatherTypes[name] then
			total += w
		end
	end
	local r = math.random() * total
	for name, w in W.Chances do
		if name ~= current and WeatherTypes[name] then
			r -= w
			if r <= 0 then
				return name
			end
		end
	end
	return "Clear"
end

local function schedule()
	nextChange = os.clock() + math.random(W.MinMinutes * 60, W.MaxMinutes * 60)
end

Shared:SetAttribute("Weather", W.Start)
Shared:SetAttribute("WeatherFrom", W.Start)
Shared:SetAttribute("WeatherSince", workspace:GetServerTimeNow() - W.FadeSeconds)
schedule()

task.spawn(function()
	while true do
		task.wait(5)
		if auto and os.clock() >= nextChange then
			set(roll())
			schedule()
		end
	end
end)

-- /weather <name|auto> -------------------------------------------------------
local NAMES = {}
for name in WeatherTypes do
	NAMES[name:lower()] = name
end

local function isAdmin(player: Player): boolean
	return RunService:IsStudio() or table.find(W.Admins, player.UserId) ~= nil
end

local function onChat(player: Player, msg: string)
	local arg = msg:lower():match("^/weather%s+(%S+)")
	if not arg or not isAdmin(player) then
		return
	end
	if arg == "auto" then
		auto = true
		schedule()
		print(`[Weather] {player.Name}: back to the automatic cycle`)
	elseif NAMES[arg] then
		auto = false -- stays until /weather auto
		set(NAMES[arg])
	end
end

-- new chat (TextChatService): a real chat command, so "/weather rain" isn't posted as a message
local TextChatService = game:GetService("TextChatService")
if TextChatService.ChatVersion == Enum.ChatVersion.TextChatService then
	local cmd = Instance.new("TextChatCommand")
	cmd.Name = "WeatherCommand"
	cmd.PrimaryAlias = "/weather"
	cmd.Triggered:Connect(function(source: TextSource, text: string)
		local player = Players:GetPlayerByUserId(source.UserId)
		if player then
			onChat(player, text)
		end
	end)
	cmd.Parent = TextChatService
else
	local function hook(player: Player)
		player.Chatted:Connect(function(msg)
			onChat(player, msg)
		end)
	end
	Players.PlayerAdded:Connect(hook)
	for _, p in Players:GetPlayers() do
		hook(p)
	end
end
