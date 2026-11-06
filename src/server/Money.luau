-- Player money, server only. Every player has two balances, kept as attributes on the
-- Player (so the HUD can read them): "Cash" (wallet) and "Bank". Whole dollars.
--
--   local Money = require(ServerScriptService.Server.Money)
--   Money.get(player)              -> cash, bank
--   Money.addCash(player, 100)     -- negative takes money; returns false if not enough
--   Money.addBank(player, -50)
--   Money.deposit(player, 200)     -- wallet -> bank
--   Money.withdraw(player, 200)    -- bank -> wallet
--
-- Server only: there is no money remote. Anything that pays or charges (ATMs, shops, jobs)
-- must decide the amount on the server and call these; never take an amount from a client.
-- Amounts that aren't real numbers (NaN, inf) are refused, so a bad value can't poison a
-- balance.
--
-- Saved in a DataStore (Config.Money) when a player leaves, on shutdown and every
-- AutosaveSeconds. If loading failed, that player's money is never saved, so a
-- DataStore hiccup can't wipe a real balance with the starting amount.
local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))
local cfg = Config.Money

local Money = {}

local store: DataStore? = nil
if cfg.Save then
	local ok, result = pcall(DataStoreService.GetDataStore, DataStoreService, cfg.DataStoreName)
	if ok then
		store = result
	else
		warn("[Money] no DataStore, balances won't save:", result)
	end
end

local loaded: { [Player]: boolean } = {} -- true = loaded from the store, safe to save

local function key(player: Player): string
	return "p_" .. player.UserId
end

local function whole(n: number): number
	return math.floor(n + 0.5)
end

local LIMIT = 1e12 -- way above any real balance; stops a runaway number

local function finite(n: any): boolean
	return typeof(n) == "number" and n == n and math.abs(n) < LIMIT
end

function Money.get(player: Player): (number, number)
	return player:GetAttribute("Cash") or 0, player:GetAttribute("Bank") or 0
end

local function change(player: Player, attr: string, amount: number): boolean
	if not finite(amount) then
		warn(`[Money] refused a bad amount for {player.Name}: {amount}`)
		return false
	end
	amount = whole(amount)
	local current = player:GetAttribute(attr) or 0
	if current + amount < 0 or current + amount >= LIMIT then
		return false
	end
	player:SetAttribute(attr, current + amount)
	return true
end

function Money.addCash(player: Player, amount: number): boolean
	return change(player, "Cash", amount)
end

function Money.addBank(player: Player, amount: number): boolean
	return change(player, "Bank", amount)
end

function Money.deposit(player: Player, amount: number): boolean
	if not finite(amount) then
		return false
	end
	amount = whole(amount)
	if amount <= 0 or not change(player, "Cash", -amount) then
		return false
	end
	change(player, "Bank", amount)
	return true
end

function Money.withdraw(player: Player, amount: number): boolean
	if not finite(amount) then
		return false
	end
	amount = whole(amount)
	if amount <= 0 or not change(player, "Bank", -amount) then
		return false
	end
	change(player, "Cash", amount)
	return true
end

local function save(player: Player)
	if not store or not loaded[player] then
		return
	end
	local cash, bank = Money.get(player)
	local ok, err = pcall(function()
		store:SetAsync(key(player), { cash = cash, bank = bank }, { player.UserId })
	end)
	if not ok then
		warn("[Money] save failed for", player.Name, err)
	end
end

local function load(player: Player)
	local cash, bank = cfg.StartCash, cfg.StartBank
	if store then
		local ok, data = pcall(function()
			return store:GetAsync(key(player))
		end)
		if ok then
			loaded[player] = true
			if type(data) == "table" then
				local c, b = tonumber(data.cash), tonumber(data.bank)
				cash = if finite(c) and c >= 0 then whole(c :: number) else cash
				bank = if finite(b) and b >= 0 then whole(b :: number) else bank
			end
		else
			warn("[Money] load failed for", player.Name, "(not saving this session):", data)
		end
	end
	if player.Parent then
		player:SetAttribute("Cash", cash)
		player:SetAttribute("Bank", bank)
	end
end

function Money.start()
	Players.PlayerAdded:Connect(load)
	for _, p in Players:GetPlayers() do
		task.spawn(load, p)
	end
	Players.PlayerRemoving:Connect(function(player)
		save(player)
		loaded[player] = nil
	end)
	game:BindToClose(function()
		local left = 0
		for _, p in Players:GetPlayers() do
			left += 1
			task.spawn(function()
				save(p)
				left -= 1
			end)
		end
		local t = os.clock()
		while left > 0 and os.clock() - t < 25 do
			task.wait()
		end
	end)
	task.spawn(function()
		while true do
			task.wait(cfg.AutosaveSeconds)
			for _, p in Players:GetPlayers() do
				task.spawn(save, p)
			end
		end
	end)
end

return Money
