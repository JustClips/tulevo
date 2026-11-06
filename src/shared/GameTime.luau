-- In-game clock, same answer on server and client.
-- The server (Server/GameClock) stores when the clock started in the "ClockOrigin" /
-- "ClockOriginMinutes" attributes on this module's parent folder (ReplicatedStorage.Shared);
-- everyone works the time out from workspace:GetServerTimeNow(), so nothing is sent per frame.
--
-- GameTime.now() -> {
--     hour, min,           -- 0-23, 0-59
--     clock,               -- hours as a decimal, for Lighting.ClockTime
--     day, month, year,    -- in-game date
--     weekday,             -- "Monday" ... "Sunday"
-- }
local Config = require(script.Parent:WaitForChild("Config"))

local GameTime = {}

local WEEKDAYS = { "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday" }
local holder = script.Parent

-- game minutes that pass per real second
function GameTime.rate(): number
	return (24 * 60) / (Config.Time.DayMinutes * 60)
end

-- in-game minutes since 00:00 of the start date (nil until the server has set the clock)
function GameTime.totalMinutes(): number?
	local origin = holder:GetAttribute("ClockOrigin")
	local startMinutes = holder:GetAttribute("ClockOriginMinutes")
	if not origin or not startMinutes then
		return nil
	end
	return startMinutes + (workspace:GetServerTimeNow() - origin) * GameTime.rate()
end

function GameTime.now()
	local total = GameTime.totalMinutes()
	if not total then
		return nil
	end
	local startDate = holder:GetAttribute("ClockStartDate") or 0 -- unix secs, 00:00 UTC
	local t = os.date("!*t", startDate + math.floor(total) * 60)
	local minutesToday = total % (24 * 60)
	return {
		hour = t.hour,
		min = t.min,
		clock = minutesToday / 60,
		day = t.day,
		month = t.month,
		year = t.year,
		weekday = WEEKDAYS[t.wday],
	}
end

return GameTime
