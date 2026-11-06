-- Server weather (ModuleScript; Server/WeatherRunner starts it). Picks the weather (see Config.Weather, Shared/WeatherTypes) and shares it through
-- attributes on ReplicatedStorage.Shared:
--   Weather       current weather name
--   WeatherFrom   the one before it (clients fade from it)
--   WeatherSince  workspace:GetServerTimeNow() when it changed
-- Also handles the /weather chat command, and in storms picks lightning strikes and sends
-- them to every client (ReplicatedStorage.WeatherRemotes.Strike: position, seed, kind).
-- The debug panel (Server/DebugPanel) uses Weather.list() and Weather.set(name).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local WeatherTypes = require(Shared:WaitForChild("WeatherTypes"))

local W = Config.Weather
local Weather = {}

-- in the order the debug panel shows them
local ORDER = { "Clear", "Cloudy", "Rain", "HeavyRain", "Thunderstorm" }

-- weather state --------------------------------------------------------------
local auto = W.Cycle
local nextChange = math.huge
local started = false

local function set(name: string)
	if not WeatherTypes[name] then
		error(`unknown weather {name}`)
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

-- lightning ------------------------------------------------------------------
local strikeRemote: RemoteEvent

local function stormy(): boolean
	local cur = WeatherTypes[Shared:GetAttribute("Weather") or "Clear"]
	local since = Shared:GetAttribute("WeatherSince") or 0
	-- wait for the storm to roll in a bit before the first bolt
	return cur ~= nil and (cur.storm or 0) > 0 and workspace:GetServerTimeNow() - since > W.FadeSeconds * 0.4
end

local strikeParams = RaycastParams.new()
strikeParams.FilterType = Enum.RaycastFilterType.Exclude

-- a bolt somewhere: kind "bolt" (hits the ground / a roof) or "sheet" (flash inside the clouds)
function Weather.strike(at: Vector3?, kind: string?)
	if not strikeRemote then
		return
	end
	local L = W.Lightning
	kind = kind or (if math.random() < L.SheetChance then "sheet" else "bolt")
	local players = Players:GetPlayers()
	local centre = Vector3.zero
	local near = false
	if #players > 0 then
		local plr = players[math.random(1, #players)]
		local root = plr.Character and plr.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
		if root then
			centre = root.Position
			near = math.random() < L.NearChance
		end
	end
	if not at then
		local ang = math.random() * math.pi * 2
		local d = if near
			then L.NearMin + math.random() * (L.NearMax - L.NearMin)
			else math.random() ^ 0.6 * L.FarRadius
		at = centre + Vector3.new(math.cos(ang) * d, 0, math.sin(ang) * d)
	end
	local pos = at :: Vector3
	if kind == "bolt" then
		-- hits whatever is highest there (roofs, towers, ground)
		local list = {}
		for _, p in players do
			if p.Character then
				table.insert(list, p.Character)
			end
		end
		strikeParams.FilterDescendantsInstances = list
		-- try a few spots close together and take the highest, so towers draw strikes
		local best: Vector3? = nil
		for i = 1, 3 do
			local o = if i == 1 then Vector3.zero else Vector3.new(math.random(-60, 60), 0, math.random(-60, 60))
			local hit =
				workspace:Raycast(Vector3.new(pos.X + o.X, 2000, pos.Z + o.Z), Vector3.new(0, -2600, 0), strikeParams)
			if hit and (not best or hit.Position.Y > best.Y) then
				best = hit.Position
			end
		end
		pos = best or Vector3.new(pos.X, 0, pos.Z)
	end
	strikeRemote:FireAllClients(pos, math.random(1, 2 ^ 30), kind)
end

function Weather.list(): { string }
	local list = table.clone(ORDER)
	for name in WeatherTypes do
		if not table.find(list, name) then
			table.insert(list, name)
		end
	end
	return list
end

-- switch now (fades over FadeSeconds); stays until the cycle is turned back on with auto()
function Weather.set(name: string)
	auto = false
	set(name)
end

-- back to the automatic cycle
function Weather.auto()
	auto = true
	schedule()
end

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
	if arg == "strike" then
		local root = player.Character and player.Character:FindFirstChild("HumanoidRootPart") :: BasePart?
		Weather.strike(root and root.Position + root.CFrame.LookVector * 80, "bolt")
	elseif arg == "auto" then
		Weather.auto()
		print(`[Weather] {player.Name}: back to the automatic cycle`)
	elseif NAMES[arg] then
		Weather.set(NAMES[arg]) -- stays until /weather auto
	end
end

local function hookChat()
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
end

function Weather.start()
	if started or not W or not W.Enabled then
		return
	end
	started = true
	Shared:SetAttribute("Weather", W.Start)
	Shared:SetAttribute("WeatherFrom", W.Start)
	Shared:SetAttribute("WeatherSince", workspace:GetServerTimeNow() - W.FadeSeconds)
	schedule()
	hookChat()
	local remotes = Instance.new("Folder")
	remotes.Name = "WeatherRemotes"
	strikeRemote = Instance.new("RemoteEvent")
	strikeRemote.Name = "Strike"
	strikeRemote.Parent = remotes
	remotes.Parent = ReplicatedStorage
	task.spawn(function()
		while true do
			local L = W.Lightning
			task.wait(L.MinGap + math.random() * (L.MaxGap - L.MinGap))
			if stormy() then
				Weather.strike()
			end
		end
	end)
	task.spawn(function()
		while true do
			task.wait(5)
			if auto and os.clock() >= nextChange then
				set(roll())
				schedule()
			end
		end
	end)
end

return Weather
