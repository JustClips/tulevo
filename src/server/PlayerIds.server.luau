--[[
	Player IDs, shown on the overhead name tags (Client/NameTags):
	- TUID: short ID handed out when a player joins this server. Counts up 1, 2, 3...
	  and is never reused while the server runs.
	- StaticUID: permanent ID for the account. The first time someone joins they get the
	  next number from a global counter in a DataStore; after that it's loaded, so it's the
	  same in every server, every session.
	Both are attributes on the Player ("TUID", "StaticUID"), so any script can read them.
	If the DataStore can't be reached, StaticUID is simply left unset for that session.

	Also hides Roblox's default overhead name, since the tag replaces it.
]]

local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterPlayer = game:GetService("StarterPlayer")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local cfg = Config.PlayerIds

local COUNTER_KEY = "next_static_uid"

-- Roblox's own name above heads: off for everyone
StarterPlayer.NameDisplayDistance = 0

local store: DataStore? = nil
do
	local ok, result = pcall(DataStoreService.GetDataStore, DataStoreService, cfg.DataStoreName)
	if ok then
		store = result
	else
		warn("[PlayerIds] no DataStore, static IDs won't load:", result)
	end
end

local function retry<T>(what: string, fn: () -> T): (boolean, T?)
	local err
	for attempt = 1, 3 do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		err = result
		task.wait(attempt * 2)
	end
	warn(`[PlayerIds] {what} failed:`, err)
	return false, nil
end

local function staticUID(player: Player): number?
	if not store or player.UserId <= 0 then
		return nil -- Studio "Local Server" test players have no real account
	end
	local key = "u_" .. player.UserId

	local ok, existing = retry("load for " .. player.Name, function()
		return store:GetAsync(key)
	end)
	if not ok then
		return nil
	end
	if type(existing) == "number" then
		return existing
	end

	-- new account: take the next number from the global counter
	local gotNew, fresh = retry("counter", function()
		return store:UpdateAsync(COUNTER_KEY, function(old)
			local nextId = if type(old) == "number" then old + 1 else cfg.FirstStaticUID
			return nextId
		end)
	end)
	if not gotNew then
		return nil
	end
	-- keep whatever is already stored (if another server assigned one at the same
	-- moment, theirs wins and this counter number just goes unused)
	local saved, final = retry("save for " .. player.Name, function()
		return store:UpdateAsync(key, function(old)
			if type(old) == "number" then
				return old
			end
			return fresh
		end, { player.UserId })
	end)
	return if saved then final else nil
end

local nextTUID = 0

local function hideDefaultName(character: Model)
	local humanoid = character:WaitForChild("Humanoid", 10) :: Humanoid?
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
	end
end

local function onPlayer(player: Player)
	nextTUID += 1
	player:SetAttribute("TUID", nextTUID)

	player.CharacterAdded:Connect(hideDefaultName)
	if player.Character then
		task.spawn(hideDefaultName, player.Character)
	end

	local id = staticUID(player)
	if id and player.Parent then
		player:SetAttribute("StaticUID", id)
	end
end

Players.PlayerAdded:Connect(onPlayer)
for _, player in Players:GetPlayers() do
	task.spawn(onPlayer, player)
end
