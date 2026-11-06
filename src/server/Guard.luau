--[[
	Small helpers every remote handler uses, so all of them check the same things the same way
	(docs/server-checks.md).

		Guard.alive(player) -> (character, humanoid, root)?  -- standing: health > 0, not knocked
		Guard.rate(player, "Fire", 12, 4) -> bool           -- token bucket: 12 a second, bursts of 4
		Guard.number(x, min?, max?) -> number?              -- a real number (not NaN / inf), in range
		Guard.flag(player, reason)                           -- counts on the CheatFlags attribute + warns
		Guard.allowTeleport(player, seconds?)                -- the server just moved this player on
		                                                        purpose (MovementGuard skips the jump)

	Remote arguments come from the client and can be anything: check the type first, then the
	range, and never trust a position, a target or an amount the client sends.
]]

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("Config"))

local Guard = {}

local function cfg()
	return Config.AntiCheat or {}
end

function Guard.alive(player: Player): (Model?, Humanoid?, BasePart?)
	local character = player.Character
	local humanoid = character and character:FindFirstChildOfClass("Humanoid")
	local root = character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
	if not (character and humanoid and root) or humanoid.Health <= 0 or character:GetAttribute("Knocked") == true then
		return nil, nil, nil
	end
	return character, humanoid, root
end

function Guard.number(x: any, min: number?, max: number?): number?
	if typeof(x) ~= "number" or x ~= x or x == math.huge or x == -math.huge then
		return nil
	end
	if (min and x < min) or (max and x > max) then
		return nil
	end
	return x
end

-- token buckets: buckets[player][key] = { tokens, at }
local buckets: { [Player]: { [string]: { number } } } = {}

function Guard.rate(player: Player, key: string, perSecond: number, burst: number?): boolean
	local mine = buckets[player]
	if not mine then
		mine = {}
		buckets[player] = mine
	end
	local cap = burst or perSecond
	local now = os.clock()
	local b = mine[key]
	if not b then
		b = { cap, now }
		mine[key] = b
	end
	b[1] = math.min(cap, b[1] + (now - b[2]) * perSecond)
	b[2] = now
	if b[1] < 1 then
		return false
	end
	b[1] -= 1
	return true
end

local flagCounts: { [Player]: { [string]: number } } = {}

function Guard.flag(player: Player, reason: string)
	local n = (player:GetAttribute("CheatFlags") or 0) + 1
	player:SetAttribute("CheatFlags", n)
	local mine = flagCounts[player] or {}
	flagCounts[player] = mine
	mine[reason] = (mine[reason] or 0) + 1
	-- first time for each reason, then every 10th, so a spammer can't flood the log
	if cfg().Debug or mine[reason] % 10 == 1 then
		warn(`[Guard] {player.Name} ({player.UserId}): {reason} (x{mine[reason]})`)
	end
end

-- MovementGuard reads this: until this os.clock() the player may jump anywhere
local teleportUntil: { [Player]: number } = {}

function Guard.allowTeleport(player: Player, seconds: number?)
	teleportUntil[player] = os.clock() + (seconds or cfg().SpawnGrace or 2)
end

function Guard.teleportAllowed(player: Player): boolean
	return (teleportUntil[player] or 0) > os.clock()
end

Players.PlayerRemoving:Connect(function(player)
	buckets[player] = nil
	flagCounts[player] = nil
	teleportUntil[player] = nil
end)

return Guard
