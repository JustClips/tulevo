-- Starts the in-game clock (see Shared/GameTime) and turns the sun with it.
local Lighting = game:GetService("Lighting")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage:WaitForChild("Shared")
local Config = require(Shared:WaitForChild("Config"))
local GameTime = require(Shared:WaitForChild("GameTime"))

-- today's real date at 00:00 UTC
local now = os.time()
local startDate = now - now % 86400

Shared:SetAttribute("ClockStartDate", startDate)
Shared:SetAttribute("ClockOriginMinutes", Config.Time.StartHour * 60)
Shared:SetAttribute("ClockOrigin", workspace:GetServerTimeNow())

if Config.Time.DriveLighting then
	while true do
		local t = GameTime.now()
		if t then
			Lighting.ClockTime = t.clock
		end
		task.wait(0.5)
	end
end
